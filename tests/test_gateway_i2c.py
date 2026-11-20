"""Run the actual gateway I2C callback/task boundary on the host."""

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GatewayI2cTests(unittest.TestCase):
    def test_configuration_preserves_length_after_mailbox_consumption(self) -> None:
        """Preserve the I2C message length after the mailbox consumes its bytes."""
        with tempfile.TemporaryDirectory() as directory:
            binary = str(Path(directory) / "gateway")
            result = subprocess.run(
                [
                    "g++",
                    "-std=c++17",
                    "-Wno-return-type",
                    "-ffunction-sections",
                    "-Wl,--gc-sections",
                    "-Itests/gateway_stub",
                    "-Itests/mvp_stub",
                    "-Itests/radio_stub",
                    "-Iinclude",
                    "-Itests/avr_stub",
                    "-Istable_lib/shared",
                    "-Istable_lib/task",
                    "-Istable_lib/iw_core",
                    "-Istable_lib/iw_tracker_radio_protocol",
                    "-Istable_lib/updi_uart",
                    "-Istable_lib/lora",
                    "-Isrc",
                    "-Istable_lib/ssot",
                    "-DLORA_ROLE_SENDER=1",
                    "tests/gateway_i2c_test.cpp",
                    "stable_lib/task/task.cpp",
                    "stable_lib/iw_core/byte_codec.cpp",
                    "-o",
                    binary,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run([binary], cwd=directory, check=True)
