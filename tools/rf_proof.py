#!/usr/bin/env python3
"""Run host/build proof and keep hardware stages behind explicit gates."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import itertools
import json
import os
import queue
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

Json = Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.config.application_config import raw_payload
ARTIFACTS = ROOT / "artifacts" / "rf-proof"
ENVIRONMENTS = ("sender", "sender_hello", "receiver", "sender_hello_spi", "receiver_spi")
# Covers bounded SF7 airtime pacing across all four attempts per sequence.
RF_TEST_TIMEOUT_SECONDS = 6 * 60 * 60
RF_SINGLE_PACKET_TIMEOUT_SECONDS = 5 * 60
RF_COMPLETION_LOG_SETTLE_SECONDS = 2.0
RADIO_SPI_TIMEOUT_SECONDS = 10
PORTS = {
    "gateway": "/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0",
    "receiver": "/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0",
}


def hardware_blockers(
    stage: str,
    *,
    mapping_verified: bool,
    power_verified: bool,
    boot_layout_verified: bool,
    authorized: bool,
    no_meter: bool = False,
) -> list[str]:
    blockers = []
    if not no_meter and not mapping_verified:
        blockers.append("physical board mapping")
    if not no_meter and not power_verified:
        blockers.append("power conditions")
    if not boot_layout_verified:
        blockers.append("BOOTSIZE/CODESIZE/BODCFG fuse verification")
    if not authorized:
        blockers.append(
            "upload authorization"
            if stage in ("upload", "radio-spi-smoke")
            else "RF-test authorization"
        )
    return blockers


def parse_raw_mvp_logs(sender_text: str, receiver_text: str) -> dict[str, object]:
    """Validate raw MVP observations only; capture provenance remains separate."""
    payload = raw_payload()
    starts = {
        int(m[1])
        for m in re.finditer(
            rf"^\[MVP SENDER\] TX_START attempt=(\d+) len={len(payload)} rc=0 cleanup=0$",
            sender_text,
            re.MULTILINE,
        )
    }
    completed = [
        int(m[1])
        for m in re.finditer(
            r"^\[MVP SENDER\] TX_DONE attempt=(\d+) cleanup=0 irq=(\d+)$", sender_text, re.MULTILINE
        )
        if int(m[1]) in starts and int(m[2]) & 8
    ]
    ready = "[MVP RECEIVER] RX_READY rc=0" in receiver_text.splitlines()
    packets = []
    for line in receiver_text.splitlines():
        if not line.startswith("[MVP RECEIVER] RX "):
            continue
        fields = dict(re.findall(r"(\w+)=([^ ]+)", line))
        try:
            if (
                int(fields["len"]) == len(payload)
                and int(fields["rc"]) == 0
                and int(fields["restart"]) == 0
                and int(fields["irq"]) & 0x40
                and not int(fields["irq"]) & 0x20
                and " PASS bytes=" in line
                and bytes.fromhex(fields["bytes"]) == payload
            ):
                packets.append({"rssi": float(fields["rssi"]), "snr": float(fields["snr"])})
        except (ValueError, KeyError):
            continue
    return {
        "passed": bool(ready and completed and packets),
        "tx_completed": len(completed),
        "rx_matches": len(packets),
        "rssi": [p["rssi"] for p in packets],
        "snr": [p["snr"] for p in packets],
        "limit": (
            "Log structure only; physical provenance and negative-control timing "
            "require capture evidence."
        ),
    }


def parse_radio_spi_log(log_text: str, role: str) -> dict[str, Json]:
    if role not in ("GATEWAY", "RECEIVER"):
        return {
            "role": role,
            "version": None,
            "tx_disabled": False,
            "passed": False,
            "issues": ["invalid role"],
        }
    prefix = f"[{role}] "
    versions = set()
    read_errors = []
    tx_disabled = False
    mismatch = False
    malformed = False
    for line in log_text.splitlines():
        if not line.startswith(prefix):
            continue
        message = line[len(prefix) :]
        if message.startswith("RADIO_SPI_VERSION="):
            match = re.fullmatch(r"RADIO_SPI_VERSION=0x([0-9A-Fa-f]{2})", message)
            if match:
                versions.add(int(match.group(1), 16))
            else:
                malformed = True
        elif message.startswith("RADIO_SPI_READ"):
            match = re.fullmatch(r"RADIO_SPI_READ E=(-?\d+)", message)
            if match:
                read_errors.append(int(match.group(1)))
            else:
                malformed = True
        elif message == "RADIO_VERSION_MISMATCH":
            mismatch = True
        elif message == "RF_TX_DISABLED_DIAGNOSTIC":
            tx_disabled = True
    issues = []
    if len(versions) != 1:
        issues.append("missing or conflicting SPI version response")
    if read_errors:
        issues.append("SPI read failed")
    if mismatch:
        issues.append("unsupported radio version")
    if malformed:
        issues.append("malformed SPI evidence")
    if not tx_disabled:
        issues.append("diagnostic firmware did not confirm TX disabled")
    return {
        "role": role,
        "version": next(iter(versions)) if len(versions) == 1 else None,
        "tx_disabled": tx_disabled,
        "passed": not issues,
        "issues": issues,
    }


def parse_test_counts(protocol_output: bytes, unit_output: bytes) -> tuple[int | None, int | None]:
    checks = re.search(rb"PASS (\d+) checks", protocol_output)
    tests = re.search(rb"Ran (\d+) tests", unit_output)
    return (int(checks.group(1)) if checks else None, int(tests.group(1)) if tests else None)


def parse_role_log_count(output: bytes) -> int | None:
    checks = re.search(rb"PASS (\d+) role-log checks", output)
    return int(checks.group(1)) if checks else None


def parse_wrapper_check_count(output: bytes) -> int | None:
    checks = re.search(rb"PASS (\d+) radio-wrapper checks", output)
    return int(checks.group(1)) if checks else None


RF_BOOT_RE = re.compile(r"^\[(GATEWAY|RECEIVER)\] BOOT ([A-Za-z0-9_-]+) (.+)$")
RF_EVENT_RE = re.compile(
    r"^\[(GATEWAY|RECEIVER)\] ([A-Z_]+) C=([0-9A-F]{4})"
    r"(?: S=([0-9A-F]{2}))?(?: A=(\d+))?(?: RTT=(\d+))?"
    r"(?: TOA_US=(\d+))?(?: LEN=(\d+))?(?: HEX=([0-9A-F]*))?"
    r"(?: ASCII=(.*))?$"
)
EXPECTED_HELLO_PAYLOAD = b"hello world"


def parse_rf_campaign(gateway_text: str, receiver_text: str) -> dict[str, Json]:
    sources = {"GATEWAY": gateway_text, "RECEIVER": receiver_text}
    build_markers: dict[str, str] = {}
    records: list[dict[str, Json]] = []
    issues: list[str] = []
    blocked_markers = (
        "RADIO_INIT_FAILED",
        "EEPROM_READBACK_FAILED",
        "TEST_ALREADY_RUN",
        "RADIO_PROFILE_MISMATCH",
        "TEST_FAILED",
    )

    for expected_role, text in sources.items():
        for line_number, line in enumerate(text.splitlines()):
            if any(marker in line for marker in blocked_markers):
                issues.extend(marker for marker in blocked_markers if marker in line)
            boot = RF_BOOT_RE.match(line)
            if boot:
                role, build_name, _ = boot.groups()
                if role != expected_role:
                    issues.append(f"{expected_role.lower()} log has {role.lower()} boot marker")
                elif role in build_markers:
                    issues.append(f"multiple {role.lower()} boot markers")
                else:
                    build_markers[role] = build_name
                continue
            event = RF_EVENT_RE.match(line)
            if not event:
                continue
            (
                role,
                name,
                campaign_id,
                sequence,
                attempt,
                rtt,
                toa_us,
                payload_length,
                payload_hex,
                payload_ascii,
            ) = event.groups()
            if role != expected_role:
                issues.append(f"{expected_role.lower()} log has {role.lower()} event")
                continue
            records.append(
                {
                    "role": role,
                    "name": name,
                    "campaign_id": int(campaign_id, 16),
                    "sequence": int(sequence, 16) if sequence is not None else None,
                    "attempt": int(attempt) if attempt is not None else None,
                    "rtt": int(rtt) if rtt is not None else None,
                    "toa_us": int(toa_us) if toa_us is not None else None,
                    "payload_length": int(payload_length) if payload_length is not None else None,
                    "payload_hex": payload_hex,
                    "payload_ascii": payload_ascii,
                    "line": line_number,
                }
            )

    if build_markers.get("GATEWAY") != "sender_hello":
        issues.append("missing or wrong sender_hello build marker")
    if build_markers.get("RECEIVER") != "receiver":
        issues.append("missing or wrong receiver build marker")

    campaign_ids = {record["campaign_id"] for record in records}
    if len(campaign_ids) > 1:
        issues.append("multiple campaign IDs")
    campaign_id = next(iter(campaign_ids)) if len(campaign_ids) == 1 else None

    def matching(
        role: str, name: str, sequence: int | None = None
    ) -> list[dict[str, Json]]:
        return [
            record
            for record in records
            if record["role"] == role
            and record["name"] == name
            and record["campaign_id"] == campaign_id
            and (sequence is None or record["sequence"] == sequence)
        ]

    expected_payload_hex = EXPECTED_HELLO_PAYLOAD.hex().upper()

    def payload_bytes_match(record: dict[str, object]) -> bool:
        return (
            record["payload_length"] == len(EXPECTED_HELLO_PAYLOAD)
            and record["payload_hex"] == expected_payload_hex
            and record["payload_ascii"] == EXPECTED_HELLO_PAYLOAD.decode("ascii")
        )

    sender_payload_records = matching("GATEWAY", "DATA_PAYLOAD", 1)
    receiver_payload_records = matching("RECEIVER", "PAYLOAD_BYTES", 1)
    sender_payload_bytes_match = bool(sender_payload_records) and all(
        payload_bytes_match(record) for record in sender_payload_records
    )
    receiver_payload_bytes_match = bool(receiver_payload_records) and all(
        payload_bytes_match(record) for record in receiver_payload_records
    )
    if not sender_payload_bytes_match:
        issues.append("sender sequence-1 payload mismatch")
    if not receiver_payload_bytes_match:
        issues.append("receiver sequence-1 payload mismatch")

    payload_validated_sequences = [
        sequence for sequence in range(1, 21) if matching("RECEIVER", "PAYLOAD_MATCH", sequence)
    ]
    receiver_data_sequences = {
        record["sequence"]
        for event_name in ("DATA_RX", "DATA_DUP")
        for record in matching("RECEIVER", event_name)
        if record["sequence"] is not None
    }
    payload_unverified_sequences = sorted(
        receiver_data_sequences - set(payload_validated_sequences)
    )
    issues.extend(
        f"receiver payload unverified for sequence {sequence:02X}"
        for sequence in payload_unverified_sequences
    )

    delivered = []
    for sequence in range(1, 21):
        gateway_tx = matching("GATEWAY", "DATA_TX", sequence)
        gateway_done = matching("GATEWAY", "DATA_DONE", sequence)
        accepted_data = matching("RECEIVER", "DATA_RX", sequence) or matching(
            "RECEIVER", "DATA_DUP", sequence
        )
        payload_match = matching("RECEIVER", "PAYLOAD_MATCH", sequence)
        ack_started = matching("RECEIVER", "ACK_TX", sequence)
        ack_done = matching("RECEIVER", "ACK_DONE", sequence)
        ack_received = matching("GATEWAY", "ACK_RX", sequence)
        if all(
            (
                gateway_tx,
                gateway_done,
                accepted_data,
                payload_match,
                ack_started,
                ack_done,
                ack_received,
            )
        ):
            delivered.append(sequence)

    preflight_events = matching("GATEWAY", "PREFLIGHT_OK", 1)
    preflight_complete = (
        1 in delivered
        and bool(preflight_events)
        and sender_payload_bytes_match
        and receiver_payload_bytes_match
    )
    continue_events = matching("GATEWAY", "CAMPAIGN_CONTINUE")
    continued = bool(
        preflight_events
        and continue_events
        and continue_events[0]["line"] > preflight_events[0]["line"]
    )
    campaign_complete = bool(matching("GATEWAY", "TEST_COMPLETED"))
    missing = [sequence for sequence in range(1, 21) if sequence not in delivered]

    data_tx = matching("GATEWAY", "DATA_TX")
    ack_tx = matching("RECEIVER", "ACK_TX")
    if any(record["toa_us"] is None for record in data_tx + ack_tx):
        issues.append("missing radio airtime estimate")

    tx_attempts: dict[tuple[int, int], set[int]] = {}
    for record in matching("GATEWAY", "DATA_TX"):
        sequence = record["sequence"]
        attempt = record["attempt"]
        if sequence is not None and attempt is not None:
            tx_attempts.setdefault((record["campaign_id"], sequence), set()).add(attempt)
    retry_count = sum(max(0, len(attempts) - 1) for attempts in tx_attempts.values())
    ack_rx = matching("GATEWAY", "ACK_RX")
    latencies = [
        record["rtt"]
        for record in ack_rx
        if record["sequence"] in delivered and record["rtt"] is not None
    ]
    latency_summary = (
        {
            "min": min(latencies),
            "max": max(latencies),
            "average": sum(latencies) / len(latencies),
        }
        if latencies
        else None
    )

    issues = list(dict.fromkeys(issues))
    passed = (
        preflight_complete
        and continued
        and campaign_complete
        and delivered == list(range(1, 21))
        and not issues
    )
    return {
        "origin": "MOCK_LOG",  # Parsing text alone never establishes physical provenance.
        "campaign_id": campaign_id,
        "build_markers": {
            "gateway": build_markers.get("GATEWAY"),
            "receiver": build_markers.get("RECEIVER"),
        },
        "preflight_complete": preflight_complete,
        "sender_payload_bytes_match": sender_payload_bytes_match,
        "receiver_payload_bytes_match": receiver_payload_bytes_match,
        "payload_validated_sequences": payload_validated_sequences,
        "payload_unverified_sequences": payload_unverified_sequences,
        "continued": continued,
        "campaign_complete": campaign_complete,
        "passed": passed,
        "delivery_sequences": delivered,
        "missing_sequences": missing,
        "data_tx_started": len(matching("GATEWAY", "DATA_TX")),
        "data_tx_completed": len(matching("GATEWAY", "DATA_DONE")),
        "receiver_data_events": (
            len(matching("RECEIVER", "DATA_RX")) + len(matching("RECEIVER", "DATA_DUP"))
        ),
        "receiver_duplicates": len(matching("RECEIVER", "DATA_DUP")),
        "ack_tx_started": len(matching("RECEIVER", "ACK_TX")),
        "ack_tx_completed": len(matching("RECEIVER", "ACK_DONE")),
        "ack_rx": len(ack_rx),
        "retry_count": retry_count,
        "ack_timeouts": len(matching("GATEWAY", "ACK_TIMEOUT")),
        "data_start_failures": len(matching("GATEWAY", "DATA_START_FAILED")),
        "data_tx_timeouts": len(matching("GATEWAY", "DATA_TX_TIMEOUT")),
        "ack_tx_start_failures": len(matching("RECEIVER", "ACK_START_FAILED")),
        "ack_tx_timeouts": len(matching("RECEIVER", "ACK_TX_TIMEOUT")),
        "airtime_estimates_us": {
            "gateway": sum(record["toa_us"] or 0 for record in data_tx),
            "receiver": sum(record["toa_us"] or 0 for record in ack_tx),
        },
        "latency_ms": latency_summary,
        "issues": issues,
    }


def single_packet_evidence_passed(evidence: dict[str, object]) -> bool:
    return bool(
        evidence.get("preflight_complete")
        and not evidence.get("issues")
        and evidence.get("data_tx_started") == 1
        and evidence.get("data_tx_completed") == 1
        and evidence.get("receiver_data_events") == 1
        and evidence.get("ack_tx_started") == 1
        and evidence.get("ack_tx_completed") == 1
        and evidence.get("ack_rx") == 1
        and evidence.get("retry_count") == 0
    )


def unresolved_adapter_paths(results: list[tuple[str, int]]) -> list[str]:
    return [f"{role} adapter path" for role, code in results if code != 0]


def unavailable_ports(results: list[tuple[str, int]]) -> list[str]:
    return [role for role, code in results if code != 1]


def check_port_owners(proof: ProofRun, stage: str) -> list[str]:
    results = [
        (role, proof.command(f"{stage}-{role}-owners", ["fuser", port])[0])
        for role, port in PORTS.items()
    ]
    return unavailable_ports(results)


def identify_targets(proof: ProofRun, args: argparse.Namespace, effective_config: str = "") -> int:
    args.target_identification_attempted = True
    args.boot_layout_verified = False
    no_meter = getattr(args, "no_meter_mode", False)
    if not no_meter and (not args.physical_mapping_verified or not args.power_verified):
        missing = []
        if not args.physical_mapping_verified:
            missing.append("physical board mapping")
        if not args.power_verified:
            missing.append("power/UPDI wiring conditions")
        proof.note(
            "target-identification.log",
            "BLOCKED: " + ", ".join(missing) + "; no serial ports opened.\n",
        )
        return 2

    evidence_errors = physical_readiness_errors(args)
    if evidence_errors:
        proof.note(
            "target-identification.log",
            "BLOCKED: " + "; ".join(evidence_errors) + "; no serial ports opened.\n",
        )
        return 2

    path_results = [
        (role, proof.command(f"identify-{role}-path", ["readlink", "-e", port])[0])
        for role, port in PORTS.items()
    ]
    unavailable_paths = unresolved_adapter_paths(path_results)
    unavailable_owners = check_port_owners(proof, "identify-preflight")
    if unavailable_paths or unavailable_owners:
        blockers = unavailable_paths + [
            f"{role} UPDI port occupied or owner check failed" for role in unavailable_owners
        ]
        proof.note(
            "target-identification.log",
            "BLOCKED: " + ", ".join(blockers) + "; no serial ports opened.\n",
        )
        return 2

    core_dir = Path(os.environ.get("PLATFORMIO_CORE_DIR", str(Path.home() / ".platformio")))
    avrdude = core_dir / "packages" / "tool-avrdude" / "avrdude"
    avrdude_conf = core_dir / "packages" / "tool-avrdude" / "avrdude.conf"
    expected_fuses = {role: target_fuses(effective_config, role) for role in PORTS}
    if (
        any(values is None for values in expected_fuses.values())
        or not avrdude.is_file()
        or not avrdude_conf.is_file()
    ):
        proof.note(
            "target-identification.log",
            "BLOCKED: target-specific BOOT geometry or PlatformIO avrdude is unavailable; "
            "no serial ports opened.\n",
        )
        return 2

    all_ok = True
    for role, port in PORTS.items():
        sib_code, sib_out, _ = proof.command(
            f"target-{role}-sib",
            [
                "uv",
                "run",
                "--no-project",
                "python",
                "-u",
                "third_party/upditerm/upditerm.py",
                "-i",
                port,
                "38400",
            ],
            20,
        )
        if sib_code != 0 or not sib_out.strip():
            all_ok = False
            continue

        bootsize_path = proof.run_dir / f"target-{role}-bootsize.bin"
        codesize_path = proof.run_dir / f"target-{role}-codesize.bin"
        bodcfg_path = proof.run_dir / f"target-{role}-bodcfg.bin"
        signature_path = proof.run_dir / f"target-{role}-signature.bin"
        serial_path = proof.run_dir / f"target-{role}-serial.bin"
        avrdude_args = [
            str(avrdude),
            "-N",
            "-p",
            "avr128da28",
            "-C",
            str(avrdude_conf),
            "-c",
            "serialupdi",
            "-P",
            port,
            "-b",
            "115200",
            "-D",
            "-U",
            f"bootsize:r:{bootsize_path}:r",
            "-U",
            f"codesize:r:{codesize_path}:r",
            "-U",
            f"bodcfg:r:{bodcfg_path}:r",
            "-U",
            f"signature:r:{signature_path}:r",
            "-U",
            f"sernum:r:{serial_path}:r",
        ]
        fuse_code, _, _ = proof.command(f"target-{role}-fuse-read", avrdude_args, 20)
        if fuse_code != 0:
            all_ok = False
            continue
        try:
            observed = {
                "bootsize": bootsize_path.read_bytes()[0],
                "codesize": codesize_path.read_bytes()[0],
                "bodcfg": bodcfg_path.read_bytes()[0],
            }
        except (OSError, IndexError):
            observed = None
        (proof.run_dir / f"target-{role}-layout.json").write_text(
            json.dumps({"expected": expected_fuses[role], "observed": observed}, indent=2) + "\n"
        )
        if not boot_fuses_match(observed, expected_fuses[role]):
            all_ok = False
        try:
            identity = json.loads((ROOT / "config/current_hardware.json").read_text())[role]
            expected_serial = bytes.fromhex(identity["device_serial_hex"])
            if identity["port_path"] != port:
                all_ok = False
            if (
                signature_path.read_bytes() != bytes.fromhex("1e970a")
                or serial_path.read_bytes() != expected_serial
            ):
                all_ok = False
        except (OSError, ValueError, KeyError):
            all_ok = False

    ports_after = check_port_owners(proof, "identify-postflight")
    all_ok = all_ok and not ports_after
    args.boot_layout_verified = all_ok
    if all_ok:
        proof.note(
            "target-identification.log",
            "PASS: both UPDI targets match AVR128DA28 and their configured BOOT/APPCODE/BOD "
            "fuses; no writes performed.\n",
        )
        return 0
    proof.note(
        "target-identification.log",
        "BLOCKED: SIB/MCU/BOOTSIZE/CODESIZE/BOD verification failed; no writes performed.\n",
    )
    return 2


def effective_project_sections(config_text: str) -> dict[str, dict[str, object]] | None:
    try:
        configuration = json.loads(config_text)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(configuration, list):
        return None
    sections = {}
    for entry in configuration:
        if (
            not isinstance(entry, list)
            or len(entry) != 2
            or not isinstance(entry[0], str)
            or not isinstance(entry[1], list)
        ):
            return None
        values = {}
        for pair in entry[1]:
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or not isinstance(pair[0], str)
                or pair[0] in values
            ):
                return None
            values[pair[0]] = pair[1]
        if entry[0] in sections:
            return None
        sections[entry[0]] = values
    return sections


def build_flag_defines(
    sections: dict[str, dict[str, object]], environment: str, name: str
) -> list[str] | None:
    flags = sections.get(f"env:{environment}", {}).get("build_flags")
    if not isinstance(flags, list) or any(not isinstance(flag, str) for flag in flags):
        return None
    values = []
    index = 0
    while index < len(flags):
        flag = flags[index]
        index += 1
        if flag == "-D":
            if index >= len(flags):
                continue
            definition = flags[index]
            index += 1
        elif flag.startswith("-D"):
            definition = flag[2:]
        else:
            continue
        key, separator, value = definition.partition("=")
        if key == name:
            values.append(value if separator else "1")
    return values


PROFILE_MACROS = (
    "HELLO_RF_FREQUENCY_MHZ",
    "HELLO_RF_TX_POWER_DBM",
    "HELLO_RF_LONG_RANGE",
    "HELLO_RF_SPREADING_FACTOR",
    "HELLO_RF_BANDWIDTH_KHZ",
    "HELLO_RF_CODING_RATE",
    "HELLO_RF_SYNC_WORD",
    "HELLO_RF_PREAMBLE_SYMBOLS",
    "HELLO_RF_CRC_ENABLED",
    "HELLO_RF_EXPLICIT_HEADER",
    "HELLO_RF_IQ_INVERTED",
    "HELLO_RF_CURRENT_LIMIT_MA",
    "HELLO_RF_AUTOMATIC_GAIN",
)


def shared_rf_profile(config_text: str) -> dict[str, object] | None:
    sections = effective_project_sections(config_text)
    if sections is None or any(
        build_flag_defines(sections, environment, "LORA_SSOT_GENERATED") != ["1"]
        for environment in ENVIRONMENTS
    ):
        return None
    if any(
        build_flag_defines(sections, environment, name) != []
        for environment in ENVIRONMENTS
        for name in PROFILE_MACROS
    ):
        return None
    try:
        sys.path.insert(0, str(ROOT / "tools/config"))
        from generate_lora_config import generate  # type: ignore[import-not-found]

        generate(check=True)
        manifest = json.loads((ROOT / "generated/lora_manifest.json").read_text())
        return dict(manifest["shared"]["radio"])
    except (KeyError, OSError, ValueError):
        return None


def valid_rf_profile_config(config_text: str) -> bool:
    sections = effective_project_sections(config_text)
    return (
        sections is not None
        and shared_rf_profile(config_text) is not None
        and build_flag_defines(sections, "sender_hello", "HELLO_TEST_MODE") == ["1"]
        and build_flag_defines(sections, "sender_hello", "HELLO_RAM_ONLY_TEST") == ["1"]
    )


def radio_profile_compile_flags(config_text: str) -> list[str] | None:
    sections = effective_project_sections(config_text)
    if sections is None or not valid_rf_profile_config(config_text):
        return None
    try:
        manifest = json.loads((ROOT / "generated/lora_manifest.json").read_text())
        role = manifest["environments"]["sender_hello"]["role"]
        if role not in ("sender", "receiver"):
            return None
        return [f"-DLORA_ROLE_{role.upper()}=1"]
    except (KeyError, OSError, ValueError):
        return None


def rf_spi_diagnostic_config(config_text: str) -> bool:
    sections = effective_project_sections(config_text)
    if sections is None or not valid_rf_profile_config(config_text):
        return False
    if (
        build_flag_defines(sections, "sender_hello", "HELLO_RF_DIAGNOSTIC_ONLY") != []
        or build_flag_defines(sections, "receiver", "HELLO_RF_DIAGNOSTIC_ONLY") != []
    ):
        return False
    return (
        build_flag_defines(sections, "sender_hello_spi", "HELLO_RF_DIAGNOSTIC_ONLY") == ["1"]
        and build_flag_defines(sections, "receiver_spi", "HELLO_RF_DIAGNOSTIC_ONLY") == ["1"]
        and build_flag_defines(sections, "sender_hello_spi", "HELLO_TEST_MODE") == ["1"]
        and build_flag_defines(sections, "sender_hello_spi", "HELLO_RAM_ONLY_TEST") == ["1"]
    )


def upload_config_preserves_flash(config_text: str) -> bool:
    effective = effective_project_sections(config_text)
    if effective is not None:
        for environment in ENVIRONMENTS:
            settings = effective.get(f"env:{environment}", {})
            flags = settings.get("upload_flags")
            if not isinstance(flags, list) or any(not isinstance(flag, str) for flag in flags):
                return False
            if (
                settings.get("upload_protocol") != "serialupdi"
                or "-D" not in flags
                or "-e" in flags
                or any(flag == "-U" or flag.startswith("-U") for flag in flags)
            ):
                return False
        return True

    sections = re.findall(r"(?ms)^\[([^\]]+)\]\s*(.*?)(?=^\[|\Z)", config_text)
    section_map = dict(sections)

    def configured_upload_flags(body: str) -> str | None:
        match = re.search(r"(?m)^\s*upload_flags\s*=\s*(.*?)\s*$", body)
        return match.group(1) if match else None

    base_flags = configured_upload_flags(section_map.get("env", ""))
    if base_flags is None:
        return False
    for environment in ENVIRONMENTS:
        value = configured_upload_flags(section_map.get(f"env:{environment}", ""))
        if value is not None:
            value = value.replace("${env.upload_flags}", base_flags)
        else:
            value = base_flags
        flags = shlex.split(value)
        if (
            "-D" not in flags
            or "-e" in flags
            or any(flag == "-U" or flag.startswith("-U") for flag in flags)
        ):
            return False
    return True


def upload_ports_match(config_text: str) -> bool:
    sections = effective_project_sections(config_text)
    if sections is None:
        return False
    expected = {
        "sender": PORTS["gateway"],
        "sender_hello": PORTS["gateway"],
        "receiver": PORTS["receiver"],
        "sender_hello_spi": PORTS["gateway"],
        "receiver_spi": PORTS["receiver"],
    }
    return all(
        sections.get(f"env:{environment}", {}).get("upload_port") == port
        for environment, port in expected.items()
    )


def parse_ihex_range(data: bytes) -> dict[str, int]:
    base = 0
    lowest: int | None = None
    highest_exclusive = 0
    data_bytes = 0
    eof = False
    for raw_line in data.splitlines():
        if not raw_line:
            continue
        if eof or not raw_line.startswith(b":"):
            msg = "invalid Intel HEX record order or prefix"
            raise ValueError(msg)
        try:
            record = bytes.fromhex(raw_line[1:].decode("ascii"))
        except (UnicodeDecodeError, ValueError) as exc:
            msg = "invalid Intel HEX encoding"
            raise ValueError(msg) from exc
        if len(record) < 5 or len(record) != record[0] + 5 or sum(record) & 0xFF:
            msg = "invalid Intel HEX length or checksum"
            raise ValueError(msg)
        length = record[0]
        address = int.from_bytes(record[1:3], "big")
        record_type = record[3]
        payload = record[4:-1]
        if record_type == 0:
            if length:
                start = base + address
                lowest = start if lowest is None else min(lowest, start)
                highest_exclusive = max(highest_exclusive, start + length)
                data_bytes += length
        elif record_type == 1 and length == 0:
            eof = True
        elif record_type == 2 and length == 2:
            base = int.from_bytes(payload, "big") << 4
        elif record_type == 4 and length == 2:
            base = int.from_bytes(payload, "big") << 16
        elif record_type in (3, 5) and length == 4:
            continue
        else:
            msg = f"unsupported Intel HEX record type {record_type}"
            raise ValueError(msg)
    if not eof or lowest is None:
        msg = "Intel HEX is missing data or EOF record"
        raise ValueError(msg)
    return {"start": lowest, "end_exclusive": highest_exclusive, "data_bytes": data_bytes}


def _config_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def target_fuses(config_text: str, role: str) -> dict[str, int] | None:
    sections = effective_project_sections(config_text)
    layout = sections.get("target_layout") if sections else None
    if role not in PORTS or not layout:
        return None
    values = {
        name: _config_int(layout.get(f"{role}_{name}"))
        for name in ("bootsize", "codesize", "bodcfg")
    }
    return (
        cast("dict[str, int]", values)
        if all(value is not None for value in values.values())
        else None
    )


def application_bounds_for_environment(
    config_text: str,
    environment: str,
) -> tuple[int, int] | None:
    sections = effective_project_sections(config_text)
    role = {
        "sender": "gateway",
        "sender_hello": "gateway",
        "sender_hello_spi": "gateway",
        "receiver": "receiver",
        "receiver_spi": "receiver",
        "sender_mvp": "gateway",
        "receiver_mvp": "receiver",
        "sender_arq": "gateway",
        "receiver_arq": "receiver",
        "sender_arq_test": "gateway",
        "receiver_arq_test": "receiver",
        "sender_arq_radio_only": "gateway",
        "receiver_arq_radio_only": "receiver",
        "sender_arq_radio_only_reverse": "gateway",
        "receiver_arq_radio_only_reverse": "receiver",
        "sender_reverse_raw": "gateway",
        "receiver_reverse_raw": "receiver",
    }.get(environment)
    if not sections or role is None:
        return None
    layout = sections.get("target_layout", {})
    geometry = sections.get("flash_geometry", {})
    expected_fuses = target_fuses(config_text, role)
    app_start = _config_int(layout.get(f"{role}_app_start"))
    env_start = _config_int(
        sections.get(f"env:{environment}", {}).get("board_build.text_section_start")
    )
    app_end = _config_int(geometry.get("application_end"))
    flash_end = _config_int(geometry.get("total_bytes"))
    if (
        not expected_fuses
        or app_start is None
        or env_start is None
        or app_end is None
        or flash_end is None
    ):
        return None
    # These targets use a full-BOOT Gateway and an APPCODE-only Receiver.
    if expected_fuses["codesize"] != 0:
        return None
    fuse_start = expected_fuses["bootsize"] * 512
    if app_start != fuse_start or env_start != fuse_start or not fuse_start < app_end <= flash_end:
        return None
    return fuse_start, app_end


def image_fits_application(
    image_range: dict[str, int] | None, bounds: tuple[int, int] | None
) -> bool:
    return bool(
        image_range
        and bounds
        and image_range["start"] == bounds[0]
        and image_range["end_exclusive"] <= bounds[1]
    )


def boot_fuses_match(actual: dict[str, int] | None, expected: dict[str, int] | None) -> bool:
    return bool(
        actual
        and expected
        and all(actual.get(name) == expected[name] for name in ("bootsize", "codesize", "bodcfg"))
    )


def application_layout_verified(environments: tuple[str, ...], effective_config: str) -> bool:
    for env in environments:
        bounds = application_bounds_for_environment(effective_config, env)
        if bounds is None:
            return False
        hex_path = ROOT / ".pio" / "build" / env / "firmware.hex"
        try:
            image_range = parse_ihex_range(hex_path.read_bytes())
        except (OSError, ValueError):
            return False
        if not image_fits_application(image_range, bounds):
            return False
    return True


class ProofRun:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=False)

    def command(
        self, name: str, argv: list[str], timeout: int | None = None
    ) -> tuple[int, bytes, bytes]:
        try:
            result = subprocess.run(
                argv, cwd=ROOT, capture_output=True, timeout=timeout, check=False
            )
            code = result.returncode
            stdout, stderr = result.stdout, result.stderr
        except subprocess.TimeoutExpired as exc:
            code = 124
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
        except OSError as exc:
            code = 127
            stdout = b""
            stderr = f"{type(exc).__name__}: {exc}\n".encode()

        (self.run_dir / f"{name}.stdout.log").write_bytes(stdout)
        (self.run_dir / f"{name}.stderr.log").write_bytes(stderr)
        print(f"{name}: exit {code}")
        if stdout:
            print(stdout.decode(errors="replace"), end="")
        if stderr:
            print(stderr.decode(errors="replace"), end="", file=sys.stderr)
        return code, stdout, stderr

    def note(self, name: str, content: str) -> None:
        data = content.encode()
        (self.run_dir / name).write_bytes(data)
        print(content, end="")


def new_run() -> ProofRun:
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    suffix = 0
    run_dir = ARTIFACTS / run_id
    while run_dir.exists():
        suffix += 1
        run_dir = ARTIFACTS / f"{run_id}-{suffix}"
    return ProofRun(run_dir)


def host_tests(proof: ProofRun, effective_config: str) -> int:
    profile_flags = radio_profile_compile_flags(effective_config)
    if profile_flags is None:
        proof.note("host-tests.log", "FAIL: effective shared RF profile is invalid.\n")
        return 1
    with tempfile.TemporaryDirectory(prefix="lora-hello-") as temp_dir:
        role_binary = str(Path(temp_dir) / "role_log_test")
        role_compile_code, _, _ = proof.command(
            "role-log-compile",
            [
                "g++",
                "-std=c++11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Istable_lib/updi_uart/src",
                "tests/role_log_test.cpp",
                "-o",
                role_binary,
            ],
        )
        if role_compile_code != 0:
            return 1
        role_test_code, role_test_out, _ = proof.command("role-log-tests", [role_binary])
        if role_test_code != 0:
            return 1
        wrapper_binary = str(Path(temp_dir) / "lora_wrapper_test")
        wrapper_compile_code, _, _ = proof.command(
            "radio-wrapper-compile",
            [
                "g++",
                "-std=c++11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Itests/radio_stub",
                "-Istable_lib/lora",
                "-Istable_lib/shared",
                "-Isrc",
                *profile_flags,
                "tests/lora_wrapper_test.cpp",
                "src/features/radio_link/radio_link.cpp",
                "-o",
                wrapper_binary,
            ],
        )
        if wrapper_compile_code != 0:
            return 1
        wrapper_test_code, wrapper_test_out, _ = proof.command(
            "radio-wrapper-tests", [wrapper_binary]
        )
        if wrapper_test_code != 0:
            return 1
        diagnostic_binary = str(Path(temp_dir) / "radio_diagnostic_test")
        diagnostic_compile, _, _ = proof.command(
            "diagnostic-protection-compile",
            [
                "g++",
                "-std=c++11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Itests/radio_stub",
                "-Istable_lib/lora",
                "-Istable_lib/shared",
                "-Isrc",
                *profile_flags,
                "-DHELLO_RF_DIAGNOSTIC_ONLY=1",
                "tests/radio_diagnostic_test.cpp",
                "src/features/radio_link/radio_link.cpp",
                "-o",
                diagnostic_binary,
            ],
        )
        if diagnostic_compile != 0:
            return 1
        diagnostic_code, _, _ = proof.command("diagnostic-protection-tests", [diagnostic_binary])
        if diagnostic_code != 0:
            return 1
        unit_code, unit_out, unit_err = proof.command(
            "host-gate-tests",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
            ],
        )
        _, unit_count = parse_test_counts(b"", unit_out + unit_err)
        role_checks = parse_role_log_count(role_test_out)
        wrapper_checks = parse_wrapper_check_count(wrapper_test_out)
        measurements = {
            "origin": "HOST_UNIT_TEST",
            "role_log_checks": role_checks,
            "radio_wrapper_checks": wrapper_checks,
            "runner_unit_tests": unit_count,
            "diagnostic_send_protection": diagnostic_code == 0,
        }
        (proof.run_dir / "host-measurements.json").write_text(
            json.dumps(measurements, indent=2) + "\n"
        )
        return 0 if unit_code == 0 and all(measurements.values()) else 1


def firmware_measurement(env: str, output: bytes) -> dict[str, object]:
    build_dir = ROOT / ".pio" / "build" / env
    manifest: Json = json.loads((ROOT / "generated/lora_manifest.json").read_text())
    result: dict[str, Json] = {
        "environment": env,
        "origin": "FIRMWARE_BUILD",
        "build_exit_code": 0,
        "clean_build": True,
        "shared_fingerprint": manifest["shared_fingerprint"],
        "build_id": manifest["environments"][env]["build_id"],
    }
    for extension in ("hex", "elf"):
        path = build_dir / f"firmware.{extension}"
        if path.is_file():
            data = path.read_bytes()
            file_result: dict[str, Json] = {
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            if extension == "hex":
                try:
                    file_result["address_range"] = parse_ihex_range(data)
                    from device_detection.firmware_identity import normalize_ihex_region  # type: ignore[import-not-found]

                    base = file_result["address_range"]["start"]
                    entry = normalize_ihex_region(data.decode("ascii"), base, base + 4)
                    word = int.from_bytes(entry[:2], "little")
                    target = None
                    if word & 0xF000 == 0xC000:
                        offset = word & 0xFFF
                        if offset & 0x800:
                            offset -= 0x1000
                        target = base + 2 + 2 * offset
                    elif word & 0xFE0E == 0x940C:
                        target = 2 * (
                            ((word & 0x1F0) << 13)
                            | ((word & 1) << 16)
                            | int.from_bytes(entry[2:], "little")
                        )
                    file_result["reset_vector_bytes"] = entry.hex()
                    file_result["reset_target"] = target
                    file_result["reset_target_inside_image"] = (
                        target is not None
                        and base <= target < file_result["address_range"]["end_exclusive"]
                    )
                except ValueError as exc:
                    file_result["address_range_error"] = str(exc)
            result[extension] = file_result
    text = output.decode(errors="replace")
    for kind in ("RAM", "Flash"):
        match = re.search(
            rf"{kind}:\s*(?:\[[^\]]*\]\s*)?([\d.]+)%\s*"
            rf"\(used\s+(\d+)\s+bytes\s+from\s+(\d+)\s+bytes\)",
            text,
        )
        if match:
            result[kind.lower()] = {
                "percent": float(match.group(1)),
                "used_bytes": int(match.group(2)),
                "total_bytes": int(match.group(3)),
            }
    return result


def clean_builds(proof: ProofRun, effective_config: str = "") -> int:
    measurements: list[dict[str, Json]] = []
    for env in ENVIRONMENTS:
        clean_code, _, _ = proof.command(
            f"{env}-clean",
            [
                "pio",
                "run",
                "-e",
                env,
                "-t",
                "clean",
            ],
        )
        if clean_code != 0:
            return 1
        build_code, stdout, stderr = proof.command(
            f"{env}-build",
            [
                "pio",
                "run",
                "-e",
                env,
            ],
        )
        if build_code != 0:
            return 1
        measurements.append(firmware_measurement(env, stdout + stderr))
    for env, measurement in zip(ENVIRONMENTS, measurements, strict=False):
        hex_info = measurement.get("hex", {})
        address_range = hex_info.get("address_range")
        measurement["application_layout_safe"] = image_fits_application(
            address_range, application_bounds_for_environment(effective_config, env)
        )
        measurement["reset_vector_safe"] = hex_info.get("reset_target_inside_image", False)
    layout = (
        "SAFE: all HEX files start at their target fuse boundary and fit the application region.\n"
        if all(item["application_layout_safe"] for item in measurements)
        else (
            "BLOCKED: HEX range does not start at its target fuse boundary, exceeds the "
            "application region, or target geometry is unavailable.\n"
        )
    )
    proof.note("application-layout.log", layout)
    (proof.run_dir / "firmware-measurements.json").write_text(
        json.dumps(measurements, indent=2) + "\n"
    )
    return (
        0
        if all(
            item["application_layout_safe"] and item["reset_vector_safe"] for item in measurements
        )
        else 1
    )


def capture_usb_topology(proof: ProofRun) -> None:
    commands = [
        ("usb-by-path-listing", ["ls", "-l", "/dev/serial/by-path/"]),
        ("usb-gateway-path", ["readlink", "-e", PORTS["gateway"]]),
        ("usb-receiver-path", ["readlink", "-e", PORTS["receiver"]]),
        ("usb-ttyUSB0-udev", ["udevadm", "info", "--query=property", "--name=/dev/ttyUSB0"]),
        ("usb-ttyUSB1-udev", ["udevadm", "info", "--query=property", "--name=/dev/ttyUSB1"]),
        ("usb-tree", ["lsusb", "-t"]),
        ("pio-device-list", ["pio", "device", "list"]),
        ("usb-port-owners", ["fuser", "-v", "/dev/ttyUSB0", "/dev/ttyUSB1"]),
        (
            "usb-role-scan",
            ["uv", "run", "--no-project", "python", "tools/detect_devices.py", "--scan", "--json"],
        ),
    ]
    for name, argv in commands:
        proof.command(name, argv)


def project_configuration(proof: ProofRun) -> tuple[int, str]:
    code, stdout, _ = proof.command(
        "pio-project-config", ["pio", "project", "config", "--json-output"]
    )
    if code != 0:
        return 1, ""
    capture_usb_topology(proof)
    return 0, stdout.decode(errors="replace")


def read_only_preflight(
    proof: ProofRun, args: argparse.Namespace, profile_ok: bool, effective_config: str
) -> int:
    path_results = [
        (role, proof.command(f"preflight-{role}-path", ["readlink", "-e", port])[0])
        for role, port in PORTS.items()
    ]
    missing = unresolved_adapter_paths(path_results)
    unavailable = check_port_owners(proof, "preflight")
    missing.extend(f"{role} UPDI port occupied or owner check failed" for role in unavailable)
    missing.extend(physical_readiness_errors(args))
    if not profile_ok:
        missing.append("valid shared SF7 profile configuration")
    if not application_layout_verified(("sender_hello", "receiver"), effective_config):
        missing.append("firmware HEX not confined to the target executable region")
    if not args.boot_layout_verified:
        missing.append("BOOTSIZE/CODESIZE/BODCFG fuse verification")
    if not upload_config_preserves_flash(effective_config):
        missing.append("serialupdi upload preservation flags")
    if not upload_ports_match(effective_config):
        missing.append("effective UPDI port mapping")
    status = "READY" if not missing else "BLOCKED: " + ", ".join(missing)
    proof.note("preflight.log", status + "\nNo serial ports opened.\n")
    return 0 if not missing else 2


def physical_readiness_errors(
    args: argparse.Namespace, require_rf: bool = False
) -> list[str]:
    errors = []
    if getattr(args, "physical_mapping_verified", False) is not True:
        errors.append("physical board mapping")
    if getattr(args, "power_verified", False) is not True:
        errors.append("safe power, common ground, UPDI wiring and CP2102 backfeed conditions")
    if require_rf and getattr(args, "rf_hardware_verified", False) is not True:
        errors.append("radio/module/antenna compatibility and safe RF power")
    return errors


def receiver_boot_handoff_supported(
    proof: ProofRun,
    args: argparse.Namespace | None = None,
    effective_config: str | None = None,
) -> bool:
    receipt = getattr(args, "receiver_boot_evidence", None)
    if receipt is not None:
        if args is None:
            return False
        if not getattr(args, "boot_layout_verified", False) or physical_readiness_errors(args):
            return False
        try:
            from receiver_boot import verify_live_receipt  # type: ignore[import-not-found]

            return bool(verify_live_receipt(proof, receipt))
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            return False
    if getattr(args, "boot_layout_verified", False) and effective_config is not None:
        bounds = application_bounds_for_environment(effective_config, "receiver")
        fuses = target_fuses(effective_config, "receiver")
        if bounds is not None and bounds[0] == 0 and fuses and fuses["bootsize"] == 0:
            proof.note(
                "receiver-boot-audit.json",
                "PASS: verified BOOTSIZE=0 and application entry at 0x0000; "
                "no boot handoff required.\n",
            )
            return True
    from boot_analysis import analyze  # type: ignore[import-not-found]

    backup = ARTIFACTS / "20261106T104722Z-target-backup/receiver-candidate-backup-flash.bin"
    objdump = Path.home() / ".platformio/packages/toolchain-atmelavr/bin/avr-objdump"
    try:
        output = subprocess.check_output(
            [str(objdump), "-D", "-b", "binary", "-m", "avr", str(backup)], text=True
        )
        audit = analyze(output, 0x5800)
        audit["backup_sha256"] = hashlib.sha256(backup.read_bytes()).hexdigest()
        proof.note("receiver-boot-audit.json", json.dumps(audit, indent=2) + "\n")
        # A direct transfer alone is not enough to prove a bootloader's validation policy.
        # This saved image has NO transfer, so it must never authorize a replacement app.
        if audit["verdict"] != "TRANSFER_PRESENT":
            proof.note(
                "receiver-boot-blocker.log",
                "BLOCKED: saved Receiver reset path does not establish application entry at "
                "0x5800; boot handoff/recovery must be resolved before writing.\n",
            )
            return False
        return audit["application_transfers"] == [0x5800] and not audit["unresolved"]
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def prepare_receiver_boot(proof: ProofRun) -> int:
    from receiver_boot import prepare

    try:
        return cast("int", prepare(proof))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        proof.note("receiver-boot-prepare.log", f"FAIL: {error}; no hardware accessed.\n")
        return 1


def program_receiver_boot(
    proof: ProofRun, args: argparse.Namespace, restore: bool = False
) -> int:
    from receiver_boot import install

    if args.stage != ("receiver-boot-restore" if restore else "receiver-boot-install"):
        proof.note(
            "receiver-boot-install.log",
            "BLOCKED: boot writes require the explicitly selected boot stage.\n",
        )
        return 2
    try:
        return cast("int", install(proof, args, restore=restore))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        proof.note(
            "receiver-boot-install.log", f"FAIL: {error}; no automatic retry or chip erase.\n"
        )
        return 1


def authorized_application_pages(
    environment: str,
    effective_config: str,
    target_serial: str | None,
    image_sha256: str | None,
    page_start: int | None,
    page_end: int | None,
) -> tuple[int, int] | None:
    """Return the exact authorized page span only when target, image, and bounds agree."""
    role = "receiver" if environment.startswith("receiver") else "gateway"
    try:
        identity = json.loads((ROOT / "config/current_hardware.json").read_text())[role]
        data = (ROOT / ".pio/build" / environment / "firmware.hex").read_bytes()
        region = parse_ihex_range(data)
        bounds = application_bounds_for_environment(effective_config, environment)
        pages = (region["start"], (region["end_exclusive"] + 511) // 512 * 512)
        if (
            identity["port_path"] != PORTS[role]
            or identity["device_serial_hex"] != target_serial
            or not re.fullmatch(r"[0-9a-f]{64}", image_sha256 or "")
            or hashlib.sha256(data).hexdigest() != image_sha256
            or pages != (page_start, page_end)
            or region["start"] % 512
            or bounds is None
            or not image_fits_application(region, bounds)
            or pages[1] > bounds[1]
        ):
            return None
        return pages
    except (OSError, ValueError, KeyError, TypeError):
        return None


def program_application(
    proof: ProofRun,
    environment: str,
    effective_config: str,
    *,
    approved_sha: str | None = None,
    approved_serial: str | None = None,
    approved_pages: tuple[int, int] | None = None,
) -> int:
    """AVRDUDE -D suppresses auto erase; explicitly erase only the validated image pages."""
    from device_detection.firmware_identity import normalize_ihex_region
    from receiver_boot import (
        AVRDUDE,
        AVRDUDE_CONF,
        ihex,
        read_snapshot,
        require_preserved,
    )

    role = "receiver" if environment.startswith("receiver") else "gateway"
    if approved_sha is None or approved_serial is None or approved_pages is None:
        proof.note(
            environment + "-program.log",
            "BLOCKED: exact MCU serial, image SHA-256, and page range are required; no port opened.\n",
        )
        return 2
    try:
        data = (ROOT / ".pio/build" / environment / "firmware.hex").read_bytes()
        region = parse_ihex_range(data)
        bounds = application_bounds_for_environment(effective_config, environment)
        if bounds is None or not image_fits_application(region, bounds) or region["start"] % 512:
            msg = "application image does not fit target page boundaries"
            raise ValueError(msg)
        start, end = region["start"], (region["end_exclusive"] + 511) // 512 * 512
        if end > bounds[1]:
            msg = "last application page exceeds approved Flash region"
            raise ValueError(msg)
        if approved_sha is not None and (
            hashlib.sha256(data).hexdigest() != approved_sha or approved_pages != (start, end)
        ):
            msg = "image hash or application pages differ from authorization"
            raise ValueError(msg)
        code, out, err = proof.command(
            environment + "-programmer-version", [str(AVRDUDE), "--version"]
        )
        if code or not re.search(rb"\bversion 8\.1\b", out + err):
            msg = "page-write strategy requires reviewed AVRDUDE 8.1"
            raise ValueError(msg)
        snapshot_options = {"current_target": True}
        if approved_serial is not None:
            snapshot_options["include_usersig"] = True
        before = read_snapshot(proof, environment + "-before-page-write", role, **snapshot_options)
        if approved_serial is not None and before["sernum"].hex() != approved_serial:
            msg = "live MCU serial differs from authorization"
            raise ValueError(msg)
        expected = normalize_ihex_region(data.decode("ascii"), start, end)
        if before["flash"][start:end] == expected:
            proof.note(
                environment + "-program.log",
                "SKIPPED: exact application page readback already matches; no repeat write.\n",
            )
            return 0
        image = proof.run_dir / (environment + "-full-pages.hex")
        image.write_text(ihex(expected, start))
        command = [
            str(AVRDUDE),
            "-N",
            "-C",
            str(AVRDUDE_CONF),
            "-p",
            "avr128da28",
            "-c",
            "serialupdi",
            "-P",
            PORTS[role],
            "-b",
            "115200",
            "-D",
            "-T",
            f"erase flash {start:#x} {end - start:#x}",
            "-U",
            f"flash:w:{image}:i",
            "-U",
            f"flash:v:{image}:i",
        ]
        proof.note(environment + "-program-command.json", json.dumps(command, indent=2) + "\n")
        code, _, _ = proof.command(environment + "-page-program", command, 120)
        if code:
            return 1
        after = read_snapshot(proof, environment + "-after-page-write", role, **snapshot_options)
        require_preserved(before, after, start, end)
        if after["flash"][start:end] != expected:
            msg = "application full-page readback mismatch"
            raise ValueError(msg)
        return 0
    except (OSError, ValueError, KeyError) as error:
        proof.note(environment + "-program.log", f"FAIL: {error}; no automatic retry.\n")
        return 1


def tracker_app_upload(
    proof: ProofRun, args: argparse.Namespace, effective_config: str
) -> int:
    try:
        pages = authorized_application_pages(
            "receiver",
            effective_config,
            getattr(args, "target_serial", None),
            getattr(args, "image_sha256", None),
            getattr(args, "page_start", None),
            getattr(args, "page_end", None),
        )
        if not args.authorize_upload or args.target_role != "receiver" or pages is None:
            msg = "target, image, page range, or authorization mismatch"
            raise ValueError(msg)
        if (
            proof.command("tracker-path", ["readlink", "-e", PORTS["receiver"]])[0] != 0
            or proof.command("tracker-owners", ["fuser", PORTS["receiver"]])[0] != 1
        ):
            msg = "Tracker port is missing or occupied"
            raise ValueError(msg)
        return program_application(
            proof,
            "receiver",
            effective_config,
            approved_sha=args.image_sha256,
            approved_serial=args.target_serial,
            approved_pages=pages,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        proof.note("tracker-upload.log", f"BLOCKED: {error}; no write performed.\n")
        return 2


def upload(
    proof: ProofRun, args: argparse.Namespace, profile_ok: bool, effective_config: str
) -> int:
    if not profile_ok:
        proof.note(
            "upload.log",
            "BLOCKED: shared SF7 profile configuration is invalid; no upload attempted.\n",
        )
        return 2
    if not args.authorize_upload:
        proof.note("upload.log", "BLOCKED: upload authorization is missing; no upload attempted.\n")
        return 2
    applications = {
        "receiver": (
            getattr(args, "target_serial", None),
            getattr(args, "image_sha256", None),
            getattr(args, "page_start", None),
            getattr(args, "page_end", None),
        ),
        "sender_hello": (
            getattr(args, "gateway_target_serial", None),
            getattr(args, "gateway_image_sha256", None),
            getattr(args, "gateway_page_start", None),
            getattr(args, "gateway_page_end", None),
        ),
    }
    approved: dict[str, tuple[str, str, tuple[int, int]]] = {}
    for environment, (serial, image_sha, page_start, page_end) in applications.items():
        pages = authorized_application_pages(
            environment, effective_config, serial, image_sha, page_start, page_end
        )
        if pages is None:
            proof.note(
                "upload.log",
                f"BLOCKED: exact {environment} MCU serial, image hash, and page range are required; "
                "no upload attempted.\n",
            )
            return 2
        approved[environment] = (cast("str", image_sha), cast("str", serial), pages)
    # Firmware writes and RF transmissions have separate explicit gates.
    evidence_errors = physical_readiness_errors(args)
    if evidence_errors:
        proof.note(
            "upload.log", "BLOCKED: " + "; ".join(evidence_errors) + "; no upload attempted.\n"
        )
        return 2
    blockers = hardware_blockers(
        "upload",
        mapping_verified=args.physical_mapping_verified,
        power_verified=args.power_verified,
        boot_layout_verified=True,
        authorized=args.authorize_upload,
        no_meter=getattr(args, "no_meter_mode", False),
    )
    if blockers:
        proof.note("upload.log", "BLOCKED: " + ", ".join(blockers) + "; no upload attempted.\n")
        return 2
    if not application_layout_verified(("sender_hello", "receiver"), effective_config):
        proof.note(
            "upload.log",
            "BLOCKED: firmware HEX is not verified inside its target executable region; "
            "no upload attempted.\n",
        )
        return 2
    if not upload_config_preserves_flash(effective_config):
        proof.note(
            "upload.log",
            "BLOCKED: upload config may erase or alter unrelated memory; no upload attempted.\n",
        )
        return 2
    if not upload_ports_match(effective_config):
        proof.note(
            "upload.log",
            "BLOCKED: effective upload ports do not match the verified Sender/Receiver paths; "
            "no upload attempted.\n",
        )
        return 2
    if not args.boot_layout_verified and not args.target_identification_attempted:
        identity_code = identify_targets(proof, args, effective_config)
        if identity_code != 0:
            proof.note(
                "upload.log",
                "BLOCKED: target identity/BOOT layout not verified; no upload attempted.\n",
            )
            return identity_code
    if not args.boot_layout_verified:
        proof.note(
            "upload.log",
            "BLOCKED: target identity/BOOT layout not verified; no upload attempted.\n",
        )
        return 2
    unavailable = check_port_owners(proof, "upload-preflight")
    if unavailable:
        proof.note(
            "upload.log",
            "BLOCKED: UPDI ports unavailable for "
            + ", ".join(unavailable)
            + "; no upload attempted.\n",
        )
        return 2
    if not receiver_boot_handoff_supported(proof, args, effective_config):
        return 2
    for env in ("receiver", "sender_hello"):
        image_sha, serial, pages = approved[env]
        code = program_application(
            proof,
            env,
            effective_config,
            approved_sha=image_sha,
            approved_serial=serial,
            approved_pages=pages,
        )
        if code != 0:
            return 1
    manifest = json.loads((ROOT / "generated/lora_manifest.json").read_text())
    images = verify_installed_images(proof, effective_config, manifest, proof.run_dir.name)
    if images is None:
        proof.note("upload.log", "FAIL: uploaded image readback/signature mismatch.\n")
        return 1
    receipt = proof.run_dir / "physical-upload.json"
    receipt.write_text(json.dumps({"origin": "PHYSICAL_UPDI", "images": images}, indent=2) + "\n")
    args.upload_evidence = receipt
    return 0


def start_rf_monitor(
    proof: ProofRun,
    role: str,
    port: str,
    output_queue: queue.Queue[tuple[str, str, bytes | None]],
) -> dict[str, Any]:
    argv = [
        "uv",
        "run",
        "--no-project",
        "python",
        "-u",
        "third_party/upditerm/upditerm.py",
        port,
        "38400",
    ]
    (proof.run_dir / f"rf-monitor-{role}.command.log").write_text(" ".join(argv) + "\n")
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        argv,
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        start_new_session=True,
        env=environment,
    )
    threads = []
    for stream_name in ("stdout", "stderr"):
        stream = getattr(process, stream_name)

        def pump(name: str = stream_name, source: Any = stream) -> None:
            with (proof.run_dir / f"rf-monitor-{role}.{name}.log").open("wb") as log:
                while True:
                    line = source.readline()
                    if not line:
                        break
                    log.write(line)
                    log.flush()
                    output_queue.put((role, name, line))
            output_queue.put((role, name, None))

        thread = threading.Thread(target=pump, daemon=True)
        thread.start()
        threads.append(thread)
    return {"process": process, "threads": threads}


def stop_rf_monitor(monitor: dict[str, Any] | None) -> int | None:
    if monitor is None:
        return None
    process = monitor["process"]
    if process.stdin and not process.stdin.closed:
        process.stdin.close()
    if process.poll() is None:
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    for thread in monitor["threads"]:
        thread.join(timeout=2)
    return cast("int | None", process.returncode)


def capture_radio_spi_log(proof: ProofRun, role: str, port: str) -> dict[str, Json]:
    output_queue: queue.Queue[tuple[str, str, bytes | None]] = queue.Queue()
    lines: list[str] = []
    monitor: dict[str, Any] | None = None
    monitor_error: str | None = None
    try:
        monitor = start_rf_monitor(proof, role.lower(), port, output_queue)
        deadline = time.monotonic() + RADIO_SPI_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            try:
                _logged_role, stream_name, raw_line = output_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if raw_line is None:
                continue
            line = raw_line.decode(errors="replace").rstrip("\r\n")
            if stream_name == "stdout":
                lines.append(line)
                print(f"[{role.lower()}] {line}", flush=True)
                evidence = parse_radio_spi_log("\n".join(lines), role)
                has_spi_result = evidence["version"] is not None or any(
                    line.startswith(f"[{role}] RADIO_SPI_READ") for line in lines
                )
                if evidence["tx_disabled"] and has_spi_result:
                    break
            else:
                print(f"[{role.lower()} upditerm] {line}", file=sys.stderr, flush=True)
    except OSError as exc:
        monitor_error = f"{type(exc).__name__}: {exc}"
    finally:
        monitor_code = stop_rf_monitor(monitor)
    evidence = parse_radio_spi_log("\n".join(lines), role)
    evidence["log_lines"] = lines
    evidence["monitor_exit_code"] = monitor_code
    if monitor_error:
        evidence["monitor_error"] = monitor_error
        evidence["passed"] = False
        evidence["issues"].append("UPDI monitor could not start")
    return evidence


def radio_spi_smoke(proof: ProofRun, args: argparse.Namespace, effective_config: str) -> int:
    if not rf_spi_diagnostic_config(effective_config):
        proof.note(
            "radio-spi-smoke.log",
            "BLOCKED: dedicated RF-disabled SPI diagnostic environments are missing; "
            "no upload or serial ports opened.\n",
        )
        return 2
    if not application_layout_verified(("sender_hello_spi", "receiver_spi"), effective_config):
        proof.note(
            "radio-spi-smoke.log",
            "BLOCKED: firmware HEX is not verified inside its target executable region; "
            "no upload or serial ports opened.\n",
        )
        return 2
    if not upload_config_preserves_flash(effective_config):
        proof.note(
            "radio-spi-smoke.log",
            "BLOCKED: effective upload config may erase or alter unrelated "
            "memory; no upload attempted.\n",
        )
        return 2
    if not upload_ports_match(effective_config):
        proof.note(
            "radio-spi-smoke.log",
            "BLOCKED: effective upload ports do not match the verified "
            "Sender/Receiver paths; no upload attempted.\n",
        )
        return 2
    diagnostic_images = {}
    for environment, serial, image_sha, page_start, page_end in (
        (
            "receiver_spi",
            getattr(args, "target_serial", None),
            getattr(args, "receiver_spi_image_sha256", None),
            getattr(args, "receiver_spi_page_start", None),
            getattr(args, "receiver_spi_page_end", None),
        ),
        (
            "sender_hello_spi",
            getattr(args, "gateway_target_serial", None),
            getattr(args, "gateway_spi_image_sha256", None),
            getattr(args, "gateway_spi_page_start", None),
            getattr(args, "gateway_spi_page_end", None),
        ),
    ):
        pages = authorized_application_pages(
            environment, effective_config, serial, image_sha, page_start, page_end
        )
        if pages is None:
            proof.note(
                "radio-spi-smoke.log",
                f"BLOCKED: exact {environment} serial, image SHA-256, and page range are required; "
                "no upload or serial ports opened.\n",
            )
            return 2
        diagnostic_images[environment] = (cast("str", serial), cast("str", image_sha), pages)
    if not args.boot_layout_verified and not args.target_identification_attempted:
        identity_code = identify_targets(proof, args, effective_config)
        if identity_code != 0:
            proof.note(
                "radio-spi-smoke.log",
                "BLOCKED: target identity/BOOT layout not verified; "
                "no diagnostic upload attempted.\n",
            )
            return identity_code
    if not args.boot_layout_verified:
        proof.note(
            "radio-spi-smoke.log",
            "BLOCKED: target identity/BOOT layout not verified; no diagnostic upload attempted.\n",
        )
        return 2
    blockers = hardware_blockers(
        "radio-spi-smoke",
        mapping_verified=args.physical_mapping_verified,
        power_verified=args.power_verified,
        boot_layout_verified=args.boot_layout_verified,
        authorized=args.authorize_upload,
        no_meter=getattr(args, "no_meter_mode", False),
    )
    if blockers:
        proof.note(
            "radio-spi-smoke.log",
            "BLOCKED: " + ", ".join(blockers) + "; no diagnostic upload attempted.\n",
        )
        return 2
    evidence_errors = physical_readiness_errors(args)
    if evidence_errors:
        proof.note(
            "radio-spi-smoke.log",
            "BLOCKED: " + "; ".join(evidence_errors) + "; no upload attempted.\n",
        )
        return 2
    unavailable = check_port_owners(proof, "radio-spi-preflight")
    if unavailable:
        proof.note(
            "radio-spi-smoke.log",
            "BLOCKED: UPDI ports unavailable for "
            + ", ".join(unavailable)
            + "; no diagnostic upload attempted.\n",
        )
        return 2

    if not receiver_boot_handoff_supported(proof, args, effective_config):
        return 2

    for env in ("receiver_spi", "sender_hello_spi"):
        image_serial, image_sha, pages = diagnostic_images[env]
        code = program_application(
            proof,
            env,
            effective_config,
            approved_sha=image_sha,
            approved_serial=image_serial,
            approved_pages=pages,
        )
        if code != 0:
            proof.note(
                "radio-spi-smoke.log",
                f"INCOMPLETE: {env} diagnostic upload failed; no RF test run.\n",
            )
            return 1

    results = {
        "gateway": capture_radio_spi_log(proof, "GATEWAY", PORTS["gateway"]),
        "receiver": capture_radio_spi_log(proof, "RECEIVER", PORTS["receiver"]),
    }
    ports_after = check_port_owners(proof, "radio-spi-postflight")
    report = {
        "origin": "PHYSICAL_SPI"
        if all(result["passed"] for result in results.values()) and not ports_after
        else "UNPROVEN",
        "status": "PASS"
        if all(result["passed"] for result in results.values()) and not ports_after
        else "INCOMPLETE",
        "rf_transmission_enabled": False,
        "ports_still_unavailable": ports_after,
        "devices": results,
    }
    (proof.run_dir / "radio-spi-measurements.json").write_text(json.dumps(report, indent=2) + "\n")
    if report["status"] == "PASS":
        proof.note(
            "radio-spi-smoke.log",
            "PASS: both radios returned a supported SPI version in RF-disabled diagnostic "
            "firmware.\n",
        )
        return 0
    proof.note(
        "radio-spi-smoke.log",
        "INCOMPLETE: radio SPI response or diagnostic TX-disabled marker was not verified; "
        "no RF test was run.\n",
    )
    return 2


def upload_evidence_matches(path: str | Path | None, manifest: Json) -> bool | None:
    if path is None:
        return False
    try:
        receipt = json.loads(Path(path).read_text())
        if (
            not isinstance(receipt, dict)
            or receipt.get("origin") != "PHYSICAL_UPDI"
            or not isinstance(receipt.get("images"), dict)
        ):
            return False
        for role, environment in [("GATEWAY", "sender_hello"), ("RECEIVER", "receiver")]:
            image = receipt["images"][role]
            if not isinstance(image, dict):
                return False
            current_hash = hashlib.sha256(
                (ROOT / ".pio/build" / environment / "firmware.hex").read_bytes()
            ).hexdigest()
            if (
                image.get("origin") != "PHYSICAL_UPDI"
                or not image.get("verified")
                or image.get("signature") != "1e970a"
                or image.get("port") != PORTS[role.lower()]
                or image.get("firmware_sha256") != current_hash
                or image.get("build_id") != manifest["environments"][environment]["build_id"]
            ):
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def radio_startup_matches(
    lines: Sequence[str], role: str, radio: Mapping[str, Json], *, allow_rearm: bool = False
) -> bool:
    ready_states = [f"[{role}] RADIO_READY"]
    if allow_rearm:
        ready_states.append(f"[{role}] RX_READY")
    required = [
        (
            f"[{role}] RADIO_PROFILE F100={round(radio['frequency_mhz'] * 100)} "
            f"P={radio['tx_power_dbm']}"
        ),
        f"[{role}] RADIO_MOD SF=7 BW=125 CR=5",
        f"[{role}] RADIO_FRAME SW=12 PRE=8 CRC=1 HDR=E IQ=0",
    ]
    init_statuses = {
        line
        for line in lines
        if line in (f"[{role}] RADIO_INIT_OK", f"[{role}] RADIO_INIT E=0")
    }
    versions = [line for line in lines if line.startswith(f"[{role}] RADIO_SPI_VERSION=")]
    return (
        all(line in lines for line in required)
        and len(init_statuses) == 1
        and f"[{role}] RADIO_INIT_FAILED" not in lines
        and any(line in ready_states for line in lines)
        and (allow_rearm or f"[{role}] RADIO_NOT_READY" not in lines)
        and len(set(versions)) == 1
        and next(iter(set(versions)))
        in [f"[{role}] RADIO_SPI_VERSION=0x{value:02X}" for value in (0x11, 0x12, 0x13)]
        and all(
            set(line for line in lines if line.startswith(prefix)) == {expected}
            for prefix, expected in (
                (
                    f"[{role}] RADIO_PROFILE ",
                    f"[{role}] RADIO_PROFILE F100={round(radio['frequency_mhz'] * 100)} "
                    f"P={radio['tx_power_dbm']}",
                ),
                (f"[{role}] RADIO_MOD ", f"[{role}] RADIO_MOD SF=7 BW=125 CR=5"),
                (
                    f"[{role}] RADIO_FRAME ",
                    f"[{role}] RADIO_FRAME SW=12 PRE=8 CRC=1 HDR=E IQ=0",
                ),
            )
        )
    )


def validate_symmetric_exchange(
    logs: Mapping[str, str], session: int, diagnostic_test: str
) -> list[str]:
    """Require both endpoints' correlated SSOT events; text alone is not RF proof."""
    if diagnostic_test not in ("T01", "T02", "T03", "T04"):
        return ["invalid symmetric diagnostic"]
    reverse = diagnostic_test in ("T03", "T04")
    nack = diagnostic_test in ("T02", "T04")
    sender, receiver = ("RECEIVER", "GATEWAY") if reverse else ("GATEWAY", "RECEIVER")
    source, destination = (1, 0) if reverse else (0, 1)
    response, response_type = ("NACK", 9) if nack else ("ACK", 3)
    pattern = re.compile(
        r"^\[(GATEWAY|RECEIVER)\] ([A-Z_]+) T=(\d+) SID=([0-9A-F]{4}) "
        r"SRC=(\d+) DST=(\d+) TYPE=([0-9A-F]{2}) Q=(\d+) E=(-?\d+) IRQ=([0-9A-F]{2})$"
    )
    events: dict[str, list[tuple[str, int, int]]] = {sender: [], receiver: []}
    issues: list[str] = []
    for role, text in logs.items():
        if text.splitlines().count(f"[{role}] TRANSPORT=SSOT_SYMMETRIC_V1") != 1:
            issues.append(f"{role}: missing symmetric transport identity")
        for line in text.splitlines():
            match = pattern.fullmatch(line)
            if not match:
                if " SID=" in line or "LOG_OVERFLOW" in line:
                    issues.append(f"{role}: malformed or lost event")
                continue
            board, name, timestamp, sid, src, dst, type_, seq, rc, irq = match.groups()
            type_, irq = int(type_, 16), int(irq, 16)
            data = type_ == 8
            if (
                board != role
                or int(sid, 16) != session
                or int(seq) != 1
                or int(rc) != 0
                or type_ not in (8, response_type)
                or (int(src), int(dst))
                != ((source, destination) if data else (destination, source))
            ):
                issues.append(f"{role}: invalid transaction identity or result")
            if name.endswith("_TX_DONE") and not irq & 8:
                issues.append(f"{role}: missing physical TxDone")
            if (name.endswith("_RX") or name == "DATA_VALIDATED") and (
                not irq & 0x40 or irq & 0x20
            ):
                issues.append(f"{role}: invalid RX IRQ/CRC")
            events[role].append((name, int(timestamp), type_))
    required = {
        sender: [
            ("DATA_TX_BEGIN", 8),
            ("DATA_TX_DONE", 8),
            (response + "_RX", response_type),
            (response + "_ACCEPTED", response_type),
            ("TRANSACTION_FAILED" if nack else "TRANSACTION_COMPLETE", response_type),
        ],
        receiver: [("DATA_RX", 8)]
        + ([] if nack else [("DATA_VALIDATED", 8)])
        + [(response + "_TX_BEGIN", response_type), (response + "_TX_DONE", response_type)],
    }
    for role, names in required.items():
        selected = [(name, type_) for name, _, type_ in events[role]]
        if selected != names:
            issues.append(f"{role}: incomplete, duplicate, or out-of-order radio events")
        times = [timestamp for _, timestamp, _ in events[role]]
        if any(
            (right - left) & 0xFFFFFFFF >= 0x80000000
            for left, right in itertools.pairwise(times)
        ):
            issues.append(f"{role}: nonmonotonic device timestamps")
    for role, name in [(sender, "DATA_PAYLOAD")] + ([] if nack else [(receiver, "PAYLOAD_BYTES")]):
        expected = (
            f"[{role}] {name} C={session:04X} S=01 LEN=11 "
            "HEX=68656C6C6F20776F726C64 ASCII=hello world"
        )
        if logs[role].splitlines().count(expected) != 1:
            issues.append(f"{role}: missing exact 11-byte payload evidence")
    return issues


def validate_live_proof(
    journal: Sequence[Json],
    manifest: Json,
    images: Json,
    run_id: str,
    session: int,
    diagnostic_test: str = "T01",
) -> dict[str, Json]:
    """Validate captured events; provenance comes from fresh UPDI image readback, not log labels."""
    issues = []
    logs = {
        role: "\n".join(item["line"] for item in journal if item["role"] == role)
        for role in ("GATEWAY", "RECEIVER")
    }
    if not shared_identity_matches(
        logs, manifest["shared_fingerprint"], manifest["shared"]["protocol"]["version"]
    ):
        issues.append("shared identity mismatch")
    for role, environment in [("GATEWAY", "sender_hello"), ("RECEIVER", "receiver")]:
        role_lines = [item["line"] for item in journal if item["role"] == role]
        if len(role_lines) != len(set(role_lines)):
            issues.append(f"{role}: duplicate log line")
        image = images.get(role, {})
        expected_id = manifest["environments"][environment]["build_id"]
        if (
            image.get("origin") != "PHYSICAL_UPDI"
            or image.get("run_id") != run_id
            or image.get("signature") != "1e970a"
            or image.get("port") != PORTS[role.lower()]
            or not image.get("verified")
            or not image.get("firmware_sha256")
            or image.get("build_id") != expected_id
        ):
            issues.append(f"{role}: missing fresh verified image identity")
        lines = logs[role].splitlines()
        if not radio_startup_matches(lines, role, manifest["shared"]["radio"]):
            issues.append(f"{role}: missing or mismatched actual radio initialization")
        if [line for line in lines if line.startswith(f"[{role}] BUILD_ID=")] != [
            f"[{role}] BUILD_ID={expected_id}"
        ]:
            issues.append(f"{role}: runtime build identity mismatch")
    if any("TRANSPORT=SSOT_SYMMETRIC_V1" in text for text in logs.values()):
        issues.extend(validate_symmetric_exchange(logs, session, diagnostic_test))
        reverse = diagnostic_test in ("T03", "T04")
        nack = diagnostic_test in ("T02", "T04")
        receiving = "GATEWAY" if reverse else "RECEIVER"
        symmetric_commands = [
            item["line"] for item in journal if item["role"] == "HOST" and item["line"] != "P"
        ]
        if symmetric_commands != [("N" if nack else "R") + f"{session:04X}", f"S{session:04X}"]:
            issues.append("incorrect or repeated symmetric control commands")
        ready_positions = [
            i
            for i, item in enumerate(journal)
            if item["role"] == receiving and item["line"] == f"[{receiving}] RX_READY"
        ]
        start_positions = [
            i
            for i, item in enumerate(journal)
            if item["role"] == "HOST" and item["line"].startswith("S")
        ]
        if (
            len(ready_positions) != 1
            or len(start_positions) != 1
            or ready_positions[0] >= start_positions[0]
        ):
            issues.append("DATA requested before receiver ready")
        return {
            "valid": not issues,
            "issues": sorted(set(issues)),
            "session": session,
            "origin": "STRUCTURAL_LOG_VALIDATION",
            "diagnostic_test": diagnostic_test,
        }
    commands = [(i, item["line"]) for i, item in enumerate(journal) if item["role"] == "HOST"]
    if [line for _, line in commands] != [f"R{session:04X}", f"S{session:04X}"]:
        issues.append("incorrect, repeated or continuation commands")
    positions: dict[str, list[int]] = {}
    records = []
    for index, item in enumerate(journal):
        role, line = item["role"], item["line"]
        if role == "HOST":
            continue
        if not line.startswith(f"[{role}] "):
            issues.append("wrong role or malformed debug line")
            continue
        positions.setdefault(line, []).append(index)
        event = RF_EVENT_RE.fullmatch(line)
        if event:
            event_role, name, campaign, sequence, *_ = event.groups()
            if (
                event_role != role
                or int(campaign, 16) != session
                or (sequence is not None and int(sequence, 16) != 1)
            ):
                issues.append("wrong session, role or sequence")
            records.append((index, role, name, event))
        elif " C=" in line or line.split("] ", 1)[-1].split(" ", 1)[0] in {
            "DATA_TX",
            "DATA_DONE",
            "DATA_RX",
            "DATA_DUP",
            "ACK_TX",
            "ACK_DONE",
            "ACK_RX",
            "DATA_PAYLOAD",
            "PAYLOAD_BYTES",
            "PAYLOAD_MATCH",
            "S_RECEIVED",
            "TEST_RUNNING",
            "PREFLIGHT_OK",
            "TEST_COMPLETED",
            "SESSION_READY",
        }:
            issues.append("malformed protocol event")
        if any(
            marker in line for marker in ("FAILED", "TIMEOUT", "CAMPAIGN_CONTINUE", "WAIT_CAMPAIGN")
        ) and "ACK_TIMEOUT C=" not in line:
            # An ACK timeout may precede a bounded retransmission; TX/init failures cannot pass.
            issues.append("radio or protocol failure")

    def unique(line: str) -> int:
        found = positions.get(line, [])
        if len(found) != 1:
            issues.append(f"missing or repeated {line}")
        return found[0] if len(found) == 1 else -1

    receiver_boot = [
        i
        for i, item in enumerate(journal)
        if item["role"] == "RECEIVER" and item["line"].startswith("[RECEIVER] BOOT receiver ")
    ]
    sender_boot = [
        i
        for i, item in enumerate(journal)
        if item["role"] == "GATEWAY" and item["line"].startswith("[GATEWAY] BOOT sender_hello ")
    ]
    if len(receiver_boot) != 1 or len(sender_boot) != 1:
        issues.append("missing or repeated boot")
    ready = unique("[RECEIVER] RX_READY")
    armed = unique(f"[RECEIVER] SESSION_READY C={session:04X}")
    waiting = unique("[GATEWAY] WAIT_START")
    if len(commands) == 2 and not (commands[0][0] < armed < ready < waiting < commands[1][0]):
        issues.append("start issued before Receiver/Sender readiness")
    for role, names in [
        (
            "GATEWAY",
            (
                "S_RECEIVED",
                "TEST_RUNNING",
                "DATA_PAYLOAD",
                "DATA_TX",
                "DATA_DONE",
                "ACK_RX",
                "PREFLIGHT_OK",
                "TEST_COMPLETED",
            ),
        ),
        ("RECEIVER", ("PAYLOAD_MATCH", "PAYLOAD_BYTES", "DATA_RX", "ACK_TX", "ACK_DONE")),
    ]:
        order = []
        for name in names:
            matches = [record for record in records if record[1:3] == (role, name)]
            if len(matches) != 1:
                issues.append(f"{role}: missing or duplicate {name}")
            else:
                order.append(matches[0][0])
        if order != sorted(order):
            issues.append(f"{role}: events out of order")
    if len(commands) == 2 and any(
        index < commands[1][0]
        for index, _, name, _ in records
        if name in ("DATA_TX", "DATA_RX", "ACK_TX", "ACK_RX")
    ):
        issues.append("RF events before start command")
    evidence = parse_rf_campaign(logs["GATEWAY"], logs["RECEIVER"])
    if not single_packet_evidence_passed(evidence):
        issues.append("incomplete or duplicate DATA/payload/ACK evidence")
    return {
        "valid": not issues,
        "issues": sorted(set(issues)),
        "session": session,
        "origin": "STRUCTURAL_LOG_VALIDATION",
    }


def validate_stable_transport(
    journal: Sequence[Json],
    images: Mapping[str, Json],
    run_id: str,
    diagnostic_test: str,
) -> dict[str, Json]:
    """Validate the current stable-library DATA/ACK or bounded DATA/NACK logs."""
    issues: list[str] = []
    if diagnostic_test not in ("T01", "T02"):
        return {"valid": False, "issues": ["stable transport supports T01/T02 only"]}

    config = json.loads((ROOT / "config/lora_system.json").read_text())
    protocol = config["protocol"]
    payload = protocol["payload"].encode("ascii")
    max_attempts = int(config["retries"]["max_retries"]) + 1
    roles = {"GATEWAY": "sender_hello", "RECEIVER": "receiver"}
    logs = {
        role: [
            (index, item["line"])
            for index, item in enumerate(journal)
            if item["role"] == role
        ]
        for role in roles
    }
    manifest = json.loads((ROOT / "generated/lora_manifest.json").read_text())

    for role in roles:
        image = images.get(role, {})
        if (
            image.get("origin") != "PHYSICAL_UPDI"
            or image.get("run_id") != run_id
            or image.get("signature") != "1e970a"
            or image.get("port") != PORTS[role.lower()]
            or not image.get("verified")
            or not image.get("firmware_sha256")
            or not image.get("build_id")
        ):
            issues.append(f"{role}: missing fresh verified image identity")
        if any("LOG_OVERFLOW" in line for _, line in logs[role]):
            issues.append(f"{role}: firmware log overflow")
        if any(
            marker in line
            for _, line in logs[role]
            for marker in ("RADIO_INIT_FAILED", "TX_TIMEOUT")
        ):
            issues.append(f"{role}: radio initialization or TX failure")
        build_ids = [line for _, line in logs[role] if line.startswith(f"[{role}] BUILD_ID=")]
        if not build_ids or set(build_ids) != {f"[{role}] BUILD_ID={image.get('build_id')}"}:
            issues.append(f"{role}: current firmware build ID is missing or mismatched")
        if not radio_startup_matches(
            [line for _, line in logs[role]], role, manifest["shared"]["radio"], allow_rearm=True
        ):
            issues.append(f"{role}: radio register/profile startup evidence is incomplete")
    identity_logs = {role: "\n".join(line for _, line in logs[role]) for role in roles}
    if not shared_identity_matches(
        identity_logs,
        manifest["shared_fingerprint"],
        manifest["shared"]["protocol"]["version"],
    ):
        issues.append("sender and receiver shared protocol/config identity does not match")

    host_commands = [
        (index, item["role"], item["line"])
        for index, item in enumerate(journal)
        if item["role"] in ("HOST_RECEIVER", "HOST_GATEWAY")
    ]
    expected_commands = [
        ("HOST_RECEIVER", "?"),
        *(([("HOST_RECEIVER", "N")] if diagnostic_test == "T02" else [])),
        ("HOST_RECEIVER", "R"),
        *([("HOST_RECEIVER", "D")] if any(role == "HOST_RECEIVER" and text == "D" for _, role, text in host_commands) else []),
        ("HOST_GATEWAY", "R"),
        ("HOST_GATEWAY", "?"),
        ("HOST_GATEWAY", "S"),
        ("HOST_RECEIVER", "P"),
        ("HOST_GATEWAY", "P"),
    ]
    if [(role, command) for _, role, command in host_commands] != expected_commands:
        issues.append("incorrect, repeated or out-of-order stable control commands")

    if sum(role == "HOST_RECEIVER" and command == "P" for _, role, command in host_commands) != 1 or sum(
        role == "HOST_GATEWAY" and command == "P" for _, role, command in host_commands
    ) != 1:
        issues.append("both radios were not explicitly parked")

    receiver_ready = [
        index for index, line in logs["RECEIVER"] if line == "[RECEIVER] RX_READY"
    ]
    sender_ready = [
        index for index, line in logs["GATEWAY"] if line == "[GATEWAY] RADIO_READY"
    ]
    receiver_rearm = next(
        (index for index, role, command in host_commands if role == "HOST_RECEIVER" and command == "R"),
        -1,
    )
    gateway_rearm = next(
        (index for index, role, command in host_commands if role == "HOST_GATEWAY" and command == "R"),
        -1,
    )
    gateway_status = next(
        (index for index, role, command in host_commands if role == "HOST_GATEWAY" and command == "?"),
        -1,
    )
    command_s = next(
        (index for index, role, command in host_commands if role == "HOST_GATEWAY" and command == "S"),
        -1,
    )
    if not any(index > receiver_rearm and index < command_s for index in receiver_ready):
        issues.append("DATA requested before a fresh receiver RX_READY")
    if not receiver_rearm < gateway_rearm < gateway_status < command_s:
        issues.append("sender was not rearmed and checked before DATA request")
    if not any(index > gateway_status and index < command_s for index in sender_ready):
        issues.append("sender did not report RADIO_READY before DATA request")
    for role in roles:
        boots = [index for index, line in logs[role] if line.startswith(f"[{role}] BOOT ")]
        if len(boots) > 1 or any(index > command_s for index in boots):
            issues.append(f"{role}: unexpected reset during physical transaction")
        if any(line.startswith(f"[{role}] BUILD_ID=") and line != f"[{role}] BUILD_ID={images.get(role, {}).get('build_id')}"
               for _, line in logs[role]):
            issues.append(f"{role}: running firmware identity differs from verified image")
    requested = [
        index
        for index, line in logs["GATEWAY"]
        if line == "[GATEWAY] DATA_TX_REQUESTED" or line.startswith("[GATEWAY] DATA_TX_REQUESTED T=")
    ]
    if len(requested) != 1 or (requested and requested[0] <= command_s):
        issues.append("sender did not report exactly one accepted DATA request")
    for role in roles:
        if not any(line == f"[{role}] PARKED E=0" for _, line in logs[role]):
            issues.append(f"{role}: radio did not park cleanly")

    pattern = re.compile(
        r"^\[(GATEWAY|RECEIVER)\] ([A-Z_]+) SID=([0-9A-F]{4}) T=(\d+) "
        r"TYPE=(\d+) Q=(\d+) E=(-?\d+)$"
    )
    events: dict[str, list[tuple[int, str, int, int, int, int, int]]] = {
        role: [] for role in roles
    }
    for index, item in enumerate(journal):
        line = item["line"]
        match = pattern.fullmatch(line)
        if match:
            role, name, campaign_id, timestamp, type_, sequence, error = match.groups()
            events[role].append(
                (
                    index,
                    name,
                    int(timestamp),
                    int(type_),
                    int(sequence),
                    int(error),
                    int(campaign_id, 16),
                )
            )
        elif any(
            line.startswith(f"[{role}] {name} ")
            for role in roles
            for name in ("DATA_TX_BEGIN", "DATA_TX_DONE", "DATA_VALIDATED", "ACK_TX_", "NACK_TX_", "ACK_ACCEPTED", "NACK_RX", "TRANSACTION_FAILED")
        ):
            issues.append("malformed stable transport event")

    campaign_ids = {event[6] for role_events in events.values() for event in role_events}
    if len(campaign_ids) != 1 or not campaign_ids or 0 in campaign_ids:
        issues.append("missing, zero or mismatched sender/receiver campaign ID")
    campaign_id = next(iter(campaign_ids), 0)

    def selected(role: str, name: str) -> list[tuple[int, str, int, int, int, int, int]]:
        return [event for event in events[role] if event[1] == name]

    data_tx = selected("GATEWAY", "DATA_TX_BEGIN")
    data_done = selected("GATEWAY", "DATA_TX_DONE")
    ack_begin = selected("RECEIVER", "ACK_TX_BEGIN")
    ack_done = selected("RECEIVER", "ACK_TX_DONE")
    nack_begin = selected("RECEIVER", "NACK_TX_BEGIN")
    nack_done = selected("RECEIVER", "NACK_TX_DONE")
    attempts = len(data_tx)
    if not 1 <= attempts <= max_attempts:
        issues.append("DATA attempts were absent or exceeded the retry bound")
    if len(data_done) != attempts:
        issues.append("DATA TX completion count does not match attempts")

    for role_events in events.values():
        for event in role_events:
            expected_type = (
                protocol["ack_type"] if event[1].startswith("ACK_") else
                protocol["nack_type"] if event[1].startswith("NACK_") else
                protocol["data_type"] if event[1].startswith("DATA_") or event[1] == "RETRY_SCHEDULED" else
                None
            )
            if expected_type is not None and event[3] != expected_type:
                issues.append("event name did not match its on-wire packet type")
        if any(
            (event[3], event[4], event[5])
            not in (
                (protocol["data_type"], protocol["sequence"], 0),
                (protocol["ack_type"], protocol["sequence"], 0),
                (protocol["nack_type"], protocol["sequence"], 0),
                (protocol["nack_type"], protocol["sequence"], -1),
            )
            for event in role_events
        ):
            issues.append("event type, sequence or result did not match the configured protocol")

    validated = selected("RECEIVER", "DATA_VALIDATED")
    accepted = selected("GATEWAY", "ACK_ACCEPTED")
    nack_rx = selected("GATEWAY", "NACK_RX")
    retries = selected("GATEWAY", "RETRY_SCHEDULED")
    if len(validated) != 1 or len(accepted) != 1:
        issues.append("DATA validation or ACK acceptance was missing or repeated")
    if not 1 <= len(ack_begin) == len(ack_done) <= attempts:
        issues.append("receiver ACK TX count did not match received DATA attempts")
    if selected("GATEWAY", "TRANSACTION_FAILED"):
        issues.append("sender reported transaction failure")
    if diagnostic_test == "T01" and (nack_rx or nack_begin or nack_done):
        issues.append("unexpected NACK in ACK proof")
    if diagnostic_test == "T02" and not (1 <= len(nack_begin) == len(nack_done) == len(nack_rx) < attempts):
        issues.append("controlled NACK must be received and followed by retry then ACK")
    retry_events = sorted(retries + nack_rx, key=lambda event: event[2])
    if len(retry_events) != attempts - 1:
        issues.append("sender retry count did not match DATA attempts")
    # UART logs are deferred during TX; compare timestamps within each MCU only.
    if len(data_done) == attempts and len(retry_events) == attempts - 1:
        if any(data_tx[i][2] > data_done[i][2] for i in range(attempts)) or any(
            not data_done[i][2] <= retry_events[i][2] <= data_tx[i + 1][2]
            for i in range(attempts - 1)
        ):
            issues.append("sender DATA retry events were out of order")
    payload_line = (
        f"[RECEIVER] PAYLOAD_BYTES C={campaign_id:04X} "
        f"S={protocol['sequence']:02X} LEN={len(payload)} "
        f"HEX={payload.hex().upper()} ASCII={payload.decode('ascii')}"
    )
    if sum(line == payload_line for _, line in logs["RECEIVER"]) != 1:
        issues.append("receiver did not log the exact application payload once")
    dropped = selected("RECEIVER", "RESPONSE_DROPPED")
    drop_requested = any(role == "HOST_RECEIVER" and text == "D" for _, role, text in host_commands)
    if len(dropped) != int(drop_requested):
        issues.append("controlled response suppression did not match the command")
    if len(selected("RECEIVER", "DATA_DUP")) != len(ack_begin) + len(dropped) - 1:
        issues.append("receiver duplicate suppression evidence did not match ACK replies")
    if validated and accepted and ack_begin and ack_done and data_tx and data_done:
        if not validated[0][2] <= ack_begin[0][2] <= ack_done[0][2]:
            issues.append("receiver DATA/ACK events were out of order")
        if data_done[-1][2] > accepted[0][2]:
            issues.append("ACK accepted before DATA TX completion")
    retries_count = len(retry_events)
    nack_count = len(nack_begin)
    ack_count = len(ack_begin)

    return {
        "valid": not issues,
        "issues": sorted(set(issues)),
        "run_id": run_id,
        "diagnostic_test": diagnostic_test,
        "campaign_id": f"{campaign_id:04X}",
        "attempts": attempts,
        "retries": retries_count,
        "timeouts": len(retries),
        "rtt_ms": accepted[0][2] - data_tx[0][2] if accepted and data_tx else None,
        "ack_tx": ack_count,
        "nack_tx": nack_count,
        "payload_bytes": len(payload),
        "origin": "STRUCTURAL_LOG_VALIDATION",
    }


def validate_wrong_destination_trials(
    journal: Sequence[Json], images: Mapping[str, Json], run_id: str
) -> dict[str, Json]:
    """Require ten physical wrong-destination DATA frames to be filtered without reply."""
    trials = 10
    issues: list[str] = []
    roles = {"GATEWAY": "sender_hello", "RECEIVER": "receiver"}
    logs = {
        role: [
            (index, item["line"])
            for index, item in enumerate(journal)
            if item["role"] == role
        ]
        for role in roles
    }
    manifest = json.loads((ROOT / "generated/lora_manifest.json").read_text())
    for role, environment in roles.items():
        image = images.get(role, {})
        if (
            image.get("origin") != "PHYSICAL_UPDI"
            or image.get("run_id") != run_id
            or image.get("signature") != "1e970a"
            or image.get("port") != PORTS[role.lower()]
            or not image.get("verified")
            or not image.get("firmware_sha256")
            or not image.get("build_id")
        ):
            issues.append(f"{role}: missing fresh verified image identity")
        if not radio_startup_matches(
            [line for _, line in logs[role]], role, manifest["shared"]["radio"], allow_rearm=True
        ):
            issues.append(f"{role}: radio startup/profile/register identity mismatch")
        build_lines = [line for _, line in logs[role] if line.startswith(f"[{role}] BUILD_ID=")]
        if not build_lines or set(build_lines) != {f"[{role}] BUILD_ID={image.get('build_id')}"}:
            issues.append(f"{role}: running firmware identity differs from verified image")
        if any("LOG_OVERFLOW" in line for _, line in logs[role]):
            issues.append(f"{role}: firmware log overflow")
    identity_logs = {role: "\n".join(line for _, line in logs[role]) for role in roles}
    if not shared_identity_matches(
        identity_logs,
        manifest["shared_fingerprint"],
        manifest["shared"]["protocol"]["version"],
    ):
        issues.append("sender and receiver shared protocol/config identity does not match")

    commands = [
        (index, item["role"], item["line"])
        for index, item in enumerate(journal)
        if item["role"] in ("HOST_RECEIVER", "HOST_GATEWAY")
    ]
    expected_commands = [
        ("HOST_RECEIVER", "?"),
        ("HOST_RECEIVER", "R"),
        ("HOST_GATEWAY", "R"),
        ("HOST_GATEWAY", "?"),
        *([("HOST_GATEWAY", "W")] * trials),
        ("HOST_RECEIVER", "P"),
        ("HOST_GATEWAY", "P"),
    ]
    if [(role, command) for _, role, command in commands] != expected_commands:
        issues.append("wrong-destination controls were repeated, missing or out of order")

    receiver_ready = [index for index, line in logs["RECEIVER"] if line == "[RECEIVER] RX_READY"]
    gateway_ready = [index for index, line in logs["GATEWAY"] if line == "[GATEWAY] RADIO_READY"]
    receiver_rearm = next(
        (index for index, role, command in commands if role == "HOST_RECEIVER" and command == "R"),
        -1,
    )
    gateway_rearm = next(
        (index for index, role, command in commands if role == "HOST_GATEWAY" and command == "R"),
        -1,
    )
    gateway_status = next(
        (index for index, role, command in commands if role == "HOST_GATEWAY" and command == "?"),
        -1,
    )
    wrong_starts = [
        index
        for index, line in logs["GATEWAY"]
        if line == "[GATEWAY] WRONG_DEST_TX_BEGIN DST=2 TYPE=08 Q=1 APP=11"
    ]
    wrong_done = [
        index for index, line in logs["GATEWAY"] if line == "[GATEWAY] WRONG_DEST_TX_DONE"
    ]
    discard_pattern = re.compile(
        r"^\[RECEIVER\] RX_DISCARD_DEST SID=0000 T=\d+ TYPE=0 Q=0 E=0$"
    )
    destination_discards = [
        index for index, line in logs["RECEIVER"] if discard_pattern.fullmatch(line)
    ]
    if len(wrong_starts) != trials or len(wrong_done) != trials:
        issues.append("Gateway did not complete exactly ten wrong-destination transmissions")
    if len(destination_discards) != trials:
        issues.append("Receiver did not log ten destination-filter discards")

    wrong_commands = [index for index, role, command in commands if role == "HOST_GATEWAY" and command == "W"]
    boundaries = [*wrong_commands[1:], len(journal)]
    for index, start in enumerate(wrong_commands[:trials]):
        end = boundaries[index]
        starts = [value for value in wrong_starts if start < value < end]
        done = [value for value in wrong_done if start < value < end]
        discards = [value for value in destination_discards if start < value < end]
        if not (len(starts) == len(done) == len(discards) == 1 and starts[0] < done[0]):
            issues.append(f"wrong-destination trial {index + 1} lacks one TX and one address discard")

    if not any(index > receiver_rearm and index < (wrong_commands[0] if wrong_commands else -1)
               for index in receiver_ready):
        issues.append("Receiver did not report fresh RX_READY before wrong-destination trials")
    if not gateway_rearm < gateway_status < (wrong_commands[0] if wrong_commands else -1):
        issues.append("Gateway was not rearmed and checked before wrong-destination trials")
    if not any(
        index > gateway_status and index < (wrong_commands[0] if wrong_commands else -1)
        for index in gateway_ready
    ):
        issues.append("Gateway did not report RADIO_READY before wrong-destination trials")
    for role in roles:
        forbidden = (
            "DATA_VALIDATED",
            "ACK_TX_BEGIN",
            "ACK_TX_DONE",
            "NACK_TX_BEGIN",
            "NACK_TX_DONE",
            "ACK_ACCEPTED",
            "NACK_RX",
        )
        if any(any(f"[{role}] {name} " in line for name in forbidden) for _, line in logs[role]):
            issues.append(f"{role}: wrong-destination packet reached delivery or response path")
        if sum(line == f"[{role}] PARKED E=0" for _, line in logs[role]) != 1:
            issues.append(f"{role}: radio did not park cleanly")

    return {
        "valid": not issues,
        "issues": sorted(set(issues)),
        "run_id": run_id,
        "trials": trials,
        "transmitted": len(wrong_done),
        "destination_discards": len(destination_discards),
        "deliveries": sum(
            line.startswith("[RECEIVER] DATA_VALIDATED ") for _, line in logs["RECEIVER"]
        ),
        "responses": sum(
            1
            for role in roles
            for _, line in logs[role]
            if any(f"[{role}] {name} " in line for name in ("ACK_TX_BEGIN", "NACK_TX_BEGIN"))
        ),
        "origin": "STRUCTURAL_LOG_VALIDATION",
    }


def verify_installed_images(
    proof: ProofRun, effective_config: str, manifest: Json, run_id: str
) -> dict[str, Json] | None:
    """Read signature and Flash anew; compare image bytes before allowing any S command."""
    from device_detection.firmware_identity import normalize_ihex_region
    from receiver_boot import read_snapshot_command

    core = Path(os.environ.get("PLATFORMIO_CORE_DIR", str(Path.home() / ".platformio")))
    executable = core / "packages/tool-avrdude/avrdude"
    configuration = core / "packages/tool-avrdude/avrdude.conf"
    images: dict[str, Json] = {}
    for role, environment in [("GATEWAY", "sender_hello"), ("RECEIVER", "receiver")]:
        image = ROOT / ".pio/build" / environment / "firmware.hex"
        signature_path = proof.run_dir / f"{role.lower()}-live-signature.bin"
        serial_path = proof.run_dir / f"{role.lower()}-live-serial.bin"
        flash_path = proof.run_dir / f"{role.lower()}-live-flash.bin"
        code = read_snapshot_command(
            proof,
            f"{role.lower()}-image-readback",
            [
                str(executable),
                "-C",
                str(configuration),
                "-p",
                "avr128da28",
                "-c",
                "serialupdi",
                "-P",
                PORTS[role.lower()],
                "-b",
                "115200",
                "-D",
                "-U",
                f"signature:r:{signature_path}:r",
                "-U",
                f"sernum:r:{serial_path}:r",
                "-U",
                f"flash:r:{flash_path}:r",
            ],
            60,
        )
        if code != 0:
            return None
        try:
            data = image.read_bytes()
            region = parse_ihex_range(data)
            bounds = application_bounds_for_environment(effective_config, environment)
            flash = flash_path.read_bytes()
            identity = json.loads((ROOT / "config/current_hardware.json").read_text())[role.lower()]
            expected_serial = bytes.fromhex(identity["device_serial_hex"])
            if identity["port_path"] != PORTS[role.lower()]:
                return None
            if (
                signature_path.read_bytes().hex() != "1e970a"
                or len(flash) != 131072
                or serial_path.read_bytes() != expected_serial
                or not image_fits_application(region, bounds)
            ):
                return None
            start, end = region["start"], region["end_exclusive"]
            expected = normalize_ihex_region(data.decode("ascii"), start, end)
            if (
                flash[start:end] != expected
                or manifest["environments"][environment]["build_id"].encode() not in expected
            ):
                return None
            images[role] = {
                "origin": "PHYSICAL_UPDI",
                "run_id": run_id,
                "verified": True,
                "signature": "1e970a",
                "port": PORTS[role.lower()],
                "environment": environment,
                "serial_number": serial_path.read_bytes().hex(),
                "firmware_sha256": hashlib.sha256(data).hexdigest(),
                "readback_region_sha256": hashlib.sha256(flash[start:end]).hexdigest(),
                "build_id": manifest["environments"][environment]["build_id"],
                "start": start,
                "end": end,
            }
        except (OSError, ValueError, KeyError):
            return None
    proof.note("live-image-identities.json", json.dumps(images, indent=2) + "\n")
    return images


def shared_identity_matches(
    logs: Mapping[str, str], fingerprint: str, protocol_version: int | str
) -> bool:
    for role in ("GATEWAY", "RECEIVER"):
        lines = logs.get(role, "").splitlines()
        hashes = [line for line in lines if line.startswith(f"[{role}] CONFIG_FINGERPRINT=")]
        versions = [line for line in lines if line.startswith(f"[{role}] PROTOCOL_VERSION=")]
        if hashes != [f"[{role}] CONFIG_FINGERPRINT={fingerprint}"]:
            return False
        if versions != [f"[{role}] PROTOCOL_VERSION={protocol_version}"]:
            return False
    return True


def reserve_session(proof: ProofRun, run_id: str) -> int:
    import secrets

    used = set()
    for path in ARTIFACTS.glob("*/run-session.json"):
        try:
            used.add(json.loads(path.read_text())["session"])
        except (OSError, ValueError, KeyError, TypeError) as error:
            msg = f"unreadable prior session reservation: {path}"
            raise ValueError(msg) from error
    initial = secrets.randbelow(65535)
    for offset in range(65535):
        session = (initial + offset) % 65535 + 1
        if session not in used:
            proof.note(
                "run-session.json",
                json.dumps({"run_id": run_id, "session": session}) + "\n",
            )
            return session
    msg = "all 16-bit session IDs are reserved; no RF command issued"
    raise ValueError(msg)


def run_stable_ack_rf_test(
    proof: ProofRun,
    args: argparse.Namespace,
    run_id: str,
    images: Mapping[str, Json],
) -> int:
    """Run one current-API DATA/ACK or controlled DATA/NACK exchange."""
    diagnostic_test = getattr(args, "transport_test", None) or "T01"
    nack = diagnostic_test == "T02"
    output_queue: queue.Queue[tuple[str, str, bytes | None]] = queue.Queue()
    journal: list[dict[str, Json]] = []
    monitors: dict[str, dict[str, Any]] = {}
    capture_error = False
    stop_reason = ""
    started = False
    rearmed = False
    terminal_at: float | None = None
    deadline = time.monotonic() + RF_SINGLE_PACKET_TIMEOUT_SECONDS

    def record(role: str, line: str) -> None:
        journal.append({"role": role, "line": line, "observed_monotonic_ns": time.monotonic_ns()})

    def command(key: str, value: str) -> None:
        process = monitors[key]["process"]
        if process.poll() is not None or process.stdin is None:
            raise OSError("serial monitor disconnected before command")
        data = value.encode("ascii")
        if process.stdin.write(data) != len(data):
            raise OSError("incomplete serial control-command write")
        process.stdin.flush()
        record(f"HOST_{key.upper()}", value)

    try:
        monitors["receiver"] = start_rf_monitor(
            proof, "receiver", PORTS["receiver"], output_queue
        )
        command("receiver", "?")
        while time.monotonic() < deadline:
            try:
                key, stream, raw = output_queue.get(timeout=0.1)
            except queue.Empty:
                if terminal_at is not None and time.monotonic() - terminal_at >= RF_COMPLETION_LOG_SETTLE_SECONDS:
                    stop_reason = "single-packet capture settled"
                    break
                if any(monitor["process"].poll() is not None for monitor in monitors.values()):
                    stop_reason = "serial monitor disconnected"
                    capture_error = True
                    break
                continue
            if stream != "stdout" or raw is None:
                continue
            role = "GATEWAY" if key == "gateway" else "RECEIVER"
            line = raw.decode("ascii", errors="replace").rstrip("\r\n")
            if not line.startswith(f"[{role}] "):
                continue
            record(role, line)

            if "LOG_OVERFLOW" in line or (line.endswith("RADIO_NOT_READY") and not (key == "receiver" and not rearmed)):
                stop_reason = line
                break
            if key == "receiver" and line in ("[RECEIVER] RADIO_READY", "[RECEIVER] RADIO_NOT_READY") and not rearmed:
                if nack:
                    command("receiver", "N")
                command("receiver", "R")
                rearmed = True
            elif key == "receiver" and rearmed and line == "[RECEIVER] RX_READY" and "gateway" not in monitors:
                if getattr(args, "drop_response_once", False):
                    command("receiver", "D")
                monitors["gateway"] = start_rf_monitor(
                    proof, "gateway", PORTS["gateway"], output_queue
                )
                command("gateway", "R")
                command("gateway", "?")
            elif key == "gateway" and line == "[GATEWAY] RADIO_READY" and not started:
                command("gateway", "S")
                started = True

            if line.startswith("[GATEWAY] ACK_ACCEPTED "):
                if terminal_at is None:
                    terminal_at = time.monotonic()
            elif "TRANSACTION_FAILED" in line or "TX_TIMEOUT" in line:
                stop_reason = line
                break
        else:
            stop_reason = "timed out waiting for bounded stable transport proof"
    except (OSError, ValueError) as error:
        stop_reason = str(error)
        capture_error = True
    finally:
        for key in ("receiver", "gateway"):
            monitor = monitors.get(key)
            if monitor is not None and monitor["process"].poll() is None:
                try:
                    command(key, "P")
                except OSError:
                    capture_error = True
        park_deadline = time.monotonic() + 5
        while time.monotonic() < park_deadline and monitors:
            parked = [
                any(item["line"] == f"[{role}] PARKED E=0" for item in journal)
                for role in ("RECEIVER", "GATEWAY")
            ]
            if all(parked):
                break
            try:
                key, stream, raw = output_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if stream == "stdout" and raw:
                role = "GATEWAY" if key == "gateway" else "RECEIVER"
                line = raw.decode("ascii", errors="replace").rstrip("\r\n")
                if line.startswith(f"[{role}] "):
                    record(role, line)
        else:
            if monitors:
                capture_error = True
        codes = {key: stop_rf_monitor(monitor) for key, monitor in monitors.items()}

    unavailable = check_port_owners(proof, "rf-postflight")
    result = validate_stable_transport(journal, images, run_id, diagnostic_test)
    if stop_reason and terminal_at is None:
        result["issues"] = sorted(set([*result["issues"], stop_reason]))
    if unavailable or capture_error or any(code != 0 for code in codes.values()):
        result["issues"] = sorted(
            set([*result["issues"], "serial monitor or postflight check failed"])
        )
    passed = bool(result["valid"] and terminal_at is not None and not result["issues"])
    result.update(
        passed=passed,
        origin="PHYSICAL_RADIO" if passed else "UNPROVEN",
        single_packet_mode=True,
        continue_command_sent=False,
        timeout_seconds=RF_SINGLE_PACKET_TIMEOUT_SECONDS,
        stop_reason=stop_reason,
        monitor_exit_codes=codes,
    )
    proof.note("rf-test-events.json", json.dumps(journal, indent=2) + "\n")
    proof.note("rf-test.json", json.dumps(result, indent=2) + "\n")
    proof.note(
        "rf-test.log",
        ("PASS" if passed else "FAIL") + ": " + "; ".join(result["issues"]) + "\n",
    )
    return 0 if passed else 1


def run_wrong_destination_rf_test(
    proof: ProofRun, run_id: str, images: Mapping[str, Json]
) -> int:
    """Transmit ten test DATA frames to a nonlocal address and require RX discard only."""
    output_queue: queue.Queue[tuple[str, str, bytes | None]] = queue.Queue()
    journal: list[dict[str, Json]] = []
    monitors: dict[str, dict[str, Any]] = {}
    capture_error = False
    stop_reason = ""

    def record(role: str, line: str) -> None:
        journal.append({"role": role, "line": line, "observed_monotonic_ns": time.monotonic_ns()})

    def command(key: str, value: str) -> None:
        nonlocal capture_error
        process = monitors[key]["process"]
        if process.poll() is not None or process.stdin is None:
            capture_error = True
            raise OSError("serial monitor disconnected before control command")
        data = value.encode("ascii")
        if process.stdin.write(data) != len(data):
            capture_error = True
            raise OSError("incomplete serial control-command write")
        process.stdin.flush()
        record(f"HOST_{key.upper()}", value)

    def pump_until(after: int, predicate: Callable[[list[Json]], bool], reason: str) -> bool:
        nonlocal capture_error, stop_reason
        deadline = time.monotonic() + RF_SINGLE_PACKET_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if predicate(journal[after:]):
                return True
            if any(monitor["process"].poll() is not None for monitor in monitors.values()):
                capture_error = True
                stop_reason = "serial monitor disconnected"
                return False
            try:
                key, stream, raw = output_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if stream != "stdout" or raw is None:
                continue
            role = "GATEWAY" if key == "gateway" else "RECEIVER"
            line = raw.decode("ascii", errors="replace").rstrip("\r\n")
            if line.startswith(f"[{role}] "):
                record(role, line)
                if "LOG_OVERFLOW" in line:
                    stop_reason = f"{role} firmware log overflow"
                    return False
        if not predicate(journal[after:]):
            stop_reason = f"timeout waiting for {reason}"
            return False
        return True

    try:
        monitors["receiver"] = start_rf_monitor(
            proof, "receiver", PORTS["receiver"], output_queue
        )
        status_at = len(journal)
        command("receiver", "?")
        if not pump_until(
            status_at,
            lambda rows: any(
                row["line"] in ("[RECEIVER] RADIO_READY", "[RECEIVER] RADIO_NOT_READY")
                for row in rows
            ),
            "Receiver status",
        ):
            raise OSError(stop_reason or "Receiver status was not observed")
        rearm_at = len(journal)
        command("receiver", "R")
        if not pump_until(
            rearm_at,
            lambda rows: any(row["line"] == "[RECEIVER] RX_READY" for row in rows),
            "fresh Receiver RX_READY",
        ):
            raise OSError(stop_reason or "fresh Receiver RX_READY was not observed")
        monitors["gateway"] = start_rf_monitor(
            proof, "gateway", PORTS["gateway"], output_queue
        )
        command("gateway", "R")
        gateway_ready_at = len(journal)
        command("gateway", "?")
        if not pump_until(
            gateway_ready_at,
            lambda rows: any(row["line"] == "[GATEWAY] RADIO_READY" for row in rows),
            "Gateway RADIO_READY",
        ):
            raise OSError(stop_reason or "Gateway RADIO_READY was not observed")

        for trial in range(10):
            after = len(journal)
            command("gateway", "W")

            def completed(rows: list[Json]) -> bool:
                lines = [row["line"] for row in rows]
                return (
                    "[GATEWAY] WRONG_DEST_TX_BEGIN DST=2 TYPE=08 Q=1 APP=11" in lines
                    and "[GATEWAY] WRONG_DEST_TX_DONE" in lines
                    and any("RX_DISCARD_DEST SID=0000 " in line for line in lines)
                )

            if not pump_until(after, completed, f"wrong-destination trial {trial + 1}"):
                break
            if any(
                any(
                    f"[{role}] {event} " in row["line"]
                    for role in ("GATEWAY", "RECEIVER")
                    for event in (
                        "DATA_VALIDATED",
                        "ACK_TX_BEGIN",
                        "NACK_TX_BEGIN",
                        "ACK_ACCEPTED",
                        "NACK_RX",
                    )
                )
                for row in journal[after:]
            ):
                stop_reason = f"application delivery or response occurred in trial {trial + 1}"
                break
    except (OSError, ValueError) as error:
        stop_reason = str(error)
        capture_error = True
    finally:
        for key in ("receiver", "gateway"):
            monitor = monitors.get(key)
            if monitor is not None and monitor["process"].poll() is None:
                try:
                    command(key, "P")
                except OSError:
                    capture_error = True
        park_deadline = time.monotonic() + 5
        while time.monotonic() < park_deadline and monitors:
            parked = [
                any(item["line"] == f"[{role}] PARKED E=0" for item in journal)
                for role in ("RECEIVER", "GATEWAY")
            ]
            if all(parked):
                break
            try:
                key, stream, raw = output_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if stream == "stdout" and raw:
                role = "GATEWAY" if key == "gateway" else "RECEIVER"
                line = raw.decode("ascii", errors="replace").rstrip("\r\n")
                if line.startswith(f"[{role}] "):
                    record(role, line)
        else:
            if monitors:
                capture_error = True
        codes = {key: stop_rf_monitor(monitor) for key, monitor in monitors.items()}

    result = validate_wrong_destination_trials(journal, images, run_id)
    if stop_reason:
        result["issues"] = sorted(set([*result["issues"], stop_reason]))
    if capture_error or any(code != 0 for code in codes.values()):
        result["issues"] = sorted(
            set([*result["issues"], "serial monitor or postflight check failed"])
        )
    unavailable = check_port_owners(proof, "wrong-destination-postflight")
    if unavailable:
        result["issues"] = sorted(
            set([*result["issues"], "serial ports remain occupied after capture"])
        )
    passed = bool(result["valid"] and not result["issues"])
    result.update(
        passed=passed,
        origin="PHYSICAL_RADIO" if passed else "UNPROVEN",
        monitor_exit_codes=codes,
        stop_reason=stop_reason,
    )
    proof.note("wrong-destination-events.json", json.dumps(journal, indent=2) + "\n")
    proof.note("wrong-destination.json", json.dumps(result, indent=2) + "\n")
    proof.note(
        "wrong-destination.log",
        ("PASS" if passed else "FAIL") + ": " + "; ".join(result["issues"]) + "\n",
    )
    return 0 if passed else 1


def run_mvp_acceptance(
    proof: ProofRun, run_id: str, images: Mapping[str, Json]
) -> int:
    """Require ten one-shot DATA/ACK successes followed by ten destination drops."""
    normal = []
    for trial in range(1, 11):
        child = ProofRun(proof.run_dir / f"data-ack-{trial:02d}")
        options = argparse.Namespace(transport_test="T01", drop_response_once=False)
        code = run_stable_ack_rf_test(child, options, run_id, images)
        try:
            result = json.loads((child.run_dir / "rf-test.json").read_text())
        except (OSError, ValueError):
            result = {"valid": False, "issues": ["single-packet result is missing"]}
        normal.append({"trial": trial, "exit_code": code, "result": result})
        if code != 0:
            break

    wrong_destination = None
    if len(normal) == 10 and all(row["exit_code"] == 0 for row in normal):
        child = ProofRun(proof.run_dir / "wrong-destination")
        code = run_wrong_destination_rf_test(child, run_id, images)
        try:
            wrong_destination = json.loads(
                (child.run_dir / "wrong-destination.json").read_text()
            )
        except (OSError, ValueError):
            wrong_destination = {"passed": False, "issues": ["destination result is missing"]}
        wrong_destination["exit_code"] = code

    passed = (
        len(normal) == 10
        and all(row["exit_code"] == 0 for row in normal)
        and wrong_destination is not None
        and wrong_destination.get("exit_code") == 0
    )
    summary = {
        "passed": passed,
        "origin": "PHYSICAL_RADIO" if passed else "UNPROVEN",
        "data_ack_planned": 10,
        "data_ack_executed": len(normal),
        "data_ack_successes": sum(row["exit_code"] == 0 for row in normal),
        "data_ack_trials": normal,
        "wrong_destination": wrong_destination,
    }
    proof.note("mvp-acceptance.json", json.dumps(summary, indent=2) + "\n")
    proof.note("mvp-acceptance.log", ("PASS" if passed else "FAIL") + "\n")
    return 0 if passed else 1


def run_stable_campaign(proof: ProofRun, args: argparse.Namespace,
                        run_id: str, images: Mapping[str, Json]) -> int:
    """Gate physical NACK, lost-ACK and 10/100/1000 cases on each preceding result."""
    cases = [("T01", "T01", False), ("T02", "T02", False), ("lost-ACK", "T01", True)]
    cases += [(f"normal-{count}-{i + 1:04}", "T01", False)
              for count in (10, 100, 1000) for i in range(count)]
    results = []
    status = 0
    for name, test, drop in cases:
        options = argparse.Namespace(**vars(args))
        options.transport_test = test
        options.drop_response_once = drop
        child = ProofRun(proof.run_dir / name)
        status = run_stable_ack_rf_test(child, options, run_id, images)
        row = {"name": name, "exit_code": status, "evidence": str(child.run_dir)}
        path = child.run_dir / "rf-test.json"
        if path.exists():
            row["result"] = json.loads(path.read_text())
        results.append(row)
        with (proof.run_dir / "campaign-events.jsonl").open("a") as output:
            output.write(json.dumps(row) + "\n")
        if status:
            break
    summary = {"passed": status == 0 and len(results) == len(cases),
               "planned": len(cases), "executed": len(results), "cases": results}
    summary["successful"] = sum(row["exit_code"] == 0 for row in results)
    for field, source in (("data_tx", "attempts"), ("ack_tx", "ack_tx"),
                          ("nack_tx", "nack_tx"), ("retries", "retries"),
                          ("timeouts", "timeouts")):
        summary[field] = sum(row.get("result", {}).get(source, 0) for row in results)
    rtts = sorted(row["result"]["rtt_ms"] for row in results
                  if row["exit_code"] == 0 and row.get("result", {}).get("rtt_ms") is not None)
    summary["average_rtt_ms"] = sum(rtts) / len(rtts) if rtts else None
    for percentile in (95, 99):
        summary[f"p{percentile}_rtt_ms"] = rtts[(len(rtts) * percentile + 99) // 100 - 1] if rtts else None
    (proof.run_dir / "campaign.json").write_text(json.dumps(summary, indent=2) + "\n")
    return status


def rf_test(
    proof: ProofRun, args: argparse.Namespace, profile_ok: bool, effective_config: str
) -> int:
    # T01/T02 drive the current transport's R/S/N/P controls and header campaign ID.
    if (
        not profile_ok
        or not application_layout_verified(("sender_hello", "receiver"), effective_config)
        or not upload_ports_match(effective_config)
    ):
        proof.note(
            "rf-test.log",
            "BLOCKED: configuration/image layout/target paths invalid; no ports opened.\n",
        )
        return 2
    if (
        not args.boot_layout_verified
        and not args.target_identification_attempted
        and identify_targets(proof, args, effective_config) != 0
    ):
        return 2
    blockers = hardware_blockers(
        "rf-test",
        mapping_verified=args.physical_mapping_verified,
        power_verified=args.power_verified,
        boot_layout_verified=args.boot_layout_verified,
        authorized=args.authorize_rf_test,
        no_meter=getattr(args, "no_meter_mode", False),
    )
    if blockers:
        proof.note("rf-test.log", "BLOCKED: " + ", ".join(blockers) + "; no ports opened.\n")
        return 2
    if check_port_owners(proof, "rf-preflight"):
        return 2
    evidence_errors = physical_readiness_errors(args, require_rf=True)
    if evidence_errors:
        proof.note(
            "rf-test.log", "BLOCKED: " + "; ".join(evidence_errors) + "; no RF test attempted.\n"
        )
        return 2
    manifest = json.loads((ROOT / "generated/lora_manifest.json").read_text())
    if not upload_evidence_matches(getattr(args, "upload_evidence", None), manifest):
        proof.note(
            "rf-test.log",
            "BLOCKED: verified upload evidence is missing or mismatched; no monitors opened.\n",
        )
        return 2
    import secrets

    run_id = secrets.token_hex(16)
    diagnostic_test = getattr(args, "transport_test", None) or "T01"
    if getattr(args, "stable_transport", False) or getattr(args, "stable_campaign", False):
        if diagnostic_test not in ("T01", "T02"):
            proof.note("rf-test.log", "BLOCKED: stable transport supports T01/T02 only.\n")
            return 2
        images = verify_installed_images(proof, effective_config, manifest, run_id)
        if images is None:
            proof.note(
                "rf-test.log", "BLOCKED: installed images/signatures do not match current firmware.\n"
            )
            return 2
        if getattr(args, "mvp_acceptance", False):
            if (
                not getattr(args, "stable_transport", False)
                or getattr(args, "transport_test", None) is not None
            ):
                proof.note(
                    "rf-test.log",
                    "BLOCKED: MVP acceptance requires the stable transport with no single-test override.\n",
                )
                return 2
            return run_mvp_acceptance(proof, run_id, images)
        if getattr(args, "stable_campaign", False):
            return run_stable_campaign(proof, args, run_id, images)
        return run_stable_ack_rf_test(proof, args, run_id, images)
    try:
        session = reserve_session(proof, run_id)
    except ValueError as error:
        proof.note("rf-test.log", f"BLOCKED: {error}\n")
        return 2
    images = verify_installed_images(proof, effective_config, manifest, run_id)
    if images is None:
        proof.note(
            "rf-test.log", "BLOCKED: installed images/signatures do not match current firmware.\n"
        )
        return 2
    reverse = diagnostic_test in ("T03", "T04")
    nack = diagnostic_test in ("T02", "T04")
    receiver_key, sender_key = ("gateway", "receiver") if reverse else ("receiver", "gateway")
    receiver_role = "GATEWAY" if reverse else "RECEIVER"
    sender_role = "RECEIVER" if reverse else "GATEWAY"
    environments = {"GATEWAY": "sender_hello", "RECEIVER": "receiver"}
    symmetric = False
    journal: list[dict[str, Json]] = []
    monitors: dict[str, dict[str, Any]] = {}
    output_queue: queue.Queue[tuple[str, str, bytes | None]] = queue.Queue()
    deadline = time.monotonic() + RF_SINGLE_PACKET_TIMEOUT_SECONDS
    armed = False
    started = False
    capture_error = False
    completion_seen_at: float | None = None
    stop_reason = ""
    result: dict[str, Json] = {
        "valid": False,
        "issues": ["capture incomplete"],
        "origin": "UNPROVEN",
    }

    def record(role: str, line: str) -> None:
        journal.append({"role": role, "line": line, "observed_monotonic_ns": time.monotonic_ns()})

    def lines(role: str) -> list[str]:
        return [item["line"] for item in journal if item["role"] == role]

    def identity(role: str, environment: str) -> bool:
        captured = lines(role)
        expected = manifest["environments"][environment]["build_id"]
        return (
            radio_startup_matches(captured, role, manifest["shared"]["radio"])
            and (
                not getattr(args, "transport_test", None)
                or captured.count(f"[{role}] TRANSPORT=SSOT_SYMMETRIC_V1") == 1
            )
            and captured.count(f"[{role}] BUILD_ID={expected}") == 1
            and captured.count(f"[{role}] CONFIG_FINGERPRINT={manifest['shared_fingerprint']}") == 1
            and captured.count(
                f"[{role}] PROTOCOL_VERSION={manifest['shared']['protocol']['version']}"
            )
            == 1
        )

    def command(role: str, prefix: str) -> None:
        text = "P" if prefix == "P" else f"{prefix}{session:04X}"
        process = monitors[role]["process"]
        if (
            prefix != "P"
            and any(monitor["process"].poll() is not None for monitor in monitors.values())
        ) or process.stdin is None:
            msg = "monitor disconnected before control command"
            raise OSError(msg)
        written = process.stdin.write(text.encode("ascii"))
        if written != len(text):
            msg = "incomplete control-command write"
            raise OSError(msg)
        process.stdin.flush()
        record("HOST", text)

    try:
        monitors[receiver_key] = start_rf_monitor(
            proof, receiver_key, PORTS[receiver_key], output_queue
        )
        while time.monotonic() < deadline:
            try:
                role, stream, raw = output_queue.get(timeout=0.1)
            except queue.Empty:
                if (
                    completion_seen_at is not None
                    and time.monotonic() - completion_seen_at >= RF_COMPLETION_LOG_SETTLE_SECONDS
                ):
                    stop_reason = "single-packet capture settled"
                    break
                if any(monitor["process"].poll() is not None for monitor in monitors.values()):
                    stop_reason = "monitor disconnected"
                    capture_error = True
                    break
                continue
            if stream != "stdout" or raw is None:
                continue
            expected_role = "GATEWAY" if role == "gateway" else "RECEIVER"
            line = raw.decode("ascii", errors="replace").rstrip("\r\n")
            if not line.startswith(f"[{expected_role}] "):
                continue  # upditerm transport banners are not firmware evidence
            record(expected_role, line)
            symmetric = symmetric or "TRANSPORT=SSOT_SYMMETRIC_V1" in line
            if line.startswith("[GATEWAY] TEST_COMPLETED C=") and completion_seen_at is None:
                completion_seen_at = time.monotonic()
            if symmetric and any(
                name in line for name in ("TRANSACTION_COMPLETE ", "NACK_ACCEPTED ")
            ) and completion_seen_at is None:
                completion_seen_at = time.monotonic()
            expected_rejection = (
                nack and "TRANSACTION_FAILED " in line and "TYPE=09" in line and " E=0 " in line
            )
            if not expected_rejection and any(
                marker in line for marker in ("FAILED", "TEST_ALREADY_RUN", "TX_TIMEOUT")
            ):
                stop_reason = line
                break
            waiting_line = (
                "[GATEWAY] WAIT_START" if role == "gateway" else "[RECEIVER] WAIT_SESSION"
            )
            if role == receiver_key and line == waiting_line and not armed:
                if not identity(receiver_role, environments[receiver_role]):
                    stop_reason = "Receiver identity mismatch before arming"
                    break
                command(receiver_key, "N" if nack else "R")
                armed = True
            if line == f"[{receiver_role}] RX_READY" and sender_key not in monitors:
                if not armed or f"[{receiver_role}] SESSION_READY C={session:04X}" not in lines(
                    receiver_role
                ):
                    stop_reason = "Receiver readiness is not fresh"
                    break
                monitors[sender_key] = start_rf_monitor(
                    proof, sender_key, PORTS[sender_key], output_queue
                )
            if role == sender_key and line == waiting_line:
                if started or not identity(sender_role, environments[sender_role]):
                    stop_reason = "Gateway identity mismatch or repeated WAIT_START"
                    break
                command(sender_key, "S")
                started = True
            if started:
                result = validate_live_proof(
                    journal, manifest, images, run_id, session, diagnostic_test
                )
        else:
            stop_reason = "timed out waiting for single-packet proof"
    except (OSError, ValueError) as error:
        stop_reason = str(error)
        capture_error = True
    finally:
        if symmetric:
            for key in (receiver_key, sender_key):
                if key not in monitors:
                    continue
                try:
                    command(key, "P")
                except OSError:
                    capture_error = True
            park_deadline = time.monotonic() + 5
            while time.monotonic() < park_deadline:
                parked = [
                    any(item["line"] == f"[{name}] PARKED E=0" for item in journal)
                    for name in (receiver_role, sender_role)
                ]
                if all(parked):
                    break
                key, stream, raw = "", "", None
                try:
                    key, stream, raw = output_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if stream == "stdout" and raw:
                    record(
                        "GATEWAY" if key == "gateway" else "RECEIVER",
                        raw.decode("ascii", errors="replace").rstrip("\r\n"),
                    )
            else:
                capture_error = True
        codes = {role: stop_rf_monitor(monitor) for role, monitor in monitors.items()}
    unavailable = check_port_owners(proof, "rf-postflight")
    result = validate_live_proof(journal, manifest, images, run_id, session, diagnostic_test)
    accepted = result["valid"] and not unavailable and not capture_error
    result.update(
        passed=bool(accepted),
        origin="PHYSICAL_RADIO" if accepted else "UNPROVEN",
        single_packet_passed=bool(accepted),
        single_packet_mode=True,
        continue_command_sent=False,
        start_command_sent=started,
        timeout_seconds=RF_SINGLE_PACKET_TIMEOUT_SECONDS,
        stop_reason=stop_reason,
        monitor_exit_codes=codes,
        run_id=run_id,
        session=session,
        firmware_images=images,
        ports_clear_after_monitor=not unavailable,
    )
    proof.note("rf-event-journal.json", json.dumps(journal, indent=2) + "\n")
    proof.note("rf-measurements.json", json.dumps(result, indent=2) + "\n")
    proof.note(
        "rf-test-input.log",
        "\n".join(item["line"] for item in journal if item["role"] == "HOST") + "\n",
    )
    proof.note(
        "rf-test.log", ("PASS" if result["passed"] else "INCOMPLETE") + ": " + stop_reason + "\n"
    )
    return 0 if result["passed"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--stage",
        choices=(
            "all",
            "config",
            "host-tests",
            "builds",
            "target-identification",
            "radio-spi-smoke",
            "preflight",
            "upload",
            "tracker-app-upload",
            "rf-test",
            "boot-analysis",
            "receiver-boot-prepare",
            "receiver-boot-install",
            "receiver-boot-restore",
        ),
    )
    parser.add_argument(
        "--physical-mapping-verified",
        action="store_true",
        help="confirm current board-to-USB role mapping",
    )
    parser.add_argument(
        "--power-verified",
        action="store_true",
        help=(
            "confirm safe supply, common ground, UPDI wiring and no CP2102 backfeed; "
            "does not assert measurements"
        ),
    )
    parser.add_argument(
        "--rf-hardware-verified",
        action="store_true",
        help=(
            "confirm connected compatible antennas/modules and permitted RF power "
            "including antenna gain"
        ),
    )
    parser.add_argument(
        "--no-meter-mode",
        action="store_true",
        help=(
            "no instrument measurements; mapping, electrical safety and RF suitability "
            "confirmations remain required"
        ),
    )
    parser.add_argument(
        "--authorize-upload",
        action="store_true",
        help="authorize only the explicitly identified application image and page spans",
    )
    parser.add_argument("--target-role", choices=("receiver",))
    parser.add_argument("--target-serial", help="Tracker MCU serial to authorize")
    parser.add_argument("--image-sha256", help="Tracker application HEX SHA-256 to authorize")
    parser.add_argument("--page-start", type=lambda value: int(value, 0), help="Tracker app page start")
    parser.add_argument("--page-end", type=lambda value: int(value, 0), help="Tracker app page end")
    parser.add_argument("--gateway-target-serial", help="Gateway MCU serial to authorize")
    parser.add_argument("--gateway-image-sha256", help="Gateway application HEX SHA-256 to authorize")
    parser.add_argument(
        "--gateway-page-start", type=lambda value: int(value, 0), help="Gateway app page start"
    )
    parser.add_argument(
        "--gateway-page-end", type=lambda value: int(value, 0), help="Gateway app page end"
    )
    parser.add_argument(
        "--receiver-spi-image-sha256", help="Receiver SPI diagnostic HEX SHA-256 to authorize"
    )
    parser.add_argument(
        "--receiver-spi-page-start",
        type=lambda value: int(value, 0),
        help="Receiver SPI diagnostic page start",
    )
    parser.add_argument(
        "--receiver-spi-page-end",
        type=lambda value: int(value, 0),
        help="Receiver SPI diagnostic page end",
    )
    parser.add_argument(
        "--gateway-spi-image-sha256", help="Gateway SPI diagnostic HEX SHA-256 to authorize"
    )
    parser.add_argument(
        "--gateway-spi-page-start",
        type=lambda value: int(value, 0),
        help="Gateway SPI diagnostic page start",
    )
    parser.add_argument(
        "--gateway-spi-page-end",
        type=lambda value: int(value, 0),
        help="Gateway SPI diagnostic page end",
    )
    parser.add_argument("--authorize-rf-test", action="store_true")
    parser.add_argument(
        "--stable-transport",
        action="store_true",
        help="use current R/S/N/P stable-library firmware controls and logs",
    )
    parser.add_argument("--stable-campaign", action="store_true",
                        help="gate T01, T02, lost ACK and 10/100/1000 physical exchanges")
    parser.add_argument(
        "--mvp-acceptance",
        action="store_true",
        help="run ten intended DATA/ACK and ten wrong-destination trials",
    )
    parser.add_argument("--drop-response-once", action="store_true",
                        help="suppress one Receiver response for a stable transport timeout test")
    parser.add_argument(
        "--transport-test",
        choices=("T01", "T02", "T03", "T04"),
        help="T01 DATA/ACK, T02 controlled NACK, T03/T04 reverse; add --stable-transport for current R/S/N/P firmware",
    )
    parser.add_argument(
        "--single-packet",
        action="store_true",
        help="verify one DATA/ACK and withhold campaign continuation",
    )
    parser.add_argument(
        "--upload-evidence",
        type=Path,
        help="physical-upload.json from a verified upload; fresh readback is also required",
    )
    parser.add_argument(
        "--receiver-boot-package", type=Path, help="reviewed receiver-boot-overwrite-map.json"
    )
    parser.add_argument(
        "--receiver-boot-evidence",
        type=Path,
        help="physical receiver-boot-receipt.json; checked against fresh BOOT readback",
    )
    parser.add_argument(
        "--authorize-receiver-boot-page0",
        metavar="PACKAGE_SHA256",
        help="specific authorization for the exact reviewed package; required before BOOT writes",
    )
    parser.add_argument(
        "--authorize-receiver-boot-restore",
        metavar="RESTORE_HEX_SHA256",
        help="specific authorization to restore original page 0 only",
    )
    mode.add_argument(
        "--raw-mvp-logs",
        nargs=2,
        type=Path,
        metavar=("SENDER", "RECEIVER"),
        help="validate raw-MVP log structure separately from ACK/NACK campaigns",
    )
    args = parser.parse_args()
    if args.raw_mvp_logs:
        raw_result = parse_raw_mvp_logs(*(path.read_text() for path in args.raw_mvp_logs))
        print(json.dumps(raw_result, indent=2))
        return 0 if raw_result["passed"] else 1
    args.boot_layout_verified = False
    args.target_identification_attempted = False

    proof = new_run()
    config_code, effective_config = project_configuration(proof)
    profile_ok = valid_rf_profile_config(effective_config)
    stages: dict[str, Callable[[], int]] = {
        "config": lambda: config_code,
        "host-tests": lambda: host_tests(proof, effective_config),
        "builds": lambda: clean_builds(proof, effective_config),
        "boot-analysis": lambda: 0 if receiver_boot_handoff_supported(proof, args) else 2,
        "receiver-boot-prepare": lambda: prepare_receiver_boot(proof),
        "receiver-boot-install": lambda: program_receiver_boot(proof, args),
        "receiver-boot-restore": lambda: program_receiver_boot(proof, args, restore=True),
        "target-identification": lambda: identify_targets(proof, args, effective_config),
        "radio-spi-smoke": lambda: radio_spi_smoke(proof, args, effective_config),
        "preflight": lambda: read_only_preflight(proof, args, profile_ok, effective_config),
        "upload": lambda: upload(proof, args, profile_ok, effective_config),
        "tracker-app-upload": lambda: tracker_app_upload(proof, args, effective_config),
        "rf-test": lambda: rf_test(proof, args, profile_ok, effective_config),
    }
    selected = tuple(stages) if args.stage == "all" else (args.stage,)
    result = 0
    for stage in selected:
        code = stages[stage]()
        result = max(result, code)
        if code == 1:
            break
    print(f"Artifacts: {proof.run_dir.relative_to(ROOT)}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
