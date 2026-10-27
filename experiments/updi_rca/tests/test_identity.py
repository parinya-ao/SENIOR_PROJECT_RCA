import pytest
from pathlib import Path
from types import SimpleNamespace
import subprocess
from updi_rca import identity

from updi_rca.identity import (
    AdapterIdentity,
    BoardIdentity,
    adapter_from_properties,
    discover_serial_ports,
    parse_udev_properties,
    resolve_connection,
    resolve_connections,
)


def adapter(tty, path):
    return AdapterIdentity(
        vid="10c4",
        pid="ea60",
        usb_serial="0001",
        id_path=path,
        sysfs_path=f"/sys/devices/{path}/{tty}",
        current_tty=f"/dev/{tty}",
    )


def board(serial):
    return BoardIdentity(
        sib="AVR P:2 D:1",
        device_signature="1e970a",
        revid="a7",
        target_serial=serial,
    )


def test_duplicate_adapter_serials_keep_distinct_target_identities():
    paths = ["usb-path-a", "usb-path-b"]
    connections = resolve_connections(
        [adapter("ttyUSB0", paths[0]), adapter("ttyUSB1", paths[1])],
        {paths[0]: board("serial-a"), paths[1]: board("serial-b")},
    )

    assert [c.board_id for c in connections] == ["serial-a", "serial-b"]
    assert {c.adapter.usb_serial for c in connections} == {"0001"}


def test_tty_rename_does_not_swap_target_identity():
    paths = ["usb-path-a", "usb-path-b"]
    connections = resolve_connections(
        [adapter("ttyUSB1", paths[0]), adapter("ttyUSB0", paths[1])],
        {paths[0]: board("serial-a"), paths[1]: board("serial-b")},
    )

    assert {c.adapter.current_tty: c.board_id for c in connections} == {
        "/dev/ttyUSB1": "serial-a",
        "/dev/ttyUSB0": "serial-b",
    }


def test_unreadable_target_stays_unknown_instead_of_inheriting_tty_label():
    connection = resolve_connection(
        "usb-path-a", [adapter("ttyUSB0", "usb-path-a")], {}
    )

    assert connection.board_id == "UNKNOWN_TARGET"
    assert connection.board.target_serial is None


def test_pairing_history_preserves_previous_unknown_state():
    path = "usb-path-a"
    adapters = [adapter("ttyUSB0", path)]
    snapshot = getattr(identity, "snapshot_pairing", None)
    assert snapshot is not None, "missing immutable pairing snapshot API"
    before = snapshot("RCA_CROSSOVER_01", resolve_connection(path, adapters, {}))
    after = snapshot(
        "RCA_CROSSOVER_01", resolve_connection(path, adapters, {path: board("target-x")})
    )

    assert before.target_id == "UNKNOWN_TARGET"
    assert after.target_id == "target-x"
    assert before.pairing_id != after.pairing_id


def test_reconnect_updates_tty_but_preserves_target_serial():
    path = "usb-path-a"
    connection = resolve_connection(
        path, [adapter("ttyUSB7", path)], {path: board("serial-a")}
    )

    assert connection.adapter.current_tty == "/dev/ttyUSB7"
    assert connection.board_id == "serial-a"


def test_duplicate_id_path_is_rejected_as_ambiguous():
    path = "usb-path-a"
    with pytest.raises(ValueError, match="duplicate ID_PATH"):
        resolve_connections(
            [adapter("ttyUSB0", path), adapter("ttyUSB1", path)],
            {path: board("serial-a")},
        )


def test_udev_parser_preserves_values_after_the_first_equals():
    assert parse_udev_properties("ID_PATH=pci-usb-1\nID_SERIAL_SHORT=0001=x\nignored") == {
        "ID_PATH": "pci-usb-1",
        "ID_SERIAL_SHORT": "0001=x",
    }


def test_adapter_metadata_requires_usb_path_and_keeps_duplicate_serial():
    item = adapter_from_properties(
        "/dev/ttyUSB9",
        "/sys/devices/usb/ttyUSB9",
        {
            "ID_VENDOR_ID": "10C4",
            "ID_MODEL_ID": "EA60",
            "ID_PATH": "usb-path-a",
            "ID_SERIAL_SHORT": "0001",
        },
        by_path="port-a",
    )
    assert item.id_path == "usb-path-a"
    assert item.usb_serial == "0001"
    assert item.current_tty == "/dev/ttyUSB9"
    with pytest.raises(ValueError, match="ID_PATH"):
        adapter_from_properties("/dev/ttyUSB9", "/sys/ttyUSB9", {})


def test_discovery_uses_sysfs_id_path_and_by_path_link(tmp_path, monkeypatch):
    sys_class = tmp_path / "sys/class/tty"
    dev_root = tmp_path / "dev"
    usb_device = tmp_path / "sys/devices/usb3/3-1"
    tty_target = usb_device / "3-1:1.0/ttyUSB9/tty/ttyUSB9"
    tty_target.mkdir(parents=True)
    (usb_device / "busnum").write_text("3")
    (usb_device / "devnum").write_text("9")
    sys_class.mkdir(parents=True)
    (sys_class / "ttyUSB9").symlink_to(tty_target, target_is_directory=True)
    (dev_root / "ttyUSB9").parent.mkdir(parents=True)
    (dev_root / "ttyUSB9").touch()
    path_dir = dev_root / "serial/by-path"
    path_dir.mkdir(parents=True)
    (path_dir / "usb-port-a").symlink_to(dev_root / "ttyUSB9")
    (path_dir / "usbv2-port-a").symlink_to(dev_root / "ttyUSB9")

    def fake_run(command, **kwargs):
        assert command[-1] == str(tty_target)
        return SimpleNamespace(
            stdout="ID_VENDOR_ID=10c4\nID_MODEL_ID=ea60\nID_PATH=usb-path-a\nID_SERIAL_SHORT=0001\n"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    devices = discover_serial_ports(sys_class, dev_root)

    assert len(devices) == 1
    assert devices[0].id_path == "usb-path-a"
    assert devices[0].by_path == "usb-port-a"
    assert devices[0].usb_bus == "3"
    assert devices[0].usb_device == "9"
