import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from tools import rf_proof

RX = (
    "[MVP RECEIVER] RX_READY rc=0\n"
    "[MVP RECEIVER] RX count=1 len=11 rc=0 irq=80 restart=0 match=1 crc_errors=0 "
    "rssi=-83.50 snr=7.25 PASS bytes=48656C6C6F20576F726C64\n"
)
TX = (
    "[MVP SENDER] TX_START attempt=1 len=11 rc=0 cleanup=0\n"
    "[MVP SENDER] TX_DONE attempt=1 cleanup=0 irq=8\n"
)


class RawEvidenceTests(unittest.TestCase):
    def test_raw_log_cli_does_not_require_a_hardware_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sender, receiver = (Path(directory) / name for name in ("sender.log", "receiver.log"))
            sender.write_text(TX)
            receiver.write_text(RX)
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(rf_proof.__file__)),
                    "--raw-mvp-logs",
                    str(sender),
                    str(receiver),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"passed": true', result.stdout)

    def test_separate_raw_format_and_validated_fields(self) -> None:
        self.assertTrue(hasattr(rf_proof, "parse_raw_mvp_logs"), "raw evidence parser missing")
        result = rf_proof.parse_raw_mvp_logs(TX, RX)
        self.assertTrue(result["passed"])
        self.assertEqual(result["rx_matches"], 1)
        self.assertEqual(result["rssi"], [-83.5])
        for old, new in (
            ("len=11", "len=10"),
            ("rc=0", "rc=-7"),
            ("irq=80", "irq=112"),
            ("restart=0", "restart=-1"),
            ("48656C", "68656C"),
            ("PASS", "REJECT"),
            ("RX_READY rc=0", "RX_READY rc=-1"),
        ):
            self.assertFalse(rf_proof.parse_raw_mvp_logs(TX, RX.replace(old, new))["passed"])
        self.assertFalse(
            rf_proof.parse_raw_mvp_logs(TX.replace("TX_DONE", "TX_TIMEOUT"), RX)["passed"]
        )
        self.assertFalse(
            rf_proof.parse_raw_mvp_logs("[GATEWAY] DATA_DONE", "[RECEIVER] PAYLOAD_MATCH")["passed"]
        )


if __name__ == "__main__":
    unittest.main()
