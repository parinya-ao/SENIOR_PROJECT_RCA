"""Pytest specifications for evidence-only replay of recorded RF transactions."""

import json
import subprocess
import sys
from pathlib import Path


def _write_replay_bundle(root: Path, receiver_line: str) -> Path:
    """Write a scripted host fixture with a single Gateway DATA/ACK exchange."""
    root.mkdir()
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"run_id": "fixture", "profile": "smoke", "seed": 7}))
    case = {
        "case_id": "case-00001",
        "direction": "gateway_to_tracker",
        "scenario": "single_payload",
        "fault": "NO_FAULT",
        "expected_result": "ACK",
        "session_id": 0x3536,
        "sequence": 1,
        "payload_hex": "6869",
        "payload_length_bytes": 2,
    }
    (root / "cases.jsonl").write_text(json.dumps(case) + "\n")
    events = (
        ("gateway", "[GATEWAY] DATA_TX_DONE SID=3536 T=100 TYPE=8 Q=1 E=0"),
        ("tracker", receiver_line),
        ("tracker", "[RECEIVER] ACK_TX_DONE SID=3536 T=115 TYPE=3 Q=1 E=0"),
        ("gateway", "[GATEWAY] ACK_ACCEPTED SID=3536 T=120 TYPE=3 Q=1 E=0"),
    )
    with (root / "events.jsonl").open("w", encoding="utf-8") as stream:
        for role, line in events:
            stream.write(json.dumps({"role": role, "stream": "stdout", "line": line}) + "\n")
    return manifest


def _replay(manifest: Path, output: Path) -> subprocess.CompletedProcess[str]:
    """Replay captured events through the public offline-only CLI."""
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


def test_replay_pass_requires_matching_two_sided_payload_and_ack(tmp_path: Path) -> None:
    """Accept a transaction only with exact receiver bytes and matching ACK evidence."""
    manifest = _write_replay_bundle(
        tmp_path / "source",
        "[RECEIVER] DATA_VALIDATED SID=3536 T=110 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869",
    )

    completed = _replay(manifest, tmp_path / "replay")

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert summary["status"] == "PASS"
    assert summary["payload_mismatches"] == 0
    assert summary["rf_transmissions"] == 0


def test_replay_without_receiver_payload_bytes_is_unverified(tmp_path: Path) -> None:
    """Do not infer byte integrity from a generic DATA_VALIDATED event."""
    manifest = _write_replay_bundle(
        tmp_path / "source",
        "[RECEIVER] DATA_VALIDATED SID=3536 T=110 TYPE=8 Q=1 E=0",
    )

    completed = _replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode != 0
    assert summary["status"] == "UNVERIFIED"


def test_replay_rejects_payload_mismatch(tmp_path: Path) -> None:
    """Classify observed bytes that differ from the generated application data as failure."""
    manifest = _write_replay_bundle(
        tmp_path / "source",
        "[RECEIVER] DATA_VALIDATED SID=3536 T=110 TYPE=8 Q=1 E=0 PAYLOAD_HEX=686a",
    )

    completed = _replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode != 0
    assert summary["status"] == "FAIL"
    assert summary["payload_mismatches"] == 1


def test_nonzero_radio_status_code_is_reported_as_failure(tmp_path: Path) -> None:
    """Keep RadioLib status errors visible in the transaction result and metrics."""
    manifest = _write_replay_bundle(
        tmp_path / "source",
        "[RECEIVER] DATA_VALIDATED SID=3536 T=110 TYPE=8 Q=1 E=0 PAYLOAD_HEX=6869",
    )
    journal = manifest.parent / "events.jsonl"
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    events[-1]["line"] = "[GATEWAY] ACK_ACCEPTED SID=3536 T=120 TYPE=3 Q=1 E=7"
    journal.write_text("".join(json.dumps(event) + "\n" for event in events))

    completed = _replay(manifest, tmp_path / "replay")

    summary = json.loads((tmp_path / "replay" / "summary.json").read_text())
    assert completed.returncode != 0
    assert summary["status"] == "FAIL"
    assert summary["radio_error_codes"] == [7]
