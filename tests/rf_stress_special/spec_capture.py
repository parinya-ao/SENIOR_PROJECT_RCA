"""Pytest specifications for retaining unexpected failures outside planned trials."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import installed_rf


def test_unplanned_transaction_failure_is_retained_in_run_summary() -> None:
    """Keep a preflight TRANSACTION_FAILED event visible when its campaign was not planned."""
    collect = getattr(installed_rf, "unplanned_transaction_failures", None)
    assert callable(collect), "installed RF capture must expose unplanned failure events"
    lines = [
        "[GATEWAY] DATA_TX_DONE SID=3531 T=100 TYPE=8 Q=1 E=0",
        "[GATEWAY] TRANSACTION_FAILED SID=3530 T=90 TYPE=0 Q=0 E=-24",
        "[GATEWAY] ACK_ACCEPTED SID=3531 T=140 TYPE=3 Q=1 E=0",
    ]

    failures = collect(lines, {"3531"})

    assert failures == [lines[1]]


def test_planned_transaction_failure_is_not_counted_as_background() -> None:
    """Keep a failed in-plan campaign separate for its transaction assessor."""
    collect = getattr(installed_rf, "unplanned_transaction_failures", None)
    assert callable(collect), "installed RF capture must expose unplanned failure events"
    line = "[GATEWAY] TRANSACTION_FAILED SID=3531 T=140 TYPE=8 Q=1 E=-24"

    assert collect([line], {"3531"}) == []


def test_capture_metrics_preserve_radio_errors_irq_and_missing_rf_metrics() -> None:
    """Count emitted status/IRQ fields and leave absent RF measurements unreported."""
    summarize = getattr(installed_rf, "capture_diagnostics", None)
    assert callable(summarize), "installed RF capture must summarize observed diagnostics"
    lines = [
        "[GATEWAY] DATA_TX_DONE SID=3531 T=100 TYPE=8 Q=1 E=0",
        "[RECEIVER] RX_DISCARD SID=0 T=101 TYPE=0 Q=0 E=-7 IRQ_FLAGS=0x20",
        "[GATEWAY] TRANSACTION_FAILED SID=3530 T=90 TYPE=0 Q=0 E=-24",
    ]

    result = summarize(lines)

    assert result["radio_error_counts"] == {"-24": 1, "-7": 1, "0": 1}
    assert result["irq_flags_seen"] == [32]
    assert result["rssi_dbm"] is None
    assert result["snr_db"] is None
    assert result["airtime_us"] is None


def test_capture_phase_distinguishes_reopened_buffer_from_post_ready_events() -> None:
    """Label reopened buffered output, pre-ready lines, and post-ready live lines separately."""
    classify = getattr(installed_rf, "capture_event_phase", None)
    assert callable(classify), "capture must classify event provenance around readiness barriers"

    assert classify(after_rf_reopen=True, ready_barrier_seen=False) == "buffered_after_rf_reopen"
    assert classify(after_rf_reopen=False, ready_barrier_seen=False) == "unclassified_before_ready"
    assert classify(after_rf_reopen=True, ready_barrier_seen=True) == "live_after_ready_barrier"


def test_capture_journal_marks_buffered_lines_until_a_fresh_readiness_barrier(
    tmp_path: Path,
) -> None:
    """Keep late Tracker output marked buffered until RX_READY on its new connection."""
    capture = installed_rf.Capture(SimpleNamespace(run_dir=tmp_path))
    capture.generations["receiver"] = 2
    capture.after_rf.add(("receiver", 2))
    capture.record("receiver", "stdout", "[RECEIVER] DATA_VALIDATED SID=3536", 2)
    capture.ready_barriers.add(("receiver", 2))
    capture.record("receiver", "stdout", "[RECEIVER] RX_READY", 2)

    rows = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]

    assert rows[0]["delivery"] == "after_rf_reopen"
    assert rows[0]["phase"] == "buffered_after_rf_reopen"
    assert rows[1]["phase"] == "live_after_ready_barrier"
