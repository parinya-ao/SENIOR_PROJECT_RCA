"""Check C++ build provenance without writing protected configuration."""

import runpy
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/config"))


class BuildEnvironment(dict):
    """Supply only the SCons operations used by the pre-build script."""

    def GetProjectOption(self, name):
        return {
            "board_build.text_section_start": "0x0",
            "build_flags": [],
            "build_type": "debug",
        }[name]

    def Append(self, **kwargs):
        pass

    def subst(self, value):
        return str(ROOT / ".pio/build/sender")

    def AddBuildMiddleware(self, callback, pattern):
        pass


class CppMigrationTests(unittest.TestCase):
    def test_states_cannot_implicitly_become_wire_integers(self):
        for expression in ("arq::Sender{}.state", "arq::Sender{}.result", "ssot::Campaign{}.state"):
            with self.subTest(expression=expression):
                result = subprocess.run(
                    [
                        "g++",
                        "-std=c++17",
                        "-fsyntax-only",
                        "-Isrc",
                        "-Istable_lib/arq/src/arq/src",
                        "-Iinclude",
                        "-x",
                        "c++",
                        "-",
                    ],
                    input='#include "arq.h"\n#include "ssot.h"\nint value = ' + expression + ";\n",
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("cannot convert", result.stderr)

    def test_build_only_writes_provenance_and_build_directory(self):
        import generate_lora_config as generator

        environment = BuildEnvironment(PROJECT_DIR=str(ROOT), PIOENV="sender")
        with patch.object(generator, "_write_atomic") as write:
            runpy.run_path(
                str(ROOT / "tools/config/platformio_generate.py"),
                init_globals={"env": environment, "Import": lambda name: None},
            )
        destinations = {Path(call.args[0]) for call in write.call_args_list}
        self.assertEqual(
            destinations,
            {
                ROOT / "generated/lora_manifest.json",
                ROOT / "generated/arq_manifest.json",
                ROOT / ".pio/build/sender/lora_build_identity.h",
            },
        )


if __name__ == "__main__":
    unittest.main()
