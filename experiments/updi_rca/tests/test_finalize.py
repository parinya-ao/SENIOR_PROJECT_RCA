import hashlib
from pathlib import Path

from updi_rca.finalize import (
    canonical_attempt_paths,
    classify_raw_event,
    protocol_event_rows,
    _run_row,
    _source_hash_summary,
    summarize_flag_rx_attempts,
    translate_hypothesis_text,
)


def test_protocol_event_stages_remain_distinct():
    assert classify_raw_event({"kind": "tx"}) == ("HOST_TX", "HOST_TO_TARGET")
    assert classify_raw_event({"kind": "echo"}) == ("LOCAL_ECHO", "TARGET_TO_HOST")
    assert classify_raw_event({"kind": "response", "stage": "UPDI_CONTROL_RESPONSE"}) == (
        "UPDI_CONTROL_RESPONSE",
        "TARGET_TO_HOST",
    )


def test_canonical_attempt_selector_excludes_uncommissioned_extra(tmp_path: Path):
    for lane, run_id in (
        ("lane_a", "baseline-20261026T171644Z-1a031f37"),
        ("lane_b", "baseline-20261026T171633Z-88c741a8"),
    ):
        for test_id in ("sib", "control"):
            root = tmp_path / lane / test_id
            root.mkdir(parents=True)
            for attempt in range(1, 102):
                (root / f"{run_id}-{test_id}-{attempt:04}.json").touch()

    selected = canonical_attempt_paths(tmp_path)

    assert len(selected[("lane_a", "sib")]) == 100
    assert selected[("lane_a", "sib")][-1].name.endswith("-0100.json")


def test_seed_hypothesis_cause_labels_are_translated_to_english():
    label = translate_hypothesis_text("H003", "VDD/GND pin ของ AVR ตัวใดตัวหนึ่งไม่ contact")

    assert label == "One AVR VDD/GND pin has poor or no contact"
    assert not any("\u0e00" <= char <= "\u0e7f" for char in label)


def test_protocol_event_rows_preserve_exact_echo_then_acc_response(tmp_path: Path):
    log = tmp_path / "flag-read.json"
    item = {"address": 30, "events": [
        {"kind": "tx", "ns": 1, "hex": "55001e", "count": 3, "baud": 38400},
        {"kind": "echo", "ns": 2, "hex": "55001e", "requested": 3, "baud": 38400},
        {"kind": "response", "ns": 3, "hex": "03", "requested": 1,
         "baud": 38400, "stage": "ACC_DATA_RESPONSE"},
    ]}

    rows = protocol_event_rows(
        run_id="flag-read-1", lane="lane_a", board_id="UNKNOWN_TARGET_LANE_A",
        source_log="evidence/raw/flag-read.json", test_id="flag_rx_read_0x1e", item=item,
    )

    assert [row["stage"] for row in rows] == ["HOST_TX", "LOCAL_ECHO", "ACC_DATA_RESPONSE"]
    assert rows[1]["classification"] == "EXACT_ECHO"
    assert rows[2]["response_hex"] == "03"


def test_flag_rx_summary_counts_bit_state_separately_from_read_success():
    attempts = [
        {"exit": 0, "latency_ms": 10.0, "values": {"LDS 1e": 0x03}},
        {"exit": 0, "latency_ms": 12.0, "values": {"LDS 1e": 0x01}},
        {"exit": 1, "latency_ms": 20.0, "failure_stage": "ACC_DATA_RESPONSE", "values": {}},
    ]

    summary = summarize_flag_rx_attempts(attempts)

    assert summary["metrics"]["successes"] == 2
    assert summary["metrics"]["failures"] == 1
    assert summary["value_counts"] == {0x01: 1, 0x03: 1}
    assert summary["flag_rx_set"] == 1
    assert summary["flag_enable_set"] == 2


def test_run_row_accepts_legacy_record_without_numeric_address(tmp_path: Path):
    source = tmp_path / "evidence" / "raw" / "legacy.json"
    source.parent.mkdir(parents=True)
    source.write_text("{}", encoding="utf-8")

    row = _run_row(
        tmp_path, source, "UNKNOWN", "legacy", {"address": None, "exit": 0, "values": {}}, 1
    )

    assert row["result"] == "PASS"
    assert row["observed_hex"] == ""


def test_source_hash_summary_checks_each_run_source(tmp_path: Path):
    source = tmp_path / "evidence" / "raw" / "probe.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"raw probe")
    row = {"source_log": "evidence/raw/probe.json", "raw_sha256": hashlib.sha256(b"raw probe").hexdigest()}

    assert _source_hash_summary(tmp_path, [row]) == (1, 0)
    source.write_bytes(b"changed")
    assert _source_hash_summary(tmp_path, [row]) == (1, 1)
