"""Host-side checks for the installed firmware's supported message contract."""

import pytest
from tools.lora_chat import protocol

from tools.lora_chat.protocol import (
    DeviceEvent,
    ProtocolParseError,
    RoundTripContext,
    UnsupportedPayloadError,
    encode_message,
    matches_ack,
    parse_firmware_event,
    verify_round_trip,
)


def test_rejects_text_that_installed_tracker_cannot_accept() -> None:
    """A message outside the configured payload must never reach the RF sender."""
    with pytest.raises(UnsupportedPayloadError, match="configured payload"):
        encode_message("different text", b"hello world", 249)


def test_encodes_supported_utf8_bytes_exactly() -> None:
    """Encoding preserves the exact UTF-8 application bytes."""
    assert encode_message("hello world", b"hello world", 249) == b"hello world"


def test_interactive_encoder_accepts_bounded_utf8_messages() -> None:
    """The interactive mode preserves arbitrary UTF-8 bytes within configured bounds."""
    encoder = getattr(protocol, "encode_interactive_message", None)
    assert callable(encoder), "interactive UTF-8 encoder is missing"
    assert encoder("café", 16) == "café".encode()


def test_fragmentation_preserves_exact_bytes_at_the_negotiated_packet_limit() -> None:
    """Fragments reassemble byte-for-byte without an invented wire envelope."""
    fragmenter = getattr(protocol, "fragment_message", None)
    assert callable(fragmenter), "interactive message fragmentation is missing"
    payload = "café-and-longer".encode()

    fragments = fragmenter(payload, 5)

    assert fragments == (payload[:5], payload[5:10], payload[10:15], payload[15:])
    assert b"".join(fragments) == payload


def test_interactive_host_command_encodes_payload_length_and_bytes() -> None:
    """The UPDI control command carries exact data as bounded ASCII hexadecimal."""
    encoder = getattr(protocol, "encode_interactive_command", None)
    assert callable(encoder), "interactive UPDI data command encoder is missing"
    assert encoder(b"\x00a\xff", 3) == "X030061FF"


def test_interactive_boundaries_reject_empty_oversize_and_invalid_utf8() -> None:
    """Invalid host messages fail before a firmware command can be formed."""
    encoder = getattr(protocol, "encode_interactive_message", None)
    fragmenter = getattr(protocol, "fragment_message", None)
    command = getattr(protocol, "encode_interactive_command", None)
    assert callable(encoder) and callable(fragmenter) and callable(command)
    with pytest.raises(UnsupportedPayloadError, match="empty"):
        encoder("", 16)
    with pytest.raises(UnsupportedPayloadError, match="configured maximum"):
        encoder("long", 3)
    with pytest.raises(ValueError, match="fragment size"):
        fragmenter(b"abc", 0)
    with pytest.raises(UnsupportedPayloadError, match="packet limit"):
        command(b"abcd", 3)


def test_interactive_capability_requires_echo_support_from_both_endpoints() -> None:
    """The host uses the lower live endpoint limit and never assumes legacy echo."""
    capability = getattr(protocol, "negotiated_payload_limit", None)
    assert callable(capability), "runtime capability negotiation is missing"
    gateway = parse_firmware_event(
        {
            "role": "GATEWAY",
            "timestamp": "host-time",
            "line": "[GATEWAY] INTERACTIVE_CAPS MAX_DATA=23 ECHO=1",
        }
    )
    tracker = parse_firmware_event(
        {
            "role": "RECEIVER",
            "timestamp": "host-time",
            "line": "[RECEIVER] INTERACTIVE_CAPS MAX_DATA=19 ECHO=1",
        }
    )
    no_echo = parse_firmware_event(
        {
            "role": "RECEIVER",
            "timestamp": "host-time",
            "line": "[RECEIVER] INTERACTIVE_CAPS MAX_DATA=19 ECHO=0",
        }
    )
    assert gateway is not None and tracker is not None and no_echo is not None
    assert capability([gateway, tracker]) == 19
    assert capability([gateway]) is None
    assert capability([gateway, no_echo]) is None


def test_rejects_configured_payload_beyond_transport_limit() -> None:
    """A bad project profile fails before any device command is sent."""
    with pytest.raises(ValueError, match="transport limit"):
        encode_message("x", b"long", 2)


def test_rejects_invalid_unicode_before_encoding() -> None:
    """Unpaired surrogate input is rejected at the UTF-8 boundary."""
    with pytest.raises(UnsupportedPayloadError, match="valid UTF-8"):
        encode_message("\ud800", b"hello world", 249)


def test_parses_firmware_campaign_sequence_and_payload_bytes() -> None:
    """A device log row becomes structured data without changing its evidence."""
    event = parse_firmware_event(
        {
            "role": "GATEWAY",
            "timestamp": "2026-11-19T14:14:35.000000+00:00",
            "line": (
                "[GATEWAY] PAYLOAD_BYTES SID=351C T=286824 TYPE=08 Q=1 "
                "SRC=1 DST=0 LEN=11 HEX=68656C6C6F20776F726C64 ASCII=hello world"
            ),
        }
    )
    assert event is not None
    assert (event.campaign_id, event.sequence, event.packet_type) == (0x351C, 1, 8)
    assert event.payload == b"hello world"
    assert (event.source, event.destination) == (1, 0)


def test_rejects_malformed_firmware_payload_hex() -> None:
    """Malformed event bytes are reported instead of becoming an empty payload."""
    with pytest.raises(ProtocolParseError, match="payload hex"):
        parse_firmware_event(
            {
                "role": "RECEIVER",
                "timestamp": "host-time",
                "line": "[RECEIVER] PAYLOAD_BYTES SID=351C TYPE=08 Q=1 LEN=1 HEX=zz",
            }
        )


def test_rejects_out_of_range_sequence_from_firmware_log() -> None:
    """Malformed log metadata cannot masquerade as a valid wire identity."""
    with pytest.raises(ProtocolParseError, match="exceeds"):
        parse_firmware_event(
            {
                "role": "GATEWAY",
                "timestamp": "host-time",
                "line": "[GATEWAY] ACK_ACCEPTED SID=351C TYPE=03 Q=256 E=0",
            }
        )


def test_ack_matching_requires_campaign_sequence_and_type() -> None:
    """A stale or unrelated ACK cannot complete the current transaction."""
    ack = parse_firmware_event(
        {
            "role": "GATEWAY",
            "timestamp": "host-time",
            "line": "[GATEWAY] ACK_ACCEPTED SID=351C T=286824 TYPE=03 Q=1 E=0",
        }
    )
    assert ack is not None
    assert matches_ack([ack], campaign_id=0x351C, sequence=1, ack_type=3)
    assert not matches_ack([ack], campaign_id=0x351D, sequence=1, ack_type=3)
    assert not matches_ack([ack], campaign_id=0x351C, sequence=2, ack_type=3)


def test_ack_alone_never_counts_as_a_tracker_echo() -> None:
    """The ACK-only installed firmware cannot satisfy the full round trip."""
    ack = parse_firmware_event(
        {
            "role": "GATEWAY",
            "timestamp": "host-time",
            "line": "[GATEWAY] ACK_ACCEPTED SID=351C T=286824 TYPE=03 Q=1 E=0",
        }
    )
    assert ack is not None
    context = RoundTripContext(0x351C, 1, b"hello world", 8, 3, 0, 1)
    assert not verify_round_trip([ack], context)


def _chunk_events(campaign: int, sequence: int, payload: bytes) -> list[DeviceEvent]:
    """Build one complete bidirectional event sequence with no host-synthesized RF rows."""
    campaign_hex = f"{campaign:04X}"
    ascii_payload = payload.decode("ascii", errors="replace")
    payload_hex = payload.hex().upper()
    lines = (
        ("GATEWAY", f"[GATEWAY] DATA_TX_BEGIN SID={campaign_hex} TYPE=08 Q={sequence}"),
        ("GATEWAY", f"[GATEWAY] DATA_TX_DONE SID={campaign_hex} TYPE=08 Q={sequence}"),
        ("RECEIVER", f"[RECEIVER] DATA_VALIDATED SID={campaign_hex} TYPE=08 Q={sequence}"),
        (
            "RECEIVER",
            f"[RECEIVER] PAYLOAD_BYTES SID={campaign_hex} TYPE=08 Q={sequence} "
            f"LEN={len(payload)} HEX={payload_hex} ASCII={ascii_payload}",
        ),
        (
            "RECEIVER",
            f"[RECEIVER] DATA_ADDRESS SID={campaign_hex} TYPE=08 Q={sequence} SRC=0 DST=1 CRC=OK",
        ),
        ("RECEIVER", f"[RECEIVER] ACK_TX_DONE SID={campaign_hex} TYPE=03 Q={sequence}"),
        ("GATEWAY", f"[GATEWAY] ACK_ACCEPTED SID={campaign_hex} TYPE=03 Q={sequence}"),
        (
            "GATEWAY",
            f"[GATEWAY] ACK_CONFIRM_TX_DONE SID={campaign_hex} TYPE=03 Q={sequence}",
        ),
        (
            "RECEIVER",
            f"[RECEIVER] ACK_CONFIRM_RX SID={campaign_hex} TYPE=03 Q={sequence}",
        ),
        ("RECEIVER", f"[RECEIVER] DATA_TX_BEGIN SID={campaign_hex} TYPE=08 Q={sequence}"),
        ("RECEIVER", f"[RECEIVER] DATA_TX_DONE SID={campaign_hex} TYPE=08 Q={sequence}"),
        ("GATEWAY", f"[GATEWAY] DATA_VALIDATED SID={campaign_hex} TYPE=08 Q={sequence}"),
        (
            "GATEWAY",
            f"[GATEWAY] PAYLOAD_BYTES SID={campaign_hex} TYPE=08 Q={sequence} "
            f"SRC=1 DST=0 LEN={len(payload)} HEX={payload_hex} ASCII={ascii_payload}",
        ),
        (
            "GATEWAY",
            f"[GATEWAY] DATA_ADDRESS SID={campaign_hex} TYPE=08 Q={sequence} SRC=1 DST=0 CRC=OK",
        ),
        ("GATEWAY", f"[GATEWAY] ACK_TX_DONE SID={campaign_hex} TYPE=03 Q={sequence}"),
        ("RECEIVER", f"[RECEIVER] ACK_ACCEPTED SID={campaign_hex} TYPE=03 Q={sequence}"),
    )
    return [
        event
        for role, line in lines
        if (event := parse_firmware_event({"role": role, "timestamp": "host-time", "line": line}))
        is not None
    ]


def test_round_trip_requires_tracker_data_gateway_ack_and_tracker_acceptance() -> None:
    """Only actual reverse DATA bytes and their correlated ACK prove a round trip."""
    events = _chunk_events(0x351C, 1, b"hello world")
    context = RoundTripContext(0x351C, 1, b"hello world", 8, 3, 0, 1)
    assert verify_round_trip(events, context)


def test_round_trip_reassembles_fragments_across_sequence_rollover() -> None:
    """Fragments preserve ordering and campaign identity across sequence 255."""
    events = _chunk_events(0xFFFF, 255, b"abc") + _chunk_events(1, 1, b"de")
    context = RoundTripContext(0xFFFF, 255, b"abcde", 8, 3, 0, 1)

    assert verify_round_trip(events, context)


def test_verified_echo_bytes_preserve_utf8_split_across_packets() -> None:
    """Return actual captured Echo bytes after verifying both DATA/ACK legs."""
    from tools.lora_chat import protocol

    payload = "สวัสดีครับ, ls".encode()
    events = _chunk_events(0x351C, 1, payload[:5]) + _chunk_events(0x351C, 2, payload[5:])
    context = RoundTripContext(0x351C, 1, payload, 8, 3, 0, 1)

    assert protocol.verified_echo_payload(events, context) == payload
    assert protocol.verified_echo_payload(events[:-1], context) is None


def test_echo_latency_uses_the_gateway_clock_and_first_attempt() -> None:
    """Keep RF latency separate from serial capture and host setup time."""
    from dataclasses import replace

    from tools.lora_chat import protocol

    events = _chunk_events(0x351C, 1, b"abc")
    begin = replace(events[0], firmware_ms=0xFFFFFFFA)
    retry = replace(begin, firmware_ms=7)
    end = next(event for event in events if event.line.startswith("[GATEWAY] ACK_TX_DONE"))
    end = replace(end, firmware_ms=22)
    assert protocol.echo_fragment_latency_ms((begin, retry, end), 8, 3) == (28,)


def test_round_trip_rejects_missing_ack_confirmation_and_out_of_order_fragments() -> None:
    """No chunk advances without the ACK handoff, and wire order must match bytes."""
    single = _chunk_events(0x351C, 1, b"abc")
    single_context = RoundTripContext(0x351C, 1, b"abc", 8, 3, 0, 1)
    without_confirmation = [event for event in single if event.name != "ACK_CONFIRM_RX"]
    assert not verify_round_trip(without_confirmation, single_context)

    first = _chunk_events(0xFFFF, 255, b"abc")
    second = _chunk_events(1, 1, b"de")
    context = RoundTripContext(0xFFFF, 255, b"abcde", 8, 3, 0, 1)
    assert not verify_round_trip(second + first, context)
