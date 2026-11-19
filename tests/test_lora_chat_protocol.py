"""Host-side checks for the installed firmware's supported message contract."""

import pytest

from tools.lora_chat.protocol import (
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


def test_round_trip_requires_tracker_data_gateway_ack_and_tracker_acceptance() -> None:
    """Only actual reverse DATA bytes and their correlated ACK prove a round trip."""
    lines = (
        ("GATEWAY", "[GATEWAY] ACK_ACCEPTED SID=351C TYPE=03 Q=1"),
        (
            "GATEWAY",
            (
                "[GATEWAY] PAYLOAD_BYTES SID=351D TYPE=08 Q=1 SRC=1 DST=0 "
                "LEN=11 HEX=68656C6C6F20776F726C64 ASCII=hello world"
            ),
        ),
        ("GATEWAY", "[GATEWAY] ACK_TX_DONE SID=351D TYPE=03 Q=1"),
        ("RECEIVER", "[RECEIVER] ACK_ACCEPTED SID=351D TYPE=03 Q=1"),
    )
    events = [
        event
        for role, line in lines
        if (event := parse_firmware_event({"role": role, "timestamp": "host-time", "line": line}))
        is not None
    ]
    context = RoundTripContext(0x351C, 1, b"hello world", 8, 3, 0, 1)
    assert verify_round_trip(events, context)
