"""Parse firmware events and assess captured protocol behavior without a radio fake."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

EVENT_PATTERN = re.compile(r"^\[(GATEWAY|TRACKER|RECEIVER)\]\s+([A-Z][A-Z0-9_]*)\s*(.*)$")
FIELD_PATTERN = re.compile(r"([A-Z][A-Z0-9_]*)=([^\s]+)")
ROLE_NAMES = {"GATEWAY": "gateway", "TRACKER": "tracker", "RECEIVER": "tracker"}
DATA_PACKET_TYPE = 8
ACK_PACKET_TYPE = 3
NACK_PACKET_TYPE = 9
SEQUENCE_MASK = 0xFF
UINT32_MASK = 0xFFFFFFFF
UINT32_HALF_RANGE = 0x80000000
SEQUENCE_ROLLOVER_WINDOW = (SEQUENCE_MASK, 0)
SINGLE_EVENT = 1
DUPLICATE_TRANSMISSIONS = 2


@dataclass(frozen=True, slots=True)
class FirmwareEvent:
    """A parsed firmware event retaining the device role and raw source line."""

    role: str
    name: str
    fields: dict[str, str]
    raw: str

    def number(self, key: str) -> int | None:
        """Return a decimal event field, or a hexadecimal session identifier."""
        value = self.fields.get(key)
        if value is None:
            return None
        try:
            return int(value, 16 if key == "SID" else 10)
        except ValueError:
            return None


def parse_event_row(row: dict[str, Any]) -> FirmwareEvent | None:
    """Parse a captured UART line and reject role labels that disagree with the line."""
    if row["stream"] != "stdout":
        return None
    match = EVENT_PATTERN.match(row["line"])
    if match is None:
        return None
    line_role, name, text = match.groups()
    role = ROLE_NAMES[line_role]
    captured_role = "tracker" if row["role"] in {"tracker", "receiver"} else row["role"]
    if role != captured_role:
        msg = "captured role does not match firmware event role"
        raise ValueError(msg)
    fields: dict[str, str] = {}
    for key, value in FIELD_PATTERN.findall(text):
        if key in fields:
            msg = f"duplicate firmware event field {key}"
            raise ValueError(msg)
        fields[key] = value
    return FirmwareEvent(role, name, fields, row["line"])


def _result(case: dict[str, Any], status: str, reason: str, **values: object) -> dict[str, Any]:
    """Build one stable, JSON-ready transaction assessment."""
    result: dict[str, Any] = {
        "case_id": case["case_id"],
        "fault": case["fault"],
        "direction": case["direction"],
        "status": status,
        "reason": reason,
        "retry_count": 0,
        "timeout_count": 0,
        "payload_mismatches": 0,
        "duplicate_deliveries": 0,
        "false_ack_acceptance": 0,
        "latency_ms": None,
        "rssi_dbm": None,
        "snr_db": None,
        "airtime_us": None,
        "radio_errors": None,
        "irq_flags_seen": None,
    }
    result.update(values)
    return result


# Guard paths represent the separate payload, sequence, and ACK invariants for 255 -> 0.
def _assess_sequence_rollover(  # noqa: C901, PLR0911
    case: dict[str, Any], events: list[FirmwareEvent], source: str, receiver: str
) -> dict[str, Any]:
    """Verify a single-session transition from sequence 255 to sequence zero."""
    session_id = int(case["session_id"])
    sequences = case["expected_sequences"]
    payloads = [bytes.fromhex(value) for value in case["payloads_hex"]]
    session_events = [event for event in events if event.number("SID") == session_id]
    data_tx = [
        event
        for event in session_events
        if event.role == source
        and event.name == "DATA_TX_DONE"
        and event.number("TYPE") == DATA_PACKET_TYPE
    ]
    ordered_sequences = list(dict.fromkeys(event.number("Q") for event in data_tx))
    if ordered_sequences != sequences:
        return _result(case, "UNVERIFIED", "missing ordered sequence 255-to-zero DATA evidence")
    if len(data_tx) > len(sequences) * (int(case["maximum_retries"]) + 1):
        return _result(case, "FAIL", "sequence rollover exceeded the configured retry limit")
    for sequence, expected_payload in zip(sequences, payloads, strict=True):
        received = [
            event
            for event in session_events
            if event.role == receiver
            and event.name == "DATA_VALIDATED"
            and event.number("TYPE") == DATA_PACKET_TYPE
            and event.number("Q") == sequence
        ]
        if len(received) != 1 or received[0].fields.get("PAYLOAD_HEX") is None:
            return _result(
                case, "UNVERIFIED", f"missing exact receiver bytes for sequence {sequence}"
            )
        try:
            actual_payload = bytes.fromhex(received[0].fields["PAYLOAD_HEX"])
        except ValueError:
            return _result(case, "FAIL", "malformed rollover payload hex", payload_mismatches=1)
        if actual_payload != expected_payload:
            return _result(
                case,
                "FAIL",
                f"payload mismatch at rollover sequence {sequence}",
                payload_mismatches=1,
            )
        ack_tx = any(
            event.role == receiver
            and event.name == "ACK_TX_DONE"
            and event.number("TYPE") == ACK_PACKET_TYPE
            and event.number("Q") == sequence
            for event in session_events
        )
        ack_rx = any(
            event.role == source
            and event.name == "ACK_ACCEPTED"
            and event.number("TYPE") == ACK_PACKET_TYPE
            and event.number("Q") == sequence
            for event in session_events
        )
        if not ack_tx or not ack_rx:
            return _result(
                case, "UNVERIFIED", f"missing matching ACK at rollover sequence {sequence}"
            )
    wrong_ack = any(
        event.role == source and event.name == "ACK_ACCEPTED" and event.number("Q") not in sequences
        for event in session_events
    )
    if wrong_ack:
        return _result(
            case,
            "FAIL",
            "Gateway accepted an ACK outside the rollover sequence pair",
            false_ack_acceptance=1,
        )
    required_events = [
        event
        for event in session_events
        if event.name in {"DATA_TX_DONE", "DATA_VALIDATED", "ACK_TX_DONE", "ACK_ACCEPTED"}
        and event.number("Q") in sequences
    ]
    if any(event.number("E") is None for event in required_events):
        return _result(case, "UNVERIFIED", "rollover packet events lack RadioLib status codes")
    radio_errors = [
        int(event.number("E") or 0) for event in required_events if event.number("E") != 0
    ]
    if radio_errors:
        return _result(
            case, "FAIL", "rollover packet has a nonzero RadioLib status", radio_errors=radio_errors
        )
    irq_flags = [
        flag for event in required_events if (flag := event.number("IRQ_FLAGS")) is not None
    ]
    return _result(
        case,
        "PASS",
        "exact payloads and ACKs verified across sequence rollover",
        retry_count=len(data_tx) - 2,
        irq_flags_seen=sorted(set(irq_flags)) if irq_flags else None,
    )


def _assess_cancellation(  # noqa: PLR0911
    case: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Require a cancellation request, both parked events, released ports and no later TX."""
    cancel_indices = [
        index
        for index, row in enumerate(rows)
        if row["stream"] == "control" and row["line"].startswith("CANCEL_REQUESTED")
    ]
    if not cancel_indices:
        return _result(case, "UNVERIFIED", "missing host cancellation request evidence")
    cancel_index = cancel_indices[0]
    cancel_clock = rows[cancel_index].get("received_monotonic_ns")
    events_after_cancel = [parse_event_row(row) for row in rows[cancel_index + 1 :]]
    parked_roles = {
        event.role
        for event in events_after_cancel
        if event is not None and event.name in {"PARKED", "PARKED_E0"}
    }
    if parked_roles != {"gateway", "tracker"}:
        return _result(case, "UNVERIFIED", "both radios must report parked after cancellation")
    released_roles = {
        row["role"]
        for row in rows[cancel_index + 1 :]
        if row["stream"] == "port_release" and row["line"] == "PORT_RELEASED"
    }
    if released_roles != {"gateway", "receiver"}:
        return _result(
            case, "UNVERIFIED", "both UPDI ports must report released after cancellation"
        )
    for row in rows[cancel_index + 1 :]:
        event = parse_event_row(row)
        if event is None or event.name != "DATA_TX_DONE":
            continue
        if row.get("delivery") == "after_rf_reopen" or type(cancel_clock) is not int:
            return _result(
                case, "UNVERIFIED", "buffered DATA evidence cannot be ordered against cancellation"
            )
        event_clock = row.get("received_monotonic_ns")
        if type(event_clock) is not int:
            return _result(case, "UNVERIFIED", "DATA event has no host monotonic timestamp")
        if event_clock >= cancel_clock:
            return _result(case, "FAIL", "a new DATA transmission was logged after cancellation")
    return _result(case, "PASS", "cancellation parked both radios and released both ports")


# The fault matrix has distinct evidence exits that are exercised by focused replay specs.
def assess_case(  # noqa: C901, PLR0911, PLR0912, PLR0915
    case: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Require two-sided, session/sequence-matched byte evidence for an RF PASS."""
    events = [event for row in rows if (event := parse_event_row(row)) is not None]
    if case["fault"] == "CANCEL_UNDER_LOAD":
        return _assess_cancellation(case, rows)
    source, receiver = (
        ("gateway", "tracker")
        if case["direction"] == "gateway_to_tracker"
        else ("tracker", "gateway")
    )
    if case["fault"] == "SEQUENCE_ROLLOVER":
        return _assess_sequence_rollover(case, events, source, receiver)
    session_id = int(case["session_id"])
    sequence = int(case["sequence"])
    matching_session = [event for event in events if event.number("SID") == session_id]
    tx_events = [
        event
        for event in matching_session
        if event.role == source
        and event.name == "DATA_TX_DONE"
        and event.number("TYPE") == DATA_PACKET_TYPE
    ]
    if not tx_events:
        return _result(case, "UNVERIFIED", "missing sender DATA_TX_DONE for the expected session")
    if any(event.number("Q") != sequence for event in tx_events):
        return _result(case, "FAIL", "DATA retry changed or violated the expected sequence")
    retry_count = len(tx_events) - 1
    maximum_retries = int(case.get("maximum_retries", 0))
    if retry_count > maximum_retries:
        return _result(
            case,
            "FAIL",
            "observed retries exceed the configured retry limit",
            retry_count=retry_count,
        )

    fault = str(case["fault"])
    reset_count: int | None = None
    receiver_data = [
        event
        for event in matching_session
        if event.role == receiver and event.name == "DATA_VALIDATED"
    ]
    timeouts = [
        event for event in matching_session if event.role == source and event.name == "TIMEOUT"
    ]
    if fault == "RECEIVER_RESET":
        reset_events = [
            event
            for event in matching_session
            if event.role == receiver and event.name in {"RESET", "APP_RESET", "BOOT"}
        ]
        if len(reset_events) != SINGLE_EVENT:
            status = "FAIL" if len(reset_events) > SINGLE_EVENT else "UNVERIFIED"
            return _result(
                case, status, "receiver reset count does not match the single injected reset"
            )
        reset_count = len(reset_events)
        reset_tick = reset_events[0].number("T")
        receiver_ready = [
            event
            for event in matching_session
            if event.role == receiver and event.name == "RX_READY" and event.number("T") is not None
        ]
        if reset_tick is None or not any(
            0 < (((event.number("T") or 0) - reset_tick) & UINT32_MASK) < UINT32_HALF_RANGE
            for event in receiver_ready
        ):
            return _result(case, "UNVERIFIED", "receiver did not confirm RX readiness after reset")
    if fault == "PHY_CRC_CORRUPT":
        crc_errors = [
            event
            for event in matching_session
            if event.role == receiver and event.name in {"CRC_ERROR", "PAYLOAD_CRC_ERROR"}
        ]
        responses = [
            event
            for event in matching_session
            if event.role == receiver and event.name.endswith("_TX_DONE")
        ]
        if receiver_data or responses:
            return _result(
                case, "FAIL", "CRC-rejected DATA reached application validation or response"
            )
        if not crc_errors or not timeouts:
            return _result(
                case, "UNVERIFIED", "missing PHY CRC rejection and bounded sender timeout"
            )
        return _result(
            case,
            "PASS",
            "PHY CRC rejection recovered through bounded timeout",
            timeout_count=len(timeouts),
            radio_errors=[
                event.number("E") for event in crc_errors if event.number("E") is not None
            ]
            or None,
            irq_flags_seen=[
                event.number("IRQ_FLAGS")
                for event in crc_errors
                if event.number("IRQ_FLAGS") is not None
            ]
            or None,
        )
    if fault == "WRONG_DESTINATION":
        replies = [
            event
            for event in matching_session
            if event.role == receiver and event.name.endswith("_TX_DONE")
        ]
        if receiver_data or replies:
            return _result(case, "FAIL", "wrong-destination DATA was accepted or answered")
        if not timeouts:
            return _result(case, "UNVERIFIED", "missing bounded no-response timeout evidence")
        if any(event.number("E") is None for event in tx_events + timeouts):
            return _result(
                case, "UNVERIFIED", "sender DATA or timeout lacks a RadioLib status code"
            )
        radio_errors = [
            int(event.number("E") or 0) for event in tx_events + timeouts if event.number("E") != 0
        ]
        if radio_errors:
            return _result(
                case,
                "FAIL",
                "wrong-destination TX had a nonzero RadioLib status",
                radio_errors=radio_errors,
            )
        return _result(
            case,
            "PASS",
            "wrong destination was ignored until the bounded timeout",
            timeout_count=len(timeouts),
        )

    invalid_application_data = fault == "INVALID_APP_PAYLOAD"
    payload_events = receiver_data
    if invalid_application_data:
        payload_events = [
            event
            for event in matching_session
            if event.role == receiver and event.name == "DATA_REJECTED"
        ]
    matching_data = [event for event in payload_events if event.number("Q") == sequence]
    if not matching_data:
        missing_event = "DATA_REJECTED" if invalid_application_data else "DATA_VALIDATED"
        return _result(case, "UNVERIFIED", f"missing receiver {missing_event} event")
    payload_values = [event.fields.get("PAYLOAD_HEX") for event in matching_data]
    if any(value is None for value in payload_values):
        return _result(case, "UNVERIFIED", "receiver did not log the exact payload bytes")
    try:
        observed_payloads = [bytes.fromhex(value or "") for value in payload_values]
        expected_payload = bytes.fromhex(case["payload_hex"])
    except ValueError:
        return _result(case, "FAIL", "malformed hexadecimal payload evidence", payload_mismatches=1)
    if any(payload != expected_payload for payload in observed_payloads):
        return _result(
            case,
            "FAIL",
            "receiver payload bytes differ from the generated bytes",
            payload_mismatches=1,
        )

    response_type = NACK_PACKET_TYPE if invalid_application_data else ACK_PACKET_TYPE
    response_name = "NACK" if response_type == NACK_PACKET_TYPE else "ACK"
    response_tx = [
        event
        for event in matching_session
        if event.role == receiver
        and event.name == f"{response_name}_TX_DONE"
        and event.number("TYPE") == response_type
        and event.number("Q") == sequence
    ]
    response_rx = [
        event
        for event in matching_session
        if event.role == source
        and event.name in {"ACK_ACCEPTED", "NACK_RX"}
        and event.number("TYPE") == response_type
        and event.number("Q") == sequence
    ]

    nack_tx: list[FirmwareEvent] = []
    nack_rx: list[FirmwareEvent] = []
    if fault.startswith("FORCE_NACK"):
        expected_nacks = 2 if fault == "FORCE_NACK_TWICE" else 1
        nack_tx = [
            event
            for event in matching_session
            if event.role == receiver and event.name == "NACK_TX_DONE"
        ]
        nack_rx = [
            event for event in matching_session if event.role == source and event.name == "NACK_RX"
        ]
        if len(nack_tx) != expected_nacks or len(nack_rx) != expected_nacks:
            return _result(
                case, "UNVERIFIED", "missing matching NACK TX/RX evidence", retry_count=retry_count
            )
        if any(
            event.number("Q") != sequence or event.number("TYPE") != NACK_PACKET_TYPE
            for event in nack_tx + nack_rx
        ):
            return _result(
                case,
                "FAIL",
                "NACK session, sequence or packet type mismatch",
                retry_count=retry_count,
            )
        if len(tx_events) < expected_nacks + 1:
            return _result(
                case,
                "FAIL",
                "NACK was not followed by a same-sequence retry",
                retry_count=retry_count,
            )

    if fault == "DUPLICATE_DATA":
        duplicate = [
            event
            for event in matching_session
            if event.role == receiver and event.name == "DUPLICATE_IGNORED"
        ]
        delivery_counts = [event.number("DELIVERY_COUNT") for event in duplicate]
        if (
            len(tx_events) < DUPLICATE_TRANSMISSIONS
            or len(matching_data) != SINGLE_EVENT
            or delivery_counts != [1]
            or len(response_tx) < DUPLICATE_TRANSMISSIONS
            or len(response_rx) < DUPLICATE_TRANSMISSIONS
        ):
            return _result(
                case,
                "UNVERIFIED",
                "duplicate suppression lacks one-delivery counter evidence",
                retry_count=retry_count,
            )

    if fault == "SUPPRESS_ACK_ONCE":
        suppressed = any(
            event.role == receiver and event.name == "ACK_SUPPRESSED" for event in matching_session
        )
        duplicate = [
            event
            for event in matching_session
            if event.role == receiver and event.name == "DUPLICATE_IGNORED"
        ]
        if not suppressed or not timeouts or len(tx_events) < DUPLICATE_TRANSMISSIONS:
            return _result(case, "UNVERIFIED", "missing suppressed-ACK timeout and retry evidence")
        if len(duplicate) != SINGLE_EVENT or duplicate[0].number("DELIVERY_COUNT") != SINGLE_EVENT:
            return _result(case, "FAIL", "suppressed ACK caused duplicate application delivery")

    if fault == "DELAYED_RESPONSE" and (not timeouts or len(tx_events) < DUPLICATE_TRANSMISSIONS):
        return _result(case, "UNVERIFIED", "delayed response case did not show timeout recovery")

    accepted_wrong_ack = [
        event
        for event in matching_session
        if event.role == source
        and event.name == "ACK_ACCEPTED"
        and event.number("TYPE") == ACK_PACKET_TYPE
        and event.number("Q") != sequence
    ]
    if accepted_wrong_ack:
        return _result(
            case,
            "FAIL",
            "Gateway accepted an ACK with the wrong sequence",
            retry_count=retry_count,
            false_ack_acceptance=1,
        )

    if fault == "WRONG_SEQUENCE":
        rejected_wrong_sequence = any(
            event.role == source
            and event.name == "ACK_REJECTED"
            and event.number("GOT_Q") not in {None, sequence}
            for event in matching_session
        )
        if not rejected_wrong_sequence:
            return _result(case, "UNVERIFIED", "missing explicit rejection of the wrong sequence")

    if fault in {"WRONG_CAMPAIGN", "STALE_ACK"}:
        rejected_wrong_session = any(
            event.role == source
            and event.name == "ACK_REJECTED"
            and event.number("GOT_SID") not in {None, session_id}
            for event in matching_session
        )
        if not rejected_wrong_session:
            return _result(case, "UNVERIFIED", "missing explicit rejection of the stale campaign")

    evidence_events = tx_events + matching_data + response_tx + response_rx
    if fault.startswith("FORCE_NACK"):
        evidence_events.extend(nack_tx + nack_rx)
    if fault == "DUPLICATE_DATA":
        evidence_events.extend(
            event
            for event in matching_session
            if event.role == receiver and event.name == "DUPLICATE_IGNORED"
        )
    if any(event.number("E") is None for event in evidence_events):
        return _result(case, "UNVERIFIED", "one or more packet events lack a RadioLib status code")
    radio_errors = [
        int(event.number("E") or 0) for event in evidence_events if event.number("E") != 0
    ]
    if radio_errors:
        return _result(
            case,
            "FAIL",
            "nonzero RadioLib status code on a required packet event",
            radio_errors=radio_errors,
        )

    if not response_tx or not response_rx:
        return _result(
            case,
            "UNVERIFIED",
            f"missing matching {response_name} TX/RX evidence",
            retry_count=retry_count,
        )
    sender_ticks = [tick for event in tx_events if (tick := event.number("T")) is not None]
    response_ticks = [tick for event in response_rx if (tick := event.number("T")) is not None]
    latency = None
    if sender_ticks and response_ticks:
        latency = (response_ticks[-1] - sender_ticks[0]) & UINT32_MASK
    rssi_values = [
        float(event.fields["RSSI_DBM"])
        for event in matching_data
        if event.fields.get("RSSI_DBM") is not None
    ]
    snr_values = [
        float(event.fields["SNR_DB"])
        for event in matching_data
        if event.fields.get("SNR_DB") is not None
    ]
    airtime_values = [
        int(event.fields["AIRTIME_US"])
        for event in matching_session
        if event.name.endswith("TX_DONE") and event.fields.get("AIRTIME_US", "").isdigit()
    ]
    irq_flags = [
        flag for event in matching_session if (flag := event.number("IRQ_FLAGS")) is not None
    ]
    return _result(
        case,
        "PASS",
        f"exact payload and matching {response_name} evidence",
        retry_count=retry_count,
        timeout_count=sum(
            event.name == "TIMEOUT" and event.role == source for event in matching_session
        ),
        latency_ms=latency,
        rssi_dbm=rssi_values[0] if rssi_values else None,
        snr_db=snr_values[0] if snr_values else None,
        airtime_us=sum(airtime_values) if airtime_values else None,
        radio_errors=radio_errors or None,
        irq_flags_seen=sorted(set(irq_flags)) if irq_flags else None,
        reset_count=reset_count,
    )
