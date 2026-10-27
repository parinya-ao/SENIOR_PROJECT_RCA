"""Board-swap interpretation must survive enumeration and require restoration."""

import importlib
import importlib.util

from updi_rca.classify import classify_crossover, classify_pairing_matrix
from updi_rca.identity import AdapterIdentity, BoardIdentity, ConnectionIdentity, snapshot_pairing
from updi_rca.physical import assess_causal_movement
import pytest


ORIGINAL = {("P", "X"): (20, 20), ("Q", "Y"): (0, 20)}
TARGET = {("P", "Y"): (0, 30), ("Q", "X"): (30, 30)}
EXTERNAL = {("P", "Y"): (30, 30), ("Q", "X"): (0, 30)}


def pairing(path, tty, label):
    return snapshot_pairing("RCA_BOARD_SWAP_01", ConnectionIdentity(
        AdapterIdentity("10c4", "ea60", "0001", path, "/sys/usb", tty), BoardIdentity()
    ), target_label=label)


def swap(name, *args, **kwargs):
    assert importlib.util.find_spec("updi_rca.board_swap") is not None, "missing board-swap interpretation"
    return getattr(importlib.import_module("updi_rca.board_swap"), name)(*args, **kwargs)


def frame(tx, echo, baud=300):
    return [
        {"kind": "tx", "hex": tx, "count": len(bytes.fromhex(tx)), "baud": baud},
        {"kind": "echo", "hex": echo, "requested": len(bytes.fromhex(tx)), "baud": baud},
    ]


def test_tty_alias_does_not_define_external_path():
    with pytest.raises(ValueError, match="ID_PATH"):
        pairing("/dev/ttyUSB0", "/dev/ttyUSB0", "X")


def test_id_path_survives_tty_renumber():
    assert pairing("path-P", "/dev/ttyUSB0", "X").pairing_id == pairing("path-P", "/dev/ttyUSB8", "X").pairing_id


def test_target_physical_label_survives_adapter_crossover():
    a = pairing("path-P", "/dev/ttyUSB0", "X")
    b = pairing("path-Q", "/dev/ttyUSB0", "X")
    assert a.target_label == b.target_label == "X"
    assert a.target_id == b.target_id == "UNKNOWN_TARGET"
    assert a.pairing_id != b.pairing_id


def test_failure_following_target_is_classified_target_local():
    assert classify_crossover(ORIGINAL, TARGET) == "TARGET_LOCAL"


def test_failure_following_external_path_is_classified_external_path():
    assert classify_crossover(ORIGINAL, EXTERNAL) == "ADAPTER_PATH"


def test_both_pass_after_reseat_is_intervention_sensitive():
    assert classify_crossover(ORIGINAL, {("P", "Y"): (30, 30), ("Q", "X"): (30, 30)}) == "INTERVENTION_SENSITIVE"


def test_both_fail_after_swap_is_not_called_two_bad_boards():
    assert classify_crossover(ORIGINAL, {("P", "Y"): (0, 30), ("Q", "X"): (0, 30)}) == "CROSSED_BOTH_FAIL_AMBIGUOUS"


def test_partial_rate_difference_is_not_forced_into_binary_pass_fail():
    assert classify_pairing_matrix({
        ("P", "X"): (99, 100), ("Q", "Y"): (42, 100),
        ("P", "Y"): (75, 100), ("Q", "X"): (31, 100),
    }) == "MIXED_OR_INTERMITTENT"


def test_adapter_target_interaction_is_preserved():
    assert classify_pairing_matrix({
        ("P", "X"): (100, 100), ("Q", "Y"): (0, 100),
        ("P", "Y"): (100, 100), ("Q", "X"): (100, 100),
    }) == "TWO_FACTOR_INTERACTION"


def test_local_echo_failure_does_not_become_acc_failure():
    record = {"mode": "sib", "events": frame("00", ""), "failure_stage": "LOCAL_ECHO"}
    assert swap("sib_outcome", record) == "BREAK1_NO_ECHO"


def test_break1_failure_and_break2_failure_are_distinct():
    assert swap("sib_outcome", {"events": frame("00", "")}) == "BREAK1_NO_ECHO"
    assert swap("sib_outcome", {"events": frame("00", "00") + frame("00", "")}) == "BREAK1_EXACT_BREAK2_NO_ECHO"


def test_one_success_does_not_clear_intermittent_failure():
    recovery = {("P", "Y"): (1, 1), ("Q", "X"): (1, 1)}
    assert assess_causal_movement([(ORIGINAL, recovery, ORIGINAL)], single_variable=True)["status"] != "PROVEN"


def test_restore_phase_is_required_before_proven_status():
    result = swap("restoration_assessment", ORIGINAL, TARGET, restored=None)
    assert result == {"domain": "TARGET_LOCAL", "status": "BLOCKED", "repeat_count": 0}
    after = swap("restoration_assessment", ORIGINAL, TARGET, restored=ORIGINAL)
    assert after["domain"] == "TARGET_LOCAL"
    assert after["repeat_count"] == 1
    assert after["status"] == "SUPPORTED"


@pytest.mark.parametrize("tail,want", [
    ([], "SYNC_COMPLETE_SIB_NOT_SENT"),
    (frame("55e6", "80", 38400), "SIB_TX_ECHO_FAIL"),
    (frame("55e6", "55e6", 38400) + [{"kind": "response", "hex": "", "requested": 32}], "SIB_TX_ECHO_OK_RESPONSE_MISSING"),
    (frame("55e6", "55e6", 38400) + [{"kind": "response", "hex": "41" * 32, "requested": 32}], "SIB_PASS"),
])
def test_sib_outcome_keeps_command_echo_and_target_response_separate(tail, want):
    assert swap("sib_outcome", {"mode": "sib", "events": frame("00", "00") + frame("00", "00") + tail}) == want
