"""Check C++ build provenance without writing protected configuration."""

import runpy
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/config"))


class BuildEnvironment(dict[str, object]):
    """Supply only the SCons operations used by the pre-build script."""

    def GetProjectOption(self, name: str) -> object:
        """Return a configured PlatformIO project option for the fixture."""
        return {
            "board_build.text_section_start": "0x0",
            "build_flags": [],
            "build_type": "debug",
        }[name]

    def Append(self, **kwargs: object) -> None:
        """Accept SCons build additions that are irrelevant to this contract."""

    def subst(self, value: str) -> str:
        """Resolve SCons substitutions to the fixture build directory."""
        return str(ROOT / ".pio/build/sender")

    def AddBuildMiddleware(self, callback: Any, pattern: Any) -> None:
        """Record no middleware because this test only inspects build provenance."""


class CppMigrationTests(unittest.TestCase):
    def test_arq_role_adapters_include_only_their_transaction_api(self) -> None:
        """Keep Sender and Receiver application headers on their own role."""
        sender = (ROOT / "src/sender/appcode/arq/sender.cpp").read_text()
        receiver = (ROOT / "src/receiver/appcode/arq/receiver.cpp").read_text()

        self.assertIn('#include "arq_sender.h"', sender)
        self.assertNotIn('#include "arq_receiver.h"', sender)
        self.assertNotIn('#include "arq.h"', sender)
        self.assertIn('#include "arq_receiver.h"', receiver)
        self.assertNotIn('#include "arq_sender.h"', receiver)
        self.assertNotIn('#include "arq.h"', receiver)

    def test_states_cannot_implicitly_become_wire_integers(self) -> None:
        """Keep C++ state enums separate from protocol integer fields."""
        for expression in ("arq::Sender{}.state", "arq::Sender{}.result", "ssot::Campaign{}.state"):
            with self.subTest(expression=expression):
                result = subprocess.run(
                    [
                        "g++",
                        "-std=c++17",
                        "-fsyntax-only",
                        "-Istable_lib/ssot",
                        "-Istable_lib/arq",
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

    def test_build_only_writes_provenance_and_build_directory(self) -> None:
        """Limit build-time writes to provenance and the selected build directory."""
        from tools.config import generate_lora_config as generator

        environment = BuildEnvironment(PROJECT_DIR=str(ROOT), PIOENV="sender")
        with (
            patch.object(generator, "_write_atomic") as write,
            patch.dict(sys.modules, {"generate_lora_config": generator}),
        ):
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
