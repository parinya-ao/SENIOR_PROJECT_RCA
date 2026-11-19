"""Host-side transaction queue and message completion checks."""

import json
from pathlib import Path

import pytest

from tools.lora_chat.protocol import DeviceEvent, MessageProtocol, parse_firmware_event
from tools.lora_chat.session import (
    ChatSession,
    ChatSettings,
    ExchangeResult,
    QueueFullError,
    RetryUnavailableError,
    load_chat_settings,
)


def _session(
    run_dir: Path,
    *,
    max_pending: int,
    retry_limit: int,
    event_limit: int = 10,
) -> ChatSession:
    """Construct a session with explicit protocol and runtime limits."""
    profile = MessageProtocol(b"hello world", 8, 3, 9, 1, 0, 1)
    settings = ChatSettings(max_pending, event_limit, 100, retry_limit)
    return ChatSession(run_dir, profile, settings)


def _event(role: str, line: str) -> DeviceEvent | None:
    """Build one parsed event fixture from the existing UART format."""
    return parse_firmware_event({"role": role, "timestamp": "host-time", "line": line})


def test_message_queue_keeps_one_active_transaction_and_is_bounded(tmp_path: Path) -> None:
    """Queued requests wait until the current full transaction ends."""
    session = _session(tmp_path, max_pending=1, retry_limit=1)
    current, queued = session.submit("hello world")
    assert not queued
    second, queued = session.submit("hello world")
    assert queued
    with pytest.raises(QueueFullError):
        session.submit("hello world")

    result = ExchangeResult("FAIL", "no ACK", (), 1, 0, 1, 1.0)
    completed, next_message = session.finish_current(result)
    assert completed.message.message_id == current.message_id
    assert next_message == second
    assert session.active == second


def test_ack_without_real_echo_is_not_round_trip_success(tmp_path: Path) -> None:
    """A correlated ACK updates ACK counters but cannot claim a Tracker echo."""
    session = _session(tmp_path, max_pending=2, retry_limit=1)
    request, queued = session.submit("hello world")
    assert not queued
    ack = _event("GATEWAY", "[GATEWAY] ACK_ACCEPTED SID=351C TYPE=03 Q=1 E=0")
    assert ack is not None
    sent = _event("GATEWAY", "[GATEWAY] DATA_TX_DONE SID=351C TYPE=08 Q=1 E=0")
    assert sent is not None
    session.observe_event(ack)
    session.observe_event(sent)

    completed, next_message = session.finish_current(
        ExchangeResult("PASS", "ACK accepted", (sent, ack), 1, 0, 0, 43.0)
    )

    assert next_message is None
    assert completed.message.message_id == request.message_id
    assert completed.status == "ACK_ONLY"
    assert completed.received_text is None
    assert session.stats.ack_count == 1
    assert session.stats.round_trip_successes == 0
    assert session.stats.failed_transactions == 1


def test_ack_matching_deduplicates_replayed_event_counts(tmp_path: Path) -> None:
    """Repeating a captured ACK line cannot inflate the operator's counters."""
    session = _session(tmp_path, max_pending=2, retry_limit=1)
    ack = _event("GATEWAY", "[GATEWAY] ACK_ACCEPTED SID=351C TYPE=03 Q=1 E=0")
    assert ack is not None
    session.observe_event(ack)
    session.observe_event(ack)
    assert session.stats.ack_count == 1


def test_nack_retry_counters_require_the_correlated_gateway_attempts(tmp_path: Path) -> None:
    """A real NACK and bounded retry count without claiming an Echo."""
    session = _session(tmp_path, max_pending=1, retry_limit=1)
    session.submit("hello world")
    events = tuple(
        event
        for event in (
            _event("GATEWAY", "[GATEWAY] DATA_TX_DONE SID=351C TYPE=08 Q=1"),
            _event("GATEWAY", "[GATEWAY] NACK_RX SID=351C TYPE=09 Q=1"),
            _event("GATEWAY", "[GATEWAY] DATA_TX_DONE SID=351C TYPE=08 Q=1"),
            _event("GATEWAY", "[GATEWAY] ACK_ACCEPTED SID=351C TYPE=03 Q=1"),
        )
        if event is not None
    )
    for event in events:
        session.observe_event(event)

    completed, _ = session.finish_current(
        ExchangeResult("PASS", "ACK accepted", events, 2, 1, 0, 80.0)
    )
    assert completed.status == "ACK_ONLY"
    assert session.stats.nack_count == 1
    assert session.stats.retry_count == 1
    assert session.stats.round_trip_successes == 0


def test_timeout_without_ack_is_a_terminal_failed_transaction(tmp_path: Path) -> None:
    """Configured timeout evidence ends the request without fabricating a response."""
    session = _session(tmp_path, max_pending=1, retry_limit=0)
    session.submit("hello world")
    completed, _ = session.finish_current(
        ExchangeResult("TIMEOUT", "ACK timeout", (), 1, 0, 1, 50.0)
    )
    assert completed.status == "TIMEOUT"
    assert completed.ack_accepted is False
    assert session.stats.timeout_count == 1
    assert session.stats.failed_transactions == 1


def test_rf_blocked_message_is_not_logged_as_unsupported(tmp_path: Path) -> None:
    """A valid configured message blocked by RF setup remains a distinct result."""
    session = _session(tmp_path, max_pending=1, retry_limit=0)
    session.reject_input("hello world", "RF inventory is unresolved")
    records = [
        json.loads(line)
        for line in (tmp_path / "messages.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert records[-1]["status"] == "BLOCKED"


def test_retry_keeps_message_identity_and_stops_at_limit(tmp_path: Path) -> None:
    """A retry preserves the original message ID and cannot run indefinitely."""
    session = _session(tmp_path, max_pending=1, retry_limit=1)
    message, _ = session.submit("hello world")
    session.finish_current(ExchangeResult("TIMEOUT", "ACK timeout", (), 1, 0, 1, 20.0))
    retry = session.retry_last()
    assert retry.message_id == message.message_id
    session.finish_current(ExchangeResult("TIMEOUT", "ACK timeout", (), 1, 0, 1, 20.0))
    with pytest.raises(RetryUnavailableError, match="limit"):
        session.retry_last()


def test_chat_settings_reject_unknown_keys_and_invalid_limits(tmp_path: Path) -> None:
    """Runtime queue and refresh limits are validated from their dedicated file."""
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "max_pending_messages": 2,
                "event_history_limit": 10,
                "refresh_interval_ms": 100,
                "manual_retry_limit": 1,
                "unexpected": 3,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown"):
        load_chat_settings(path)


def test_chat_settings_allow_zero_manual_retries(tmp_path: Path) -> None:
    """The operator can explicitly disable host-level retries in file config."""
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "max_pending_messages": 1,
                "event_history_limit": 1,
                "refresh_interval_ms": 100,
                "manual_retry_limit": 0,
            }
        ),
        encoding="utf-8",
    )
    assert load_chat_settings(path).manual_retry_limit == 0


def test_chat_settings_enforce_memory_and_refresh_caps(tmp_path: Path) -> None:
    """A valid JSON integer cannot expand the queue or event history without bound."""
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "max_pending_messages": 65,
                "event_history_limit": 10,
                "refresh_interval_ms": 100,
                "manual_retry_limit": 1,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"1\.\.64"):
        load_chat_settings(path)
