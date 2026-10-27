"""Conservative failure-stage classification and deterministic evidence weights."""

STAGES = {
    "PORT_DISCOVERY", "SERIAL_OPEN", "USB_HOST", "HOST_TX", "LOCAL_ECHO",
    "UPDI_PHY_CONTROL", "UPDI_CONTROL_RESPONSE", "ACC_ACK", "ACC_DATA_RESPONSE",
    "OCD_STATUS", "OCD_MESSAGE", "TARGET_RUNTIME", "TARGET_RESET",
    "FLASH_PROGRAM", "FLASH_VERIFY", "PASS", "UNKNOWN",
}


def _bytes(value: str | None) -> bytes | None:
    if value is None:
        return None
    return bytes.fromhex(value.replace(" ", ""))


def classify_event(event: dict) -> str:
    if event.get("result") == "pass":
        return "PASS"
    stage = event.get("stage")
    if stage in STAGES and stage != "PASS":
        return stage

    error = " ".join(str(event.get(key, "")) for key in ("error_type", "errno", "kernel_usb_error", "message")).upper()
    if any(code in error for code in ("EPROTO", "EILSEQ", "DISCONNECT")):
        return "USB_HOST"
    if "NO SUCH FILE" in error or "PORT_MISSING" in error or "MISSING TTY" in error:
        return "PORT_DISCOVERY"
    if "SERIAL OPEN" in error or "PERMISSION DENIED" in error or "DEVICE OR RESOURCE BUSY" in error:
        return "SERIAL_OPEN"
    if "UPDI LINK INITIALIZATION" in error:
        return "UPDI_PHY_CONTROL"
    tx = _bytes(event.get("tx_hex"))
    echo = _bytes(event.get("echo_hex"))
    if tx is not None and event.get("tx_count") is not None and event["tx_count"] != len(tx):
        return "HOST_TX"
    if tx is not None and (echo is None or echo != tx):
        return "LOCAL_ECHO"

    operation = str(event.get("operation", "")).upper()
    error_type = str(event.get("error_type", "")).upper()
    if "FLASH PROGRAM" in operation or "PROGRAM_FAILED" in error_type:
        return "FLASH_PROGRAM"
    if "OCD_STATUS" in operation or "OCD STATUS" in operation:
        return "OCD_STATUS"
    if "OCD_MESSAGE" in operation or "OCD MESSAGE" in operation:
        return "OCD_MESSAGE"
    if "FLASH_VERIFY" in operation:
        return "FLASH_VERIFY"
    if "STS ACK" in operation or "ACK" in error_type and operation.startswith("STS"):
        return "ACC_ACK"
    if event.get("expected_len") is not None and event.get("actual_len") != event["expected_len"]:
        if operation.startswith("LDCS") or operation == "SIB":
            return "UPDI_CONTROL_RESPONSE"
        if operation.startswith("LDS"):
            return "ACC_DATA_RESPONSE"
    if "INITIALIZATION" in error or "BREAK" in operation:
        return "UPDI_PHY_CONTROL"
    if "TARGET_RESET" in error or event.get("new_boot_observed"):
        return "TARGET_RESET"
    if "TARGET_RUNTIME" in error:
        return "TARGET_RUNTIME"
    return "UNKNOWN"


def is_fresh_reset(event: dict) -> bool:
    """BORF is historical unless an independent boot marker changed or a boot was seen."""
    before, after = event.get("boot_id_before"), event.get("boot_id_after")
    return bool(event.get("new_boot_observed")) or (before is not None and after is not None and before != after)


def _success_rate(result: tuple[int, int]) -> float:
    successes, attempts = result
    if attempts <= 0 or successes < 0 or successes > attempts:
        raise ValueError("pairing result must satisfy 0 <= successes <= attempts and attempts > 0")
    return successes / attempts


def classify_pairing_matrix(results: dict[tuple[str, str], tuple[int, int]]) -> str:
    """Classify a complete 2x2 adapter/target matrix without forcing interactions."""
    if len(results) != 4:
        raise ValueError("a 2x2 pairing matrix requires exactly four cells")
    adapters = sorted({adapter for adapter, _ in results})
    targets = sorted({target for _, target in results})
    if len(adapters) != 2 or len(targets) != 2 or set(results) != {
        (adapter, target) for adapter in adapters for target in targets
    }:
        raise ValueError("pairing results must cover two adapters by two targets")

    rates = {pair: _success_rate(result) for pair, result in results.items()}
    a, b = adapters
    x, y = targets
    target_x_deltas = (rates[(a, x)] - rates[(a, y)], rates[(b, x)] - rates[(b, y)])
    adapter_p_deltas = (rates[(a, x)] - rates[(b, x)], rates[(a, y)] - rates[(b, y)])
    target_follows = all(delta >= 0.8 for delta in target_x_deltas) or all(
        delta <= -0.8 for delta in target_x_deltas
    )
    adapter_follows = all(delta >= 0.8 for delta in adapter_p_deltas) or all(
        delta <= -0.8 for delta in adapter_p_deltas
    )
    if target_follows and adapter_follows:
        return "MULTIPLE_MAIN_EFFECTS_OR_INTERACTION"
    if target_follows:
        return "TARGET_LOCAL"
    if adapter_follows:
        return "ADAPTER_PATH"

    interaction = target_x_deltas[0] - target_x_deltas[1]
    if abs(interaction) >= 0.8:
        return "TWO_FACTOR_INTERACTION"
    if all(rate >= 0.95 for rate in rates.values()):
        return "ALL_PASS"
    if all(rate <= 0.05 for rate in rates.values()):
        return "ALL_FAIL_AMBIGUOUS"
    return "MIXED_OR_INTERMITTENT"


def classify_crossover(
    before: dict[tuple[str, str], tuple[int, int]],
    crossed: dict[tuple[str, str], tuple[int, int]],
) -> str:
    """Classify before/crossed pairs, preserving intervention and interaction ambiguity."""
    if len(before) != 2 or len(crossed) != 2 or set(before) & set(crossed):
        raise ValueError("before and crossed results must be two disjoint pairings each")
    matrix = {**before, **crossed}
    classify_pairing_matrix(matrix)  # Validate a complete, balanced 2x2 mapping.
    before_rates = [_success_rate(value) for value in before.values()]
    crossed_rates = [_success_rate(value) for value in crossed.values()]
    if min(crossed_rates) >= 0.95 and min(before_rates) <= 0.5:
        return "INTERVENTION_SENSITIVE"
    if max(crossed_rates) <= 0.05:
        return "CROSSED_BOTH_FAIL_AMBIGUOUS"
    return classify_pairing_matrix(matrix)


def score_evidence(domain: str, facts: dict) -> int:
    """Return the prompt's additive prioritization score; this is not a probability."""
    score = 0
    if facts.get("same_external_chain_board_changes"):
        score += 8 if domain in {"A", "B", "C", "D", "E", "H"} else -6 if domain == "G" else 0
    if facts.get("local_echo_mismatch"):
        score += 6 if domain in {"B", "G", "H"} else 0
        score -= 4 if domain == "F" and facts.get("pure_acc_hypothesis") else 0
        score -= 3 if domain == "F" and facts.get("pure_application_hypothesis") else 0
    if facts.get("exact_echo_response_missing"):
        score += 4 if domain in {"A", "B", "C", "D"} else 2 if domain == "F" else 0
    if facts.get("control_stable_running_data_failure"):
        score += 7 if domain in {"A", "C", "D", "F"} else -5 if domain == "G" else 0
    if facts.get("stopped_pass_running_failure"):
        score += 8 if domain in {"A", "C", "D", "F"} else 0
        score += 4 if domain == "H" and facts.get("cpu_load_sensitive_board_fault") else 0
    if facts.get("fresh_borf_with_new_boot") and domain == "A":
        score += 8
    if facts.get("borf_without_new_boot") and domain == "C":
        score += 1
    if facts.get("fuses_differ") and domain == "E":
        score += 7
    if facts.get("fuses_identical") and domain == "E":
        score -= 6
    if facts.get("same_firmware_hash_verified") and domain == "F":
        score -= 6
    if facts.get("usb_error_correlated") and domain == "G":
        score += 7
    if facts.get("clean_usb_exact_echo_target_timeout"):
        score += -5 if domain == "G" else 3 if domain in {"A", "B", "C", "D"} else 0
    if facts.get("silent_firmware") and facts.get("ocdmv_reasserted") and domain in {"D", "F"}:
        score += 6
    return score


def confidence_label(facts: dict) -> str:
    """Assign only the confidence levels justified by explicit evidence fields."""
    if facts.get("direct_measurement_proves_violation"):
        return "PROVEN"
    if facts.get("component_specific") and facts.get("measurement_available") is False:
        return "BLOCKED"
    if facts.get("aba_cycles", 0) >= 3 and facts.get("single_variable") and not facts.get("contradictory_evidence"):
        return "PROVEN"
    if facts.get("required_prediction_contradicted"):
        return "FALSIFIED"
    if facts.get("repeated_falsifier"):
        return "DISFAVORED"
    if facts.get("requires_physical_measurement") and facts.get("measurement_available") is False:
        return "BLOCKED"
    if facts.get("repeated_boundary_isolation"):
        return "STRONGLY_SUPPORTED"
    if facts.get("supports") or facts.get("attempts", 0) and facts.get("failures", 0):
        return "SUPPORTED"
    return "UNRESOLVED"
