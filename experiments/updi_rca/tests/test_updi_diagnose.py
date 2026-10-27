"""Host checks for the bounded diagnostic glue; no serial port is opened."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('diagnose', Path(__file__).resolve().parents[1] / 'scripts/updi-diagnose.py')
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)


class ScratchTests(unittest.TestCase):
    def test_scratch_restores_original_and_restricts_address(self):
        memory = {0x1d: 0xa5}
        writes = []

        def store(address, value):
            writes.append((address, value))
            memory[address] = value

        self.assertEqual(diag.scratch(memory.__getitem__, store), 0xa5)
        self.assertEqual(memory, {0x1d: 0xa5})
        self.assertEqual(writes, [(0x1d, 0xff), (0x1d, 0xa5)])
        with self.assertRaises(AssertionError):
            diag.scratch(memory.__getitem__, store, address=0x1051)

    def test_scratch_stops_immediately_on_failed_write(self):
        calls = []

        def load(address):
            calls.append(('read', address))
            return 0x12

        def store(address, value):
            calls.append(('write', address))
            raise RuntimeError('lost ACK')

        with self.assertRaisesRegex(RuntimeError, 'lost ACK'):
            diag.scratch(load, store)
        self.assertEqual(calls, [('read', 0x1d), ('write', 0x1d)])

    def test_observer_preserves_bytes_and_rejects_lost_echo(self):
        device = type('Device', (), {'baudrate': 38400})()
        events = []
        with patch.object(diag.serial.Serial, 'write', lambda dev, data: len(data)), \
                patch.object(diag.serial.Serial, 'read', side_effect=[b'\x55\x85', b'\x01', b'']):
            with diag.observe(events):
                diag.serial.Serial.write(device, b'\x55\x85')
                self.assertEqual(diag.serial.Serial.read(device, 2), b'\x55\x85')
                self.assertEqual(diag.serial.Serial.read(device, 1), b'\x01')
                diag.serial.Serial.write(device, b'\x55\x85')
                with self.assertRaisesRegex(RuntimeError, 'echo mismatch'):
                    diag.serial.Serial.read(device, 2)
        self.assertEqual([e['kind'] for e in events], ['tx', 'echo', 'response', 'tx', 'echo'])
        self.assertTrue(all(e['end_ns'] >= e['ns'] for e in events))

    def test_oracle_readline_timeout_is_not_a_missing_response(self):
        device = type('Device', (), {'baudrate': 38400})()
        with patch.object(diag.serial.Serial, 'read', return_value=b''):
            with diag.observe([], [True]):
                self.assertEqual(diag.serial.Serial.read(device, 1), b'')
            with diag.observe([]):
                with self.assertRaisesRegex(RuntimeError, 'missing response'):
                    diag.serial.Serial.read(device, 1)

    def test_observer_rejects_wrong_sts_ack(self):
        device = type('Device', (), {'baudrate': 38400})()
        command = b'\x55\x40\x1d'
        with patch.object(diag.serial.Serial, 'write', lambda dev, data: len(data)), \
                patch.object(diag.serial.Serial, 'read', side_effect=[command, b'\x00']):
            with diag.observe([]):
                diag.serial.Serial.write(device, command)
                diag.serial.Serial.read(device, len(command))
                with self.assertRaisesRegex(RuntimeError, 'STS ACK1'):
                    diag.serial.Serial.read(device, 1)


if __name__ == '__main__':
    unittest.main()
