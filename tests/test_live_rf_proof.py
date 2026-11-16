import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import tools.rf_proof as rf


def fixture() -> Any:
    manifest = json.loads((rf.ROOT / "generated/lora_manifest.json").read_text())
    journal = []
    images = {}

    def add(role: Any, text: Any) -> None:
        journal.append({"role": role, "line": text if role == "HOST" else f"[{role}] {text}"})

    def boot(role: Any, environment: Any) -> None:
        add(role, f"BOOT {environment} fixture")
        add(role, "CONFIG_FINGERPRINT=" + manifest["shared_fingerprint"])
        add(role, "PROTOCOL_VERSION=" + str(manifest["shared"]["protocol"]["version"]))
        add(role, "BUILD_ID=" + manifest["environments"][environment]["build_id"])
        radio = manifest["shared"]["radio"]
        for text in (
            "RADIO_SPI_VERSION=0x12",
            "RADIO_INIT E=0",
            "RADIO_READY",
            f"RADIO_PROFILE F100={round(radio['frequency_mhz'] * 100)} P={radio['tx_power_dbm']}",
            "RADIO_MOD SF=7 BW=125 CR=5",
            "RADIO_FRAME SW=12 PRE=8 CRC=1 HDR=E IQ=0",
        ):
            add(role, text)
        images[role] = {
            "origin": "PHYSICAL_UPDI",
            "run_id": "unit-run",
            "verified": True,
            "signature": "1e970a",
            "port": rf.PORTS[role.lower()],
            "firmware_sha256": "a" * 64,
            "build_id": manifest["environments"][environment]["build_id"],
        }

    boot("RECEIVER", "receiver")
    add("RECEIVER", "WAIT_SESSION")
    add("HOST", "R1234")
    add("RECEIVER", "SESSION_READY C=1234")
    add("RECEIVER", "RX_READY")
    boot("GATEWAY", "sender_hello")
    add("GATEWAY", "WAIT_START")
    add("HOST", "S1234")
    add("GATEWAY", "S_RECEIVED C=1234")
    add("GATEWAY", "TEST_RUNNING C=1234")
    payload = "C=1234 S=01 LEN=11 HEX=68656C6C6F20776F726C64 ASCII=hello world"
    add("GATEWAY", "DATA_PAYLOAD " + payload)
    add("GATEWAY", "DATA_TX C=1234 S=01 A=1 TOA_US=50000")
    add("GATEWAY", "DATA_DONE C=1234 S=01 A=1")
    add("RECEIVER", "PAYLOAD_MATCH C=1234 S=01 A=0")
    add("RECEIVER", "PAYLOAD_BYTES " + payload)
    add("RECEIVER", "DATA_RX C=1234 S=01 A=0")
    add("RECEIVER", "ACK_TX C=1234 S=01 A=0 TOA_US=30000")
    add("RECEIVER", "ACK_DONE C=1234 S=01 A=0")
    add("GATEWAY", "ACK_RX C=1234 S=01 RTT=100")
    add("GATEWAY", "PREFLIGHT_OK C=1234 S=01 A=1")
    add("GATEWAY", "TEST_COMPLETED C=1234")
    return manifest, journal, images


class LiveProofTests(unittest.TestCase):
    def test_session_is_not_reused_after_interrupted_capture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = root / "previous"
            previous.mkdir()
            (previous / "run-session.json").write_text('{"session":4660}')
            proof: Any = SimpleNamespace(note=lambda *_: None)
            with (
                patch.object(rf, "ARTIFACTS", root),
                patch("secrets.randbelow", return_value=0x1233),
            ):
                self.assertEqual(rf.reserve_session(proof, "fresh"), 0x1235)

    def test_complete_correlated_structure(self) -> None:
        manifest, journal, images = fixture()
        self.assertTrue(
            rf.validate_live_proof(journal, manifest, images, "unit-run", 0x1234)["valid"]
        )

    def test_missing_duplicate_wrong_and_stale_evidence_never_passes(self) -> None:
        manifest, original, images = fixture()
        # Every required line is individually removed and duplicated.
        for index in range(len(original)):
            for operation in ("remove", "duplicate"):
                changed = copy.deepcopy(original)
                if operation == "remove":
                    del changed[index]
                else:
                    changed.insert(index, changed[index].copy())
                if original[index]["line"].endswith("WAIT_SESSION"):
                    continue
                with self.subTest(index=index, operation=operation):
                    self.assertFalse(
                        rf.validate_live_proof(changed, manifest, images, "unit-run", 0x1234)[
                            "valid"
                        ]
                    )
        for before, after in [
            ("S=01", "S=02"),
            ("C=1234", "C=1235"),
            ("LEN=11", "LEN=10"),
            ("HEX=6865", "HEX=0065"),
            ("VERSION=2", "VERSION=9"),
            ("CONFIG_FINGERPRINT=", "CONFIG_FINGERPRINT=0"),
            ("BUILD_ID=", "BUILD_ID=0"),
        ]:
            changed = copy.deepcopy(original)
            for event in changed:
                event["line"] = event["line"].replace(before, after)
            with self.subTest(before=before):
                self.assertFalse(
                    rf.validate_live_proof(changed, manifest, images, "unit-run", 0x1234)["valid"]
                )
        for field, value in [
            ("origin", "MOCK_LOG"),
            ("run_id", "stale-run"),
            ("verified", False),
            ("signature", "000000"),
            ("build_id", "wrong"),
            ("port", "/dev/ttyUSB42"),
        ]:
            changed = copy.deepcopy(images)
            changed["GATEWAY"][field] = value
            self.assertFalse(
                rf.validate_live_proof(original, manifest, changed, "unit-run", 0x1234)["valid"]
            )
        changed = copy.deepcopy(original)
        changed.insert(0, {"role": "HOST", "line": "C"})
        self.assertFalse(
            rf.validate_live_proof(changed, manifest, images, "unit-run", 0x1234)["valid"]
        )

    def test_upload_image_mismatch_rejected(self) -> None:
        manifest, _, images = fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text(json.dumps({"origin": "PHYSICAL_UPDI", "images": images}))
            self.assertFalse(rf.upload_evidence_matches(path, manifest))

    def test_fresh_readback_rejects_wrong_image_or_target_serial(self) -> None:
        from tests.test_rf_proof import ihex_record

        manifest, _, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "artifacts"
            backup = artifact / "20261106T104722Z-target-backup"
            backup.mkdir(parents=True)
            (backup / "backup-summary.json").write_text(
                json.dumps(
                    {
                        role + "-candidate": {"device_serial_hex": "ff ff"}
                        for role in ("gateway", "receiver")
                    }
                )
            )
            (root / "config").mkdir()
            (root / "config/current_hardware.json").write_text(
                json.dumps(
                    {
                        role: {"device_serial_hex": "01 02", "port_path": rf.PORTS[role]}
                        for role in ("gateway", "receiver")
                    }
                )
            )
            expected = {}
            for role, environment in [("GATEWAY", "sender_hello"), ("RECEIVER", "receiver")]:
                payload = manifest["environments"][environment]["build_id"].encode()
                image = b"\n".join([ihex_record(0, 0, payload), ihex_record(0, 1, b"")]) + b"\n"
                path = root / ".pio/build" / environment / "firmware.hex"
                path.parent.mkdir(parents=True)
                path.write_bytes(image)
                expected[role.lower()] = payload + b"\xff" * (131072 - len(payload))
            corrupt = None

            def command(name: Any, argv: Any, *_: Any) -> Any:
                role = name.split("-")[0]
                for arg in argv:
                    if ":r:" not in arg:
                        continue
                    memory, _, path, _ = arg.split(":")
                    value = {
                        "signature": bytes.fromhex("1e970a"),
                        "sernum": b"\x01\x02",
                        "flash": expected[role],
                    }[memory]
                    if corrupt == memory:
                        value = bytes([value[0] ^ 1]) + value[1:]
                    Path(path).write_bytes(value)
                return 0, b"", b""

            run = root / "run"
            run.mkdir()
            proof: Any = SimpleNamespace(run_dir=run, command=command, note=lambda *_: None)
            with (
                patch.object(rf, "ROOT", root),
                patch.object(rf, "ARTIFACTS", artifact),
                patch.object(rf, "application_bounds_for_environment", return_value=(0, 130048)),
            ):
                self.assertIsNotNone(rf.verify_installed_images(proof, "config", manifest, "run"))
                for corrupt in ("flash", "signature", "sernum"):
                    self.assertIsNone(rf.verify_installed_images(proof, "config", manifest, "run"))

    def test_verification_flags_without_measurement_record_cannot_open_monitors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof: Any = SimpleNamespace(run_dir=Path(directory), note=lambda *_: None)
            args: Any = SimpleNamespace(
                physical_mapping_verified=True,
                power_verified=True,
                boot_layout_verified=True,
                target_identification_attempted=True,
                authorize_rf_test=True,
            )
            with (
                patch.object(rf, "ROOT", Path(directory)),
                patch.object(rf, "application_layout_verified", return_value=True),
                patch.object(rf, "upload_ports_match", return_value=True),
                patch.object(rf, "check_port_owners", return_value=[]),
                patch.object(rf, "start_rf_monitor") as monitor,
            ):
                self.assertEqual(rf.rf_test(proof, args, True, "config"), 2)
                monitor.assert_not_called()

    def test_live_runner_routes_fresh_commands_and_stops_without_c(self) -> None:
        self._run_capture()

    def test_short_control_write_never_starts_sender(self) -> None:
        self._run_capture(short_write=True)

    def test_repeated_wait_start_never_reissues_sender_command(self) -> None:
        self._run_capture(repeat_wait_start=True)

    def _run_capture(self, short_write: Any=False, repeat_wait_start: Any=False) -> None:
        _manifest, journal, images = fixture()
        writes = []

        class Process:
            def __init__(self, role: Any, output: Any) -> None:
                self.role, self.output, self.stdin = role, output, self

            def poll(self) -> None:
                return None

            def flush(self) -> None:
                pass

            def write(self, data: Any) -> Any:
                writes.append((self.role, data))
                if self.role == "receiver":
                    emit("receiver", ["SESSION_READY C=1234", "RX_READY"], self.output)
                else:
                    if repeat_wait_start:
                        emit("gateway", ["WAIT_START"], self.output)
                    for item in journal:
                        if " C=1234" in item["line"] and "SESSION_READY" not in item["line"]:
                            role = "gateway" if item["role"] == "GATEWAY" else "receiver"
                            self.output.put((role, "stdout", (item["line"] + "\n").encode()))
                return 1 if short_write else len(data)

        def emit(role: Any, values: Any, output: Any) -> None:
            name = "GATEWAY" if role == "gateway" else "RECEIVER"
            for value in values:
                output.put((role, "stdout", f"[{name}] {value}\n".encode()))

        def start(proof: Any, role: Any, port: Any, output: Any) -> Any:
            name = "GATEWAY" if role == "gateway" else "RECEIVER"
            initial = [
                item["line"].split("] ", 1)[1]
                for item in journal
                if item["role"] == name
                and (" C=" not in item["line"])
                and item["line"] != "[RECEIVER] RX_READY"
            ]
            emit(role, initial, output)
            return {"process": Process(role, output), "threads": []}

        with tempfile.TemporaryDirectory() as directory:
            proof: Any = SimpleNamespace(
                run_dir=Path(directory),
                note=lambda name, content: (Path(directory) / name).write_text(content),
            )
            args: Any = SimpleNamespace(
                physical_mapping_verified=True,
                power_verified=True,
                boot_layout_verified=True,
                authorize_rf_test=True,
            )
            with (
                patch.object(rf, "application_layout_verified", return_value=True),
                patch.object(rf, "upload_ports_match", return_value=True),
                patch.object(rf, "check_port_owners", return_value=[]),
                patch.object(rf, "physical_readiness_errors", return_value=[]),
                patch.object(rf, "upload_evidence_matches", return_value=True),
                patch.object(rf, "verify_installed_images", return_value=images),
                patch("secrets.randbelow", return_value=0x1233),
                patch("secrets.token_hex", return_value="unit-run"),
                patch.object(rf, "start_rf_monitor", side_effect=start),
                patch.object(rf, "stop_rf_monitor", return_value=0),
            ):
                self.assertEqual(
                    rf.rf_test(proof, args, True, "config"),
                    2 if short_write or repeat_wait_start else 0,
                )
            self.assertEqual(
                writes,
                [("receiver", b"R1234")]
                if short_write
                else [("receiver", b"R1234"), ("gateway", b"S1234")],
            )
