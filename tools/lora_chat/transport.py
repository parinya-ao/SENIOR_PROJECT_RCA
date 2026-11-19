"""Adapter for the repository's verified UPDI monitors and RF bench runner."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tools.debug_protocol_ack_nack import Hardware, Session
from tools.lora_chat.errors import make_error
from tools.lora_chat.protocol import (
    MAX_APPLICATION_PAYLOAD_BYTES,
    MessageProtocol,
    encode_message,
    parse_firmware_event,
)
from tools.lora_chat.session import ExchangeResult

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TextIO


ROOT = Path(__file__).resolve().parents[2]
PROJECT_CONFIG = ROOT / "config" / "lora_system.json"
DEVICE_ROLE_COUNT = 2
DATA_CHECKPOINT_INDEX = 2


@dataclass(frozen=True, slots=True)
class BenchProfile(MessageProtocol):
    """Validated values shared with the installed Gateway and Tracker images."""

    radio_inventory: str | None
    antenna_inventory: str | None
    max_retries: int


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
    if (
        not isinstance(experiment, dict)
        or not isinstance(protocol, dict)
        or not isinstance(retries, dict)
    ):
        raise make_error(
            ProfileTypeError,
            "active LoRa profile is missing experiment, protocol, or retry settings",
        )
    if experiment.get("mode") != "single_packet":
        raise make_error(
            ProfileError, "the installed bench supports only the configured single-packet profile"
        )
    if protocol.get("encoding") != "existing_radio_header":
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
        radio_inventory=_optional_inventory(experiment, "radio_inventory"),
        antenna_inventory=_optional_inventory(experiment, "antenna_inventory"),
        max_retries=_required_int(retries, "max_retries", 0, 255),
    )


class BenchTransport:
    """Reuse existing identity verification, event capture, RF exchange, and cleanup."""

    def __init__(
        self,
        run_dir: Path,
        profile: BenchProfile,
        *,
        authorize_rf_test: bool,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        """Create one run directory and a non-flashing production bench adapter."""
        self.run_dir = run_dir
        self.profile = profile
        self.authorize_rf_test = authorize_rf_test
        self.dry_run = dry_run
        self.verbose = verbose
        self.log: Session | None = None
        self.hardware: Hardware | None = None
        self.connected = False
        self.parked = False
        self.last_park_ok: bool | None = None
        if dry_run:
            run_dir.mkdir(parents=True, exist_ok=False)
            (run_dir / "events.jsonl").touch()
            return

        self.log = Session(run_dir)
        self.hardware = Hardware(self.log)
        self.hardware.no_flash = True
        self.hardware.write_approval = None
        self.hardware.authorize_rf = authorize_rf_test
        self.hardware.verbose = verbose

    def connect(self) -> None:
        """Verify installed images and identities, open both UPDI monitors, and arm RX."""
        if self.dry_run:
            return
        if self.hardware is None:
            raise make_error(TransportError, "hardware adapter was not initialized")
        try:
            result = self.hardware.connect()
            if result.get("status") != "PASS":
                raise make_error(
                    TransportError, str(result.get("detail", "device verification failed"))
                )
            self.hardware.ready()
        except OSError, TimeoutError, ValueError, KeyError, RuntimeError:
            self.hardware.close()
            raise
        self.connected = True
        self.parked = False
        self.last_park_ok = None

    def reconnect(self) -> None:
        """Release old ports and repeat the existing readback-verified connection flow."""
        if self.dry_run:
            return
        if self.hardware is not None:
            self.hardware.close()
        self.connected = False
        self.connect()

    def events_since(self, offset: int) -> tuple[list[dict[str, Any]], int]:
        """Return newly captured rows from the existing host-side event journal."""
        if self.log is None:
            return [], offset
        rows = self.log.snapshot()
        return rows[offset:], len(rows)

    def attach_prompt_output(self, output: TextIO) -> None:
        """Route verbose monitor output through prompt_toolkit's safe stdout proxy."""
        if self.verbose and self.hardware is not None:
            self.hardware.out = output

    def send_message(self, text: str) -> ExchangeResult:
        """Send only the exact configured DATA through the existing bounded ARQ runner."""
        encode_message(text, self.profile.payload, MAX_APPLICATION_PAYLOAD_BYTES)
        self._require_transmit()
        if self.hardware is None or self.log is None:
            raise make_error(TransportError, "real Gateway and Tracker monitors are unavailable")
        hardware = self.hardware
        self.log.step = DATA_CHECKPOINT_INDEX
        return self._run_exchange(hardware.exchange)

    def retry_message(self, text: str) -> ExchangeResult:
        """Retry through the existing bench checkpoint, retaining firmware retry rules."""
        encode_message(text, self.profile.payload, MAX_APPLICATION_PAYLOAD_BYTES)
        self._require_transmit()
        if self.hardware is None or self.log is None:
            raise make_error(TransportError, "real Gateway and Tracker monitors are unavailable")
        hardware = self.hardware
        self.log.step = DATA_CHECKPOINT_INDEX
        return self._run_exchange(lambda: hardware.step(DATA_CHECKPOINT_INDEX))

    def park(self) -> bool:
        """Park both radios with the existing P command and release both serial monitors."""
        if self.hardware is None:
            self.connected = False
            return True
        if not self.hardware.monitors:
            self.connected = False
            return self.last_park_ok if self.parked and self.last_park_ok is not None else True
        clean = self.hardware.close()
        self.connected = False
        self.parked = True
        self.last_park_ok = clean
        return clean

    def close(self) -> bool:
        """Release the monitored devices on every normal or interrupted exit."""
        return self.park()

    def firmware_identity(self, role: str) -> str:
        """Return the readback verification state without inventing a device identity."""
        if self.hardware is None:
            return "not connected"
        image_role = "RECEIVER" if role == "TRACKER" else "GATEWAY"
        image = self.hardware.images.get(image_role)
        if not isinstance(image, dict):
            return "not verified"
        build_id = image.get("build_id")
        serial_number = image.get("serial_number")
        if not isinstance(build_id, str):
            return "readback identity unavailable"
        if image.get("verified") is not True:
            return f"{build_id} · readback mismatch"
        if not isinstance(serial_number, str):
            return f"{build_id} · readback verified"
        return f"{build_id} · MCU {serial_number}"

    def radio_state(self, role: str) -> str:
        """Return the latest observed radio-ready state for one physical role."""
        if self.log is None:
            return "not connected"
        log_role = "RECEIVER" if role == "TRACKER" else "GATEWAY"
        for row in reversed(self.log.snapshot()):
            if row.get("role") != log_role:
                continue
            line = row.get("line")
            if isinstance(line, str) and any(
                marker in line for marker in ("RX_READY", "RADIO_READY", "PARKED")
            ):
                return line.split("] ", 1)[-1]
        return "unknown"

    def transmit_blocker(self) -> str | None:
        """Explain why no DATA command may be issued under the current setup."""
        reason: str | None = None
        if self.dry_run:
            reason = "dry-run mode disables hardware access and RF transmission"
        elif not self.authorize_rf_test:
            reason = "pass --authorize-rf-test to enable the existing bounded RF test command"
        elif self.profile.radio_inventory is None or self.profile.antenna_inventory is None:
            reason = (
                "config/lora_system.json has null radio_inventory and antenna_inventory; "
                "the RF test arrangement is unresolved"
            )
        else:
            hardware = self.hardware
            if not self.connected or hardware is None:
                reason = "both verified Gateway and Tracker monitors must be connected"
            elif hardware.fault:
                reason = f"hardware monitor fault: {hardware.fault}"
            elif len(hardware.monitors) != DEVICE_ROLE_COUNT or any(
                monitor["process"].poll() is not None for monitor in hardware.monitors.values()
            ):
                reason = "both verified Gateway and Tracker monitors must be connected"
        return reason

    @property
    def is_connected(self) -> bool:
        """Report responsive monitors only while both enrolled devices remain open."""
        if not self.connected or self.hardware is None or self.hardware.fault:
            return False
        return len(self.hardware.monitors) == DEVICE_ROLE_COUNT and all(
            monitor["process"].poll() is None for monitor in self.hardware.monitors.values()
        )

    @property
    def monitors_open(self) -> bool:
        """Report whether any real UPDI monitor process still owns a device port."""
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
            1 for event in events if event.role.value == "GATEWAY" and event.name == "DATA_TX_BEGIN"
        )
        attempts = _result_count(raw_result, "attempts", observed_attempts)
        retries = _result_count(raw_result, "retries", max(0, attempts - 1))
        observed_timeouts = sum(
            event.name in {"ACK_TIMEOUT", "TX_TIMEOUT", "TIMEOUT"} for event in events
        )
        timeouts = _result_count(raw_result, "timeouts", observed_timeouts)
        return ExchangeResult(
            status=status,
            detail=detail,
            events=events,
            attempts=attempts,
            retries=retries,
            timeouts=timeouts,
            host_elapsed_ms=(time.monotonic() - started) * 1000,
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
