import csv

import pytest

from updi_rca.reporting import (
    EVENT_COLUMNS,
    RUN_COLUMNS,
    append_run_csv,
    render_summary,
    write_csv,
)


def test_run_csv_appends_with_the_contract_header(tmp_path):
    path = tmp_path / "runs.csv"
    row = {column: "" for column in RUN_COLUMNS}
    row.update(run_id="r1", lane="A", result="fail", failure_stage="ACC_DATA_RESPONSE")

    append_run_csv(path, row)
    append_run_csv(path, {**row, "run_id": "r2"})

    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert tuple(rows[0]) == RUN_COLUMNS
    assert [item["run_id"] for item in rows] == ["r1", "r2"]


def test_csv_writer_rejects_a_header_mismatch(tmp_path):
    path = tmp_path / "events.csv"
    write_csv(path, EVENT_COLUMNS, [])
    path.write_text("wrong,header\n")
    with pytest.raises(ValueError, match="header mismatch"):
        write_csv(path, EVENT_COLUMNS, [])


def test_summary_contains_sample_size_rates_and_wilson_interval():
    text = render_summary({
        "attempts": 60,
        "successes": 41,
        "failures": 19,
        "success_rate": 41 / 60,
        "failure_rate": 19 / 60,
        "wilson_95": (0.54, 0.79),
        "median_latency_ms": 2.5,
        "p95_latency_ms": 4.0,
    }, title="LDS unheld")
    assert "LDS unheld" in text
    assert "N = 60" in text
    assert "31.7%" in text
    assert "Wilson 95%" in text
