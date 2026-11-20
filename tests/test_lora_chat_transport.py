"""Host checks for active project configuration and non-radio dry runs."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import installed_rf
from tools.device_detection.evidence import DeviceRole
from tools.lora_chat.cli import _create_run_directory
from tools.lora_chat.session import load_chat_settings
from tools.lora_chat.transport import (
    BenchTransport,
    TransportError,
    load_bench_profile,
)


def test_current_profile_exposes_fixed_payload_and_unresolved_rf_inventory() -> None:
    """The console derives message and RF arrangement facts from project SSOT."""
    profile = load_bench_profile()
    assert profile.payload == b"hello world"
    assert profile.data_type == 8
    assert profile.ack_type == 3
    assert profile.nack_type == 9
    assert profile.max_retries == 3
    assert profile.radio_inventory is None
    assert profile.antenna_inventory is None


def test_profile_rejects_wrong_numeric_types(tmp_path: Path) -> None:
    """Boolean values cannot pass as protocol integers at the configuration edge."""
    project_root = Path(__file__).resolve().parents[1]
    profile = json.loads((project_root / "config" / "lora_system.json").read_text(encoding="utf-8"))
    profile["protocol"]["data_type"] = True
    path = tmp_path / "lora_system.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    with pytest.raises(TypeError, match="data_type"):
        load_bench_profile(path)


def test_dry_run_creates_empty_event_log_and_disables_transmission(tmp_path: Path) -> None:
    """Dry run never fabricates hardware events or opens a serial transport."""
    profile = load_bench_profile()
    run_dir = tmp_path / "run"
    transport = BenchTransport(
        run_dir,
        profile,
        max_message_bytes=load_chat_settings().max_message_bytes,
        authorize_rf_test=False,
        dry_run=True,
    )
    rows, offset = transport.events_since(0)

    assert rows == []
    assert offset == 0
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == ""
    assert "dry-run" in (transport.transmit_blocker() or "")
    assert transport.close()


def test_rf_authorization_requires_separate_setup_confirmation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """RF authorization alone cannot override missing setup confirmation."""
    profile = load_bench_profile()
    transport = BenchTransport(
        tmp_path / "run",
        profile,
        max_message_bytes=load_chat_settings().max_message_bytes,
        authorize_rf_test=True,
    )

    def connected(_transport: BenchTransport) -> bool:
        return True

    monkeypatch.setattr(BenchTransport, "is_connected", property(connected))
    assert "--confirm-rf-setup" in (transport.transmit_blocker() or "")
    assert transport.hardware is not None
    assert transport.hardware.no_flash is True
    assert transport.hardware.write_approval is None
    assert transport.hardware.monitors == {}
    with pytest.raises(TransportError, match="arrangement is unresolved"):
        transport.send_message("hello world")
    assert transport.log is not None
    assert transport.log.snapshot() == []


def test_run_directory_is_created_once_by_the_transport(tmp_path: Path) -> None:
    """The CLI chooses a unique path while the transport owns directory creation."""
    profile = load_bench_profile()
    run_dir = _create_run_directory(tmp_path / "runs")
    assert not run_dir.exists()
    transport = BenchTransport(
        run_dir,
        profile,
        max_message_bytes=load_chat_settings().max_message_bytes,
        authorize_rf_test=False,
        dry_run=True,
    )
    assert run_dir.is_dir()
    assert transport.close()


def test_connect_read_only_with_a_current_build_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A byte mismatch still exposes fresh per-board diagnostics."""
    transport = BenchTransport(
        tmp_path / "run",
        load_bench_profile(),
        max_message_bytes=100,
        authorize_rf_test=False,
    )
    hardware = transport.hardware
    assert hardware is not None

    def read_images() -> dict[str, dict[str, object]]:
        hardware.images = {"GATEWAY": {"verified": False, "serial_number": "abcd"}}
        hardware.usb_present = {"gateway"}
        return hardware.images

    monkeypatch.setattr(hardware, "read_chat_images", read_images, raising=False)
    monkeypatch.setattr(transport, "_connect_capture", lambda: None, raising=False)
    monkeypatch.setattr(hardware, "connect", lambda: pytest.fail("production preparation"))
    transport.connect()
    assert transport.board_status("GATEWAY")["USB"] == "Present"
    assert transport.board_status("GATEWAY")["Enrolled MCU"] == "abcd"
    assert transport.board_status("GATEWAY")["Current build"] == "Mismatch"
    assert transport.board_status("TRACKER")["USB"] == "Absent"
    assert transport.board_status("TRACKER")["Enrolled MCU"] == "Unverified"


def test_verified_current_pair_takes_precedence_over_saved_legacy_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Probe current firmware for Echo even when the bench retains its prior receipt."""
    transport = BenchTransport(
        tmp_path / "run",
        load_bench_profile(),
        max_message_bytes=100,
        authorize_rf_test=True,
        historical_receipt=tmp_path / "old-receipt.json",
    )
    hardware = transport.hardware
    assert hardware is not None
    images = {
        "GATEWAY": {"verified": True, "build_id": "current-gateway"},
        "RECEIVER": {"verified": True, "build_id": "current-receiver"},
    }
    hardware.proof = SimpleNamespace(run_dir=tmp_path)
    monkeypatch.setattr(hardware, "read_chat_images", lambda: images)
    monkeypatch.setattr(hardware, "ready", lambda: None)
    monkeypatch.setattr(
        installed_rf, "verify_snapshots", lambda *_: pytest.fail("consulted the legacy receipt")
    )
    monkeypatch.setattr(
        transport,
        "_negotiate_interactive",
        lambda: setattr(transport, "interactive_max_data_bytes", 30),
    )

    transport.connect()

    assert transport.interactive_max_data_bytes == 30
    assert transport.connection_stage == "READY"


def test_archived_gateway_names_and_full_fresh_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Compare all readback bytes against the reviewed upload archive."""
    archive, live = tmp_path / "archive", tmp_path / "live"
    for directory in (archive, live, tmp_path / "generated"):
        directory.mkdir()
    monkeypatch.setattr(installed_rf.rf, "ROOT", tmp_path)
    hardware = {
        DeviceRole.GATEWAY: SimpleNamespace(serial_number=b"gateway"),
        DeviceRole.TRACKER: SimpleNamespace(serial_number=b"tracker"),
    }
    monkeypatch.setattr(installed_rf, "load_hardware_registry", lambda _: hardware)
    monkeypatch.setattr(installed_rf, "hardware_ports", lambda _: {"gateway": "g", "receiver": "r"})
    manifest = {
        "boards": {"sender": {"mcu": "avr"}, "receiver": {"mcu": "avr"}},
        "device_profiles": {"avr": {"flash_bytes": 8, "signature_hex": "010203"}},
    }
    (tmp_path / "generated/lora_manifest.json").write_text(json.dumps(manifest))
    images = {}
    for role, live_prefix, environment, port in (
        (DeviceRole.GATEWAY, "sender", "sender_hello", "g"),
        (DeviceRole.TRACKER, "receiver", "receiver", "r"),
    ):
        archived = "gateway" if role == DeviceRole.GATEWAY else "receiver"
        data = b"12345678"
        serial = hardware[role].serial_number
        signature = bytes.fromhex("010203")
        fuses = bytes(16)
        (archive / f"{archived}-live-flash.bin").write_bytes(data)
        (archive / f"{archived}-live-serial.bin").write_bytes(serial)
        (archive / f"{archived}-live-signature.bin").write_bytes(signature)
        (archive / f"{environment}-after-page-write-fuses.bin").write_bytes(fuses)
        for kind, content in (
            ("flash", data),
            ("sernum", serial),
            ("signature", signature),
            ("fuses", fuses),
        ):
            (live / f"{live_prefix}-{kind}.bin").write_bytes(content)
        images[archived.upper()] = {
            "serial_number": serial.hex(),
            "signature": signature.hex(),
            "port": port,
            "environment": environment,
            "verified": True,
            "start": 0,
            "end": len(data),
            "build_id": "a" * 64,
            "readback_region_sha256": hashlib.sha256(data).hexdigest(),
        }
    receipt = archive / "physical-upload.json"
    receipt.write_text(json.dumps({"origin": "PHYSICAL_UPDI", "images": images}))
    assert installed_rf.verify_snapshots(live, receipt) == images
    for kind in ("flash", "sernum", "signature", "fuses"):
        path = live / f"sender-{kind}.bin"
        original = path.read_bytes()
        path.write_bytes(original[:-1])
        with pytest.raises(ValueError, match="Gateway"):
            installed_rf.verify_snapshots(live, receipt)
        path.write_bytes(original)


def test_lost_or_reset_legacy_monitor_cannot_trigger_data(tmp_path: Path) -> None:
    """Reset, previous-generation readiness, and monitor loss all block DATA."""
    proof = installed_rf.rf.ProofRun(tmp_path / "journal")
    capture = installed_rf.Capture(proof)
    process = SimpleNamespace(poll=lambda: None)
    capture.monitors["gateway"] = {"process": process}
    capture.generations["gateway"] = 2
    capture.record("gateway", "stdout", "[GATEWAY] RX_READY", 1)
    capture.ready_barriers.add(("gateway", 1))
    assert capture.fresh_lines("gateway", 0) == []
    with pytest.raises(OSError, match="fresh RX readiness"):
        capture.send("gateway", "S")

    capture.ready_barriers.add(("gateway", 2))
    capture.record("gateway", "stdout", "[GATEWAY] BOOT gateway", 2)
    assert ("gateway", 2) not in capture.ready_barriers
    with pytest.raises(OSError, match="reset"):
        capture.wait(lambda: True, 0)
    with pytest.raises(OSError, match="fresh RX readiness"):
        capture.send("gateway", "S")

    process.poll = lambda: 1
    with pytest.raises(OSError, match="disconnected"):
        capture.send("gateway", "S")


def test_post_rf_tracker_monitor_reopens_without_reissuing_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the intentional post-RF Tracker capture can recover a lost monitor."""
    capture = installed_rf.Capture(installed_rf.rf.ProofRun(tmp_path / "journal"))
    capture.generations["receiver"] = 2
    capture.after_rf.add(("receiver", 2))
    capture.monitors["receiver"] = {"process": SimpleNamespace(poll=lambda: 1)}
    capture.monitors["gateway"] = {"process": SimpleNamespace(poll=lambda: None)}

    def reconnect(role: str, *, after_rf: bool = False) -> None:
        assert (role, after_rf) == ("receiver", True)
        capture.generations[role] += 1
        capture.monitors[role] = {"process": SimpleNamespace(poll=lambda: None)}

    monkeypatch.setattr(capture, "connect", reconnect)
    monkeypatch.setattr(capture, "send", lambda *_: pytest.fail("unexpected command"))
    assert capture.wait(lambda: capture.generations["receiver"] == 3, 1, recover_tracker=True)
