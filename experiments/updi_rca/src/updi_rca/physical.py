"""Analyze existing physical-layer evidence without opening a serial device."""

from .classify import classify_crossover, classify_pairing_matrix


def echo_details(expected: bytes, observed: bytes) -> dict:
    """Report byte differences; Hamming distance covers observed overlap only."""
    overlap = bytes(a ^ b for a, b in zip(expected, observed))
    mismatch = next((i for i, value in enumerate(overlap) if value), None)
    if mismatch is None and len(expected) != len(observed):
        mismatch = min(len(expected), len(observed))
    if expected == observed:
        category = "EXACT"
    elif not observed:
        category = "EMPTY"
    elif len(observed) < len(expected):
        category = "SHORT"
    elif len(observed) > len(expected):
        category = "EXTRA"
    elif any(observed == expected[i:] + expected[:i] for i in range(1, len(expected))):
        category = "SHIFTED"
    else:
        category = "CORRUPT"
    return {
        "class": category,
        "expected_len": len(expected), "actual_len": len(observed),
        "missing_byte_count": max(0, len(expected) - len(observed)),
        "extra_byte_count": max(0, len(observed) - len(expected)),
        "xor_hex": overlap.hex(),
        "hamming_distance_overlap": sum(value.bit_count() for value in overlap),
        "first_mismatch_index": mismatch,
    }


def analyze_sync(record: dict) -> dict:
    """Stop at the earliest failed exchange; later bytes cannot validate it."""
    result = {
        "classification": "UNKNOWN_SYNC", "failure_stage": "",
        "sync_complete": False, "request_reached": False,
        "target_response_reached": False, "breaks": [],
    }
    events = record.get("events", [])
    command_echo_ok = False
    for index, tx in enumerate(events):
        if tx.get("kind") == "response":
            payload = bytes.fromhex(tx.get("hex", ""))
            if command_echo_ok and payload and len(payload) == tx.get("requested"):
                result["target_response_reached"] = True
                result["classification"] = "TARGET_RESPONSE_REACHED"
            elif command_echo_ok:
                result["failure_stage"] = tx.get("stage") or "UPDI_CONTROL_RESPONSE"
                return result
            continue
        if tx.get("kind") != "tx":
            continue
        expected = bytes.fromhex(tx.get("hex", ""))
        is_break = tx.get("baud") == 300 and expected == b"\x00" and len(result["breaks"]) < 2
        echo = events[index + 1] if index + 1 < len(events) and events[index + 1].get("kind") == "echo" else None
        if tx.get("count") != len(expected):
            result.update(classification="HOST_TX_INCOMPLETE", failure_stage="HOST_TX")
            return result
        if echo is None:
            if is_break:
                result["breaks"].append({"ordinal": len(result["breaks"]) + 1, "class": "NOT_CAPTURED"})
            result.update(classification="ECHO_NOT_CAPTURED", failure_stage=record.get("failure_stage") or "UNKNOWN")
            return result
        observed = bytes.fromhex(echo.get("hex", ""))
        details = echo_details(expected, observed)
        if is_break:
            ordinal = len(result["breaks"]) + 1
            result["breaks"].append({
                "ordinal": ordinal, "tx_hex": expected.hex(), "echo_hex": observed.hex(),
                "timestamp_monotonic_ns": tx.get("ns"),
                "write_end_ns": tx.get("end_ns"), "read_start_ns": echo.get("ns"),
                "read_end_ns": echo.get("end_ns"),
                "latency_ms": (echo["end_ns"] - echo["ns"]) / 1_000_000 if "end_ns" in echo and "ns" in echo else None,
                **details,
            })
            if details["class"] != "EXACT":
                prefix = "BREAK1" if ordinal == 1 else "BREAK1_EXACT_BREAK2"
                suffix = "NO_ECHO" if details["class"] == "EMPTY" else "CORRUPT_ECHO"
                result.update(classification=f"{prefix}_{suffix}", failure_stage="LOCAL_ECHO")
                return result
            if ordinal == 2:
                result.update(sync_complete=True, classification="SYNC_COMPLETE")
        elif result["sync_complete"]:
            if record.get("mode") == "sib" and expected == b"\x55\xe6" or (
                record.get("mode") == "control" and len(expected) == 2 and expected[0] == 0x55 and 0x80 <= expected[1] <= 0x8F
            ):
                result.update(request_reached=True, classification="SIB_REQUEST_REACHED" if record["mode"] == "sib" else "CONTROL_REQUEST_REACHED")
            if details["class"] != "EXACT":
                result["failure_stage"] = "LOCAL_ECHO"
                return result
            command_echo_ok = True
    return result


def assess_causal_movement(cycles: list[tuple[dict, dict, dict]], *, single_variable: bool) -> dict:
    """Grade path/target locality, never an individual component or mechanism."""
    if not cycles:
        return {"domain": "UNRESOLVED", "status": "BLOCKED", "repeat_count": 0}
    domains = [classify_crossover(before, crossed) for before, crossed, _ in cycles]
    domain = domains[0] if len(set(domains)) == 1 else "MIXED_OR_INTERMITTENT"
    restored = all(classify_crossover(after, crossed) == domain for _, crossed, after in cycles)
    adequate = all(n >= 30 for cycle in cycles for state in cycle for _, n in state.values())
    isolated = domain in {"TARGET_LOCAL", "ADAPTER_PATH"}
    status = "UNRESOLVED"
    if single_variable and restored and isolated:
        status = "PROVEN" if len(cycles) >= 3 and adequate else "SUPPORTED"
    return {"domain": domain, "status": status, "repeat_count": len(cycles)}


def pairing_effects(results: dict[tuple[str, str], tuple[int, int]]) -> dict | None:
    """Descriptive success-rate effects; missing cells cannot be imputed."""
    if len(results) != 4:
        return None
    classify_pairing_matrix(results)
    a, b = sorted({adapter for adapter, _ in results})
    x, y = sorted({target for _, target in results})
    rates = {pair: successes / attempts for pair, (successes, attempts) in results.items()}
    ax, ay, bx, by = (rates[pair] for pair in ((a, x), (a, y), (b, x), (b, y)))
    return {
        "adapter_reference": a, "target_reference": x,
        "adapter_success_delta": ((ax + ay) - (bx + by)) / 2,
        "target_success_delta": ((ax + bx) - (ay + by)) / 2,
        "interaction_difference_of_differences": (ax - ay) - (bx - by),
    }
