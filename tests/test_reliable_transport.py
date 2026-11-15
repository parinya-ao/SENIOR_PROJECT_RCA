"""Execute the real transport/HAL with bounded in-memory radio fault injection."""

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReliableTransportTests(unittest.TestCase):
    def compile_run(self, source, *extra) -> None:
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "test"
            ssot = Path(directory) / "ssot.o"
            subprocess.run(
                ["clang", "-std=c11", "-Isrc", "-Iinclude", "-c", "src/ssot.c", "-o", str(ssot)],
                cwd=ROOT,
                check=True,
            )
            command = [
                "clang",
                "--driver-mode=g++",
                "-nostdlib++",
                "-std=c++17",
                "-fno-exceptions",
                "-fno-rtti",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-fsanitize=address,undefined",
                "-fno-omit-frame-pointer",
                "-fno-sanitize-link-c++-runtime",
                "-D_Bool=bool",
                "-DLORA_ROLE_SENDER=1",
                "-Itests/mvp_stub",
                "-Itests/radio_stub",
                "-Isrc/shared",
                "-Isrc",
                "-Iinclude",
                "-Ilib/lora/src",
                "-Ilib/updi_uart/src",
                source,
                *extra,
                str(ssot),
                "-o",
                str(binary),
            ]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([binary], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            print(result.stdout.strip())

    def test_hal_contract(self) -> None:
        self.compile_run("tests/lora_contract_test.cpp", "lib/lora/src/lora.cpp")

    def test_existing_hal_vectors(self) -> None:
        self.compile_run("tests/lora_wrapper_test.cpp", "lib/lora/src/lora.cpp")

    def test_five_dbm_candidate_reaches_radio_without_other_phy_changes(self) -> None:
        self.compile_run(
            "tests/lora_wrapper_test.cpp",
            "lib/lora/src/lora.cpp",
            "-DLORA_TEST_TX_POWER_DBM=5",
            "-DEXPECTED_TX_POWER_DBM=5",
            '-DLORA_TEST_CONFIG_FINGERPRINT="candidate"',
        )

    def test_transport(self) -> None:
        self.assertTrue(
            (ROOT / "src/shared/reliable_transport.h").exists(),
            "shared SSOT reliable transport is missing",
        )
        self.compile_run("tests/reliable_transport_test.cpp")

    def test_application(self) -> None:
        self.assertTrue(
            (ROOT / "src/reliable/main.cpp").exists(), "shared bidirectional application is missing"
        )
        self.compile_run(
            "tests/reliable_app_test.cpp", "lib/lora/src/lora.cpp", '-DLORA_BUILD_ID="HOST_TEST"'
        )
        self.compile_run(
            "tests/reliable_app_test.cpp",
            "lib/lora/src/lora.cpp",
            '-DLORA_BUILD_ID="HOST_TEST"',
            "-ULORA_ROLE_SENDER",
            "-DLORA_ROLE_RECEIVER=1",
        )

    def test_radio_progress_when_ocd_mailbox_is_full(self) -> None:
        self.compile_run(
            "tests/reliable_app_test.cpp",
            "lib/lora/src/lora.cpp",
            '-DLORA_BUILD_ID="HOST_TEST"',
            "-DLORA_NONBLOCKING_LOG=1",
            "-DTEST_LOG_BACKPRESSURE=1",
        )

    def test_radio_progress_with_debug_output_disabled(self) -> None:
        self.compile_run(
            "tests/reliable_app_test.cpp",
            "lib/lora/src/lora.cpp",
            '-DLORA_BUILD_ID="HOST_TEST"',
            "-DLORA_NONBLOCKING_LOG=1",
            "-DLORA_DEBUG_OUTPUT=0",
            "-DTEST_LOG_DISABLED=1",
        )

    def test_diagnostic_disables_transmit(self) -> None:
        self.compile_run(
            "tests/reliable_app_test.cpp",
            "lib/lora/src/lora.cpp",
            '-DLORA_BUILD_ID="HOST_TEST"',
            "-DHELLO_RF_DIAGNOSTIC_ONLY=1",
        )


if __name__ == "__main__":
    unittest.main()
