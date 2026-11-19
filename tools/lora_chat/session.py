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
    DeviceEvent,
    DeviceRole,
    MessageProtocol,
    RoundTripContext,
    encode_message,
    matches_ack,
    verify_round_trip,
)

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "config" / "lora_chat.json"
SETTING_RANGES = {
    "max_pending_messages": (1, 64),
    "event_history_limit": (1, 1000),
    "refresh_interval_ms": (25, 2000),
    "manual_retry_limit": (0, 3),
}


@dataclass(frozen=True, slots=True)
class ChatSettings:
    """Validated limits used by the interactive console."""

    max_pending_messages: int
    event_history_limit: int
    refresh_interval_ms: int
    manual_retry_limit: int


@dataclass(frozen=True, slots=True)
class MessageRequest:
    """One user message and its stable identity across bounded retries."""

    message_id: str
    text: str
    payload: bytes
    created_at: str


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
    failed_transactions: int = 0


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
    """Load and strictly validate the file-backed console limits."""
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise make_error(
            SessionConfigError, f"Cannot read LoRa console settings from {path}: {error}"
        ) from error
    if not isinstance(values, dict):
        raise make_error(SessionConfigTypeError, "LoRa console settings must be a JSON object")

    expected = {
        "max_pending_messages",
        "event_history_limit",
        "refresh_interval_ms",
        "manual_retry_limit",
    }
    if values.keys() != expected:
        unknown = sorted(values.keys() - expected)
        missing = sorted(expected - values.keys())
        raise make_error(
            SessionConfigError,
            f"Invalid LoRa console settings; missing={missing}, unknown={unknown}",
        )
    for name, value in values.items():
        if type(value) is not int:
            raise make_error(
                SessionConfigTypeError, f"LoRa console setting {name} must be an integer"
            )
        minimum, maximum = SETTING_RANGES[name]
        if not minimum <= value <= maximum:
            raise make_error(
                SessionConfigError,
                f"LoRa console setting {name} must be in {minimum}..{maximum}",
            )
    return ChatSettings(
        max_pending_messages=values["max_pending_messages"],
        event_history_limit=values["event_history_limit"],
        refresh_interval_ms=values["refresh_interval_ms"],
        manual_retry_limit=values["manual_retry_limit"],
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
        self.stats = ChatStats()
        self.started_at = _utc_now()
        self.visible_events: deque[DeviceEvent] = deque(maxlen=settings.event_history_limit)
        self._seen_event_lines: set[tuple[str, str, str]] = set()
        self._seen_event_order: deque[tuple[str, str, str]] = deque(
            maxlen=settings.event_history_limit
        )
        self._seen_data: set[tuple[DeviceRole, int | None, int | None]] = set()
        self._seen_transmissions: set[tuple[int | None, int | None]] = set()
        self._seen_data_order: deque[tuple[DeviceRole, int | None, int | None]] = deque(
            maxlen=settings.event_history_limit
        )
        self._seen_transmissions_order: deque[tuple[int | None, int | None]] = deque(
            maxlen=settings.event_history_limit
        )
        self._retry_message_id: str | None = None
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
        payload = encode_message(text, self.profile.payload, MAX_APPLICATION_PAYLOAD_BYTES)
        message = MessageRequest(uuid4().hex, text, payload, _utc_now())
        queued = self.active is not None
        if queued:
            if len(self.pending) >= self.settings.max_pending_messages:
                raise QueueFullError
            self.pending.append(message)
        else:
            self.active = message
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

        if event.role is DeviceRole.GATEWAY and event.name == "ACK_ACCEPTED":
            self.stats.ack_count += 1
        if event.role is DeviceRole.GATEWAY and event.name == "NACK_RX":
            self.stats.nack_count += 1
        if event.name in {"ACK_TIMEOUT", "TX_TIMEOUT", "TIMEOUT"}:
            self.stats.timeout_count += 1
        if event.name == "DATA_TX_DONE" and event.role is DeviceRole.GATEWAY:
            tx_identity = (event.campaign_id, event.sequence)
            if tx_identity not in self._seen_transmissions:
                _remember_bounded(
                    tx_identity, self._seen_transmissions, self._seen_transmissions_order
                )
                self._seen_transmissions.add(tx_identity)
                self.stats.messages_sent += 1
        if event.name in {"DATA_RX", "PAYLOAD_BYTES"} and event.payload is not None:
            rx_identity = (event.role, event.campaign_id, event.sequence)
            if rx_identity not in self._seen_data:
                _remember_bounded(rx_identity, self._seen_data, self._seen_data_order)
                self._seen_data.add(rx_identity)
                self.stats.messages_received += 1
        self.persist_session()
        return True

    def finish_current(
        self, result: ExchangeResult
    ) -> tuple[CompletedMessage, MessageRequest | None]:
        """Finish one exchange, require real echo evidence, then promote one queued item."""
        message = self.active
        if message is None:
            raise make_error(SessionStateError, "no active message transaction")

        transmit = next(
            (
                event
                for event in result.events
                if event.role is DeviceRole.GATEWAY
                and event.name in {"DATA_TX_BEGIN", "DATA_TX_DONE"}
                and event.packet_type == self.profile.data_type
            ),
            None,
        )
        campaign_id = transmit.campaign_id if transmit else None
        sequence = transmit.sequence if transmit else None
        ack_accepted = bool(
            campaign_id is not None
            and sequence is not None
            and matches_ack(
                list(result.events),
                campaign_id=campaign_id,
                sequence=sequence,
                ack_type=self.profile.ack_type,
            )
        )
        round_trip = bool(
            result.status == "PASS"
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
                ),
            )
        )
        received_text = message.text if round_trip else None
        if round_trip:
            status = "SUCCESS"
            self.stats.round_trip_successes += 1
        elif ack_accepted:
            status = "ACK_ONLY"
            self.stats.failed_transactions += 1
        else:
            status = "TIMEOUT" if result.status == "TIMEOUT" else "FAILED"
            self.stats.failed_transactions += 1

        transmitted = transmit is not None
        total_retries = max(0, result.retries) + (self.manual_retries if transmitted else 0)
        self.stats.retry_count += total_retries
        if result.timeouts and not any(
            event.name in {"ACK_TIMEOUT", "TX_TIMEOUT", "TIMEOUT"} for event in result.events
        ):
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
                if ack_accepted and not round_trip
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
                event.role is DeviceRole.GATEWAY and event.name == "NACK_RX"
                for event in result.events
            ),
        )
        self._append_message(self._message_record(completed))
        self.last_retryable = message if not ack_accepted else None
        if self._retry_message_id != message.message_id:
            self.manual_retries = 0
        self._retry_message_id = message.message_id
        self.active = self.pending.popleft() if self.pending else None
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
            "tracker_echo_supported_by_installed_firmware": False,
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
            "chunk_index": 1,
            "chunk_count": 1,
            "ack": "accepted" if completed.ack_accepted else None,
            "nack_count": completed.transaction_nacks,
            "attempts": completed.attempts,
            "retries": completed.retries,
            "timeouts": completed.timeouts,
            "transaction_result": completed.status,
            "host_timestamp": completed.message.created_at,
            "host_elapsed_ms": completed.host_elapsed_ms,
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
