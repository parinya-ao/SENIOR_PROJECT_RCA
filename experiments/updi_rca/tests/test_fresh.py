"""Fresh epoch contract, including the thirteen inherited causal checks."""
from copy import deepcopy
from dataclasses import replace
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

from updi_rca.board_swap import post_swap_assessment
from updi_rca.classify import classify_pairing_matrix
from updi_rca.identity import AdapterIdentity, BoardIdentity, ConnectionIdentity, snapshot_pairing
from updi_rca.physical import assess_causal_movement


def fresh():
    assert importlib.util.find_spec("updi_rca.fresh"), "fresh runner is missing"
    return importlib.import_module("updi_rca.fresh")


def adapters():
    return [AdapterIdentity("10c4", "ea60", "0001", f"pci-usb-{n}", f"/sys/{n}",
                            f"/dev/ttyUSB{2-n}", by_path=f"pci-usb-{n}") for n in (2, 1)]


def mapping():
    return fresh().freeze_mapping(adapters(), {"/dev/ttyUSB0": "PowerBoard branch0",
                                               "/dev/ttyUSB1": "PowerBoard branch1"})


def exchange(tx="00", echo="00", baud=300):
    return [{"kind": "tx", "hex": tx, "count": len(bytes.fromhex(tx)), "baud": baud},
            {"kind": "echo", "hex": echo, "requested": len(bytes.fromhex(tx))}]


def raw(echo="00", response=""):
    return {"mode": "sib", "exit": 1, "events": exchange(echo=echo) if echo != "00" else
            exchange() * 2 + exchange("55e6", "55e6", 38400) +
            [{"kind": "response", "hex": response, "requested": 32}],
            "failure_stage": "LOCAL_ECHO" if echo != "00" else "UPDI_CONTROL_RESPONSE"}


A = {("P", "X"): (30, 30), ("Q", "Y"): (0, 30)}
TARGET = {("P", "Y"): (0, 30), ("Q", "X"): (30, 30)}


def test_01_new_mapping_preserves_old_history():
    old = deepcopy(A)
    m = mapping()
    assert A == old and m["P"]["adapter"]["id_path"] == "pci-usb-1"


def test_02_tty_is_locator_not_identity():
    m = mapping()
    changed = [replace(a, current_tty="/dev/ttyUSB9") for a in adapters()]
    assert fresh().resolve_lane(m["P"], changed).id_path == "pci-usb-1"


def test_03_target_following():
    assert post_swap_assessment(A, TARGET)["candidate"] == "TARGET_FOLLOWING"


def test_04_path_following():
    assert post_swap_assessment(A, {("P", "Y"): (30, 30), ("Q", "X"): (0, 30)})["candidate"] == "PATH_FOLLOWING"


def test_05_intervention_sensitive():
    assert post_swap_assessment(A, {("P", "Y"): (30, 30), ("Q", "X"): (30, 30)})["candidate"] == "INTERVENTION_SENSITIVE"


def test_06_shared_failure_not_two_bad_boards():
    assert post_swap_assessment(A, {("P", "Y"): (0, 30), ("Q", "X"): (0, 30)})["candidate"] == "SHARED_FAILURE"


def test_07_interaction():
    assert classify_pairing_matrix({**A, ("P", "Y"): (30, 30), ("Q", "X"): (30, 30)}) == "TWO_FACTOR_INTERACTION"


def test_08_break_and_response_are_separate():
    assert fresh().failure_stage(raw(echo="")) == "BREAK1_EMPTY_ECHO"
    assert fresh().failure_stage(raw()) == "SIB_RESPONSE_EMPTY"


def test_09_acc_failure_is_preserved():
    assert fresh().failure_stage({"mode": "read", "events": [], "failure_stage": "ACC_DATA_RESPONSE"}) == "ACC_DATA_RESPONSE"


def test_10_restoration_and_three_cycles_required():
    assert post_swap_assessment(A, TARGET)["status"] == "UNRESOLVED"
    assert assess_causal_movement([(A, TARGET, A)], single_variable=True)["status"] == "SUPPORTED"
    assert assess_causal_movement([(A, TARGET, A)] * 3, single_variable=True)["status"] == "PROVEN"


def test_11_full_serial_survives_tty_change():
    target = BoardIdentity(target_serial="0102030405060708090a0b0c0d0e0f10")
    assert snapshot_pairing("RCA_FRESH_01", ConnectionIdentity(adapters()[0], target)).target_id == target.target_serial
    assert mapping()["P"]["target_id"] == "UNKNOWN"


def test_12_power_cycle_is_confound():
    assert post_swap_assessment(A, TARGET, restored=A, power_cycle="UNKNOWN")["status"] == "UNRESOLVED"


def test_13_raw_hash_and_immutability(tmp_path):
    f = fresh()
    path = tmp_path / "raw.json"
    f.write_once(path, {"epoch_id": f.EPOCH})
    digest = f.sha256(path)
    with pytest.raises(FileExistsError):
        f.write_once(path, {})
    assert f.sha256(path) == digest


def test_separate_power_boards_and_unresolved_units():
    m = mapping()
    assert m["P"]["power_board"] != m["Q"]["power_board"]
    assert all(x["adapter_unit_id"] == "UNRESOLVED" for x in m.values())


@pytest.mark.parametrize("items", [[], adapters()[:1], adapters() * 2,
                                            [replace(a, by_path=None) for a in adapters()]])
def test_ambiguous_discovery_rejected(items):
    with pytest.raises(ValueError):
        fresh().freeze_mapping(items, {})


@pytest.mark.parametrize("echo,expected", [("", "BREAK1_EMPTY_ECHO"), ("80", "BREAK1_CORRUPT_ECHO")])
def test_break_classes(echo, expected):
    assert fresh().failure_stage(raw(echo=echo)) == expected


def test_second_break_ordinal_and_short_command():
    f = fresh()
    assert f.failure_stage({"events": exchange() + exchange(echo=""), "mode": "sib"}) == "BREAK2_EMPTY_ECHO"
    assert f.failure_stage({"events": exchange()*2 + exchange("55e6", "55", 38400), "mode": "sib"}) == "SIB_SHORT_ECHO"
    assert f.failure_stage(raw(response="01")) == "SIB_RESPONSE_SHORT"


def test_control_gate_ignores_smoke_and_historical():
    f = fresh()
    passed = [{"epoch_id": f.EPOCH, "batch": "smoke", "mode": "sib", "success": True}] * 30
    assert not f.control_allowed(passed)
    passed = [{**r, "batch": "baseline-1"} for r in passed]
    assert f.control_allowed(passed)
    assert not f.control_allowed(passed[:-1])
    assert not f.control_allowed(passed + [{**passed[0], "batch": "baseline-2", "success": False}])
    assert not f.control_allowed([{**r, "epoch_id": "OLD"} for r in passed])


def test_batch_gate_requires_three_untouched_when_mixed():
    f = fresh()
    one = [{"success": True, "failure_stage": "PASS"}, {"success": False, "failure_stage": "BREAK1_EMPTY_ECHO"}]
    assert f.needs_untouched_repeats([one])
    assert not f.needs_untouched_repeats([one, one, one])
    assert f.needs_untouched_repeats([[one[1]], [{"success": False, "failure_stage": "SIB_RESPONSE_EMPTY"}]])


def test_scores_count_evidence_once_and_start_zero():
    f = fresh()
    assert all(r["score"] == 0 and r["status"] == "UNRESOLVED" for r in f.domain_scores([]))
    evidence = {"epoch_id": f.EPOCH, "evidence_id": "one", "domain": "D1", "delta": 1}
    with pytest.raises(ValueError, match="duplicate"):
        f.domain_scores([evidence, evidence])
    assert f.domain_scores([evidence])[0]["score"] == 1


def install_attempt(monkeypatch, tmp_path, *, busy=False, discovery_error=False, exception=False):
    f = fresh()
    monkeypatch.setattr(f, "LOCK_ROOT", tmp_path / "locks")
    def discover():
        if discovery_error:
            raise OSError("udev unavailable")
        return adapters()
    monkeypatch.setattr(f, "discover_serial_ports", discover)
    monkeypatch.setattr(f, "port_busy", lambda p: busy)
    def execute(command, **kwargs):
        if exception:
            raise subprocess.TimeoutExpired(command, 45)
        path = Path(command[command.index("--timeout") - 1])
        path.write_text(json.dumps(raw()))
        return subprocess.CompletedProcess(command, 1, json.dumps({"stage": "UPDI_CONTROL_RESPONSE", "success": False}), "")
    monkeypatch.setattr(f.subprocess, "run", execute)
    return f


def test_attempt_envelope_and_hashes(tmp_path, monkeypatch):
    f = install_attempt(monkeypatch, tmp_path)
    p = f.run_attempt(tmp_path, mapping(), "P", "baseline-1", "sib")
    env = json.loads(p.read_text())
    assert env["epoch_id"] == f.EPOCH and env["run_id"].startswith(f.EPOCH)
    assert env["failure_stage"] == "SIB_RESPONSE_EMPTY" and env["transport_stage"] == "UPDI_CONTROL_RESPONSE"
    assert env["wall_start"] and env["monotonic_end_ns"] >= env["monotonic_start_ns"]
    assert env["command"] and env["exit_status"] == 1
    assert f.validate_evidence([p], mapping())[0]["run_id"] == env["run_id"]


@pytest.mark.parametrize("kind,expected", [("busy", "PORT_BUSY"), ("discovery", "DISCOVERY_ERROR"), ("exception", "EXECUTION_ERROR")])
def test_attempt_failure_and_lock_cleanup(tmp_path, monkeypatch, kind, expected):
    f = install_attempt(monkeypatch, tmp_path, busy=kind == "busy", discovery_error=kind == "discovery", exception=kind == "exception")
    p = f.run_attempt(tmp_path, mapping(), "P", "baseline-1", "sib")
    assert json.loads(p.read_text())["failure_stage"] == expected
    with f.lane_lock("pci-usb-1"):
        pass


def test_same_path_lock_is_busy(tmp_path, monkeypatch):
    f = install_attempt(monkeypatch, tmp_path)
    with f.lane_lock("pci-usb-1"):
        p = f.run_attempt(tmp_path, mapping(), "P", "baseline-1", "sib")
    assert json.loads(p.read_text())["failure_stage"] == "PORT_BUSY"


@pytest.mark.parametrize("corruption", ["epoch", "hash", "absent_hash", "unmapped", "event_id", "run_id", "identity", "raw_overwrite"])
def test_evidence_rejects_corruption(tmp_path, monkeypatch, corruption):
    f = install_attempt(monkeypatch, tmp_path)
    m = mapping()
    p = f.run_attempt(tmp_path, m, "P", "baseline-1", "sib")
    env = json.loads(p.read_text())
    if corruption == "epoch":
        env["epoch_id"] = "OLD"
    elif corruption == "hash":
        env["artifacts"][0]["sha256"] = "0" * 64
    elif corruption == "absent_hash":
        del env["artifacts"][0]["sha256"]
    elif corruption == "unmapped":
        env["events"][0]["run_id"] = "alien"
    elif corruption == "event_id":
        env["events"][1]["event_id"] = env["events"][0]["event_id"]
    elif corruption == "run_id":
        with pytest.raises(ValueError, match="duplicate"):
            f.validate_evidence([p, p], m)
        return
    elif corruption == "identity":
        env["mapping"]["adapter"]["id_path"] = "alien"
    else:
        Path(env["artifacts"][0]["path"]).write_text("overwritten")
    p.write_text(json.dumps(env))
    p.with_suffix(".sha256").write_text(f.sha256(p))
    with pytest.raises(ValueError):
        f.validate_evidence([p], m)


def test_initialize_preserves_history_and_empty_reports(tmp_path, monkeypatch):
    f = fresh()
    assert hasattr(f, "initialize"), "fresh initialization is missing"
    project = tmp_path / "project"
    old = project / "experiments/updi_rca/reports/runs.csv"
    old.parent.mkdir(parents=True)
    old.write_text("run_id\nold-run\n")
    root = project / "artifacts/updi/fresh"
    monkeypatch.setattr(f, "discover_serial_ports", adapters)
    f.initialize(root, project)
    assert old.read_text() == "run_id\nold-run\n"
    assert f.verify_history(root) == 1
    assert json.loads((root / "mapping.json").read_text())["P"]["target_id"] == "UNKNOWN"
    with pytest.raises(FileExistsError):
        f.initialize(root, project)
    old.write_text("changed")
    with pytest.raises(ValueError, match="historical"):
        f.verify_history(root)


def test_reports_keep_smoke_separate_and_unmeasured_blank(tmp_path, monkeypatch):
    import csv
    f = install_attempt(monkeypatch, tmp_path)
    assert hasattr(f, "refresh_reports"), "fresh reports are missing"
    f.write_once(tmp_path / "mapping.json", mapping())
    f.run_attempt(tmp_path, mapping(), "P", "smoke", "sib")
    f.run_attempt(tmp_path, mapping(), "P", "baseline-1", "sib")
    f.refresh_reports(tmp_path)
    reports = tmp_path / "reports"
    required = ("device_inventory", "runs", "events", "hypothesis_status", "pairwise_comparison",
                "fuse_compare", "flash_budget", "root_cause_ranking", "batch_metrics", "echo_errors",
                "causal_proof", "experiment_matrix")
    for name in required:
        with (reports / f"{name}.csv").open() as stream:
            assert "epoch_id" in next(csv.reader(stream))
    metrics = list(csv.DictReader((reports / "batch_metrics.csv").open()))
    assert len(metrics) == 2 and {r["batch"] for r in metrics} == {"smoke", "baseline-1"}
    assert all(r["attempts"] == "1" for r in metrics)
    unmeasured = list(csv.DictReader((reports / "experiment_matrix.csv").open()))
    assert any(r["lane"] == "Q" and r["attempts"] == "" for r in unmeasured)
    assert len(list(csv.DictReader((reports / "hypothesis_status.csv").open()))) == 8


def test_missing_transport_artifact_rejected_even_with_empty_events(tmp_path, monkeypatch):
    f = install_attempt(monkeypatch, tmp_path)
    p = f.run_attempt(tmp_path, mapping(), "P", "smoke", "sib")
    env = json.loads(p.read_text())
    env["events"] = []
    env["artifacts"] = [a for a in env["artifacts"] if not a["path"].endswith("transport.json")]
    p.write_text(json.dumps(env))
    p.with_suffix(".sha256").write_text(f.sha256(p))
    with pytest.raises(ValueError, match="transport"):
        f.validate_evidence([p], mapping())


@pytest.mark.parametrize("field,value", [("success", True), ("exit_status", 0), ("command", ["unsafe"]), ("latency_ms", -1)])
def test_envelope_cannot_misrepresent_transport(tmp_path, monkeypatch, field, value):
    f = install_attempt(monkeypatch, tmp_path)
    p = f.run_attempt(tmp_path, mapping(), "P", "baseline-1", "sib")
    env = json.loads(p.read_text())
    env[field] = value
    p.write_text(json.dumps(env))
    p.with_suffix(".sha256").write_text(f.sha256(p))
    with pytest.raises(ValueError):
        f.validate_evidence([p], mapping())


def test_no_control_batch_reservation_before_gate(tmp_path, monkeypatch):
    f = install_attempt(monkeypatch, tmp_path)
    f.write_once(tmp_path / "mapping.json", mapping())
    with pytest.raises(ValueError, match="SIB30"):
        f.run_batch(tmp_path, "P", "control-1", "control", 30)
    assert not list((tmp_path / "evidence").glob("*/*"))
