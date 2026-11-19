import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class SsotProtocolTests(unittest.TestCase):
    def compile_and_run(self, flags: Any=()) -> None:
        with tempfile.TemporaryDirectory(prefix="ssot-protocol-") as directory:
            binary = Path(directory) / "ssot_protocol_test"
            compile_result = subprocess.run(
                [
                    "g++",
                    "-std=c++17",
                    "-O2",
                    "-Wall",
                    "-Wextra",
                    "-Wshadow",
                    "-Wconversion",
                    "-Werror",
                    *flags,
                    "-I" + str(ROOT / "stable_lib/ssot"),
                    "-I" + str(ROOT / "include"),
                    str(ROOT / "tests/ssot_protocol_test.cpp"),
                    str(ROOT / "stable_lib/ssot/ssot_codec.cpp"),
                    str(ROOT / "stable_lib/ssot/ssot_session.cpp"),
                    str(ROOT / "stable_lib/ssot/ssot_control_input.cpp"),
                    "-o",
                    str(binary),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(
                compile_result.returncode, 0, compile_result.stdout + compile_result.stderr
            )
            result = subprocess.run(
                [str(binary)], capture_output=True, text=True, timeout=10, check=False
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS C++ protocol tests", result.stdout)

    def test_protocol_vectors_and_state_machine(self) -> None:
        self.compile_and_run()

    def test_ram_only_campaign_stops_after_one_attempt(self) -> None:
        self.compile_and_run(("-DHELLO_TEST_MODE=1", "-DHELLO_RAM_ONLY_TEST=1"))


if __name__ == "__main__":
    unittest.main()
