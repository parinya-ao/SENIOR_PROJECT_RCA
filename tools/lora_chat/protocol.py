"""Parse the existing LoRa firmware events without creating radio evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

from tools.lora_chat.errors import make_error
from tools.device_detection.evidence import DeviceRole as CanonicalDeviceRole
from tools.device_detection.firmware_events import (
    FirmwareEventName,
    parse_firmware_event_line,
)

DeviceRole = CanonicalDeviceRole
EventName = FirmwareEventName
MAX_APPLICATION_PAYLOAD_BYTES = 249
MAX_HOST_MESSAGE_BYTES = 65_536
MAX_CAMPAIGN_ID = 0xFFFF
MAX_SEQUENCE = 0xFF
MAX_SEQUENCE_BITS = MAX_SEQUENCE.bit_length()
FIRMWARE_TICK_MASK = 0xFFFFFFFF
TIMEOUT_EVENTS = {
    EventName.ACK_TIMEOUT,
    EventName.ACK_CONFIRM_TIMEOUT,
    EventName.ECHO_TIMEOUT,
    EventName.TX_TIMEOUT,
    EventName.TIMEOUT,
}
RETRY_EVENTS = {EventName.RETRY_SCHEDULED, EventName.ACK_CONFIRM_RETRY}


class EventField(StrEnum):
    """Structured field names used in firmware event lines."""

    DESTINATION = "DST"
    DESTINATION_LONG = "DEST"
    HEX = "HEX"
    ECHO = "ECHO"
    LENGTH = "LEN"
    MAX_DATA = "MAX_DATA"
    PACKET_TYPE = "TYPE"
    SEQUENCE = "Q"
    SEQUENCE_LEGACY = "S"
    SOURCE = "SRC"
    SOURCE_LONG = "SOURCE"
    TIME = "T"
    CAMPAIGN = "SID"


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
    max_data_bytes: int | None = None
    echo_supported: bool | None = None


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
    sequence_bits: int = field(default=8, kw_only=True)


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
    sequence_bits: int = 8


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


def encode_interactive_message(text: str, max_message_bytes: int) -> bytes:
    """Encode one bounded UTF-8 message without imposing the legacy fixed payload."""
    if max_message_bytes < 1:
        raise make_error(PayloadConfigurationError, "configured message maximum must be positive")
    try:
        payload = text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise make_error(UnsupportedPayloadError, "message is not valid UTF-8 text") from error
    if not payload:
        raise make_error(UnsupportedPayloadError, "empty messages are not supported")
    if len(payload) > max_message_bytes:
        raise make_error(
            UnsupportedPayloadError,
            f"message exceeds configured maximum of {max_message_bytes} UTF-8 bytes",
        )
    return payload


def fragment_message(payload: bytes, max_fragment_bytes: int) -> tuple[bytes, ...]:
    """Split exact message bytes at the firmware-negotiated per-packet limit."""
    if not payload:
        raise make_error(UnsupportedPayloadError, "empty messages are not supported")
    if max_fragment_bytes < 1:
        raise ValueError("fragment size must be positive")
    return tuple(
        payload[offset : offset + max_fragment_bytes]
        for offset in range(0, len(payload), max_fragment_bytes)
    )


def encode_interactive_command(payload: bytes, max_data_bytes: int) -> str:
    """Encode one bounded payload as an ASCII UPDI control command."""
    if not payload:
        raise make_error(UnsupportedPayloadError, "empty DATA payload is not supported")
    if not 1 <= max_data_bytes <= MAX_APPLICATION_PAYLOAD_BYTES:
        raise make_error(PayloadConfigurationError, "firmware packet limit is invalid")
    if len(payload) > max_data_bytes:
        raise make_error(
            UnsupportedPayloadError,
            f"payload exceeds firmware packet limit of {max_data_bytes} bytes",
        )
    return f"X{len(payload):02X}{payload.hex().upper()}"


def parse_firmware_event(row: Mapping[str, object]) -> DeviceEvent | None:
    """Parse one existing UART log row; ignore host and unrelated diagnostics."""
    role_text = row.get("role")
    line = row.get("line")
    host_timestamp = row.get("timestamp")
    if not isinstance(role_text, str) or not isinstance(line, str):
        raise make_error(ProtocolParseError, "event row requires string role and line fields")
    role = DeviceRole.from_legacy(role_text)
    if role is None:
        return None
    try:
        parsed = parse_firmware_event_line(line)
    except ValueError as error:
        raise make_error(ProtocolParseError, str(error)) from error
    if parsed is None or parsed.role is not role:
        return None

    name = parsed.name
    fields = parsed.fields
    max_data = _optional_bounded_decimal(fields, EventField.MAX_DATA, MAX_APPLICATION_PAYLOAD_BYTES)
    echo = _optional_bounded_decimal(fields, EventField.ECHO, 1)
    payload: bytes | None = None
    if EventField.HEX in fields:
        try:
            payload = bytes.fromhex(fields[EventField.HEX])
        except ValueError as error:
            raise make_error(ProtocolParseError, "event payload hex is malformed") from error
        if len(payload) > MAX_APPLICATION_PAYLOAD_BYTES:
            raise make_error(
                ProtocolParseError, "event payload exceeds the existing transport limit"
            )
        if EventField.LENGTH in fields and _decimal(
            fields[EventField.LENGTH], EventField.LENGTH
        ) != len(payload):
            raise make_error(
                ProtocolParseError, "event payload length does not match its hex bytes"
            )

    return DeviceEvent(
        role=role,
        name=name,
        line=line,
        host_timestamp=host_timestamp if isinstance(host_timestamp, str) else "",
        firmware_ms=_optional_bounded_decimal(fields, EventField.TIME, FIRMWARE_TICK_MASK),
        campaign_id=_optional_hex(fields, EventField.CAMPAIGN, 0xFFFF),
        sequence=_optional_bounded_decimal(fields, EventField.SEQUENCE, 0xFF)
        if EventField.SEQUENCE in fields
        else _optional_hex(fields, EventField.SEQUENCE_LEGACY, 0xFF),
        packet_type=_optional_bounded_decimal(fields, EventField.PACKET_TYPE, 0xFF),
        source=_optional_bounded_decimal(fields, EventField.SOURCE, 0xFF)
        if EventField.SOURCE in fields
        else _optional_bounded_decimal(fields, EventField.SOURCE_LONG, 0xFF),
        destination=_optional_bounded_decimal(fields, EventField.DESTINATION, 0xFF)
        if EventField.DESTINATION in fields
        else _optional_bounded_decimal(fields, EventField.DESTINATION_LONG, 0xFF),
        payload=payload,
        max_data_bytes=max_data,
        echo_supported=bool(echo) if echo is not None else None,
    )


def negotiated_payload_limit(events: list[DeviceEvent]) -> int | None:
    """Return the lower live data limit only when both devices advertise echo support."""
    limits: dict[DeviceRole, set[int]] = {DeviceRole.GATEWAY: set(), DeviceRole.TRACKER: set()}
    for event in events:
        if event.name != EventName.INTERACTIVE_CAPS:
            continue
        if event.max_data_bytes is None or event.max_data_bytes < 1 or not event.echo_supported:
            return None
        limits[event.role].add(event.max_data_bytes)
    if any(len(values) != 1 for values in limits.values()):
        return None
    return min(next(iter(limits[role])) for role in limits)


def matches_ack(
    events: list[DeviceEvent], *, campaign_id: int, sequence: int, ack_type: int
) -> bool:
    """Return true only for a Gateway-accepted ACK with the matching identity."""
    return any(
        event.role is DeviceRole.GATEWAY
        and event.name == EventName.ACK_ACCEPTED
        and event.campaign_id == campaign_id
        and event.sequence == sequence
        and event.packet_type == ack_type
        for event in events
    )


def verify_round_trip(events: list[DeviceEvent], context: RoundTripContext) -> bool:
    """Require two DATA/ACK legs for every ordered fragment and exact reassembly."""
    keys = _gateway_transactions(events, context)
    if not keys or not _sequential_transactions(keys, context):
        return False
    expected = set(keys)
    unexpected_control = any(
        event.name in {EventName.ACK_ACCEPTED, EventName.ACK_TX_DONE}
        and event.campaign_id is not None
        and event.sequence is not None
        and (event.campaign_id, event.sequence) not in expected
        for event in events
    )
    if unexpected_control:
        return False

    tracker_chunks: list[bytes] = []
    gateway_chunks: list[bytes] = []
    for identity in keys:
        original = _verified_payload(
            events, DeviceRole.GATEWAY, DeviceRole.TRACKER, identity, context
        )
        echo = _verified_payload(events, DeviceRole.TRACKER, DeviceRole.GATEWAY, identity, context)
        if original is None or echo is None or original != echo:
            return False
        if not _has_ack_confirmation(events, identity, context.ack_type):
            return False
        tracker_chunks.append(original)
        gateway_chunks.append(echo)

    return (
        b"".join(tracker_chunks) == context.original_payload
        and b"".join(gateway_chunks) == context.original_payload
    )


def echo_fragment_latency_ms(
    events: tuple[DeviceEvent, ...], data_type: int, ack_type: int
) -> tuple[int, ...]:
    """Time each proven fragment from Gateway's first DATA TX to its Echo ACK."""
    starts: dict[tuple[int, int], int] = {}
    elapsed: dict[tuple[int, int], int] = {}
    for event in events:
        if (
            event.role is not DeviceRole.GATEWAY
            or event.firmware_ms is None
            or event.campaign_id is None
            or event.sequence is None
        ):
            continue
        identity = (event.campaign_id, event.sequence)
        if event.name == EventName.DATA_TX_BEGIN and event.packet_type == data_type:
            starts.setdefault(identity, event.firmware_ms)
        elif (
            event.name == EventName.ACK_TX_DONE
            and event.packet_type == ack_type
            and identity in starts
        ):
            elapsed[identity] = (event.firmware_ms - starts[identity]) & FIRMWARE_TICK_MASK
    return tuple(elapsed.values())


def _gateway_transactions(
    events: list[DeviceEvent], context: RoundTripContext
) -> list[tuple[int, int]]:
    """Return unique Gateway DATA identities in their observed transmission order."""
    keys: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for event in events:
        if (
            event.role is not DeviceRole.GATEWAY
            or event.name != EventName.DATA_TX_BEGIN
            or event.packet_type != context.data_type
            or event.campaign_id is None
            or event.sequence is None
        ):
            continue
        identity = (event.campaign_id, event.sequence)
        if identity not in seen:
            keys.append(identity)
            seen.add(identity)
    return keys


def _sequential_transactions(keys: list[tuple[int, int]], context: RoundTripContext) -> bool:
    """Require each next fragment to use the protocol's sequence/campaign successor."""
    if not 1 <= context.sequence_bits <= MAX_SEQUENCE_BITS:
        return False
    max_sequence = (1 << context.sequence_bits) - 1
    campaign_id, sequence = context.campaign_id, context.sequence
    for identity in keys:
        if identity != (campaign_id, sequence):
            return False
        if sequence == max_sequence:
            campaign_id = 1 if campaign_id == MAX_CAMPAIGN_ID else campaign_id + 1
            sequence = 1
        else:
            sequence += 1
    return True


def _has_event(
    events: list[DeviceEvent],
    role: DeviceRole,
    name: EventName,
    identity: tuple[int, int],
    packet_type: int,
) -> bool:
    """Find one real event with the exact role and wire identity."""
    campaign_id, sequence = identity
    return any(
        event.role is role
        and event.name == name
        and event.campaign_id == campaign_id
        and event.sequence == sequence
        and event.packet_type == packet_type
        for event in events
    )


def _payload_for(
    events: list[DeviceEvent], role: DeviceRole, campaign_id: int, sequence: int
) -> list[DeviceEvent]:
    """Return actual payload-byte records for one direction and transaction."""
    return [
        event
        for event in events
        if event.role is role
        and event.name == EventName.PAYLOAD_BYTES
        and event.campaign_id == campaign_id
        and event.sequence == sequence
        and event.payload is not None
    ]


def _address_matches(
    events: list[DeviceEvent],
    role: DeviceRole,
    identity: tuple[int, int],
    source: int,
    destination: int,
) -> bool:
    """Require the receiving firmware to report the direction's decoded addresses."""
    campaign_id, sequence = identity
    return any(
        event.role is role
        and event.name == EventName.DATA_ADDRESS
        and event.campaign_id == campaign_id
        and event.sequence == sequence
        and event.source == source
        and event.destination == destination
        for event in events
    )


def _verified_payload(
    events: list[DeviceEvent],
    source_role: DeviceRole,
    receiver_role: DeviceRole,
    identity: tuple[int, int],
    context: RoundTripContext,
) -> bytes | None:
    """Return received bytes only when a complete addressed DATA/ACK leg is proven."""
    source_address, destination_address = (
        (context.gateway_address, context.tracker_address)
        if source_role is DeviceRole.GATEWAY
        else (context.tracker_address, context.gateway_address)
    )
    payloads = _payload_for(events, receiver_role, *identity)
    complete_leg = (
        _has_event(events, source_role, EventName.DATA_TX_DONE, identity, context.data_type)
        and _has_event(events, receiver_role, EventName.DATA_VALIDATED, identity, context.data_type)
        and len(payloads) == 1
        and _address_matches(events, receiver_role, identity, source_address, destination_address)
        and _has_event(events, receiver_role, EventName.ACK_TX_DONE, identity, context.ack_type)
        and _has_event(events, source_role, EventName.ACK_ACCEPTED, identity, context.ack_type)
    )
    return payloads[0].payload if complete_leg else None


def _has_ack_confirmation(
    events: list[DeviceEvent], identity: tuple[int, int], ack_type: int
) -> bool:
    """Require Gateway TX completion and Tracker RX of the matching confirmation."""
    return _has_event(
        events, DeviceRole.GATEWAY, EventName.ACK_CONFIRM_TX_DONE, identity, ack_type
    ) and _has_event(events, DeviceRole.TRACKER, EventName.ACK_CONFIRM_RX, identity, ack_type)


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
