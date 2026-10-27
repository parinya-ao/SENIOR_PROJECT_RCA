import importlib.util
import os
from pathlib import Path
import pty
import subprocess
import sys
import termios
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('upditerm', ROOT.parents[1] / 'third_party/upditerm/upditerm.py')
u = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(u)
u.TRACING = False


class FakeSerial:
    def __init__(self, *args, **kwargs):
        self.baudrate = args[1]
        self.responses = []
        self.writes = []
        self.closed = False

    def write(self, data):
        self.writes.append(data)
        return len(data)

    def read(self, length):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def close(self):
        self.closed = True


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch.object(u.serial, 'Serial', FakeSerial)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.port = u.SerialPort('/dev/fake', 38400, halfduplex=True)

    def test_echo_mismatch_reports_context_once_and_stops_writes(self):
        self.port.dev.responses = [b'\x55\x00']
        with self.assertRaises(u.TransportError) as caught:
            self.port.send(b'\x55\x85')
        text = str(caught.exception)
        for value in ['/dev/fake', '38400', 'echo', '55 85', '55 00']:
            self.assertIn(value, text)
        with self.assertRaises(u.TransportError):
            self.port.send(b'\x00')
        self.assertEqual(len(self.port.dev.writes), 1)
        self.port.close()
        self.assertTrue(self.port.dev.closed)

    def test_short_response_reports_last_transmission(self):
        self.port.dev.responses = [b'\x55\xe6', b'AVR']
        self.port.send(b'\x55\xe6')
        with self.assertRaises(u.TransportError) as caught:
            self.port.recv(32)
        for value in ['32', '41 56 52', '55 e6']:
            self.assertIn(value, str(caught.exception))

    def test_serial_exception_is_contextual(self):
        self.port.dev.responses = [u.serial.SerialException('disconnected')]
        with self.assertRaises(u.TransportError) as caught:
            self.port.send(b'\x55')
        self.assertIn('disconnected', str(caught.exception))
        self.assertTrue(self.port.failed)

    def test_constructor_failure_closes_without_cleanup_transactions(self):
        dev = FakeSerial('/dev/fake', 38400)
        dev.responses = [b'']
        with patch.object(u.serial, 'Serial', return_value=dev):
            with self.assertRaises(u.TransportError):
                u.SerialUPDI('/dev/fake', 38400)
        self.assertTrue(dev.closed)
        self.assertEqual(dev.writes, [b'\x00'])

    def test_healthy_explicit_close_disables_updi_and_closes(self):
        updi = u.UPDI.__new__(u.UPDI)
        updi.ser = self.port
        self.port.dev.responses = [b'\x55\xc3\x04']
        updi.close()
        self.assertEqual(self.port.dev.writes, [b'\x55\xc3\x04'])
        self.assertTrue(self.port.dev.closed)

    def test_missing_sts_ack_names_expected_ack_byte(self):
        updi = u.UPDI.__new__(u.UPDI)
        updi.ser = self.port
        self.port.dev.responses = [b'\x55\x40\x1e', b'']
        with self.assertRaises(u.TransportError) as caught:
            updi.sts8(u.UART_FLAGS, u.FLAG_ENABLE)
        self.assertIn('expected=[40]', str(caught.exception))

    def test_baudrate_reconfiguration_failure_has_context(self):
        def disconnect(dev, value):
            raise u.serial.SerialException('disconnected')

        with patch.object(FakeSerial, 'baudrate', property(lambda dev: 38400, disconnect), create=True):
            with self.assertRaises(u.TransportError) as caught:
                self.port.set_baudrate(300)
        for value in ['/dev/fake', 'baud=38400', 'baudrate', 'expected=300', 'received=[]']:
            self.assertIn(value, str(caught.exception))


class WorkerTests(unittest.TestCase):
    def test_reader_and_writer_failures_reach_wait_and_stop_both_workers(self):
        self.assertTrue(hasattr(u, 'TransportError'))
        for failing in ['reader', 'writer']:
            with self.subTest(failing=failing):
                class Console:
                    def get(self):
                        if failing == 'writer':
                            return ord('x')
                        self.stop.wait(1)
                        return None

                    def put(self, byte):
                        pass

                class Port:
                    calls = 0

                    def send1(self, *args, **kwargs):
                        self.calls += 1
                        raise u.TransportError('writer failed')

                    def recv1(self, **kwargs):
                        if failing == 'reader':
                            self.calls += 1
                            raise u.TransportError('reader failed')

                port = Port()
                terminal = u.Terminal(Console(), port)
                with self.assertRaises(u.TransportError):
                    terminal.wait()
                self.assertFalse(terminal.reader_thread.is_alive())
                self.assertFalse(terminal.writer_thread.is_alive())
                self.assertEqual(port.calls, 1)


class PtyTests(unittest.TestCase):
    def run_terminal(self, fail):
        master, slave = pty.openpty()
        before = termios.tcgetattr(slave)
        code = f'''
import importlib.util, sys, time
s = importlib.util.spec_from_file_location('u', {str(ROOT.parents[1] / 'third_party/upditerm/upditerm.py')!r})
u = importlib.util.module_from_spec(s); s.loader.exec_module(u)
u.TRACING = False
class Port:
    def __init__(self, *args): self.started = time.monotonic()
    def recv1(self, **kwargs):
        if {fail!r} and time.monotonic() - self.started > .3:
            raise u.TransportError('/dev/fake baud=38400 echo expected=[55] received=[]')
    def close(self, **kwargs): print('CLOSED', file=sys.stderr)
u.SerialUPDI = Port
sys.exit(u.main(u.parse_arguments()))
'''
        proc = subprocess.Popen([sys.executable, '-c', code, '/dev/fake', '38400', '-q'],
                                stdin=slave, stdout=slave, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 3
            while termios.tcgetattr(slave) == before and proc.poll() is None:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            if not fail:
                os.write(master, b'\x05e')
            _, stderr = proc.communicate(timeout=4)
            self.assertEqual(proc.returncode, 1 if fail else 0)
            self.assertEqual(termios.tcgetattr(slave), before)
            self.assertEqual(stderr.count(b'echo expected'), int(fail))
            self.assertIn(b'CLOSED', stderr)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            os.close(master)
            os.close(slave)

    def test_failure_restores_terminal_and_closes_port(self):
        self.run_terminal(True)

    def test_escape_exit_is_zero_and_restores_terminal(self):
        self.run_terminal(False)


class WindowsInputTests(unittest.TestCase):
    def test_redirected_input_uses_pipe_readiness_instead_of_select(self):
        import ctypes
        stdin = types.SimpleNamespace(isatty=lambda: False, fileno=lambda: 0, read=lambda n: 'x')

        def peek(handle, buffer, size, read, available, remaining):
            available._obj.value = 1
            return 1

        win = types.SimpleNamespace(kernel32=types.SimpleNamespace(PeekNamedPipe=peek))
        with patch.object(u.platform, 'system', return_value='Windows'), \
             patch.object(u.sys, 'stdin', stdin), \
             patch.dict(sys.modules, {'msvcrt': types.SimpleNamespace(get_osfhandle=lambda fd: 0)}), \
             patch.object(ctypes, 'windll', win, create=True), \
             patch.object(u.os, 'read', return_value=b'x'), \
             patch.object(u.select, 'select', side_effect=AssertionError('Windows pipe select')):
            self.assertEqual(u.Console().get(), ord('x'))


if __name__ == '__main__':
    unittest.main()
