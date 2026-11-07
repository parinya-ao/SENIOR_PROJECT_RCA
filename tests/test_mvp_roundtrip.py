"""HOST SIMULATION: actual firmware roles; only MCU/radio I/O is replaced."""
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRACKER_LIB = ROOT.parent / 'iwing-tracker/device-lora_dev/lib'


class Board:
    def __init__(self, binary):
        self.process = subprocess.Popen(
            [str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        self.timer = threading.Timer(10, self.process.kill)
        self.timer.start()
        self.transcript = []
        try:
            self.initial = self.read()
        except BaseException:
            self.close()
            raise

    def read(self):
        lines = []
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise AssertionError('Native board stopped: ' + self.process.stderr.read())
            line = line.rstrip()
            self.transcript.append(line)
            if line == 'HOST_READY':
                return lines
            lines.append(line)

    def command(self, command):
        self.process.stdin.write(command + '\n')
        self.process.stdin.flush()
        return self.read()

    def status(self):
        return next(json.loads(line.removeprefix('HOST_STATUS '))
                    for line in self.command('STATUS') if line.startswith('HOST_STATUS '))

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=5)
        self.timer.cancel()
        self.process.stdout.close()
        self.process.stderr.close()


def frames(lines):
    return [bytes.fromhex(line.removeprefix('HOST_FRAME '))
            for line in lines if line.startswith('HOST_FRAME ')]


class MvpRoundtripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='lora-mvp-host-')
        cls.binaries = {}
        for role in ('sender', 'receiver'):
            binary = Path(cls.directory.name) / role
            command = [
                'g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                '-Wno-implicit-fallthrough', '-Wno-unused-but-set-variable', '-D_Bool=bool',
                '-DLORA_BUILD_ID="HOST_SIMULATION"',
                '-I' + str(ROOT / 'tests/mvp_stub'),
                '-I' + str(ROOT / 'tests/radio_stub'),
                '-I' + str(ROOT / 'src/shared'),
                '-I' + str(ROOT / 'src/lib/lora'),
                '-I' + str(ROOT / 'src/lib/updi_uart'),
                '-I' + str(TRACKER_LIB / 'task'),
                '-I' + str(TRACKER_LIB / 'iw_core/include'),
                '-I' + str(TRACKER_LIB / 'iw_tracker_radio_protocol/include'),
                *(['-DHELLO_TEST_MODE=1', '-DHELLO_RAM_ONLY_TEST=1']
                  if role == 'sender' else ['-DLORA_RECEIVER_BOARD=1']),
                str(ROOT / 'tests/mvp_board.cpp'),
                str(ROOT / 'src/lib/lora/lora.cpp'),
                str(ROOT / 'src/shared/hello_protocol.cpp'),
                str(Path(cls.directory.name) / 'task.o'),
                str(TRACKER_LIB / 'iw_tracker_radio_protocol/src/codec.cpp'),
                str(TRACKER_LIB / 'iw_core/src/byte_codec.cpp'),
                '-o', str(binary),
            ]
            if role == 'sender':
                # The existing Task::Restart returns a protothread value from void;
                # AVR builds allow this. Keep its host-only compatibility flag local.
                flags = command[:command.index(str(ROOT / 'tests/mvp_board.cpp'))]
                dependency = subprocess.run([
                    *[flag for flag in flags if flag != '-Werror'], '-fpermissive',
                    '-c', str(TRACKER_LIB / 'task/task.cpp'),
                    '-o', str(Path(cls.directory.name) / 'task.o'),
                ], capture_output=True, text=True, timeout=30)
                if dependency.returncode:
                    raise AssertionError(dependency.stdout + dependency.stderr)
                cls.task_host_warning = dependency.stderr
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            cls.binaries[role] = binary

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def board(self, role):
        board = Board(self.binaries[role])
        self.addCleanup(board.close)
        self.assertIn('RADIO_INIT E=0', '\n'.join(board.initial))
        self.assertIn('RADIO_MOD SF=7 BW=125 CR=5', '\n'.join(board.initial))
        self.assertIn('RADIO_PROFILE F100=92300 P=10', '\n'.join(board.initial))
        self.assertIn('RADIO_FRAME SW=12 PRE=8 CRC=1 HDR=E IQ=0',
                      '\n'.join(board.initial))
        return board

    def assert_no_eeprom(self, board):
        state = board.status()
        self.assertEqual(state['eeprom_reads'], 0)
        self.assertEqual(state['eeprom_writes'], 0)
        return state

    def start(self, sender):
        result = frames(sender.command('SA17C'))
        self.assertEqual(result, [bytes.fromhex('01007CA1080168656C6C6F20776F726C64')])
        return result[0]

    def test_real_roles_complete_one_host_data_ack_and_stop(self):
        receiver = self.board('receiver')
        sender = self.board('sender')
        self.assertIn('WAIT_SESSION', '\n'.join(receiver.initial))
        self.assertIn('WAIT_START', '\n'.join(sender.initial))
        ready = '\n'.join(receiver.command('RA17C'))
        self.assertIn('SESSION_READY C=A17C', ready)
        self.assertIn('RX_READY', ready)
        data = self.start(sender)
        result = receiver.command('RX ' + data.hex())
        self.assertIn('PAYLOAD_MATCH C=A17C S=01', '\n'.join(result))
        self.assertIn('LEN=11 HEX=68656C6C6F20776F726C64 ASCII=hello world', '\n'.join(result))
        self.assertIn('DATA_RX C=A17C S=01', '\n'.join(result))
        self.assertIn('ACK_DONE C=A17C S=01', '\n'.join(result))
        self.assertEqual(frames(result), [bytes.fromhex('00017CA10301')])
        result = sender.command('RX ' + frames(result)[0].hex())
        self.assertIn('ACK_RX C=A17C S=01', '\n'.join(result))
        self.assertIn('TEST_COMPLETED C=A17C', '\n'.join(result))
        self.assertEqual(sender.status()['state'], 'TEST_COMPLETED')
        self.assertEqual(frames(sender.command('SA17C')), [])
        self.assertEqual(frames(sender.command('SBEEF')), [])
        self.assertEqual(frames(sender.command('START')), [])
        self.assertEqual(frames(sender.command('TICK 6000')), [])
        self.assertEqual(self.assert_no_eeprom(sender)['tx'], 1)
        self.assertEqual(self.assert_no_eeprom(receiver)['tx'], 1)
        print('HOST_SIMULATION DATA_ACK=PASS DATA=1 PAYLOAD_MATCH=11/11 ACK=1 RETRIES=0 EEPROM_WRITES=0')

    def test_wrong_ack_fields_never_complete_or_retransmit(self):
        for index in range(6):
            with self.subTest(frame_byte=index):
                sender = self.board('sender')
                self.start(sender)
                ack = bytearray.fromhex('00017CA10301')
                ack[index] ^= 0x40
                result = sender.command('RX ' + ack.hex())
                self.assertNotIn('ACK_RX', '\n'.join(result))
                self.assertNotIn('TEST_COMPLETED', '\n'.join(result))
                self.assertEqual(frames(sender.command('TICK 6000')), [])
                self.assertEqual(sender.status()['state'], 'TEST_FAILED')
                self.assertEqual(self.assert_no_eeprom(sender)['tx'], 1)

    def test_invalid_start_and_duplicate_start_cannot_send_extra_data(self):
        sender = self.board('sender')
        for command in ('S0000', 'SZZZZ', 'Sa17c', 'RA17C'):
            self.assertEqual(frames(sender.command(command)), [])
        self.start(sender)
        for command in ('SA17C', 'SBEEF', 'START', 'TICK 6000'):
            self.assertEqual(frames(sender.command(command)), [])
        self.assertEqual(self.assert_no_eeprom(sender)['tx'], 1)

    def test_fresh_boot_never_resumes_previous_session(self):
        sender = self.board('sender')
        self.start(sender)
        self.assertEqual(self.assert_no_eeprom(sender)['tx'], 1)
        rebooted = self.board('sender')
        self.assertEqual(frames(rebooted.initial), [])
        self.assertEqual(frames(rebooted.command('TICK 6000')), [])
        state = self.assert_no_eeprom(rebooted)
        self.assertEqual(state['state'], 'TEST_IDLE')
        self.assertEqual(state['tx'], 0)

    def test_receiver_rejects_wrong_payload_and_wrong_session(self):
        receiver = self.board('receiver')
        receiver.command('RA17C')
        bad_payload = bytes.fromhex('01007CA1080168656C6C6F20776F726C65')
        result = receiver.command('RX ' + bad_payload.hex())
        self.assertNotIn('PAYLOAD_MATCH', '\n'.join(result))
        self.assertNotIn('[RECEIVER] ACK_TX', '\n'.join(result))
        self.assertEqual(frames(result), [bytes.fromhex('00017CA10901')])
        self.assertEqual(frames(receiver.command('RX 0100EFBE080168656C6C6F20776F726C64')), [])
        self.assert_no_eeprom(receiver)


if __name__ == '__main__':
    unittest.main(verbosity=2)
