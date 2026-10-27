"""Resolve USB adapters by stable path and targets by safe probe identity."""

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from typing import Mapping


@dataclass(frozen=True)
class AdapterIdentity:
    vid: str
    pid: str
    usb_serial: str | None
    id_path: str
    sysfs_path: str
    current_tty: str | None = None
    by_id: str | None = None
    by_path: str | None = None
    usb_bus: str | None = None
    usb_device: str | None = None
    manufacturer: str | None = None
    product: str | None = None


@dataclass(frozen=True)
class BoardIdentity:
    sib: str | None = None
    device_signature: str | None = None
    revid: str | None = None
    target_serial: str | None = None

    @property
    def board_id(self) -> str:
        # A model signature is shared by all parts; only the documented serial identifies a board.
        return self.target_serial or "UNKNOWN_TARGET"


@dataclass(frozen=True)
class ConnectionIdentity:
    adapter: AdapterIdentity
    board: BoardIdentity

    @property
    def board_id(self) -> str:
        return self.board.board_id


@dataclass(frozen=True)
class PairingSnapshot:
    epoch_id: str
    adapter_id_path: str
    target_id: str
    current_tty: str | None
    target_label: str = "UNKNOWN_PHYSICAL_LABEL"

    @property
    def pairing_id(self) -> str:
        return f"{self.epoch_id}|{self.adapter_id_path}|{self.target_label}|{self.target_id}"


def snapshot_pairing(
    epoch_id: str, connection: ConnectionIdentity, *, target_label: str = "UNKNOWN_PHYSICAL_LABEL"
) -> PairingSnapshot:
    """Freeze what was known for a pairing; later reads cannot rewrite history."""
    if not epoch_id:
        raise ValueError("epoch_id is required")
    if not connection.adapter.id_path or connection.adapter.id_path.startswith(("/dev/", "ttyUSB", "ttyACM")):
        raise ValueError("a physical ID_PATH is required; tty is only a locator")
    if not target_label:
        raise ValueError("target_label must be explicit or UNKNOWN_PHYSICAL_LABEL")
    return PairingSnapshot(
        epoch_id=epoch_id,
        adapter_id_path=connection.adapter.id_path,
        target_id=connection.board_id,
        current_tty=connection.adapter.current_tty,
        target_label=target_label,
    )


def parse_udev_properties(text: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def adapter_from_properties(
    current_tty: str,
    sysfs_path: str,
    properties: Mapping[str, str],
    *,
    by_id: str | None = None,
    by_path: str | None = None,
    usb_bus: str | None = None,
    usb_device: str | None = None,
) -> AdapterIdentity:
    required = ("ID_VENDOR_ID", "ID_MODEL_ID", "ID_PATH")
    missing = [key for key in required if not properties.get(key)]
    if missing:
        raise ValueError(f"missing udev identity fields: {', '.join(missing)}")
    return AdapterIdentity(
        vid=properties["ID_VENDOR_ID"].lower(),
        pid=properties["ID_MODEL_ID"].lower(),
        usb_serial=properties.get("ID_SERIAL_SHORT"),
        id_path=properties["ID_PATH"],
        sysfs_path=sysfs_path,
        current_tty=current_tty,
        by_id=by_id,
        by_path=by_path,
        usb_bus=usb_bus,
        usb_device=usb_device,
        manufacturer=properties.get("ID_VENDOR"),
        product=properties.get("ID_MODEL"),
    )


def _links_for(device: Path, directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return sorted(link.name for link in directory.iterdir() if os.path.realpath(link) == str(device))


def _usb_numbers(sysfs_path: Path) -> tuple[str | None, str | None]:
    for parent in sysfs_path.parents:
        busnum, devnum = parent / "busnum", parent / "devnum"
        if busnum.is_file() and devnum.is_file():
            return busnum.read_text().strip(), devnum.read_text().strip()
    return None, None


def discover_serial_ports(
    sys_class_tty: str | Path = "/sys/class/tty",
    dev_root: str | Path = "/dev",
) -> list[AdapterIdentity]:
    """Discover USB serial devices; tty is a locator and ID_PATH is the identity key."""
    sys_class_tty, dev_root = Path(sys_class_tty), Path(dev_root)
    adapters = []
    entries = sorted((*sys_class_tty.glob("ttyUSB*"), *sys_class_tty.glob("ttyACM*")))
    for entry in entries:
        device = dev_root / entry.name
        sysfs_path = Path(os.path.realpath(entry))
        completed = subprocess.run(
            ["udevadm", "info", "--query=property", "--path", str(sysfs_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        properties = parse_udev_properties(completed.stdout)
        bus, usb_device = _usb_numbers(sysfs_path)
        id_links = _links_for(device, dev_root / "serial/by-id")
        path_links = _links_for(device, dev_root / "serial/by-path")
        adapters.append(
            adapter_from_properties(
                str(device),
                str(sysfs_path),
                properties,
                by_id=id_links[0] if len(id_links) == 1 else None,
                by_path=path_links[0] if path_links else None,
                usb_bus=bus,
                usb_device=usb_device,
            )
        )
    paths = [adapter.id_path for adapter in adapters]
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate ID_PATH values; refusing ambiguous adapter mapping")
    return sorted(adapters, key=lambda adapter: adapter.id_path)


def resolve_connection(
    id_path: str,
    adapters: list[AdapterIdentity],
    targets_by_id_path: Mapping[str, BoardIdentity | None],
) -> ConnectionIdentity:
    matches = [adapter for adapter in adapters if adapter.id_path == id_path]
    if not matches:
        raise ValueError(f"no adapter for ID_PATH {id_path!r}")
    if len(matches) != 1:
        raise ValueError(f"duplicate ID_PATH {id_path!r}; refusing ambiguous mapping")
    return ConnectionIdentity(matches[0], targets_by_id_path.get(id_path) or BoardIdentity())


def resolve_connections(
    adapters: list[AdapterIdentity],
    targets_by_id_path: Mapping[str, BoardIdentity | None],
) -> list[ConnectionIdentity]:
    paths = [adapter.id_path for adapter in adapters]
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate ID_PATH values; refusing ambiguous mapping")
    return [
        ConnectionIdentity(adapter, targets_by_id_path.get(adapter.id_path) or BoardIdentity())
        for adapter in sorted(adapters, key=lambda item: item.id_path)
    ]
