"""Adapter for the repository's verified UPDI monitors and RF bench runner."""

from __future__ import annotations

import json
import time
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tools import installed_rf
from tools.debug_protocol_ack_nack import Hardware, Session
from tools.lora_chat.errors import make_error
from tools.lora_chat.protocol import (
    MAX_APPLICATION_PAYLOAD_BYTES,
    MAX_HOST_MESSAGE_BYTES,
    RETRY_EVENTS,
    TIMEOUT_EVENTS,
    DeviceRole,
    EventName,
    MessageProtocol,
    encode_interactive_message,
    fragment_message,
    negotiated_payload_limit,
    parse_firmware_event,
)
from tools.lora_chat.session import ExchangeResult, ExchangeStatus

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TextIO


ROOT = Path(__file__).resolve().parents[2]
PROJECT_CONFIG = ROOT / "config" / "lora_system.json"
DEVICE_ROLE_COUNT = 2
DATA_CHECKPOINT_INDEX = 2
BENCH_FREQUENCY_HZ = 915_000_000


class ProfileValue(StrEnum):
    """Supported mode and wire encoding names in the active project profile."""

    SINGLE_PACKET = "single_packet"
    RADIO_HEADER = "existing_radio_header"


@dataclass(frozen=True, slots=True)
class BenchProfile(MessageProtocol):
    """Validated values shared with the installed Gateway and Tracker images."""

    radio_inventory: str | None
    antenna_inventory: str | None
    max_retries: int
    ack_timeout_ms: int


class TransportError(OSError):
    """Raised when the existing hardware transport is unavailable or unsafe."""


class ProfileError(ValueError):
    """Raised when the active project LoRa profile is inconsistent."""


class ProfileTypeError(TypeError):
    """Raised when an active project profile field has the wrong type."""


def load_bench_profile(path: Path = PROJECT_CONFIG) -> BenchProfile:
    """Read the active LoRa profile and fail closed on malformed fields."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise make_error(
            ProfileError, f"Cannot read the active LoRa profile at {path}: {error}"
        ) from error
    if not isinstance(document, dict):
        raise make_error(ProfileTypeError, "active LoRa profile must be a JSON object")
    experiment = document.get("experiment")
    protocol = document.get("protocol")
    retries = document.get("retries")
    timeouts = document.get("timeouts")
    if (
        not isinstance(experiment, dict)
        or not isinstance(protocol, dict)
        or not isinstance(retries, dict)
        or not isinstance(timeouts, dict)
    ):
        raise make_error(
            ProfileTypeError,
            "active LoRa profile is missing experiment, protocol, or retry settings",
        )
    if experiment.get("mode") != ProfileValue.SINGLE_PACKET:
        raise make_error(
            ProfileError, "the installed bench supports only the configured single-packet profile"
        )
    if protocol.get("encoding") != ProfileValue.RADIO_HEADER:
        raise make_error(ProfileError, "unsupported LoRa wire encoding in the active profile")
    payload_text = protocol.get("payload")
    if not isinstance(payload_text, str):
        raise make_error(ProfileTypeError, "protocol payload must be text")
    try:
        payload = payload_text.encode("ascii")
    except UnicodeEncodeError as error:
        raise make_error(ProfileError, "installed diagnostic payload must be ASCII") from error
    if not payload or len(payload) > MAX_APPLICATION_PAYLOAD_BYTES:
        raise make_error(
            ProfileError, "configured application payload exceeds the existing transport limit"
        )

    return BenchProfile(
        payload=payload,
        data_type=_required_int(protocol, "data_type", 0, 255),
        ack_type=_required_int(protocol, "ack_type", 0, 255),
        nack_type=_required_int(protocol, "nack_type", 0, 255),
        sequence=_required_int(protocol, "sequence", 1, 255),
        gateway_address=_required_int(protocol, "sender_address", 0, 255),
        tracker_address=_required_int(protocol, "receiver_address", 0, 255),
        sequence_bits=_required_int(protocol, "sequence_bits", 1, 8),
        radio_inventory=_optional_inventory(experiment, "radio_inventory"),
        antenna_inventory=_optional_inventory(experiment, "antenna_inventory"),
        max_retries=_required_int(retries, "max_retries", 0, 255),
        ack_timeout_ms=_required_int(timeouts, "ack_ms", 1, 60000),
    )


class BenchTransport:
    """Reuse existing identity verification, event capture, RF exchange, and cleanup."""

    def __init__(
        self,
        run_dir: Path,
        profile: BenchProfile,
        *,
        max_message_bytes: int,
        authorize_rf_test: bool,
        dry_run: bool = False,
        confirm_rf_setup: bool = False,
        historical_receipt: Path | None = None,
    ) -> None:
        """Create one run directory and a non-flashing production bench adapter."""
        self.run_dir = run_dir
        self.profile = profile
        if not 1 <= max_message_bytes <= MAX_HOST_MESSAGE_BYTES:
            raise make_error(
                ProfileError, "maximum message size is outside the supported host bound"
            )
        self.max_message_bytes = max_message_bytes
        self.interactive_checked = False
        self.interactive_max_data_bytes: int | None = None
        self.interactive_capability_error: str | None = None
        self.authorize_rf_test = authorize_rf_test
        self.confirm_rf_setup = confirm_rf_setup
        self.historical_receipt = historical_receipt
        self.legacy_images: dict[str, dict[str, Any]] = {}
        self.capture: installed_rf.Capture | None = None
        self.trusted_roles: set[str] = set()
        self.ready_roles: set[str] = set()
        self.standby_roles: set[str] = set()
        self.runtime_builds: dict[str, str] = {}
        self.reported_radio: dict[str, str] = {}
        self.legacy_profile: dict[str, Any] = {}
        self.dry_run = dry_run
        self.verbose = False
        self.log: Session | None = None
        self.hardware: Hardware | None = None
        self.connected = False
        self.parked = False
        self.last_park_ok: bool | None = None
        self.connection_stage = "DRY_RUN" if dry_run else "NOT_STARTED"
        self.connection_error: str | None = None
        if dry_run:
            run_dir.mkdir(parents=True, exist_ok=False)
            (run_dir / "events.jsonl").touch()
            return

        self.log = Session(run_dir)
        (run_dir / "rf-authorization.json").write_text(
            json.dumps(
                {
                    "authorize_rf_test": authorize_rf_test,
                    "confirm_rf_setup": confirm_rf_setup,
                    "historical_receipt": str(historical_receipt) if historical_receipt else None,
                },
                indent=2,
            )
            + "\n"
        )
        self.hardware = Hardware(self.log)
        self.hardware.no_flash = True
        self.hardware.write_approval = None
        self.hardware.authorize_rf = authorize_rf_test and confirm_rf_setup
        self.hardware.verbose = False

    def connect(self) -> None:
        """Verify installed images and identities, open both UPDI monitors, and arm RX."""
        if self.dry_run:
            return
        if self.hardware is None:
            raise make_error(TransportError, "hardware adapter was not initialized")
        self.interactive_checked = False
        self.interactive_max_data_bytes = None
        self.interactive_capability_error = None
        self.capture = None
        self.legacy_images = {}
        self.trusted_roles.clear()
        self.ready_roles.clear()
        self.standby_roles.clear()
        self.runtime_builds.clear()
        self.reported_radio.clear()
        self.parked = False
        self.last_park_ok = None
        self.connection_error = None
        self.connection_stage = "FLASH_READBACK"
        try:
            images = self.hardware.read_chat_images()
        except (OSError, ValueError, RuntimeError) as error:
            self.connection_stage = self.hardware.stage
            self.connection_error = str(error)
            self._record_board_status()
            raise
        current_pair = len(images) == DEVICE_ROLE_COUNT and all(
            image["verified"] for image in images.values()
        )
        if not current_pair:
            proof = self.hardware.proof
            if self.historical_receipt is not None and proof is not None:
                try:
                    self.legacy_images = installed_rf.verify_snapshots(
                        proof.run_dir, self.historical_receipt
                    )
                except (OSError, ValueError, KeyError, TypeError) as error:
                    self.connection_error = f"Historical image verification failed: {error}"
            self._connect_capture()
        else:
            try:
                self.hardware.ready()
                self.trusted_roles = {role.lower() for role in images}
                self.ready_roles = self.trusted_roles.copy()
                self.runtime_builds = {
                    role.lower(): image["build_id"] for role, image in images.items()
                }
                self._negotiate_interactive()
            except (OSError, ValueError, RuntimeError) as error:
                self.connection_error = str(error)
                self.hardware.close()
                self.trusted_roles.clear()
                self.ready_roles.clear()
                self.runtime_builds.clear()
                self._connect_capture()
        self.connected = self.monitors_open
        self.connection_stage = (
            "READY"
            if self.ready_roles == self.trusted_roles
            and (len(self.ready_roles) == DEVICE_ROLE_COUNT)
            else "DIAGNOSTICS"
        )
        self._record_board_status()

    def _connect_capture(self) -> None:
        """Open verified MCU ports for runtime diagnostics or the reviewed legacy pair."""
        assert (
            self.hardware is not None and self.hardware.proof is not None and self.log is not None
        )
        capture = installed_rf.Capture(self.hardware.proof, observe=self.log.record)
        self.capture = capture
        radio = tomllib.loads((ROOT / "config/radio_915.toml").read_text())["radio"]
        self.legacy_profile = {**radio, "frequency_mhz": radio["frequency_hz"] / 1_000_000}
        for role in ("receiver", "gateway"):
            if role.upper() not in self.hardware.images:
                continue
            try:
                capture.connect(role)
                if self.legacy_images:
                    self.trusted_roles.add(role)
                    capture.marker(role, "R", installed_rf.RX_READY_MARKER)
                    installed_rf.verify_console(
                        capture, role, self.legacy_images[role.upper()], self.legacy_profile
                    )
                    self.ready_roles.add(role)
                else:
                    start = capture.send(role, "?")
                    capture.wait(
                        lambda: any(
                            line
                            in (
                                f"[{role.upper()}] RADIO_READY",
                                f"[{role.upper()}] RADIO_NOT_READY",
                            )
                            for line in capture.fresh_lines(role, start)
                        ),
                        12,
                    )
            except OSError as error:
                self.connection_error = str(error)
            finally:
                ids = [
                    line.split("=", 1)[1]
                    for line in capture.fresh_lines(role, 0)
                    if line.startswith(f"[{role.upper()}] BUILD_ID=")
                ]
                if ids:
                    self.runtime_builds[role] = ids[-1]
                for line in reversed(capture.fresh_lines(role, 0)):
                    if line in (
                        f"[{role.upper()}] RADIO_READY",
                        f"[{role.upper()}] RADIO_NOT_READY",
                    ):
                        self.reported_radio[role] = line.split()[-1] + " (firmware report)"
                        break
        self.interactive_checked = bool(self.legacy_images)

    def _record_board_status(self) -> None:
        """Keep both independent diagnostic records alongside the event journal."""
        if self.log is not None:
            status = {role.value: self.board_status(role.value) for role in DeviceRole}
            (self.run_dir / "boards.json").write_text(json.dumps(status, indent=2) + "\n")

    def reconnect(self) -> None:
        """Release old ports and repeat read-only connection and capability checks."""
        if not self.dry_run:
            self.park()
            self.connect()

    def events_since(self, offset: int) -> tuple[list[dict[str, Any]], int]:
        """Return newly captured rows from the existing host-side event journal."""
        if self.log is None:
            return [], offset
        rows = self.log.snapshot()
        return rows[offset:], len(rows)

    def attach_prompt_output(self, output: TextIO, *, verbose: bool) -> None:
        """Route verbose monitor output through prompt_toolkit's safe stdout proxy."""
        self.verbose = verbose
        if self.hardware is not None:
            self.hardware.verbose = verbose
            if verbose:
                self.hardware.out = output

    def send_message(self, text: str) -> ExchangeResult:
        """Send one UTF-8 message through the negotiated bounded radio transport."""
        return self.retry_message(text)

    def retry_message(self, text: str) -> ExchangeResult:
        """Run a new bounded, replay-protected transaction after validating input."""
        payload = encode_interactive_message(text, self.max_message_bytes)
        self._require_transmit()
        if self.hardware is None or self.log is None:
            raise make_error(TransportError, "real Gateway and Tracker monitors are unavailable")
        self.log.step = DATA_CHECKPOINT_INDEX
        if self.legacy_images:
            if text != "hello world":
                return self._unsupported_payload_result()
            return self._run_exchange(self.legacy_exchange)
        max_data_bytes = self.interactive_max_data_bytes
        if max_data_bytes is None:
            return self._unsupported_payload_result()
        fragments = fragment_message(payload, max_data_bytes)
        return self._run_exchange(lambda: self._hardware_exchange(fragments, max_data_bytes))

    def _hardware_exchange(
        self, fragments: tuple[bytes, ...], max_data_bytes: int
    ) -> dict[str, Any]:
        """Run the current firmware exchange and invalidate its parked readiness."""
        assert self.hardware is not None
        try:
            return self.hardware.exchange_interactive_message(fragments, max_data_bytes)
        finally:
            self.ready_roles.clear()

    def legacy_exchange(self, *, nack: bool = False) -> dict[str, Any]:
        """Run one reviewed installed-firmware DATA/ACK (optionally with controlled NACK)."""
        self._require_transmit()
        if self.capture is None or not self.legacy_images:
            raise make_error(TransportError, "the reviewed legacy pair is unavailable")
        try:
            result = installed_rf.exchange_once(
                self.capture, self.legacy_images, self.legacy_profile, nack=nack
            )
        except OSError, ValueError:
            self.ready_roles.clear()
            self.connection_error = "Legacy exchange stopped before verification"
            self.connection_stage = "RF_FAILED"
            raise
        return {**result, "status": "PASS", "detail": "Verified legacy DATA/ACK", "legacy": True}

    def _negotiate_interactive(self) -> int | None:
        """Require matching live capabilities from Gateway and Tracker before arbitrary DATA."""
        if self.interactive_checked:
            return self.interactive_max_data_bytes
        if self.hardware is None or self.log is None:
            raise make_error(TransportError, "real Gateway and Tracker monitors are unavailable")

        start = len(self.log.snapshot())
        for role in ("receiver", "gateway"):
            self.hardware.command(role, "V")

        try:
            self.hardware.wait(
                lambda: self._both_capability_records(start),
                self.profile.ack_timeout_ms / 1000,
                "interactive capabilities from both firmware roles",
            )
        except TimeoutError:
            self.interactive_capability_error = (
                "installed firmware did not advertise interactive DATA/Echo capabilities"
            )
        else:
            events = [
                event
                for row in self.log.snapshot(start)
                if (event := parse_firmware_event(row)) is not None
            ]
            self.interactive_max_data_bytes = negotiated_payload_limit(events)
            if self.interactive_max_data_bytes is None:
                self.interactive_capability_error = (
                    "Gateway and Tracker lack matching interactive DATA/Echo capabilities"
                )

        self.interactive_checked = True
        return self.interactive_max_data_bytes

    def _both_capability_records(self, start: int) -> bool:
        """Check for fresh capability records from both physical endpoints."""
        if self.log is None:
            return False
        events = [
            event
            for row in self.log.snapshot(start)
            if (event := parse_firmware_event(row)) is not None
        ]
        roles = {event.role for event in events if event.name == EventName.INTERACTIVE_CAPS}
        return roles == {DeviceRole.GATEWAY, DeviceRole.TRACKER}

    def _unsupported_payload_result(self) -> ExchangeResult:
        """Describe the legacy-only firmware contract without recording DATA evidence."""
        detail = (
            self.interactive_capability_error
            or "installed firmware does not support interactive DATA/Echo"
        )
        return ExchangeResult(
            status=ExchangeStatus.UNSUPPORTED,
            detail=(
                f"{detail}; only configured payload "
                f"{self.profile.payload.decode('ascii')} is supported"
            ),
            events=(),
            attempts=0,
            retries=0,
            timeouts=0,
            host_elapsed_ms=0.0,
        )

    def park(self) -> bool:
        """Park both radios with the existing P command and release both serial monitors."""
        if not self.monitors_open:
            return self.last_park_ok if self.last_park_ok is not None else True
        clean = True
        if self.capture is not None:
            clean = self.trusted_roles <= self.capture.monitors.keys()
            for role in tuple(self.capture.monitors):
                try:
                    if role in self.trusted_roles:
                        self.capture.park(role)
                        self.standby_roles.add(role)
                except OSError as error:
                    clean = False
                    self.connection_error = str(error)
                finally:
                    self.capture.close(role)
        elif self.hardware is not None and self.log is not None:
            start = len(self.log.snapshot())
            clean = self.hardware.close()
            for role in self.trusted_roles:
                if (
                    f"[{role.upper()}] PARKED E=0"
                    in self.hardware.text(role.upper(), start).splitlines()
                ):
                    self.standby_roles.add(role)
        self.ready_roles.clear()
        self.connected = False
        self.parked = bool(self.trusted_roles)
        self.last_park_ok = clean
        self._record_board_status()
        return clean

    def close(self) -> bool:
        """Release the monitored devices on every normal or interrupted exit."""
        return self.park()

    def board_status(self, role: str) -> dict[str, str]:
        """Report independent USB, identity, image, runtime, radio and FOTA observations."""
        key = "receiver" if role == DeviceRole.TRACKER else "gateway"
        hardware = self.hardware
        image = hardware.images.get(key.upper()) if hardware is not None else None
        radio = "Unknown"
        if self._monitor_live(key) and key in self.ready_roles:
            radio = "Verified ready"
            if (
                self.capture is not None
                and (key, self.capture.generations[key]) not in self.capture.ready_barriers
            ):
                radio = "Fresh readiness required"
        elif key in self.standby_roles:
            radio = "Standby"
        elif self._monitor_live(key) and key not in self.trusted_roles:
            radio = self.reported_radio.get(key, "Unknown")
        return {
            "Monitor": "Connected" if self._monitor_live(key) else "Disconnected",
            "USB": "Present" if hardware is not None and key in hardware.usb_present else "Absent",
            "Enrolled MCU": image["serial_number"] if image else "Unverified",
            "Current build": ("Match" if image["verified"] else "Mismatch") if image else "Unread",
            "Runtime build": self.runtime_builds.get(key, "Unobserved"),
            "Radio": radio,
            "FOTA": image.get("fota_layout_status", "Unverified") if image else "Unverified",
        }

    def transmit_blocker(self) -> str | None:
        """Explain why DATA is blocked before touching either transmitter."""
        if self.dry_run:
            return "dry-run mode disables hardware access and RF transmission"
        if not self.authorize_rf_test:
            return "pass --authorize-rf-test to enable bounded RF exchanges"
        if not self.confirm_rf_setup:
            return "RF arrangement is unresolved; pass --confirm-rf-setup after confirming it"
        if not self.is_connected:
            return (
                self.connection_error
                or "both verified Gateway and Tracker monitors must be connected"
            )
        if self.connection_stage != "READY":
            return (
                self.connection_error
                or "both installed builds require fresh verified runtime and PHY evidence"
            )
        radio = (
            self.legacy_profile
            if self.legacy_images
            else self.hardware.manifest["shared"]["radio"]
            if self.hardware is not None
            else {}
        )
        if radio.get("frequency_hz") != BENCH_FREQUENCY_HZ:
            return "the verified runtime profile is outside the confirmed 915 MHz setup"
        if not self.legacy_images and self.interactive_max_data_bytes is None:
            return (
                self.interactive_capability_error or "both runtimes must advertise interactive Echo"
            )
        return None

    @property
    def echo_supported(self) -> bool | None:
        """Return verified Echo support, leaving unrecognized pairs unknown."""
        if self.legacy_images:
            return False
        return True if self.interactive_max_data_bytes is not None else None

    @property
    def interactive_state(self) -> str:
        """Report negotiated payload support from the verified pair."""
        if self.legacy_images:
            return "Legacy DATA/ACK · hello world"
        if self.interactive_max_data_bytes is None:
            return "Echo unverified"
        return f"Echo enabled · {self.interactive_max_data_bytes} bytes per DATA packet"

    def _monitor_live(self, role: str) -> bool:
        if self.capture is not None:
            return (
                not self.capture.disconnected(role)
                and (role, self.capture.generations[role]) not in self.capture.reset_connections
            )
        if self.hardware is None or self.hardware.fault:
            return False
        monitor = self.hardware.monitors.get(role)
        return monitor is not None and monitor["process"].poll() is None

    @property
    def is_connected(self) -> bool:
        """Require a responsive monitor on each verified MCU."""
        return self.connected and all(self._monitor_live(role) for role in ("gateway", "receiver"))

    @property
    def monitors_open(self) -> bool:
        """Report whether any real UPDI monitor process still owns a device port."""
        if self.capture is not None:
            return bool(self.capture.monitors)
        return self.hardware is not None and bool(self.hardware.monitors)

    def _require_transmit(self) -> None:
        """Fail closed before writing a DATA command unless every RF prerequisite is met."""
        reason = self.transmit_blocker()
        if reason:
            raise make_error(TransportError, reason)

    def _exchange_result(
        self, raw_result: dict[str, Any], start_index: int, started: float
    ) -> ExchangeResult:
        """Convert the production runner result and actual captured rows to typed data."""
        if self.log is None:
            raise make_error(TransportError, "host event journal is unavailable")
        rows = self.log.snapshot()[start_index:]
        events = tuple(event for row in rows if (event := parse_firmware_event(row)) is not None)
        status = raw_result.get("status")
        detail = raw_result.get("detail")
        if not isinstance(status, str) or not isinstance(detail, str):
            raise make_error(
                TransportError, "production bench returned a malformed transaction result"
            )
        observed_attempts = sum(
            1
            for event in events
            if event.role is DeviceRole.GATEWAY and event.name == EventName.DATA_TX_BEGIN
        )
        attempts = _result_count(raw_result, "attempts", observed_attempts)
        observed_retries = (
            max(0, attempts - 1)
            if self.legacy_images
            else sum(event.name in RETRY_EVENTS for event in events)
        )
        retries = _result_count(raw_result, "retries", observed_retries)
        observed_timeouts = sum(event.name in TIMEOUT_EVENTS for event in events)
        timeouts = _result_count(raw_result, "timeouts", observed_timeouts)
        return ExchangeResult(
            status=status,
            detail=detail,
            events=events,
            attempts=attempts,
            retries=retries,
            timeouts=timeouts,
            host_elapsed_ms=(time.monotonic() - started) * 1000,
            legacy_data_ack=raw_result.get("legacy") is True and status == ExchangeStatus.SUCCESS,
        )

    def _run_exchange(self, operation: Callable[[], dict[str, Any]]) -> ExchangeResult:
        """Run one bounded exchange and retain any real events emitted before failure."""
        if self.log is None:
            raise make_error(TransportError, "host event journal is unavailable")
        start_index = len(self.log.snapshot())
        started = time.monotonic()
        try:
            result = operation()
        except TimeoutError as error:
            result = {"status": "TIMEOUT", "detail": str(error)}
        except (OSError, ValueError, KeyError, RuntimeError) as error:
            result = {"status": "FAIL", "detail": str(error)}
        return self._exchange_result(result, start_index, started)


def _required_int(values: dict[str, Any], name: str, minimum: int, maximum: int) -> int:
    """Read a required bounded integer from project configuration."""
    value = values.get(name)
    if type(value) is not int or not minimum <= value <= maximum:
        if type(value) is not int:
            raise make_error(
                ProfileTypeError, f"active LoRa profile field {name} must be an integer"
            )
        raise make_error(
            ProfileError, f"active LoRa profile field {name} must be in {minimum}..{maximum}"
        )
    return value


def _optional_inventory(values: dict[str, Any], name: str) -> str | None:
    """Accept only a nonempty inventory label or an explicitly unresolved null."""
    value = values.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise make_error(
            ProfileTypeError, f"active LoRa profile field {name} must be nonempty text or null"
        )
    return value.strip()


def _result_count(values: dict[str, Any], name: str, observed: int = 0) -> int:
    """Read an optional nonnegative result counter from the existing bench runner."""
    value = values.get(name, observed)
    if type(value) is not int or value < 0:
        raise make_error(TransportError, f"production bench returned invalid {name} count")
    return value
