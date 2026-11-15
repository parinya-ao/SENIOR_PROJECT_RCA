#!/usr/bin/env python3
"""Read-only 15-second UPDI idle control; does not issue an application command."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "config"))
sys.path.insert(0, str(ROOT / "third_party" / "upditerm"))

import rf_proof as rf
import upditerm
from arq_trial import close_updi_without_recovery, read_reset_state, sample_updi_idle


def run() -> Path:
    artifacts = ROOT / "artifacts" / "arq"
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-updi-idle-control")
    run_dir = artifacts / run_id
    suffix = 0
    while run_dir.exists():
        suffix += 1
        run_dir = artifacts / f"{run_id}-{suffix}"
    proof = rf.ProofRun(run_dir)
    port = rf.PORTS["receiver"]
    record = dict(
        scope="non-RF UPDI idle control",
        device_role="Tracker",
        device_path=port,
        interval_seconds=15,
        rf_commands=0,
        cpu_reset_requested=False,
        startup_breaks=2,
    )
    session = None
    try:
        standby_files = sorted(
            artifacts.glob("*-standby/standby-verified.json"),
            key=lambda path: path.stat().st_mtime_ns,
        )
        if not standby_files:
            raise RuntimeError("no verified normal standby evidence")
        standby_path = standby_files[-1]
        standby = json.loads(standby_path.read_text())
        if not standby.get("standby") or standby.get("rf_transmissions") != 0:
            raise RuntimeError("latest normal standby evidence is not verified")
        record["standby_evidence"] = str(standby_path.relative_to(ROOT))
        record["firmware_sha256"] = standby["firmware"]["receiver"]
        owners = rf.check_port_owners(proof, "idle-control")
        if owners:
            raise RuntimeError("serial ports owned: " + ", ".join(owners))
        session = upditerm.SerialUPDI(port, 38400)
        record["baseline"] = read_reset_state(session, upditerm)
        record["sample"] = sample_updi_idle(session, upditerm, 15)
        record["result"] = (
            "NO_RESET_OBSERVED"
            if record["sample"]["before"]["gpior0"] == record["sample"]["after"]["gpior0"]
            and record["sample"]["before"]["rstfr"] == record["sample"]["after"]["rstfr"]
            else "RESET_STATE_CHANGED"
        )
    except Exception as error:
        record.update(
            result="ERROR", exception_type=type(error).__name__, exception_message=str(error)
        )
    finally:
        if session and session.updi:
            try:
                session.updi.sts8(upditerm.UART_FLAGS, 0)
                record["uart_cleanup"] = "disabled"
            except Exception as error:
                record["uart_cleanup_error"] = f"{type(error).__name__}: {error}"
            close_updi_without_recovery(session)
        record["utc_end"] = datetime.now(UTC).isoformat()
        (run_dir / "idle-control.json").write_text(json.dumps(record, indent=2) + "\n")
        (run_dir / "idle_control.py").write_bytes(Path(__file__).read_bytes())
        hashes = {
            str(path.relative_to(run_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(run_dir.rglob("*"))
            if path.is_file() and path.name != "sha256.json"
        }
        (run_dir / "sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return run_dir


if __name__ == "__main__":
    print(run())
