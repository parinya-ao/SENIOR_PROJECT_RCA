"""Run the bounded physical Echo acceptance trials through the production chat path."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from shutil import copyfile
from typing import Any

from tools import rf_proof as rf
from tools.lora_chat.cli import ROOT, _create_run_directory
from tools.lora_chat.protocol import DeviceRole, EventName
from tools.lora_chat.session import ChatSession, ExchangeResult, load_chat_settings
from tools.lora_chat.transport import BenchTransport, load_bench_profile


def messages() -> tuple[str, ...]:
    """Return the ten acceptance inputs, including a 1024-byte UTF-8 message."""
    return (
        "hello",
        "hello world",
        "test123",
        "123456789",
        "สวัสดีครับ",
        "Gateway to Tracker",
        "LoRa FOTA",
        "ls",
        "ก" * 341 + "!",
        "Gateway → Tracker: สวัสดีครับ! /mode?",
    )


def suppressed_echo_observed(result: ExchangeResult) -> bool:
    """Require a correlated forward ACK and real timeout after suppressing one reply."""
    for event in result.events:
        if (
            event.role is DeviceRole.TRACKER
            and event.name == "ECHO_SUPPRESSED_TEST"
            and event.campaign_id is not None
            and event.sequence is not None
        ):
            matching = {
                row.name
                for row in result.events
                if row.role is DeviceRole.GATEWAY
                and row.campaign_id == event.campaign_id
                and row.sequence == event.sequence
            }
            return {
                EventName.ACK_ACCEPTED,
                EventName.ECHO_TIMEOUT,
            } <= matching and not matching.intersection(
                {EventName.ROUND_TRIP_DONE, EventName.PAYLOAD_BYTES}
            )
    return False


def run_trials(transport: BenchTransport, chat: ChatSession) -> dict[str, Any]:
    """Send one message at a time and stop at the first incomplete physical proof."""
    blocker = transport.transmit_blocker()
    if blocker or transport.echo_supported is not True:
        return {"status": "BLOCKED", "reason": blocker or "Echo is not installed", "trials": []}

    trials: list[dict[str, Any]] = []
    for text in messages():
        request, _ = chat.submit(text)
        complete, _ = chat.finish_current(transport.send_message(text))
        passed = complete.status == "SUCCESS"
        trials.append({"message_id": request.message_id, "status": "PASS" if passed else "FAIL"})
        if not passed:
            return {"status": "FAIL", "reason": complete.detail, "trials": trials}

    fault_results = {}
    for fault, name in (("N", "nack_recovery"), ("J", "missing_echo")):
        request, _ = chat.submit("ls")
        result = transport.echo_fault_trial(request.text, fault)
        complete, _ = chat.finish_current(result)
        if fault == "N":
            passed = (
                complete.status == "SUCCESS"
                and complete.transaction_nacks == 1
                and complete.retries >= 1
                and complete.attempts >= 2
            )
        else:
            passed = complete.received_text is None and suppressed_echo_observed(result)
        fault_results[name] = {
            "message_id": request.message_id,
            "status": "PASS" if passed else "FAIL",
        }
        if not passed:
            return {"status": "FAIL", "trials": trials, "fault_trials": fault_results}

    return {"status": "PASS", "trials": trials, "fault_trials": fault_results}


def _write_json(run_dir: Path, name: str, data: object) -> None:
    """Write one complete UTF-8 evidence record alongside the raw event journal."""
    (run_dir / name).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    """Verify the physical pair, run acceptance trials, and always release the ports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorize-rf-test", action="store_true", required=True)
    parser.add_argument("--confirm-rf-setup", action="store_true", required=True)
    args = parser.parse_args()
    settings, profile = load_chat_settings(), load_bench_profile()
    run_dir = _create_run_directory(ROOT / "artifacts" / "lora-chat")
    transport = BenchTransport(
        run_dir,
        profile,
        max_message_bytes=settings.max_message_bytes,
        authorize_rf_test=args.authorize_rf_test,
        confirm_rf_setup=args.confirm_rf_setup,
        historical_receipt=(
            ROOT / settings.confirmed_bench_receipt
            if settings.confirmed_bench_receipt is not None
            else None
        ),
    )
    chat = ChatSession(run_dir, profile, settings)
    print(run_dir, flush=True)
    report: dict[str, Any]
    capability = "UNVERIFIED"
    try:
        transport.connect()
        capability = transport.interactive_state
        chat.echo_supported = transport.echo_supported
        report = run_trials(transport, chat)
    except (OSError, ValueError, RuntimeError, KeyboardInterrupt) as error:
        report = {"status": "FAIL" if chat.stats.messages_sent else "BLOCKED", "reason": str(error)}
    finally:
        parked = transport.close()
    hardware = transport.hardware
    images = hardware.images if hardware is not None else {}
    layouts = {}
    if hardware is not None:
        for role, image in images.items():
            layout = rf.flash_layout_for_role(hardware.effective, role.lower())
            if layout is not None:
                layouts[role] = {**layout.to_dict(), "live_fuses_hex": image.get("live_fuses_hex")}
    _write_json(
        run_dir,
        "device-identities.json",
        {
            role: {
                "serial": image.get("serial_number"),
                "signature": image.get("signature"),
                "live_build": transport.runtime_builds.get(role.lower()),
            }
            for role, image in images.items()
        },
    )
    build_record = (
        hardware.proof.run_dir / "production-build.json" if hardware and hardware.proof else None
    )
    if build_record is not None and build_record.is_file():
        copyfile(build_record, run_dir / "firmware-builds.json")
    else:
        _write_json(run_dir, "firmware-builds.json", {"status": "UNVERIFIED"})
    _write_json(run_dir, "flash-layout.json", layouts)
    _write_json(run_dir, "flash-verification.json", images)
    _write_json(
        run_dir,
        "capabilities.json",
        {
            "state_before_trials": capability,
            "max_data_bytes": transport.interactive_max_data_bytes,
            "advertisements": [
                row
                for row in transport.events_since(0)[0]
                if " INTERACTIVE_CAPS " in row.get("line", "")
            ],
        },
    )
    _write_json(run_dir, "echo-trials.json", report)
    _write_json(run_dir, "metrics.json", asdict(chat.stats))
    passed = report["status"] == "PASS" and parked
    _write_json(
        run_dir,
        "test-results.json",
        {"status": "PASS" if passed else report["status"] if parked else "FAIL", "parked": parked},
    )
    (run_dir / "summary.md").write_text(
        f"# Physical LoRa Echo trials\n\nResult **{report['status']}**. Radios parked **{parked}**.\n",
        encoding="utf-8",
    )
    return 0 if passed else 2 if report["status"] == "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
