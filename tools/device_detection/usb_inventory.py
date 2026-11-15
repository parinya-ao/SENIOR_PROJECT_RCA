"""Enumerate USB serial adapters without attaching roles to USB topology."""

import os
import re
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evidence import USBDevice


@dataclass(frozen=True)
class InventoryResult:
    devices: tuple[USBDevice, ...]
    errors: tuple[str, ...]
    tools: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "devices": [device.to_dict() for device in self.devices],
            "errors": list(self.errors),
            "tools": {
                name: {
                    "returncode": result.get("returncode"),
                    "available": result.get("returncode") is not None,
                }
                for name, result in self.tools.items()
            },
        }


def parse_udev_properties(text: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def _normalize_hex(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        return f"{int(value, 0) if isinstance(value, str) else int(value):04x}"
    except (TypeError, ValueError):
        return str(value).lower().removeprefix("0x")


def _run_command(
    runner: Callable[..., Any], argv: list[str], *, timeout: float = 3.0
) -> dict[str, Any]:
    try:
        result = runner(argv, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "returncode": result.returncode,
            "stdout": str(result.stdout or "")[:4000],
            "stderr": str(result.stderr or "")[:1000],
        }
    except (OSError, subprocess.SubprocessError, TypeError) as exc:
        return {"returncode": None, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}


def start_udev_monitor(popen: Callable[..., Any] = subprocess.Popen):
    """Start a tty udev event stream, or return None for polling fallback."""
    try:
        return popen(
            ["udevadm", "monitor", "--udev", "--subsystem-match=tty", "--property"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
    except OSError:
        return None


def _usb_instance(properties: dict[str, str], sysfs_usb_dir: Path, device_node: str) -> str | None:
    devpath = properties.get("DEVPATH", "")
    usb_name = next(
        (part for part in devpath.split("/") if re.fullmatch(r"\d+-\d+(?:\.\d+)*", part)), None
    )
    if not usb_name:
        return None
    try:
        parent = sysfs_usb_dir / usb_name
        bus = (parent / "busnum").read_text().strip()
        dev = (parent / "devnum").read_text().strip()
        stat = os.stat(device_node)
        return f"{bus}:{dev}:{stat.st_ino}:{stat.st_ctime_ns}"
    except OSError:
        return None


def discover_usb_devices(
    *,
    list_ports_fn: Callable[..., Iterable[Any]] | None = None,
    command_runner: Callable[..., Any] = subprocess.run,
    by_path_dir: str | Path = "/dev/serial/by-path",
    sysfs_usb_dir: str | Path = "/sys/bus/usb/devices",
) -> InventoryResult:
    """Return one record per live USB serial device; port names are locators only."""
    errors: list[str] = []
    tools: dict[str, dict[str, Any]] = {}
    directory = Path(by_path_dir)
    links_by_device: dict[str, list[str]] = {}
    try:
        for link in sorted(directory.iterdir()):
            try:
                target = os.path.realpath(link)
                links_by_device.setdefault(target, []).append(str(link))
            except OSError as exc:
                errors.append(f"by-path link {link}: {exc}")
    except FileNotFoundError:
        errors.append(f"by-path directory missing: {directory}")
    except OSError as exc:
        errors.append(f"cannot read by-path directory {directory}: {exc}")

    tools["by_path_listing"] = _run_command(command_runner, ["ls", "-l", str(directory)])
    tools["platformio"] = _run_command(command_runner, ["pio", "device", "list", "--json-output"])
    tools["usb_tree"] = _run_command(command_runner, ["lsusb", "-t"])

    if list_ports_fn is None:
        try:
            from serial.tools import list_ports

            list_ports_fn = list_ports.comports
        except ImportError as exc:
            errors.append(f"PySerial port enumeration unavailable: {exc}")
            list_ports_fn = lambda **_kwargs: ()
    try:
        try:
            port_infos = list(list_ports_fn(include_links=True))
        except TypeError:
            port_infos = list(list_ports_fn())
    except Exception as exc:
        port_infos = []
        errors.append(f"PySerial enumeration failed: {type(exc).__name__}: {exc}")

    candidates: dict[str, Any | None] = {}
    for port in port_infos:
        node = str(getattr(port, "device", "") or "")
        if node:
            candidates.setdefault(os.path.realpath(node), port)
    for real_path in links_by_device:
        candidates.setdefault(real_path, None)

    devices: list[USBDevice] = []
    for real_path, port in sorted(candidates.items()):
        query_path = str(getattr(port, "device", real_path) if port else real_path)
        udev = _run_command(
            command_runner,
            ["udevadm", "info", "--query=property", f"--name={query_path}"],
        )
        properties = parse_udev_properties(udev["stdout"])
        metadata_errors: list[str] = []
        if udev["returncode"] != 0:
            metadata_errors.append(udev["stderr"].strip() or "udevadm metadata unavailable")

        usb_by_path = tuple(sorted(set(links_by_device.get(real_path, ()))))
        udev_path = properties.get("ID_PATH")
        if not udev_path and usb_by_path:
            base = Path(usb_by_path[0]).name
            udev_path = base.removesuffix("-port0")
        vid = _normalize_hex(properties.get("ID_VENDOR_ID") or getattr(port, "vid", None))
        pid = _normalize_hex(properties.get("ID_MODEL_ID") or getattr(port, "pid", None))
        if not (vid or udev_path or usb_by_path):
            continue

        node = real_path if real_path.startswith("/dev/") else query_path
        devices.append(
            USBDevice(
                device_node=node,
                real_device_path=real_path,
                usb_path=udev_path,
                usb_by_path=usb_by_path,
                vid=vid,
                pid=pid,
                serial_number=(
                    properties.get("ID_SERIAL_SHORT") or getattr(port, "serial_number", None)
                ),
                manufacturer=(properties.get("ID_VENDOR") or getattr(port, "manufacturer", None)),
                product=(properties.get("ID_MODEL") or getattr(port, "product", None)),
                usb_location=(udev_path or getattr(port, "location", None)),
                driver=properties.get("ID_USB_DRIVER"),
                usb_instance=_usb_instance(properties, Path(sysfs_usb_dir), real_path),
                present=os.path.exists(real_path),
                metadata_errors=tuple(metadata_errors),
            )
        )

    devices.sort(key=lambda device: (device.usb_path or "", device.device_node))
    return InventoryResult(tuple(devices), tuple(errors), tools)
