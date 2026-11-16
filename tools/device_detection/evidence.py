"""Evidence models for the device detector."""

from dataclasses import dataclass
from typing import Any

ROLES = ("SENDER", "RECEIVER")


@dataclass(frozen=True)
class USBDevice:
    """USB serial adapter metadata without assigning an agent role."""

    device_node: str
    real_device_path: str
    usb_path: str | None = None
    usb_by_path: tuple[str, ...] = ()
    vid: str | None = None
    pid: str | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    product: str | None = None
    usb_location: str | None = None
    driver: str | None = None
    usb_instance: str | None = None
    present: bool = True
    metadata_errors: tuple[str, ...] = ()

    @property
    def port(self) -> str:
        """Return the current device-node path used to open the adapter."""
        return self.device_node

    @property
    def stable_key(self) -> str:
        """Return the best available key that survives port renumbering."""
        return self.usb_path or self.real_device_path

    def to_dict(self) -> dict[str, Any]:
        """Serialize adapter identifiers and probe metadata."""
        return {
            "device_node": self.device_node,
            "port": self.port,
            "real_device_path": self.real_device_path,
            "usb_path": self.usb_path,
            "usb_by_path": list(self.usb_by_path),
            "vid": self.vid,
            "pid": self.pid,
            "serial_number": self.serial_number,
            "manufacturer": self.manufacturer,
            "product": self.product,
            "usb_location": self.usb_location,
            "driver": self.driver,
            "usb_instance": self.usb_instance,
            "present": self.present,
            "metadata_errors": list(self.metadata_errors),
        }


@dataclass(frozen=True)
class FirmwareIdentity:
    """A role and build identifier decoded from firmware evidence."""

    role: str
    build_id: str
    protocol: int
    crc8: int | None
    integrity: str = "crc8"


@dataclass(frozen=True)
class ProbeEvidence:
    """Results from current firmware, flash, MCU, and access probes."""

    firmware_identity: FirmwareIdentity | None = None
    fingerprint_identity: FirmwareIdentity | None = None
    firmware_status: str = "NOT_ATTEMPTED"
    fingerprint_status: str = "NOT_ATTEMPTED"
    mcu_identity: str | None = None
    mcu_status: str = "NOT_ATTEMPTED"
    sib: str | None = None
    physical_id: str | None = None
    access_status: str = "READY"
    parse_status: str = "NONE"
    error: str | None = None
    legacy_hint: str | None = None


@dataclass(frozen=True)
class DetectedDevice:
    """A USB device paired with its current role and supporting evidence."""

    usb: USBDevice | None
    role: str = "UNKNOWN"
    identity_status: str = "UNKNOWN"
    evidence_type: str = "none"
    evidence: tuple[str, ...] = ()
    build_id: str | None = None
    mcu: str | None = None
    warnings: tuple[str, ...] = ()

    @property
    def port(self) -> str | None:
        """Return the current port path when a USB device is present."""
        return self.usb.port if self.usb else None

    @property
    def stable_key(self) -> str:
        """Return the USB identity key, or `missing` when no device exists."""
        return self.usb.stable_key if self.usb else "missing"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the detected role, identity, and evidence."""
        device = self.usb.to_dict() if self.usb else {}
        return {
            **device,
            "port": self.port,
            "role": self.role,
            "identity_status": self.identity_status,
            "evidence_type": self.evidence_type,
            "evidence": list(self.evidence),
            "build_id": self.build_id,
            "mcu": self.mcu,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ScanResult:
    """Complete role-detection result for the current USB inventory."""

    status: str
    devices: tuple[DetectedDevice, ...]
    missing_roles: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()

    def _unique_role(self, role: str) -> DetectedDevice | None:
        matches = [
            device
            for device in self.devices
            if device.role == role and device.identity_status == f"VERIFIED_{role}"
        ]
        return matches[0] if len(matches) == 1 else None

    @property
    def sender(self) -> DetectedDevice | None:
        """Return the unique verified sender, if one was found."""
        return self._unique_role("SENDER")

    @property
    def receiver(self) -> DetectedDevice | None:
        """Return the unique verified receiver, if one was found."""
        return self._unique_role("RECEIVER")

    def to_dict(self, inventory: dict[str, Any] | None = None) -> dict[str, Any]:
        """Serialize role results and optional raw inventory details."""
        result: dict[str, Any] = {
            "status": self.status,
            "devices": [device.to_dict() for device in self.devices],
            "missing_roles": list(self.missing_roles),
            "issues": list(self.issues),
        }
        if inventory is not None:
            result["inventory"] = inventory
        return result
