"""Calculate reliability metrics from assessed, correlated test cases."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from tools.rf_stress.status import ResultStatus

if TYPE_CHECKING:
    from collections.abc import Sequence


def _percentile(values: Sequence[float], fraction: float) -> float | None:
    """Return a linearly interpolated percentile, or None without measurements."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def calculate_metrics(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Summarize rates with scheduled cases as the explicit denominator."""
    total = len(results)
    passed = sum(result["status"] == ResultStatus.SUCCESS for result in results)
    failed = sum(result["status"] == ResultStatus.FAILURE for result in results)
    unverified = sum(result["status"] == ResultStatus.UNVERIFIED for result in results)
    first_attempt = sum(
        result["status"] == ResultStatus.SUCCESS and result["retry_count"] == 0
        for result in results
    )
    retry_cases = [result for result in results if result["retry_count"] > 0]
    timeout_cases = [result for result in results if result["timeout_count"] > 0]
    latencies = [
        float(result["latency_ms"]) for result in results if result["latency_ms"] is not None
    ]
    rssi = [float(result["rssi_dbm"]) for result in results if result["rssi_dbm"] is not None]
    snr = [float(result["snr_db"]) for result in results if result["snr_db"] is not None]
    airtime = [int(result["airtime_us"]) for result in results if result["airtime_us"] is not None]
    reset_counts = [
        int(result["reset_count"]) for result in results if result.get("reset_count") is not None
    ]
    radio_errors = [error for result in results for error in (result.get("radio_errors") or [])]
    irq_flags = sorted(
        {int(flag) for result in results for flag in (result.get("irq_flags_seen") or [])}
    )

    return {
        "scheduled_transactions": total,
        "pass": passed,
        "fail": failed,
        "unverified": unverified,
        "application_delivery_success_rate": passed / total if total else None,
        "first_attempt_successes": first_attempt,
        "first_attempt_success_rate": first_attempt / total if total else None,
        "recovery_after_retry_rate": (
            sum(result["status"] == ResultStatus.SUCCESS for result in retry_cases)
            / len(retry_cases)
            if retry_cases
            else None
        ),
        "recovery_after_timeout_rate": (
            sum(result["status"] == ResultStatus.SUCCESS for result in timeout_cases)
            / len(timeout_cases)
            if timeout_cases
            else None
        ),
        "retries": sum(int(result["retry_count"]) for result in results),
        "timeouts": sum(int(result["timeout_count"]) for result in results),
        "duplicate_deliveries": sum(int(result["duplicate_deliveries"]) for result in results),
        "payload_mismatches": sum(int(result["payload_mismatches"]) for result in results),
        "false_ack_acceptance": sum(int(result["false_ack_acceptance"]) for result in results),
        "unexpected_resets": None,
        "reset_count": sum(reset_counts) if reset_counts else None,
        "rssi_dbm_mean": sum(rssi) / len(rssi) if rssi else None,
        "snr_db_mean": sum(snr) / len(snr) if snr else None,
        "airtime_us": sum(airtime) if airtime else None,
        "radio_error_codes": sorted({int(error) for error in radio_errors})
        if radio_errors
        else None,
        "irq_flags_seen": irq_flags or None,
        "latency_p50_ms": _percentile(latencies, 0.50),
        "latency_p95_ms": _percentile(latencies, 0.95),
        "latency_p99_ms": _percentile(latencies, 0.99),
        "latency_max_ms": max(latencies) if latencies else None,
    }
