"""Pytest specifications for explicit, bounded RF fault evidence."""

import json
import subprocess
import sys
from pathlib import Path


def _fault_bundle(
    root: Path,
    fault: str,
    lines: list[tuple[str, str]],
    payload_hex: str = "6869",
) -> Path:
    """Create a host-only captured transaction for a single injected fault."""
    root.mkdir()
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"run_id": "fault-fixture", "profile": "smoke", "seed": 11}))
    case = {
        "case_id": "case-00001",
        "direction": "gateway_to_tracker",
        "scenario": "fault_test",
        "fault": fault,
        "expected_result": "NACK_RETRY_ACK" if fault.startswith("FORCE_NACK") else "ACK",
        "session_id": 0x3536,
        "sequence": 1,
        "payload_hex": payload_hex,
        "payload_length_bytes": len(bytes.fromhex(payload_hex)),
        "maximum_retries": 4,
    }
    (root / "cases.jsonl").write_text(json.dumps(case) + "\n")
    with (root / "events.jsonl").open("w", encoding="utf-8") as stream:
        for role, line in lines:
            stream.write(json.dumps({"role": role, "stream": "stdout", "line": line}) + "\n")
    return manifest


def _run_replay(manifest: Path, output: Path) -> subprocess.CompletedProcess[str]:
    """Analyze the fixture using replay mode, which has no radio transport."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.rf_stress",
            "--replay",
            str(manifest),
            "--case-id",
            "case-00001",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_controlled_nack_retries_the_same_session_and_sequence(tmp_path: Path) -> None:
    """Require real NACK TX/RX, a same-sequence retry, and the final accepted ACK."""
    common = "SID=3536"
    lines = [
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=100 TYPE=8 Q=1 E=0"),
        ("tracker", f"[RECEIVER] NACK_TX_DONE {common} T=105 TYPE=9 Q=1 E=0"),
        ("gateway", f"[GATEWAY] NACK_RX {common} T=110 TYPE=9 Q=1 E=0"),
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=120 TYPE=8 Q=1 E=0"),
        (
            "tracker",
            f"[RECEIVER] DATA_VALIDATED {common} T=125 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869",
        ),
        ("tracker", f"[RECEIVER] ACK_TX_DONE {common} T=130 TYPE=3 Q=1 E=0"),
        ("gateway", f"[GATEWAY] ACK_ACCEPTED {common} T=135 TYPE=3 Q=1 E=0"),
    ]
    manifest = _fault_bundle(tmp_path / "source", "FORCE_NACK_ONCE", lines)

    completed = _run_replay(manifest, tmp_path / "replay")

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert summary["status"] == "PASS"
    assert summary["retries"] == 1


def test_duplicate_is_not_passed_without_single_delivery_evidence(tmp_path: Path) -> None:
    """Require duplicate suppression evidence before accepting a replay test result."""
    common = "SID=3536"
    lines = [
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=100 TYPE=8 Q=1 E=0"),
        (
            "tracker",
            f"[RECEIVER] DATA_VALIDATED {common} T=105 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869",
        ),
        ("tracker", f"[RECEIVER] ACK_TX_DONE {common} T=110 TYPE=3 Q=1 E=0"),
        ("gateway", f"[GATEWAY] ACK_ACCEPTED {common} T=115 TYPE=3 Q=1 E=0"),
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=120 TYPE=8 Q=1 E=0"),
        ("tracker", f"[RECEIVER] DUPLICATE_IGNORED {common} T=125 TYPE=8 Q=1 DELIVERY_COUNT=1 E=0"),
        ("tracker", f"[RECEIVER] ACK_TX_DONE {common} T=130 TYPE=3 Q=1 E=0"),
        ("gateway", f"[GATEWAY] ACK_ACCEPTED {common} T=135 TYPE=3 Q=1 E=0"),
    ]
    manifest = _fault_bundle(tmp_path / "source", "DUPLICATE_DATA", lines)

    completed = _run_replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode == 0, completed.stderr
    assert summary["status"] == "PASS"
    assert summary["duplicate_deliveries"] == 0


def test_two_controlled_nacks_preserve_session_and_sequence(tmp_path: Path) -> None:
    """Require both NACKs, two same-sequence retries and the terminal ACK."""
    common = "SID=3536"
    lines = [
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=100 TYPE=8 Q=1 E=0"),
        ("tracker", f"[RECEIVER] NACK_TX_DONE {common} T=105 TYPE=9 Q=1 E=0"),
        ("gateway", f"[GATEWAY] NACK_RX {common} T=110 TYPE=9 Q=1 E=0"),
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=120 TYPE=8 Q=1 E=0"),
        ("tracker", f"[RECEIVER] NACK_TX_DONE {common} T=125 TYPE=9 Q=1 E=0"),
        ("gateway", f"[GATEWAY] NACK_RX {common} T=130 TYPE=9 Q=1 E=0"),
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=140 TYPE=8 Q=1 E=0"),
        ("tracker", f"[RECEIVER] DATA_VALIDATED {common} T=145 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869"),
        ("tracker", f"[RECEIVER] ACK_TX_DONE {common} T=150 TYPE=3 Q=1 E=0"),
        ("gateway", f"[GATEWAY] ACK_ACCEPTED {common} T=155 TYPE=3 Q=1 E=0"),
    ]
    manifest = _fault_bundle(tmp_path / "source", "FORCE_NACK_TWICE", lines)

    completed = _run_replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode == 0, completed.stderr
    assert summary["status"] == "PASS"
    assert summary["retries"] == 2


def test_invalid_application_payload_requires_a_real_nack(tmp_path: Path) -> None:
    """Require exact rejected bytes plus matching NACK TX/RX for invalid application data."""
    common = "SID=3536"
    rejected_payload_line = (
        f"[RECEIVER] DATA_REJECTED {common} T=105 TYPE=8 Q=1 E=0 PAYLOAD_HEX=57726f6e6720576f726c64"
    )
    lines = [
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=100 TYPE=8 Q=1 E=0"),
        ("tracker", rejected_payload_line),
        ("tracker", f"[RECEIVER] NACK_TX_DONE {common} T=110 TYPE=9 Q=1 E=0"),
        ("gateway", f"[GATEWAY] NACK_RX {common} T=115 TYPE=9 Q=1 E=0"),
    ]
    manifest = _fault_bundle(
        tmp_path / "source",
        "INVALID_APP_PAYLOAD",
        lines,
        payload_hex="57726f6e6720576f726c64",
    )

    completed = _run_replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode == 0, completed.stderr
    assert summary["status"] == "PASS"


def test_crc_rejection_uses_timeout_recovery_without_application_nack(tmp_path: Path) -> None:
    """Classify a PHY CRC error as timeout recovery, with no invented application NACK."""
    case_lines = [
        ("gateway", "[GATEWAY] DATA_TX_DONE SID=3536 T=100 TYPE=8 Q=1 E=0"),
        ("tracker", "[RECEIVER] CRC_ERROR SID=3536 T=105 TYPE=8 Q=1 E=0 IRQ_FLAGS=32"),
        ("gateway", "[GATEWAY] TIMEOUT SID=3536 T=110 Q=1 E=0"),
    ]
    manifest = _fault_bundle(tmp_path / "source", "PHY_CRC_CORRUPT", case_lines)

    completed = _run_replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode == 0, completed.stderr
    assert summary["status"] == "PASS"
    assert summary["timeouts"] == 1
    assert summary["irq_flags_seen"] == [32]


def test_sequence_rollover_accepts_255_then_zero_in_one_session(tmp_path: Path) -> None:
    """Verify both payloads and ACKs across the 8-bit sequence boundary."""
    common = "SID=3536"
    case = {
        "case_id": "case-00001",
        "direction": "gateway_to_tracker",
        "fault": "SEQUENCE_ROLLOVER",
        "session_id": 0x3536,
        "sequence": 255,
        "expected_sequences": [255, 0],
        "payloads_hex": ["52", "30"],
        "maximum_retries": 4,
    }
    lines = [
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=100 TYPE=8 Q=255 E=0"),
        ("tracker", f"[RECEIVER] DATA_VALIDATED {common} T=105 TYPE=8 Q=255 E=0 PAYLOAD_HEX=52"),
        ("tracker", f"[RECEIVER] ACK_TX_DONE {common} T=110 TYPE=3 Q=255 E=0"),
        ("gateway", f"[GATEWAY] ACK_ACCEPTED {common} T=115 TYPE=3 Q=255 E=0"),
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=120 TYPE=8 Q=0 E=0"),
        ("tracker", f"[RECEIVER] DATA_VALIDATED {common} T=125 TYPE=8 Q=0 E=0 PAYLOAD_HEX=30"),
        ("tracker", f"[RECEIVER] ACK_TX_DONE {common} T=130 TYPE=3 Q=0 E=0"),
        ("gateway", f"[GATEWAY] ACK_ACCEPTED {common} T=135 TYPE=3 Q=0 E=0"),
    ]
    manifest = _fault_bundle(tmp_path / "source", "SEQUENCE_ROLLOVER", lines)
    source_case = json.loads((manifest.parent / "cases.jsonl").read_text())
    source_case.update(case)
    (manifest.parent / "cases.jsonl").write_text(json.dumps(source_case) + "\n")

    completed = _run_replay(manifest, tmp_path / "replay")

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert summary["status"] == "PASS"


def test_receiver_reset_case_needs_reset_and_rx_rearm_evidence(tmp_path: Path) -> None:
    """Do not treat a normal exchange as proof that reset recovery was exercised."""
    common = "SID=3536"
    lines = [
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=100 TYPE=8 Q=1 E=0"),
        ("tracker", f"[RECEIVER] DATA_VALIDATED {common} T=105 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869"),
        ("tracker", f"[RECEIVER] ACK_TX_DONE {common} T=110 TYPE=3 Q=1 E=0"),
        ("gateway", f"[GATEWAY] ACK_ACCEPTED {common} T=115 TYPE=3 Q=1 E=0"),
    ]
    manifest = _fault_bundle(tmp_path / "source", "RECEIVER_RESET", lines)

    completed = _run_replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode != 0
    assert summary["status"] == "UNVERIFIED"


def test_receiver_reset_recovery_requires_rx_ready_and_final_ack(tmp_path: Path) -> None:
    """Pass a reset recovery only after the receiver rearms and accepts the retried DATA."""
    common = "SID=3536"
    lines = [
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=90 TYPE=8 Q=1 E=0"),
        ("tracker", f"[RECEIVER] RESET {common} T=100 E=0"),
        ("tracker", f"[RECEIVER] RX_READY {common} T=105 E=0"),
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=110 TYPE=8 Q=1 E=0"),
        ("tracker", f"[RECEIVER] DATA_VALIDATED {common} T=115 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869"),
        ("tracker", f"[RECEIVER] ACK_TX_DONE {common} T=120 TYPE=3 Q=1 E=0"),
        ("gateway", f"[GATEWAY] ACK_ACCEPTED {common} T=125 TYPE=3 Q=1 E=0"),
    ]
    manifest = _fault_bundle(tmp_path / "source", "RECEIVER_RESET", lines)

    completed = _run_replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode == 0, completed.stderr
    assert summary["status"] == "PASS"
    assert summary["reset_count"] == 1


def test_cancel_fault_is_not_passed_by_a_normal_ack_exchange(tmp_path: Path) -> None:
    """Require cancellation, park and port-release evidence for the cancellation case."""
    common = "SID=3536"
    lines = [
        ("gateway", f"[GATEWAY] DATA_TX_DONE {common} T=100 TYPE=8 Q=1 E=0"),
        ("tracker", f"[RECEIVER] DATA_VALIDATED {common} T=105 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869"),
        ("tracker", f"[RECEIVER] ACK_TX_DONE {common} T=110 TYPE=3 Q=1 E=0"),
        ("gateway", f"[GATEWAY] ACK_ACCEPTED {common} T=115 TYPE=3 Q=1 E=0"),
    ]
    manifest = _fault_bundle(tmp_path / "source", "CANCEL_UNDER_LOAD", lines)

    completed = _run_replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode != 0
    assert summary["status"] == "UNVERIFIED"


def test_cancel_is_passed_only_after_both_radios_park_and_ports_release(tmp_path: Path) -> None:
    """Verify cancellation evidence includes terminal park and adapter release for both roles."""
    lines = [
        ("gateway", "[GATEWAY] DATA_TX_DONE SID=3536 T=100 TYPE=8 Q=1 E=0"),
    ]
    manifest = _fault_bundle(tmp_path / "source", "CANCEL_UNDER_LOAD", lines)
    journal = manifest.parent / "events.jsonl"
    rows = [json.loads(line) for line in journal.read_text().splitlines()]
    rows += [
        {
            "role": "gateway",
            "stream": "control",
            "line": "CANCEL_REQUESTED case-00001",
            "received_monotonic_ns": 110,
        },
        {"role": "gateway", "stream": "stdout", "line": "[GATEWAY] PARKED E=0"},
        {"role": "receiver", "stream": "stdout", "line": "[RECEIVER] PARKED E=0"},
        {"role": "gateway", "stream": "port_release", "line": "PORT_RELEASED"},
        {"role": "receiver", "stream": "port_release", "line": "PORT_RELEASED"},
    ]
    journal.write_text("".join(json.dumps(row) + "\n" for row in rows))

    completed = _run_replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode == 0, completed.stderr
    assert summary["status"] == "PASS"


def test_cancel_requires_park_after_the_cancel_request(tmp_path: Path) -> None:
    """Reject stale parked events that occurred before cancellation was requested."""
    manifest = _fault_bundle(
        tmp_path / "source",
        "CANCEL_UNDER_LOAD",
        [
            ("gateway", "[GATEWAY] DATA_TX_DONE SID=3536 T=100 TYPE=8 Q=1 E=0"),
            ("gateway", "[GATEWAY] PARKED E=0"),
            ("receiver", "[RECEIVER] PARKED E=0"),
        ],
    )
    journal = manifest.parent / "events.jsonl"
    rows = [json.loads(line) for line in journal.read_text().splitlines()]
    rows += [
        {
            "role": "gateway",
            "stream": "control",
            "line": "CANCEL_REQUESTED case-00001",
            "received_monotonic_ns": 110,
        },
        {"role": "gateway", "stream": "port_release", "line": "PORT_RELEASED"},
        {"role": "receiver", "stream": "port_release", "line": "PORT_RELEASED"},
    ]
    journal.write_text("".join(json.dumps(row) + "\n" for row in rows))

    completed = _run_replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode != 0
    assert summary["status"] == "UNVERIFIED"
