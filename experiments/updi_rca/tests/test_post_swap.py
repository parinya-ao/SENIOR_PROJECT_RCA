"""Post-swap comparisons must retain history and withhold unjustified locality."""

from copy import deepcopy
import importlib

from updi_rca.board_swap import sib_outcome
from updi_rca.classify import classify_event, classify_crossover, classify_pairing_matrix
from updi_rca.identity import AdapterIdentity, BoardIdentity, ConnectionIdentity, snapshot_pairing
from updi_rca.physical import echo_details
import pytest


A = {("P", "X"): (100, 100), ("Q", "Y"): (0, 100)}
TARGET = {("P", "Y"): (0, 30), ("Q", "X"): (30, 30)}
PATH = {("P", "Y"): (30, 30), ("Q", "X"): (0, 30)}


def assess(b, **kwargs):
    module = importlib.import_module("updi_rca.board_swap")
    assert hasattr(module, "post_swap_assessment"), "missing confound-aware post-swap gate"
    return module.post_swap_assessment(A, b, **kwargs)


def test_post_swap_phase_preserves_original_history():
    old = deepcopy(A)
    assess(TARGET)
    assert A == old


def test_current_tty_is_not_physical_identity():
    with pytest.raises(ValueError, match="ID_PATH"):
        snapshot_pairing("RCA_POST_SWAP_01", ConnectionIdentity(
            AdapterIdentity("10c4", "ea60", "0001", "/dev/ttyUSB0", "/sys/usb", "/dev/ttyUSB0"), BoardIdentity()))


def test_failure_movement_to_target_classifies_target_following():
    assert assess(TARGET)["candidate"] == "TARGET_FOLLOWING"


def test_failure_staying_on_path_classifies_path_following():
    assert assess(PATH)["candidate"] == "PATH_FOLLOWING"


def test_both_pass_classifies_intervention_sensitive():
    assert assess({("P", "Y"): (30, 30), ("Q", "X"): (30, 30)})["candidate"] == "INTERVENTION_SENSITIVE"


def test_both_fail_does_not_claim_two_failed_boards():
    assert assess({("P", "Y"): (0, 30), ("Q", "X"): (0, 30)})["candidate"] == "SHARED_FAILURE"


def test_partial_matrix_classifies_interaction():
    assert classify_pairing_matrix({**A, ("P", "Y"): (100, 100), ("Q", "X"): (100, 100)}) == "TWO_FACTOR_INTERACTION"
    assert classify_crossover(A, {("P", "Y"): (29, 30), ("Q", "X"): (12, 30)}) == "MIXED_OR_INTERMITTENT"


def test_break_failure_is_separate_from_sib_response_failure():
    def frame(tx, echo, baud):
        return [{"kind": "tx", "hex": tx, "count": len(bytes.fromhex(tx)), "baud": baud},
                {"kind": "echo", "hex": echo, "requested": len(bytes.fromhex(tx))}]
    assert sib_outcome({"mode": "sib", "events": frame("00", "", 300)}) == "BREAK1_NO_ECHO"
    assert sib_outcome({"mode": "sib", "events": frame("00", "00", 300) * 2 + frame("55e6", "55e6", 38400) +
                        [{"kind": "response", "hex": "", "requested": 32}]}) == "SIB_TX_ECHO_OK_RESPONSE_MISSING"
    assert echo_details(b"\x55\xe6", b"\x55")["class"] == "SHORT"


def test_acc_history_is_not_merged_into_local_echo_failure():
    assert classify_event({"stage": "ACC_DATA_RESPONSE", "tx_hex": "550000", "echo_hex": "550000"}) == "ACC_DATA_RESPONSE"
    assert classify_event({"tx_hex": "00", "echo_hex": ""}) == "LOCAL_ECHO"


def test_restore_phase_required_before_proven_locality():
    result = assess(TARGET)
    assert result["status"] == "UNRESOLVED"
    assert result["restore_measured"] is False


def test_target_sigrow_identity_survives_tty_swap():
    target = BoardIdentity(target_serial="0102030405060708090a0b0c0d0e0f10")
    one = snapshot_pairing("OLD", ConnectionIdentity(AdapterIdentity("10c4", "ea60", "0001", "path-P", "/sys/a", "/dev/ttyUSB0"), target), target_label="X")
    two = snapshot_pairing("RCA_POST_SWAP_01", ConnectionIdentity(AdapterIdentity("10c4", "ea60", "0001", "path-Q", "/sys/b", "/dev/ttyUSB9"), target), target_label="X")
    assert one.target_id == two.target_id == "0102030405060708090a0b0c0d0e0f10"
    assert two.adapter_id_path == "path-Q"


def test_power_cycle_is_recorded_as_confound():
    result = assess(TARGET, restored=A, power_cycle="UNKNOWN", baseline_stationary=False)
    assert result["power_cycle"] == "UNKNOWN"
    assert result["baseline_stationary"] is False
    assert result["status"] == "UNRESOLVED"


def test_raw_log_hashes_are_preserved(tmp_path):
    from updi_rca.reporting import write_csv
    import csv
    import hashlib
    raw = tmp_path / "raw.log"
    raw.write_bytes(b"TX 00; ECHO EMPTY\n")
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    output = tmp_path / "runs.csv"
    write_csv(output, ["raw_log_path", "raw_log_sha256"], [{"raw_log_path": str(raw), "raw_log_sha256": digest}])
    row = next(csv.DictReader(output.open()))
    assert row["raw_log_sha256"] == hashlib.sha256(raw.read_bytes()).hexdigest()
