"""Compile the portable module contracts independently of Arduino."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CppInterfaceTests(unittest.TestCase):
    def test_sd_line_reader_truncates_overlong_lines_without_losing_sync(self) -> None:
        """Recover after an overlong SD line without losing the next command."""
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            binary = str(Path(directory) / "sd_utils")
            result = subprocess.run(
                [
                    "clang",
                    "--driver-mode=g++",
                    "-std=c++17",
                    "-fsanitize=address,undefined",
                    "-Itests/sd_stub",
                    "-Istable_lib/sd-utils",
                    "tests/sd_utils_test.cpp",
                    "stable_lib/sd-utils/sd-utils.cpp",
                    "-o",
                    binary,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run([binary], check=True)

    def test_command_grammar_and_overflow_recovery(self) -> None:
        """Reject malformed commands and resume after the bounded input buffer."""
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            for role in ("SENDER", "RECEIVER"):
                binary = str(Path(directory) / role)
                result = subprocess.run(
                    [
                        "g++",
                        "-std=c++17",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-Iinclude",
                        "-Istable_lib/arq",
                        "-DARQ_TEST_MODE=1",
                        "-DLORA_ROLE_" + role,
                        "tests/arq/commands_test.cpp",
                        "stable_lib/arq/commands.cpp",
                        "-o",
                        binary,
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                subprocess.run([binary], check=True)

    def test_diagnostics_queue_is_bounded_and_nonblocking(self) -> None:
        """Preserve bounded diagnostic queuing without blocking the caller."""
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            binary = str(Path(directory) / "diagnostics")
            result = subprocess.run(
                [
                    "clang",
                    "--driver-mode=g++",
                    "-std=c++17",
                    "-fsanitize=address,undefined",
                    "-Itests/arq/stub",
                    "-Itests/raw_mvp_stub",
                    "-Iinclude",
                    "tests/arq/diagnostics_test.cpp",
                    "-o",
                    binary,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run([binary], check=True)

    def test_headers_are_self_contained(self) -> None:
        """Compile each public protocol header without relying on include order."""
        headers = [
            "arq_codec.h",
            "arq_sender.h",
            "arq_receiver.h",
            "ssot_codec.h",
            "ssot_session.h",
            "ssot_control_input.h",
        ]
        for header in headers:
            with self.subTest(header=header):
                result = subprocess.run(
                    [
                        "g++",
                        "-std=c++17",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-fsyntax-only",
                        "-Istable_lib/arq",
                        "-Istable_lib/ssot",
                        "-Iinclude",
                        "-x",
                        "c++",
                        "-",
                    ],
                    cwd=ROOT,
                    input=f'#include "{header}"\n',
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_named_states_remain_distinct_from_wire_bytes(self) -> None:
        """Keep internal enum states from implicitly changing wire values."""
        result = subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-fsyntax-only",
                "-Istable_lib/arq",
                "-Istable_lib/ssot",
                "-Iinclude",
                "-x",
                "c++",
                "-",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            input="""#include "arq_sender.h"
#include "ssot_session.h"
static_assert(sizeof(arq::SenderState) == sizeof(int));
static_assert(sizeof(ssot::CampaignState) == sizeof(int));
arq::Sender sender{};
ssot::Campaign campaign{};
""",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
