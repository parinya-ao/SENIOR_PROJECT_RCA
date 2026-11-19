"""Typer entry point and prompt-safe interactive LoRa bench console."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tools.lora_chat.errors import make_error
from tools.lora_chat.protocol import (
    DeviceEvent,
    DeviceRole,
    UnsupportedPayloadError,
    parse_firmware_event,
)
from tools.lora_chat.session import (
    ChatSession,
    ChatSettings,
    ExchangeResult,
    InputDisposition,
    QueueFullError,
    RetryUnavailableError,
    load_chat_settings,
)
from tools.lora_chat.transport import (
    BenchTransport,
    TransportError,
    load_bench_profile,
)

if TYPE_CHECKING:
    from collections import deque


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class ConsoleRuntime:
    """Run-specific display settings that do not belong to protocol state."""

    settings: ChatSettings
    dry_run: bool
    startup_error: str | None


class ConsoleStateError(RuntimeError):
    """Raised when the interactive console is used before its UI is initialized."""


class InteractiveConsole:
    """Own the prompt, event watcher, serialized message worker, and shutdown."""

    def __init__(
        self,
        transport: BenchTransport,
        chat: ChatSession,
        runtime: ConsoleRuntime,
    ) -> None:
        """Bind one session to the real transport or an explicitly non-radio dry run."""
        self.transport = transport
        self.chat = chat
        self.settings = runtime.settings
        self.profile = transport.profile
        self.dry_run = runtime.dry_run
        self.startup_error = runtime.startup_error
        self.console: Console | None = None
        self.prompt: PromptSession[str] | None = None
        self.worker: asyncio.Task[None] | None = None
        self.event_watcher: asyncio.Task[None] | None = None
        self.stop_events = asyncio.Event()
        self.accepting_messages = True
        self.startup_row_count = 0

    async def run(self) -> None:
        """Run until /quit, EOF, or Ctrl-C, then park and release device ports."""
        with patch_stdout():
            self.console = Console(file=sys.stdout, highlight=False, soft_wrap=True)
            self.prompt = PromptSession()
            self.transport.attach_prompt_output(sys.stdout)
            initial_rows, self.startup_row_count = self.transport.events_since(0)
            self._render_dashboard()
            if self.startup_error:
                self.console.print(f"[red]Connection unavailable:[/] {self.startup_error}")
            self.event_watcher = asyncio.create_task(self._watch_events(initial_rows))
            try:
                await self._prompt_loop()
            finally:
                self.accepting_messages = False
                await self._shutdown()

    async def _shutdown(self) -> None:
        """Drain the bounded active exchange and always release monitored ports."""
        try:
            try:
                self.chat.cancel_pending("console is shutting down")
            finally:
                await self._finish_worker()
        finally:
            clean = False
            cleanup_error: str | None = None
            try:
                clean = await asyncio.to_thread(self.transport.close)
            except (OSError, TimeoutError, RuntimeError) as error:
                cleanup_error = str(error)
            self.stop_events.set()
            if self.event_watcher is not None:
                await self.event_watcher
            if self.dry_run:
                final_state = "DRY_RUN_COMPLETE"
                cleanup_message = "Dry run ended; no radios or device ports were accessed."
            elif cleanup_error is not None:
                final_state = "CLEANUP_FAILED"
                cleanup_message = f"Cleanup failed: {cleanup_error}"
            elif self.transport.parked and clean:
                final_state = "PARKED"
                cleanup_message = "Radios parked and ports released."
            elif self.transport.parked:
                final_state = "CLEANUP_FAILED"
                cleanup_message = "Radio park status could not be verified."
            elif self.transport.monitors_open:
                final_state = "CLEANUP_FAILED"
                cleanup_message = "Cleanup could not verify both radios parked."
            else:
                final_state = "DISCONNECTED"
                cleanup_message = "No device monitors remained open."
            self.chat.set_state(
                final_state,
                mode="DRY RUN" if self.dry_run else "REAL RF",
                connected=False,
            )
            if self.console is not None:
                self.console.print(cleanup_message)
                self.console.print(f"Logs: {self.transport.run_dir}")

    async def _prompt_loop(self) -> None:
        """Read complete lines while prompt_toolkit safely redraws streamed events."""
        if self.prompt is None:
            raise make_error(ConsoleStateError, "interactive prompt is not initialized")
        while True:
            try:
                line = await self.prompt.prompt_async("You > ")
            except EOFError, KeyboardInterrupt:
                return
            if not await self._handle_line(line):
                return

    async def _handle_line(self, line: str) -> bool:
        """Dispatch console commands or queue one supported configured message."""
        if self.console is None:
            raise make_error(ConsoleStateError, "console renderer is not initialized")
        command = line.strip().lower()
        if command.startswith("/"):
            return await self._handle_command(command, line)
        if line:
            self.console.print(Text(f"You > {line}", style="cyan"))
            await self._queue_message(line)
        return True

    async def _handle_command(self, command: str, original_line: str) -> bool:
        """Run one named console command and return whether the prompt should continue."""
        if self.console is None:
            raise make_error(ConsoleStateError, "console renderer is not initialized")
        keep_running = True
        if command == "/help":
            self.console.print(_help_panel())
        elif command == "/status":
            self._render_dashboard()
        elif command == "/clear":
            self.console.clear()
            self._render_dashboard()
        elif command == "/logs":
            self.console.print(f"Logs: {self.transport.run_dir}")
        elif command == "/retry":
            await self._retry()
        elif command == "/park":
            await self._park()
        elif command == "/quit":
            keep_running = False
        else:
            self.console.print(f"[yellow]Unknown command:[/] {original_line}")
        return keep_running

    async def _queue_message(self, text: str) -> None:
        """Accept only the active firmware payload and keep one exchange in flight."""
        if self.console is None:
            raise make_error(ConsoleStateError, "console renderer is not initialized")
        if not self.accepting_messages:
            reason = "console is parked and no longer accepts transmissions"
            self.chat.reject_input(text, reason)
            self.console.print(f"[red]BLOCKED:[/] {reason}")
            return
        try:
            encoded = text.encode("utf-8")
        except UnicodeEncodeError as error:
            self._reject_input(text, str(error), InputDisposition.UNSUPPORTED)
            return
        if encoded != self.profile.payload:
            reason = (
                "installed firmware accepts only its configured payload: "
                f"{self.profile.payload.decode('ascii')}"
            )
            self._reject_input(text, reason, InputDisposition.UNSUPPORTED)
            return
        blocker = self.transport.transmit_blocker()
        if blocker:
            self._reject_input(text, blocker)
            return
        try:
            _, queued = self.chat.submit(text)
        except UnsupportedPayloadError as error:
            self._reject_input(text, str(error), InputDisposition.UNSUPPORTED)
            return
        except QueueFullError as error:
            self._reject_input(text, str(error))
            return
        self.chat.set_state(
            "QUEUED" if queued else "PREPARE",
            mode="DRY RUN" if self.dry_run else "REAL RF",
            connected=self.transport.is_connected,
        )
        self.console.print(
            "[yellow]QUEUED[/] — waiting for the current transaction"
            if queued
            else "[yellow]WAITING FOR RF EXCHANGE[/]"
        )
        self._start_worker()

    def _reject_input(
        self,
        text: str,
        reason: str,
        disposition: InputDisposition = InputDisposition.BLOCKED,
    ) -> None:
        """Log a locally rejected message without recording any RF event."""
        if self.console is None:
            raise make_error(ConsoleStateError, "console renderer is not initialized")
        self.chat.reject_input(text, reason, disposition)
        if disposition is InputDisposition.UNSUPPORTED:
            self.console.print(f"[red]UNSUPPORTED; no DATA sent:[/] {reason}")
        else:
            self.console.print(f"[yellow]BLOCKED; no DATA sent:[/] {reason}")

    def _start_worker(self, *, retry_first: bool = False) -> None:
        """Start one message worker only when no previous exchange is still active."""
        if self.worker is None or self.worker.done():
            self.worker = asyncio.create_task(self._drain_messages(retry_first=retry_first))

    async def _drain_messages(self, *, retry_first: bool = False) -> None:
        """Process queued messages sequentially through the existing bounded RF runner."""
        if self.console is None:
            raise make_error(ConsoleStateError, "console renderer is not initialized")
        while self.chat.active is not None:
            message = self.chat.active
            self.chat.set_state(
                "WAIT_ACK",
                mode="DRY RUN" if self.dry_run else "REAL RF",
                connected=self.transport.is_connected,
            )
            operation = self.transport.retry_message if retry_first else self.transport.send_message
            retry_first = False
            try:
                result = await asyncio.to_thread(operation, message.text)
            except (TransportError, TimeoutError, ValueError) as error:
                result = ExchangeResult("FAILED", str(error), (), 0, 0, 0, 0.0)
            completed, next_message = self.chat.finish_current(result)
            if completed.ack_accepted and completed.campaign_id is not None:
                self.console.print(
                    f"[green]ACK accepted[/] — SEQ={completed.sequence} "
                    f"CAMPAIGN={completed.campaign_id:04X}"
                )
            else:
                self.console.print(f"[red]{completed.status}[/] — {completed.detail}")
            if completed.received_text is not None:
                self.console.print(Text(f"Tracker > {completed.received_text}", style="cyan"))
                self.console.print("[green]Status > SUCCESS[/]")
            elif completed.ack_accepted:
                self.console.print(
                    "[yellow]Status > ACK ONLY; Tracker application echo is unsupported.[/]"
                )
            self.console.print(
                f"Attempts={completed.attempts} Retries={completed.retries} "
                f"Timeouts={completed.timeouts} Host elapsed={completed.host_elapsed_ms:.1f} ms"
            )
            if next_message is None:
                return
            if not self.accepting_messages:
                self.chat.cancel_pending("console is parking")
                return

    async def _retry(self) -> None:
        """Reconnect explicitly if needed, then allow only a bounded unacknowledged retry."""
        if self.console is None:
            raise make_error(ConsoleStateError, "console renderer is not initialized")
        if not self.accepting_messages:
            self.console.print("[yellow]Retry unavailable; the console is parked.[/]")
            return
        if self.chat.active is not None or (self.worker is not None and not self.worker.done()):
            self.console.print("[yellow]Retry unavailable; a transaction is still active.[/]")
            return
        if not self.transport.is_connected and not self.transport.dry_run:
            try:
                await asyncio.to_thread(self.transport.reconnect)
            except (OSError, TimeoutError, ValueError, RuntimeError) as error:
                self.console.print(f"[red]Reconnect failed:[/] {error}")
                return
            self.console.print("[green]Both devices reconnected and reverified.[/]")
            if self.chat.last_retryable is None:
                return
        reason = self.transport.transmit_blocker()
        if reason:
            self.console.print(f"[yellow]Retry blocked; no DATA sent:[/] {reason}")
            return
        try:
            self.chat.retry_last()
        except RetryUnavailableError as error:
            self.console.print(f"[yellow]Retry unavailable:[/] {error}")
            return
        self._start_worker(retry_first=True)

    async def _park(self) -> None:
        """Stop queue admission, finish any active bounded exchange, then park both radios."""
        if self.console is None:
            raise make_error(ConsoleStateError, "console renderer is not initialized")
        self.accepting_messages = False
        self.chat.cancel_pending("radios are being parked")
        await self._finish_worker()
        had_monitors = self.transport.monitors_open
        clean = await asyncio.to_thread(self.transport.park)
        if self.dry_run:
            state = "DRY_RUN_COMPLETE"
            message = "Dry run ended; no radios or device ports were accessed."
        elif self.transport.parked and clean:
            state = "PARKED"
            message = "Both radios parked; ports released."
        elif had_monitors:
            state = "CLEANUP_FAILED"
            message = "Could not verify both radios parked."
        else:
            state = "DISCONNECTED"
            message = "No device monitors were open; no park event was claimed."
        self.chat.set_state(
            state,
            mode="DRY RUN" if self.dry_run else "REAL RF",
            connected=False,
        )
        self.console.print(message)

    async def _finish_worker(self) -> None:
        """Wait for the current firmware transaction's configured finite timeout."""
        if self.worker is not None and not self.worker.done():
            await self.worker

    async def _watch_events(self, startup_rows: list[dict[str, Any]]) -> None:
        """Display captured device lines while preserving the active input prompt."""
        if self.console is None:
            raise make_error(ConsoleStateError, "console renderer is not initialized")
        offset = 0
        for row_index, row in enumerate(startup_rows):
            self._show_row(row, buffered=row_index < self.startup_row_count)
        if startup_rows:
            self._render_dashboard()
        offset = len(startup_rows)
        while True:
            rows, next_offset = self.transport.events_since(offset)
            for row in rows:
                self._show_row(row, buffered=False)
            if rows:
                self._render_dashboard()
            offset = next_offset
            if self.stop_events.is_set():
                return
            await asyncio.sleep(self.settings.refresh_interval_ms / 1000)

    def _show_row(self, row: dict[str, Any], *, buffered: bool) -> None:
        """Render one captured row only when the existing device logger supplied it."""
        if self.console is None:
            return
        event = _parse_event(row)
        if event is None:
            return
        self.chat.observe_event(event)
        prefix = "BUFFERED" if buffered else "LIVE"
        style = _event_style(event)
        stamp = event.host_timestamp or "host time unavailable"
        role = "TRACKER" if event.role is DeviceRole.TRACKER else "GATEWAY"
        if not self.transport.verbose:
            self.console.print(
                f"[dim]{stamp} {prefix}[/] [{style}]{role}[/] [{style}]{event.line}[/]"
            )

    def _render_dashboard(self) -> None:
        """Render the header, both live device panels, and session counters."""
        if self.console is None:
            raise make_error(ConsoleStateError, "console renderer is not initialized")
        mode = "DRY RUN — RF DISABLED" if self.dry_run else "REAL RF"
        header = Panel(
            Text.assemble(
                ("LoRa Interactive Debug Console\n", "bold cyan"),
                ("Gateway ↔ Tracker\n", "white"),
                (mode, "yellow" if self.dry_run else "bold green"),
            ),
            border_style="cyan",
            box=box.ROUNDED,
        )
        devices = Columns([self._device_panel("GATEWAY"), self._device_panel("TRACKER")])
        counters = Table.grid(padding=(0, 2))
        counters.add_column(style="dim")
        counters.add_column()
        values = self.chat.stats
        for label, value in (
            ("Messages sent", values.messages_sent),
            ("Messages received", values.messages_received),
            ("ACK accepted", values.ack_count),
            ("NACK received", values.nack_count),
            ("Retries", values.retry_count),
            ("Timeouts", values.timeout_count),
            ("Successful round trips", values.round_trip_successes),
            ("Failed transactions", values.failed_transactions),
            ("State", self.chat.state),
        ):
            counters.add_row(label, str(value))
        status = Panel(counters, title="Session status", border_style="blue")
        self.console.print(Group(header, devices, status))

    def _device_panel(self, role: str) -> Panel:
        """Show the latest actual event and identity for one endpoint."""
        if self.console is None:
            raise make_error(ConsoleStateError, "console renderer is not initialized")
        table = Table.grid(padding=(0, 1))
        table.add_column(style="dim", width=15)
        table.add_column()
        if self.dry_run:
            connection = "DRY RUN — not connected"
        else:
            connection = "CONNECTED" if self.transport.is_connected else "DISCONNECTED"
        table.add_row("Connection", connection)
        table.add_row("Firmware", self.transport.firmware_identity(role))
        table.add_row("Radio", self.transport.radio_state(role))
        event_fields: list[tuple[str, set[str]]]
        if role == "GATEWAY":
            event_fields = [
                ("DATA TX", {"DATA_TX_BEGIN", "DATA_TX_DONE"}),
                ("DATA RX", {"DATA_RX", "PAYLOAD_BYTES"}),
                ("ACK RX", {"ACK_RX", "ACK_ACCEPTED"}),
                ("NACK RX", {"NACK_RX"}),
            ]
        else:
            event_fields = [
                ("DATA RX", {"DATA_RX", "PAYLOAD_BYTES"}),
                ("DATA TX", {"DATA_TX_BEGIN", "DATA_TX_DONE"}),
                ("ACK TX", {"ACK_TX_BEGIN", "ACK_TX_DONE", "ACK_DUP_TX_DONE"}),
                ("NACK TX", {"NACK_TX_BEGIN", "NACK_TX_DONE"}),
                (
                    "Validation",
                    {"DATA_VALIDATED", "DATA_REJECTED_PAYLOAD", "DATA_REJECTED_TEST"},
                ),
            ]
        for label, names in event_fields:
            event = _latest_event(self.chat.visible_events, role, names)
            table.add_row(label, _event_summary(event) if event else "—")
        if role == "TRACKER":
            payload_event = _latest_event(self.chat.visible_events, role, {"PAYLOAD_BYTES"})
            payload_text = (
                repr(payload_event.payload.decode("utf-8", errors="replace"))
                if payload_event is not None and payload_event.payload is not None
                else "—"
            )
            table.add_row("Payload", payload_text)
        table.add_row("Retries", str(self.chat.stats.retry_count))
        last = _latest_event(self.chat.visible_events, role, None)
        table.add_row("Sequence", str(last.sequence) if last and last.sequence else "—")
        table.add_row(
            "Campaign",
            f"{last.campaign_id:04X}" if last and last.campaign_id is not None else "—",
        )
        return Panel(table, title=role, border_style="cyan" if role == "GATEWAY" else "blue")


def main(
    *,
    dry_run: bool = False,
    authorize_rf_test: bool = False,
    verbose: bool = False,
) -> None:
    """Launch the interactive console without flashing or transmitting on startup."""
    try:
        settings = load_chat_settings()
        profile = load_bench_profile()
    except (OSError, TypeError, ValueError) as error:
        Console(stderr=True).print(f"[red]Configuration error:[/] {error}")
        raise typer.Exit(code=2) from error
    if dry_run and authorize_rf_test:
        Console(stderr=True).print("[red]--dry-run cannot be combined with RF authorization.[/]")
        raise typer.Exit(code=2)

    run_dir = _create_run_directory(ROOT / "artifacts" / "lora-chat")
    transport = BenchTransport(
        run_dir,
        profile,
        authorize_rf_test=authorize_rf_test,
        dry_run=dry_run,
        verbose=verbose,
    )
    chat = ChatSession(
        run_dir,
        profile,
        settings,
    )
    startup_error: str | None = None
    if not dry_run:
        try:
            transport.connect()
        except (OSError, TimeoutError, ValueError, KeyError, RuntimeError) as error:
            startup_error = str(error)
            transport.close()
    chat.set_state(
        "IDLE" if transport.is_connected or dry_run else "DISCONNECTED",
        mode="DRY RUN" if dry_run else "REAL RF",
        connected=transport.is_connected,
    )
    try:
        asyncio.run(
            InteractiveConsole(
                transport,
                chat,
                ConsoleRuntime(settings, dry_run, startup_error),
            ).run()
        )
    except KeyboardInterrupt:
        transport.close()
        chat.set_state("PARKED", mode="DRY RUN" if dry_run else "REAL RF", connected=False)


def _create_run_directory(root: Path) -> Path:
    """Choose a unique UTC-named host evidence path; the transport creates it once."""
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    return root / run_id


def _help_panel() -> Panel:
    """Render supported commands and the installed-firmware payload constraint."""
    return Panel(
        "Type the configured message directly. Installed firmware currently accepts only "
        "its exact hello world payload.\n\n"
        "/help  /status  /clear  /logs  /retry  /park  /quit",
        title="Commands",
        border_style="cyan",
    )


def _parse_event(row: dict[str, Any]) -> DeviceEvent | None:
    """Parse a structured firmware line and keep malformed output diagnostic-only."""
    try:
        return parse_firmware_event(row)
    except ValueError as error:
        role = DeviceRole.GATEWAY if row.get("role") == "GATEWAY" else DeviceRole.TRACKER
        return DeviceEvent(
            role=role,
            name="MALFORMED_EVENT",
            line=(
                row["line"]
                if isinstance(row.get("line"), str)
                else f"Malformed firmware event: {error}"
            ),
            host_timestamp=str(row.get("timestamp", "")),
            firmware_ms=None,
            campaign_id=None,
            sequence=None,
            packet_type=None,
            source=None,
            destination=None,
            payload=None,
        )


def _event_style(event: DeviceEvent) -> str:
    """Choose display color from the observed event name, not inferred success."""
    if "NACK" in event.name or "FAIL" in event.name or "ERROR" in event.name:
        return "red"
    if event.name.startswith("ACK"):
        return "green"
    if "DATA" in event.name or event.name == "PAYLOAD_BYTES":
        return "cyan"
    return "bright_black"


def _latest_event(
    events: deque[DeviceEvent], role: str, names: set[str] | None
) -> DeviceEvent | None:
    """Find the newest bounded-history event for one role and optional event set."""
    desired = DeviceRole.TRACKER if role == "TRACKER" else DeviceRole.GATEWAY
    for event in reversed(events):
        if event.role is desired and (names is None or event.name in names):
            return event
    return None


def _event_summary(event: DeviceEvent) -> str:
    """Show event identity fields only when the firmware actually supplied them."""
    identity = []
    if event.sequence is not None:
        identity.append(f"SEQ={event.sequence}")
    if event.campaign_id is not None:
        identity.append(f"CAMPAIGN={event.campaign_id:04X}")
    if event.payload is not None:
        identity.append(f"LEN={len(event.payload)}")
    return " ".join((event.name, *identity))
