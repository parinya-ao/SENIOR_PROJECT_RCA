"""Classify devices only from current, role-bearing evidence."""

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .evidence import DetectedDevice, FirmwareIdentity, ProbeEvidence, ScanResult, USBDevice


def _probe_for(device: USBDevice, probes: Mapping[str, ProbeEvidence]) -> ProbeEvidence:
    for key in (device.device_node, device.real_device_path, device.usb_path, *device.usb_by_path):
        if key and key in probes:
            return probes[key]
    return ProbeEvidence()


def _identity_role(identity: FirmwareIdentity | None) -> str | None:
    if identity is None or identity.role not in ("SENDER", "RECEIVER"):
        return None
    return identity.role


def _registry_record(registry: Mapping[str, Any], device: USBDevice) -> Mapping[str, Any]:
    value = registry.get(device.usb_path or "", {})
    return value if isinstance(value, Mapping) else {"role": value}


def _registry_hint(registry: Mapping[str, Any], device: USBDevice) -> str | None:
    hint = _registry_record(registry, device).get("role")
    return hint if hint in ("SENDER", "RECEIVER") else None


def classify_devices(
    devices: Sequence[USBDevice],
    probes: Mapping[str, ProbeEvidence] | None = None,
    *,
    registry: Mapping[str, Any] | None = None,
) -> ScanResult:
    """Return VERIFIED only for current firmware or unique exact flash evidence."""
    probes = probes or {}
    registry = registry or {}
    detected: list[DetectedDevice] = []
    for usb in devices:
        probe = _probe_for(usb, probes)
        warnings: list[str] = []
        details: list[str] = []
        fw = probe.firmware_identity
        flash = probe.fingerprint_identity
        fw_role = _identity_role(fw)
        flash_role = _identity_role(flash)
        enrollment = _registry_record(registry, usb)
        enrolled_role = (
            enrollment.get("role") if enrollment.get("role") in ("SENDER", "RECEIVER") else None
        )
        enrollment_id = enrollment.get("physical_id")
        enrollment_match = bool(
            enrolled_role
            and enrollment_id
            and probe.physical_id
            and enrollment_id == probe.physical_id
        )

        if not usb.present:
            detected.append(
                DetectedDevice(usb, "UNKNOWN", "MISSING", "none", ("USB device is not present",))
            )
            continue
        if probe.access_status == "INACCESSIBLE":
            detected.append(
                DetectedDevice(
                    usb,
                    "UNKNOWN",
                    "INACCESSIBLE",
                    "probe",
                    (probe.error or "serial interface is busy",),
                    mcu=probe.mcu_identity,
                )
            )
            continue
        if probe.access_status == "PROBE_FAILED":
            detected.append(
                DetectedDevice(
                    usb,
                    "UNKNOWN",
                    "PROBE_FAILED",
                    "probe",
                    (probe.error or "identity probe failed",),
                    mcu=probe.mcu_identity,
                )
            )
            continue
        if probe.parse_status == "AMBIGUOUS":
            detected.append(
                DetectedDevice(
                    usb,
                    "UNKNOWN",
                    "AMBIGUOUS",
                    "firmware_identity",
                    (probe.error or "conflicting firmware markers",),
                    mcu=probe.mcu_identity,
                )
            )
            continue

        if fw_role and flash_role and fw_role != flash_role:
            detected.append(
                DetectedDevice(
                    usb,
                    "UNKNOWN",
                    "AMBIGUOUS",
                    "firmware_identity+flash_fingerprint",
                    (f"firmware marker says {fw_role}, flash fingerprint says {flash_role}",),
                    mcu=probe.mcu_identity,
                )
            )
            continue
        role = fw_role or flash_role or (enrolled_role if enrollment_match else None)
        if role:
            if probe.mcu_identity and probe.mcu_identity != "AVR128DA28":
                detected.append(
                    DetectedDevice(
                        usb,
                        "UNKNOWN",
                        "AMBIGUOUS",
                        "firmware_identity",
                        (f"firmware role is on unexpected MCU {probe.mcu_identity}",),
                        mcu=probe.mcu_identity,
                    )
                )
                continue
            historical = _registry_hint(registry, usb)
            if historical and historical != role:
                warnings.append(
                    f"Historical USB-path role {historical} disagrees with live {role}; "
                    "current firmware identity takes precedence"
                )
            if enrollment_match and not (fw_role or flash_role):
                evidence_type = "verified_enrollment"
                details.append("current physical identity matches the verified local enrollment")
                build_id = None
            elif fw_role and flash_role:
                evidence_type = "firmware_identity+flash_fingerprint"
                details.extend(("valid current firmware identity", "exact application flash match"))
                build_id = (
                    fw.build_id
                    if fw is not None
                    else flash.build_id if flash is not None else None
                )
            elif fw_role:
                evidence_type = "firmware_identity"
                integrity = fw.integrity if fw else "verified"
                details.append(f"current UPDI firmware identity ({integrity})")
                build_id = fw.build_id if fw else None
            else:
                evidence_type = "flash_fingerprint"
                details.append("exact application-region flash fingerprint match")
                build_id = flash.build_id if flash else None
            detected.append(
                DetectedDevice(
                    usb,
                    role,
                    f"VERIFIED_{role}",
                    evidence_type,
                    tuple(details),
                    build_id=build_id,
                    mcu=probe.mcu_identity,
                    warnings=tuple(warnings),
                )
            )
            continue

        if probe.error:
            warnings.append(probe.error)
        if probe.mcu_identity:
            details.append("MCU identity does not establish firmware role")
            evidence_type = "updi_mcu_identity"
        elif probe.sib:
            details.append("UPDI SIB identifies the target but not its firmware role")
            evidence_type = "updi_sib"
        elif enrolled_role:
            details.append("historical registry role is not current identity evidence")
            evidence_type = "historical_hint"
            warnings.append(f"Historical role hint: {enrolled_role}; current role remains UNKNOWN")
        elif probe.legacy_hint:
            details.append("historical identity is a hint only")
            evidence_type = "historical_hint"
            warnings.append(
                f"Historical role hint: {probe.legacy_hint}; current role remains UNKNOWN"
            )
        elif probe.parse_status == "MALFORMED":
            details.append("firmware identity frame was malformed or failed its checksum")
            evidence_type = "firmware_identity"
        else:
            details.append("USB adapter metadata identifies no firmware role")
            evidence_type = "usb_inventory"

        if probe.firmware_status == "INACCESSIBLE" or probe.fingerprint_status == "INACCESSIBLE":
            identity_status = "INACCESSIBLE"
        elif probe.firmware_status == "PROBE_FAILED" or probe.fingerprint_status == "PROBE_FAILED":
            identity_status = "PROBE_FAILED"
        elif probe.parse_status == "AMBIGUOUS":
            identity_status = "AMBIGUOUS"
        else:
            identity_status = "UNKNOWN"
        detected.append(
            DetectedDevice(
                usb,
                "UNKNOWN",
                identity_status,
                evidence_type,
                tuple(details),
                mcu=probe.mcu_identity,
                warnings=tuple(warnings),
            )
        )

    claims = Counter(
        device.role
        for device in detected
        if device.identity_status in ("VERIFIED_SENDER", "VERIFIED_RECEIVER")
    )
    issues: list[str] = []
    conflicts = {role for role, count in claims.items() if count > 1}
    if conflicts:
        issues.append(
            "multiple devices claim the same verified role: " + ", ".join(sorted(conflicts))
        )
        detected = [
            DetectedDevice(
                device.usb,
                device.role,
                "CONFLICT" if device.role in conflicts else device.identity_status,
                device.evidence_type,
                device.evidence,
                device.build_id,
                device.mcu,
                device.warnings + (("duplicate role claim",) if device.role in conflicts else ()),
            )
            for device in detected
        ]
        status = "CONFLICT"
    elif any(device.identity_status == "AMBIGUOUS" for device in detected):
        status = "AMBIGUOUS"
    elif any(device.identity_status in ("INACCESSIBLE", "PROBE_FAILED") for device in detected):
        status = "ERROR"
    elif not detected:
        status = "MISSING"
    elif claims["SENDER"] and claims["RECEIVER"]:
        status = "PASS"
    elif claims["SENDER"] or claims["RECEIVER"]:
        status = "PARTIAL"
    else:
        status = "UNKNOWN"

    missing_roles: tuple[str, ...] = ()
    if status == "MISSING":
        missing_roles = ("SENDER", "RECEIVER")
    elif status == "PARTIAL":
        missing_roles = tuple(role for role in ("SENDER", "RECEIVER") if not claims[role])
    return ScanResult(status, tuple(detected), missing_roles, tuple(issues))


def diff_device_presence(
    previous: Sequence[DetectedDevice], current: Sequence[DetectedDevice]
) -> list[dict[str, Any]]:
    """Diff current snapshots; removed devices lose active role assignments."""
    old = {device.stable_key: device for device in previous}
    new = {device.stable_key: device for device in current}
    events: list[dict[str, Any]] = []
    for key in sorted(old.keys() - new.keys()):
        prior = old[key]
        events.append(
            {
                "event": "disconnected",
                "port": prior.port,
                "usb_path": prior.usb.usb_path if prior.usb else None,
                "role": "UNKNOWN",
                "identity_status": "MISSING",
                "last_verified_role": prior.role
                if prior.identity_status.startswith("VERIFIED_")
                else None,
            }
        )
    for key in sorted(new.keys() - old.keys()):
        current_device = new[key]
        events.append({"event": "connected", **current_device.to_dict()})
    for key in sorted(old.keys() & new.keys()):
        before, after = old[key], new[key]
        if before.port != after.port or before.to_dict() != after.to_dict():
            events.append({"event": "updated", **after.to_dict()})
    return events
