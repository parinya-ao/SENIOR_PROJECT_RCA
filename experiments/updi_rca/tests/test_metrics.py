import pytest

from updi_rca.metrics import metric_summary, wilson_interval


def test_summary_reports_counts_rates_latency_and_wilson_interval():
    summary = metric_summary([
        {"success": True, "latency_ms": 1, "failure_stage": "PASS"},
        {"success": True, "latency_ms": 2, "failure_stage": "PASS"},
        {"success": False, "latency_ms": 3, "failure_stage": "ACC_DATA_RESPONSE"},
        {"success": True, "latency_ms": 4, "failure_stage": "PASS"},
        {"success": True, "latency_ms": 5, "failure_stage": "PASS"},
    ])

    assert summary["attempts"] == 5
    assert summary["successes"] == 4
    assert summary["failures"] == 1
    assert summary["success_rate"] == 0.8
    assert summary["failure_rate"] == 0.2
    assert summary["median_latency_ms"] == 3
    assert summary["p95_latency_ms"] == 5
    assert summary["failure_stages"] == {"ACC_DATA_RESPONSE": 1}
    assert summary["wilson_95"] == pytest.approx(wilson_interval(4, 5))


def test_wilson_interval_handles_zero_and_full_success_without_zero_width():
    lo_zero, hi_zero = wilson_interval(0, 10)
    lo_full, hi_full = wilson_interval(10, 10)
    assert lo_zero == 0
    assert hi_zero > 0
    assert lo_full < 1
    assert hi_full == 1


def test_invalid_wilson_inputs_are_rejected():
    with pytest.raises(ValueError):
        wilson_interval(0, 0)
    with pytest.raises(ValueError):
        wilson_interval(4, 3)
