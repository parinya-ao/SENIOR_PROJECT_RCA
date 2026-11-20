"""Host checks for the physical acceptance runner's gating and evidence rules."""

from types import SimpleNamespace

from tools.lora_chat.echo_trials import messages, run_trials, suppressed_echo_observed
from tools.lora_chat.protocol import parse_firmware_event
from tools.lora_chat.session import ExchangeResult


def test_trial_list_has_utf8_boundary_and_command_like_payloads() -> None:
    """Keep exactly ten positive cases including a multi-packet UTF-8 message."""
    samples = messages()
    assert len(samples) == 10
    assert "สวัสดีครับ" in samples and "ls" in samples
    assert max(len(text.encode()) for text in samples) == 1024


def test_legacy_pair_blocks_acceptance_without_sending() -> None:
    """An authorized legacy pair cannot transmit any of the Echo acceptance cases."""
    transport = SimpleNamespace(transmit_blocker=lambda: None, echo_supported=False)
    chat = SimpleNamespace()
    assert run_trials(transport, chat)["status"] == "BLOCKED"


def test_missing_echo_trial_requires_matching_ack_and_timeout() -> None:
    """A stale timeout and ACK-only success cannot satisfy the negative trial."""
    rows = [
        ("RECEIVER", "ECHO_SUPPRESSED_TEST SID=351C T=2 TYPE=8 Q=1 E=0"),
        ("GATEWAY", "ACK_ACCEPTED SID=351C T=3 TYPE=3 Q=1 E=0"),
        ("GATEWAY", "ECHO_TIMEOUT SID=351D T=4 TYPE=8 Q=1 E=-1"),
        ("GATEWAY", "ECHO_TIMEOUT SID=351C T=5 TYPE=8 Q=1 E=-1"),
    ]
    events = tuple(
        event
        for role, line in rows
        if (event := parse_firmware_event({"role": role, "line": f"[{role}] {line}"})) is not None
    )
    assert len(events) == 4
    assert not suppressed_echo_observed(ExchangeResult("FAIL", "stale", events[:-1], 1, 0, 1, 5))
    assert suppressed_echo_observed(ExchangeResult("FAIL", "timeout", events, 1, 0, 1, 5))
