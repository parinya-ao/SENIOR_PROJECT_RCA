"""Compile and exercise the real raw MVP entrypoint with hardware boundaries stubbed."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/config"))
sys.path.insert(0, str(ROOT / "tools"))


class RawMvpTests(unittest.TestCase):
    def test_legacy_boot_repair_refuses_replacement_geometry(self) -> None:
        import tools.receiver_boot as boot

        proof = SimpleNamespace(run_dir=ROOT)
        with self.assertRaisesRegex(ValueError, "fuse geometry"):
            boot.prepare(proof)

    def test_current_target_snapshot_is_strict_about_serial_and_fuses(self) -> None:
        import tools.receiver_boot as boot

        inventory = json.loads((ROOT / "config/current_hardware.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            proof = SimpleNamespace(run_dir=Path(directory))
            for role in ("receiver", "gateway"):
                expected = inventory[role]

                def command(
                    name: str, argv: list[str], timeout: int, expected: Any = expected
                ) -> tuple[int, bytes, bytes]:
                    for memory in ("signature", "sernum", "fuses", "lock", "flash", "eeprom"):
                        data = {
                            "signature": bytes.fromhex("1e970a"),
                            "sernum": bytes.fromhex(expected["device_serial_hex"]),
                            "fuses": bytes.fromhex(expected["fuses_hex"]),
                            "lock": bytes.fromhex("5cc5c55c"),
                            "flash": b"\xff" * 131072,
                            "eeprom": b"\xff" * 512,
                        }[memory]
                        (proof.run_dir / (name + "-" + memory + ".bin")).write_bytes(data)
                    return 0, b"", b""

                proof.command = command
                result = boot.read_snapshot(proof, "current", role, current_target=True)
                self.assertEqual(result["sernum"], bytes.fromhex(expected["device_serial_hex"]))
                for memory in ("sernum", "fuses"):
                    original = proof.command

                    def wrong(
                        name: str,
                        argv: list[str],
                        timeout: int,
                        original: Any = original,
                        memory: str = memory,
                    ) -> tuple[int, bytes, bytes]:
                        result = cast("tuple[int, bytes, bytes]", original(name, argv, timeout))
                        path = proof.run_dir / (name + "-" + memory + ".bin")
                        path.write_bytes(b"\0" * len(path.read_bytes()))
                        return result

                    proof.command = wrong
                    with self.assertRaises(ValueError):
                        boot.read_snapshot(proof, "bad", role, current_target=True)
                    proof.command = original

    def test_replacement_receiver_geometry(self) -> None:
        from tools.config.validate_lora_ssot import load

        board = load(ROOT / "config/lora_system.json")["receiver_board"]
        self.assertEqual((board["bootsize"], board["bodcfg"], board["image_start"]), (0, 0, 0))

    def test_mvp_roles_are_registered(self) -> None:
        from tools.config.generate_lora_config import load_radio_profile

        profile = load_radio_profile()
        for role in ("sender", "receiver"):
            self.assertIn(role + "_mvp", profile["environments"][role])

    def test_real_entrypoint(self) -> None:
        self.assertTrue((ROOT / "stable_lib/mvp_app/mvp_app.cpp").exists(), "raw MVP entrypoint missing")
        with tempfile.TemporaryDirectory() as directory:
            for role in ("SENDER", "RECEIVER"):
                binary = Path(directory) / role
                result = subprocess.run(
                    [
                        "g++",
                        "-std=c++17",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-DLORA_ROLE_" + role,
                        "-Itests/raw_mvp_stub",
                        "-Iinclude",
                        "-Istable_lib/firmware_app",
                        "-Istable_lib/mvp_app",
                        "-Istable_lib/reverse_raw_app",
                        "-Istable_lib/updi_uart",
                        "-DLORA_APP_MVP=1",
                        "-Istable_lib/updi_uart",
                        "tests/raw_mvp_test.cpp",
                        "-o",
                        str(binary),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    unittest.main()
