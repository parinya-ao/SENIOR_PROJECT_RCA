"""Read-only acceptance checks for the completed RCA_FRESH_01 checkpoint."""
import csv
import json
from pathlib import Path
import sys

from updi_rca.fresh import (
    EPOCH, control_allowed, discover_serial_ports, needs_untouched_repeats,
    port_busy, resolve_lane, resolve_recorded_path, sha256, validate_evidence, verify_history,
)
from updi_rca.paths import ARTIFACTS_ROOT, REPOSITORY_ROOT as PROJECT

ROOT = ARTIFACTS_ROOT / "fresh"


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def verify():
    historical_files = verify_history(ROOT)
    for source in read_csv(ROOT / "source_sha256.csv"):
        assert sha256(source["path"]) == source["sha256"], source["path"]
    mapping = json.loads((ROOT / "mapping.json").read_text())
    assert sha256(ROOT / "mapping.json") == (ROOT / "mapping.sha256").read_text().strip()
    assert list(mapping) == ["P", "Q"]
    assert mapping["P"]["adapter"]["id_path"] < mapping["Q"]["adapter"]["id_path"]
    assert mapping["P"]["power_board"] != mapping["Q"]["power_board"]
    assert all(m["target_id"] == "UNKNOWN" and m["adapter_unit_id"] == "UNRESOLVED" for m in mapping.values())
    rows = validate_evidence(sorted((ROOT / "evidence").glob("*/*/envelope.json")), mapping)
    assert len(rows) == 80 and sum(len(r["events"]) for r in rows) == 560
    assert all(not r["success"] and r["failure_stage"] == "SIB_RESPONSE_EMPTY" for r in rows)
    assert all(r["transport_stage"] == "UPDI_CONTROL_RESPONSE" and r["exit_status"] == 1 for r in rows)
    for lane in ("P", "Q"):
        local = [r for r in rows if r["lane"] == lane]
        smoke = [r for r in local if r["batch"] == "smoke"]
        baseline = [r for r in local if r["batch"] == "baseline-1"]
        assert len(smoke) == 10 and len(baseline) == 30
        assert not control_allowed(local)
        assert not needs_untouched_repeats([smoke, baseline])
    for row in rows:
        raw = json.loads((ROOT / "evidence" / row["lane"] / row["run_id"] / "transport.json").read_text())
        assert raw["mode"] == "sib" and raw["baud"] == 38400
        assert raw["id_path"] == mapping[row["lane"]]["adapter"]["id_path"]
        assert raw["by_path"] == mapping[row["lane"]]["adapter"]["by_path"]
        tx = [(e["baud"], e["hex"]) for e in raw["events"] if e["kind"] == "tx"]
        echoes = [e["hex"] for e in raw["events"] if e["kind"] == "echo"]
        assert tx == [(300, "00"), (300, "00"), (38400, "55e6")]
        assert echoes == ["00", "00", "55e6"]
        assert raw["events"][-1]["hex"] == "" and raw["events"][-1]["requested"] == 32
        assert [e["break_ordinal"] for e in row["events"][:4]] == [1, 1, 2, 2]
    required = {"device_inventory", "runs", "events", "hypothesis_status", "pairwise_comparison",
                "fuse_compare", "flash_budget", "root_cause_ranking", "batch_metrics", "echo_errors",
                "causal_proof", "experiment_matrix"}
    for name in required:
        path = ROOT / "reports" / f"{name}.csv"
        with path.open() as stream:
            assert "epoch_id" in next(csv.reader(stream))
        assert all(r["epoch_id"] == EPOCH for r in read_csv(path))
    runs = read_csv(ROOT / "reports/runs.csv")
    events = read_csv(ROOT / "reports/events.csv")
    assert len(runs) == len({r["run_id"] for r in runs}) == 80
    assert len(events) == len({e["event_id"] for e in events}) == 560
    assert {e["run_id"] for e in events} <= {r["run_id"] for r in runs}
    assert all(sha256(resolve_recorded_path(r["raw_path"])) == r["raw_sha256"] for r in runs)
    assert all(r["score"] == "0" and r["status"] == "UNRESOLVED" for r in read_csv(ROOT / "reports/hypothesis_status.csv"))
    budget = read_csv(ROOT / "reports/flash_budget.csv")[0]
    assert all(budget[k] == "0" for k in ("flash_writes", "fuse_writes", "chip_erases", "bod_changes"))
    assert all(r["attempts"] == "" for r in read_csv(ROOT / "reports/experiment_matrix.csv") if r["status"] == "UNMEASURED")
    old_runs, old_events = [], []
    report = PROJECT / "artifacts/updi/legacy/experiment-reports"
    for run_path, event_path in (
        (report / "runs.csv", report / "events.csv"),
        (report / "swap_runs.csv", report / "swap_events.csv"),
        (report / "post_swap_runs.csv", report / "post_swap_events.csv"),
        (report / "continuation/RCA_CROSSOVER_01/runs_RCA_CROSSOVER_01.csv",
         report / "continuation/RCA_CROSSOVER_01/events_RCA_CROSSOVER_01.csv"),
    ):
        old_runs.extend(read_csv(run_path))
        old_events.extend(read_csv(event_path))
    assert len(old_runs) == 629 and len(old_events) == 7350
    # Historical run_id identifies batches; only fresh run_id identifies attempts.
    assert len({r["run_id"] for r in old_runs}) == 17
    assert len({e["event_id"] for e in old_events}) == 7350
    assert {e["run_id"] for e in old_events} <= {r["run_id"] for r in old_runs}
    assert not {r["run_id"] for r in old_runs} & {r["run_id"] for r in runs}
    for row in old_runs:
        locator = Path(row.get("source_log") or row["raw_log_path"])
        candidates = [locator] if locator.is_absolute() else [PROJECT / locator, ROOT.parent / locator]
        path = next((resolve_recorded_path(p) for p in candidates if resolve_recorded_path(p).is_file()), None)
        assert path and sha256(path) == row["raw_sha256"], locator
    live = discover_serial_ports()
    for m in mapping.values():
        adapter = resolve_lane(m, live)
        assert not port_busy(Path("/dev/serial/by-path") / adapter.by_path)
    return dict(epoch_id=EPOCH, status="PASS", inherited_runs=629, inherited_events=7350,
                historical_files_unchanged=historical_files, inherited_raw_hashes=629, inherited_batch_run_ids=17,
                fresh_runs=80, fresh_events=560, fresh_envelope_hashes=80,
                fresh_artifact_hashes=sum(len(r["artifacts"]) for r in rows),
                required_csv_schemas=len(required), source_hashes="PASS", identity_continuity="PASS",
                unique_mapped_ids="PASS", epoch_isolation="PASS", strict_tx_frames="PASS",
                control_gates={"P": False, "Q": False}, ports_closed=True,
                flash_writes=0, fuse_writes=0, chip_erases=0, bod_changes=0)


if __name__ == "__main__":
    if "--manifest" in sys.argv:
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(("epoch_id", "path", "sha256"))
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and not any(p in {"__pycache__", ".pytest_cache"} for p in path.parts) and path.name != "artifact_sha256.csv":
                writer.writerow((EPOCH, str(path), sha256(path)))
    else:
        print(json.dumps(verify(), indent=2))
