import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import tools.receiver_boot as boot
import receiver_boot as receiver_boot_module
from tools.device_detection.firmware_identity import normalize_ihex_region


def recording_command(commands: list[list[str]]) -> Any:
    def command(name: str, argv: list[str], *_args: Any) -> tuple[int, bytes, bytes]:
        commands.append(argv)
        return 0, b"", b""

    return command


class ReceiverBootTests(unittest.TestCase):
    def test_snapshot_read_retries_at_lower_baud_after_link_failure(self) -> None:
        class Proof:
            run_dir = Path()

            def __init__(self) -> None:
                self.calls: list[tuple[str, list[str], Any]] = []

            def command(self, name: Any, command: Any, timeout: Any) -> Any:
                self.calls.append((name, command, timeout))
                return (1 if len(self.calls) == 1 else 0), b"", b""

        proof = Proof()
        self.assertEqual(
            boot.read_snapshot_command(proof, "snapshot", ["avrdude", "-b", "115200"]), 0
        )
        self.assertEqual(
            [call[1][call[1].index("-b") + 1] for call in proof.calls], ["115200", "57600"]
        )

    def test_page0_overlay_preserves_every_other_byte(self) -> None:
        original = bytes(range(256)) * 512
        stub = b"\xf8\x94\x11\x24"
        patched, changes = boot.patch_page0(original, stub)
        self.assertEqual(len(patched), 512)
        self.assertEqual(patched[len(stub) :], original[len(stub) : 512])
        self.assertEqual(changes, [[0, 4]])

    def test_rejects_invalid_backup_and_out_of_page_stub(self) -> None:
        for original, stub in [
            (b"bad", b"ab"),
            (b"\xff" * 131072, b"x" * 513),
            (b"\xff" * 131072, b""),
        ]:
            with self.assertRaises(ValueError):
                boot.patch_page0(original, stub)

    def test_write_command_is_exact_page_erase_not_chip_or_fuses(self) -> None:
        command = boot.page_write_command("avrdude", "avrdude.conf", "receiver", "page.hex", 0, 512)
        self.assertNotIn("-e", command)
        self.assertNotIn("-V", command)
        self.assertIn("-D", command)
        self.assertEqual(command[command.index("-T") + 1], "erase flash 0x0 0x200")
        self.assertEqual(
            [command[i + 1] for i, x in enumerate(command) if x == "-U"],
            ["flash:w:page.hex:i", "flash:v:page.hex:i"],
        )
        for start, size in [(1, 512), (0, 513), (0x5800, 512), (0, 1024)]:
            with self.assertRaises(ValueError):
                boot.page_write_command("a", "c", "p", "f", start, size)

    def test_address_units_use_byte_addresses(self) -> None:
        self.assertEqual(boot.reset_target(bytes.fromhex("0c94002c"), 0), 0x5800)
        self.assertEqual(boot.reset_target(bytes.fromhex("52c00000"), 0x5800), 0x58A6)
        with self.assertRaises(ValueError):
            boot.reset_target(b"\xff" * 4, 0x5800)

    def test_missing_or_wrong_specific_authorization_opens_no_port(self) -> None:
        proof: Any = SimpleNamespace(note=lambda *_: None)
        args: Any = SimpleNamespace(
            authorize_receiver_boot_page0=None, receiver_boot_package=None, authorize_upload=True
        )
        with patch.object(boot, "read_snapshot") as snapshot:
            self.assertEqual(boot.install(proof, args), 2)
            snapshot.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "map.json"
            package.write_text("{}")
            args.receiver_boot_package = package
            args.authorize_receiver_boot_page0 = "wrong"
            with (
                patch.object(boot, "load_package", return_value={}),
                patch.object(boot, "read_snapshot") as snapshot,
            ):
                with self.assertRaises(ValueError):
                    boot.install(proof, args)
                snapshot.assert_not_called()

    def test_unapproved_flash_fuse_or_eeprom_changes_fail_preservation(self) -> None:
        before = dict.fromkeys(("signature", "sernum", "fuses", "eeprom", "lock"), b"abc")
        before["flash"] = b"\xff" * 131072
        after = dict(before)
        after["flash"] = b"\0" * 512 + before["flash"][512:]
        boot.require_preserved(before, after, 0, 512)
        for name in ("signature", "sernum", "fuses", "eeprom", "lock", "flash"):
            changed = dict(after)
            changed[name] = changed[name][:-1] + b"\x00"
            with self.subTest(name=name), self.assertRaises(ValueError):
                boot.require_preserved(before, changed, 0, 512)

    def test_no_meter_still_blocks_write_without_wiring_observations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "map.json"
            package.write_text("{}")
            args: Any = SimpleNamespace(
                receiver_boot_package=package,
                authorize_upload=True,
                authorize_receiver_boot_page0=boot.sha(package.read_bytes()),
                no_meter_mode=True,
                physical_mapping_verified=False,
                power_verified=False,
            )
            proof: Any = SimpleNamespace(note=lambda *_: None)
            with (
                patch.object(boot, "load_package", return_value={}),
                patch.object(boot, "read_snapshot") as snapshot,
            ):
                self.assertEqual(boot.install(proof, args), 2)
                snapshot.assert_not_called()


class CompiledHandoffTests(unittest.TestCase):
    code: bytes

    @classmethod
    def setUpClass(cls) -> None:
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.directory = Path(temporary.name) / "fixture"
        boot.build_fixture(cls.directory)
        cls.code = (cls.directory / "receiver-handoff.bin").read_bytes()

    def test_fixture_contains_standalone_flash_artifacts(self) -> None:
        for extension in ("elf", "map", "hex", "disassembly.txt"):
            self.assertTrue((self.directory / f"receiver-handoff.{extension}").stat().st_size)
        self.assertEqual(
            normalize_ihex_region(
                (self.directory / "receiver-handoff.hex").read_text(), 0, len(self.code)
            ),
            self.code,
        )

    def test_compiled_handoff_uses_correct_byte_target_and_interrupt_state(self) -> None:
        result = boot.trace_stub(self.code, bytes.fromhex("52c00000"))
        self.assertEqual(result, {"application_entered": True, "cpuint": 0, "interrupts": False})
        self.assertLess(len(self.code), 512)
        self.assertIn(bytes.fromhex("0c94002c"), self.code)

    def test_blank_or_any_wrong_reset_byte_parks(self) -> None:
        cases: list[bytes] = [b"\xff" * 4]
        for index in range(4):
            corrupted = bytearray.fromhex("52c00000")
            corrupted[index] ^= 1
            cases.append(bytes(corrupted))
        for entry in cases:
            with self.subTest(entry=entry):
                result = boot.trace_stub(self.code, entry)
                self.assertFalse(result["application_entered"])
                self.assertFalse(result["interrupts"])
                self.assertEqual(result["cpuint"], 0)


class BootPackageTests(unittest.TestCase):
    directory: Path
    package: Path

    @classmethod
    def setUpClass(cls) -> None:
        if (
            json.loads((boot.ROOT / "config/lora_system.json").read_text())["receiver_board"][
                "bootsize"
            ]
            != 44
        ):
            msg = "archived BOOTSIZE=44 repair does not apply to the replacement Receiver"
            raise unittest.SkipTest(
                msg
            )
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.directory = Path(temporary.name)

        def command(name: Any, argv: Any, timeout: Any=None) -> Any:
            result = subprocess.run(argv, capture_output=True, timeout=timeout, check=False)
            (cls.directory / (name + ".stdout.log")).write_bytes(result.stdout)
            (cls.directory / (name + ".stderr.log")).write_bytes(result.stderr)
            return result.returncode, result.stdout, result.stderr

        proof: Any = SimpleNamespace(
            run_dir=cls.directory,
            command=command,
            note=lambda name, content: (cls.directory / name).write_text(content),
        )
        boot.prepare(proof)
        cls.package = cls.directory / "receiver-boot-overwrite-map.json"

    def test_exact_installed_compiler_and_avrdude_simulation_package(self) -> None:
        report = boot.load_package(self.package)
        self.assertEqual(report["boot_pages_written"], [0])
        self.assertEqual(report["stub_size"], 48)
        self.assertEqual(report["physical_restore_test"], "NOT_RUN")
        self.assertEqual(report["physical_programming"], "NOT_RUN")
        self.assertTrue((self.directory / "receiver-handoff.map").is_file())

    def test_modified_package_image_is_rejected(self) -> None:
        image = self.directory / "receiver-boot-page0.hex"
        original = image.read_bytes()
        try:
            image.write_bytes(original.replace(b"F894", b"0000", 1))
            with self.assertRaises(ValueError):
                boot.load_package(self.package)
        finally:
            image.write_bytes(original)

    def snapshots(self) -> Any:
        original = boot.BACKUP.read_bytes()
        report = boot.load_package(self.package)
        spi = normalize_ihex_region(
            (self.directory / "receiver-spi-full-pages.hex").read_text(),
            boot.APP_START,
            report["application_write_range"][1],
        )
        base = {
            "signature": bytes.fromhex("1e970a"),
            "sernum": bytes.fromhex(report["expected_serial"]),
            "fuses": boot.BACKUP.with_name("receiver-candidate-backup-fuses.bin").read_bytes(),
            "eeprom": boot.BACKUP.with_name("receiver-candidate-backup-eeprom.bin").read_bytes(),
            "lock": bytes.fromhex("5cc5c55c"),
            "flash": original,
        }
        app = dict(
            base,
            flash=original[: boot.APP_START]
            + spi
            + original[report["application_write_range"][1] :],
        )
        page = normalize_ihex_region(
            (self.directory / "receiver-boot-page0.hex").read_text(), 0, 512
        )
        patched = dict(app, flash=page + app["flash"][512:])
        return base, app, patched

    def test_authorized_installer_programs_app_before_boot_with_preservation(self) -> None:
        import tools.rf_proof as rf

        snapshots = self.snapshots()
        commands: list[list[str]] = []
        proof: Any = SimpleNamespace(
            run_dir=self.directory,
            command=recording_command(commands),
            note=lambda name, text: (self.directory / name).write_text(text),
        )
        args: Any = SimpleNamespace(
            receiver_boot_package=self.package,
            authorize_upload=True,
            authorize_receiver_boot_page0=boot.sha(self.package.read_bytes()),
            physical_mapping_verified=True,
            power_verified=True,
        )
        with (
            patch.object(boot, "read_snapshot", side_effect=snapshots),
            patch.object(rf, "physical_readiness_errors", return_value=[]),
            patch.object(rf, "check_port_owners", return_value=[]),
        ):
            self.assertEqual(boot.install(proof, args), 0)
        self.assertEqual(
            [command[command.index("-T") + 1] for command in commands],
            ["erase flash 0x5800 0x7800", "erase flash 0x0 0x200"],
        )
        self.assertTrue(all("-e" not in command for command in commands))

    def test_restore_can_recover_partly_erased_page_without_rewriting_app(self) -> None:
        import tools.rf_proof as rf

        _base, app, _ = self.snapshots()
        damaged = dict(app, flash=b"\xff" * 512 + app["flash"][512:])
        commands: list[list[str]] = []
        proof: Any = SimpleNamespace(
            run_dir=self.directory,
            command=recording_command(commands),
            note=lambda name, text: (self.directory / name).write_text(text),
        )
        report = boot.load_package(self.package)
        args: Any = SimpleNamespace(
            receiver_boot_package=self.package,
            authorize_upload=True,
            authorize_receiver_boot_restore=report["restore_hex_sha256"],
            physical_mapping_verified=True,
            power_verified=True,
        )
        with (
            patch.object(boot, "read_snapshot", side_effect=[damaged, app]),
            patch.object(rf, "physical_readiness_errors", return_value=[]),
            patch.object(rf, "check_port_owners", return_value=[]),
        ):
            self.assertEqual(boot.install(proof, args, restore=True), 0)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][commands[0].index("-T") + 1], "erase flash 0x0 0x200")

    def test_app_preservation_failure_prevents_boot_write(self) -> None:
        import tools.rf_proof as rf

        base, app, _ = self.snapshots()
        broken = bytearray(app["flash"])
        broken[1000] ^= 1
        app["flash"] = bytes(broken)
        commands: list[list[str]] = []
        proof: Any = SimpleNamespace(
            run_dir=self.directory,
            command=recording_command(commands),
            note=lambda *_: None,
        )
        args: Any = SimpleNamespace(
            receiver_boot_package=self.package,
            authorize_upload=True,
            authorize_receiver_boot_page0=boot.sha(self.package.read_bytes()),
            physical_mapping_verified=True,
            power_verified=True,
        )
        with (
            patch.object(boot, "read_snapshot", side_effect=[base, app]),
            patch.object(rf, "physical_readiness_errors", return_value=[]),
            patch.object(rf, "check_port_owners", return_value=[]),self.assertRaises(ValueError)
        ):
            boot.install(proof, args)
        self.assertEqual(len(commands), 1)


class ApplicationPageWriteTests(unittest.TestCase):
    def test_guarded_writer_rejects_live_serial_before_erase(self) -> None:
        import tools.rf_proof as rf
        from tests.test_rf_proof import effective_platformio_config

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / ".pio/build/receiver"
            build.mkdir(parents=True)
            data = boot.ihex(b"abcd", boot.APP_START).encode()
            (build / "firmware.hex").write_bytes(data)
            commands: list[list[str]] = []

            def command(name: Any, argv: Any, *unused: Any) -> Any:
                commands.append(argv)
                return 0, b"avrdude version 8.1", b""

            proof: Any = SimpleNamespace(run_dir=root, command=command, note=lambda *_: None)
            with (
                patch.object(rf, "ROOT", root),
                patch.object(boot, "read_snapshot", return_value={"sernum": b"wrong"}),
            ):
                result = rf.program_application(
                    proof,
                    "receiver",
                    effective_platformio_config(),
                    approved_sha=hashlib.sha256(data).hexdigest(),
                    approved_serial="00",
                    approved_pages=(boot.APP_START, boot.APP_START + 512),
                )
            self.assertEqual(result, 1)
            self.assertFalse(any("-T" in command for command in commands))

    def test_tracker_selector_rejects_wrong_identity_or_hash_before_programming(self) -> None:
        import tools.rf_proof as rf

        args: Any = SimpleNamespace(
            target_role="receiver",
            target_serial="bad",
            image_sha256="bad",
            page_start=0,
            page_end=0x9800,
            authorize_upload=True,
        )
        proof: Any = SimpleNamespace(note=lambda *_: None)
        with patch.object(rf, "program_application") as writer:
            self.assertNotEqual(rf.tracker_app_upload(proof, args, ""), 0)
            writer.assert_not_called()

    def test_userrow_changes_fail_preservation(self) -> None:
        before = dict.fromkeys(("signature", "sernum", "fuses", "eeprom", "lock", "usersig"), b"a")
        before["flash"] = bytes(1024)
        with self.assertRaisesRegex(ValueError, "usersig"):
            boot.require_preserved(before, dict(before, usersig=b"b"), 0, 512)

    def test_application_writer_refuses_unbound_image_before_updi(self) -> None:
        import tools.rf_proof as rf
        from tests.test_rf_proof import effective_platformio_config

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / ".pio/build/receiver_spi"
            build.mkdir(parents=True)
            (build / "firmware.hex").write_text(boot.ihex(b"\x52\xc0\x00\x00", boot.APP_START))
            commands: list[list[str]] = []

            def command(_name: str, argv: list[str], *_args: Any) -> tuple[int, bytes, bytes]:
                commands.append(argv)
                return 0, b"avrdude version 8.1", b""

            proof: Any = SimpleNamespace(run_dir=root, command=command, note=lambda *_: None)
            with (
                patch.object(rf, "ROOT", root),
                patch.object(receiver_boot_module, "read_snapshot") as snapshot,
            ):
                self.assertNotEqual(
                    rf.program_application(proof, "receiver_spi", effective_platformio_config()), 0
                )
            self.assertEqual(commands, [])
            snapshot.assert_not_called()

    def test_guarded_app_writer_erases_only_its_page_with_installed_avrdude_dryrun(self) -> None:
        import tools.rf_proof as rf
        from tests.test_rf_proof import effective_platformio_config

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / ".pio/build/receiver_spi"
            build.mkdir(parents=True)
            payload = bytes.fromhex("52c00000")
            (build / "firmware.hex").write_text(boot.ihex(payload, boot.APP_START))
            original = bytes(range(256)) * 512
            approved_serial = "11" * 16
            before = dict.fromkeys(("signature", "fuses", "eeprom", "lock"), b"unchanged")
            before["sernum"] = bytes.fromhex(approved_serial)
            before["usersig"] = b"unchanged-userrow"
            before["flash"] = original
            (root / "before.bin").write_bytes(original)
            commands: list[list[str]] = []

            def command(name: Any, argv: Any, *args: Any) -> Any:
                commands.append(argv)
                if "--version" in argv:
                    return 0, b"avrdude version 8.1", b""
                self.assertIn("erase flash 0x5800 0x200", argv)
                self.assertNotIn("-e", argv)
                simulated = list(argv)
                simulated[simulated.index("-c") + 1] = "dryrun"
                at = simulated.index("-T")
                simulated[at:at] = ["-U", f"flash:w:{root / 'before.bin'}:r"]
                simulated += ["-U", f"flash:r:{root / 'after.bin'}:r"]
                result = subprocess.run(simulated, capture_output=True, check=False)
                return result.returncode, result.stdout, result.stderr

            def snapshot(proof: Any, name: Any, role: Any, **options: Any) -> Any:
                self.assertTrue(options.get("current_target"))
                if "before" in name:
                    return dict(before)
                return dict(before, flash=(root / "after.bin").read_bytes())

            proof: Any = SimpleNamespace(run_dir=root, command=command, note=lambda *_: None)
            with (
                patch.object(rf, "ROOT", root),
                patch.object(receiver_boot_module, "read_snapshot", side_effect=snapshot),
            ):
                self.assertEqual(
                    rf.program_application(
                        proof,
                        "receiver_spi",
                        effective_platformio_config(),
                        approved_sha=hashlib.sha256((build / "firmware.hex").read_bytes()).hexdigest(),
                        approved_serial=approved_serial,
                        approved_pages=(boot.APP_START, boot.APP_START + 512),
                    ),
                    0,
                )
            after = (root / "after.bin").read_bytes()
            self.assertEqual(after[: boot.APP_START], original[: boot.APP_START])
            self.assertEqual(after[boot.APP_START + 512 :], original[boot.APP_START + 512 :])
            self.assertEqual(after[boot.APP_START : boot.APP_START + 512], payload + b"\xff" * 508)
