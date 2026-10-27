"""Sequential execution for bounded probes with one raw record per attempt."""

from pathlib import Path
import re

from .probes import ProbeResult


def run_campaign(probe, attempts: int, raw_directory: str | Path, run_id: str) -> list[dict]:
    if attempts < 1:
        raise ValueError("campaign requires at least one attempt")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("run_id must contain only letters, digits, '_' or '-'")

    raw_directory = Path(raw_directory)
    rows = []
    for attempt in range(1, attempts + 1):
        raw_path = raw_directory / f"{run_id}-{attempt:04d}.json"
        result: ProbeResult = probe(raw_path)
        rows.append({
            "attempt": attempt,
            "result": "PASS" if result.success else "FAIL",
            "failure_stage": "" if result.success else result.stage,
            "error_type": result.error_type or "",
            "latency_ms": result.latency_ms,
            "tx_hex": result.tx.hex(),
            "echo_hex": result.echo.hex(),
            "response_hex": result.response.hex(),
            "source_log": result.raw_path,
            "raw_sha256": result.raw_sha256,
        })
    return rows
