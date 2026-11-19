"""Host checks for active project configuration and non-radio dry runs."""

import json
from pathlib import Path

import pytest

from tools.lora_chat.cli import _create_run_directory
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
    path = tmp_path / "lora_system.json"
    path.write_text(
        json.dumps(
            {
                "experiment": {
                    "mode": "single_packet",
                    "radio_inventory": None,
                    "antenna_inventory": None,
                },
                "protocol": {
                    "encoding": "existing_radio_header",
                    "payload": "hello world",
                    "data_type": True,
                    "ack_type": 3,
                    "nack_type": 9,
                    "sequence": 1,
                    "sender_address": 0,
                    "receiver_address": 1,
                },
                "retries": {"max_retries": 3},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(TypeError, match="data_type"):
        load_bench_profile(path)


def test_dry_run_creates_empty_event_log_and_disables_transmission(tmp_path: Path) -> None:
    """Dry run never fabricates hardware events or opens a serial transport."""
    profile = load_bench_profile()
    run_dir = tmp_path / "run"
    transport = BenchTransport(
        run_dir,
        profile,
        authorize_rf_test=False,
        dry_run=True,
    )
    rows, offset = transport.events_since(0)

    assert rows == []
    assert offset == 0
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == ""
    assert "dry-run" in (transport.transmit_blocker() or "")
    assert transport.close()


def test_rf_authorization_still_blocks_when_inventory_is_unresolved(tmp_path: Path) -> None:
    """An explicit RF flag cannot override missing project inventory facts."""
    profile = load_bench_profile()
    transport = BenchTransport(
        tmp_path / "run",
        profile,
        authorize_rf_test=True,
    )
    assert "radio_inventory and antenna_inventory" in (transport.transmit_blocker() or "")
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
        authorize_rf_test=False,
        dry_run=True,
    )
    assert run_dir.is_dir()
    assert transport.close()
