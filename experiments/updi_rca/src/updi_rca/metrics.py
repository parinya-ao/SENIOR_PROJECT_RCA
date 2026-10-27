"""Small-sample rates and latency summaries using only the standard library."""

from collections import Counter
from math import ceil, sqrt
from statistics import median


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0 or successes < 0 or successes > total:
        raise ValueError("require 0 <= successes <= total and total > 0")
    p = successes / total
    z2 = z * z
    denominator = 1 + z2 / total
    center = (p + z2 / (2 * total)) / denominator
    margin = z * sqrt((p * (1 - p) + z2 / (4 * total)) / total) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def metric_summary(attempts: list[dict]) -> dict:
    if not attempts:
        raise ValueError("cannot summarize zero attempts")
    successes = sum(bool(item["success"]) for item in attempts)
    failures = len(attempts) - successes
    latencies = sorted(float(item["latency_ms"]) for item in attempts if item.get("latency_ms") is not None)
    stages = Counter(
        item.get("failure_stage") or item.get("stage") or "UNKNOWN"
        for item in attempts
        if not item["success"]
    )
    success_rate = successes / len(attempts)
    return {
        "attempts": len(attempts),
        "successes": successes,
        "failures": failures,
        "success_rate": success_rate,
        "failure_rate": failures / len(attempts),
        "success_percentage": success_rate * 100,
        "failure_percentage": failures / len(attempts) * 100,
        "median_latency_ms": median(latencies) if latencies else None,
        "p95_latency_ms": latencies[ceil(0.95 * len(latencies)) - 1] if latencies else None,
        "wilson_95": wilson_interval(successes, len(attempts)),
        "failure_stages": dict(sorted(stages.items())),
    }
