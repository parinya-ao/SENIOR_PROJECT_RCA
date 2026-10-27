#!/usr/bin/env python3
"""Run the coordinator-approved, read-only 20-attempt Lane P SIB campaign."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import datetime as dt
import hashlib
import io
import json
import math
import os
import pathlib
import subprocess
import sys
import time

from updi_rca.identity import BoardIdentity, discover_serial_ports, resolve_connection
from updi_rca.probes import run_sib_probe
from updi_rca.runner import run_campaign

ROOT = pathlib.Path(__file__).resolve().parents[5]
BASE = pathlib.Path(__file__).resolve().parent
OUT = BASE / "pre"
EXPECTED_ID_PATH = "pci-0000:00:14.0-usb-0:4:1.0"
ATTEMPTS = 20
BAUD = 38400
TIMEOUT = 1.0
BOARD_LABEL = "X"  # Physical label from the coordinator-confirmed board map.
PAIRING = "P->X"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def command(argv: list[str], timeout: float = 12) -> dict:
    start_utc, start_mono = utc_now(), time.monotonic_ns()
    try:
        p = subprocess.run(argv, capture_output=True, text=True, errors="replace", timeout=timeout, check=False)
        stdout, stderr, code, timed_out = p.stdout, p.stderr, p.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        code, timed_out = None, True
    except OSError as exc:
        stdout, stderr, code, timed_out = "", f"{type(exc).__name__}: {exc}\n", 127, False
    return {
        "argv": argv, "start_utc": start_utc, "end_utc": utc_now(),
        "monotonic_start_ns": start_mono, "monotonic_end_ns": time.monotonic_ns(),
        "exit_code": code, "timed_out": timed_out, "stdout": stdout, "stderr": stderr,
        "stdout_sha256": sha(stdout.encode()), "stderr_sha256": sha(stderr.encode()),
    }


def source_hashes() -> dict:
    files = [
        "experiments/updi_rca/src/updi_rca/probes.py",
        "experiments/updi_rca/src/updi_rca/runner.py",
        "experiments/updi_rca/src/updi_rca/identity.py",
        "experiments/updi_rca/src/updi_rca/classify.py",
        "experiments/updi_rca/memory/SWAP_PLAN.md",
        "experiments/updi_rca/memory/SWAP_FREEZE.md",
        "experiments/updi_rca/evidence/RCA_BOARD_SWAP_01/path_p/run_pre_campaign.py",
    ]
    return {name: sha((ROOT / name).read_bytes()) for name in files}


def wilson95(successes: int, n: int) -> list[float] | None:
    if not n:
        return None
    z = 1.959963984540054
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def record_raw(raw_path: pathlib.Path, run_id: str, attempt: int, started_utc: str,
               started_mono: int, result) -> object:
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    end_mono = time.monotonic_ns()
    data.update({
        "epoch": "RCA_BOARD_SWAP_01", "run_id": run_id, "attempt": attempt,
        "board_label": BOARD_LABEL, "pairing": PAIRING,
        "target_identity": "UNKNOWN_TARGET", "expected_id_path": EXPECTED_ID_PATH,
        "attempt_start_utc": started_utc, "attempt_end_utc": utc_now(),
        "attempt_monotonic_start_ns": started_mono, "attempt_monotonic_end_ns": end_mono,
        "attempt_duration_ms": (end_mono - started_mono) / 1_000_000,
        "probe": "SIB only", "approved_attempts": ATTEMPTS,
    })
    raw_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return replace(result, raw_sha256=sha(raw_path.read_bytes()))


class StopCampaign(RuntimeError):
    pass


def main() -> int:
    if OUT.exists():
        print(json.dumps({"status": "ABORT_EXISTING_OUTPUT", "path": str(OUT)}, indent=2))
        return 2
    OUT.mkdir()
    (OUT / "raw").mkdir()
    (OUT / "commands").mkdir()

    cmd_start_utc, cmd_start_mono = utc_now(), time.monotonic_ns()
    attempted_utc_start = cmd_start_utc
    map_snapshot: dict = {"expected_id_path": EXPECTED_ID_PATH, "pairing": PAIRING,
                          "board_label": BOARD_LABEL, "target_identity": "UNKNOWN_TARGET"}
    stdout_capture, stderr_capture = io.StringIO(), io.StringIO()
    status, abort_reason, rows = "PREFLIGHT", None, []
    run_id = "not-started"
    metrics: dict = {}
    try:
        adapters = discover_serial_ports()
        connection = resolve_connection(EXPECTED_ID_PATH, adapters, {EXPECTED_ID_PATH: BoardIdentity()})
        adapter = connection.adapter
        map_snapshot.update({
            "adapter": adapter.__dict__,
            "current_tty_at_preflight": adapter.current_tty,
            "by_path_locator": str(pathlib.Path("/dev/serial/by-path") / adapter.by_path) if adapter.by_path else None,
            "sysfs_path": adapter.sysfs_path,
        })
        if (adapter.vid.lower(), adapter.pid.lower(), adapter.id_path) != ("10c4", "ea60", EXPECTED_ID_PATH):
            raise StopCampaign("adapter VID/PID/ID_PATH differs from verified Lane P identity")
        if not adapter.by_path:
            raise StopCampaign("stable by-path locator missing")
        port = pathlib.Path("/dev/serial/by-path") / adapter.by_path
        if not port.is_symlink() or not port.exists():
            raise StopCampaign("resolved stable by-path link is absent")

        # Port ownership is checked immediately before entering the approved batch.
        fuser = command(["fuser", "-v", str(port)])
        (OUT / "commands" / "fuser_preflight.json").write_text(json.dumps(fuser, indent=2) + "\n")
        if fuser["exit_code"] == 0:
            raise StopCampaign(f"PORT_BUSY: fuser reported owner(s): {fuser['stdout']} {fuser['stderr']}")
        if fuser["exit_code"] != 1 or fuser["timed_out"]:
            raise StopCampaign(f"PORT_OWNERSHIP_UNKNOWN: fuser exit={fuser['exit_code']} stderr={fuser['stderr']}")

        pgrep_owners = {}
        for label, pattern in (("upditerm", "[u]pditerm"), ("avrdude", "[a]vrdude")):
            proc = command(["pgrep", "-a", "-f", pattern])
            (OUT / "commands" / f"{label}_processes_preflight.json").write_text(json.dumps(proc, indent=2) + "\n")
            pgrep_owners[label] = {"exit_code": proc["exit_code"], "stdout": proc["stdout"], "stderr": proc["stderr"]}
            if proc["exit_code"] == 0:
                raise StopCampaign(f"active {label} process detected; refusing batch")
            if proc["exit_code"] != 1:
                raise StopCampaign(f"{label} process check inconclusive (exit {proc['exit_code']})")
        map_snapshot["fuser_preflight"] = {k: fuser[k] for k in ("exit_code", "stdout", "stderr", "start_utc", "end_utc")}
        map_snapshot["upditerm_avrdude_process_checks"] = pgrep_owners
        status = "READY"

        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        run_id = f"swap-pre-P-{stamp}"
        hashes = source_hashes()
        (OUT / "source_hashes.json").write_text(json.dumps({"capture_utc": utc_now(), "sha256": hashes}, indent=2) + "\n")

        observed = []

        def one_attempt(raw_path: pathlib.Path):
            attempt = int(raw_path.stem.rsplit("-", 1)[-1])
            start_utc, start_mono = utc_now(), time.monotonic_ns()
            # run_sib_probe re-resolves the exact ID_PATH before every exclusive open.
            try:
                result = run_sib_probe(connection, BAUD, raw_path, timeout=TIMEOUT)
            except Exception as exc:
                # Identity ambiguity is a hard stop and occurs before a serial open.
                raw_path.write_text(json.dumps({
                    "epoch": "RCA_BOARD_SWAP_01", "run_id": run_id, "attempt": attempt,
                    "board_label": BOARD_LABEL, "pairing": PAIRING,
                    "target_identity": "UNKNOWN_TARGET", "id_path": EXPECTED_ID_PATH,
                    "mode": "sib", "baud": BAUD, "timeout": TIMEOUT,
                    "write_policy": "no STCS, STS, programming key, reset, or NVM write",
                    "serial_open_attempted": False, "exit": 1,
                    "failure_stage": "IDENTITY_OR_PROBE_ABORT",
                    "error": f"{type(exc).__name__}: {exc}",
                    "attempt_start_utc": start_utc, "attempt_end_utc": utc_now(),
                    "attempt_monotonic_start_ns": start_mono,
                    "attempt_monotonic_end_ns": time.monotonic_ns(),
                }, indent=2) + "\n", encoding="utf-8")
                observed.append({"attempt": attempt, "success": False,
                                 "stage": "IDENTITY_OR_PROBE_ABORT", "latency_ms": 0.0,
                                 "raw_path": str(raw_path), "raw_sha256": sha(raw_path.read_bytes())})
                raise StopCampaign(f"per-attempt identity/probe abort: {type(exc).__name__}: {exc}") from exc
            result = record_raw(raw_path, run_id, attempt, start_utc, start_mono, result)
            item = {
                "attempt": attempt, "success": result.success, "stage": result.stage,
                "latency_ms": result.latency_ms, "raw_path": str(raw_path),
                "raw_sha256": result.raw_sha256,
            }
            observed.append(item)
            if result.stage == "SERIAL_OPEN":
                raise StopCampaign("SERIAL_OPEN failure: stop immediately; do not retry a busy/ambiguous port")
            return result

        (OUT / "campaign_start.json").write_text(json.dumps({
            "run_id": run_id, "start_utc": utc_now(), "monotonic_ns": time.monotonic_ns(),
            "attempts": ATTEMPTS, "mode": "SIB only", "baud": BAUD, "timeout": TIMEOUT,
            "pairing": PAIRING, "target_label": BOARD_LABEL, "target_identity": "UNKNOWN_TARGET",
            "adapter_id_path": adapter.id_path, "by_path": str(port),
            "policy": "BREAK sync then SIB reads only; no control reads, writes, keys, reset, or NVM operations",
        }, indent=2) + "\n")
        batch_start_utc = utc_now()
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                rows = run_campaign(one_attempt, ATTEMPTS, OUT / "raw", run_id)
            status = "COMPLETE"
        except StopCampaign as exc:
            abort_reason = str(exc)
            rows = observed
            status = "STOPPED"
        except Exception as exc:
            abort_reason = f"{type(exc).__name__}: {exc}"
            rows = observed
            status = "STOPPED"
        finally:
            end_utc, end_mono = utc_now(), time.monotonic_ns()
            campaign_start_dt = dt.datetime.fromisoformat(batch_start_utc.replace("Z", "+00:00"))
            start_for_log = (campaign_start_dt - dt.timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S UTC")
            end_for_log = (dt.datetime.fromisoformat(end_utc.replace("Z", "+00:00")) + dt.timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S UTC")
            klog = command(["journalctl", "-k", "--since", start_for_log, "--until", end_for_log, "--no-pager", "-o", "short-iso"], timeout=25)
            (OUT / "commands" / "kernel_log_campaign_window.json").write_text(json.dumps(klog, indent=2) + "\n")
            attempts_done = len(observed)
            stage_counts: dict[str, int] = {}
            for item in observed:
                if not item["success"]:
                    stage_counts[item["stage"]] = stage_counts.get(item["stage"], 0) + 1
            latencies = sorted(item["latency_ms"] for item in observed)
            success_count = sum(item["success"] for item in observed)
            raw_records = []
            for item in observed:
                raw_records.append(json.loads(pathlib.Path(item["raw_path"]).read_text(encoding="utf-8")))
            first_break_exact = 0
            second_break_exact = 0
            sib_request_tx = 0
            sib_response = 0
            for rec in raw_records:
                echoes = [e.get("hex", "") for e in rec.get("events", []) if e.get("kind") == "echo"]
                txs = [e.get("hex", "") for e in rec.get("events", []) if e.get("kind") == "tx"]
                first_break_exact += int(len(echoes) > 0 and echoes[0] == "00")
                second_break_exact += int(len(echoes) > 1 and echoes[1] == "00")
                sib_request_tx += int("55e6" in txs)
                sib_response += int(bool(rec.get("values", {}).get("SIB")))
            metrics = {
                "n_attempted": attempts_done, "planned_n": ATTEMPTS,
                "successes": success_count, "failures": attempts_done - success_count,
                "success_rate": success_count / attempts_done if attempts_done else None,
                "failure_rate": (attempts_done - success_count) / attempts_done if attempts_done else None,
                "success_wilson95": wilson95(success_count, attempts_done),
                "failure_stages": stage_counts,
                "break1_exact_echoes": first_break_exact,
                "break2_exact_echoes": second_break_exact,
                "sib_request_tx_count": sib_request_tx,
                "sib_response_count": sib_response,
                "latency_median_ms": (latencies[(len(latencies)-1)//2] if len(latencies) % 2 else
                                       ((latencies[len(latencies)//2 - 1] + latencies[len(latencies)//2]) / 2)) if latencies else None,
                "latency_p95_ms": latencies[max(0, math.ceil(.95 * len(latencies)) - 1)] if latencies else None,
            }
            summary = {
                "epoch": "RCA_BOARD_SWAP_01", "status": status, "run_id": run_id,
                "pairing": PAIRING, "board_label": BOARD_LABEL, "target_identity": "UNKNOWN_TARGET",
                "adapter_id_path": EXPECTED_ID_PATH, "current_tty_at_preflight": adapter.current_tty,
                "by_path": str(port), "baud": BAUD, "timeout": TIMEOUT,
                "attempt_limit": ATTEMPTS, "metrics": metrics, "abort_reason": abort_reason,
                "mapping": map_snapshot, "source_hashes": hashes,
                "kernel_log_window": {"since": start_for_log, "until": end_for_log,
                                       "exit_code": klog["exit_code"], "stdout_sha256": klog["stdout_sha256"]},
                "raw_attempts": observed,
                "start_utc": cmd_start_utc, "end_utc": end_utc,
                "duration_ms": (end_mono - cmd_start_mono) / 1_000_000,
            }
            (OUT / "campaign_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            (OUT / "mapping.json").write_text(json.dumps(map_snapshot, indent=2) + "\n")
            (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")

    except StopCampaign as exc:
        abort_reason = str(exc)
        status = "ABORT_PREFLIGHT"
        cmd_end_utc, cmd_end_mono = utc_now(), time.monotonic_ns()
        stdout_capture.write(json.dumps({"status": status, "abort_reason": abort_reason, "mapping": map_snapshot}, indent=2) + "\n")
    except Exception as exc:
        abort_reason = f"{type(exc).__name__}: {exc}"
        status = "ABORT_ERROR"
        cmd_end_utc, cmd_end_mono = utc_now(), time.monotonic_ns()
        stderr_capture.write(abort_reason + "\n")

    if status in {"ABORT_PREFLIGHT", "ABORT_ERROR"}:
        cmd_end_utc, cmd_end_mono = utc_now(), time.monotonic_ns()
        (OUT / "campaign_summary.json").write_text(json.dumps({
            "epoch": "RCA_BOARD_SWAP_01", "status": status, "run_id": run_id,
            "pairing": PAIRING, "board_label": BOARD_LABEL, "target_identity": "UNKNOWN_TARGET",
            "adapter_id_path": EXPECTED_ID_PATH, "attempt_limit": ATTEMPTS,
            "attempts_made": 0, "abort_reason": abort_reason, "mapping": map_snapshot,
            "start_utc": cmd_start_utc, "end_utc": cmd_end_utc,
            "duration_ms": (cmd_end_mono - cmd_start_mono) / 1_000_000,
        }, indent=2) + "\n")

    exit_code = 0 if status == "COMPLETE" and not metrics.get("failures", 0) else (1 if status == "COMPLETE" else 2 if status.startswith("ABORT") else 3)
    stdout_text = stdout_capture.getvalue()
    if status not in {"ABORT_PREFLIGHT", "ABORT_ERROR"}:
        stdout_text += json.dumps({"status": status, "run_id": run_id, "metrics": metrics,
                                   "abort_reason": abort_reason}, indent=2) + "\n"
    stderr_text = stderr_capture.getvalue()
    cmd_end_utc, cmd_end_mono = utc_now(), time.monotonic_ns()
    outer = {
        "outer_command_record": "PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python experiments/updi_rca/evidence/RCA_BOARD_SWAP_01/path_p/run_pre_campaign.py --id-path pci-0000:00:14.0-usb-0:4:1.0 --attempts 20 --baud 38400 --timeout 1.0 --target X --pairing P-to-X",
        "argv": sys.argv, "python_executable": sys.executable,
        "cwd": os.getcwd(), "start_utc": cmd_start_utc, "end_utc": cmd_end_utc,
        "monotonic_start_ns": cmd_start_mono, "monotonic_end_ns": cmd_end_mono,
        "duration_ms": (cmd_end_mono - cmd_start_mono) / 1_000_000,
        "exit_code": exit_code, "status": status, "abort_reason": abort_reason,
        "stdout": stdout_text, "stderr": stderr_text,
        "stdout_sha256": sha(stdout_text.encode()), "stderr_sha256": sha(stderr_text.encode()),
    }
    (OUT / "command.json").write_text(json.dumps(outer, indent=2) + "\n")
    sys.stdout.write(stdout_text)
    sys.stderr.write(stderr_text)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
