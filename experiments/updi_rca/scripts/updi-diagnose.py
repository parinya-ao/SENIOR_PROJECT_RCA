"""Bounded evidence harness using existing UPDI implementations (no flashing)."""
import argparse
from contextlib import contextmanager
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

import serial
from updi_rca.paths import EXPERIMENT_ROOT, REPOSITORY_ROOT as ROOT, VENDOR_ROOT

LIBS = EXPERIMENT_ROOT / 'vendor/pymcuprog'
sys.path.insert(0, str(LIBS))
spec = importlib.util.spec_from_file_location('upditerm', VENDOR_ROOT / 'upditerm/upditerm.py')
up = importlib.util.module_from_spec(spec)
spec.loader.exec_module(up)
from pymcuprog.serialupdi.physical import UpdiPhysical
from pymcuprog.serialupdi.link import UpdiDatalink16bit, UpdiDatalink24bit


@contextmanager
def observe(events, line_timeout=None):
    """Observe actual pyserial bytes, including echoes normally discarded by oracle."""
    read, write = serial.Serial.read, serial.Serial.write
    pending = None
    ack_stage = 0

    def tx(dev, data):
        nonlocal pending, ack_stage
        raw = bytes(data)
        start = time.monotonic_ns()
        count = write(dev, data)
        events.append(dict(kind='tx', ns=start, end_ns=time.monotonic_ns(),
                           hex=raw.hex(), count=count, baud=dev.baudrate))
        pending = raw
        if len(raw) >= 3 and raw[0] == 0x55 and raw[1] & 0xe0 == 0x40:
            ack_stage = 1
        if count != len(raw):
            raise RuntimeError('short serial write')
        return count

    def rx(dev, size=1):
        nonlocal pending, ack_stage
        start = time.monotonic_ns()
        raw = read(dev, size)
        echo = pending
        pending = None
        events.append(dict(kind='echo' if echo is not None else 'response',
                           ns=start, end_ns=time.monotonic_ns(), hex=raw.hex(),
                           requested=size, baud=dev.baudrate))
        if echo is not None and raw != echo:
            raise RuntimeError(f'echo mismatch: expected {echo.hex()} received {raw.hex()}')
        if len(raw) != size and not (line_timeout and line_timeout[0]):
            raise RuntimeError(f'missing response: expected {size} bytes received {raw.hex()}')
        if echo is None and ack_stage:
            if raw != b'\x40':
                raise RuntimeError(f'STS ACK{ack_stage}: expected 40 received {raw.hex()}')
            ack_stage = 2 if ack_stage == 1 else 0
        return raw

    with patch.object(serial.Serial, 'read', rx), patch.object(serial.Serial, 'write', tx):
        yield


def scratch(ld, st, address=0x1d):
    """Only GPR1, proven unused by the guarded image; never recover a failed link."""
    assert address == 0x1d
    original = ld(address)
    st(address, original ^ 0x5a)
    assert ld(address) == original ^ 0x5a, 'scratch readback mismatch'
    st(address, original)
    assert ld(address) == original, 'scratch restoration mismatch'
    return original


def run(args):
    events, values = [], []
    line_timeout = [False]
    result = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        baud=args.baud, backend=args.backend, mode=args.mode, address=args.address,
        hypothesis=args.hypothesis, falsifier=args.falsifier,
        preconditions='unchanged H image; no power cycle; prior teardown in preceding record',
        changed_variable=args.variable, target_state='unknown until snapshots', oracle_root=str(LIBS),
        reset_key_operations=[], first_anomaly=None, exit=0, events=events, values=values)
    conn = phy = None
    stage = 'initialization'

    def sample(name, action):
        nonlocal stage
        stage = name
        value = action()
        values.append(dict(name=name, ns=time.monotonic_ns(), value=value))
        return value

    try:
        with observe(events, line_timeout):
            if args.backend == 'upstream':
                conn = up.UPDI(args.port, args.baud)
                ld, st, cs, cst = conn.lds8, conn.sts8, conn.ldcs, conn.stcs
                result['initialization'] = 'UPDI(): two 300-baud BREAKs, CTRLB=8; no reset/key'
            else:
                phy = UpdiPhysical(args.port, args.baud)
                if args.double_break:
                    stage = 'explicit official double BREAK before datalink initialization'
                    phy.send_double_break()
                conn = (UpdiDatalink24bit() if args.backend == 'oracle24' else UpdiDatalink16bit())
                conn.set_physical(phy)
                stage = 'oracle init_datalink'
                conn.init_datalink()
                ld, st, cs, cst = conn.ld, conn.st, conn.ldcs, conn.stcs
                result['initialization'] = 'Microchip e2fa9a7 UpdiPhysical + init_datalink; default DTR/RTS; initial zero; CTRLB=8 CTRLA=80(hex)'
                result['explicit_double_break'] = args.double_break
            if args.ctrla is not None:
                sample('diagnostic CTRLA setting', lambda: cst(2, args.ctrla))
                result['diagnostic_ctrla'] = args.ctrla
            if args.mode in ('sib', 'read', 'scratch'):
                result['target_state'] = {f'CS{a:02x}': sample(f'precondition LDCS {a:02x}', lambda a=a: cs(a))
                                          for a in (2, 3, 5, 7, 11)}
            if args.mode == 'sib':
                # Oracle sib() uses readline: a no-newline SIB ends normally at timeout.
                line_timeout[0] = args.backend != 'upstream'
                if args.backend == 'upstream':
                    sample('SIB', conn.sib)
                else:
                    raw = sample('oracle SIB hex', lambda: phy.sib().hex())
                    assert len(bytes.fromhex(raw)) == 32, 'incomplete oracle SIB'
                    sample('SIB', lambda: bytes.fromhex(raw).decode('ascii'))
                line_timeout[0] = False
            elif args.mode == 'control':
                for address in (0, 1, 2, 3, 7, 8, 9, 10, 11, 11, 12, 4, 5):
                    sample(f'LDCS {address:02x}', lambda a=address: cs(a))
            elif args.mode == 'read':
                sample(f'LDS {args.address:04x}', lambda: ld(args.address))
            elif args.mode == 'scratch':
                sample('GPR1 before scratch', lambda: ld(0x1d))
                sample('scratch GPR1 restored', lambda: scratch(ld, st))
            elif args.mode == 'release':
                sample('UART_FLAGS disable', lambda: st(0x1e, 0))
                sample('UPDIDIS clear debug keys', lambda: cst(3, 4))
                result['reset_key_operations'].append('UPDIDIS releases keys and UPDI; no reset request or RUN')
            elif args.mode == 'detach':
                assert args.backend == 'upstream'
                sample('normal UPDI close sends UPDIDIS', conn.close)
            elif args.mode == 'key-snapshot':
                assert args.backend == 'upstream'
                for address in (7, 4, 5, 11):
                    sample(f'before key LDCS {address:02x}', lambda a=address: cs(a))
                result['reset_key_operations'].append('KEY_OCD; no reset request, no RUN')
                sample('KEY_OCD', lambda: conn.key(up.KEY_OCD))
                for address in (7, 4, 5, 11):
                    sample(f'after key LDCS {address:02x}', lambda a=address: cs(a))
                for address in (0x40, 0x1c, 0x1d, 0x1e, 0x63):
                    sample(f'after key LDS {address:04x}', lambda a=address: ld(a))
            else:
                # Preserve historical reset evidence before any clear or diagnostic reset.
                for address in (0x40, 0x1c, 0x1d, 0x1e, 0x1f, 0x63):
                    sample(f'initial LDS {address:04x}', lambda a=address: ld(a))
                for address in (11, 11, 7, 4, 5):
                    sample(f'initial LDCS {address:02x}', lambda a=address: cs(a))
                if args.mode == 'startup':
                    assert args.backend == 'upstream'
                    result['reset_key_operations'].append('KEY_OCD (no reset request)')
                    sample('KEY_OCD', lambda: conn.key(up.KEY_OCD))
                    sample('after key OCD_STATUS', lambda: cs(5))
                    sample('after key RSTFR', lambda: ld(0x40))
                    sample('UART_FLAGS enable', lambda: st(0x1e, 1))
                    sample('after enable OCD_STATUS', lambda: cs(5))
                    if cs(5) & 1:
                        result['reset_key_operations'].append('OCD_RUN exactly once')
                        sample('OCD_RUN once', lambda: cst(4, 2))
                    start = time.monotonic()
                    while time.monotonic() - start < 1:
                        stopped = sample('after RUN OCD_STATUS', lambda: cs(5))
                        if stopped & 1:
                            result['recurring_stop'] = True
                            sample('restopped RSTFR', lambda: ld(0x40))
                            sample('restopped GPR0', lambda: ld(0x1c))
                            break
                        time.sleep(0.01)
                elif args.mode in ('bor-clear', 'bor-marker'):
                    assert cs(5) & 1, 'requires already stopped CPU'
                    if args.mode == 'bor-marker':
                        original = sample('GPR1 original before marker', lambda: ld(0x1d))
                        sample('GPR1 marker write', lambda: st(0x1d, original ^ 0x5a))
                        assert sample('GPR1 marker readback', lambda: ld(0x1d)) == original ^ 0x5a
                    result['reset_key_operations'].append('BORF-only W1C; no RUN, KEY or reset request')
                    sample('clear BORF only', lambda: st(0x40, 2))
                    for i in range(20):
                        sample('stopped RSTFR after clear', lambda: ld(0x40))
                        sample('stopped OCD_STATUS after clear', lambda: cs(5))
                        if args.mode == 'bor-marker':
                            sample('stopped GPR1 marker after clear', lambda: ld(0x1d))
                        time.sleep(0.01)
                    if args.mode == 'bor-marker':
                        sample('GPR1 marker restore', lambda: st(0x1d, original))
                        assert sample('GPR1 marker restored readback', lambda: ld(0x1d)) == original
                elif args.mode == 'reset':
                    result['reset_key_operations'].append('diagnostic ASI_RESET_REQ=59 then 00')
                    sample('apply reset', lambda: cst(8, 0x59))
                    sample('release reset', lambda: cst(8, 0))
                    for address in (11, 11, 5):
                        sample(f'after reset LDCS {address:02x}', lambda a=address: cs(a))
                    sample('after reset RSTFR', lambda: ld(0x40))
                elif args.mode == 'progmode':
                    assert args.backend != 'upstream'
                    from logging import getLogger
                    from pymcuprog.serialupdi.application import UpdiApplication
                    from pymcuprog.serialupdi.readwrite import UpdiReadWrite
                    app = UpdiApplication.__new__(UpdiApplication)
                    app.logger = getLogger('diagnostic.progmode')
                    app.phy = phy
                    app.readwrite = UpdiReadWrite(conn)
                    result['reset_key_operations'].append('official enter_progmode; NVM key and diagnostic reset only; no erase/program call')
                    sample('enter programming mode', app.enter_progmode)
                    sample('programming ASI_SYS_STATUS', lambda: cs(11))
                    for address in (0x40, 0x1c, 0xf01, 0x1051, 0x4000):
                        sample(f'programming LDS {address:04x}', lambda a=address: ld(a))
                    sample('leave programming mode', app.leave_progmode)
                    result['reset_key_operations'].append('official leave_progmode resets then UPDIDIS')
    except (Exception, SystemExit) as exc:
        result.update(exit=1, first_anomaly=f'{stage}: {type(exc).__name__}: {exc}')
    finally:
        # No more protocol traffic after a failed transaction. Close the OS handle.
        if args.backend == 'upstream' and conn:
            conn.close(abort=True)
        elif phy and phy.ser:
            phy.ser.close()
        result['teardown'] = 'finally: OS handle closed with no extra recovery/protocol traffic; explicit operation teardown is recorded in values and raw TX'
        result['firmware_sha256'] = hashlib.sha256((ROOT / '.pio/build/receiver/firmware.hex').read_bytes()).hexdigest()
        result['interpretation'] = 'See report; do not interpret bytes after first anomaly'
        result['confidence_update'] = 'Engineering judgments updated by experiment group in report section 5; repeated trials do not constitute independent causal evidence'
        result['next_discriminator'] = ('Compare RUN once versus stopped snapshots' if args.mode in ('read', 'scratch', 'control')
                                        else 'Compare independent implementation with observed state held equivalent')
        result['self_review'] = 'No fuse/erase/programming calls; one variable identified; failure ends session; no repeated RUN'
        output = Path(args.output)
        if not output.is_absolute():
            output = ROOT / output
        with output.open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
    print(json.dumps({k: result[k] for k in ('mode', 'backend', 'baud', 'address', 'exit', 'first_anomaly')}))
    return result['exit']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['sib', 'control', 'read', 'scratch', 'snapshot', 'startup', 'key-snapshot', 'bor-clear', 'bor-marker', 'reset', 'progmode', 'release', 'detach'])
    parser.add_argument('output')
    parser.add_argument('--backend', choices=['upstream', 'oracle16', 'oracle24'], default='upstream')
    parser.add_argument('--port', default='/dev/ttyUSB0')
    parser.add_argument('--baud', type=int, default=38400)
    parser.add_argument('--address', type=lambda s: int(s, 0), default=0x1c)
    parser.add_argument('--double-break', action='store_true', help='Use the oracle physical layer existing double-BREAK before initialization')
    parser.add_argument('--ctrla', type=lambda s: int(s, 0), choices=[0, 128], help='Isolate documented default versus oracle IBDLY; no timeout or ACK disable bits')
    parser.add_argument('--hypothesis', required=True)
    parser.add_argument('--falsifier', required=True)
    parser.add_argument('--variable', required=True)
    args = parser.parse_args()
    if Path(args.output).exists():
        parser.error('evidence path already exists')
    if args.backend == 'upstream' and args.mode == 'read' and not 0 <= args.address <= 255:
        parser.error('upditerm LDS uses 8-bit addresses; use oracle for higher addresses')
    raise SystemExit(run(args))
