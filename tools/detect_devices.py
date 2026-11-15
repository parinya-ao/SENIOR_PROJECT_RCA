"""Detect USB-attached AVR device roles without assigning roles by USB path."""

from __future__ import annotations

import argparse
import json
import select
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.device_detection.evidence import ProbeEvidence, ScanResult
from tools.device_detection.firmware_identity import FirmwareReference
from tools.device_detection.output import exit_code_for, format_text, result_to_json
from tools.device_detection.role_detector import classify_devices, diff_device_presence
from tools.device_detection.updi_probe import (
    firmware_fingerprint_evidence,
    probe_firmware_identity,
    probe_target_sib,
    read_firmware_flash,
)
from tools.device_detection.usb_inventory import (
    InventoryResult,
    discover_usb_devices,
    start_udev_monitor,
)


class SafetyArgumentParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args, namespace)
        if (
            parsed.probe_updi or parsed.probe_firmware or parsed.probe_flash
        ) and not parsed.hardware_safe:
            self.error("UPDI probes require --hardware-safe after physical wiring checks")
        if parsed.probe_flash and not parsed.authorize_flash_read:
            self.error("--probe-flash also requires --authorize-flash-read")
        if parsed.probe_flash and not parsed.boot_layout_verified:
            self.error("--probe-flash requires --boot-layout-verified")
        if parsed.authorize_flash_read and not parsed.probe_flash:
            self.error("--authorize-flash-read requires --probe-flash")
        if parsed.watch and parsed.scan:
            self.error("choose either --scan or --watch")
        if parsed.self_test and (parsed.scan or parsed.watch):
            self.error("--self-test cannot be combined with --scan or --watch")
        return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = SafetyArgumentParser(
        description="Discover USB/UPDI devices and verify Sender/Receiver roles."
    )
    commands = parser.add_mutually_exclusive_group()
    commands.add_argument("--scan", action="store_true", help="scan connected USB serial adapters")
    commands.add_argument("--watch", action="store_true", help="watch USB hotplug and rescan")
    commands.add_argument(
        "--self-test", action="store_true", help="run the local detector test suite"
    )
    parser.add_argument("--json", action="store_true", help="write JSON to stdout")
    parser.add_argument("--explain", action="store_true", help="include classification reasons")
    parser.add_argument("--registry", type=Path, help="optional local history/reference JSON file")
    parser.add_argument("--probe-updi", action="store_true", help="read the AVR SIB via upditerm")
    parser.add_argument(
        "--probe-firmware", action="store_true", help="read current UPDI virtual-UART identity"
    )
    parser.add_argument(
        "--probe-flash", action="store_true", help="read-only flash fingerprint comparison"
    )
    parser.add_argument(
        "--hardware-safe",
        action="store_true",
        help="assert board power, ground, and UPDI wiring were physically checked",
    )
    parser.add_argument(
        "--authorize-flash-read",
        action="store_true",
        help="explicitly allow intrusive read-only full-flash inspection",
    )
    parser.add_argument(
        "--boot-layout-verified",
        action="store_true",
        help="assert BOOT/application geometry is verified for the target",
    )
    parser.add_argument("--baudrate", type=int, default=38400)
    parser.add_argument("--probe-timeout", type=float, default=2.0)
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="bounded watch fallback interval in seconds",
    )
    return parser


def _load_registry(path: Path | None) -> tuple[dict[str, Any], list[FirmwareReference], list[str]]:
    if path is None:
        return {}, [], []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, [], [f"registry not found: {path}"]
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [], [f"cannot read registry {path}: {exc}"]
    if not isinstance(raw, dict):
        return {}, [], ["registry root must be a JSON object"]

    registry: dict[str, Any] = {}
    issues: list[str] = []
    device_entries = raw.get("devices", [])
    reference_entries = raw.get("firmware_references", [])
    if not isinstance(device_entries, list):
        issues.append("registry devices must be a JSON array")
        device_entries = []
    if not isinstance(reference_entries, list):
        issues.append("registry firmware_references must be a JSON array")
        reference_entries = []
    for entry in device_entries:
        if not isinstance(entry, dict) or not entry.get("usb_path"):
            issues.append("ignored registry entry without usb_path")
            continue
        role = entry.get("role")
        if role not in {"SENDER", "RECEIVER"}:
            issues.append(f"ignored registry entry with invalid role for {entry['usb_path']}")
            continue
        registry[str(entry["usb_path"])] = {
            "role": role,
            "physical_id": entry.get("physical_id"),
        }

    references: list[FirmwareReference] = []
    for entry in reference_entries:
        try:
            image_path = Path(entry["ihex_path"])
            if not image_path.is_absolute():
                image_path = path.parent / image_path
            references.append(
                FirmwareReference(
                    role=entry["role"],
                    build_id=entry["build_id"],
                    ihex=image_path.read_text(encoding="ascii"),
                    flash_size=int(entry["flash_size"]),
                    app_start=int(entry["app_start"]),
                    app_end=int(entry["app_end"]),
                )
            )
        except (KeyError, OSError, ValueError, TypeError) as exc:
            issues.append(f"ignored invalid firmware reference: {exc}")
    return registry, references, issues


def _probe_device(
    device,
    args: argparse.Namespace,
    references: list[FirmwareReference],
    *,
    command_runner=subprocess.run,
) -> ProbeEvidence:
    port = device.usb_by_path[0] if device.usb_by_path else device.device_node
    base = ProbeEvidence()
    if args.probe_firmware:
        base = probe_firmware_identity(
            port,
            hardware_safe=args.hardware_safe,
            baudrate=args.baudrate,
            timeout=args.probe_timeout,
            command_runner=command_runner,
        )
    if args.probe_updi or args.probe_flash:
        sib = probe_target_sib(
            port,
            hardware_safe=args.hardware_safe,
            baudrate=args.baudrate,
            timeout=args.probe_timeout,
            command_runner=command_runner,
        )
        base = replace(
            base,
            mcu_identity=sib.mcu_identity,
            mcu_status=sib.mcu_status,
            sib=sib.sib,
            access_status=sib.access_status,
            error=base.error or sib.error,
        )
    if args.probe_flash and base.access_status == "READY" and base.mcu_identity == "AVR128DA28":
        geometries = {(r.flash_size, r.app_start, r.app_end) for r in references}
        if len(geometries) != 1:
            return replace(
                base,
                fingerprint_status="NOT_ATTEMPTED",
                error="flash fingerprint needs references with one verified layout",
            )
        flash_size, app_start, app_end = next(iter(geometries))
        dump = read_firmware_flash(
            port,
            hardware_safe=args.hardware_safe,
            authorize_flash_read=args.authorize_flash_read,
            boot_layout_verified=args.boot_layout_verified,
            mcu_identity=base.mcu_identity,
            flash_size=flash_size,
            command_runner=command_runner,
        )
        fingerprint = firmware_fingerprint_evidence(
            dump, references, flash_size=flash_size, app_start=app_start, app_end=app_end
        )
        base = replace(
            base,
            fingerprint_identity=fingerprint.fingerprint_identity,
            fingerprint_status=fingerprint.fingerprint_status,
            parse_status=fingerprint.parse_status,
            error=base.error or fingerprint.error,
        )
    return base


def _scan(
    args: argparse.Namespace,
    *,
    inventory_fn=discover_usb_devices,
    registry: dict[str, Any] | None = None,
    references: list[FirmwareReference] | None = None,
    probe_cache: dict[str, tuple[str, str | None, ProbeEvidence]] | None = None,
) -> tuple[ScanResult, InventoryResult]:
    inventory = inventory_fn()
    probes: dict[str, ProbeEvidence] = {}
    probe_cache = probe_cache if probe_cache is not None else {}
    requested = args.probe_updi or args.probe_firmware or args.probe_flash
    if requested:
        active_keys = {device.stable_key for device in inventory.devices}
        for key in tuple(probe_cache):
            if key not in active_keys:
                del probe_cache[key]
        for device in inventory.devices:
            cached = probe_cache.get(device.stable_key)
            if cached and cached[0] == device.device_node and cached[1] == device.usb_instance:
                evidence = cached[2]
            else:
                evidence = _probe_device(device, args, references or [])
                probe_cache[device.stable_key] = (device.device_node, device.usb_instance, evidence)
            probes[device.device_node] = evidence
    result = classify_devices(inventory.devices, probes, registry=registry)
    return result, inventory


def _print_result(
    result: ScanResult, inventory: InventoryResult, as_json: bool, explain: bool = False
) -> None:
    if as_json:
        print(result_to_json(result, inventory.to_dict()))
    else:
        print(format_text(result, explain=explain))


def _watch(args, registry, references) -> int:
    monitor = start_udev_monitor()
    cache: dict[str, tuple[str, str | None, ProbeEvidence]] = {}
    previous_result, inventory = _scan(
        args, registry=registry, references=references, probe_cache=cache
    )
    if args.json:
        print(
            json.dumps(
                {"event": "snapshot", "result": previous_result.to_dict(inventory.to_dict())}
            )
        )
    else:
        print(format_text(previous_result, explain=args.explain))
    sys.stdout.flush()

    next_fallback = time.monotonic() + max(args.poll_interval, 1.0)
    try:
        while True:
            triggered = False
            if monitor is not None and monitor.stdout is not None and monitor.poll() is None:
                ready, _, _ = select.select([monitor.stdout], [], [], args.poll_interval)
                if ready:
                    line = monitor.stdout.readline()
                    triggered = line.startswith("UDEV ") or line.startswith("ACTION=")
                if time.monotonic() >= next_fallback:
                    triggered = True
                    next_fallback = time.monotonic() + max(args.poll_interval, 1.0)
            else:
                time.sleep(max(args.poll_interval, 0.1))
                triggered = True

            if not triggered:
                continue
            if monitor is not None:
                cache.clear()
            current_result, inventory = _scan(
                args, registry=registry, references=references, probe_cache=cache
            )
            events = diff_device_presence(previous_result.devices, current_result.devices)
            for event in events:
                event_type = event.pop("event")
                if args.json:
                    print(json.dumps({"event": event_type, **event}, sort_keys=True))
                else:
                    print(
                        f"USB {event_type.upper()}: {event.get('port') or 'unknown'} "
                        f"role={event.get('role', 'UNKNOWN')} "
                        f"status={event.get('identity_status', 'UNKNOWN')}"
                    )
            previous_result = current_result
            sys.stdout.flush()
    except KeyboardInterrupt:
        return 0
    finally:
        if monitor is not None:
            monitor.terminate()
            try:
                monitor.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                monitor.kill()
                monitor.wait()


def _run_self_test() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
        cwd=ROOT,
    )
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        return _run_self_test()
    registry, references, registry_issues = _load_registry(args.registry)
    if args.watch:
        return _watch(args, registry, references)

    result, inventory = _scan(args, registry=registry, references=references)
    if registry_issues:
        result = replace(result, issues=result.issues + tuple(registry_issues))
    _print_result(result, inventory, args.json, args.explain)
    return exit_code_for(result)


if __name__ == "__main__":
    raise SystemExit(main())
