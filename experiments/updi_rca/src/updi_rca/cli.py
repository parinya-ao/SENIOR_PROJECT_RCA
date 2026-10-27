"""Small read-only command-line entry point for inventory and probes."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .identity import BoardIdentity, discover_serial_ports, resolve_connection
from .metrics import metric_summary
from .probes import run_control_read, run_data_read, run_ocd_message_probe, run_sib_probe
from .runner import run_campaign


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="updi-rca")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inventory", help="list adapters by stable ID_PATH")

    baseline = commands.add_parser("baseline", help="run 100 bounded read-only SIB and control probes")
    baseline.add_argument("id_path", help="stable udev ID_PATH, never a ttyUSB number")
    baseline.add_argument("raw_directory", type=Path)
    baseline.add_argument("--attempts", type=int, default=100)
    baseline.add_argument("--baud", type=int, default=38400)
    baseline.add_argument("--timeout", type=float, default=1.0)

    probe = commands.add_parser("probe", help="run one bounded, read-only probe")
    probe.add_argument("mode", choices=("sib", "control", "read", "ocd-message"))
    probe.add_argument("id_path")
    probe.add_argument("output", type=Path)
    probe.add_argument("--baud", type=int, default=38400)
    probe.add_argument("--address", type=lambda value: int(value, 0))
    probe.add_argument("--timeout", type=float, default=1.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    adapters = discover_serial_ports()
    if args.command == "inventory":
        rows = [
            {**asdict(adapter), "target_identity": "UNKNOWN_TARGET"}
            for adapter in adapters
        ]
        print(json.dumps(rows, indent=2))
        return 0

    if args.command == "baseline":
        if args.attempts < 1:
            _parser().error("--attempts must be positive")
        connection = resolve_connection(args.id_path, adapters, {args.id_path: BoardIdentity()})
        suffix = hashlib.sha256(args.id_path.encode()).hexdigest()[:8]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        base_run_id = f"baseline-{stamp}-{suffix}"
        condition_results = {}
        for mode, probe in (("sib", run_sib_probe), ("control", run_control_read)):
            run_id = f"{base_run_id}-{mode}"
            def one_attempt(raw_path, probe=probe):
                return probe(connection, args.baud, raw_path, timeout=args.timeout)
            rows = run_campaign(one_attempt, args.attempts, args.raw_directory / mode, run_id)
            metrics = metric_summary([
                {"success": row["result"] == "PASS", "failure_stage": row["failure_stage"],
                 "latency_ms": row["latency_ms"]}
                for row in rows
            ])
            summary_path = args.raw_directory / mode / f"{run_id}-summary.json"
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(json.dumps({"run_id": run_id, "metrics": metrics, "attempts": rows},
                                               indent=2) + "\n", encoding="utf-8")
            condition_results[mode] = {"run_id": run_id, "raw_directory": str(summary_path.parent),
                                       "summary": str(summary_path), "metrics": metrics}
        output = {
            "run_id": base_run_id, "adapter_id_path": connection.adapter.id_path,
            "adapter_serial": connection.adapter.usb_serial,
            "current_tty_at_start": connection.adapter.current_tty,
            "board_id": connection.board.board_id or "UNKNOWN_TARGET",
            "target_identity": "UNKNOWN_TARGET", "baud": args.baud,
            "attempts_per_condition": args.attempts,
            "write_policy": "no STCS, STS, programming key, reset, or NVM write",
            "conditions": condition_results,
        }
        print(json.dumps(output, indent=2))
        return 0 if all(item["metrics"]["failures"] == 0 for item in condition_results.values()) else 1

    if args.mode == "read" and args.address is None:
        _parser().error("read probe requires --address")
    if args.mode != "read" and args.address is not None:
        _parser().error("--address is only valid with read")
    connection = resolve_connection(args.id_path, adapters, {args.id_path: BoardIdentity()})
    options = {"timeout": args.timeout}
    if args.mode == "sib":
        result = run_sib_probe(connection, args.baud, args.output, **options)
    elif args.mode == "control":
        result = run_control_read(connection, args.baud, args.output, **options)
    elif args.mode == "ocd-message":
        result = run_ocd_message_probe(connection, args.baud, args.output, **options)
    else:
        result = run_data_read(connection, args.address, args.baud, args.output, **options)
    print(json.dumps({
        "success": result.success,
        "stage": result.stage,
        "tx_hex": result.tx.hex(),
        "echo_hex": result.echo.hex(),
        "response_hex": result.response.hex(),
        "latency_ms": result.latency_ms,
        "error_type": result.error_type,
        "raw_path": result.raw_path,
        "raw_sha256": result.raw_sha256,
    }, indent=2))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
