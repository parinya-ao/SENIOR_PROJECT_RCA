"""One-shot, bounded Gate 1 recorder around the existing UPDI Monitor classes."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.arq_trial import parse_event, status_complete


def utc():
    return datetime.now(timezone.utc).isoformat()


def startup_profile(path):
    tree = ast.parse(Path(path).read_text())
    updi = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'UPDI')
    init = next(n for n in updi.body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
    breaks = sum(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == 'send_break' for n in ast.walk(init))
    serial_updi = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'SerialUPDI')
    serial_init = next(n for n in serial_updi.body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
    reset_default = next(a for a in serial_init.args.defaults
                         if isinstance(a, ast.Constant) and isinstance(a.value, bool))
    return {'break_calls': breaks, 'startup_reset': reset_default.value,
            'normal_monitor_startup_authorized': breaks == 2 and reset_default.value is False}


class Gate1Audit:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.lock = threading.RLock()
        self.current_transaction = None
        self.expected_length = None
        self.expected_value = None
        self.operation = 'INITIALIZATION'
        self.trace = self.directory / 'transport-trace.jsonl'
        self.acquisition = self.directory / 'acquisition-events.jsonl'
        self.stdout = self.directory / 'monitor.stdout.log'
        self.stderr = self.directory / 'monitor.stderr.log'
        self.transactions = self.directory / 'status-transactions.jsonl'
        self.break_count = 0
        self.synch_count = 0
        self.resume_count = 0
        self.reset_count = 0
        self.last_complete_request_hex = None
        self.updi_operation = 'UNKNOWN'
        self.updi_instruction_hex = None
        self.device_path = None
        self.adapter_identity = 'UNKNOWN'
        self.rows = []
        self.first_failure = None
        self.stdout_stream = None

    def _append(self, path, record, durable=False):
        with self.lock:
            with path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record, sort_keys=True) + '\n')
                stream.flush()
                if durable:
                    os.fsync(stream.fileno())

    def event(self, name, **values):
        self._append(self.acquisition, {'timestamp_utc': utc(),
                      'timestamp_monotonic_ns': time.monotonic_ns(),
                      'host_process_id': os.getpid(), 'event': name, **values}, True)

    def transport(self, **record):
        self._append(self.trace, {'timestamp_utc': utc(),
                      'timestamp_monotonic_ns': time.monotonic_ns(),
                      'transaction_index': self.current_transaction,
                      'operation_name': self.operation,
                      'updi_operation': self.updi_operation,
                      'updi_instruction_hex': self.updi_instruction_hex,
                      'device_path':self.device_path,
                      'adapter_identity':self.adapter_identity,
                      'host_process_id':os.getpid(),
                      'expected_response_length': self.expected_length,
                      'expected_response_value_hex': None if self.expected_value is None else self.expected_value.hex(),
                      **record})

    def fail(self, error, operation):
        if self.first_failure is not None:
            return
        self.first_failure = {'timestamp_utc': utc(), 'timestamp_monotonic_ns': time.monotonic_ns(),
                              'transaction_index': self.current_transaction,
                              'operation_name': operation, 'exception_type': type(error).__name__,
                              'exception_message': str(error),
                              'last_complete_request_hex':self.last_complete_request_hex,
                              'expected_response_length':self.expected_length,
                              'expected_response_value_hex':None if self.expected_value is None else self.expected_value.hex(),
                              'actual_rx_hex': self.trace_last_rx(),
                              'actual_rx_length': self.trace_last_rx_length(),
                              'previous_successful_transaction': self.rows[-1] if self.rows else None}
        self._append(self.directory / 'first-failure.json', self.first_failure, True)

    def trace_last_rx(self):
        try:
            lines = self.trace.read_text().splitlines()
            for line in reversed(lines):
                item = json.loads(line)
                if item.get('direction') == 'read' and item.get('transaction_index') == self.current_transaction:
                    return item.get('actual_rx_hex', 'UNKNOWN')
        except (OSError, json.JSONDecodeError):
            pass
        return 'UNKNOWN'

    def trace_last_rx_length(self):
        try:
            lines = self.trace.read_text().splitlines()
            for line in reversed(lines):
                item = json.loads(line)
                if item.get('direction') == 'read' and item.get('transaction_index') == self.current_transaction:
                    return item.get('actual_rx_length', 'UNKNOWN')
        except (OSError, json.JSONDecodeError):
            pass
        return 'UNKNOWN'

    def write_transaction(self, row):
        self.rows.append(row)
        self._append(self.transactions, row, True)


class TracePort:
    """Transparent serial proxy: delegates unchanged and records returned bytes."""
    def __init__(self, port, audit):
        object.__setattr__(self, '_port', port)
        object.__setattr__(self, '_audit', audit)

    def __getattr__(self, name):
        return getattr(self._port, name)

    def __setattr__(self, name, value):
        setattr(self._port, name, value)

    def write(self, data):
        start = time.monotonic_ns()
        settings={'baudrate':self.baudrate,'parity':self.parity,'stopbits':self.stopbits,
                  'read_timeout_s':self.timeout,'write_timeout_s':self.write_timeout}
        try:
            result = self._port.write(data)
        except Exception as exc:
            self._audit.transport(direction='write', host_tx_hex=bytes(data).hex(),
                                  host_tx_length=len(data), serial_write_start_ns=start,
                                  serial_write_end_ns=time.monotonic_ns(), serial_settings=settings,
                                  exception_type=type(exc).__name__,
                                  exception_message=str(exc))
            raise
        self._audit.transport(direction='write', host_tx_hex=bytes(data).hex(),
                              host_tx_length=len(data), bytes_written=result,
                              serial_write_start_ns=start, serial_write_end_ns=time.monotonic_ns(),
                              serial_settings=settings)
        return result

    def read(self, length):
        start = time.monotonic_ns()
        settings={'baudrate':self.baudrate,'parity':self.parity,'stopbits':self.stopbits,
                  'read_timeout_s':self.timeout,'write_timeout_s':self.write_timeout}
        try:
            data = self._port.read(length)
        except Exception as exc:
            self._audit.transport(direction='read', requested_response_length=length,
                                  actual_rx_hex='UNKNOWN', actual_rx_length='UNKNOWN',
                                  serial_read_start_ns=start, serial_read_end_ns=time.monotonic_ns(),
                                  serial_settings=settings,
                                  exception_type=type(exc).__name__, exception_message=str(exc))
            raise
        self._audit.transport(direction='read', requested_response_length=length,
                              actual_rx_hex=bytes(data).hex(), actual_rx_length=len(data),
                              serial_read_start_ns=start, serial_read_end_ns=time.monotonic_ns(),
                              serial_settings=settings)
        return data


class MonitorConsole:
    def __init__(self):
        self.input = queue.Queue()
        self.output = queue.Queue()

    def get(self):
        return self.input.get()

    def put(self, byte):
        self.output.put((byte, time.monotonic_ns()))

    def send(self, data):
        for byte in data:
            self.input.put(byte)


def instrument(module, audit, serial_module):
    real_serial = serial_module.Serial

    def open_exclusive(*args, **kwargs):
        kwargs['exclusive'] = True
        raw = real_serial(*args, **kwargs)
        audit.event('SERIAL_PORT_OPEN', device_path=str(args[0]), baudrate=args[1],
                    parity=kwargs.get('parity'), stopbits=kwargs.get('stopbits'), exclusive=True)
        return TracePort(raw, audit)

    serial_module.Serial = open_exclusive
    original_break = module.SerialPort.send_break
    def send_break(self):
        audit.break_count += 1
        audit.event('UPDI_BREAK_START', break_index=audit.break_count,
                    baudrate_before=self.dev.baudrate)
        try:
            return original_break(self)
        except Exception as exc:
            audit.fail(exc, 'UPDI_BREAK')
            raise
        finally:
            audit.event('UPDI_BREAK_END', break_index=audit.break_count,
                        baudrate_after=self.dev.baudrate)
    module.SerialPort.send_break = send_break

    original_instr = module.UPDI.instr
    def instr(self, data):
        audit.synch_count += 1
        caller=inspect.currentframe().f_back.f_code.co_name
        old_operation,old_instruction=audit.updi_operation,audit.updi_instruction_hex
        audit.updi_operation='UPDI.'+caller
        audit.updi_instruction_hex=bytes(data).hex()
        audit.operation = 'UPDI_SYNCH_INSTRUCTION'
        try:
            return original_instr(self, data)
        except Exception as exc:
            audit.fail(exc, audit.operation)
            raise
        finally:
            audit.updi_operation=old_operation
            audit.updi_instruction_hex=old_instruction
    module.UPDI.instr = instr

    for cls, method in [(module.SerialPort, 'send'), (module.SerialPort, 'recv'),
                        (module.UPDI, 'key'), (module.UPDI, 'reset'),
                        (module.SerialUPDI, 'send1'), (module.SerialUPDI, 'recv1')]:
        original = getattr(cls, method)
        def wrapper(self, *args, __original=original, __name=method, **kwargs):
            old = audit.operation
            audit.operation = f'{type(self).__name__}.{__name}'
            if __name == 'send' and args:
                audit.expected_length = len(args[0])
                audit.expected_value = bytes(args[0])
            elif __name == 'recv' and args:
                audit.expected_length = args[0]
                audit.expected_value = args[1] if len(args) > 1 else kwargs.get('expected')
            try:
                result = __original(self, *args, **kwargs)
                if __name == 'send' and args:
                    audit.last_complete_request_hex = bytes(args[0]).hex()
                if __name == 'reset':
                    audit.reset_count += 1
                    audit.event('CONTROLLED_CPU_RESET', operation='UPDI.reset', count=audit.reset_count)
                return result
            except Exception as exc:
                audit.fail(exc, audit.operation)
                raise
            finally:
                audit.operation = old
                if __name in ('recv','send'):
                    audit.expected_length = None
                    audit.expected_value = None
        setattr(cls, method, wrapper)

    original_ldcs = module.UPDI.ldcs
    def ldcs(self, address):
        value = original_ldcs(self, address)
        if address == module.ASI_OCD_STATUS and value & module.OCD_STOPPED:
            audit.event('OCD_STOP_OBSERVED', status=value)
        return value
    module.UPDI.ldcs = ldcs

    original_stcs = module.UPDI.stcs
    def stcs(self, address, value):
        if address == module.ASI_OCD_CTRLA and value == module.OCD_RUN:
            audit.resume_count += 1
            audit.event('OCD_CPU_RESUME', address=address, value=value, count=audit.resume_count)
        return original_stcs(self, address, value)
    module.UPDI.stcs = stcs
    return real_serial


def _parse_block(lines, expected):
    events = [parse_event(line) for line in lines]
    if not events or any(event is None for event in events):
        raise ValueError('status event parse failure')
    role = expected['role']
    for event in events:
        event['role'] = role
    names = [event['e'] for event in events]
    if not {'BOOT', 'IDENTITY', 'STATUS', 'RESULT', 'RTT_LAST', 'RTT_MIN',
            'RTT_MAX', 'RTT_COUNT', 'RX_DONE_COUNT', 'DECODE_ERRORS',
            'CONTROL_REJECTS', 'REG', 'STATUS_END'} <= set(names):
        raise ValueError('incomplete STATUS block')
    if not status_complete(events, role, 0):
        raise ValueError('STATUS_END missing, reordered, or overflowed')
    if any(int(event['s'], 16) != 0 for event in events):
        raise ValueError('STATUS session is not idle')
    status = next(event for event in events if event['e'] == 'STATUS')
    identity = next(event for event in events if event['e'] == 'IDENTITY')
    if status.get('ready') != '1' or status.get('overflow') != '0':
        raise ValueError('STATUS reports not-ready radio or logger overflow')
    if identity.get('build') != expected['build_id'] or identity.get('config') != expected['config_hash']:
        raise ValueError('firmware build/config identity mismatch')
    return events


def _readline(console, audit, terminal, deadline, output_file):
    line = bytearray()
    while time.monotonic() < deadline:
        if terminal.failure is not None:
            raise terminal.failure
        try:
            byte, host_ns = console.output.get(timeout=min(.05, max(0.001, deadline-time.monotonic())))
        except queue.Empty:
            continue
        raw = bytes([byte])
        output_file.write(raw)
        if byte == 0x0a:
            output_file.flush()
        line.extend(raw)
        if byte == 0x0a:
            return line.decode('ascii', errors='replace').rstrip('\r\n'), bytes(line)
        if len(line) > 8192:
            raise ValueError('monitor line exceeds 8192 bytes')
    raise TimeoutError('STATUS acquisition or transaction deadline')


def _read_block(console, audit, terminal, expected, deadline, output_file, startup=False):
    lines, events, raw_block = [], [], bytearray()
    seen_boot = False
    while time.monotonic() < deadline:
        line, raw_line = _readline(console, audit, terminal, deadline, output_file)
        lines.append(line)
        raw_block.extend(raw_line)
        event = parse_event(line)
        if event:
            events.append(event)
            if event['e'] == 'BOOT': seen_boot = True
            if event['e'] == 'STATUS_END':
                break
        if len(lines) > 64:
            raise ValueError('STATUS output exceeded bounded event count')
    if not lines or not events or events[-1]['e'] != 'STATUS_END':
        raise TimeoutError('incomplete STATUS_END before deadline')
    if startup and not seen_boot:
        raise ValueError('startup block did not contain BOOT')
    parsed = _parse_block(lines, expected)
    return lines, parsed, bytes(raw_block)


def read_data_space_byte(updi, address):
    """Read one byte using the AVR128DA 16-bit-address, byte-data LDS form."""
    if type(address) is not int or not 0 <= address <= 0xffff:
        raise ValueError('AVR128DA data-space address must fit in 16 bits')
    # DS40002183C Figure 35-6: SizeA=01 (16-bit address), SizeB=00 (byte) => LDS 0x04.
    updi.instr([0x04, address & 0xff, address >> 8])
    return updi.recv(1)[0]


def part_from_signature(signature):
    return 'AVR128DA28' if signature == bytes.fromhex('1e970a') else None


def run_gate1(port, directory):
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT/'artifacts/arq/gate1-updi') or directory.exists():
        raise ValueError('run directory must be a new child of artifacts/arq/gate1-updi')
    directory.mkdir(parents=True)
    for name in ['transport-trace.jsonl','acquisition-events.jsonl','status-transactions.jsonl',
                 'monitor.stdout.log','monitor.stderr.log']:
        (directory/name).write_text('')
    audit = Gate1Audit(directory)
    start = time.monotonic()
    deadline = start + 45
    status_deadline = None
    expected = json.loads((ROOT/'config/current_hardware.json').read_text())['receiver']
    manifest = json.loads((ROOT/'generated/arq_manifest.json').read_text())
    verified = json.loads((ROOT/'artifacts/arq/20261113T123837Z-standby/independent-verification.json').read_text())
    expected_identity = {'build_id':verified['receiver']['build_id'], 'config_hash':manifest['config_hash'],
                         'role':'receiver'}
    git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    git_status=subprocess.check_output(['git','status','--porcelain=v1','-uall'],cwd=ROOT,text=True)
    source_paths=['third_party/upditerm/upditerm.py','tools/arq_trial.py','tools/rca/gate1.py',
                  'tools/rca/gate1_live.py','tools/rf_proof.py','tools/device_detection/updi_probe.py',
                  'src/arq/main.cpp','config/current_hardware.json','generated/arq_manifest.json',
                  'artifacts/arq/20261113T123837Z-standby/independent-verification.json']
    (directory/'source-revision.json').write_text(json.dumps({'repository_root':str(ROOT),
        'requested_legacy_path':'/home/parinya/university/iwing-tracker/gateway-lora/loraboard',
        'git_head':git_head,'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        'preexisting_dirty_entries':len(git_status.splitlines()),'python':sys.version,
        'run_directory':str(directory),'utc':utc()},indent=2)+'\n')
    (directory/'source-hashes.json').write_text(json.dumps({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                                                            for p in source_paths},indent=2)+'\n')
    hist=json.loads((ROOT/'artifacts/arq/gate1-updi/20261113T142138Z/preservation.json').read_text())['historical_before']
    changed=[p for p,h in hist.items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    (directory/'preservation-before.json').write_text(json.dumps({'historical_file_count':len(hist),
        'hashes':hist,'mismatches':changed},indent=2)+'\n')
    if changed:
        raise RuntimeError('original production/evidence hash changed before live Gate 1')
    test_logs={'full':ROOT/'.automation/gate1-full-suite.txt','focused':ROOT/'.automation/gate1-offline.txt'}
    for label,path in test_logs.items():
        if not path.is_file(): raise RuntimeError('required offline test log missing')
        content=path.read_text()
        if 'OK' not in content or 'FAILED' in content or 'ERROR' in content:
            raise RuntimeError(f'{label} offline Gate 1 tests are not green')
        (directory/('test-results.txt' if label=='full' else 'focused-test-results.txt')).write_text(content)
    (directory/'source-audit.md').write_bytes((ROOT/'docs/arq/investigations/rca-20261113/GATE1_SOURCE_AUDIT.md').read_bytes())
    archive_integrity={}
    for name in ['20261113T121506Z-reverse-raw','20261113T123620Z-reverse-raw','20261113T123837Z-standby']:
        path=ROOT/'artifacts/arq'/name
        bundle=json.loads((path/'bundle.json' if (path/'bundle.json').exists() else path/'standby-verified.json').read_text())
        hashes=bundle.get('files') or json.loads((path/'integrity-sha256.json').read_text())
        bad=[f for f,h in hashes.items() if not (path/f).is_file() or hashlib.sha256((path/f).read_bytes()).hexdigest()!=h]
        archive_integrity[name]={'recorded_files':len(hashes),'hash_mismatches':bad}
    (directory/'original-incident-integrity.json').write_text(json.dumps(archive_integrity,indent=2)+'\n')
    if any(v['hash_mismatches'] for v in archive_integrity.values()):
        raise RuntimeError('original incident archive integrity check failed')
    if port != expected['port_path'] or os.path.realpath(port) != os.path.realpath(expected['port_path']):
        raise ValueError('port does not match configured Tracker receiver stable path')
    profile = startup_profile(ROOT/'third_party/upditerm/upditerm.py')
    if not profile['normal_monitor_startup_authorized']:
        raise RuntimeError('Monitor startup source is not the audited two-BREAK, no-reset path')
    udev = subprocess.run(['udevadm','info','--query=property','--name',port],
                          capture_output=True,text=True,timeout=3,check=False)
    properties = dict(line.split('=',1) for line in udev.stdout.splitlines() if '=' in line)
    if (udev.returncode != 0 or properties.get('ID_PATH') != 'pci-0000:00:14.0-usb-0:1:1.0'
            or properties.get('ID_VENDOR_ID') != '10c4' or properties.get('ID_MODEL_ID') != 'ea60'):
        raise ValueError('Tracker adapter identity/path did not match configured receiver port')
    audit.device_path=port
    audit.adapter_identity=properties.get('ID_SERIAL','UNKNOWN')
    owner = subprocess.run(['fuser','-v',port],capture_output=True,text=True,timeout=2,check=False)
    if owner.returncode == 0 or owner.returncode not in (1,):
        raise RuntimeError('Tracker UPDI port is owned or fuser ownership check failed')
    (directory/'preflight.json').write_text(json.dumps({'utc':utc(),'port':port,
        'real_device':os.path.realpath(port),'udev_returncode':udev.returncode,
        'udev_properties':properties,'fuser_returncode':owner.returncode,
        'fuser_stdout':owner.stdout,'fuser_stderr':owner.stderr,'target_port_owner':'none observed',
        'expected_mcu_serial_from_config':expected['device_serial_hex'],
        'current_mcu_serial':'UNKNOWN',
        'identity_method':'read-only SIB plus SIGROW device ID/serial using raw UPDI LDS; stable USB location and application build',
        'excluded_serial_read':'AVRDUDE 8.1 SerialUPDI initialize enters NVM programming and toggles RESET; not used because a reset is optional for Gate 1'},indent=2)+'\n')
    audit.event('GATE1_START', port=port, expected_identity=expected_identity,
                startup_profile=profile, acquisition_deadline_s=45, status_deadline_s=120)
    history = json.loads((ROOT/'artifacts/arq/gate1-updi/20261113T142138Z/preservation.json').read_text())
    old_hashes = history['historical_before']
    changed_before = [name for name, digest in old_hashes.items()
                      if not (ROOT/name).is_file() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest]
    if changed_before:
        raise RuntimeError('historical production/evidence preservation baseline mismatch')
    audit.event('PRESERVATION_PREFLIGHT', historical_files_checked=len(old_hashes), changed=changed_before)
    import importlib.util
    import serial
    from tools.device_detection.updi_probe import identify_mcu
    module_path = ROOT/'third_party/upditerm/upditerm.py'
    spec = importlib.util.spec_from_file_location('gate1_upditerm', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    real_serial = instrument(module, audit, serial)
    monitor, console, updi, connection = None, None, None, None
    verdict = {'verdict':'GATE1_INCONCLUSIVE','classification':'EVIDENCE_INCOMPLETE',
               'status_attempted':0,'status_successful':0,'status_failed':0,
               'response_timeouts':0,'response_mismatches':0,'monitor_exits':0,
               'identity_mismatches':0,'first_failure':None}
    identity={'mcu_part':'UNKNOWN','silicon_signature_hex':'UNKNOWN','serial_hex':'UNKNOWN',
              'expected_serial_from_config':expected['device_serial_hex']}
    try:
        audit.operation = 'UPDI_MONITOR_STARTUP'
        connection = module.UPDI(port, 38400)
        sib = connection.sib()
        audit.event('SIB_READ', raw_text=sib, full_part_in_text='UNKNOWN', operation='read-only SIB')
        signature = bytes(read_data_space_byte(connection,0x1100+i) for i in range(3))
        serial_number = bytes(read_data_space_byte(connection,0x1110+i) for i in range(16))
        identity = {'mcu_part':part_from_signature(signature), 'silicon_signature_hex':signature.hex(),
                    'serial_hex':serial_number.hex(), 'expected_serial_from_config':expected['device_serial_hex']}
        if identity['mcu_part'] != 'AVR128DA28' or serial_number.hex() != expected['device_serial_hex']:
            raise ValueError(f'IDENTITY_UNVERIFIED: signature/serial mismatch: {identity}')
        expected_identity.update(signature_hex=signature.hex(),serial_hex=serial_number.hex())
        audit.event('TARGET_IDENTITY_VERIFIED', **identity, expected_role='receiver', path=port,
                    adapter_id_path='pci-0000:00:14.0-usb-0:1:1.0')
        connection.key(module.KEY_OCD)
        connection.sts8(module.UART_FLAGS, module.FLAG_ENABLE)
        # Same SerialUPDI methods and mailbox as the Monitor constructor; no reset call.
        updi = module.SerialUPDI.__new__(module.SerialUPDI)
        updi.updi = connection
        console = MonitorConsole()
        audit.stdout_stream=(directory/'monitor.stdout.log').open('ab',buffering=0)
        monitor = module.Terminal(console, updi, escape=None, logfile=None)
        audit.event('MONITOR_STARTED', monitor_process_id=os.getpid(),
                    process_mode='in-process existing SerialUPDI + Terminal', reset_argument=False)
        if time.monotonic() > deadline:
            raise TimeoutError('45-second acquisition deadline')
        audit.event('ACQUISITION_COMPLETE', mcu_identity=identity,
                    firmware_identity='VERIFIED_BY_STATUS_TRANSACTION',
                    updi_break_count=audit.break_count, synch_count=audit.synch_count,
                    cpu_reset_operation_invoked=False, cpu_resume_count=audit.resume_count)
        if audit.break_count != 2:
            raise ValueError(f'expected normal two-BREAK startup, observed {audit.break_count}')
        status_deadline = time.monotonic() + 120
        for index in range(1, 21):
            if time.monotonic() >= status_deadline:
                raise TimeoutError('120-second STATUS deadline expired before next request')
            audit.current_transaction = index
            audit.operation = 'STATUS_COMMAND'
            started = time.monotonic_ns()
            start_utc = utc()
            audit.event('STATUS_START', transaction_index=index, command='STATUS',
                        request_tx_hex=b'STATUS\n'.hex(), start_monotonic_ns=started)
            console.send(b'STATUS\n')
            lines, parsed, raw_status = _read_block(console, audit, monitor, expected_identity,
                                        status_deadline, audit.stdout_stream)
            ended = time.monotonic_ns()
            row = {'transaction_index':index,'command':'STATUS','device_path':port,
                   'adapter_identity':'Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001',
                   'mcu_signature':identity['mcu_part'],'mcu_signature_hex':identity['silicon_signature_hex'],
                   'mcu_serial':identity['serial_hex'],
                   'firmware_identity':expected_identity['build_id'],'firmware_role':'receiver',
                   'host_process_id':os.getpid(),'monitor_process_id':os.getpid(),
                   'host_tx_hex':b'STATUS\n'.hex(),'host_tx_length':7,
                   'status_response_raw_hex':raw_status.hex(),
                   'status_payload_parsed':parsed,'status_ready':1,'status_session':0,'status_overflow':0,
                   'monotonic_start_ns':started,'monotonic_end_ns':ended,
                   'utc_start':start_utc,'utc_end':utc(),'latency_ms':(ended-started)/1_000_000,
                   'updi_break_count':audit.break_count,'synch_count_total':audit.synch_count,
                   'ocd_resume_count_total':audit.resume_count,'cpu_reset_observed':'UNKNOWN',
                   'reset_cause':'UNKNOWN','result':'PASS','transport_error':None}
            audit.write_transaction(row)
            audit.event('STATUS_PASS', transaction_index=index, latency_ms=row['latency_ms'])
            verdict['status_attempted'] += 1
            verdict['status_successful'] += 1
        verdict.update(verdict='GATE1_PASS',classification=None,
                       monitor_exit_code=None,first_failure=None)
    except Exception as exc:
        (directory/'monitor.stderr.log').write_text(traceback.format_exc())
        audit.fail(exc, audit.operation)
        text = str(exc).lower()
        if isinstance(exc, module.TransportError) and 'response mismatch' in text:
            response_length = audit.trace_last_rx_length()
            classification = ('UPDI_RESPONSE_TIMEOUT' if response_length == 0
                              else 'UPDI_RESPONSE_LENGTH_MISMATCH')
        elif isinstance(exc, module.TransportError):
            classification = 'UPDI_PROTOCOL_ERROR'
        elif 'monitor' in text and 'exit' in text:
            classification = 'MONITOR_EXIT'
        elif 'identity' in text:
            classification = 'IDENTITY_MISMATCH'
        elif isinstance(exc, TimeoutError):
            classification = 'UPDI_RESPONSE_TIMEOUT'
        else:
            classification = type(exc).__name__.upper()
        verdict.update(verdict='GATE1_FAIL' if audit.current_transaction else 'GATE1_INCONCLUSIVE',
                       classification=classification,
                       first_failure=audit.first_failure,
                       status_attempted=len(audit.rows)+int(audit.current_transaction is not None),
                       status_successful=len(audit.rows),status_failed=int(audit.current_transaction is not None))
        verdict['response_timeouts'] = int(isinstance(exc, TimeoutError))
        verdict['response_mismatches'] = int('mismatch' in str(exc).lower())
        verdict['monitor_exits'] = int(monitor is not None and monitor.failure is not None)
        verdict['identity_mismatches'] = int('identity mismatch' in str(exc).lower())
        if isinstance(exc,TimeoutError) and connection is not None:
            # Deadline cleanup closes the link; it does not reconnect or issue recovery traffic.
            try:
                connection.ser.dev.close()
                audit.event('SERIAL_CLOSED_AFTER_DEADLINE', no_recovery=True)
            except Exception as close_error:
                audit.event('SERIAL_CLOSE_ERROR', error=str(close_error))
    finally:
        audit.event('CLEANUP_START', failure_preserved=audit.first_failure is not None)
        if console is not None:
            console.input.put(None)
        if monitor is not None:
            try:
                monitor.wait()
            except Exception as exc:
                with audit.stderr.open('a') as stream:
                    stream.write(f'cleanup: {type(exc).__name__}: {exc}\n'); stream.flush(); os.fsync(stream.fileno())
                if verdict['verdict'] == 'GATE1_PASS':
                    verdict.update(verdict='GATE1_INCONCLUSIVE',classification='MONITOR_EXIT')
        if updi is not None:
            try:
                connection = updi.updi
                port_object = connection.ser.dev
                updi.__del__()
                connection.__del__()
                port_object.close()
                connection.ser = None
                connection = None
                audit.event('MONITOR_NORMAL_CLEANUP', break_count=audit.break_count,
                            synch_count=audit.synch_count, reset_count=audit.reset_count)
                updi.updi = None
            except Exception as exc:
                with audit.stderr.open('a') as stream:
                    stream.write(f'UPDI cleanup: {type(exc).__name__}: {exc}\n'); stream.flush(); os.fsync(stream.fileno())
        elif connection is not None:
            try:
                port_object=connection.ser.dev
                connection.__del__()
                port_object.close()
                connection.ser=None
                audit.event('UPDI_PRE_MONITOR_CLEANUP', break_count=audit.break_count,
                            synch_count=audit.synch_count, reset_count=audit.reset_count)
            except Exception as exc:
                with audit.stderr.open('a') as stream:
                    stream.write(f'UPDI pre-monitor cleanup: {type(exc).__name__}: {exc}\n')
                    stream.flush(); os.fsync(stream.fileno())
        if audit.stdout_stream is not None:
            audit.stdout_stream.close()
        serial_module = sys.modules.get('serial')
        if serial_module is not None:
            serial_module.Serial = real_serial

    latencies = [row['latency_ms'] for row in audit.rows]
    import statistics
    stats = {'count':len(latencies), 'minimum_ms':min(latencies) if latencies else None,
             'median_ms':statistics.median(latencies) if latencies else None,
             'maximum_ms':max(latencies) if latencies else None}
    (directory/'latency-statistics.json').write_text(json.dumps(stats,indent=2)+'\n')
    verdict.update(first_failure=audit.first_failure, status_attempted=verdict['status_attempted'],
                   status_successful=len(audit.rows), status_failed=max(0,verdict['status_attempted']-len(audit.rows)),
                   updi_break_count=audit.break_count, synch_count=audit.synch_count,
                   ocd_initialization='PASS' if audit.break_count == 2 else 'UNKNOWN',
                   cpu_reset_observed='UNKNOWN', cpu_reset_operation_count=audit.reset_count,
                   cpu_resume_count=audit.resume_count,
                   rf_transmissions=0, flash_operations=0, fuse_writes=0,
                   mcu_identity=identity, firmware_identity=expected_identity,
                   acquisition_duration_s=time.monotonic()-start,
                   status_duration_s=None if status_deadline is None else time.monotonic()-(status_deadline-120))
    (directory/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n')
    return verdict


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-gate1', action='store_true', required=True,
                        help='required explicit selector; this program has no RF/flash commands')
    parser.add_argument('--port', required=True)
    parser.add_argument('--run-dir', required=True)
    args = parser.parse_args(argv)
    try:
        result = run_gate1(args.port,args.run_dir)
    except Exception as exc:
        directory=Path(args.run_dir).resolve()
        result={'verdict':'GATE1_BLOCKED','classification':'IDENTITY_UNVERIFIED',
                'first_failure':None,'status_attempted':0,'status_successful':0,
                'status_failed':0,'exception_type':type(exc).__name__,'exception_message':str(exc),
                'rf_transmissions':0,'flash_operations':0,'fuse_writes':0}
        if directory.is_relative_to(ROOT/'artifacts/arq/gate1-updi') and directory.is_dir():
            (directory/'monitor.stderr.log').write_text(traceback.format_exc())
            (directory/'verdict.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['verdict']=='GATE1_PASS' else 2)


if __name__ == '__main__':
    main()
