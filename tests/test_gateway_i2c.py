"""Run the actual gateway I2C callback/task boundary on the host."""

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GatewayI2cTests(unittest.TestCase):
    def test_configuration_preserves_length_after_mailbox_consumption(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = str(Path(directory) / "gateway")
            result = subprocess.run(
                ["g++", "-std=c++17", "-Wno-return-type",
                 "-Itests/gateway_stub", "-Itests/mvp_stub", "-Itests/radio_stub",
                 "-Iinclude", "-Istable_lib/shared", "-Istable_lib/task",
                 "-Istable_lib/iw_core/src", "-Istable_lib/iw_tracker_radio_protocol/src",
                 "-Istable_lib/updi_uart/src", "-DLORA_ROLE_SENDER=1",
                 "tests/gateway_i2c_test.cpp", "stable_lib/task/task.cpp",
                 "stable_lib/iw_core/src/byte_codec.cpp", "-o", binary],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run([binary], cwd=directory, check=True)
