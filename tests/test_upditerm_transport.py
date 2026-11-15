import importlib.util
import queue
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock

SPEC = importlib.util.spec_from_file_location(
    "upditerm_transport", Path(__file__).resolve().parents[1] / "third_party/upditerm/upditerm.py"
)
upditerm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(upditerm)


class ReceiveTests(unittest.TestCase):
    def test_empty_read_reports_last_request_without_reusing_failed_connection(self):
        port = self.port(b"")
        port.halfduplex = False
        port.send(b"\x55\x85")
        with self.assertRaisesRegex(upditerm.TransportError, "last_tx=55 85"):
            port.recv(1)
        with self.assertRaises(upditerm.TransportError):
            port.send(b"\x55\x85")
        self.assertEqual(port.dev.write.call_count, 1)

    def test_empty_response_records_requested_length_and_read_timeout(self):
        port = self.port(b"")
        port.halfduplex = False
        port.dev.timeout = 0.25
        port.send(b"\x55\x85")
        with self.assertRaises(upditerm.TransportError) as caught:
            port.recv(1)
        self.assertRegex(
            str(caught.exception),
            r"requested_len=1, actual_len=0, read_timeout=0\.25, "
            r"read_duration_ns=\d+; last_tx=55 85",
        )

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

    def test_halfduplex_echo_mismatch_preserves_request_and_actual_bytes(self):
        port = self.port(b"\x00")
        port.halfduplex = True
        port.dev.timeout = 0.25
        with self.assertRaises(upditerm.TransportError) as caught:
            port.send(b"\x55\x85")
        self.assertEqual(
            str(caught.exception),
            "UPDI echo mismatch: expected b'U\\x85', received b'\\x00'; "
            "expected_len=2, actual_len=1, read_timeout=0.25",
        )
        self.assertTrue(port.failed)

    def test_bad_store_ack_prevents_value_write_and_connection_reuse(self):
        port = self.port(b"\x00")
        port.halfduplex = False
        connection = upditerm.UPDI.__new__(upditerm.UPDI)
        connection.ser = port
        with self.assertRaises(upditerm.TransportError):
            connection.sts8(0x1E, 1)
        self.assertEqual(port.dev.write.call_count, 1)
        with self.assertRaises(upditerm.TransportError):
            port.send(b"\x01")
        self.assertEqual(port.dev.write.call_count, 1)

    def test_sts8_uses_sixteen_bit_address_for_avr_da_data_space(self):
        class Link:
            def __init__(self):
                self.sent = []
                self.responses = [b"\x40", b"\x40"]
                self.expected = []

            def send(self, data):
                self.sent.append(bytes(data))

            def recv(self, length, expected=None):
                self.expected.append(expected)
                data = self.responses.pop(0)
                if expected is not None and data != expected:
                    raise AssertionError((data, expected))
                return data

        link = Link()
        connection = upditerm.UPDI.__new__(upditerm.UPDI)
        connection.ser = link
        connection.sts8(0x1E, 1)
        self.assertEqual(link.sent, [b"\x55\x44\x1e\x00", b"\x01"])
        self.assertEqual(link.expected, [b"\x40", b"\x40"])

    def test_reader_transport_failure_exits_while_console_input_is_blocked(self):
        release = threading.Event()
        done = threading.Event()
        errors = []
        console = Mock()
        console.get.side_effect = lambda: release.wait(2) and None
        serial = Mock()
        serial.recv1.side_effect = upditerm.TransportError("bad ACK")
        terminal = upditerm.Terminal(console, serial)

        def wait():
            try:
                terminal.wait()
            except upditerm.TransportError as error:
                errors.append(str(error))
            finally:
                done.set()

        thread = threading.Thread(target=wait, daemon=True)
        thread.start()
        try:
            self.assertTrue(done.wait(1), "monitor did not exit after transport failure")
            self.assertEqual(errors, ["bad ACK"])
        finally:
            release.set()
            thread.join(2)

    def test_reader_unexpected_exception_releases_idle_lock_for_cleanup(self):
        class Console:
            def __init__(self):
                self.input = queue.Queue()

            def get(self):
                return self.input.get()

            def put(self, value):
                self.input.put(value)

        console = Console()
        serial = Mock()
        serial.recv1.side_effect = TypeError("serial closed during cleanup")
        terminal = upditerm.Terminal(console, serial)
        errors = []
        done = threading.Event()

        def wait():
            try:
                terminal.wait()
            except Exception as error:
                errors.append(str(error))
            finally:
                done.set()

        waiter = threading.Thread(target=wait, daemon=True)
        waiter.start()
        try:
            self.assertTrue(done.wait(1), "monitor cleanup did not surface the reader error")
            self.assertEqual(errors, ["serial closed during cleanup"])
        finally:
            console.put(None)
            waiter.join(1)
            terminal.writer_thread.join(1)
        self.assertFalse(terminal.writer_thread.is_alive())
