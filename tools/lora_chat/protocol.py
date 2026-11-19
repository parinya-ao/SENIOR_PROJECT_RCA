"""Parse the existing LoRa firmware events without creating radio evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

from tools.lora_chat.errors import make_error

_FIELD_PATTERN = re.compile(r"\b([A-Z][A-Z0-9_]*)=([^\s]+)")
MAX_APPLICATION_PAYLOAD_BYTES = 249


class DeviceRole(StrEnum):
    """Physical role names used by Gateway and Tracker event records."""

    GATEWAY = "GATEWAY"
    TRACKER = "TRACKER"


@dataclass(frozen=True, slots=True)
class DeviceEvent:
    """One parsed firmware line, retaining both host and firmware timestamps."""

    role: DeviceRole
    name: str
    line: str
    host_timestamp: str
    firmware_ms: int | None
    campaign_id: int | None
    sequence: int | None
    packet_type: int | None
    source: int | None
    destination: int | None
    payload: bytes | None


@dataclass(frozen=True, slots=True)
class MessageProtocol:
    """Application protocol fields shared by the transport and chat session."""

    payload: bytes
    data_type: int
    ack_type: int
    nack_type: int
    sequence: int
    gateway_address: int
    tracker_address: int


@dataclass(frozen=True, slots=True)
class RoundTripContext:
    """Identity and addressing needed to prove one complete two-way transaction."""

    campaign_id: int
    sequence: int
    original_payload: bytes
    data_type: int
    ack_type: int
    gateway_address: int
    tracker_address: int


class UnsupportedPayloadError(ValueError):
    """Raised when a message is outside the installed firmware contract."""


class ProtocolParseError(ValueError):
    """Raised when a device event contains malformed structured fields."""


class PayloadConfigurationError(ValueError):
    """Raised when the installed payload contract exceeds a protocol invariant."""


def encode_message(text: str, configured_payload: bytes, max_payload_bytes: int) -> bytes:
    """Encode only the exact application bytes accepted by the installed Tracker."""
    try:
        payload = text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise make_error(UnsupportedPayloadError, "message is not valid UTF-8 text") from error

    if not configured_payload or len(configured_payload) > max_payload_bytes:
        raise make_error(
            PayloadConfigurationError, "configured payload exceeds the existing transport limit"
        )
    if payload != configured_payload:
        raise make_error(
            UnsupportedPayloadError, "message must match the installed Tracker's configured payload"
        )
    return payload


def parse_firmware_event(row: Mapping[str, object]) -> DeviceEvent | None:
    """Parse one existing UART log row; ignore host and unrelated diagnostics."""
    role_text = row.get("role")
    line = row.get("line")
    host_timestamp = row.get("timestamp")
    if not isinstance(role_text, str) or not isinstance(line, str):
        raise make_error(ProtocolParseError, "event row requires string role and line fields")
    if role_text == "GATEWAY":
        role = DeviceRole.GATEWAY
        prefix = "[GATEWAY] "
    elif role_text in {"RECEIVER", "TRACKER"}:
        role = DeviceRole.TRACKER
        prefix = "[RECEIVER] " if role_text == "RECEIVER" else "[TRACKER] "
    else:
        return None
    if not line.startswith(prefix):
        return None

    body = line[len(prefix) :]
    parts = body.split(maxsplit=1)
    if not parts:
        return None
    name = parts[0]
    fields = dict(_FIELD_PATTERN.findall(body))
    payload: bytes | None = None
    if "HEX" in fields:
        try:
            payload = bytes.fromhex(fields["HEX"])
        except ValueError as error:
            raise make_error(ProtocolParseError, "event payload hex is malformed") from error
        if len(payload) > MAX_APPLICATION_PAYLOAD_BYTES:
            raise make_error(
                ProtocolParseError, "event payload exceeds the existing transport limit"
            )
        if "LEN" in fields and _decimal(fields["LEN"], "LEN") != len(payload):
            raise make_error(
                ProtocolParseError, "event payload length does not match its hex bytes"
            )

    return DeviceEvent(
        role=role,
        name=name,
        line=line,
        host_timestamp=host_timestamp if isinstance(host_timestamp, str) else "",
        firmware_ms=_optional_bounded_decimal(fields, "T", 0xFFFFFFFF),
        campaign_id=_optional_hex(fields, "SID", 0xFFFF),
        sequence=_optional_bounded_decimal(fields, "Q", 0xFF)
        if "Q" in fields
        else _optional_hex(fields, "S", 0xFF),
        packet_type=_optional_bounded_decimal(fields, "TYPE", 0xFF),
        source=_optional_bounded_decimal(fields, "SRC", 0xFF)
        if "SRC" in fields
        else _optional_bounded_decimal(fields, "SOURCE", 0xFF),
        destination=_optional_bounded_decimal(fields, "DST", 0xFF)
        if "DST" in fields
        else _optional_bounded_decimal(fields, "DEST", 0xFF),
        payload=payload,
    )


def matches_ack(
    events: list[DeviceEvent], *, campaign_id: int, sequence: int, ack_type: int
) -> bool:
    """Return true only for a Gateway-accepted ACK with the matching identity."""
    return any(
        event.role is DeviceRole.GATEWAY
        and event.name == "ACK_ACCEPTED"
        and event.campaign_id == campaign_id
        and event.sequence == sequence
        and event.packet_type == ack_type
        for event in events
    )


def verify_round_trip(events: list[DeviceEvent], context: RoundTripContext) -> bool:
    """Require original ACK, exact Tracker DATA bytes, Gateway ACK, and Tracker acceptance."""
    if not matches_ack(
        events,
        campaign_id=context.campaign_id,
        sequence=context.sequence,
        ack_type=context.ack_type,
    ):
        return False

    echoes = [
        event
        for event in events
        if event.role is DeviceRole.GATEWAY
        and event.name in {"DATA_RX", "PAYLOAD_BYTES"}
        and event.packet_type == context.data_type
        and event.source == context.tracker_address
        and event.destination == context.gateway_address
        and event.payload is not None
    ]
    if len(echoes) != 1 or echoes[0].payload != context.original_payload:
        return False
    echo = echoes[0]
    if echo.campaign_id is None or echo.sequence is None:
        return False

    gateway_ack_sent = any(
        event.role is DeviceRole.GATEWAY
        and event.name == "ACK_TX_DONE"
        and event.campaign_id == echo.campaign_id
        and event.sequence == echo.sequence
        and event.packet_type == context.ack_type
        for event in events
    )
    tracker_ack_accepted = any(
        event.role is DeviceRole.TRACKER
        and event.name == "ACK_ACCEPTED"
        and event.campaign_id == echo.campaign_id
        and event.sequence == echo.sequence
        and event.packet_type == context.ack_type
        for event in events
    )
    return gateway_ack_sent and tracker_ack_accepted


def _decimal(fields: str, name: str) -> int:
    """Parse a nonnegative base-ten field or raise an event-specific error."""
    try:
        value = int(fields, 10)
    except ValueError as error:
        raise make_error(
            ProtocolParseError, f"event field {name} is not a decimal integer"
        ) from error
    if value < 0:
        raise make_error(ProtocolParseError, f"event field {name} cannot be negative")
    return value


def _optional_decimal(fields: dict[str, str], name: str) -> int | None:
    """Parse an optional decimal event field."""
    return _decimal(fields[name], name) if name in fields else None


def _optional_bounded_decimal(fields: dict[str, str], name: str, maximum: int) -> int | None:
    """Parse an optional decimal field within its wire-width range."""
    value = _optional_decimal(fields, name)
    if value is not None and value > maximum:
        raise make_error(ProtocolParseError, f"event field {name} exceeds {maximum}")
    return value


def _optional_hex(fields: dict[str, str], name: str, maximum: int) -> int | None:
    """Parse an optional hexadecimal event field within its wire-width range."""
    if name not in fields:
        return None
    try:
        value = int(fields[name], 16)
    except ValueError as error:
        raise make_error(ProtocolParseError, f"event field {name} is not hexadecimal") from error
    if value < 0:
        raise make_error(ProtocolParseError, f"event field {name} cannot be negative")
    if value > maximum:
        raise make_error(ProtocolParseError, f"event field {name} exceeds {maximum}")
    return value
