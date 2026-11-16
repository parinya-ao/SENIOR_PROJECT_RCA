"""Stable text and JSON representations for detection results."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .evidence import ScanResult


def result_to_json(result: ScanResult, inventory: dict[str, Any] | None = None) -> str:
    """Return a stable JSON representation of a scan result."""
    return json.dumps(result.to_dict(inventory), indent=2, sort_keys=True)


def exit_code_for(result: ScanResult) -> int:
    """Map scan status and probe failures to the detector CLI exit code."""
    if result.status == "PASS":
        return 0
    if result.status in {"AMBIGUOUS", "CONFLICT"}:
        return 3
    if result.status == "ERROR" or any(
        device.identity_status in {"INACCESSIBLE", "PROBE_FAILED"} for device in result.devices
    ):
        return 4
    return 2


def format_text(
    result: ScanResult, *, explain: bool = False
) -> str:
    """Format the inventory and verified roles for human-readable output."""
    lines = ["DEVICE ROLE DETECTION", "", f"Detected devices: {len(result.devices)}", ""]
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for index, detected in enumerate(result.devices):
        device = detected.usb
        lines.append(f"Device {labels[index] if index < len(labels) else index + 1}")
        lines.append(f"  Port: {detected.port or 'MISSING'}")
        lines.append(f"  USB path: {device.usb_path if device and device.usb_path else 'unknown'}")
        if device:
            adapter = " ".join(part for part in (device.manufacturer, device.product) if part)
            if adapter:
                lines.append(f"  Adapter: {adapter}")
            if device.serial_number:
                lines.append(f"  USB serial: {device.serial_number}")
            if device.vid or device.pid:
                lines.append(f"  VID:PID: {(device.vid or '????')}:{(device.pid or '????')}")
            if device.driver:
                lines.append(f"  Driver: {device.driver}")
        lines.append(f"  MCU: {detected.mcu or 'unknown'}")
        lines.append(f"  Firmware role: {detected.role}")
        lines.append(f"  Evidence: {detected.evidence_type}")
        status = (
            "VERIFIED"
            if detected.identity_status.startswith("VERIFIED_")
            else detected.identity_status
        )
        lines.append(f"  Status: {status}")
        if detected.build_id:
            lines.append(f"  Build: {detected.build_id}")
        if explain:
            lines.extend(f"  Reason: {item}" for item in detected.evidence)
            lines.extend(f"  Warning: {item}" for item in detected.warnings)
        lines.append("")

    lines.extend(
        (
            "RESULT",
            f"  Sender: {result.sender.port if result.sender else 'UNKNOWN'}",
            f"  Receiver: {result.receiver.port if result.receiver else 'UNKNOWN'}",
            f"  Detection: {result.status}",
        )
    )
    if result.missing_roles:
        lines.append(f"  Missing roles: {', '.join(result.missing_roles)}")
    lines.extend(f"  Issue: {issue}" for issue in result.issues)
    if explain and result.status == "UNKNOWN":
        lines.append(
            "  Reason: MCU or USB adapter identity alone does not establish firmware role."
        )
        lines.append("  UPDI probes are opt-in and require --hardware-safe after physical checks.")
    return "\n".join(lines)
