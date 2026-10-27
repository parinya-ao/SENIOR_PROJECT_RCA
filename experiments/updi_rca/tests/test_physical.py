"""Catch identity leakage, skipped echo gates, and unjustified causal proof."""

from dataclasses import FrozenInstanceError
import importlib
import importlib.util

import pytest

from updi_rca.identity import AdapterIdentity, BoardIdentity, ConnectionIdentity, snapshot_pairing
from updi_rca.classify import classify_crossover, classify_pairing_matrix


def connection(path="path-P", tty="/dev/ttyUSB0"):
    return ConnectionIdentity(AdapterIdentity("10c4", "ea60", "0001", path, "/sys/usb", tty), BoardIdentity())


def physical(name, *args, **kwargs):
    assert importlib.util.find_spec("updi_rca.physical") is not None, "missing physical evidence analysis"
    return getattr(importlib.import_module("updi_rca.physical"), name)(*args, **kwargs)


def exchange(tx, echo, baud=300):
    return [
        {"kind": "tx", "hex": tx, "count": len(bytes.fromhex(tx)), "baud": baud, "ns": 1, "end_ns": 2},
        {"kind": "echo", "hex": echo, "requested": len(bytes.fromhex(tx)), "baud": baud, "ns": 3, "end_ns": 1000003},
    ]


ORIGINAL = {("P", "X"): (100, 100), ("Q", "Y"): (0, 100)}
TARGET = {("P", "Y"): (0, 100), ("Q", "X"): (100, 100)}
EXTERNAL = {("P", "Y"): (100, 100), ("Q", "X"): (0, 100)}


def test_tty_alias_never_defines_adapter_identity():
    with pytest.raises(ValueError, match="ID_PATH"):
        snapshot_pairing("RCA_PHY_01", connection(path="/dev/ttyUSB0"))


def test_adapter_identity_follows_id_path_not_tty_number():
    before = snapshot_pairing("RCA_PHY_01", connection())
    after = snapshot_pairing("RCA_PHY_01", connection(tty="/dev/ttyUSB7"))
    assert before.pairing_id == after.pairing_id
    assert after.adapter_id_path == "path-P"


def test_target_label_survives_adapter_crossover():
    before = snapshot_pairing("RCA_PHY_01", connection(), target_label="X")
    after = snapshot_pairing("RCA_PHY_01", connection("path-Q", "/dev/ttyUSB1"), target_label="X")
    assert before.target_label == after.target_label == "X"
    assert before.target_id == after.target_id == "UNKNOWN_TARGET"
    assert before.pairing_id != after.pairing_id


def test_pairing_history_preserves_before_and_after_states():
    before = snapshot_pairing("RCA_PHY_01", connection(), target_label="X")
    after = snapshot_pairing("RCA_PHY_01", connection(), target_label="Y")
    assert before.target_label == "X"
    assert after.target_label == "Y"
    assert before.pairing_id != after.pairing_id
    with pytest.raises(FrozenInstanceError):
        before.target_label = "Y"


def test_local_echo_failure_stops_higher_layer_classification():
    # Even a contradictory later response cannot bypass an earlier failed echo.
    record = {"mode": "sib", "events": exchange("00", "") + [
        {"kind": "tx", "hex": "55e6", "count": 2, "baud": 38400},
        {"kind": "response", "hex": "41", "requested": 1},
    ]}
    result = physical("analyze_sync", record)
    assert result["classification"] == "BREAK1_NO_ECHO"
    assert result["failure_stage"] == "LOCAL_ECHO"
    assert result["request_reached"] is False
    assert result["target_response_reached"] is False


def test_first_break_failure_differs_from_second_break_failure():
    first = physical("analyze_sync", {"events": exchange("00", "")})
    second = physical("analyze_sync", {"events": exchange("00", "00") + exchange("00", "ff")})
    assert first["classification"] == "BREAK1_NO_ECHO"
    assert second["classification"] == "BREAK1_EXACT_BREAK2_CORRUPT_ECHO"
    assert [x["class"] for x in second["breaks"]] == ["EXACT", "CORRUPT"]


def test_external_path_effect_is_not_called_target_effect():
    assert classify_crossover(ORIGINAL, EXTERNAL) == "ADAPTER_PATH"


def test_target_effect_is_not_called_adapter_effect():
    assert classify_crossover(ORIGINAL, TARGET) == "TARGET_LOCAL"


def test_two_factor_interaction_is_not_forced_to_single_cause():
    assert classify_pairing_matrix({**ORIGINAL, ("P", "Y"): (100, 100), ("Q", "X"): (100, 100)}) == "TWO_FACTOR_INTERACTION"


def test_reseat_only_change_is_classified_intervention_sensitive():
    assert classify_crossover(ORIGINAL, {("P", "Y"): (100, 100), ("Q", "X"): (100, 100)}) == "INTERVENTION_SENSITIVE"


def test_one_success_does_not_clear_intermittent_failure():
    one_recovery = {("P", "Y"): (1, 1), ("Q", "X"): (1, 1)}
    result = physical("assess_causal_movement", [(ORIGINAL, one_recovery, ORIGINAL)], single_variable=True)
    assert result["status"] != "PROVEN"
    assert result["domain"] == "INTERVENTION_SENSITIVE"


def test_root_cause_requires_repeated_causal_movement():
    one_cycle = [(ORIGINAL, TARGET, ORIGINAL)]
    assert physical("assess_causal_movement", one_cycle, single_variable=True)["status"] == "SUPPORTED"
    assert physical("assess_causal_movement", one_cycle * 3, single_variable=True) == {
        "domain": "TARGET_LOCAL", "status": "PROVEN", "repeat_count": 3,
    }
    assert physical("assess_causal_movement", one_cycle * 3, single_variable=False)["status"] == "UNRESOLVED"
    # Repeating a failed restoration is not causal movement.
    wrong_restore = {("P", "X"): (0, 100), ("Q", "Y"): (0, 100)}
    assert physical("assess_causal_movement", [(ORIGINAL, TARGET, wrong_restore)] * 3, single_variable=True)["status"] != "PROVEN"


@pytest.mark.parametrize("tx,echo,want,distance,index", [
    ("5585", "5585", "EXACT", 0, None),
    ("00", "", "EMPTY", 0, 0),
    ("5585", "55", "SHORT", 0, 1),
    ("55", "5500", "EXTRA", 0, 1),
    ("00", "80", "CORRUPT", 1, 0),
    ("5585", "8555", "SHIFTED", 6, 0),
])
def test_echo_byte_forensics_preserves_missing_bytes(tx, echo, want, distance, index):
    result = physical("echo_details", bytes.fromhex(tx), bytes.fromhex(echo))
    assert result["class"] == want
    assert result["hamming_distance_overlap"] == distance
    assert result["first_mismatch_index"] == index
    assert result["missing_byte_count"] == (1 if want in {"EMPTY", "SHORT"} else 0)


def test_exact_sync_and_response_require_both_breaks_and_command_echo():
    result = physical("analyze_sync", {"mode": "sib", "events": (
        exchange("00", "00") + exchange("00", "00") + exchange("55e6", "55e6", 38400) +
        [{"kind": "response", "hex": "41" * 32, "requested": 32}]
    )})
    assert result["classification"] == "TARGET_RESPONSE_REACHED"
    assert result["sync_complete"] is True
    assert result["request_reached"] is True
    assert result["target_response_reached"] is True


def test_no_capture_is_not_fabricated_as_empty_echo():
    result = physical("analyze_sync", {"events": [exchange("00", "00")[0]], "failure_stage": "HOST_TX"})
    assert result["classification"] == "ECHO_NOT_CAPTURED"
    assert result["breaks"][0]["class"] == "NOT_CAPTURED"
    assert result["target_response_reached"] is False


def test_interaction_effects_use_all_four_cells_without_forcing_locality():
    effects = physical("pairing_effects", {
        ("P", "X"): (100, 100), ("P", "Y"): (80, 100),
        ("Q", "X"): (70, 100), ("Q", "Y"): (0, 100),
    })
    assert effects["adapter_success_delta"] == pytest.approx(0.55)
    assert effects["target_success_delta"] == pytest.approx(0.45)
    assert effects["interaction_difference_of_differences"] == pytest.approx(-0.5)
    assert physical("pairing_effects", ORIGINAL) is None


def test_short_host_write_is_not_called_echo_loss():
    events = exchange("00", "")
    events[0]["count"] = 0
    result = physical("analyze_sync", {"events": events})
    assert result["failure_stage"] == "HOST_TX"
    assert result["classification"] == "HOST_TX_INCOMPLETE"
