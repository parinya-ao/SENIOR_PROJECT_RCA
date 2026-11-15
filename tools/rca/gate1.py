"""Offline Gate 1 evidence assessment. This module never opens a device."""

import copy
import hashlib
import statistics
from pathlib import Path

from tools.arq_trial import parse_event, status_complete
from tools.rca.analyze import parse_updi


def response(expected_length, expected_value, actual):
    """Preserve the difference between an unavailable capture and captured b''."""
    result = dict(
        expected_response_length=expected_length,
        expected_response_value=expected_value.hex() if expected_value is not None else None,
        actual_response_hex="UNKNOWN" if actual is None else actual.hex(),
        actual_response_length="UNKNOWN" if actual is None else len(actual),
        classification=None,
    )
    if actual is None or type(expected_length) is not int or expected_length < 0:
        result["classification"] = "EVIDENCE_INCOMPLETE"
    elif len(actual) != expected_length:
        result["classification"] = "UPDI_RESPONSE_LENGTH_MISMATCH"
    elif expected_value is not None and actual != expected_value:
        result["classification"] = "UPDI_RESPONSE_VALUE_MISMATCH"
    return result


def verify_hashes(directory, hashes):
    """Read only, including when a file is missing or its path escapes the bundle."""
    root = Path(directory).resolve()
    bad = []
    for name, expected in hashes.items():
        path = (root / name).resolve()
        if (
            not path.is_relative_to(root)
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            bad.append(name)
    return bad


def _status(raw, identity):
    rows = [parse_event(line) for line in raw.splitlines()]
    if not rows or any(row is None for row in rows):
        return False
    required = {
        "BOOT",
        "IDENTITY",
        "STATUS",
        "RESULT",
        "RTT_LAST",
        "RTT_MIN",
        "RTT_MAX",
        "RTT_COUNT",
        "RX_DONE_COUNT",
        "DECODE_ERRORS",
        "CONTROL_REJECTS",
        "REG",
        "STATUS_END",
    }
    if len(rows) != len(required) or {row["e"] for row in rows} != required:
        return False
    if any(int(row["s"], 16) != 0 for row in rows):
        return False
    for row in rows:
        row["role"] = identity["role"]
    status = next(row for row in rows if row["e"] == "STATUS")
    build = next(row for row in rows if row["e"] == "IDENTITY")
    return (
        rows[-1]["e"] == "STATUS_END"
        and status_complete(rows, identity["role"], 0)
        and status.get("ready") == "1"
        and status.get("overflow") == "0"
        and build.get("build") == identity["build"]
        and build.get("config") == identity["config"]
    )


def assess(records, identity, *, safe_path=False, owners=()):
    """Assess an offline replay, stopping at its first failure, never retrying.

    safe_path is an externally audited precondition, not permission to contact a
    device. This function and its callers here implement no hardware execution.
    """
    result = dict(
        verdict="GATE1_INCONCLUSIVE",
        classification="EVIDENCE_INCOMPLETE",
        attempted=0,
        passed=0,
        failed=0,
        timed_out=0,
        response_mismatches=0,
        monitor_crashes=0,
        identity_mismatches=0,
        first_failure=None,
        usb_disconnected="UNKNOWN",
        root_cause="UNKNOWN",
        latency_ms=dict(minimum="UNKNOWN", median="UNKNOWN", maximum="UNKNOWN"),
    )
    if not safe_path:
        result.update(verdict="GATE1_BLOCKED", classification="UNSAFE_COMMAND_PATH")
        return result
    if owners:
        result.update(verdict="GATE1_BLOCKED", classification="PORT_OWNERSHIP_CONFLICT")
        return result
    if not isinstance(identity, dict) or any(
        identity.get(key) in (None, "", "UNKNOWN")
        for key in ("signature", "serial", "build", "config", "role")
    ):
        result.update(verdict="GATE1_BLOCKED", classification="IDENTITY_MISMATCH")
        return result
    previous_end = -1
    durations = []
    for index, row in enumerate(records, 1):
        if index > 20:
            result.update(verdict="GATE1_INCONCLUSIVE", classification="EVIDENCE_INCOMPLETE")
            return result
        result["attempted"] += 1
        classification = None
        try:
            start, end = row.get("monotonic_start_ns"), row.get("monotonic_end_ns")
            if (
                row.get("transaction_index") != index
                or type(start) is not int
                or type(end) is not int
                or start < 0
                or start < previous_end
                or end < start
            ):
                classification = "EVIDENCE_INCOMPLETE"
            elif row.get("identity") != identity:
                classification = "IDENTITY_MISMATCH"
                result["identity_mismatches"] += 1
            elif row.get("request_tx_hex") != b"STATUS\n".hex():
                classification = "UNSAFE_COMMAND_PATH"
            elif row.get("timeout_reason"):
                classification = "UPDI_RESPONSE_TIMEOUT"
                result["timed_out"] += 1
            elif row.get("monitor_exit_code") is not None:
                classification = "MONITOR_EXIT"
                result["monitor_crashes"] += 1
            elif row.get("transport_error"):
                classification = "UNKNOWN_TRANSPORT_CAUSE"
                result["response_mismatches"] += int("mismatch" in row["transport_error"])
            else:
                exchanges = row.get("transport_exchanges")
                if not isinstance(exchanges, list) or not exchanges:
                    classification = "EVIDENCE_INCOMPLETE"
                else:
                    for exchange in exchanges:
                        actual = exchange.get("actual_hex")
                        expected = exchange.get("expected_hex")
                        checked = response(
                            exchange.get("expected_length"),
                            None if expected is None else bytes.fromhex(expected),
                            None if actual is None else bytes.fromhex(actual),
                        )
                        if checked["classification"]:
                            classification = checked["classification"]
                            result["response_mismatches"] += int("MISMATCH" in classification)
                            break
                if classification is None and not _status(row["status_payload_raw"], identity):
                    classification = "EVIDENCE_INCOMPLETE"
        except (KeyError, ValueError, TypeError, AttributeError):
            classification = "EVIDENCE_INCOMPLETE"
        if classification:
            failure = copy.deepcopy(row)
            failure["classification"] = classification
            if row.get("transport_error"):
                failure["parsed_error"] = parse_updi(row["transport_error"])
            result.update(
                verdict="GATE1_INCONCLUSIVE"
                if classification == "EVIDENCE_INCOMPLETE"
                else "GATE1_FAIL",
                classification=classification,
                failed=1,
                first_failure=failure,
            )
            return result
        durations.append((end - start) / 1_000_000)
        result["latency_ms"] = dict(
            minimum=min(durations), median=statistics.median(durations), maximum=max(durations)
        )
        previous_end = end
        result["passed"] += 1
    if result["passed"] == 20:
        result.update(verdict="GATE1_PASS", classification=None)
    return result
