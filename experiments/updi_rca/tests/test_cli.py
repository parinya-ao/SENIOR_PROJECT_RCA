import json
from pathlib import Path
from types import SimpleNamespace

from updi_rca import cli
from updi_rca.identity import AdapterIdentity


def test_inventory_cli_reports_stable_identity_and_marks_target_unknown(monkeypatch, capsys):
    adapter = AdapterIdentity(
        vid="10c4",
        pid="ea60",
        usb_serial="0001",
        id_path="pci-0000:00:14.0-usb-0:1:1.0",
        sysfs_path="/sys/devices/usb/3-1/ttyUSB1",
        current_tty="/dev/ttyUSB1",
        by_id=None,
        by_path="pci-0000:00:14.0-usb-0:1:1.0-port0",
        usb_bus="003",
        usb_device="019",
        manufacturer="Silicon Labs",
        product="CP2102 USB to UART Bridge Controller",
    )
    monkeypatch.setattr(cli, "discover_serial_ports", lambda: [adapter])

    assert cli.main(["inventory"]) == 0
    row = json.loads(capsys.readouterr().out)[0]
    assert row["id_path"] == adapter.id_path
    assert row["current_tty"] == "/dev/ttyUSB1"
    assert row["target_identity"] == "UNKNOWN_TARGET"


def test_baseline_cli_runs_sib_and_control_on_selected_id_path(tmp_path, monkeypatch, capsys):
    adapters = [
        AdapterIdentity("10c4", "ea60", "0001", f"stable-{lane}", f"/sys/{lane}",
                        current_tty=f"/dev/ttyUSB{i}", by_path=f"path-{lane}")
        for i, lane in enumerate(("A", "B"))
    ]
    monkeypatch.setattr(cli, "discover_serial_ports", lambda: adapters)
    probes = []

    def fake_campaign(probe, attempts, raw_directory, run_id):
        assert attempts == 3
        assert run_id.endswith(("-sib", "-control"))
        result = probe(tmp_path / "sample.json")
        probes.append((result, raw_directory, run_id))
        return [
            {"attempt": 1, "result": "PASS", "failure_stage": "", "latency_ms": 1.0,
             "raw_sha256": "a" * 64, "source_log": str(tmp_path / "sample.json")}
        ]

    monkeypatch.setattr(cli, "run_campaign", fake_campaign, raising=False)
    selected_connections = []
    def passing_probe(conn, baud, path, **kwargs):
        selected_connections.append(conn)
        return SimpleNamespace(success=True, stage="PASS")
    monkeypatch.setattr(cli, "run_sib_probe", passing_probe)
    monkeypatch.setattr(cli, "run_control_read", passing_probe)

    assert cli.main(["baseline", adapters[1].id_path, str(tmp_path / "raw"), "--attempts", "3"]) == 0

    result = json.loads(capsys.readouterr().out)
    assert [conn.adapter.id_path for conn in selected_connections] == [adapters[1].id_path] * 2
    assert [item[2].rsplit("-", 1)[-1] for item in probes] == ["sib", "control"]
    assert result["target_identity"] == "UNKNOWN_TARGET"
    assert set(result["conditions"]) == {"sib", "control"}


def test_ocd_message_probe_cli_uses_selected_id_path(tmp_path, monkeypatch, capsys):
    adapter = AdapterIdentity(
        "10c4", "ea60", "0001", "stable-A", "/sys/A",
        current_tty="/dev/ttyUSB0", by_path="path-A",
    )
    monkeypatch.setattr(cli, "discover_serial_ports", lambda: [adapter])
    selected = []

    def fake_probe(connection, baud, output, **kwargs):
        selected.append((connection.adapter.id_path, baud, output, kwargs))
        return SimpleNamespace(success=True, stage="PASS", tx=b"tx", echo=b"echo",
                               response=b"bytes", latency_ms=4.0, error_type=None,
                               raw_path=str(output), raw_sha256="f" * 64)

    monkeypatch.setattr(cli, "run_ocd_message_probe", fake_probe, raising=False)

    assert cli.main(["probe", "ocd-message", "stable-A", str(tmp_path / "message.json")]) == 0

    output = json.loads(capsys.readouterr().out)
    assert selected[0][0:2] == ("stable-A", 38400)
    assert selected[0][3]["timeout"] == 1.0
    assert output["response_hex"] == b"bytes".hex()
