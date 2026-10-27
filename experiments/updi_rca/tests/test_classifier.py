from updi_rca import classify
from updi_rca.classify import confidence_label


def _classify(name, *args):
    function = getattr(classify, name, None)
    assert function is not None, f"missing {name} classifier"
    return function(*args)


def test_failure_following_target_classifies_target_local():
    before = {("P", "X"): (10, 10), ("Q", "Y"): (0, 10)}
    crossed = {("P", "Y"): (0, 100), ("Q", "X"): (100, 100)}

    assert _classify("classify_crossover", before, crossed) == "TARGET_LOCAL"


def test_failure_following_adapter_classifies_adapter_path():
    before = {("P", "X"): (10, 10), ("Q", "Y"): (0, 10)}
    crossed = {("P", "Y"): (100, 100), ("Q", "X"): (0, 100)}

    assert _classify("classify_crossover", before, crossed) == "ADAPTER_PATH"


def test_both_pass_after_reconnection_is_intervention_sensitive():
    before = {("P", "X"): (10, 10), ("Q", "Y"): (0, 10)}
    crossed = {("P", "Y"): (100, 100), ("Q", "X"): (100, 100)}

    assert _classify("classify_crossover", before, crossed) == "INTERVENTION_SENSITIVE"


def test_both_crossed_pairings_fail_without_claiming_both_targets_failed():
    before = {("P", "X"): (10, 10), ("Q", "Y"): (0, 10)}
    crossed = {("P", "Y"): (0, 100), ("Q", "X"): (0, 100)}

    assert _classify("classify_crossover", before, crossed) == "CROSSED_BOTH_FAIL_AMBIGUOUS"


def test_interaction_matrix_does_not_force_single_cause():
    matrix = {
        ("P", "X"): (100, 100),
        ("P", "Y"): (100, 100),
        ("Q", "X"): (100, 100),
        ("Q", "Y"): (0, 100),
    }

    assert _classify("classify_pairing_matrix", matrix) == "TWO_FACTOR_INTERACTION"


def test_one_isolated_timeout_never_proves_a_cause():
    assert confidence_label({"attempts": 1, "failures": 1, "supports": True}) == "SUPPORTED"


def test_repeated_board_only_aba_proves_board_locality_but_not_component():
    assert confidence_label({
        "aba_cycles": 3,
        "single_variable": True,
        "board_only": True,
        "contradictory_evidence": False,
    }) == "PROVEN"
    assert confidence_label({
        "aba_cycles": 3,
        "single_variable": True,
        "board_only": True,
        "component_specific": True,
        "measurement_available": False,
    }) == "BLOCKED"


def test_component_claim_needs_direct_measurement_or_remains_blocked():
    assert confidence_label({
        "component_specific": True,
        "repeated_boundary_isolation": True,
        "measurement_available": False,
    }) == "BLOCKED"
    assert confidence_label({
        "direct_measurement_proves_violation": True,
    }) == "PROVEN"


def test_contradicted_predictions_are_falsified_and_weak_fit_is_disfavored():
    assert confidence_label({"required_prediction_contradicted": True}) == "FALSIFIED"
    assert confidence_label({"repeated_falsifier": True}) == "DISFAVORED"
