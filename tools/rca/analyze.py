"""Read-only, bounded RCA of archived reverse-raw/standby evidence. JSON to stdout."""

# Validation failures are collected into integrity_problems rather than escaping.

import argparse
import ast
import hashlib
import json
import re
import shlex
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# Reuse the existing event and Intel HEX parsers; importing does not open a port.
from tools.arq_trial import checked_events, parse_event  # noqa: E402 -- direct CLI path setup
from tools.device_detection.firmware_identity import (  # noqa: E402 -- direct CLI path setup
    normalize_ihex_region,
)

Json = Any
_REG_OP_MODE = 0x01
_REG_VERSION = 0x40
_OPMODE_RESERVED_MASK = 0xF8
_OPMODE_MODE_MASK = 0x07
_OPMODE_STANDBY = 0x05
_VERSION_MODE_MASK = 0xC0
_VERSION_SLEEP = 0x00
_VERSION_RX = 0x40
_VERSION_VALUE_MASK = 0x3F
_RX_TIMEOUT_NS = 15_000
_MAX_MANIFEST_ENTRIES = 2048

ADDRESSES = (
    0x42,
    1,
    6,
    7,
    8,
    9,
    0x4D,
    0x1D,
    0x1E,
    0x26,
    0x20,
    0x21,
    0x39,
    0x33,
    0x3B,
    0x11,
    0x40,
    0x41,
    0x0C,
    0x31,
    0x37,
    0x24,
    0x4B,
)


def delta(later: Json, earlier: Json, clock: str = "host") -> int:
    """Return elapsed time on the host clock or one MCU's clock."""
    if clock == "host":
        return int(later["host_ns"]) - int(earlier["host_ns"])
    if clock != "mcu" or later.get("role") != earlier.get("role"):
        msg = "independent MCU clocks cannot be subtracted"
        raise ValueError(msg)
    return int(later["t"]) - int(earlier["t"])


def parse_updi(message: str) -> Json:
    """Extract bounded request and response diagnostics from one UPDI error."""
    result: dict[str, Json] = {
        "message": message,
        "request_hex": None,
        "request_length": None,
        "response_hex": None,
        "response_length": None,
        "expected": None,
        "start_ns": None,
        "end_ns": None,
        "timeout_s": None,
        "parser_state": None,
        "port": None,
        "port_owner": None,
        "monitor_pid": None,
        "monitor_exit_code": None,
        "exception_type": None,
    }
    pattern = (
        r"expected (None|b'(?:\\.|[^'\\])*'|b\"(?:\\.|[^\"\\])*\"), "
        r"received (b'(?:\\.|[^'\\])*'|b\"(?:\\.|[^\"\\])*\")"
    )
    match = re.search(pattern, message)
    if match:
        expected, actual = map(ast.literal_eval, match.groups())
        result.update(
            expected="ANY_VALUE_EXACT_LENGTH_UNKNOWN" if expected is None else expected.hex(),
            response_hex=actual.hex(),
            response_length=len(actual),
            exception_type="TransportError",
        )
    elif "UPDI echo mismatch" in message:
        result["exception_type"] = "TransportError"
    request = re.search(r"last_tx=([0-9a-fA-F ]+)", message)
    if request:
        data = bytes.fromhex(request[1])
        result.update(request_hex=data.hex(), request_length=len(data))
    return result


def compare_snapshots(rx: str | None, tx: str | None) -> Json:
    """Compare register snapshots while accounting for expected mode changes."""
    if rx is None or tx is None:
        return {"status": "NOT CAPTURED", "registers": {}}
    a, b = bytes.fromhex(rx), bytes.fromhex(tx)
    if len(a) != len(ADDRESSES) or len(b) != len(ADDRESSES):
        msg = "snapshot length"
        raise ValueError(msg)
    rows = {}
    for addr, x, y in zip(ADDRESSES, a, b, strict=False):
        expected = (
            addr == _REG_OP_MODE
            and x & _OPMODE_RESERVED_MASK == y & _OPMODE_RESERVED_MASK
            and x & _OPMODE_MODE_MASK == _OPMODE_STANDBY
            and y & _OPMODE_MODE_MASK in (1, 3)
        ) or (
            addr == _REG_VERSION
            and x & _VERSION_MODE_MASK == _VERSION_SLEEP
            and y & _VERSION_MODE_MASK == _VERSION_RX
            and x & _VERSION_VALUE_MASK == y & _VERSION_VALUE_MASK
        )
        rows[f"{addr:02X}"] = (
            "MATCH" if x == y else "EXPECTED DIFFERENCE" if expected else "UNEXPECTED DIFFERENCE"
        )
    return {"status": "COMPARED", "registers": rows}


def classify(events: list[Json], *, transport_error: bool, integrity: bool) -> Json:
    """Classify a failed transaction from observed host and device events."""
    tx = [
        e
        for e in events
        if e.get("role") == "receiver" and e.get("e") == "RAW_TX" and e.get("rc") == "0"
    ]
    done = [
        e
        for e in events
        if e.get("role") == "receiver"
        and e.get("e") == "RAW_TX_DONE"
        and e.get("rc") == "0"
        and int(e.get("flags", "0")) & 8
    ]
    timeout = [e for e in events if e.get("role") == "sender" and e.get("e") == "RAW_RX_TIMEOUT"]
    overflow = any(e.get("overflow", "0") != "0" for e in events)
    ready = [
        e
        for e in events
        if e.get("role") == "sender" and e.get("e") == "RAW_RX_READY" and e.get("rc") == "0"
    ]
    negative = bool(
        len(tx) == len(done) == len(timeout) == len(ready) == 1
        and not overflow
        and int(timeout[0]["t"]) - int(ready[0]["t"]) >= _RX_TIMEOUT_NS
        and ready[0].get("host_ns", float("inf")) < tx[0].get("host_ns", 0)
        and not any(e.get("e") == "RAW_RX" for e in events)
    )
    classification = (
        "EVIDENCE_CORRUPTED"
        if not integrity
        else "HOST_TRANSPORT_ERROR"
        if transport_error
        else "PHYSICAL_RF_FAILURE_UNISOLATED"
        if negative
        else "EVIDENCE_INCOMPLETE"
    )
    return {
        "classification": classification,
        "rf_verdict": "FAIL" if negative and integrity and not transport_error else "INCONCLUSIVE",
        "root_cause": "UNKNOWN",
        "evidence_completeness": "PASS"
        if negative and integrity and not transport_error
        else "INCOMPLETE",
        "tx_started": True if tx else None,
        "radiated_rf": None,
        "received_packet_count": None,
        "usb_disconnected": None,
        "reset_during_send": None,
    }


def analyze(
    directory: str | Path,
) -> Json:
    """Validate and summarize one archived RCA evidence bundle."""
    directory = Path(directory).resolve()
    problems: list[str] = []
    used_bytes = 0

    def read(name: str) -> bytes:
        nonlocal used_bytes
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise ValueError("missing/unsafe file: " + name)
        size = path.stat().st_size
        used_bytes += size
        if size > 16 * 1024 * 1024 or used_bytes > 64 * 1024 * 1024:
            msg = "evidence size bound exceeded"
            raise TypeError(msg)
        return path.read_bytes()

    def load(name: str) -> Json:
        def unique(pairs: list[tuple[str, Json]]) -> dict[str, Json]:
            obj = {}
            for k, v in pairs:
                if k in obj:
                    msg = "duplicate JSON key"
                    raise ValueError(msg)
                obj[k] = v
            return obj

        return json.loads(read(name), object_pairs_hook=unique)

    result: dict[str, Json] = {
        "incident_id": directory.name,
        "observed_events": [],
        "missing_evidence": [],
        "hypotheses": [],
        "recommended_next_experiment": (
            "Capture UPDI and MCU VDD/3V3-LORA synchronously; separate authorization required."
        ),
        "evidence_integrity": "FAIL",
        "identity_checks": [],
        "transport": [],
        "timeline": [],
        "mcu_timelines": {},
        "root_cause": "UNKNOWN",
    }
    try:
        standby = not (directory / "bundle.json").exists()
        b = load("standby-verified.json" if standby else "bundle.json")
        if not isinstance(b, dict):
            msg = "manifest must be an object"
            raise TypeError(msg)
        files = load("integrity-sha256.json") if standby else b.get("files")
        if not isinstance(files, dict) or not files or len(files) > _MAX_MANIFEST_ENTRIES:
            msg = "invalid file manifest"
            raise ValueError(msg)
        if not standby and (directory / "integrity-sha256.json").exists():
            supplemental = load("integrity-sha256.json")
            if not isinstance(supplemental, dict) or len(supplemental) > _MAX_MANIFEST_ENTRIES:
                msg = "invalid supplemental manifest"
                raise ValueError(msg)
            for name, value in supplemental.items():
                if name in files and files[name] != value:
                    problems.append("conflicting manifest hash: " + name)
                else:
                    files[name] = value
            if len(files) > _MAX_MANIFEST_ENTRIES:
                msg = "combined manifest entry bound exceeded"
                raise ValueError(msg)
        for name, expected in files.items():
            try:
                if not isinstance(expected, str) or not re.fullmatch("[a-f0-9]{64}", expected):
                    raise ValueError("invalid hash: " + name)
                if hashlib.sha256(read(name)).hexdigest() != expected:
                    raise ValueError("hash mismatch: " + name)
            except (OSError, ValueError) as error:
                problems.append(str(error))
        events = load("status.json") if standby else b.get("events")
        commands: Json = [] if standby else b.get("commands")
        if not isinstance(events, list) or not isinstance(commands, list):
            msg = "invalid event/command list"
            raise TypeError(msg)
        for e in events:
            if not isinstance(e, dict) or not {"t", "e", "s", "role", "host_ns"} <= e.keys():
                msg = "invalid journal entry"
                raise TypeError(msg)
            if (
                e["role"] not in ("sender", "receiver")
                or type(e["host_ns"]) is not int
                or e["host_ns"] < 0
            ):
                msg = "invalid clock/role"
                raise ValueError(msg)
            if any(not isinstance(e[k], str) for k in e if k != "host_ns"):
                msg = "invalid event types"
                raise ValueError(msg)
            parse_event("A " + " ".join(f"{k}={v}" for k, v in e.items()))
        for c in commands:
            if (
                not isinstance(c, dict)
                or c.get("role") not in ("sender", "receiver")
                or not isinstance(c.get("text"), str)
                or type(c.get("host_ns")) is not int
            ):
                msg = "invalid command"
                raise ValueError(msg)
        try:
            for role in ("sender", "receiver"):
                read(f"rf-monitor-{role}.stdout.log")
            checked_events(events, directory)
        except (OSError, ValueError) as error:
            problems.append(str(error))
        for role in ("sender", "receiver"):
            name = f"rf-monitor-{role}.stderr.log"
            message = read(name).decode(errors="replace")
            if message:
                info = parse_updi(message)
                info["role"] = role
                command = shlex.split(read(f"rf-monitor-{role}.command.log").decode())
                info["port"] = command[-2]
                info["baud"] = command[-1]
                result["transport"].append(info)
            identities = [e for e in events if e["role"] == role and e["e"] == "IDENTITY"]
            image = role + "_arq.hex" if standby else role + "_reverse_raw.hex"
            raw = read(image)
            declared = b["firmware"][role]
            expected = declared if standby else declared["sha256"]
            if hashlib.sha256(raw).hexdigest() != expected:
                problems.append("firmware hash mismatch: " + role)
            binary = normalize_ihex_region(raw.decode(), 0, 131072)
            if not identities:
                problems.append("missing firmware identity: " + role)
            for identity in identities:
                if identity["build"].encode() not in binary:
                    problems.append("embedded identity mismatch: " + role)
                if not standby and identity["build"] != declared["build_id"]:
                    problems.append("declared build mismatch: " + role)
                result["identity_checks"].append(
                    {
                        "role": role,
                        "build": identity["build"],
                        "config": identity["config"],
                        "image_sha256": hashlib.sha256(raw).hexdigest(),
                    }
                )
        configs = {e["config"] for e in events if e["e"] == "IDENTITY"}
        if len(configs) != 1:
            problems.append("configuration identities disagree")
        if (directory / "source-hashes.json").exists():
            source_hashes = load("source-hashes.json")
            if not isinstance(source_hashes, dict):
                msg = "invalid source manifest"
                raise ValueError(msg)
            for name, expected in source_hashes.items():
                if hashlib.sha256(read("source/" + name)).hexdigest() != expected:
                    problems.append("source identity mismatch: " + name)
        if (directory / "source/config/arq_test.toml").exists():
            config = tomllib.loads(read("source/config/arq_test.toml").decode())
            expected = hashlib.sha256(
                json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            if configs != {expected}:
                problems.append("source configuration mismatch")
        transport = bool(
            result["transport"]
            or b.get("capture_errors")
            or b.get("failure_reason") == "monitor exited"
        )
        result.update(classify(events, transport_error=transport, integrity=not problems))
        if standby:
            result.update(
                classification="EVIDENCE_CORRUPTED" if problems else "STANDBY_RESTORE_OBSERVED",
                rf_verdict="NOT_RUN",
                evidence_completeness="NOT_APPLICABLE_TO_RF",
            )
        result["evidence_integrity"] = "FAIL" if problems else "PASS"
        result["observed_events"] = events
        result["timeline"] = sorted(
            [dict(x, kind="HOST_COMMAND") for x in commands]
            + [dict(x, kind="DEVICE_EVENT_RECEIVED") for x in events],
            key=lambda x: x["host_ns"],
        )
        result["mcu_timelines"] = {
            role: [e for e in events if e["role"] == role] for role in ("sender", "receiver")
        }
        rx = next((e.get("bytes") for e in events if e["e"] == "RAW_RX_ACTIVE"), None)
        tx = next((e.get("bytes") for e in events if e["e"] == "RAW_TX_STATE"), None)
        result["operational_snapshot_comparison"] = compare_snapshots(rx, tx)
        result["missing_evidence"] = [
            name
            for name in ("RAW_TX_PRE", "RAW_TX_STATE", "RAW_RX_DONE", "RAW_RX_TIMEOUT")
            if not any(e["e"] == name for e in events)
        ]
        result["restore_record"] = (
            load("restore.json") if (directory / "restore.json").exists() else None
        )
        result["hypotheses"] = [
            {"id": h, "status": "HYPOTHESIS", "confidence": "INSUFFICIENT_EVIDENCE"}
            for h in (("H3", "H5", "H6") if transport else ("H8", "H9", "H10", "H11", "H12"))
        ]
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError) as error:
        problems.append(str(error))
        result.update(classify([], transport_error=False, integrity=False))
    result["integrity_problems"] = problems
    return result


def main(argv: list[str] | None = None) -> int:
    """Print one evidence audit and return its integrity status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args(argv)
    result = analyze(args.evidence)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["evidence_integrity"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
