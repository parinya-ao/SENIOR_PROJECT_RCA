#!/usr/bin/env python3
"""Run host/build proof and keep hardware stages behind explicit gates."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "rf-proof"
ENVIRONMENTS = ("sender", "sender_hello", "receiver",
                "sender_hello_spi", "receiver_spi")
# Covers bounded SF7 airtime pacing across all four attempts per sequence.
RF_TEST_TIMEOUT_SECONDS = 6 * 60 * 60
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
) -> list[str]:
    blockers = []
    if not mapping_verified:
        blockers.append("physical board mapping")
    if not power_verified:
        blockers.append("power conditions")
    if not boot_layout_verified:
        blockers.append("BOOTSIZE/CODESIZE/BODCFG fuse verification")
    if not authorized:
        blockers.append("upload authorization" if stage in ("upload", "radio-spi-smoke")
                        else "RF-test authorization")
    return blockers


def parse_radio_spi_log(log_text: str, role: str) -> dict[str, object]:
    if role not in ("GATEWAY", "RECEIVER"):
        return {"role": role, "version": None, "tx_disabled": False,
                "passed": False, "issues": ["invalid role"]}
    prefix = f"[{role}] "
    versions = set()
    read_errors = []
    tx_disabled = False
    mismatch = False
    malformed = False
    for line in log_text.splitlines():
        if not line.startswith(prefix):
            continue
        message = line[len(prefix):]
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
    return (int(checks.group(1)) if checks else None,
            int(tests.group(1)) if tests else None)


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


def parse_rf_campaign(gateway_text: str, receiver_text: str) -> dict[str, object]:
    sources = {"GATEWAY": gateway_text, "RECEIVER": receiver_text}
    build_markers: dict[str, str] = {}
    records: list[dict[str, object]] = []
    issues: list[str] = []
    blocked_markers = (
        "RADIO_INIT_FAILED", "EEPROM_READBACK_FAILED",
        "TEST_ALREADY_RUN", "RADIO_PROFILE_MISMATCH", "TEST_FAILED",
    )

    for expected_role, text in sources.items():
        for line_number, line in enumerate(text.splitlines()):
            if any(marker in line for marker in blocked_markers):
                for marker in blocked_markers:
                    if marker in line:
                        issues.append(marker)
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
            (role, name, campaign_id, sequence, attempt, rtt, toa_us,
             payload_length, payload_hex, payload_ascii) = event.groups()
            if role != expected_role:
                issues.append(f"{expected_role.lower()} log has {role.lower()} event")
                continue
            records.append({
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
            })

    if build_markers.get("GATEWAY") != "sender_hello":
        issues.append("missing or wrong sender_hello build marker")
    if build_markers.get("RECEIVER") != "receiver":
        issues.append("missing or wrong receiver build marker")

    campaign_ids = {record["campaign_id"] for record in records}
    if len(campaign_ids) > 1:
        issues.append("multiple campaign IDs")
    campaign_id = next(iter(campaign_ids)) if len(campaign_ids) == 1 else None

    def matching(role: str, name: str, sequence: int | None = None):
        return [record for record in records
                if record["role"] == role and record["name"] == name
                and record["campaign_id"] == campaign_id
                and (sequence is None or record["sequence"] == sequence)]

    expected_payload_hex = EXPECTED_HELLO_PAYLOAD.hex().upper()

    def payload_bytes_match(record: dict[str, object]) -> bool:
        return (record["payload_length"] == len(EXPECTED_HELLO_PAYLOAD) and
                record["payload_hex"] == expected_payload_hex and
                record["payload_ascii"] == EXPECTED_HELLO_PAYLOAD.decode("ascii"))

    sender_payload_records = matching("GATEWAY", "DATA_PAYLOAD", 1)
    receiver_payload_records = matching("RECEIVER", "PAYLOAD_BYTES", 1)
    sender_payload_bytes_match = bool(sender_payload_records) and all(
        payload_bytes_match(record) for record in sender_payload_records)
    receiver_payload_bytes_match = bool(receiver_payload_records) and all(
        payload_bytes_match(record) for record in receiver_payload_records)
    if not sender_payload_bytes_match:
        issues.append("sender sequence-1 payload mismatch")
    if not receiver_payload_bytes_match:
        issues.append("receiver sequence-1 payload mismatch")

    payload_validated_sequences = [
        sequence for sequence in range(1, 21)
        if matching("RECEIVER", "PAYLOAD_MATCH", sequence)
    ]
    receiver_data_sequences = {
        record["sequence"]
        for event_name in ("DATA_RX", "DATA_DUP")
        for record in matching("RECEIVER", event_name)
        if record["sequence"] is not None
    }
    payload_unverified_sequences = sorted(
        receiver_data_sequences - set(payload_validated_sequences))
    for sequence in payload_unverified_sequences:
        issues.append(f"receiver payload unverified for sequence {sequence:02X}")

    delivered = []
    for sequence in range(1, 21):
        gateway_tx = matching("GATEWAY", "DATA_TX", sequence)
        gateway_done = matching("GATEWAY", "DATA_DONE", sequence)
        accepted_data = (matching("RECEIVER", "DATA_RX", sequence) or
                         matching("RECEIVER", "DATA_DUP", sequence))
        payload_match = matching("RECEIVER", "PAYLOAD_MATCH", sequence)
        ack_started = matching("RECEIVER", "ACK_TX", sequence)
        ack_done = matching("RECEIVER", "ACK_DONE", sequence)
        ack_received = matching("GATEWAY", "ACK_RX", sequence)
        if all((gateway_tx, gateway_done, accepted_data, payload_match,
                ack_started, ack_done, ack_received)):
            delivered.append(sequence)

    preflight_events = matching("GATEWAY", "PREFLIGHT_OK", 1)
    preflight_complete = (1 in delivered and bool(preflight_events) and
                          sender_payload_bytes_match and
                          receiver_payload_bytes_match)
    continue_events = matching("GATEWAY", "CAMPAIGN_CONTINUE")
    continued = bool(preflight_events and continue_events and
                     continue_events[0]["line"] > preflight_events[0]["line"])
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
    latencies = [record["rtt"] for record in ack_rx
                 if record["sequence"] in delivered and record["rtt"] is not None]
    latency_summary = ({
        "min": min(latencies), "max": max(latencies),
        "average": sum(latencies) / len(latencies),
    } if latencies else None)

    issues = list(dict.fromkeys(issues))
    passed = (preflight_complete and continued and campaign_complete and
              delivered == list(range(1, 21)) and not issues)
    return {
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
        "receiver_data_events": (len(matching("RECEIVER", "DATA_RX")) +
                                 len(matching("RECEIVER", "DATA_DUP"))),
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
        evidence.get("preflight_complete") and not evidence.get("issues") and
        evidence.get("data_tx_started") == 1 and
        evidence.get("data_tx_completed") == 1 and
        evidence.get("receiver_data_events") == 1 and
        evidence.get("ack_tx_started") == 1 and
        evidence.get("ack_tx_completed") == 1 and
        evidence.get("ack_rx") == 1 and evidence.get("retry_count") == 0
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


def identify_targets(proof: ProofRun, args: argparse.Namespace,
                     effective_config: str = "") -> int:
    args.target_identification_attempted = True
    args.boot_layout_verified = False
    if not args.physical_mapping_verified or not args.power_verified:
        missing = []
        if not args.physical_mapping_verified:
            missing.append("physical board mapping")
        if not args.power_verified:
            missing.append("power/UPDI wiring conditions")
        proof.note("target-identification.log",
                   "BLOCKED: " + ", ".join(missing) +
                   "; no serial ports opened.\n")
        return 2

    path_results = [
        (role, proof.command(f"identify-{role}-path", ["readlink", "-e", port])[0])
        for role, port in PORTS.items()
    ]
    unavailable_paths = unresolved_adapter_paths(path_results)
    unavailable_owners = check_port_owners(proof, "identify-preflight")
    if unavailable_paths or unavailable_owners:
        blockers = unavailable_paths + [
            f"{role} UPDI port occupied or owner check failed"
            for role in unavailable_owners
        ]
        proof.note("target-identification.log",
                   "BLOCKED: " + ", ".join(blockers) +
                   "; no serial ports opened.\n")
        return 2

    core_dir = Path(os.environ.get(
        "PLATFORMIO_CORE_DIR", str(Path.home() / ".platformio")))
    avrdude = core_dir / "packages" / "tool-avrdude" / "avrdude"
    avrdude_conf = core_dir / "packages" / "tool-avrdude" / "avrdude.conf"
    expected_fuses = {role: target_fuses(effective_config, role)
                      for role in PORTS}
    if any(values is None for values in expected_fuses.values()) or \
            not avrdude.is_file() or not avrdude_conf.is_file():
        proof.note("target-identification.log",
                   "BLOCKED: target-specific BOOT geometry or PlatformIO avrdude is unavailable; no serial ports opened.\n")
        return 2

    all_ok = True
    for role, port in PORTS.items():
        sib_code, sib_out, _ = proof.command(
            f"target-{role}-sib", ["uv", "run", "python", "-u",
                                   "third_party/upditerm/upditerm.py", "-i",
                                   port, "38400"], 20)
        if sib_code != 0 or not sib_out.strip():
            all_ok = False
            continue

        bootsize_path = proof.run_dir / f"target-{role}-bootsize.bin"
        codesize_path = proof.run_dir / f"target-{role}-codesize.bin"
        bodcfg_path = proof.run_dir / f"target-{role}-bodcfg.bin"
        avrdude_args = [
            str(avrdude), "-p", "avr128da28", "-C", str(avrdude_conf),
            "-c", "serialupdi", "-P", port, "-b", "115200", "-D",
            "-U", f"bootsize:r:{bootsize_path}:r",
            "-U", f"codesize:r:{codesize_path}:r",
            "-U", f"bodcfg:r:{bodcfg_path}:r",
        ]
        fuse_code, _, _ = proof.command(f"target-{role}-fuse-read",
                                        avrdude_args, 20)
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
            json.dumps({"expected": expected_fuses[role],
                        "observed": observed}, indent=2) + "\n")
        if not boot_fuses_match(observed, expected_fuses[role]):
            all_ok = False

    ports_after = check_port_owners(proof, "identify-postflight")
    all_ok = all_ok and not ports_after
    args.boot_layout_verified = all_ok
    if all_ok:
        proof.note("target-identification.log",
                   "PASS: both UPDI targets match AVR128DA28 and their configured BOOT/APPCODE/BOD fuses; no writes performed.\n")
        return 0
    proof.note("target-identification.log",
               "BLOCKED: SIB/MCU/BOOTSIZE/CODESIZE/BOD verification failed; no writes performed.\n")
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
        if not isinstance(entry, list) or len(entry) != 2 or \
                not isinstance(entry[0], str) or not isinstance(entry[1], list):
            return None
        values = {}
        for pair in entry[1]:
            if not isinstance(pair, list) or len(pair) != 2 or \
                    not isinstance(pair[0], str) or pair[0] in values:
                return None
            values[pair[0]] = pair[1]
        if entry[0] in sections:
            return None
        sections[entry[0]] = values
    return sections


def build_flag_defines(sections: dict[str, dict[str, object]],
                       environment: str, name: str) -> list[str] | None:
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
    "HELLO_RF_FREQUENCY_MHZ", "HELLO_RF_TX_POWER_DBM", "HELLO_RF_LONG_RANGE",
    "HELLO_RF_SPREADING_FACTOR", "HELLO_RF_BANDWIDTH_KHZ",
    "HELLO_RF_CODING_RATE", "HELLO_RF_SYNC_WORD",
    "HELLO_RF_PREAMBLE_SYMBOLS", "HELLO_RF_CRC_ENABLED",
    "HELLO_RF_IQ_INVERTED",
)


def _parse_rf_profile(raw: dict[str, str]) -> dict[str, object] | None:
    try:
        profile = {
            "frequency_mhz": float(raw["HELLO_RF_FREQUENCY_MHZ"].rstrip("fF")),
            "tx_power_dbm": int(raw["HELLO_RF_TX_POWER_DBM"], 0),
            "long_range": int(raw["HELLO_RF_LONG_RANGE"], 0),
            "spreading_factor": int(raw["HELLO_RF_SPREADING_FACTOR"], 0),
            "bandwidth_khz": int(raw["HELLO_RF_BANDWIDTH_KHZ"], 0),
            "coding_rate": int(raw["HELLO_RF_CODING_RATE"], 0),
            "sync_word": int(raw["HELLO_RF_SYNC_WORD"], 0),
            "preamble_symbols": int(raw["HELLO_RF_PREAMBLE_SYMBOLS"], 0),
            "crc_enabled": int(raw["HELLO_RF_CRC_ENABLED"], 0),
            "iq_inverted": int(raw["HELLO_RF_IQ_INVERTED"], 0),
        }
    except ValueError:
        return None

    if not (920.0 <= profile["frequency_mhz"] <= 925.0 and
            2 <= profile["tx_power_dbm"] <= 20 and
            profile["long_range"] == 0 and
            profile["spreading_factor"] == 7 and
            profile["bandwidth_khz"] == 125 and
            profile["coding_rate"] == 5 and
            profile["sync_word"] == 0x12 and
            profile["preamble_symbols"] == 8 and
            profile["crc_enabled"] == 1 and
            profile["iq_inverted"] == 0):
        return None
    return profile


def shared_rf_profile(config_text: str) -> dict[str, object] | None:
    sections = effective_project_sections(config_text)
    if sections is not None:
        profiles = []
        for environment in ENVIRONMENTS:
            values = {}
            for name in PROFILE_MACROS:
                definitions = build_flag_defines(sections, environment, name)
                if definitions is None or len(definitions) != 1:
                    return None
                values[name] = definitions[0]
            profiles.append(values)
        if any(profile != profiles[0] for profile in profiles[1:]):
            return None
        return _parse_rf_profile(profiles[0])

    sections_text = dict(re.findall(
        r"(?ms)^\[([^\]]+)\]\s*(.*?)(?=^\[|\Z)", config_text))
    base = sections_text.get("env", "")
    raw = {}
    for name in PROFILE_MACROS:
        values = re.findall(rf"(?m)^\s*-D{name}=([^\s]+)", base)
        if len(values) != 1:
            return None
        raw[name] = values[0]
    for environment in ENVIRONMENTS:
        body = sections_text.get(f"env:{environment}", "")
        if any(re.search(rf"-D{name}(?:=|\s)", body) for name in PROFILE_MACROS):
            return None
    return _parse_rf_profile(raw)


def valid_rf_profile_config(config_text: str) -> bool:
    if shared_rf_profile(config_text) is None:
        return False
    sections = effective_project_sections(config_text)
    if sections is not None:
        return build_flag_defines(sections, "sender_hello", "HELLO_TEST_MODE") == ["1"]

    sections_text = dict(re.findall(
        r"(?ms)^\[([^\]]+)\]\s*(.*?)(?=^\[|\Z)", config_text))
    sender_hello = sections_text.get("env:sender_hello", "")
    return "-DHELLO_TEST_MODE=1" in sender_hello


def radio_profile_compile_flags(config_text: str) -> list[str] | None:
    sections = effective_project_sections(config_text)
    if sections is None or not valid_rf_profile_config(config_text):
        return None
    definitions = []
    for name in PROFILE_MACROS:
        values = build_flag_defines(sections, "sender_hello", name)
        if values is None or len(values) != 1:
            return None
        definitions.append(f"-D{name}={values[0]}")
    return definitions


def rf_spi_diagnostic_config(config_text: str) -> bool:
    sections = effective_project_sections(config_text)
    if sections is None or not valid_rf_profile_config(config_text):
        return False
    if build_flag_defines(sections, "sender_hello", "HELLO_RF_DIAGNOSTIC_ONLY") != [] or \
            build_flag_defines(sections, "receiver", "HELLO_RF_DIAGNOSTIC_ONLY") != []:
        return False
    return (
        build_flag_defines(sections, "sender_hello_spi", "HELLO_RF_DIAGNOSTIC_ONLY") == ["1"] and
        build_flag_defines(sections, "receiver_spi", "HELLO_RF_DIAGNOSTIC_ONLY") == ["1"] and
        build_flag_defines(sections, "sender_hello_spi", "HELLO_TEST_MODE") == ["1"]
    )


def upload_config_preserves_flash(config_text: str) -> bool:
    effective = effective_project_sections(config_text)
    if effective is not None:
        for environment in ENVIRONMENTS:
            settings = effective.get(f"env:{environment}", {})
            flags = settings.get("upload_flags")
            if not isinstance(flags, list) or any(not isinstance(flag, str) for flag in flags):
                return False
            if settings.get("upload_protocol") != "serialupdi" or "-D" not in flags or \
                    "-e" in flags or any(flag == "-U" or flag.startswith("-U")
                                          for flag in flags):
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
        if "-D" not in flags or "-e" in flags or any(
                flag == "-U" or flag.startswith("-U") for flag in flags):
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
    return all(sections.get(f"env:{environment}", {}).get("upload_port") == port
               for environment, port in expected.items())


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
            raise ValueError("invalid Intel HEX record order or prefix")
        try:
            record = bytes.fromhex(raw_line[1:].decode("ascii"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("invalid Intel HEX encoding") from exc
        if len(record) < 5 or len(record) != record[0] + 5 or sum(record) & 0xff:
            raise ValueError("invalid Intel HEX length or checksum")
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
            raise ValueError(f"unsupported Intel HEX record type {record_type}")
    if not eof or lowest is None:
        raise ValueError("Intel HEX is missing data or EOF record")
    return {"start": lowest, "end_exclusive": highest_exclusive,
            "data_bytes": data_bytes}


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
    return values if all(value is not None for value in values.values()) else None


def application_bounds_for_environment(
    config_text: str, environment: str,
) -> tuple[int, int] | None:
    sections = effective_project_sections(config_text)
    role = {
        "sender": "gateway",
        "sender_hello": "gateway",
        "sender_hello_spi": "gateway",
        "receiver": "receiver",
        "receiver_spi": "receiver",
    }.get(environment)
    if not sections or role is None:
        return None
    layout = sections.get("target_layout", {})
    geometry = sections.get("flash_geometry", {})
    expected_fuses = target_fuses(config_text, role)
    app_start = _config_int(layout.get(f"{role}_app_start"))
    env_start = _config_int(
        sections.get(f"env:{environment}", {}).get("board_build.text_section_start"))
    app_end = _config_int(geometry.get("application_end"))
    flash_end = _config_int(geometry.get("total_bytes"))
    if not expected_fuses or app_start is None or env_start is None or \
            app_end is None or flash_end is None:
        return None
    # These targets use a full-BOOT Gateway and an APPCODE-only Receiver.
    if expected_fuses["codesize"] != 0:
        return None
    fuse_start = expected_fuses["bootsize"] * 512
    if app_start != fuse_start or env_start != fuse_start or \
            not fuse_start < app_end <= flash_end:
        return None
    return fuse_start, app_end


def image_fits_application(image_range: dict[str, int] | None,
                           bounds: tuple[int, int] | None) -> bool:
    return bool(image_range and bounds and
                image_range["start"] == bounds[0] and
                image_range["end_exclusive"] <= bounds[1])


def boot_fuses_match(actual: dict[str, int] | None,
                     expected: dict[str, int] | None) -> bool:
    return bool(actual and expected and
                all(actual.get(name) == expected[name]
                    for name in ("bootsize", "codesize", "bodcfg")))


def application_layout_verified(environments: tuple[str, ...],
                                effective_config: str) -> bool:
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
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=False)

    def command(self, name: str, argv: list[str], timeout: int | None = None):
        try:
            result = subprocess.run(argv, cwd=ROOT, capture_output=True,
                                    timeout=timeout, check=False)
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

    def note(self, name: str, content: str):
        data = content.encode()
        (self.run_dir / name).write_bytes(data)
        print(content, end="")


def new_run() -> ProofRun:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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
        binary = str(Path(temp_dir) / "lora_hello_test")
        compile_code, _, _ = proof.command("host-compile", [
            "g++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
            "-fsanitize=address,undefined", "-Isrc/shared",
            "tests/lora_hello_test.cpp", "src/shared/hello_protocol.cpp",
            "-o", binary,
        ])
        if compile_code != 0:
            return 1
        test_code, test_out, _ = proof.command("host-protocol-tests", [binary])
        if test_code != 0:
            return 1
        role_binary = str(Path(temp_dir) / "role_log_test")
        role_compile_code, _, _ = proof.command("role-log-compile", [
            "g++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
            "-Isrc/lib/updi_uart", "tests/role_log_test.cpp",
            "-o", role_binary,
        ])
        if role_compile_code != 0:
            return 1
        role_test_code, role_test_out, _ = proof.command(
            "role-log-tests", [role_binary])
        if role_test_code != 0:
            return 1
        wrapper_binary = str(Path(temp_dir) / "lora_wrapper_test")
        wrapper_compile_code, _, _ = proof.command("radio-wrapper-compile", [
            "g++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
            "-Itests/radio_stub", "-Isrc/lib/lora", "-Isrc/shared",
            *profile_flags,
            "tests/lora_wrapper_test.cpp", "src/lib/lora/lora.cpp",
            "-o", wrapper_binary,
        ])
        if wrapper_compile_code != 0:
            return 1
        wrapper_test_code, wrapper_test_out, _ = proof.command(
            "radio-wrapper-tests", [wrapper_binary])
        if wrapper_test_code != 0:
            return 1
        unit_code, unit_out, unit_err = proof.command("host-gate-tests", [
            sys.executable, "-m", "unittest", "discover", "-s", "tests",
            "-p", "test_rf_proof.py",
        ])
        checks, unit_count = parse_test_counts(test_out, unit_out + unit_err)
        role_checks = parse_role_log_count(role_test_out)
        wrapper_checks = parse_wrapper_check_count(wrapper_test_out)
        measurements = {
            "protocol_checks": checks,
            "role_log_checks": role_checks,
            "radio_wrapper_checks": wrapper_checks,
            "runner_unit_tests": unit_count,
        }
        (proof.run_dir / "host-measurements.json").write_text(
            json.dumps(measurements, indent=2) + "\n")
        return 0 if unit_code == 0 and all(measurements.values()) else 1


def firmware_measurement(env: str, output: bytes) -> dict[str, object]:
    build_dir = ROOT / ".pio" / "build" / env
    result: dict[str, object] = {"environment": env}
    for extension in ("hex", "elf"):
        path = build_dir / f"firmware.{extension}"
        if path.is_file():
            data = path.read_bytes()
            file_result: dict[str, object] = {
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            if extension == "hex":
                try:
                    file_result["address_range"] = parse_ihex_range(data)
                except ValueError as exc:
                    file_result["address_range_error"] = str(exc)
            result[extension] = file_result
    text = output.decode(errors="replace")
    for kind in ("RAM", "Flash"):
        match = re.search(
            rf"{kind}:\s*(?:\[[^\]]*\]\s*)?([\d.]+)%\s*"
            rf"\(used\s+(\d+)\s+bytes\s+from\s+(\d+)\s+bytes\)", text)
        if match:
            result[kind.lower()] = {
                "percent": float(match.group(1)),
                "used_bytes": int(match.group(2)),
                "total_bytes": int(match.group(3)),
            }
    return result


def clean_builds(proof: ProofRun, effective_config: str = "") -> int:
    measurements = []
    for env in ENVIRONMENTS:
        clean_code, _, _ = proof.command(f"{env}-clean", [
            "pio", "run", "-e", env, "-t", "clean",
        ])
        if clean_code != 0:
            return 1
        build_code, stdout, stderr = proof.command(f"{env}-build", [
            "pio", "run", "-e", env,
        ])
        if build_code != 0:
            return 1
        measurements.append(firmware_measurement(env, stdout + stderr))
    for env, measurement in zip(ENVIRONMENTS, measurements):
        hex_info = measurement.get("hex", {})
        address_range = hex_info.get("address_range")
        measurement["application_layout_safe"] = image_fits_application(
            address_range,
            application_bounds_for_environment(effective_config, env))
    layout = "SAFE: all HEX files start at their target fuse boundary and fit the application region.\n" if all(
        item["application_layout_safe"] for item in measurements) else \
        "BLOCKED: HEX range does not start at its target fuse boundary, exceeds the application region, or target geometry is unavailable.\n"
    proof.note("application-layout.log", layout)
    (proof.run_dir / "firmware-measurements.json").write_text(
        json.dumps(measurements, indent=2) + "\n")
    return 0


def capture_usb_topology(proof: ProofRun) -> None:
    commands = [
        ("usb-by-path-listing", ["ls", "-l", "/dev/serial/by-path/"]),
        ("usb-gateway-path", ["readlink", "-e", PORTS["gateway"]]),
        ("usb-receiver-path", ["readlink", "-e", PORTS["receiver"]]),
        ("usb-ttyUSB0-udev", ["udevadm", "info", "--query=property",
                              "--name=/dev/ttyUSB0"]),
        ("usb-ttyUSB1-udev", ["udevadm", "info", "--query=property",
                              "--name=/dev/ttyUSB1"]),
        ("usb-tree", ["lsusb", "-t"]),
        ("pio-device-list", ["pio", "device", "list"]),
        ("usb-port-owners", ["fuser", "-v", "/dev/ttyUSB0", "/dev/ttyUSB1"]),
        ("usb-role-scan", ["uv", "run", "python", "tools/detect_devices.py",
                            "--scan", "--json"]),
    ]
    for name, argv in commands:
        proof.command(name, argv)


def project_configuration(proof: ProofRun) -> tuple[int, str]:
    code, stdout, _ = proof.command(
        "pio-project-config", ["pio", "project", "config", "--json-output"])
    if code != 0:
        return 1, ""
    capture_usb_topology(proof)
    return 0, stdout.decode(errors="replace")


def read_only_preflight(proof: ProofRun, args: argparse.Namespace,
                        profile_ok: bool, effective_config: str) -> int:
    path_results = [
        (role, proof.command(f"preflight-{role}-path", ["readlink", "-e", port])[0])
        for role, port in PORTS.items()
    ]
    missing = unresolved_adapter_paths(path_results)
    unavailable = check_port_owners(proof, "preflight")
    missing.extend(f"{role} UPDI port occupied or owner check failed"
                   for role in unavailable)
    if not args.physical_mapping_verified:
        missing.append("physical board mapping")
    if not args.power_verified:
        missing.append("power conditions")
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


def upload(proof: ProofRun, args: argparse.Namespace, profile_ok: bool,
           effective_config: str) -> int:
    if not profile_ok:
        proof.note("upload.log", "BLOCKED: shared SF7 profile configuration is invalid; no upload attempted.\n")
        return 2
    if not args.authorize_upload:
        proof.note("upload.log", "BLOCKED: upload authorization is missing; no upload attempted.\n")
        return 2
    if not args.authorize_rf_test:
        proof.note("upload.log",
                   "BLOCKED: sender starts its bounded RF campaign at boot; RF-test authorization is missing, so no upload attempted.\n")
        return 2
    blockers = hardware_blockers(
        "upload", mapping_verified=args.physical_mapping_verified,
        power_verified=args.power_verified,
        boot_layout_verified=True,
        authorized=args.authorize_upload,
    )
    if blockers:
        proof.note("upload.log", "BLOCKED: " + ", ".join(blockers) + "; no upload attempted.\n")
        return 2
    if not application_layout_verified(("sender_hello", "receiver"), effective_config):
        proof.note("upload.log", "BLOCKED: firmware HEX is not verified inside its target executable region; no upload attempted.\n")
        return 2
    if not upload_config_preserves_flash(effective_config):
        proof.note("upload.log", "BLOCKED: upload config may erase or alter unrelated memory; no upload attempted.\n")
        return 2
    if not upload_ports_match(effective_config):
        proof.note("upload.log", "BLOCKED: effective upload ports do not match the verified Sender/Receiver paths; no upload attempted.\n")
        return 2
    if not args.boot_layout_verified and not args.target_identification_attempted:
        identity_code = identify_targets(proof, args, effective_config)
        if identity_code != 0:
            proof.note("upload.log", "BLOCKED: target identity/BOOT layout not verified; no upload attempted.\n")
            return identity_code
    if not args.boot_layout_verified:
        proof.note("upload.log", "BLOCKED: target identity/BOOT layout not verified; no upload attempted.\n")
        return 2
    unavailable = check_port_owners(proof, "upload-preflight")
    if unavailable:
        proof.note("upload.log", "BLOCKED: UPDI ports unavailable for " +
                   ", ".join(unavailable) + "; no upload attempted.\n")
        return 2
    for env in ("receiver", "sender_hello"):
        code, _, _ = proof.command(f"{env}-upload", ["pio", "run", "-e", env, "-t", "upload"])
        if code != 0:
            return 1
    return 0


def start_rf_monitor(proof: ProofRun, role: str, port: str,
                     output_queue: queue.Queue):
    argv = ["uv", "run", "python", "-u", "third_party/upditerm/upditerm.py",
            port, "38400"]
    (proof.run_dir / f"rf-monitor-{role}.command.log").write_text(
        " ".join(argv) + "\n")
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        argv, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, bufsize=0, start_new_session=True, env=environment,
    )
    threads = []
    for stream_name in ("stdout", "stderr"):
        stream = getattr(process, stream_name)

        def pump(name=stream_name, source=stream):
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


def stop_rf_monitor(monitor) -> int | None:
    if monitor is None:
        return None
    process = monitor["process"]
    if process.stdin and not process.stdin.closed:
        process.stdin.close()
    if process.poll() is None:
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
    for thread in monitor["threads"]:
        thread.join(timeout=2)
    return process.returncode


def capture_radio_spi_log(proof: ProofRun, role: str, port: str) -> dict[str, object]:
    output_queue: queue.Queue = queue.Queue()
    lines = []
    monitor = None
    monitor_error = None
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
                    line.startswith(f"[{role}] RADIO_SPI_READ") for line in lines)
                if evidence["tx_disabled"] and has_spi_result:
                    break
            else:
                print(f"[{role.lower()} upditerm] {line}",
                      file=sys.stderr, flush=True)
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


def radio_spi_smoke(proof: ProofRun, args: argparse.Namespace,
                    effective_config: str) -> int:
    if not rf_spi_diagnostic_config(effective_config):
        proof.note("radio-spi-smoke.log",
                   "BLOCKED: dedicated RF-disabled SPI diagnostic environments are missing; "
                   "no upload or serial ports opened.\n")
        return 2
    if not application_layout_verified(("sender_hello_spi", "receiver_spi"),
                                       effective_config):
        proof.note("radio-spi-smoke.log",
                   "BLOCKED: firmware HEX is not verified inside its target executable region; "
                   "no upload or serial ports opened.\n")
        return 2
    if not upload_config_preserves_flash(effective_config):
        proof.note("radio-spi-smoke.log",
                   "BLOCKED: effective upload config may erase or alter unrelated "
                   "memory; no upload attempted.\n")
        return 2
    if not upload_ports_match(effective_config):
        proof.note("radio-spi-smoke.log",
                   "BLOCKED: effective upload ports do not match the verified "
                   "Sender/Receiver paths; no upload attempted.\n")
        return 2
    if not args.boot_layout_verified and not args.target_identification_attempted:
        identity_code = identify_targets(proof, args, effective_config)
        if identity_code != 0:
            proof.note("radio-spi-smoke.log",
                       "BLOCKED: target identity/BOOT layout not verified; "
                       "no diagnostic upload attempted.\n")
            return identity_code
    if not args.boot_layout_verified:
        proof.note("radio-spi-smoke.log",
                   "BLOCKED: target identity/BOOT layout not verified; "
                   "no diagnostic upload attempted.\n")
        return 2
    blockers = hardware_blockers(
        "radio-spi-smoke", mapping_verified=args.physical_mapping_verified,
        power_verified=args.power_verified,
        boot_layout_verified=args.boot_layout_verified,
        authorized=args.authorize_upload,
    )
    if blockers:
        proof.note("radio-spi-smoke.log",
                   "BLOCKED: " + ", ".join(blockers) +
                   "; no diagnostic upload attempted.\n")
        return 2
    unavailable = check_port_owners(proof, "radio-spi-preflight")
    if unavailable:
        proof.note("radio-spi-smoke.log",
                   "BLOCKED: UPDI ports unavailable for " +
                   ", ".join(unavailable) + "; no diagnostic upload attempted.\n")
        return 2

    for env in ("receiver_spi", "sender_hello_spi"):
        code, _, _ = proof.command(
            f"{env}-radio-spi-diagnostic-upload",
            ["pio", "run", "-e", env, "-t", "upload"],
        )
        if code != 0:
            proof.note("radio-spi-smoke.log",
                       f"INCOMPLETE: {env} diagnostic upload failed; no RF test run.\n")
            return 1

    results = {
        "gateway": capture_radio_spi_log(proof, "GATEWAY", PORTS["gateway"]),
        "receiver": capture_radio_spi_log(proof, "RECEIVER", PORTS["receiver"]),
    }
    ports_after = check_port_owners(proof, "radio-spi-postflight")
    report = {
        "status": "PASS" if all(result["passed"] for result in results.values())
                  and not ports_after else "INCOMPLETE",
        "rf_transmission_enabled": False,
        "ports_still_unavailable": ports_after,
        "devices": results,
    }
    (proof.run_dir / "radio-spi-measurements.json").write_text(
        json.dumps(report, indent=2) + "\n")
    if report["status"] == "PASS":
        proof.note("radio-spi-smoke.log",
                   "PASS: both radios returned a supported SPI version in RF-disabled diagnostic firmware.\n")
        return 0
    proof.note("radio-spi-smoke.log",
               "INCOMPLETE: radio SPI response or diagnostic TX-disabled marker was not verified; "
               "no RF test was run.\n")
    return 2


def rf_test(proof: ProofRun, args: argparse.Namespace, profile_ok: bool,
            effective_config: str) -> int:
    single_packet = bool(getattr(args, "single_packet", False))
    if not profile_ok:
        proof.note("rf-test.log", "BLOCKED: shared SF7 profile configuration is invalid; no RF test or port open attempted.\n")
        return 2
    if not application_layout_verified(("sender_hello", "receiver"), effective_config):
        proof.note("rf-test.log", "BLOCKED: firmware HEX is not verified inside its target executable region; no RF test or port open attempted.\n")
        return 2
    if not upload_ports_match(effective_config):
        proof.note("rf-test.log",
                   "BLOCKED: effective upload ports do not match the verified "
                   "Sender/Receiver paths; no RF test or port open attempted.\n")
        return 2
    if not args.boot_layout_verified and not args.target_identification_attempted:
        identity_code = identify_targets(proof, args, effective_config)
        if identity_code != 0:
            proof.note("rf-test.log", "BLOCKED: target identity/BOOT layout not verified; no RF test attempted.\n")
            return identity_code
    if not args.boot_layout_verified:
        proof.note("rf-test.log", "BLOCKED: target identity/BOOT layout not verified; no RF test attempted.\n")
        return 2
    blockers = hardware_blockers(
        "rf-test", mapping_verified=args.physical_mapping_verified,
        power_verified=args.power_verified,
        boot_layout_verified=args.boot_layout_verified,
        authorized=args.authorize_rf_test,
    )
    if blockers:
        proof.note("rf-test.log", "BLOCKED: " + ", ".join(blockers) + "; no RF test or port open attempted.\n")
        return 2
    unavailable = check_port_owners(proof, "rf-preflight")
    if unavailable:
        proof.note("rf-test.log", "BLOCKED: UPDI ports unavailable for " +
                   ", ".join(unavailable) + "; no RF test or port open attempted.\n")
        return 2

    output_queue: queue.Queue = queue.Queue()
    log_lines = {"gateway": [], "receiver": []}
    monitors = {}
    stop_reason = ""
    continue_sent = False
    receiver_ready = False
    monitor_error = False
    campaign_completed_at = None
    deadline = time.monotonic() + RF_TEST_TIMEOUT_SECONDS

    def consume(item):
        role, stream_name, raw_line = item
        if raw_line is None:
            return ""
        line = raw_line.decode(errors="replace").rstrip("\r\n")
        if stream_name == "stdout":
            log_lines[role].append(line)
            print(f"[{role}] {line}", flush=True)
        else:
            print(f"[{role} upditerm] {line}", file=sys.stderr, flush=True)
        return line

    try:
        # The receiver is already listening; attach its monitor before starting the gateway.
        monitors["receiver"] = start_rf_monitor(
            proof, "receiver", PORTS["receiver"], output_queue)
        while time.monotonic() < deadline and not receiver_ready:
            try:
                item = output_queue.get(timeout=0.1)
            except queue.Empty:
                item = None
            if item is not None:
                line = consume(item)
                if "[RECEIVER] RADIO_INIT_FAILED" in line:
                    stop_reason = "receiver radio did not become ready"
                    break
                if "[RECEIVER] BOOT receiver " in line:
                    receiver_ready = True
                    # Wait for the initialization result before starting the Sender.
                    while time.monotonic() < deadline:
                        if any("[RECEIVER] RADIO_READY" in entry or
                               "[RECEIVER] RADIO_INIT_FAILED" in entry
                               for entry in log_lines["receiver"]):
                            break
                        try:
                            next_item = output_queue.get(timeout=0.1)
                        except queue.Empty:
                            continue
                        next_line = consume(next_item)
                        if "[RECEIVER] RADIO_INIT_FAILED" in next_line:
                            receiver_ready = False
                            stop_reason = "receiver radio did not become ready"
                            break
                    receiver_ready = receiver_ready and any(
                        "[RECEIVER] RADIO_READY" in entry
                        for entry in log_lines["receiver"])
            receiver_process = monitors["receiver"]["process"]
            if receiver_process.poll() is not None and not receiver_ready:
                monitor_error = receiver_process.returncode != 0
                stop_reason = "receiver monitor exited before its ready marker"
                break

        if not receiver_ready:
            if not stop_reason:
                stop_reason = "timed out waiting for receiver boot and RADIO_READY markers"
        else:
            monitors["gateway"] = start_rf_monitor(
                proof, "gateway", PORTS["gateway"], output_queue)
            while time.monotonic() < deadline:
                try:
                    item = output_queue.get(timeout=0.1)
                except queue.Empty:
                    item = None
                if item is not None:
                    line = consume(item)
                    if "[GATEWAY] RADIO_INIT_FAILED" in line or \
                            "[GATEWAY] TEST_ALREADY_RUN" in line:
                        stop_reason = line
                        break
                    if "[GATEWAY] WAIT_CAMPAIGN" in line:
                        waiting_evidence = parse_rf_campaign(
                            "\n".join(log_lines["gateway"]),
                            "\n".join(log_lines["receiver"]))
                        if (not waiting_evidence["preflight_complete"] or
                                waiting_evidence["issues"]):
                            stop_reason = (
                                "Gateway reached campaign wait without verified "
                                "sequence-1 payload/DATA/ACK evidence")
                            break

                evidence = parse_rf_campaign(
                    "\n".join(log_lines["gateway"]),
                    "\n".join(log_lines["receiver"]))
                if (evidence["preflight_complete"] and not continue_sent and
                        not evidence["issues"]):
                    if single_packet:
                        stop_reason = (
                            "single DATA/ACK verified; campaign continuation withheld"
                            if single_packet_evidence_passed(evidence) else
                            "sequence-1 was not exactly one DATA/ACK attempt")
                        break
                    gateway_stdin = monitors["gateway"]["process"].stdin
                    try:
                        gateway_stdin.write(b"C")
                        gateway_stdin.flush()
                    except (BrokenPipeError, OSError) as exc:
                        stop_reason = f"could not continue campaign after preflight: {exc}"
                        monitor_error = True
                        break
                    (proof.run_dir / "rf-test-input.log").write_text(
                        "Sent C to Gateway only after correlated seq 1 DATA/ACK proof.\n")
                    continue_sent = True
                if evidence["passed"]:
                    break
                if evidence["campaign_complete"]:
                    if campaign_completed_at is None:
                        campaign_completed_at = time.monotonic()
                    elif (time.monotonic() - campaign_completed_at >=
                          RF_COMPLETION_LOG_SETTLE_SECONDS):
                        stop_reason = (
                            "Gateway reported TEST_COMPLETED with incomplete "
                            "payload/DATA/ACK evidence")
                        break
                if "TEST_FAILED" in evidence["issues"]:
                    stop_reason = "Gateway reported TEST_FAILED before campaign acceptance"
                    break
                gateway_process = monitors["gateway"]["process"]
                if gateway_process.poll() is not None:
                    monitor_error = gateway_process.returncode != 0
                    stop_reason = "Gateway monitor exited before campaign completion"
                    break
            else:
                stop_reason = "timed out before 20 correlated DATA/ACK deliveries"
    except OSError as exc:
        monitor_error = True
        stop_reason = f"could not start UPDI monitors: {exc}"
    finally:
        monitor_codes = {
            role: stop_rf_monitor(monitor)
            for role, monitor in monitors.items()
        }

    gateway = "\n".join(log_lines["gateway"])
    receiver = "\n".join(log_lines["receiver"])
    evidence = parse_rf_campaign(gateway, receiver)
    ports_after = check_port_owners(proof, "rf-postflight")
    result = dict(evidence)
    campaign_passed = bool(evidence["passed"])
    one_packet_passed = single_packet_evidence_passed(evidence) if single_packet else False
    result.update({
        "single_packet_mode": single_packet,
        "single_packet_passed": one_packet_passed,
        "campaign_passed": campaign_passed,
        "passed": one_packet_passed if single_packet else campaign_passed,
        "continue_command_sent": continue_sent,
        "timeout_seconds": RF_TEST_TIMEOUT_SECONDS,
        "monitor_exit_codes": monitor_codes,
        "ports_clear_after_monitor": not ports_after,
        "ports_still_unavailable": ports_after,
        "stop_reason": stop_reason,
    })
    (proof.run_dir / "rf-measurements.json").write_text(
        json.dumps(result, indent=2) + "\n")
    delivered = len(evidence["delivery_sequences"])
    if single_packet and one_packet_passed and not continue_sent and not ports_after:
        (proof.run_dir / "rf-test-input.log").write_text(
            "Single-packet mode withheld campaign continuation; no C command sent.\n")
        proof.note("rf-test.log",
                   "PASS: one sequence-1 Hello World DATA/ACK; no campaign continuation sent.\n")
        return 0
    if evidence["passed"] and continue_sent and not ports_after:
        proof.note("rf-test.log", "PASS: 20/20 correlated DATA/ACK deliveries.\n")
        return 0
    status = (f"INCOMPLETE: sequence-1 one-packet proof not established"
              if single_packet else
              f"INCOMPLETE: {delivered}/20 confirmed deliveries")
    if stop_reason:
        status += f"; {stop_reason}"
    elif evidence["issues"]:
        status += "; " + ", ".join(evidence["issues"])
    elif ports_after:
        status += "; UPDI ports remain occupied after monitor cleanup"
    proof.note("rf-test.log", status + "; hardware proof NOT PASS.\n")
    return 1 if monitor_error else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("all", "config", "host-tests", "builds",
                        "target-identification", "radio-spi-smoke", "preflight",
                        "upload", "rf-test"), default="all")
    parser.add_argument("--physical-mapping-verified", action="store_true")
    parser.add_argument("--power-verified", action="store_true")
    parser.add_argument("--authorize-upload", action="store_true")
    parser.add_argument("--authorize-rf-test", action="store_true")
    parser.add_argument("--single-packet", action="store_true",
                        help="verify one DATA/ACK and withhold campaign continuation")
    args = parser.parse_args()
    args.boot_layout_verified = False
    args.target_identification_attempted = False

    proof = new_run()
    config_code, effective_config = project_configuration(proof)
    profile_ok = valid_rf_profile_config(effective_config)
    stages = {
        "config": lambda: config_code,
        "host-tests": lambda: host_tests(proof, effective_config),
        "builds": lambda: clean_builds(proof, effective_config),
        "target-identification": lambda: identify_targets(proof, args, effective_config),
        "radio-spi-smoke": lambda: radio_spi_smoke(proof, args, effective_config),
        "preflight": lambda: read_only_preflight(
            proof, args, profile_ok, effective_config),
        "upload": lambda: upload(proof, args, profile_ok, effective_config),
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
