"""Independent, immutable fresh evidence around the unchanged strict probe CLI."""
import argparse
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from .identity import discover_serial_ports
from .metrics import metric_summary
from .paths import REPOSITORY_ROOT as REPO_ROOT
from .physical import echo_details
from .reporting import write_csv

EPOCH = "RCA_FRESH_01"
LOCK_ROOT = Path(f"/tmp/updi-rca-locks-{os.getuid()}")
DOMAINS = (
    "Host/software/USB", "Adapter unit", "External UPDI harness/resistor",
    "Separate power board/supply", "Target power/GND", "Target UPDI assembly",
    "AVR silicon/reset/config", "Firmware/runtime/ACC",
)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_recorded_path(path):
    path = Path(path)
    if path.is_file():
        return path
    try:
        relative = path.relative_to(REPO_ROOT)
    except ValueError:
        return path
    relocations = (
        ("experiments/updi_rca/evidence/", "artifacts/updi/legacy/experiment-evidence/"),
        ("experiments/updi_rca/reports/", "artifacts/updi/legacy/experiment-reports/"),
        ("experiments/updi_rca/fresh/", "artifacts/updi/fresh/"),
        ("experiments/updi_rca/diagrams/", "artifacts/updi/legacy/diagrams/"),
        ("experiments/updi_rca/target/manual-build/", "artifacts/updi/legacy/target-build/"),
    )
    value = relative.as_posix()
    for old, new in relocations:
        if value.startswith(old):
            candidate = REPO_ROOT / new / value[len(old):]
            if candidate.is_file():
                return candidate
    return path


def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2) + "\n" if not isinstance(value, str) else value)


def freeze_mapping(adapters, power_by_tty):
    if len(adapters) != 2 or len({a.id_path for a in adapters}) != 2:
        raise ValueError("exactly two unambiguous ID_PATH adapters required")
    if any(not a.id_path or a.id_path.startswith(("/dev/", "tty")) or not a.by_path for a in adapters):
        raise ValueError("stable ID_PATH and by-path required")
    return {lane: {"epoch_id": EPOCH, "lane": lane, "adapter": asdict(adapter),
                   "adapter_unit_id": "UNRESOLVED", "target_id": "UNKNOWN",
                   "power_board": f"PowerBoard {lane}",
                   "power_board_branch_report": power_by_tty.get(adapter.current_tty, "UNKNOWN"),
                   "power_board_physical_id": "UNKNOWN", "supply": "UNKNOWN"}
            for lane, adapter in zip(("P", "Q"), sorted(adapters, key=lambda a: a.id_path))}


def resolve_lane(mapping, adapters):
    expected = mapping["adapter"]
    matches = [a for a in adapters if a.id_path == expected["id_path"]]
    if len(matches) != 1:
        raise ValueError("missing or ambiguous ID_PATH")
    live = matches[0]
    if any(getattr(live, k) != expected[k] for k in ("vid", "pid", "usb_serial", "by_path")):
        raise ValueError("adapter descriptor/path continuity changed")
    return live


@contextmanager
def lane_lock(id_path):
    LOCK_ROOT.mkdir(mode=0o700, exist_ok=True)
    stat = LOCK_ROOT.lstat()
    if LOCK_ROOT.is_symlink() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise OSError("unsafe lane lock directory")
    name = hashlib.sha256(id_path.encode()).hexdigest() + ".lock"
    fd = os.open(LOCK_ROOT / name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise BlockingIOError("PORT_BUSY: lane lock held") from error
        yield
    finally:
        os.close(fd)


def port_busy(port):
    result = subprocess.run(["fuser", str(port)], capture_output=True, text=True, timeout=5)
    if result.returncode not in (0, 1):
        raise OSError(f"ownership check failed: {result.stderr}")
    # fuser 1 is also returned for missing devices; never interpret those as idle.
    if not Path(port).exists():
        raise OSError("stable serial device is absent")
    return result.returncode == 0


def failure_stage(record):
    breaks = 0
    command = record.get("mode", "UPDI").upper()
    events = record.get("events", [])
    for i, event in enumerate(events):
        if event["kind"] == "tx":
            tx = bytes.fromhex(event.get("hex", ""))
            is_break = event.get("baud") == 300 and tx == b"\x00"
            if is_break:
                breaks += 1
            prefix = f"BREAK{breaks}" if is_break else command
            if event.get("count") != len(tx):
                return "HOST_TX_INCOMPLETE"
            if i + 1 == len(events) or events[i + 1]["kind"] != "echo":
                return f"{prefix}_ECHO_NOT_CAPTURED"
            details = echo_details(tx, bytes.fromhex(events[i + 1].get("hex", "")))
            if details["class"] != "EXACT":
                return f"{prefix}_{details['class']}_ECHO"
        elif event["kind"] == "response":
            actual = len(bytes.fromhex(event.get("hex", "")))
            if actual != event["requested"]:
                if record.get("mode") == "read":
                    return event.get("stage", "ACC_DATA_RESPONSE")
                return f"{command}_RESPONSE_{'EMPTY' if actual == 0 else 'SHORT'}"
    return "PASS" if record.get("exit") == 0 else record.get("failure_stage", "UNKNOWN")


def control_allowed(rows):
    batches = {}
    for row in rows:
        if row["epoch_id"] == EPOCH and row["mode"] == "sib" and row["batch"].startswith("baseline-"):
            batches.setdefault(row["batch"], []).append(row)
    latest = next(reversed(batches.values())) if batches else []
    return len(latest) == 30 and all(r["success"] for r in latest)


def needs_untouched_repeats(batches):
    if not batches or len(batches) >= 3:
        return False
    mixed = any(len({r["success"] for r in b}) > 1 for b in batches)
    boundaries = [{r["failure_stage"] for r in b if not r["success"]} for b in batches]
    return mixed or any(s != boundaries[0] for s in boundaries[1:])


def domain_scores(evidence):
    scores = [dict(epoch_id=EPOCH, domain=f"D{i}", cause=cause, score=0, status="UNRESOLVED")
              for i, cause in enumerate(DOMAINS, 1)]
    seen = set()
    for item in evidence:
        if item["epoch_id"] != EPOCH or item["evidence_id"] in seen:
            raise ValueError("mixed epoch or duplicate evidence")
        seen.add(item["evidence_id"])
        if item["delta"] not in (-3, -1, 1, 3) or item["domain"] not in {r["domain"] for r in scores}:
            raise ValueError("invalid domain score")
        if abs(item["delta"]) == 3 and not item.get("controlled_aba"):
            raise ValueError("controlled A/B/A required for three points")
        next(r for r in scores if r["domain"] == item["domain"])["score"] += item["delta"]
    return scores


def run_attempt(root, mapping, lane, batch, mode):
    if lane not in ("P", "Q") or mode not in ("sib", "control"):
        raise ValueError("only assigned lanes and bounded SIB/control permitted")
    if not batch or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in batch):
        raise ValueError("invalid batch")
    frozen = mapping[lane]
    if frozen["epoch_id"] != EPOCH:
        raise ValueError("mixed epoch mapping")
    root = Path(root).resolve()
    if mode == "control":
        previous = validate_evidence(sorted((root / "evidence" / lane).glob("*/envelope.json")), mapping)
        if not control_allowed(previous):
            raise ValueError("control requires latest fresh SIB30 all pass")
    run_id = f"{EPOCH}-{lane}-{batch}-{mode}-{uuid.uuid4().hex}"
    directory = root / "evidence" / lane / run_id
    directory.mkdir(parents=True, exist_ok=False)
    transport = directory / "transport.json"
    command = [sys.executable, "-m", "updi_rca.cli", "probe", mode,
               frozen["adapter"]["id_path"], str(transport), "--timeout", "1", "--baud", "38400"]
    env = dict(epoch_id=EPOCH, run_id=run_id, lane=lane, batch=batch, mode=mode,
               mapping=frozen, wall_start=utc(), monotonic_start_ns=time.monotonic_ns(),
               command=command, success=False, failure_stage="EXECUTION_ERROR", transport_stage="",
               exit_status=None, events=[], artifacts=[])
    stdout, stderr = "", ""
    try:
        with lane_lock(frozen["adapter"]["id_path"]):
            try:
                # Lock the frozen stable path, check ownership, then resolve immediately before open.
                port = Path("/dev/serial/by-path") / frozen["adapter"]["by_path"]
                if port_busy(port):
                    raise BlockingIOError("PORT_BUSY: device owner present")
                live = resolve_lane(frozen, discover_serial_ports())
                env["current_tty"] = live.current_tty
            except BlockingIOError:
                raise
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                env["failure_stage"] = "DISCOVERY_ERROR"
                raise RuntimeError(str(error)) from error
            result = subprocess.run(command, capture_output=True, text=True, timeout=45)
            stdout, stderr = result.stdout, result.stderr
            env["exit_status"] = result.returncode
            if transport.exists():
                record = json.loads(transport.read_text())
                result_summary = json.loads(stdout)
                env.update(success=result.returncode == 0 and record["exit"] == 0,
                           failure_stage=failure_stage(record), transport_stage=result_summary["stage"])
                ordinal = 0
                for i, event in enumerate(record["events"]):
                    if event["kind"] == "tx" and event.get("baud") == 300 and event.get("hex") == "00":
                        ordinal += 1
                    env["events"].append({**event, "epoch_id": EPOCH, "run_id": run_id,
                                          "event_id": f"{run_id}-e{i+1}", "break_ordinal": ordinal if ordinal <= 2 and event.get("baud") == 300 else None})
            else:
                env["failure_stage"] = "DISCOVERY_ERROR" if result.returncode else "EXECUTION_ERROR"
    except BlockingIOError as error:
        env["failure_stage"] = "PORT_BUSY"
        stderr = str(error)
    except Exception as error:
        stderr += f"{type(error).__name__}: {error}"
        if isinstance(error, subprocess.TimeoutExpired):
            stdout = error.stdout or ""
            stderr = (error.stderr or b"").decode(errors="replace") if isinstance(error.stderr, bytes) else (error.stderr or stderr)
    finally:
        env.update(wall_end=utc(), monotonic_end_ns=time.monotonic_ns())
        env["latency_ms"] = (env["monotonic_end_ns"] - env["monotonic_start_ns"]) / 1e6
        for name, value in (("stdout.txt", stdout), ("stderr.txt", stderr)):
            write_once(directory / name, value.decode(errors="replace") if isinstance(value, bytes) else value)
        for artifact in sorted(directory.iterdir()):
            env["artifacts"].append({"path": str(artifact), "sha256": sha256(artifact)})
        path = directory / "envelope.json"
        write_once(path, env)
        write_once(directory / "envelope.sha256", sha256(path))
    return path


def validate_evidence(paths, mapping):
    rows, runs, events, raw_paths = [], set(), set(), set()
    for path in paths:
        path = Path(path)
        row = json.loads(path.read_text())
        if sha256(path) != path.with_suffix(".sha256").read_text().strip():
            raise ValueError("envelope hash mismatch")
        run = row["run_id"]
        if row["epoch_id"] != EPOCH or not run.startswith(EPOCH + "-"):
            raise ValueError("mixed epoch")
        if run in runs:
            raise ValueError("duplicate run ID")
        runs.add(run)
        if row["lane"] not in mapping or row["mapping"] != mapping[row["lane"]]:
            raise ValueError("identity continuity mismatch")
        expected_command = [row["command"][0], "-m", "updi_rca.cli", "probe", row["mode"],
                            row["mapping"]["adapter"]["id_path"], str(path.parent / "transport.json"),
                            "--timeout", "1", "--baud", "38400"]
        if row["command"] != expected_command or row["mode"] not in {"sib", "control"}:
            raise ValueError("unexpected probe command")
        elapsed = (row["monotonic_end_ns"] - row["monotonic_start_ns"]) / 1e6
        if elapsed < 0 or row["latency_ms"] != elapsed:
            raise ValueError("inconsistent attempt timing")
        for artifact in row["artifacts"]:
            artifact_path = Path(artifact["path"]).resolve()
            if artifact_path.parent != path.parent.resolve() or artifact_path in raw_paths:
                raise ValueError("overlapping or foreign raw path")
            raw_paths.add(artifact_path)
            if not artifact.get("sha256") or not artifact_path.is_file() or sha256(artifact_path) != artifact["sha256"]:
                raise ValueError("absent or incorrect raw hash")
        names = {Path(a["path"]).name for a in row["artifacts"]}
        if not {"stdout.txt", "stderr.txt"} <= names:
            raise ValueError("missing raw artifacts")
        if row["failure_stage"] not in {"PORT_BUSY", "DISCOVERY_ERROR", "EXECUTION_ERROR"} and "transport.json" not in names:
            raise ValueError("missing transport artifact")
        for event in row["events"]:
            if event["epoch_id"] != EPOCH or event["run_id"] != run:
                raise ValueError("unmapped event or mixed epoch")
            if event["event_id"] in events:
                raise ValueError("duplicate event ID")
            events.add(event["event_id"])
        if "transport.json" in names:
            record = json.loads((path.parent / "transport.json").read_text())
            if row["success"] != (record["exit"] == 0) or row["exit_status"] != record["exit"]:
                raise ValueError("transport result mismatch")
            original = [{k: v for k, v in e.items() if k not in ("epoch_id", "run_id", "event_id", "break_ordinal")} for e in row["events"]]
            if original != record["events"] or row["failure_stage"] != failure_stage(record):
                raise ValueError("raw event/stage mismatch")
        rows.append(row)
    return sorted(rows, key=lambda r: r["monotonic_start_ns"])


def initialize(root, project):
    """Freeze history and current discovery without opening a serial device."""
    root, project = Path(root).resolve(), Path(project).resolve()
    root.mkdir(parents=True, exist_ok=True)
    # A failed discovery leaves a documented checkpoint, never a silently reusable epoch.
    write_once(root / "INITIALIZED.json", {"epoch_id": EPOCH, "utc": utc()})
    historical = []
    for path in sorted((project / "experiments/updi_rca").rglob("*")):
        if not path.is_file() or root in path.parents or any(p in {".venv", "__pycache__", ".pytest_cache"} for p in path.parts):
            continue
        historical.append({"epoch_id": EPOCH, "path": str(path), "sha256": sha256(path)})
    write_csv(root / "historical_sha256.csv", ("epoch_id", "path", "sha256"), historical)
    snapshots = {}
    for label, command in (("git_state", ["git", "status", "--short", "--untracked-files=no"]),
                           ("git_head", ["git", "rev-parse", "HEAD"]),
                           ("kernel", ["uname", "-a"]), ("uv", ["uv", "--version"]),
                           ("python_serial", [sys.executable, "-c", "import sys,serial; print(sys.version); print(serial.VERSION)"])):
        result = subprocess.run(command, cwd=project, capture_output=True, text=True, timeout=15)
        snapshots[label] = dict(command=command, stdout=result.stdout, stderr=result.stderr, exit_status=result.returncode)
    write_once(root / "host_snapshot.json", {"epoch_id": EPOCH, "utc": utc(), "monotonic_ns": time.monotonic_ns(), "snapshots": snapshots})
    sources = [{"epoch_id": EPOCH, "path": str(p), "sha256": sha256(p)}
               for p in sorted((project / "experiments/updi_rca/src").rglob("*.py"))]
    write_csv(root / "source_sha256.csv", ("epoch_id", "path", "sha256"), sources)
    try:
        adapters = discover_serial_ports()
        write_once(root / "usb_inventory.json", {"epoch_id": EPOCH, "utc": utc(), "adapters": [asdict(a) for a in adapters]})
        mapping = freeze_mapping(adapters, {"/dev/ttyUSB0": "user-reported separate power board on current ttyUSB0 branch",
                                            "/dev/ttyUSB1": "user-reported separate power board on current ttyUSB1 branch"})
        write_once(root / "mapping.json", mapping)
        write_once(root / "mapping.sha256", sha256(root / "mapping.json"))
    except Exception as error:
        write_once(root / "DISCOVERY_ERROR.json", {"epoch_id": EPOCH, "error": f"{type(error).__name__}: {error}", "utc": utc()})
        raise
    refresh_reports(root)
    return mapping


def verify_history(root):
    import csv
    rows = list(csv.DictReader((Path(root) / "historical_sha256.csv").open()))
    for row in rows:
        path = resolve_recorded_path(row["path"])
        if row["epoch_id"] != EPOCH or not path.is_file() or sha256(path) != row["sha256"]:
            raise ValueError(f"historical hash mismatch: {row['path']}")
    return len(rows)


def refresh_reports(root):
    """Coordinator-only projection; unmeasured conditions have blank counts."""
    root = Path(root).resolve()
    mapping = json.loads((root / "mapping.json").read_text())
    if (root / "mapping.sha256").exists() and sha256(root / "mapping.json") != (root / "mapping.sha256").read_text().strip():
        raise ValueError("frozen mapping hash mismatch")
    rows = validate_evidence(sorted((root / "evidence").glob("*/*/envelope.json")), mapping)
    reports = root / "reports"

    def emit(name, columns, data):
        values = [{"epoch_id": EPOCH, **r} for r in data]
        write_csv(reports / f"{name}.csv", ("epoch_id", *columns.split()), values)

    emit("device_inventory", "lane id_path current_tty by_path vid pid adapter_serial adapter_unit_id target_id power_board power_board_branch_report power_board_physical_id supply", [
        {"lane": lane, "id_path": m["adapter"]["id_path"], "current_tty": m["adapter"]["current_tty"],
         "by_path": m["adapter"]["by_path"], "vid": m["adapter"]["vid"], "pid": m["adapter"]["pid"], "adapter_serial": m["adapter"]["usb_serial"],
         **{k: m[k] for k in ("adapter_unit_id", "target_id", "power_board", "power_board_branch_report", "power_board_physical_id", "supply")}}
        for lane, m in mapping.items()])
    run_columns = "run_id lane batch mode success failure_stage transport_stage exit_status latency_ms wall_start wall_end monotonic_start_ns monotonic_end_ns current_tty raw_path raw_sha256"
    emit("runs", run_columns, [{**{k: r.get(k) for k in run_columns.split() if not k.startswith("raw_")},
                                "raw_path": str(root / "evidence" / r["lane"] / r["run_id"] / "envelope.json"),
                                "raw_sha256": sha256(root / "evidence" / r["lane"] / r["run_id"] / "envelope.json")}
                               for r in rows])
    event_rows, echo_rows = [], []
    for r in rows:
        for i, e in enumerate(r["events"]):
            event_rows.append({"run_id": r["run_id"], "event_id": e["event_id"], "lane": r["lane"],
                               "kind": e["kind"], "hex": e.get("hex"), "break_ordinal": e["break_ordinal"],
                               "ns": e.get("ns"), "end_ns": e.get("end_ns"), "baud": e.get("baud"),
                               "count": e.get("count"), "requested": e.get("requested"), "transport_stage": e.get("stage")})
            if e["kind"] == "echo" and i and r["events"][i-1]["kind"] == "tx":
                tx = r["events"][i-1]
                details = echo_details(bytes.fromhex(tx["hex"]), bytes.fromhex(e["hex"]))
                echo_rows.append({"run_id": r["run_id"], "event_id": e["event_id"], "lane": r["lane"], "break_ordinal": e["break_ordinal"],
                                  "tx_hex": tx["hex"], "echo_hex": e["hex"], **details})
    emit("events", "run_id event_id lane kind hex break_ordinal ns end_ns baud count requested transport_stage", event_rows)
    emit("echo_errors", "run_id event_id lane break_ordinal tx_hex echo_hex class expected_len actual_len missing_byte_count extra_byte_count xor_hex hamming_distance_overlap first_mismatch_index", echo_rows)
    groups = defaultdict(list)
    for r in rows:
        groups[(r["lane"], r["batch"], r["mode"])].append(r)
    metrics = []
    for (lane, batch, mode), attempts in sorted(groups.items()):
        m = metric_summary(attempts)
        metrics.append({"lane": lane, "batch": batch, "mode": mode,
                        **{k: m[k] for k in ("attempts", "successes", "failures", "success_rate", "failure_rate", "median_latency_ms", "p95_latency_ms")},
                        "wilson_low": m["wilson_95"][0], "wilson_high": m["wilson_95"][1],
                        "failure_stages": json.dumps(m["failure_stages"], sort_keys=True)})
    emit("batch_metrics", "lane batch mode attempts successes failures success_rate failure_rate wilson_low wilson_high median_latency_ms p95_latency_ms failure_stages", metrics)
    matrix = [{"lane": lane, "batch": batch, "mode": mode, "attempts": len(groups[(lane, batch, mode)]) or None,
               "status": "MEASURED" if groups[(lane, batch, mode)] else "UNMEASURED"}
              for lane in ("P", "Q") for batch, mode in [("smoke", "sib"), ("baseline-1", "sib"), ("baseline-2", "sib"), ("baseline-3", "sib"), ("control-1", "control"), ("crossed", "sib"), ("restored", "sib")]]
    emit("experiment_matrix", "lane batch mode attempts status", matrix)
    scores = domain_scores([])
    emit("hypothesis_status", "domain cause score status", scores)
    emit("root_cause_ranking", "domain cause score status", scores)
    emit("causal_proof", "domain status controlled_cycles decisive_evidence unresolved_alternatives", [
        {"domain": r["domain"], "status": "UNRESOLVED", "controlled_cycles": 0, "decisive_evidence": "",
         "unresolved_alternatives": "No controlled intervention; path, power board and target remain confounded"} for r in scores])
    emit("pairwise_comparison", "batch mode n_p n_q rate_p rate_q delta interpretation", [
        {"batch": b, "mode": mode, "n_p": len(groups[("P", b, mode)]) or None, "n_q": len(groups[("Q", b, mode)]) or None,
         "rate_p": metric_summary(groups[("P", b, mode)])["success_rate"] if groups[("P", b, mode)] else None,
         "rate_q": metric_summary(groups[("Q", b, mode)])["success_rate"] if groups[("Q", b, mode)] else None,
         "delta": (metric_summary(groups[("P", b, mode)])["success_rate"] - metric_summary(groups[("Q", b, mode)])["success_rate"])
                   if groups[("P", b, mode)] and groups[("Q", b, mode)] else None,
         "interpretation": "Descriptive only; no locality inference"} for b, mode in sorted({(r["batch"], r["mode"]) for r in rows})])
    emit("fuse_compare", "lane status firmware_sha256 fuse_sha256", [{"lane": lane, "status": "UNMEASURED"} for lane in mapping])
    emit("flash_budget", "flash_writes fuse_writes chip_erases bod_changes policy", [dict(flash_writes=0, fuse_writes=0, chip_erases=0, bod_changes=0, policy="strict SIB/LDCS only; no register writes")])
    return rows, metrics


def run_batch(root, lane, batch, mode, attempts):
    root = Path(root)
    mapping = json.loads((root / "mapping.json").read_text())
    if (root / "mapping.sha256").exists() and sha256(root / "mapping.json") != (root / "mapping.sha256").read_text().strip():
        raise ValueError("frozen mapping hash mismatch")
    if attempts not in (10, 30) or batch == "smoke" and (mode != "sib" or attempts != 10):
        raise ValueError("only planned 10/30 attempt batches permitted")
    if mode == "control" and not control_allowed(validate_evidence(sorted((root / "evidence" / lane).glob("*/envelope.json")), mapping)):
        raise ValueError("control requires latest fresh SIB30 all pass")
    batch_path = root / "evidence" / lane / f"{batch}-{mode}.json"
    # Reserve batch before any attempt so an interrupted batch cannot be silently rerun.
    write_once(batch_path, {"epoch_id": EPOCH, "batch": batch, "mode": mode, "attempts": attempts, "status": "STARTED"})
    paths = [run_attempt(root, mapping, lane, batch, mode) for _ in range(attempts)]
    rows = validate_evidence(paths, mapping)
    metrics = metric_summary(rows)
    write_once(batch_path.with_name(batch_path.stem + "-summary.json"), {"epoch_id": EPOCH, "lane": lane, "batch": batch, "mode": mode, "metrics": metrics})
    with (root / "evidence" / lane / "MEMORY.md").open("a") as stream:
        stream.write(f"\n{utc()} {batch}/{mode}: {json.dumps(metrics)}\n")
    print(json.dumps({"lane": lane, "batch": batch, "mode": mode, "metrics": metrics}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("lane", choices=("P", "Q"))
    parser.add_argument("batch")
    parser.add_argument("mode", choices=("sib", "control"))
    parser.add_argument("attempts", type=int)
    args = parser.parse_args()
    run_batch(args.root, args.lane, args.batch, args.mode, args.attempts)


if __name__ == "__main__":
    main()
