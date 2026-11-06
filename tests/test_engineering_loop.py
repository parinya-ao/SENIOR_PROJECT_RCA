import hashlib
import json
import fcntl
import tempfile
import unittest
from pathlib import Path

from tools.engineering_loop import run_controller


GATEWAY_PATH = "/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0"
RECEIVER_PATH = "/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0"


def put_manifest_entry(root: Path, manifest: list[str], relative: str, data: bytes):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    manifest.append(f"{hashlib.sha256(data).hexdigest()}  {relative}")


def make_existing_evidence(root: Path):
    backup = root / "artifacts/rf-proof/20261106T104722Z-target-backup"
    backup.mkdir(parents=True)
    backup_manifest = []
    summary = {}
    for role, candidate, port, bootsize, bodcfg, fuse_hex in (
        ("gateway", "gateway-candidate", GATEWAY_PATH, 0, 0,
         "00 00 F0 FF FF D2 F8 00 00 FF FF FF FF FF FF FF"),
        ("receiver", "receiver-candidate", RECEIVER_PATH, 44, 84,
         "00 54 00 FF FF C9 06 00 2C FF FF FF FF FF FF FF"),
    ):
        flash = bytes([0xFF]) * 131072
        eeprom = bytes([0xFF]) * 512
        fuses = bytes.fromhex(fuse_hex)
        signature = bytes.fromhex("1E 97 0A")
        prefix = f"{candidate}-"
        put_manifest_entry(backup, backup_manifest, prefix + "backup-flash.bin", flash)
        put_manifest_entry(backup, backup_manifest, prefix + "backup-eeprom.bin", eeprom)
        put_manifest_entry(backup, backup_manifest, prefix + "backup-fuses.bin", fuses)
        put_manifest_entry(backup, backup_manifest, prefix + "backup-signature.bin", signature)
        put_manifest_entry(backup, backup_manifest, prefix + "lock.bin", b"\x5c\xc5\xc5\x5c")
        put_manifest_entry(backup, backup_manifest, prefix + "serial-number.bin", bytes(range(16)))
        if role == "receiver":
            put_manifest_entry(backup, backup_manifest, prefix + "flash-reread.bin", flash)
        summary[candidate] = {
            "port_path": port, "signature_hex": "1E 97 0A",
            "fuses_raw_16_hex": fuse_hex,
            "fuses_named": {"bootsize": bootsize, "codesize": 0, "bodcfg": bodcfg},
            "flash": {"bytes": len(flash), "sha256": hashlib.sha256(flash).hexdigest()},
            "eeprom": {"bytes": len(eeprom), "sha256": hashlib.sha256(eeprom).hexdigest()},
        }
    (backup / "sha256.txt").write_text("\n".join(backup_manifest) + "\n")
    (backup / "backup-summary.json").write_text(json.dumps(summary))

    build = root / "artifacts/rf-proof/20261106T111347Z"
    build.mkdir(parents=True)
    build_manifest = []
    for env in ("sender_hello", "receiver"):
        for extension in ("elf", "hex"):
            rel = f".pio/build/{env}/firmware.{extension}"
            put_manifest_entry(root, build_manifest, rel, b"test image\n")
    (build / "firmware-image-hashes.sha256").write_text("\n".join(build_manifest) + "\n")


class EngineeringLoopTests(unittest.TestCase):
    def test_missing_physical_measurements_runs_only_safe_preflight_and_persists_wait(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_existing_evidence(root)
            calls = []

            def fake_command(argv, cwd, timeout):
                calls.append(argv)
                proof_dir = cwd / "artifacts/rf-proof/20261106T114610Z"
                proof_dir.mkdir(parents=True, exist_ok=True)
                (proof_dir / "preflight.log").write_text(
                    "BLOCKED: power conditions, BOOTSIZE/CODESIZE/BODCFG fuse verification\n"
                    "No serial ports opened.\n")
                return 2, (
                    "BLOCKED: power conditions\nNo serial ports opened.\n"
                    "Artifacts: artifacts/rf-proof/20261106T114610Z\n"
                ), ""

            port_resolver = lambda path: ("/dev/ttyUSB1" if ":4:" in path else "/dev/ttyUSB0", True)
            result = run_controller(root=root, command_runner=fake_command,
                                    port_resolver=port_resolver)

            self.assertEqual(result, 2)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][calls[0].index("--stage") + 1], "preflight")
            self.assertNotIn("--power-verified", calls[0])
            self.assertNotIn("--authorize-upload", calls[0])
            self.assertNotIn("--authorize-rf-test", calls[0])

            state = json.loads((root / "artifacts/engineering-loop/state.json").read_text())
            self.assertEqual(state["stage"], "WAITING_PHYSICAL_PREFLIGHT")
            self.assertEqual(state["status"], "BLOCKED_HARDWARE")
            self.assertIn("CHECK_CURRENT_STATE", state["completed_stages"])
            self.assertEqual(state["physical_target_mapping"]["gateway"]["usb_path"], GATEWAY_PATH)
            self.assertEqual(state["latest_verified_mcu_signatures"]["receiver"]["signature"], "1E 97 0A")
            self.assertEqual(state["upload_status"], {"receiver": "NOT_RUN", "sender": "NOT_RUN"})
            self.assertEqual(state["radio_spi_results"], {"receiver": "NOT_RUN", "sender": "NOT_RUN"})
            self.assertEqual(state["final_data_ack_result"], "NOT_RUN")
            self.assertFalse(state["backup_recovery"]["restore_tested"])
            self.assertIsNone(state["active_action"])

            result = run_controller(root=root, command_runner=fake_command,
                                    port_resolver=port_resolver)
            self.assertEqual(result, 2)
            self.assertEqual(len(calls), 1, "safe preflight is not repeated while waiting for the same measurements")

    def test_interrupted_hardware_action_is_never_replayed_automatically(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_existing_evidence(root)
            state_dir = root / "artifacts/engineering-loop"
            state_dir.mkdir(parents=True)
            (state_dir / "state.json").write_text(json.dumps({
                "schema_version": 1,
                "goal": "single_lora_data_ack",
                "stage": "RUN_SPI_SMOKE",
                "active_action": {"stage": "RUN_SPI_SMOKE", "started_at": "earlier"},
            }))
            calls = []
            result = run_controller(
                root=root,
                command_runner=lambda *args: calls.append(args),
            )

            self.assertEqual(result, 2)
            self.assertEqual(calls, [])
            state = json.loads((state_dir / "state.json").read_text())
            self.assertEqual(state["stage"], "BLOCKED_HARDWARE")
            self.assertTrue(state["operator_resume_required"])

    def test_corrupt_backup_manifest_stops_before_running_proof_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_existing_evidence(root)
            manifest = root / "artifacts/rf-proof/20261106T104722Z-target-backup/sha256.txt"
            manifest.write_text("0" * 64 + "  gateway-candidate-backup-signature.bin\n")
            calls = []

            result = run_controller(root=root, command_runner=lambda *args: calls.append(args))

            self.assertEqual(result, 1)
            self.assertEqual(calls, [])
            state = json.loads((root / "artifacts/engineering-loop/state.json").read_text())
            self.assertEqual(state["stage"], "FAILED")
            self.assertIn("hash mismatch", state["last_real_error"].lower())

    def test_concurrent_controller_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock_path = root / "artifacts/engineering-loop/run.lock"
            lock_path.parent.mkdir(parents=True)
            calls = []
            with lock_path.open("a") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = run_controller(root=root,
                                        command_runner=lambda *args: calls.append(args))
            self.assertEqual(result, 2)
            self.assertEqual(calls, [])

    def test_recorded_success_never_repeats_rf_transmission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "artifacts/engineering-loop"
            state_dir.mkdir(parents=True)
            (state_dir / "state.json").write_text(json.dumps({
                "schema_version": 1,
                "goal": "single_lora_data_ack",
                "stage": "PROVEN",
                "status": "RF_DATA_ACK_PROVEN",
                "completed_stages": ["PROVEN"],
            }))
            calls = []
            result = run_controller(root=root,
                                    command_runner=lambda *args: calls.append(args))
            self.assertEqual(result, 0)
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
