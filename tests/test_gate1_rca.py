"""Synthetic replay only: none of these tests accesses a target."""
import ast
import copy
import hashlib
import inspect
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.rca import gate1
from tools.rca.gate1_live import Gate1Audit, TracePort, part_from_signature, read_data_space_byte, startup_profile


IDENTITY = dict(signature='1e970a', serial='synthetic-tracker',
                build='synthetic-build', config='synthetic-config', role='receiver')
EVENTS = ['BOOT', 'IDENTITY', 'STATUS', 'RESULT', 'RTT_LAST', 'RTT_MIN',
          'RTT_MAX', 'RTT_COUNT', 'RX_DONE_COUNT', 'DECODE_ERRORS',
          'CONTROL_REJECTS', 'REG', 'STATUS_END']


def transaction(index):
    lines = []
    for name in EVENTS:
        extra = ' rc=0 v=0'
        if name == 'IDENTITY': extra = ' build=synthetic-build config=synthetic-config'
        if name == 'STATUS': extra = ' ready=1 overflow=0'
        lines.append(f'A t=1 e={name} s=0{extra}\n')
    return dict(transaction_index=index, monotonic_start_ns=index * 100,
                monotonic_end_ns=index * 100 + 50, identity=IDENTITY.copy(),
                request_tx_hex='5354415455530a', status_payload_raw=''.join(lines),
                transport_exchanges=[dict(expected_length=1, expected_hex='40', actual_hex='40')],
                monitor_exit_code=None, transport_error=None, timeout_reason=None)


class Gate1Tests(unittest.TestCase):
    def assess(self, rows, **kwargs):
        kwargs.setdefault('safe_path', True)
        return gate1.assess(rows, IDENTITY, **kwargs)

    def test_T01_twenty_successes(self):
        self.assertTrue(callable(getattr(gate1, 'assess', None)), 'offline Gate 1 assessor missing')
        result = self.assess([transaction(i) for i in range(1, 21)])
        self.assertEqual((result['verdict'], result['passed'], result['attempted']), ('GATE1_PASS', 20, 20))

    def test_T02_first_failure_stops_consumption(self):
        def rows():
            yield transaction(1)
            row = transaction(2); row['timeout_reason'] = 'reader deadline'; yield row
            self.fail('read beyond first failure')
        result = self.assess(rows())
        self.assertEqual((result['attempted'], result['first_failure']['transaction_index']), (2, 2))
        self.assertEqual(result['latency_ms']['median'], 0.00005)

    def test_T03_empty_bytes_are_zero_length(self):
        result = gate1.response(1, None, b'')
        self.assertEqual((result['actual_response_hex'], result['actual_response_length']), ('', 0))
        self.assertEqual(result['classification'], 'UPDI_RESPONSE_LENGTH_MISMATCH')

    def test_T04_original_exception_preserved(self):
        row = transaction(1); message = "UPDI response mismatch: expected None, received b''\n"
        row['transport_error'] = message
        result = self.assess([row])
        self.assertEqual(result['first_failure']['transport_error'], message)
        self.assertEqual(result['first_failure']['parsed_error']['response_length'], 0)

    def test_T05_incomplete_status_fails(self):
        row = transaction(1); row['status_payload_raw'] = row['status_payload_raw'].replace('e=STATUS_END', 'e=MISSING')
        self.assertEqual(self.assess([row])['classification'], 'EVIDENCE_INCOMPLETE')
        self.assertEqual(gate1.response(2, None, b'\x40')['classification'], 'UPDI_RESPONSE_LENGTH_MISMATCH')

    def test_T06_response_value_mismatch(self):
        row = transaction(1); row['transport_exchanges'][0]['actual_hex'] = '62'
        self.assertEqual(self.assess([row])['classification'], 'UPDI_RESPONSE_VALUE_MISMATCH')

    def test_T07_timeout_is_failure(self):
        row = transaction(1); row['timeout_reason'] = 'deadline'
        self.assertEqual((self.assess([row])['verdict'], self.assess([row])['timed_out']), ('GATE1_FAIL', 1))

    def test_T08_monitor_exit_is_not_usb_disconnect(self):
        row = transaction(1); row['monitor_exit_code'] = 1
        result = self.assess([row])
        self.assertEqual(result['classification'], 'MONITOR_EXIT')
        self.assertEqual(result['usb_disconnected'], 'UNKNOWN')

    def test_T09_wrong_identity_rejected(self):
        row = transaction(1); row['identity']['serial'] = 'other'
        self.assertEqual(self.assess([row])['classification'], 'IDENTITY_MISMATCH')

    def test_T10_existing_owner_blocks_without_consuming(self):
        self.assertEqual(self.assess(iter(()), owners=[123])['classification'], 'PORT_OWNERSHIP_CONFLICT')

    def test_T11_non_status_and_rf_commands_rejected(self):
        row = transaction(1); row['request_tx_hex'] = b'SEND 4869\n'.hex()
        self.assertEqual(self.assess([row])['classification'], 'UNSAFE_COMMAND_PATH')

    def test_T12_offline_tool_has_no_hardware_or_process_api(self):
        tree = ast.parse(inspect.getsource(gate1))
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertFalse(any(x in ast.unparse(n) for n in imports for x in ['serial', 'subprocess', 'pymcuprog', 'receiver_boot']))
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                             and n.func.attr in {'write_bytes', 'write_text', 'send_break', 'reset', 'program_application'}
                             for n in ast.walk(tree)))

    def test_T13_unsafe_initialization_blocks_without_read(self):
        def rows():
            self.fail('blocked path consumed a transaction'); yield
        self.assertEqual(self.assess(rows(), safe_path=False)['verdict'], 'GATE1_BLOCKED')

    def test_T14_detects_hash_corruption(self):
        with tempfile.TemporaryDirectory() as name:
            p = Path(name) / 'raw'; p.write_bytes(b'original')
            hashes = {'raw': hashlib.sha256(p.read_bytes()).hexdigest()}
            p.write_bytes(b'changed')
            self.assertEqual(gate1.verify_hashes(Path(name), hashes), ['raw'])

    def test_T15_verification_never_modifies_originals(self):
        with tempfile.TemporaryDirectory() as name:
            p = Path(name) / 'raw'; p.write_bytes(b'original')
            hashes = {'raw': hashlib.sha256(p.read_bytes()).hexdigest()}
            self.assertEqual(gate1.verify_hashes(Path(name), hashes), [])
            self.assertEqual(p.read_bytes(), b'original')
            self.assertEqual(gate1.verify_hashes(Path(name), {'missing': hashes['raw']}), ['missing'])

    def test_T16_monotonic_order_and_duplicate_index(self):
        for field, value in [('transaction_index', 1), ('monotonic_start_ns', 149)]:
            row = transaction(2); row[field] = value
            self.assertEqual(self.assess([transaction(1), row])['classification'], 'EVIDENCE_INCOMPLETE')

    def test_T17_missing_response_is_unknown(self):
        result = gate1.response(1, None, None)
        self.assertEqual(result['actual_response_length'], 'UNKNOWN')
        self.assertEqual(result['actual_response_hex'], 'UNKNOWN')
        self.assertEqual(result['classification'], 'EVIDENCE_INCOMPLETE')

    def test_T18_deterministic_json_and_no_input_mutation(self):
        import json
        rows = [transaction(1)]; before = copy.deepcopy(rows)
        first = self.assess(rows)
        self.assertEqual(first, self.assess(rows)); self.assertEqual(rows, before)
        self.assertEqual(json.loads(json.dumps(first)), first)
        self.assertNotEqual(first['verdict'], 'GATE1_PASS')

    def test_T19_normal_two_break_startup_is_authorized(self):
        profile = startup_profile(Path('third_party/upditerm/upditerm.py'))
        self.assertEqual(profile['break_calls'], 2)
        self.assertFalse(profile['startup_reset'])
        self.assertTrue(profile['normal_monitor_startup_authorized'])

    def test_T20_trace_port_preserves_raw_empty_and_nonempty_reads(self):
        class Sink:
            current_transaction = 1
            expected_length = 1
            expected_value = b'@'
            def __init__(self): self.rows = []
            def transport(self, **row): self.rows.append({'transaction_index':self.current_transaction,
                'expected_response_length':self.expected_length,**row})
        class Port:
            baudrate = 38400; parity = 'E'; stopbits = 2; timeout = 1; write_timeout = None
            def __init__(self): self.reads = [b'', b'@']; self.writes = []
            def read(self, n): return self.reads.pop(0)
            def write(self, data): self.writes.append(bytes(data)); return len(data)
        sink = Sink(); raw = Port(); traced = TracePort(raw, sink)
        self.assertEqual(traced.read(1), b'')
        self.assertEqual(traced.read(1), b'@')
        self.assertEqual((sink.rows[0]['actual_rx_hex'], sink.rows[0]['actual_rx_length']), ('', 0))
        self.assertEqual((sink.rows[1]['actual_rx_hex'], sink.rows[1]['actual_rx_length']), ('40', 1))
        self.assertTrue(all(row['expected_response_length'] == 1 for row in sink.rows))

    def test_T21_port_trace_records_exact_write_and_timestamps(self):
        class Sink:
            current_transaction = 7
            expected_length = None
            expected_value = None
            def __init__(self): self.rows = []
            def transport(self, **row): self.rows.append({'transaction_index':self.current_transaction,
                'expected_response_length':self.expected_length,**row})
        class Port:
            baudrate = 38400; parity = 'E'; stopbits = 2; timeout = 1; write_timeout = None
            def write(self, data): return len(data)
        sink = Sink(); traced = TracePort(Port(), sink)
        self.assertEqual(traced.write(b'\x55\x85'), 2)
        row = sink.rows[0]
        self.assertEqual((row['transaction_index'], row['host_tx_hex'], row['host_tx_length']), (7, '5585', 2))
        self.assertLessEqual(row['serial_write_start_ns'], row['serial_write_end_ns'])

    def test_T22_read_only_extended_LDS_uses_verified_sigrow_address(self):
        class Link:
            def __init__(self): self.frames=[]; self.lengths=[]
            def instr(self, frame): self.frames.append(frame)
            def recv(self, length): self.lengths.append(length); return b'\x1e'
        link=Link()
        self.assertEqual(read_data_space_byte(link,0x1110),0x1e)
        self.assertEqual(link.frames,[[0x04,0x10,0x11]])
        self.assertEqual(link.lengths,[1])

    def test_T23_live_cli_help_loads_without_opening_hardware(self):
        proc=subprocess.run([sys.executable,'tools/rca/gate1_live.py','--help'],
                            capture_output=True,text=True,timeout=5)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIn('--execute-gate1',proc.stdout)

    def test_T24_part_identity_comes_from_read_signature_not_SIB_label(self):
        self.assertEqual(part_from_signature(bytes.fromhex('1e970a')),'AVR128DA28')
        self.assertIsNone(part_from_signature(bytes.fromhex('1e9709')))
        self.assertIsNone(part_from_signature(None))


if __name__ == '__main__':
    unittest.main()
