#!/usr/bin/env python3
"""Read-only Lane P identity/ownership/topology/power inventory; never opens tty."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
COMMANDS = ROOT / "commands"
COMMANDS.mkdir(exist_ok=True)
EXPECTED_ID_PATH = "pci-0000:00:14.0-usb-0:4:1.0"
records: list[dict] = []


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def run(label: str, argv: list[str], timeout: float = 20) -> dict:
    start_utc = utc_now()
    start_mono = time.monotonic_ns()
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, errors="surrogateescape", timeout=timeout, check=False)
        stdout, stderr, returncode, timed_out = p.stdout, p.stderr, p.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="surrogateescape") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="surrogateescape") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        returncode, timed_out = None, True
    except OSError as exc:
        stdout, stderr, returncode, timed_out = "", f"{type(exc).__name__}: {exc}\n", 127, False
    end_mono = time.monotonic_ns()
    end_utc = utc_now()
    stdout_bytes, stderr_bytes = stdout.encode(errors="surrogateescape"), stderr.encode(errors="surrogateescape")
    rec = {
        "label": label,
        "argv": argv,
        "cwd": os.getcwd(),
        "start_utc": start_utc,
        "end_utc": end_utc,
        "monotonic_start_ns": start_mono,
        "monotonic_end_ns": end_mono,
        "duration_ms": (end_mono - start_mono) / 1_000_000,
        "exit_code": returncode,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
        "argv_sha256": hashlib.sha256(b"\0".join(x.encode() for x in argv)).hexdigest(),
        "stdout_sha256": hashlib.sha256(stdout_bytes).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr_bytes).hexdigest(),
    }
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
    (COMMANDS / f"{len(records)+1:03d}_{safe}.json").write_text(json.dumps(rec, indent=2) + "\n")
    records.append(rec)
    return rec


def props_from_output(stdout: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            result[k] = v
    return result


start = {
    "epoch": "RCA_BOARD_SWAP_01",
    "lane": "P",
    "expected_id_path": EXPECTED_ID_PATH,
    "capture_start_utc": utc_now(),
    "host": os.uname().nodename,
    "platform": os.uname().sysname + " " + os.uname().release,
    "python": sys.version,
    "serial_open_attempted": False,
    "hardware_moved": False,
}
(ROOT / "capture_start.json").write_text(json.dumps(start, indent=2) + "\n")

# Resolve all current USB serial interfaces via sysfs/udev before any owner checks.
by_path_list = run("serial_by_path_listing", ["ls", "-la", "/dev/serial/by-path"])
tty_candidates = sorted(pathlib.Path("/sys/class/tty").glob("ttyUSB*"))
tty_data = []
for sys_tty in tty_candidates:
    dev = pathlib.Path("/dev") / sys_tty.name
    prop = run(f"udev_properties_{sys_tty.name}", ["udevadm", "info", "--query=property", f"--name={dev}"])
    query_path = run(f"udev_sysfs_path_{sys_tty.name}", ["udevadm", "info", "--query=path", f"--name={dev}"])
    tty_data.append({
        "tty": sys_tty.name,
        "device_exists": dev.exists(),
        "udev_properties": props_from_output(prop["stdout"]),
        "udev_properties_command": prop["label"],
        "udev_sysfs_path": query_path["stdout"].strip(),
        "sysfs_realpath": os.path.realpath(sys_tty / "device"),
    })

lane_matches = [d for d in tty_data if d["udev_properties"].get("ID_PATH") == EXPECTED_ID_PATH]
by_path_matches: list[str] = []
if len(lane_matches) == 1:
    id_path_rec = lane_matches[0]
    # Prefer the non-usbv2 by-path name derived from the exact udev ID_PATH.
    # udev also publishes a usbv2 alias, so target tty alone is not unique.
    stable_link = pathlib.Path("/dev/serial/by-path") / f"{EXPECTED_ID_PATH}-port0"
    if stable_link.is_symlink() and os.path.basename(os.path.realpath(stable_link)) == id_path_rec["tty"]:
        by_path_matches.append(str(stable_link))

owner_results: dict[str, dict] = {}
if len(lane_matches) == 1 and len(by_path_matches) == 1:
    lane_link = by_path_matches[0]
    link_udev = run("lane_by_path_udev_properties", ["udevadm", "info", "--query=property", f"--name={lane_link}"])
    owner_results["fuser"] = run("fuser_lane_by_path", ["fuser", "-v", lane_link], timeout=10)
    owner_results["lsof"] = run("lsof_lane_by_path", ["lsof", "-nP", lane_link], timeout=10)
else:
    lane_link = None
    link_udev = None

# Current USB topology and a bounded recent kernel log; no usbfs control query.
topology = run("lsusb_tree", ["lsusb", "-t"])
kernel_log = run("kernel_log_last_15_minutes", ["journalctl", "-k", "--since", "15 minutes ago", "--no-pager", "-o", "short-iso"], timeout=25)

# Narrow process check only; avoid persisting unrelated process command lines.
upditerm_ps = run("upditerm_processes", ["pgrep", "-a", "-f", "[u]pditerm"])
avrdude_ps = run("avrdude_processes", ["pgrep", "-a", "-f", "[a]vrdude"])
holder_rows = [line for rec in (upditerm_ps, avrdude_ps) for line in rec["stdout"].splitlines()]

# Host power sources: list names then read only common status attributes.
power_listing = run("power_supply_listing", ["find", "/sys/class/power_supply", "-maxdepth", "2", "-type", "f"])
power_reads = []
for path in power_listing["stdout"].splitlines():
    if pathlib.Path(path).name in {"type", "online", "status", "capacity", "voltage_now", "current_now", "power_now"}:
        power_reads.append(run("power_" + path.rsplit("/", 1)[-2] + "_" + pathlib.Path(path).name,
                               ["cat", path], timeout=5))

# Read sysfs USB ancestor attributes for the resolved P device.
usb_sysfs: dict[str, dict[str, str]] = {}
if len(lane_matches) == 1:
    current = pathlib.Path(lane_matches[0]["sysfs_realpath"])
    for parent in [current, *current.parents]:
        if (parent / "idVendor").exists() and (parent / "idProduct").exists():
            attrs = ["idVendor", "idProduct", "manufacturer", "product", "serial", "busnum", "devnum", "speed", "devpath", "bConfigurationValue", "bNumInterfaces"]
            values = {}
            for attr in attrs:
                f = parent / attr
                if f.exists():
                    try:
                        values[attr] = f.read_text(errors="replace").strip()
                    except OSError as exc:
                        values[attr] = f"ERROR {type(exc).__name__}: {exc}"
            usb_sysfs[str(parent)] = values
            break

summary = {
    **start,
    "capture_end_utc": utc_now(),
    "tty_candidates": tty_data,
    "lane_p_match_count": len(lane_matches),
    "lane_p_match": lane_matches[0] if len(lane_matches) == 1 else None,
    "lane_p_by_path_match_count": len(by_path_matches),
    "lane_p_by_path": lane_link,
    "by_path_udev_properties": props_from_output(link_udev["stdout"]) if link_udev else None,
    "usb_sysfs_attributes": usb_sysfs,
    "owner_checks": {
        name: {"exit_code": rec["exit_code"], "stdout": rec["stdout"], "stderr": rec["stderr"]}
        for name, rec in owner_results.items()
    },
    "upditerm_process_check": {"exit_code": upditerm_ps["exit_code"], "stdout": upditerm_ps["stdout"], "stderr": upditerm_ps["stderr"]},
    "avrdude_process_check": {"exit_code": avrdude_ps["exit_code"], "stdout": avrdude_ps["stdout"], "stderr": avrdude_ps["stderr"]},
    "upditerm_avrdude_process_matches": holder_rows,
    "topology_command": {"exit_code": topology["exit_code"], "stdout": topology["stdout"], "stderr": topology["stderr"]},
    "kernel_log_command": {"exit_code": kernel_log["exit_code"], "stdout": kernel_log["stdout"], "stderr": kernel_log["stderr"]},
    "power_supply_paths": power_listing["stdout"].splitlines(),
    "power_read_commands": [r["label"] for r in power_reads],
    "command_records": [p.name for p in sorted(COMMANDS.glob("*.json"))],
}
(ROOT / "inventory_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({
    "lane_p_match_count": len(lane_matches),
    "lane_p_by_path_match_count": len(by_path_matches),
    "tty": lane_matches[0]["tty"] if len(lane_matches) == 1 else None,
    "by_path": lane_link,
    "usb_sysfs": usb_sysfs,
    "owner_checks": summary["owner_checks"],
    "upditerm_avrdude_matches": holder_rows,
    "topology_exit": topology["exit_code"],
    "kernel_log_exit": kernel_log["exit_code"],
    "power_reads": len(power_reads),
}, indent=2))
