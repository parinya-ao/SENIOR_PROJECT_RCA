"""CLI contract tests for Typer help and prompt-safe terminal output."""

from __future__ import annotations

import asyncio
import fcntl
from io import StringIO
import os
import select
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path

import pytest
import typer
from rich.console import Console
from typer.testing import CliRunner

from tools.lora_chat import cli
from tools.lora_chat.session import ChatSession, load_chat_settings
from tools.lora_chat.transport import BenchTransport, load_bench_profile


def test_typer_app_exposes_help_for_supported_options() -> None:
    """Keep module options discoverable through the explicit Typer application."""
    app = getattr(cli, "app", None)
    assert isinstance(app, typer.Typer), "CLI should expose an explicit Typer app"

    result = CliRunner().invoke(
        app,
        ["--help"],
        color=False,
        terminal_width=120,
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )

    assert result.exit_code == 0
    assert "--dry-run" in result.output
    assert "--authorize-rf-test" in result.output
    assert "--confirm-rf-setup" in result.output
    assert "--historical-receipt" in result.output
    assert "--verbose" in result.output


@pytest.mark.parametrize(
    ("args", "receipt_exists", "authorized", "confirmed", "expected_receipt"),
    [
        ([], True, True, True, "reviewed.json"),
        (["--no-authorize-rf-test"], True, False, True, "reviewed.json"),
        (["--dry-run"], True, False, False, None),
        ([], False, False, False, None),
        (["--historical-receipt", "other.json"], True, False, False, "other.json"),
    ],
)
def test_plain_chat_uses_only_the_configured_bench_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
    receipt_exists: bool,
    authorized: bool,
    confirmed: bool,
    expected_receipt: str | None,
) -> None:
    """Resolve the saved bench at the normal CLI entry point, without accessing hardware."""
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    receipt = tmp_path / "reviewed.json"
    if receipt_exists:
        receipt.touch()
    settings_file = tmp_path / "lora_chat.json"
    settings_file.write_text(
        '{"max_pending_messages":8,"max_message_bytes":4096,"event_history_limit":120,'
        '"refresh_interval_ms":100,"manual_retry_limit":1,"confirmed_bench_receipt":"reviewed.json"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "load_chat_settings", lambda: load_chat_settings(settings_file))
    connections: list[BenchTransport] = []
    monkeypatch.setattr(BenchTransport, "connect", lambda self: connections.append(self))

    async def check_console(console: cli.InteractiveConsole) -> None:
        """Check options forwarded to the real transport constructor."""
        assert console.transport.authorize_rf_test is authorized
        assert console.transport.confirm_rf_setup is confirmed
        selected = console.transport.historical_receipt
        assert (selected.name if selected is not None else None) == expected_receipt

    monkeypatch.setattr(cli.InteractiveConsole, "run", check_console)
    result = CliRunner().invoke(cli.app, args, catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert bool(connections) is ("--dry-run" not in args)


def test_terminal_output_preserves_rich_ansi_in_prompt_toolkit() -> None:
    """Exercise the actual module entry point in a TTY with Rich colors enabled."""
    master_fd, slave_fd = os.openpty()
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
    environment = os.environ.copy()
    environment["TERM"] = "xterm-256color"
    environment.pop("NO_COLOR", None)
    process = subprocess.Popen(
        [sys.executable, "-m", "tools.lora_chat", "--dry-run"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=environment,
        close_fds=True,
    )
    os.close(slave_fd)
    output = bytearray()
    deadline = time.monotonic() + 10
    try:
        os.write(master_fd, b"test\n/quit\n")
        while process.poll() is None and time.monotonic() < deadline:
            readable, _, _ = select.select([master_fd], [], [], 0.1)
            if readable:
                try:
                    output.extend(os.read(master_fd, 65536))
                except OSError:
                    break
        if process.poll() is None:
            raise AssertionError("dry-run CLI did not exit after /quit")
        while select.select([master_fd], [], [], 0.1)[0]:
            try:
                output.extend(os.read(master_fd, 65536))
            except OSError:
                break
    finally:
        os.close(master_fd)
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)

    assert b"\x1b[" in output
    assert b"?[36m" not in output
    assert output.count(b"You > test") == 1
    assert b"BLOCKED; no DATA sent" in output
    assert b"\x1b[>0u" in output
    assert b"\x1b[<u" in output


def test_csi_u_keyboard_sequence_is_rejected_as_a_message(tmp_path: Path) -> None:
    """Keep terminal key protocol output out of real or queued DATA messages."""
    profile = load_bench_profile()
    settings = load_chat_settings()
    transport = BenchTransport(
        tmp_path / "transport",
        profile,
        max_message_bytes=settings.max_message_bytes,
        authorize_rf_test=False,
        dry_run=True,
    )
    chat_path = tmp_path / "chat"
    chat_path.mkdir()
    chat = ChatSession(chat_path, profile, settings)
    console = cli.InteractiveConsole(
        transport,
        chat,
        cli.ConsoleRuntime(settings, dry_run=True, startup_error=None),
    )
    output = StringIO()
    console.console = Console(file=output, force_terminal=False)

    asyncio.run(console._handle_line("[3593;5u"))

    assert "CSI-u keyboard sequence" in output.getvalue()
    assert transport.events_since(0) == ([], 0)
    assert chat.stats.messages_sent == 0


def test_prompt_admits_utf8_when_both_endpoints_support_echo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Admit arbitrary UTF-8 only after the transport negotiated Echo."""
    profile = load_bench_profile()
    settings = load_chat_settings()
    transport = BenchTransport(
        tmp_path / "transport",
        profile,
        max_message_bytes=settings.max_message_bytes,
        authorize_rf_test=False,
        dry_run=True,
    )
    chat_path = tmp_path / "chat"
    chat_path.mkdir()
    chat = ChatSession(chat_path, profile, settings)
    console = cli.InteractiveConsole(
        transport, chat, cli.ConsoleRuntime(settings, dry_run=False, startup_error=None)
    )
    console.console = Console(file=StringIO(), force_terminal=False)
    monkeypatch.setattr(transport, "transmit_blocker", lambda: None)
    monkeypatch.setattr(console, "_start_worker", lambda: None)

    asyncio.run(console._handle_line("สวัสดี"))
    assert chat.active is None
    transport.interactive_max_data_bytes = 30
    asyncio.run(console._handle_line("สวัสดี"))
    assert chat.active is not None
    assert chat.active.payload == "สวัสดี".encode()

    asyncio.run(console._handle_line("/send   /quit  "))
    assert [message.payload for message in chat.pending] == [b"  /quit  "]
