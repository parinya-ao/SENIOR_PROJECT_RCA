import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock


SPEC = importlib.util.spec_from_file_location(
    "upditerm_transport", Path(__file__).resolve().parents[1]
    / "third_party/upditerm/upditerm.py")
upditerm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(upditerm)


class ReceiveTests(unittest.TestCase):
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
