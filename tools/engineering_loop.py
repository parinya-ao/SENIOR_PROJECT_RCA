#!/usr/bin/env python3
"""Resume the single-packet hardware proof without repeating uncertain writes."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = Path("artifacts/engineering-loop")
STATE_FILE = STATE_DIR / "state.json"
LOCK_FILE = STATE_DIR / "run.lock"
PHYSICAL_PREFLIGHT = STATE_DIR / "physical-preflight.json"
RF_HARDWARE_EVIDENCE = STATE_DIR / "radio-hardware.json"
BACKUP_DIR = Path("artifacts/rf-proof/20261106T104722Z-target-backup")
PORTS = {
    "gateway": "/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0",
    "receiver": "/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0",
}
STAGES = (
    "CHECK_CURRENT_STATE", "WAITING_PHYSICAL_PREFLIGHT", "VERIFY_FLASH_LAYOUT",
    "RUN_SPI_SMOKE", "VERIFY_RADIO_HARDWARE", "PROGRAM_RECEIVER",
    "PROGRAM_SENDER", "START_RECEIVER", "SEND_SINGLE_PACKET", "VERIFY_DATA",
    "VERIFY_ACK", "DIAGNOSE_FAILURE", "SOFTWARE_REPAIR", "RETEST", "PROVEN",
    "BLOCKED_HARDWARE", "FAILED",
)
sys.path.insert(0, str(ROOT / 'tools/config'))
from validate_lora_ssot import load as load_lora_ssot
RF_PROFILE = dict(load_lora_ssot(ROOT / 'config/lora_system.json')['radio'], long_range=0)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _initial_state() -> dict:
    return {
        "schema_version": 1,
        "goal": "single_lora_data_ack",
        "stage": "CHECK_CURRENT_STATE",
        "status": "RUNNING",
        "completed_stages": [],
        "firmware_hashes": {},
        "physical_target_mapping": {},
        "latest_verified_mcu_signatures": {},
        "boot_execution_compatibility": {
            "gateway": "NOT_RUN; new image replaces the existing executable at 0x0000",
            "receiver": "UNVERIFIED; saved BOOT reset path to APPCODE 0x5800 has not been proven",
        },
        "backup_recovery": {
            "backup_hashes_verified": False,
            "full_flash_images_present": False,
            "restore_tested": False,
        },
        "upload_status": {"receiver": "NOT_RUN", "sender": "NOT_RUN"},
        "radio_spi_results": {"receiver": "NOT_RUN", "sender": "NOT_RUN"},
        "last_real_error": None,
        "retry_count": 0,
        "last_repair_description": None,
        "last_test_evidence": {},
        "campaign_session_id": None,
        "final_data_ack_result": "NOT_RUN",
        "active_action": None,
        "operator_resume_required": False,
        "updated_at": _now(),
    }


def _write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    fd, temp_name = tempfile.mkstemp(prefix="state.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _read_state(path: Path) -> dict:
    if not path.exists():
        return _initial_state()
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("schema_version") != 1 or state.get("goal") != "single_lora_data_ack":
        raise ValueError(f"unsupported or invalid state file: {path}")
    state = {**_initial_state(), **state}
    if state.get("stage") not in STAGES or not isinstance(state.get("completed_stages"), list):
        raise ValueError(f"invalid state stage or completion list: {path}")
    return state


def _manifest_entries(path: Path, base: Path) -> tuple[dict[str, str], list[str]]:
    entries: dict[str, str] = {}
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {}, [f"missing hash manifest {path}: {exc}"]
    for line in lines:
        if not line.strip():
            continue
        try:
            expected, name = line.split(None, 1)
            name = name.lstrip("*")
            image = Path(name)
            image = image if image.is_absolute() else base / image
            actual = hashlib.sha256(image.read_bytes()).hexdigest()
        except (ValueError, OSError) as exc:
            errors.append(f"invalid or unreadable manifest entry in {path}: {line}: {exc}")
            continue
        if actual.lower() != expected.lower():
            errors.append(f"hash mismatch: {image}")
        entries[name] = actual
    if not entries:
        errors.append(f"empty hash manifest: {path}")
    return entries, errors


def _latest_build_manifest(root: Path) -> Path | None:
    matches = sorted((root / "artifacts/rf-proof").glob("*/firmware-image-hashes.sha256"))
    return matches[-1] if matches else None


def _verify_recorded_state(root: Path) -> tuple[dict, dict, list[str]]:
    errors: list[str] = []
    backup = root / BACKUP_DIR
    backup_hashes, backup_errors = _manifest_entries(backup / "sha256.txt", backup)
    errors.extend(backup_errors)
    try:
        summary = json.loads((backup / "backup-summary.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        summary = {}
        errors.append(f"backup summary unreadable: {exc}")

    required_backup_files = {
        "gateway-candidate-backup-eeprom.bin", "gateway-candidate-backup-flash.bin",
        "gateway-candidate-backup-fuses.bin", "gateway-candidate-backup-signature.bin",
        "gateway-candidate-lock.bin", "gateway-candidate-serial-number.bin",
        "receiver-candidate-backup-eeprom.bin", "receiver-candidate-backup-flash.bin",
        "receiver-candidate-backup-fuses.bin", "receiver-candidate-backup-signature.bin",
        "receiver-candidate-flash-reread.bin", "receiver-candidate-lock.bin",
        "receiver-candidate-serial-number.bin",
    }
    missing_backups = required_backup_files - backup_hashes.keys()
    if missing_backups:
        errors.append("complete target backups are missing: " + ", ".join(sorted(missing_backups)))

    signatures = {}
    for role, candidate, port, bootsize, bodcfg in (
        ("gateway", "gateway-candidate", PORTS["gateway"], 0x00, 0x00),
        ("receiver", "receiver-candidate", PORTS["receiver"], 0x2C, 0x54),
    ):
        record = summary.get(candidate, {})
        signature = record.get("signature_hex")
        fuses = record.get("fuses_named", {})
        if record.get("port_path") != port or signature != "1E 97 0A":
            errors.append(f"{role} backup does not match the recorded target path/signature")
        if (fuses.get("bootsize") != bootsize or fuses.get("codesize") != 0 or
                fuses.get("bodcfg") != bodcfg or record.get("flash", {}).get("bytes") != 131072):
            errors.append(f"{role} backup has unexpected fuse or flash geometry")
        prefix = f"{candidate}-"
        flash_name, eeprom_name, fuse_name, sig_name = (
            prefix + "backup-flash.bin", prefix + "backup-eeprom.bin",
            prefix + "backup-fuses.bin", prefix + "backup-signature.bin")
        try:
            flash = (backup / flash_name).read_bytes()
            eeprom = (backup / eeprom_name).read_bytes()
            fuse_bytes = (backup / fuse_name).read_bytes()
            signature_bytes = (backup / sig_name).read_bytes()
            if len(flash) != 131072 or len(eeprom) != record.get("eeprom", {}).get("bytes"):
                errors.append(f"{role} Flash/EEPROM backup has an unexpected size")
            if hashlib.sha256(flash).hexdigest() != record.get("flash", {}).get("sha256"):
                errors.append(f"{role} Flash backup hash differs from its summary")
            if hashlib.sha256(eeprom).hexdigest() != record.get("eeprom", {}).get("sha256"):
                errors.append(f"{role} EEPROM backup hash differs from its summary")
            if fuse_bytes != bytes.fromhex(record.get("fuses_raw_16_hex", "")):
                errors.append(f"{role} fuse backup differs from its summary")
            if signature_bytes != bytes.fromhex(signature or ""):
                errors.append(f"{role} signature backup differs from its summary")
        except (OSError, ValueError) as exc:
            errors.append(f"{role} full backup could not be read/validated: {exc}")
        signatures[role] = {
            "signature": signature,
            "evidence": str(BACKUP_DIR / "backup-summary.json"),
            "live_rechecked_this_run": False,
        }
    reread_hash = backup_hashes.get("receiver-candidate-flash-reread.bin")
    receiver_flash_hash = backup_hashes.get("receiver-candidate-backup-flash.bin")
    if reread_hash != receiver_flash_hash:
        errors.append("receiver repeat Flash read does not match the stored backup")

    build_manifest = _latest_build_manifest(root)
    if build_manifest is None:
        build_hashes, build_errors = {}, ["firmware hash manifest not found"]
    else:
        build_hashes, build_errors = _manifest_entries(build_manifest, root)
    errors.extend(build_errors)
    firmware = {}
    for env in ("sender_hello", "receiver"):
        prefix = f".pio/build/{env}/firmware."
        env_hashes = {suffix: digest for name, digest in build_hashes.items()
                      if name.startswith(prefix) for suffix in (name[len(prefix):],)}
        if "hex" not in env_hashes or "elf" not in env_hashes:
            errors.append(f"{env} ELF/HEX hashes are missing from the build manifest")
        firmware[env] = env_hashes
    return firmware, signatures, errors


def _physical_preflight_errors(path: Path, *, no_meter=False, operation='write',
                               roles=('gateway', 'receiver')) -> list[str]:
    if operation not in ('diagnostic', 'write') or not roles or any(role not in PORTS for role in roles):
        return ['unknown physical operation or target role']
    if not path.exists():
        return [f"physical preflight evidence is missing: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"physical preflight evidence is unreadable: {exc}"]
    if not isinstance(data, dict):
        return ["physical preflight evidence must be a JSON object"]
    errors = []
    for key in (("operator",) if no_meter else ("operator", "measured_at", "instrument")):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"physical preflight must record {key}")
    # In no-meter mode fresh MCU serial comparison establishes the target mapping.
    if not no_meter and data.get("mapping_verified_by_operator") is not True:
        errors.append("physical board-role mapping must be confirmed by the operator")
    paths = data.get("usb_paths", {})
    if not isinstance(paths, dict):
        paths = {}
    if any(paths.get(role) != PORTS[role] for role in roles):
        errors.append("physical USB path mapping does not match current configuration")
    attestation = data.get('operator_safety_attestation', {})
    attested = (isinstance(attestation, dict) and
        attestation.get('origin') == 'OPERATOR_SAFETY_ATTESTATION' and
        attestation.get('considered_safe_for_normal_operation') is True and
        all(isinstance(attestation.get(key), str) and attestation[key].strip()
            for key in ('operator', 'recorded_at', 'source')) and
        isinstance(attestation.get('roles'), list) and
        all(isinstance(role, str) and role in PORTS for role in attestation['roles']))
    for role in roles:
        board = data.get(role, {})
        if not isinstance(board, dict):
            errors.append(f"{role} measurements must be a JSON object")
            continue
        if board.get('electrical_fault_reported') is True or board.get('operator_confirmed_safe') is False:
            errors.append(f'{role} has a reported unsafe condition; stop powered access')
        if no_meter:
            for key in ('powered_reported_by_operator', 'connected_reported_by_operator'):
                if board.get(key) is not True:
                    errors.append(f'{role} {key} requires operator confirmation')
            if operation == 'diagnostic':
                continue
            # The owner may assess an unmeasured setup; this never asserts inspected wiring.
            # Callers still verify live MCU identity and authorized page scope before writing.
            if attested and role in attestation['roles']:
                continue
        for key in (() if no_meter else ("mcu_vcc_v", "radio_vcc_v")):
            value = board.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                errors.append(f"{role} {key} must be a measured positive voltage")
        for key in ("power_source", "cp2102_vcc_arrangement"):
            if not isinstance(board.get(key), str) or not board[key].strip():
                errors.append(f"{role} {key} must be recorded")
        for key in ("operator_confirmed_safe", "common_ground_verified",
                    "updi_to_h1_pin5_verified", "cp2102_backfeed_safe",
                    "setup_unchanged_since_verification" if no_meter else "setup_unchanged_since_measurement"):
            if board.get(key) is not True:
                errors.append(f"{role} {key} requires operator verification")
    return errors


def _radio_hardware_errors(path: Path) -> list[str]:
    if not path.exists():
        return [f"module, antenna, and RF evidence is missing: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"radio hardware evidence is unreadable: {exc}"]
    if not isinstance(data, dict):
        return ["radio hardware evidence must be a JSON object"]
    errors = []
    for key in ("operator", "verified_at", "regulatory_reference"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"radio evidence must record {key}")
    if data.get("profile") != RF_PROFILE:
        errors.append("operator-verified RF profile must match the built SF7 profile exactly")
    regulatory = data.get("regulatory", {})
    if not isinstance(regulatory, dict):
        regulatory = {}
    if not isinstance(regulatory.get("equipment_conformity_reference"), str) or not regulatory["equipment_conformity_reference"].strip():
        errors.append("radio evidence must include an equipment conformity reference")
    limit = regulatory.get("max_eirp_dbm")
    if not isinstance(limit, (int, float)) or isinstance(limit, bool) or not math.isfinite(limit):
        errors.append("radio evidence must include a documented EIRP limit")
    for role in ("gateway", "receiver"):
        board = data.get(role, {})
        if not isinstance(board, dict):
            errors.append(f"{role} radio evidence must be a JSON object")
            continue
        for key in ("module_marking", "module_spec_reference", "antenna_model"):
            if not isinstance(board.get(key), str) or not board[key].strip():
                errors.append(f"{role} {key} must be documented")
        if board.get("antenna_path") not in ("SB1/SMA", "SB2/U.FL") or board.get("antenna_connected") is not True:
            errors.append(f"{role} antenna path must be physically identified and connected")
        for key in ("module_frequency_mhz", "antenna_frequency_mhz"):
            band = board.get(key)
            if (not isinstance(band, list) or len(band) != 2 or
                    not all(isinstance(x, (int, float)) and math.isfinite(x) for x in band) or
                    not band[0] <= RF_PROFILE["frequency_mhz"] <= band[1]):
                errors.append(f"{role} {key} must document support for 923 MHz")
        gain, loss = board.get("antenna_gain_dbi"), board.get("feed_loss_db")
        if not isinstance(gain, (int, float)) or isinstance(gain, bool) or not math.isfinite(gain):
            errors.append(f"{role} antenna gain must be documented")
        if not isinstance(loss, (int, float)) or isinstance(loss, bool) or not math.isfinite(loss) or loss < 0:
            errors.append(f"{role} feed loss must be documented")
        if isinstance(limit, (int, float)) and isinstance(gain, (int, float)) and isinstance(loss, (int, float)):
            if RF_PROFILE["tx_power_dbm"] + gain - loss > limit:
                errors.append(f"{role} calculated EIRP exceeds the documented limit")
    return errors


def _run_command(argv: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                                timeout=timeout, check=False)
        return result.returncode, result.stdout, result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 124, "", f"{type(exc).__name__}: {exc}"


def _artifact_path(output: str, root: Path) -> Path | None:
    match = re.search(r"^Artifacts: (.+)$", output, re.MULTILINE)
    if not match:
        return None
    path = Path(match.group(1).strip())
    return path if path.is_absolute() else root / path


def _resolve_port(path: str) -> tuple[str, bool]:
    resolved = Path(path).resolve(strict=False)
    return str(resolved), resolved.exists()


def _proof_action(state: dict, state_path: Path, root: Path,
                  command_runner: Callable, stage: str, flags: list[str],
                  timeout: int = 300, state_stage: str | None = None) -> tuple[int, Path | None, str]:
    argv = ["uv", "run", "python", "tools/rf_proof.py", "--stage", stage, *flags]
    state["stage"] = state_stage or stage.upper().replace("-", "_")
    state["status"] = "RUNNING"
    state["active_action"] = {"stage": state["stage"], "argv": argv, "started_at": _now()}
    _write_state(state_path, state)
    code, stdout, stderr = command_runner(argv, root, timeout)
    artifact = _artifact_path(stdout, root)
    evidence = {"stage": stage, "exit_code": code, "artifact_dir": str(artifact) if artifact else None}
    state["last_test_evidence"][stage] = evidence
    state["active_action"]["finished_at"] = _now()
    state["active_action"]["exit_code"] = code
    _write_state(state_path, state)
    return code, artifact, stdout + stderr


def _complete(state: dict, *stages: str) -> None:
    for stage in stages:
        if stage not in state["completed_stages"]:
            state["completed_stages"].append(stage)


def _block(state: dict, state_path: Path, stage: str, errors: list[str], *,
           operator_resume_required: bool = False) -> int:
    state["stage"] = stage
    state["status"] = "BLOCKED_HARDWARE"
    state["active_action"] = None
    state["operator_resume_required"] = operator_resume_required
    state["last_real_error"] = "; ".join(errors)
    _write_state(state_path, state)
    print(f"BLOCKED_HARDWARE at {stage}: {state['last_real_error']}")
    return 2


def run_controller(root: Path = ROOT,
                   command_runner: Callable = _run_command,
                   port_resolver: Callable = _resolve_port) -> int:
    root = Path(root).resolve()
    state_path = root / STATE_FILE
    lock_path = root / LOCK_FILE
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("BLOCKED: another engineering-loop controller is running")
            return 2
        try:
            state = _read_state(state_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"FAILED: cannot read state: {exc}")
            return 1

        if state.get("active_action"):
            state["stage"] = "BLOCKED_HARDWARE"
            state["status"] = "BLOCKED_HARDWARE"
            state["operator_resume_required"] = True
            state["last_real_error"] = (
                "controller restarted while an operation was in progress; outcome is unknown, "
                "so no flash or packet action was repeated")
            _write_state(state_path, state)
            print(f"BLOCKED_HARDWARE: inspect interrupted action {state['active_action'].get('stage')}; it was not repeated")
            return 2
        if state.get("operator_resume_required"):
            print("BLOCKED_HARDWARE: prior interrupted operation requires operator review; no action repeated")
            return 2
        if state.get("stage") in ("DIAGNOSE_FAILURE", "FAILED"):
            print(f"FAILED: review the recorded failure at {state['stage']}; no proof action repeated")
            return 1
        if state.get("status") == "RF_DATA_ACK_PROVEN":
            print("PROVEN: one correlated DATA/ACK is already recorded; no repeat transmission")
            return 0

        state["stage"] = "CHECK_CURRENT_STATE"
        state["status"] = "RUNNING"
        _write_state(state_path, state)
        firmware, signatures, errors = _verify_recorded_state(root)
        state["firmware_hashes"] = firmware
        state["latest_verified_mcu_signatures"] = signatures
        mapping = {}
        for role, path in PORTS.items():
            resolved, present = port_resolver(path)
            mapping[role] = {"usb_path": path, "resolved_device": resolved,
                             "present": present, "role_source": "operator-reported"}
            if not present:
                errors.append(f"{role} USB path is not currently present: {path}")
        state["physical_target_mapping"] = mapping
        if errors:
            state["stage"] = "FAILED"
            state["status"] = "FAILED"
            state["last_real_error"] = "; ".join(errors)
            _write_state(state_path, state)
            print(f"FAILED: {state['last_real_error']}")
            return 1
        state["backup_recovery"] = {
            "backup_hashes_verified": True,
            "full_flash_images_present": True,
            "restore_tested": False,
            "restore_note": "No destructive restore drill was run; backup integrity does not establish a tested recovery.",
        }
        _complete(state, "CHECK_CURRENT_STATE")
        _write_state(state_path, state)

        physical_path = root / PHYSICAL_PREFLIGHT
        physical_errors = _physical_preflight_errors(physical_path)
        if physical_errors:
            previous = state["last_test_evidence"].get("preflight", {})
            if not previous.get("artifact_dir"):
                code, artifact, output = _proof_action(
                    state, state_path, root, command_runner, "preflight",
                    ["--physical-mapping-verified"], timeout=60)
                preflight_log = artifact / "preflight.log" if artifact else None
                if preflight_log and preflight_log.exists():
                    status_line = next((line for line in preflight_log.read_text(errors="replace").splitlines()
                                        if line.startswith("BLOCKED:")), "")
                    blockers = {part.strip() for part in status_line.partition(":")[2].split(",") if part.strip()}
                    allowed = {"power conditions", "BOOTSIZE/CODESIZE/BODCFG fuse verification"}
                    if (code == 0 or "No serial ports opened." not in preflight_log.read_text(errors="replace")
                            or not blockers or not blockers.issubset(allowed)):
                        state["active_action"] = None
                        state["stage"] = "DIAGNOSE_FAILURE"
                        state["status"] = "FAILED"
                        state["last_real_error"] = output[-1200:] or "safe preflight returned an unexpected result"
                        _write_state(state_path, state)
                        print(f"DIAGNOSE_FAILURE during safe preflight: {state['last_real_error']}")
                        return 1
                state["last_test_evidence"]["preflight"] = {
                    "exit_code": code,
                    "artifact_dir": str(artifact) if artifact else None,
                    "serial_ports_opened": False,
                    "output_tail": output[-1200:],
                }
            state["active_action"] = None
            return _block(state, state_path, "WAITING_PHYSICAL_PREFLIGHT", physical_errors)

        if "VERIFY_FLASH_LAYOUT" not in state["completed_stages"]:
            code, artifact, output = _proof_action(
                state, state_path, root, command_runner, "target-identification",
                ["--physical-mapping-verified", "--power-verified"], timeout=180,
                state_stage="VERIFY_FLASH_LAYOUT")
            target_log = artifact / "target-identification.log" if artifact else None
            if code != 0 or target_log is None or not target_log.exists() or "PASS:" not in target_log.read_text(errors="replace"):
                state["active_action"] = None
                state["last_real_error"] = output[-1200:] or "live target signature/fuse/layout verification failed"
                state["stage"] = "DIAGNOSE_FAILURE"
                state["status"] = "FAILED"
                _write_state(state_path, state)
                print(f"DIAGNOSE_FAILURE at VERIFY_FLASH_LAYOUT: {state['last_real_error']}")
                return 1
            _complete(state, "VERIFY_FLASH_LAYOUT")
            state["active_action"] = None
            _write_state(state_path, state)

        if "RUN_SPI_SMOKE" not in state["completed_stages"]:
            code, artifact, output = _proof_action(
                state, state_path, root, command_runner, "radio-spi-smoke",
                ["--physical-mapping-verified", "--power-verified", "--authorize-upload"], timeout=300,
                state_stage="RUN_SPI_SMOKE")
            measurements = None
            if artifact and (artifact / "radio-spi-measurements.json").exists():
                measurements = json.loads((artifact / "radio-spi-measurements.json").read_text())
            if code != 0 or not measurements or measurements.get("status") != "PASS" or measurements.get("rf_transmission_enabled") is not False:
                state["radio_spi_results"] = {
                    "sender": measurements.get("devices", {}).get("gateway", {}).get("version", "NOT_RUN")
                    if measurements else "NOT_RUN",
                    "receiver": measurements.get("devices", {}).get("receiver", {}).get("version", "NOT_RUN")
                    if measurements else "NOT_RUN",
                }
                return _block(state, state_path, "RUN_SPI_SMOKE",
                              [output[-1200:] or "RF-disabled SPI smoke did not pass on both targets"],
                              operator_resume_required=True)
            state["radio_spi_results"] = {
                "sender": measurements.get("devices", {}).get("gateway", {}).get("version", "PASS"),
                "receiver": measurements.get("devices", {}).get("receiver", {}).get("version", "PASS"),
            }
            _complete(state, "RUN_SPI_SMOKE")
            state["active_action"] = None
            _write_state(state_path, state)

        radio_errors = _radio_hardware_errors(root / RF_HARDWARE_EVIDENCE)
        if radio_errors:
            return _block(state, state_path, "VERIFY_RADIO_HARDWARE", radio_errors)
        _complete(state, "VERIFY_RADIO_HARDWARE")

        if not {"PROGRAM_RECEIVER", "PROGRAM_SENDER"}.issubset(state["completed_stages"]):
            code, artifact, output = _proof_action(
                state, state_path, root, command_runner, "upload",
                ["--physical-mapping-verified", "--power-verified", "--authorize-upload",
                 "--authorize-rf-test"], timeout=300, state_stage="PROGRAM_RECEIVER")
            if code != 0:
                state["last_real_error"] = output[-1200:] or "guarded receiver/sender upload failed"
                state["stage"] = "DIAGNOSE_FAILURE"
                state["status"] = "FAILED"
                state["active_action"] = None
                state["operator_resume_required"] = True
                _write_state(state_path, state)
                print(f"DIAGNOSE_FAILURE at PROGRAM_RECEIVER: {state['last_real_error']}")
                return 1
            state["upload_status"] = {"receiver": "VERIFIED", "sender": "VERIFIED"}
            state['upload_evidence'] = str(artifact / 'physical-upload.json') if artifact else None
            _complete(state, "PROGRAM_RECEIVER", "PROGRAM_SENDER")
            state["active_action"] = None
            _write_state(state_path, state)

        state["stage"] = "START_RECEIVER"
        _write_state(state_path, state)
        code, artifact, output = _proof_action(
            state, state_path, root, command_runner, "rf-test",
            ["--single-packet", "--physical-mapping-verified", "--power-verified",
             "--authorize-rf-test", '--upload-evidence',
             str(state.get('upload_evidence') or root / 'MISSING-UPLOAD-EVIDENCE')], timeout=6 * 60 + 60, state_stage="START_RECEIVER")
        measurements = None
        if artifact and (artifact / "rf-measurements.json").exists():
            measurements = json.loads((artifact / "rf-measurements.json").read_text())
        if code == 0 and measurements and measurements.get("single_packet_passed") is True and measurements.get("continue_command_sent") is False:
            _complete(state, "START_RECEIVER", "SEND_SINGLE_PACKET", "VERIFY_DATA", "VERIFY_ACK", "PROVEN")
            state["stage"] = "PROVEN"
            state["status"] = "RF_DATA_ACK_PROVEN"
            state["final_data_ack_result"] = "PASS"
            state["last_real_error"] = None
            state["campaign_session_id"] = measurements.get("session")
            state["retry_count"] = measurements.get("retry_count", state["retry_count"])
            state["last_test_evidence"]["rf-test"] = {
                "artifact_dir": str(artifact), "single_packet_passed": True,
                "continue_command_sent": False,
            }
            state["active_action"] = None
            _write_state(state_path, state)
            print("PROVEN: one real sequence-1 DATA/ACK; continuation withheld")
            return 0

        state["stage"] = "DIAGNOSE_FAILURE"
        state["status"] = "FAILED"
        state["active_action"] = None
        state["operator_resume_required"] = True
        state["final_data_ack_result"] = "NOT_PROVEN"
        state["last_real_error"] = output[-1200:] or "single-packet RF proof did not complete"
        state["last_test_evidence"]["rf-test"] = {
            "artifact_dir": str(artifact) if artifact else None,
            "single_packet_passed": False,
            "continue_command_sent": bool(measurements and measurements.get("continue_command_sent")),
        }
        _write_state(state_path, state)
        print(f"DIAGNOSE_FAILURE: {state['last_real_error']}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="resume the next safe single-packet proof stage")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run is required")
    return run_controller()


if __name__ == "__main__":
    raise SystemExit(main())
