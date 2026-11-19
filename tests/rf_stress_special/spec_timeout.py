"""Pytest specifications for bounded timeout recovery and ACK rejection evidence."""

import json
import subprocess
import sys
from pathlib import Path


def _write_bundle(root: Path, case: dict[str, object], lines: list[tuple[str, str]]) -> Path:
    """Write a one-case host capture bundle for offline event assessment."""
    root.mkdir()
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"run_id": "timeout-fixture", "profile": "smoke", "seed": 17}))
    (root / "cases.jsonl").write_text(json.dumps(case) + "\n")
    with (root / "events.jsonl").open("w", encoding="utf-8") as stream:
        for role, line in lines:
            stream.write(json.dumps({"role": role, "stream": "stdout", "line": line}) + "\n")
    return manifest


def _replay(manifest: Path, output: Path) -> subprocess.CompletedProcess[str]:
    """Analyze recorded events without opening the hardware transport."""
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


def test_gateway_accepting_wrong_sequence_is_a_false_ack_failure(tmp_path: Path) -> None:
    """Fail if the Gateway logs ACK_ACCEPTED for a sequence other than the DATA sequence."""
    case = {
        "case_id": "case-00001",
        "direction": "gateway_to_tracker",
        "fault": "WRONG_SEQUENCE",
        "session_id": 0x3536,
        "sequence": 1,
        "payload_hex": "6869",
        "maximum_retries": 4,
    }
    lines = [
        ("gateway", "[GATEWAY] DATA_TX_DONE SID=3536 T=100 TYPE=8 Q=1 E=0"),
        ("tracker", "[RECEIVER] DATA_VALIDATED SID=3536 T=105 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869"),
        ("tracker", "[RECEIVER] ACK_TX_DONE SID=3536 T=110 TYPE=3 Q=1 E=0"),
        ("gateway", "[GATEWAY] ACK_ACCEPTED SID=3536 T=115 TYPE=3 Q=2 E=0"),
    ]
    manifest = _write_bundle(tmp_path / "source", case, lines)

    completed = _replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode != 0
    assert summary["status"] == "FAIL"
    assert summary["false_ack_acceptance"] == 1


def test_timeout_recovery_keeps_the_same_session_and_sequence(tmp_path: Path) -> None:
    """Count a timeout retry as recovered only after the matching ACK is accepted."""
    case = {
        "case_id": "case-00001",
        "direction": "gateway_to_tracker",
        "fault": "NO_FAULT",
        "session_id": 0x3536,
        "sequence": 1,
        "payload_hex": "6869",
        "maximum_retries": 2,
    }
    lines = [
        ("gateway", "[GATEWAY] DATA_TX_DONE SID=3536 T=100 TYPE=8 Q=1 E=0"),
        ("gateway", "[GATEWAY] TIMEOUT SID=3536 T=110 Q=1 E=0"),
        ("gateway", "[GATEWAY] DATA_TX_DONE SID=3536 T=120 TYPE=8 Q=1 E=0"),
        ("tracker", "[RECEIVER] DATA_VALIDATED SID=3536 T=125 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869"),
        ("tracker", "[RECEIVER] ACK_TX_DONE SID=3536 T=130 TYPE=3 Q=1 E=0"),
        ("gateway", "[GATEWAY] ACK_ACCEPTED SID=3536 T=140 TYPE=3 Q=1 E=0"),
    ]
    manifest = _write_bundle(tmp_path / "source", case, lines)

    completed = _replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode == 0, completed.stderr
    assert summary["status"] == "PASS"
    assert summary["retries"] == 1
    assert summary["timeouts"] == 1
    assert summary["latency_p50_ms"] == 40


def test_retry_limit_excess_is_a_failure(tmp_path: Path) -> None:
    """Fail when the captured sender exceeds the protocol retry bound."""
    case = {
        "case_id": "case-00001",
        "direction": "gateway_to_tracker",
        "fault": "NO_FAULT",
        "session_id": 0x3536,
        "sequence": 1,
        "payload_hex": "6869",
        "maximum_retries": 2,
    }
    lines = [
        ("gateway", f"[GATEWAY] DATA_TX_DONE SID=3536 T={tick} TYPE=8 Q=1 E=0")
        for tick in (100, 110, 120, 130)
    ]
    manifest = _write_bundle(tmp_path / "source", case, lines)

    completed = _replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode != 0
    assert summary["status"] == "FAIL"


def test_latency_wraps_the_same_device_millisecond_counter(tmp_path: Path) -> None:
    """Calculate latency across 32-bit uptime wrap using Gateway timestamps only."""
    case = {
        "case_id": "case-00001",
        "direction": "gateway_to_tracker",
        "fault": "NO_FAULT",
        "session_id": 0x3536,
        "sequence": 1,
        "payload_hex": "6869",
        "maximum_retries": 2,
    }
    lines = [
        ("gateway", "[GATEWAY] DATA_TX_DONE SID=3536 T=4294967290 TYPE=8 Q=1 E=0"),
        ("tracker", "[RECEIVER] DATA_VALIDATED SID=3536 T=900 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869"),
        ("tracker", "[RECEIVER] ACK_TX_DONE SID=3536 T=905 TYPE=3 Q=1 E=0"),
        ("gateway", "[GATEWAY] ACK_ACCEPTED SID=3536 T=5 TYPE=3 Q=1 E=0"),
    ]
    manifest = _write_bundle(tmp_path / "source", case, lines)

    completed = _replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode == 0, completed.stderr
    assert summary["latency_p50_ms"] == 11


def test_wrong_sequence_is_explicitly_rejected_before_correct_ack(tmp_path: Path) -> None:
    """Require a rejected stale sequence and a later valid ACK for the DATA sequence."""
    case = {
        "case_id": "case-00001",
        "direction": "gateway_to_tracker",
        "fault": "WRONG_SEQUENCE",
        "session_id": 0x3536,
        "sequence": 1,
        "payload_hex": "6869",
        "maximum_retries": 2,
    }
    lines = [
        ("gateway", "[GATEWAY] DATA_TX_DONE SID=3536 T=100 TYPE=8 Q=1 E=0"),
        ("tracker", "[RECEIVER] DATA_VALIDATED SID=3536 T=105 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869"),
        ("gateway", "[GATEWAY] ACK_REJECTED SID=3536 T=110 TYPE=3 Q=1 GOT_Q=2 E=0"),
        ("tracker", "[RECEIVER] ACK_TX_DONE SID=3536 T=115 TYPE=3 Q=1 E=0"),
        ("gateway", "[GATEWAY] ACK_ACCEPTED SID=3536 T=120 TYPE=3 Q=1 E=0"),
    ]
    manifest = _write_bundle(tmp_path / "source", case, lines)

    completed = _replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode == 0, completed.stderr
    assert summary["status"] == "PASS"


def test_wrong_campaign_is_explicitly_rejected(tmp_path: Path) -> None:
    """Require a mismatched campaign rejection before accepting the current transaction."""
    case = {
        "case_id": "case-00001",
        "direction": "gateway_to_tracker",
        "fault": "WRONG_CAMPAIGN",
        "session_id": 0x3536,
        "sequence": 1,
        "payload_hex": "6869",
        "maximum_retries": 2,
    }
    lines = [
        ("gateway", "[GATEWAY] DATA_TX_DONE SID=3536 T=100 TYPE=8 Q=1 E=0"),
        ("tracker", "[RECEIVER] DATA_VALIDATED SID=3536 T=105 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869"),
        ("gateway", "[GATEWAY] ACK_REJECTED SID=3536 T=110 TYPE=3 Q=1 GOT_SID=3537 E=0"),
        ("tracker", "[RECEIVER] ACK_TX_DONE SID=3536 T=115 TYPE=3 Q=1 E=0"),
        ("gateway", "[GATEWAY] ACK_ACCEPTED SID=3536 T=120 TYPE=3 Q=1 E=0"),
    ]
    manifest = _write_bundle(tmp_path / "source", case, lines)

    completed = _replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode == 0, completed.stderr
    assert summary["status"] == "PASS"


def test_wrong_destination_must_be_ignored_until_timeout(tmp_path: Path) -> None:
    """Pass a wrong-destination case only with no receiver acceptance and a bounded timeout."""
    case = {
        "case_id": "case-00001",
        "direction": "gateway_to_tracker",
        "fault": "WRONG_DESTINATION",
        "session_id": 0x3536,
        "sequence": 1,
        "payload_hex": "6869",
        "maximum_retries": 2,
    }
    lines = [
        ("gateway", "[GATEWAY] DATA_TX_DONE SID=3536 T=100 TYPE=8 Q=1 E=0"),
        ("gateway", "[GATEWAY] TIMEOUT SID=3536 T=110 Q=1 E=0"),
    ]
    manifest = _write_bundle(tmp_path / "source", case, lines)

    completed = _replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode == 0, completed.stderr
    assert summary["status"] == "PASS"
