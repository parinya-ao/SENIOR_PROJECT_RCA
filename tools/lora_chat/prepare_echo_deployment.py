"""Build and package a reversible laboratory Echo replacement without writing hardware."""

from __future__ import annotations

import json
import os
from hashlib import sha256
from shutil import copyfile
from typing import Any

from tools import installed_rf, production_bench as bench, rf_proof as rf
from tools.device_detection.firmware_identity import normalize_ihex_region
from tools.device_detection.flash_layout import Section, page_write_range
from tools.lora_chat.cli import ROOT, _create_run_directory
from tools.lora_chat.session import load_chat_settings
from tools.receiver_boot import AVRDUDE, AVRDUDE_CONF, PAGE_SIZE, ihex, read_snapshot


def package_target(
    proof: rf.ProofRun,
    effective: str,
    role: str,
    environment: str,
    snapshot: dict[str, bytes],
    legacy: dict[str, Any],
) -> dict[str, Any]:
    """Bind exact install and rollback pages to the freshly verified MCU and Flash layout."""
    run = proof.run_dir
    image_layout = rf.firmware_image_bounds_for_environment(effective, environment)
    if image_layout is None:
        raise ValueError(f"{role}: firmware has no validated image layout")
    layout, section, _, _ = image_layout
    if section is not Section.BOOT or layout.bootsize_pages or layout.codesize_pages:
        raise ValueError(f"{role}: this package requires the original all-BOOT bench layout")
    source = (ROOT / ".pio/build" / environment / "firmware.hex").read_bytes()
    region = rf.parse_ihex_range(source)
    span = page_write_range(layout, section, region["start"], region["end_exclusive"])
    if span is None or span[0] != 0 or span[1] > 65536:
        raise ValueError(f"{role}: firmware exceeds the supported laboratory page range")
    start, end = span
    proposed = normalize_ihex_region(source.decode("ascii"), start, end)
    echo = run / f"{role}-echo-pages.hex"
    rollback = run / f"{role}-restore-pages.hex"
    for path, contents in ((echo, proposed), (rollback, snapshot["flash"][start:end])):
        path.write_text(ihex(contents, start), encoding="ascii")
        if normalize_ihex_region(path.read_text(), start, end) != contents:
            raise ValueError(f"{role}: page package does not round-trip")
    (run / f"{role}-firmware.hex").write_bytes(source)

    common = [str(AVRDUDE), "-N", "-C", str(AVRDUDE_CONF), "-p", "avr128da28"]
    erase = [
        argument
        for address in range(start, end, PAGE_SIZE)
        for argument in ("-T", f"pgerase flash {address:#x}")
    ] + ["-T", "flush"]
    install = ["-U", f"flash:w:{echo}:i", "-U", f"flash:v:{echo}:i"]
    restore = ["-U", f"flash:w:{rollback}:i", "-U", f"flash:v:{rollback}:i"]
    physical = common + [
        "-c",
        "serialupdi",
        "-P",
        legacy["port"],
        "-b",
        "115200",
        "-D",
        "-U",
        f"sernum:v:{run / environment}-sernum.bin:r",
        "-U",
        f"fuses:v:{run / environment}-fuses.bin:r",
    ]
    original_flash = run / f"{environment}-flash.bin"
    expected_flash = run / f"{role}-expected-full-flash.bin"
    expected_flash.write_bytes(proposed + snapshot["flash"][end:])
    simulation = common + ["-c", "dryrun", "-D", "-U", f"flash:w:{original_flash}:r"]
    code, _, _ = proof.command(
        f"{role}-programmer-simulation",
        simulation
        + erase
        + install
        + ["-U", f"flash:v:{expected_flash}:r"]
        + erase
        + restore
        + ["-U", f"flash:v:{original_flash}:r"],
        30,
    )
    return {
        "serial": snapshot["sernum"].hex(),
        "signature": snapshot["signature"].hex(),
        "port": legacy["port"],
        "fuses": snapshot["fuses"].hex(),
        "section": "BOOT",
        "start": start,
        "end_exclusive": end,
        "legacy_build_id": legacy["build_id"],
        "environment": environment,
        "firmware_hex_sha256": sha256(source).hexdigest(),
        "install_page_hex_sha256": sha256(echo.read_bytes()).hexdigest(),
        "restore_page_hex_sha256": sha256(rollback.read_bytes()).hexdigest(),
        "pre_write_memory_sha256": {
            key: sha256(value).hexdigest() for key, value in snapshot.items()
        },
        "expected_flash_sha256": sha256(proposed + snapshot["flash"][end:]).hexdigest(),
        "install_argv": physical + erase + install,
        "restore_argv": physical + erase + restore,
        "offline_avrdude_simulation_exit": code,
    }


def main() -> int:
    """Capture full original memories, build both images, and save the exact proposed operations."""
    os.umask(0o077)
    settings = load_chat_settings()
    if settings.confirmed_bench_receipt is None:
        raise ValueError("a reviewed legacy receipt is required for this lab workflow")
    run = _create_run_directory(ROOT / "artifacts" / "lora-chat")
    proof = rf.ProofRun(run)
    print(run, flush=True)
    code, out, err = proof.command("programmer-version", [str(AVRDUDE), "--version"])
    if code or b"version 8.1" not in out + err:
        raise ValueError("AVRDUDE 8.1 required for the reviewed page strategy")
    effective, _ = bench.build(proof)
    copyfile(run / "production-build.json", run / "firmware-builds.json")
    bench.read_layouts(proof, effective)
    targets = {"gateway": "sender", "receiver": "receiver"}
    snapshots = {}
    for role, environment in targets.items():
        if rf.check_port_owners(proof, f"echo-{role}-before"):
            raise OSError("UPDI port in use; cannot capture an independent backup")
        snapshots[role] = read_snapshot(
            proof, environment, role, current_target=True, include_usersig=True
        )
    legacy = installed_rf.verify_snapshots(run, ROOT / settings.confirmed_bench_receipt)
    records = {
        role: package_target(proof, effective, role, env, snapshots[role], legacy[role.upper()])
        for role, env in targets.items()
    }
    status = (
        "AWAITING_EXACT_AUTHORIZATION"
        if all(row["offline_avrdude_simulation_exit"] == 0 for row in records.values())
        else "BLOCKED_OFFLINE_PROGRAMMER_REHEARSAL"
    )
    documents = {
        "deployment-package.json": {
            "status": status,
            "programmer": "AVRDUDE 8.1",
            "targets": records,
        },
        "device-identities.json": {
            role: {
                key: row[key]
                for key in (
                    "serial",
                    "signature",
                    "port",
                    "fuses",
                    "legacy_build_id",
                    "pre_write_memory_sha256",
                )
            }
            for role, row in records.items()
        },
        "flash-verification.json": {
            "status": "BLOCKED",
            "programmed": False,
            "legacy_archive_matches_fresh_full_flash": True,
            "readback_after_programming": None,
        },
        "capabilities.json": {
            "state": "LEGACY_ONLY",
            "echo_ready": False,
            "basis": "fresh complete Flash byte match with reviewed Legacy receipt",
        },
        "echo-trials.json": {"status": "BLOCKED", "trials": [], "reason": status},
        "metrics.json": {
            "status": "UNVERIFIED",
            "physical_echo_attempts": 0,
            "physical_echo_successes": 0,
            "physical_echo_payload_mismatches": None,
        },
    }
    for name, data in documents.items():
        proof.note(name, json.dumps(data, indent=2) + "\n")
    (run / "messages.jsonl").touch()
    return 0 if status == "AWAITING_EXACT_AUTHORIZATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
