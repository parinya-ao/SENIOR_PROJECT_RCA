"""Execute the real transport/HAL with bounded in-memory radio fault injection."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class ReliableTransportTests(unittest.TestCase):
    def compile_run(self, source: Any, *extra: Any) -> None:
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "test"
            ssot = Path(directory) / "ssot.o"
            subprocess.run(
                [
                    "clang",
                    "--driver-mode=g++",
                    "-std=c++17",
                    "-Istable_lib/ssot",
                    "-Iinclude",
                    "-c",
                    "stable_lib/ssot/ssot_codec.cpp",
                    "-o",
                    str(ssot),
                ],
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
                "-Itests/avr_stub",
                "-Itests/radio_stub",
                "-Istable_lib/shared",
                "-Isrc",
                "-Istable_lib/ssot",
                "-Iinclude",
                "-Istable_lib/lora",
                "-Istable_lib/updi_uart",
                source,
                *extra,
                str(ssot),
                "stable_lib/ssot/ssot_session.cpp",
                "stable_lib/ssot/ssot_control_input.cpp",
                "-o",
                str(binary),
            ]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run(
                [binary], capture_output=True, text=True, timeout=10, check=False
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            print(result.stdout.strip())

    def test_hal_contract(self) -> None:
        self.compile_run("tests/lora_contract_test.cpp", "src/shared/radio/radio_link.cpp")

    def test_existing_hal_vectors(self) -> None:
        self.compile_run("tests/lora_wrapper_test.cpp", "src/shared/radio/radio_link.cpp")

    def test_five_dbm_candidate_reaches_radio_without_other_phy_changes(self) -> None:
        self.compile_run(
            "tests/lora_wrapper_test.cpp",
            "src/shared/radio/radio_link.cpp",
            "-DLORA_TEST_TX_POWER_DBM=5",
            "-DEXPECTED_TX_POWER_DBM=5",
            '-DLORA_TEST_CONFIG_FINGERPRINT="candidate"',
        )

    def test_transport(self) -> None:
        self.assertTrue(
            (ROOT / "src/shared/protocol/reliable_transport.h").exists(),
            "reliable transfer feature is missing",
        )
        self.compile_run("tests/reliable_transport_test.cpp")

    def test_application(self) -> None:
        for role in ("sender", "receiver"):
            self.assertTrue((ROOT / f"src/{role}/appcode/reliable.cpp").is_file())
        self.compile_run(
            "tests/reliable_app_test.cpp",
            "src/shared/diagnostics/radio_diagnostics.cpp",
            "src/shared/radio/radio_link.cpp",
            "-DLORA_APP_RELIABLE=1",
            '-DLORA_BUILD_ID="HOST_TEST"',
        )
        self.compile_run(
            "tests/reliable_app_test.cpp",
            "src/shared/diagnostics/radio_diagnostics.cpp",
            "src/shared/radio/radio_link.cpp",
            "-DLORA_APP_RELIABLE=1",
            '-DLORA_BUILD_ID="HOST_TEST"',
            "-ULORA_ROLE_SENDER",
            "-DLORA_ROLE_RECEIVER=1",
        )
        self.compile_run(
            "tests/reliable_app_test.cpp",
            "src/shared/diagnostics/radio_diagnostics.cpp",
            "src/shared/radio/radio_link.cpp",
            "-DLORA_APP_RELIABLE=1",
            "-DHELLO_TEST_MODE=1",
            "-DTEST_WRONG_DESTINATION=1",
            '-DLORA_BUILD_ID="HOST_TEST"',
        )

    def test_radio_progress_when_ocd_mailbox_is_full(self) -> None:
        self.compile_run(
            "tests/reliable_app_test.cpp",
            "src/shared/diagnostics/radio_diagnostics.cpp",
            "src/shared/radio/radio_link.cpp",
            "-DLORA_APP_RELIABLE=1",
            '-DLORA_BUILD_ID="HOST_TEST"',
            "-DLORA_NONBLOCKING_LOG=1",
            "-DTEST_LOG_BACKPRESSURE=1",
        )

    def test_radio_progress_with_debug_output_disabled(self) -> None:
        self.compile_run(
            "tests/reliable_app_test.cpp",
            "src/shared/diagnostics/radio_diagnostics.cpp",
            "src/shared/radio/radio_link.cpp",
            "-DLORA_APP_RELIABLE=1",
            '-DLORA_BUILD_ID="HOST_TEST"',
            "-DLORA_NONBLOCKING_LOG=1",
            "-DLORA_DEBUG_OUTPUT=0",
            "-DTEST_LOG_DISABLED=1",
        )

    def test_diagnostic_disables_transmit(self) -> None:
        self.compile_run(
            "tests/reliable_app_test.cpp",
            "src/shared/diagnostics/radio_diagnostics.cpp",
            "src/shared/radio/radio_link.cpp",
            "-DLORA_APP_RELIABLE=1",
            '-DLORA_BUILD_ID="HOST_TEST"',
            "-DHELLO_RF_DIAGNOSTIC_ONLY=1",
        )


if __name__ == "__main__":
    unittest.main()
