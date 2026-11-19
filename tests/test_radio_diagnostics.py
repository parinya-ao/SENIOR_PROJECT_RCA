"""Compile and exercise the bounded diagnostics queue with real C++ code."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RadioDiagnosticsTests(unittest.TestCase):
    def test_queue_preserves_fifo_across_wrap_and_saturates_overflow(self) -> None:
        compiler = shutil.which("g++") or shutil.which("clang++")
        if compiler is None:
            self.fail("a host C++ compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "radio_diagnostics_test"
            command = [
                compiler,
                "-std=c++17",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Isrc",
                "-Iinclude",
                "tests/radio_diagnostics_test.cpp",
                "src/shared/diagnostics/radio_diagnostics.cpp",
                "-o",
                str(binary),
            ]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run(
                [binary], capture_output=True, text=True, check=False, timeout=10
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS bounded diagnostics FIFO", result.stdout)


if __name__ == "__main__":
    unittest.main()
