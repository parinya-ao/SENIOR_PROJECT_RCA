"""Compile the portable module contracts independently of Arduino."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CppInterfaceTests(unittest.TestCase):
    def test_command_grammar_and_overflow_recovery(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            for role in ("SENDER", "RECEIVER"):
                binary = str(Path(directory) / role)
                result = subprocess.run(
                    ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                     "-Iinclude", "-Isrc/arq", "-DARQ_TEST_MODE=1",
                     "-DLORA_ROLE_" + role, "tests/arq/commands_test.cpp",
                     "src/arq/commands.cpp", "-o", binary],
                    cwd=ROOT, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                subprocess.run([binary], check=True)

    def test_diagnostics_queue_is_bounded_and_nonblocking(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            binary = str(Path(directory) / "diagnostics")
            result = subprocess.run(
                ["clang", "--driver-mode=g++", "-std=c++17", "-fsanitize=address,undefined", "-Itests/arq/stub",
                 "-Itests/raw_mvp_stub", "-Iinclude",
                 "tests/arq/diagnostics_test.cpp", "-o", binary],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run([binary], check=True)

    def test_headers_are_self_contained(self):
        headers = [
            "arq/codec.h",
            "arq/sender.h",
            "arq/receiver.h",
            "ssot/codec.h",
            "ssot/session.h",
            "ssot/control_input.h",
        ]
        for header in headers:
            with self.subTest(header=header):
                result = subprocess.run(
                    ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                     "-fsyntax-only", "-Isrc", "-Iinclude", "-x", "c++", "-"],
                    cwd=ROOT, input=f'#include "{header}"\n',
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_named_states_remain_distinct_from_wire_bytes(self):
        result = subprocess.run(
            ["g++", "-std=c++17", "-fsyntax-only", "-Isrc", "-Iinclude",
             "-x", "c++", "-"],
            cwd=ROOT, capture_output=True, text=True,
            input='''#include "arq/sender.h"
#include "ssot/session.h"
static_assert(sizeof(arq::SenderState) == sizeof(int));
static_assert(sizeof(ssot::CampaignState) == sizeof(int));
arq::Sender sender{};
ssot::Campaign campaign{};
''',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
