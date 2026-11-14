import unittest
from contextlib import redirect_stderr
import hashlib
from io import StringIO
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from unittest.mock import patch

from tools import arq_trial


class ReaderFreeH01SummaryTests(unittest.TestCase):
    def summarize(self, events, before=None, after=None):
        summarize = getattr(arq_trial, "reader_free_h01_summary", None)
        self.assertTrue(callable(summarize), "reader-free H01 summary is missing")
        return summarize(events, before, after)

    def test_valid_h01_events_confirm_data_ack_and_delivery(self):
        data = "010101020700000000000B0048656C6C6F20576F726C64"
        ack = "010202010700000000000000"
        events = [
            {"role": "sender", "e": "TX", "bytes": data},
            {"role": "sender", "e": "TX_DONE", "rc": "0", "v": "8"},
            {"role": "receiver", "e": "RX", "bytes": data},
            {"role": "receiver", "e": "ACCEPT"},
            {"role": "receiver", "e": "TX", "bytes": ack},
            {"role": "receiver", "e": "TX_DONE", "rc": "0", "v": "8"},
            {"role": "sender", "e": "RX", "bytes": ack},
            {"role": "sender", "e": "DELIVERED"},
        ]

        result = self.summarize(events)

        self.assertTrue(result["gateway_data_tx_done"])
        self.assertTrue(result["tracker_data_rx"])
        self.assertTrue(result["tracker_data_accepted"])
        self.assertTrue(result["tracker_ack_tx_done"])
        self.assertTrue(result["gateway_ack_rx"])
        self.assertEqual(result["gateway_terminal"], "DELIVERED")

    def test_absent_radio_events_remain_unknown(self):
        result = self.summarize([{"role": "sender", "e": "TX_DONE", "rc": "0", "v": "8"}])

        self.assertTrue(result["gateway_data_tx_done"])
        self.assertIsNone(result["tracker_data_rx"])
        self.assertIsNone(result["tracker_ack_tx_done"])
        self.assertIsNone(result["gateway_ack_rx"])
        self.assertIsNone(result["gateway_terminal"])

    def test_por_transition_is_only_reported_from_before_and_after_reset_state(self):
        result = self.summarize(
            [], {"gpior0": 0x20, "rstfr": 0, "uart_flags": 1},
            {"gpior0": 0x01, "rstfr": 0, "uart_flags": 0},
        )

        self.assertFalse(result["porf_before"])
        self.assertTrue(result["porf_after"])
        self.assertTrue(result["porf_transition_to_set"])

    def test_missing_reset_state_does_not_become_a_clear_reset_result(self):
        result = self.summarize([], {"gpior0": 0x20, "rstfr": 0}, None)

        self.assertFalse(result["porf_before"])
        self.assertIsNone(result["porf_after"])
        self.assertIsNone(result["porf_transition_to_set"])

    def test_reader_free_h01_requires_rf_path_confirmation_before_running(self):
        run = patch.object(arq_trial, "reader_free_h01", create=True)
        with run as run_hardware, patch.object(sys, "argv", ["arq_trial.py", "--reader-free-h01"]):
            error = StringIO()
            with redirect_stderr(error), self.assertRaises(SystemExit):
                arq_trial.main()

        self.assertIn("RF transmission requires --rf-path-confirmed", error.getvalue())
        run_hardware.assert_not_called()

    def test_confirmed_reader_free_h01_mode_dispatches_exactly_once(self):
        with patch.object(arq_trial, "reader_free_h01", return_value="run-dir", create=True) as run, \
             patch.object(sys, "argv", ["arq_trial.py", "--reader-free-h01", "--rf-path-confirmed"]):
            arq_trial.main()

        run.assert_called_once_with()

    def test_reader_free_h01_firmware_metadata_binds_identity_to_hex_hash(self):
        describe = getattr(arq_trial, "reader_free_h01_firmware", None)
        self.assertTrue(callable(describe), "reader-free H01 firmware metadata helper is missing")
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory) / ".pio/build/receiver_arq_test"
            build.mkdir(parents=True)
            image = build / "firmware.hex"
            image.write_bytes(b":00000001FF\n")
            (build / "lora_build_identity.h").write_text(
                '#define LORA_BUILD_ID "' + 'a' * 64 + '"\n'
            )

            result = describe(Path(directory), "receiver")

        self.assertEqual(result["environment"], "receiver_arq_test")
        self.assertEqual(result["sha256"], hashlib.sha256(b":00000001FF\n").hexdigest())
        self.assertEqual(result["build_id"], "a" * 64)

    def test_reader_free_session_initializes_updi_without_sending_an_application_command(self):
        open_session = getattr(arq_trial, "open_reader_free_h01_session", None)
        self.assertTrue(callable(open_session), "reader-free UPDI session opener is missing")
        calls = []
        session = object()
        upditerm = ModuleType("upditerm")
        upditerm.SerialUPDI = lambda port, baud: calls.append((port, baud)) or session

        with patch.dict(sys.modules, {"upditerm": upditerm}):
            actual_session, actual_protocol = open_session("/dev/test-tracker")

        self.assertIs(actual_session, session)
        self.assertIs(actual_protocol, upditerm)
        self.assertEqual(calls, [("/dev/test-tracker", 38400)])


if __name__ == "__main__":
    unittest.main()
