"""Bounded host-side message queue and evidence-backed session journal."""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Hashable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from tools.lora_chat.errors import make_error
from tools.lora_chat.protocol import (
    MAX_APPLICATION_PAYLOAD_BYTES,
    MAX_HOST_MESSAGE_BYTES,
    TIMEOUT_EVENTS,
    DeviceEvent,
    DeviceRole,
    EventName,
    MessageProtocol,
    RoundTripContext,
    echo_fragment_latency_ms,
    encode_interactive_message,
    matches_ack,
    verify_round_trip,
)

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "config" / "lora_chat.json"
SETTING_RANGES = {
    "max_pending_messages": (1, 64),
    "max_message_bytes": (1, MAX_HOST_MESSAGE_BYTES),
    "event_history_limit": (1, 1000),
    "refresh_interval_ms": (25, 2000),
    "manual_retry_limit": (0, 3),
}


@dataclass(frozen=True, slots=True)
class ChatSettings:
    """Console limits and optional receipt for the confirmed RF bench."""

    max_pending_messages: int
    max_message_bytes: int
    event_history_limit: int
    refresh_interval_ms: int
    manual_retry_limit: int
    confirmed_bench_receipt: Path | None = None


@dataclass(frozen=True, slots=True)
class MessageRequest:
    """One user message and its stable identity across bounded retries."""

    message_id: str
    text: str
    payload: bytes
    created_at: str


class ExchangeStatus(StrEnum):
    """Terminal results returned by the existing RF transaction runner."""

    SUCCESS = "PASS"
    TIMEOUT = "TIMEOUT"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class ExchangeResult:
    """The real bench outcome and the parsed firmware evidence for one attempt."""

    status: str
    detail: str
    events: tuple[DeviceEvent, ...]
    attempts: int
    retries: int
    timeouts: int
    host_elapsed_ms: float
    legacy_data_ack: bool = False


@dataclass(frozen=True, slots=True)
class CompletedMessage:
    """A terminal message result derived from real, correlated device events."""

    message: MessageRequest
    status: str
    campaign_id: int | None
    sequence: int | None
    received_text: str | None
    ack_accepted: bool
    detail: str
    attempts: int
    retries: int
    timeouts: int
    host_elapsed_ms: float
    firmware_timestamps_ms: tuple[int, ...]
    transaction_nacks: int
    fragment_count: int
    echo_fragment_latency_ms: tuple[int, ...]


@dataclass(slots=True)
class ChatStats:
    """Counts only observed firmware traffic and completed host requests."""

    messages_sent: int = 0
    messages_received: int = 0
    ack_count: int = 0
    nack_count: int = 0
    retry_count: int = 0
    timeout_count: int = 0
    round_trip_successes: int = 0
    legacy_data_ack_successes: int = 0
    failed_transactions: int = 0
    blocked_transactions: int = 0


class QueueFullError(RuntimeError):
    """Raised when the configured pending-message limit has been reached."""

    def __init__(self) -> None:
        """Give the full-queue condition one stable operator-facing message."""
        super().__init__("pending message queue is full")


class RetryUnavailableError(RuntimeError):
    """Raised when a safe retry cannot preserve the original transaction."""


class InputDisposition(StrEnum):
    """Distinguish unsupported payloads from valid requests blocked by setup."""

    BLOCKED = "BLOCKED"
    UNSUPPORTED = "UNSUPPORTED"


class SessionConfigError(ValueError):
    """Raised when console limits or protocol settings are invalid."""


class SessionConfigTypeError(TypeError):
    """Raised when a console setting has the wrong JSON value type."""


class SessionStateError(RuntimeError):
    """Raised when an internal message-state transition lacks an active transaction."""


def load_chat_settings(path: Path = SETTINGS_PATH) -> ChatSettings:
    """Load and validate the console limits and optional repository-relative receipt."""
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise make_error(
            SessionConfigError, f"Cannot read LoRa console settings from {path}: {error}"
        ) from error
    if not isinstance(values, dict):
        raise make_error(SessionConfigTypeError, "LoRa console settings must be a JSON object")

    unknown = sorted(values.keys() - SETTING_RANGES.keys() - {"confirmed_bench_receipt"})
    missing = sorted(SETTING_RANGES.keys() - values.keys())
    if unknown or missing:
        raise make_error(
            SessionConfigError,
            f"Invalid LoRa console settings; missing={missing}, unknown={unknown}",
        )
    for name, (minimum, maximum) in SETTING_RANGES.items():
        value = values[name]
        if type(value) is not int:
            raise make_error(
                SessionConfigTypeError, f"LoRa console setting {name} must be an integer"
            )
        if not minimum <= value <= maximum:
            raise make_error(
                SessionConfigError,
                f"LoRa console setting {name} must be in {minimum}..{maximum}",
            )
    receipt = values.get("confirmed_bench_receipt")
    if receipt is not None and (
        not isinstance(receipt, str)
        or not receipt.strip()
        or "\x00" in receipt
        or Path(receipt).is_absolute()
        or ".." in Path(receipt).parts
    ):
        raise make_error(
            SessionConfigError, "confirmed_bench_receipt must be a repository-relative path or null"
        )
    return ChatSettings(
        max_pending_messages=values["max_pending_messages"],
        max_message_bytes=values["max_message_bytes"],
        event_history_limit=values["event_history_limit"],
        refresh_interval_ms=values["refresh_interval_ms"],
        manual_retry_limit=values["manual_retry_limit"],
        confirmed_bench_receipt=Path(receipt) if receipt is not None else None,
    )


class ChatSession:
    """Serialize user messages, correlate evidence, and persist bounded history."""

    def __init__(
        self,
        run_dir: Path,
        profile: MessageProtocol,
        settings: ChatSettings,
    ) -> None:
        """Create an empty session whose limits are supplied by validated config."""
        if (
            settings.max_pending_messages < 1
            or settings.max_message_bytes < 1
            or settings.manual_retry_limit < 0
            or settings.event_history_limit < 1
        ):
            raise make_error(
                SessionConfigError, "queue, retry, and event-history limits are invalid"
            )
        if len(profile.payload) > MAX_APPLICATION_PAYLOAD_BYTES:
            raise make_error(
                SessionConfigError, "configured application payload exceeds Transport::kMaxData"
            )
        self.run_dir = run_dir
        self.profile = profile
        self.settings = settings
        self.active: MessageRequest | None = None
        self.pending: deque[MessageRequest] = deque()
        self.last_retryable: MessageRequest | None = None
        self.manual_retries = 0
        self.state = "IDLE"
        self.mode = "REAL RF"
        self.connected = False
        self.echo_supported: bool | None = None
        self.stats = ChatStats()
        self.started_at = _utc_now()
        self.visible_events: deque[DeviceEvent] = deque(maxlen=settings.event_history_limit)
        self._seen_event_lines: set[tuple[str, str, str]] = set()
        self._seen_event_order: deque[tuple[str, str, str]] = deque(
            maxlen=settings.event_history_limit
        )
        self._retry_message_id: str | None = None
        self._active_transmitted = False
        self.messages_path = run_dir / "messages.jsonl"
        self.session_path = run_dir / "session.json"
        self.messages_path.touch(exist_ok=True)
        self.persist_session()

    @property
    def queued_count(self) -> int:
        """Return the number of messages waiting behind the active transaction."""
        return len(self.pending)

    def submit(self, text: str) -> tuple[MessageRequest, bool]:
        """Validate a message and make it active or place it in the bounded queue."""
        payload = encode_interactive_message(text, self.settings.max_message_bytes)
        message = MessageRequest(uuid4().hex, text, payload, _utc_now())
        queued = self.active is not None
        if queued:
            if len(self.pending) >= self.settings.max_pending_messages:
                raise QueueFullError
            self.pending.append(message)
        else:
            self.active = message
            self._active_transmitted = False
            self.state = "PREPARE"
        self._append_message(
            {
                "message_id": message.message_id,
                "original_text": message.text,
                "received_text": None,
                "direction": "gateway_to_tracker",
                "status": "QUEUED" if queued else "PREPARE",
                "host_timestamp": message.created_at,
            }
        )
        self.persist_session()
        return message, queued

    def observe_event(self, event: DeviceEvent) -> bool:
        """Remember one real event and update counters without counting replays twice."""
        signature = (event.role.value, event.host_timestamp, event.line)
        if signature in self._seen_event_lines:
            return False
        if len(self._seen_event_order) == self._seen_event_order.maxlen:
            old = self._seen_event_order.popleft()
            self._seen_event_lines.discard(old)
        self._seen_event_order.append(signature)
        self._seen_event_lines.add(signature)
        self.visible_events.append(event)

        if event.name == EventName.ACK_ACCEPTED:
            self.stats.ack_count += 1
        if event.name == EventName.NACK_RX:
            self.stats.nack_count += 1
        if event.name in TIMEOUT_EVENTS:
            self.stats.timeout_count += 1
        if (
            event.name == EventName.DATA_TX_DONE
            and event.role is DeviceRole.GATEWAY
            and self.active is not None
            and not self._active_transmitted
        ):
            self.stats.messages_sent += 1
            self._active_transmitted = True
        self.persist_session()
        return True

    def finish_current(
        self, result: ExchangeResult
    ) -> tuple[CompletedMessage, MessageRequest | None]:
        """Finish one exchange, require real echo evidence, then promote one queued item."""
        message = self.active
        if message is None:
            raise make_error(SessionStateError, "no active message transaction")

        for event in result.events:
            self.observe_event(event)

        transmits = [
            event
            for event in result.events
            if event.role is DeviceRole.GATEWAY
            and event.name in {EventName.DATA_TX_BEGIN, EventName.DATA_TX_DONE}
            and event.packet_type == self.profile.data_type
        ]
        transmit = transmits[0] if transmits else None
        campaign_id = transmit.campaign_id if transmit else None
        sequence = transmit.sequence if transmit else None
        transaction_keys = {
            (event.campaign_id, event.sequence)
            for event in transmits
            if event.campaign_id is not None and event.sequence is not None
        }
        ack_accepted = bool(transaction_keys) and all(
            matches_ack(
                list(result.events),
                campaign_id=campaign,
                sequence=transaction_sequence,
                ack_type=self.profile.ack_type,
            )
            for campaign, transaction_sequence in transaction_keys
        )
        round_trip = bool(
            result.status == ExchangeStatus.SUCCESS
            and campaign_id is not None
            and sequence is not None
            and verify_round_trip(
                list(result.events),
                RoundTripContext(
                    campaign_id=campaign_id,
                    sequence=sequence,
                    original_payload=message.payload,
                    data_type=self.profile.data_type,
                    ack_type=self.profile.ack_type,
                    gateway_address=self.profile.gateway_address,
                    tracker_address=self.profile.tracker_address,
                    sequence_bits=self.profile.sequence_bits,
                ),
            )
        )
        received_text = message.text if round_trip else None
        if round_trip:
            status = "SUCCESS"
            self.stats.round_trip_successes += 1
            self.stats.messages_received += 1
        elif result.status == ExchangeStatus.UNSUPPORTED:
            status = ExchangeStatus.UNSUPPORTED
            self.stats.blocked_transactions += 1
        elif result.legacy_data_ack and result.status == ExchangeStatus.SUCCESS and ack_accepted:
            status = "DATA_ACK_VERIFIED"
            self.stats.legacy_data_ack_successes += 1
        elif result.status == ExchangeStatus.SUCCESS and ack_accepted:
            status = "ACK_ONLY"
            self.stats.failed_transactions += 1
        else:
            status = "TIMEOUT" if result.status == ExchangeStatus.TIMEOUT else "FAILED"
            self.stats.failed_transactions += 1

        transmitted = transmit is not None
        total_retries = max(0, result.retries) + (self.manual_retries if transmitted else 0)
        self.stats.retry_count += total_retries
        if result.timeouts and not any(event.name in TIMEOUT_EVENTS for event in result.events):
            self.stats.timeout_count += result.timeouts
        completed = CompletedMessage(
            message=message,
            status=status,
            campaign_id=campaign_id,
            sequence=sequence,
            received_text=received_text,
            ack_accepted=ack_accepted,
            detail=(
                "ACK accepted; installed Tracker firmware has no application DATA echo."
                if status == "ACK_ONLY"
                else result.detail
            ),
            attempts=result.attempts,
            retries=total_retries,
            timeouts=result.timeouts,
            host_elapsed_ms=result.host_elapsed_ms,
            firmware_timestamps_ms=tuple(
                event.firmware_ms for event in result.events if event.firmware_ms is not None
            ),
            transaction_nacks=sum(
                event.role is DeviceRole.GATEWAY and event.name == EventName.NACK_RX
                for event in result.events
            ),
            fragment_count=len(transaction_keys),
            echo_fragment_latency_ms=(
                echo_fragment_latency_ms(
                    result.events, self.profile.data_type, self.profile.ack_type
                )
                if round_trip
                else ()
            ),
        )
        self._append_message(self._message_record(completed))
        self.last_retryable = message if status in {"FAILED", "TIMEOUT", "ACK_ONLY"} else None
        if self._retry_message_id != message.message_id:
            self.manual_retries = 0
        self._retry_message_id = message.message_id
        self.active = self.pending.popleft() if self.pending else None
        self._active_transmitted = False
        self.state = "PREPARE" if self.active else status
        self.persist_session()
        return completed, self.active

    def retry_last(self) -> MessageRequest:
        """Retry one failed message with its original message identity, within a fixed bound."""
        if self.active is not None:
            raise make_error(RetryUnavailableError, "a message transaction is already active")
        message = self.last_retryable
        if message is None:
            raise make_error(
                RetryUnavailableError, "no unacknowledged message is available to retry"
            )
        if self.manual_retries >= self.settings.manual_retry_limit:
            raise make_error(RetryUnavailableError, "manual retry limit has been reached")
        self.manual_retries += 1
        self.last_retryable = None
        self.active = message
        self._active_transmitted = False
        self.state = "PREPARE"
        self.persist_session()
        return message

    def cancel_pending(self, reason: str) -> int:
        """Log and discard pending messages without interrupting an active exchange."""
        cancelled = len(self.pending)
        while self.pending:
            message = self.pending.popleft()
            self._append_message(
                {
                    "message_id": message.message_id,
                    "original_text": message.text,
                    "received_text": None,
                    "direction": "gateway_to_tracker",
                    "status": "CANCELLED",
                    "detail": reason,
                    "host_timestamp": _utc_now(),
                }
            )
        self.persist_session()
        return cancelled

    def clear_visible_events(self) -> None:
        """Clear only the bounded terminal view; preserve evidence files and counters."""
        self.visible_events.clear()

    def reject_input(
        self,
        text: str,
        reason: str,
        disposition: InputDisposition = InputDisposition.BLOCKED,
    ) -> None:
        """Persist a rejected input without recording it as a radio transmission."""
        self._append_message(
            {
                "message_id": uuid4().hex,
                "original_text": text,
                "received_text": None,
                "direction": "gateway_to_tracker",
                "status": disposition.value,
                "detail": reason,
                "host_timestamp": _utc_now(),
            }
        )

    def set_state(self, state: str, *, mode: str, connected: bool) -> None:
        """Persist the current console state and actual connection status."""
        self.state = state
        self.mode = mode
        self.connected = connected
        self.persist_session(mode=mode, connected=connected)

    def persist_session(self, *, mode: str | None = None, connected: bool | None = None) -> None:
        """Atomically refresh the host-side summary without writing device storage."""
        if mode is not None:
            self.mode = mode
        if connected is not None:
            self.connected = connected
        document = {
            "mode": self.mode,
            "connected": self.connected,
            "started_at": self.started_at,
            "updated_at": _utc_now(),
            "state": self.state,
            "active_message_id": self.active.message_id if self.active else None,
            "pending_messages": len(self.pending),
            "counters": asdict(self.stats),
            "tracker_echo_supported_by_installed_firmware": self.echo_supported,
        }
        temporary = self.session_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.session_path)

    def _message_record(self, completed: CompletedMessage) -> dict[str, Any]:
        """Build the requested per-message evidence record from observed events."""
        return {
            "message_id": completed.message.message_id,
            "original_text": completed.message.text,
            "received_text": completed.received_text,
            "direction": "gateway_to_tracker_and_back",
            "campaign": completed.campaign_id,
            "sequence": completed.sequence,
            "chunk_index": 1 if completed.fragment_count else None,
            "chunk_count": completed.fragment_count,
            "ack": "accepted" if completed.ack_accepted else None,
            "nack_count": completed.transaction_nacks,
            "attempts": completed.attempts,
            "retries": completed.retries,
            "timeouts": completed.timeouts,
            "transaction_result": completed.status,
            "host_timestamp": completed.message.created_at,
            "host_elapsed_ms": completed.host_elapsed_ms,
            "echo_fragment_latency_ms": completed.echo_fragment_latency_ms,
            "firmware_timestamps_ms": completed.firmware_timestamps_ms,
            "detail": completed.detail,
        }

    def _append_message(self, record: dict[str, Any]) -> None:
        """Append one UTF-8 JSON record to the host message journal."""
        with self.messages_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def _utc_now() -> str:
    """Return an RFC 3339 UTC timestamp for host-observed events."""
    return datetime.now(UTC).isoformat()


def _remember_bounded[Identity: Hashable](
    identity: Identity, seen: set[Identity], history: deque[Identity]
) -> None:
    """Keep replay-detection identities within the configured event-history bound."""
    if len(history) == history.maxlen:
        seen.discard(history.popleft())
    history.append(identity)
