import importlib.util
from pathlib import Path
import unittest
import threading
from unittest.mock import Mock


SPEC = importlib.util.spec_from_file_location(
    "upditerm_transport", Path(__file__).resolve().parents[1]
    / "third_party/upditerm/upditerm.py")
upditerm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(upditerm)


class ReceiveTests(unittest.TestCase):
    def test_empty_read_reports_last_request_without_reusing_failed_connection(self):
        port=self.port(b'');port.halfduplex=False
        port.send(b'\x55\x85')
        with self.assertRaisesRegex(upditerm.TransportError,'last_tx=55 85'):
            port.recv(1)
        with self.assertRaises(upditerm.TransportError):port.send(b'\x55\x85')
        self.assertEqual(port.dev.write.call_count,1)

    def port(self, response):
        port = upditerm.SerialPort.__new__(upditerm.SerialPort)
        port.failed = False
        port.port = "mock"
        port.baudrate = 38400
        port.operation = "STS"
        port.last_tx = b"\x55\x40\x1e"
        port.dev = Mock()
        port.dev.read.return_value = response
        return port

    def test_ack_is_compared_and_failed_connection_is_not_reused(self):
        for response in (b"\x00", b"\xff", b""):
            with self.subTest(response=response):
                port = self.port(response)
                with self.assertRaises(upditerm.TransportError):
                    port.recv(1, b"\x40")
                with self.assertRaises(upditerm.TransportError):
                    port.recv(1, b"\x40")
                port.dev.read.assert_called_once_with(1)

    def test_ack_and_unrestricted_payload_are_accepted(self):
        self.assertEqual(self.port(b"\x40").recv(1, b"\x40"), b"\x40")
        self.assertEqual(self.port(b"\x00").recv(1), b"\x00")

    def test_bad_store_ack_prevents_value_write_and_connection_reuse(self):
        port=self.port(b'\x00');port.halfduplex=False
        connection=upditerm.UPDI.__new__(upditerm.UPDI);connection.ser=port
        with self.assertRaises(upditerm.TransportError):connection.sts8(0x1e,1)
        self.assertEqual(port.dev.write.call_count,1)
        with self.assertRaises(upditerm.TransportError):port.send(b'\x01')
        self.assertEqual(port.dev.write.call_count,1)

    def test_reader_transport_failure_exits_while_console_input_is_blocked(self):
        release=threading.Event();done=threading.Event();errors=[]
        console=Mock();console.get.side_effect=lambda:release.wait(2) and None
        serial=Mock();serial.recv1.side_effect=upditerm.TransportError('bad ACK')
        terminal=upditerm.Terminal(console,serial)
        def wait():
            try:terminal.wait()
            except upditerm.TransportError as error:errors.append(str(error))
            finally:done.set()
        thread=threading.Thread(target=wait,daemon=True);thread.start()
        try:
            self.assertTrue(done.wait(1), 'monitor did not exit after transport failure')
            self.assertEqual(errors,['bad ACK'])
        finally:
            release.set();thread.join(2)
