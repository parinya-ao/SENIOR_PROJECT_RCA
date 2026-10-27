"""Board-swap views of the existing raw synchronization and locality evidence."""

from .classify import classify_crossover
from .physical import analyze_sync, assess_causal_movement


def sib_outcome(record: dict) -> str:
    result = analyze_sync(record)
    if result["classification"].startswith("BREAK1"):
        return result["classification"]
    if result["failure_stage"] not in {"", "LOCAL_ECHO", "UPDI_CONTROL_RESPONSE"}:
        return result["failure_stage"]
    if not result["sync_complete"]:
        return result["classification"]
    if not result["request_reached"]:
        return "SYNC_COMPLETE_SIB_NOT_SENT"
    if result["failure_stage"] == "LOCAL_ECHO":
        return "SIB_TX_ECHO_FAIL"
    if result["target_response_reached"]:
        return "SIB_PASS"
    return "SIB_TX_ECHO_OK_RESPONSE_MISSING"


def restoration_assessment(original: dict, crossed: dict, *, restored: dict | None) -> dict:
    """Retain a tentative crossover effect without granting proof before restore."""
    if restored is None:
        return {"domain": classify_crossover(original, crossed), "status": "BLOCKED", "repeat_count": 0}
    return assess_causal_movement([(original, crossed, restored)], single_variable=True)


def post_swap_assessment(original: dict, crossed: dict, *, restored: dict | None = None,
                         power_cycle: str = "UNKNOWN", baseline_stationary: bool = False) -> dict:
    """A historical pattern suggests a branch; uncontrolled intervention grants no proof."""
    domain = classify_crossover(original, crossed)
    candidate = {
        "TARGET_LOCAL": "TARGET_FOLLOWING", "ADAPTER_PATH": "PATH_FOLLOWING",
        "CROSSED_BOTH_FAIL_AMBIGUOUS": "SHARED_FAILURE",
        "TWO_FACTOR_INTERACTION": "INTERACTION",
        "MULTIPLE_MAIN_EFFECTS_OR_INTERACTION": "INTERACTION",
    }.get(domain, domain)
    result = {"candidate": candidate, "status": "UNRESOLVED",
              "restore_measured": restored is not None, "power_cycle": power_cycle,
              "baseline_stationary": baseline_stationary}
    if restored is not None and baseline_stationary and power_cycle == "CONTROLLED":
        result["status"] = restoration_assessment(original, crossed, restored=restored)["status"]
    return result
