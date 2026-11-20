"""Build and prepare the two production images for the physical LoRa debugger."""

from __future__ import annotations

import json
import os
import re
import sys
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools import rf_proof as rf
from tools.device_detection.flash_layout import page_write_range, validate_image_range
from tools.device_detection.hardware_registry import hardware_ports

ENVIRONMENTS = ("sender", "receiver")
MANIFEST = rf.ROOT / "generated/lora_manifest.json"
SX1276_LORA_HF_RX = 0x85
SX1276_BW_125_KHZ = 7
PROFILE_BANDWIDTH_KHZ = 125
OCP_FINE_STEP_LIMIT_MA = 120
LNA_HF_BOOST = 0x03
PA_NORMAL_POWER_DAC = 0x04
Json = dict[str, Any]


class BenchBlockedError(OSError):
    """An unmet hardware or authorization prerequisite stopped the bench."""


class BenchFailedError(RuntimeError):
    """An attempted build, program, or proof operation failed."""


def build(proof: rf.ProofRun) -> tuple[str, Json]:
    """Check generated inputs before PlatformIO resolves or consumes them."""
    code, _, _ = proof.command(
        "generated-inputs",
        [sys.executable, "tools/config/generate_lora_config.py", "--prepare-build"],
        30,
    )
    if code:
        msg = "Generated build inputs are stale or invalid. See generated-inputs.stderr.log."
        raise BenchFailedError(msg)
    code, resolved, _ = proof.command(
        "configuration", ["pio", "project", "config", "--json-output"], 30
    )
    effective = resolved.decode()
    if (
        code
        or not rf.valid_rf_profile_config(effective)
        or not rf.upload_ports_match(effective)
        or not rf.firmware_image_layout_verified(ENVIRONMENTS, effective)
    ):
        msg = "Production PlatformIO profile, linked ranges, or enrolled ports are invalid."
        raise BenchFailedError(msg)
    measurements = {}
    for environment in ENVIRONMENTS:
        code, output, _ = proof.command(
            f"build-{environment}", ["pio", "run", "-e", environment], 300
        )
        if code:
            msg = f"{environment} build failed. See build-{environment}.stderr.log."
            raise BenchFailedError(msg)
        measurements[environment] = inspect_image(proof, effective, environment, output)
    proof.note("production-build.json", json.dumps(measurements, indent=2) + "\n")
    return effective, json.loads(MANIFEST.read_text())


def inspect_image(proof: rf.ProofRun, effective: str, environment: str, output: bytes) -> Json:
    """Require ELF vectors and all loadable sections to agree with the HEX span."""
    measurement = rf.firmware_measurement(environment, output)
    hex_info = measurement.get("hex")
    if not isinstance(hex_info, dict) or not hex_info.get("reset_target_inside_image"):
        msg = f"{environment} lacks a valid HEX reset vector."
        raise BenchFailedError(msg)
    region = hex_info["address_range"]
    start, end = region["start"], region["end_exclusive"]
    image_layout = rf.firmware_image_bounds_for_environment(effective, environment)
    if image_layout is None:
        msg = f"{environment} has no validated fuse-derived firmware image section."
        raise BenchFailedError(msg)
    layout, section, expected_start, expected_end = image_layout
    valid_range, detail = validate_image_range(layout, section, start, end)
    rounded_span = page_write_range(layout, section, start, end)
    if (
        not valid_range
        or start != expected_start
        or rounded_span is None
        or rounded_span[0] != start
        or rounded_span[1] > expected_end
    ):
        msg = f"{environment} HEX does not fit its declared {section.value} section: {detail}."
        raise BenchFailedError(msg)
    core = Path(os.getenv("PLATFORMIO_CORE_DIR", str(Path.home() / ".platformio")))
    elf = rf.ROOT / ".pio/build" / environment / "firmware.elf"
    code, raw, _ = proof.command(
        f"elf-{environment}",
        [str(core / "packages/toolchain-atmelavr/bin/avr-objdump"), "-h", "-t", str(elf)],
        30,
    )
    listing = raw.decode()
    vectors = re.search(r"^([0-9a-f]+)\s+[^\n]*\s__vectors$", listing, re.MULTILINE)
    sections = re.findall(
        r"^\s*\d+\s+(\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)[^\n]*\n"
        r"[^\n]*\bLOAD\b",
        listing,
        re.MULTILINE,
    )
    loads = {name: (int(lma, 16), int(size, 16)) for name, size, _, lma in sections}
    if (
        code
        or not vectors
        or int(vectors[1], 16) != start
        or loads.get(".text", (None, None))[0] != start
        or any(addr < start or addr + size > end for addr, size in loads.values())
        or max(addr + size for addr, size in loads.values()) != end
    ):
        msg = f"{environment} ELF vectors or load sections disagree with the HEX image."
        raise BenchFailedError(msg)
    return {
        **measurement,
        "elf_loads": loads,
        "image_section": section.value,
        "fuse_layout_status": layout.fuse_status.value,
        "fota_layout_status": layout.fota_status.value,
        "rounded_span": list(rounded_span),
    }


def read_layouts(proof: rf.ProofRun, effective: str) -> dict[str, Json]:
    """Obtain fresh signature, serial and fuse geometry on the enrolled adapters."""
    args = Namespace(physical_mapping_verified=True, power_verified=True)
    if rf.identify_targets(proof, args, effective):
        msg = "MCU signature, enrolled serial, port ownership or fuses failed verification."
        raise BenchBlockedError(msg)
    layouts = {}
    for role in hardware_ports(rf.ROOT / "config" / "current_hardware.json"):
        observed = json.loads(
            (proof.run_dir / f"target-{role}-layout.json").read_text(encoding="utf-8")
        )["observed"]
        geometry = rf.flash_layout_for_role(effective, role)
        if geometry is None:
            raise BenchBlockedError(f"{role}: fuse-derived memory geometry is invalid")
        row = {**observed, "calculated_layout": geometry.to_dict()}
        layouts[role.upper()] = row
    proof.note("flash-layout.json", json.dumps(layouts, indent=2) + "\n")
    return layouts


def write_span_is_application(start: int, end: int, layout: Json) -> bool:
    """Allow only a page-aligned APPCODE span in the independently read fuse layout."""
    calculated = layout.get("calculated_layout")
    if not isinstance(calculated, dict):
        return False
    sections = calculated.get("sections")
    page_bytes = calculated.get("page_bytes")
    appcode = sections.get("APPCODE") if isinstance(sections, dict) else None
    start_address = appcode.get("start") if isinstance(appcode, dict) else None
    end_address = appcode.get("end_exclusive") if isinstance(appcode, dict) else None
    if (
        not isinstance(appcode, dict)
        or type(page_bytes) is not int
        or type(start) is not int
        or type(end) is not int
        or type(start_address) is not int
        or type(end_address) is not int
        or start % page_bytes
        or end % page_bytes
        or not start < end
    ):
        return False
    return start_address <= start < end <= end_address


def approve_writes(
    mismatches: dict[str, Json], layouts: dict[str, Json], approval: Path | None
) -> dict[str, Json]:
    """Check all mismatches against live bounds and exact authorization before any write."""
    for role, image in mismatches.items():
        layout = layouts[role]
        if not write_span_is_application(image["start"], image["end"], layout):
            calculated = layout.get("calculated_layout", {})
            appcode = calculated.get("sections", {}).get("APPCODE")
            if appcode is None:
                detail = calculated.get("detail", "APPCODE is absent in the observed fuse layout")
            else:
                detail = "image pages are outside APPCODE or not page aligned"
            msg = f"{role} image mismatch cannot be prepared safely: {detail}. No write performed."
            raise BenchBlockedError(msg)
    expected = {
        role: {
            "serial_number": image["serial_number"],
            "firmware_sha256": image["firmware_sha256"],
            "start": image["start"],
            "end": image["end"],
        }
        for role, image in mismatches.items()
    }
    if approval is None or json.loads(approval.read_text()) != expected:
        msg = "Exact write authorization required for APPCODE pages. " + json.dumps(expected)
        raise BenchBlockedError(msg)
    return expected


def publish_receipt(
    proof: rf.ProofRun, images: dict[str, Json], layouts: dict[str, Json], manifest: Json
) -> None:
    """Publish one receipt after both full-page readbacks match."""
    rows = {
        role: {
            **image,
            "layout": layouts[role],
            "source_fingerprint": manifest["source_fingerprint"],
            "shared_fingerprint": manifest["shared_fingerprint"],
            "verification": "fresh full-page UPDI readback",
            "result": "MATCH",
        }
        for role, image in images.items()
    }
    temp = proof.run_dir / ".physical-upload.json.tmp"
    with temp.open("w") as handle:
        json.dump({"timestamp": datetime.now(UTC).isoformat(), "roles": rows}, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(proof.run_dir / "physical-upload.json")


def phy_matches(text: str, role: str, radio: Json) -> bool:
    """Validate HF continuous RX, PHY fields and DIO0 RxDone from SPI readback."""
    pattern = (
        rf"^\[{role}\] RADIO_REG MODE=([0-9A-F]{{2}}) FRF=([0-9A-F]{{6}}) "
        r"MC=([0-9A-F]{6}) PRE=(\d+) IQ=([0-9A-F]{2}) SYNC=([0-9A-F]{2}) "
        r"DIO=([0-9A-F]{2}) MASK=([0-9A-F]{2})$"
    )
    match = re.search(pattern, text, re.MULTILINE)
    if not match or f"[{role}] RADIO_SPI_VERSION=0x12" not in text:
        return False
    mode, frf, modem, preamble, iq, sync, dio, mask = match.groups()
    modem1, modem2, modem3 = bytes.fromhex(modem)
    return (
        int(mode, 16) == SX1276_LORA_HF_RX
        and int(frf, 16) == radio["frequency_hz"] * (1 << 19) // 32_000_000
        and radio["bandwidth_khz"] == PROFILE_BANDWIDTH_KHZ
        and modem1 >> 4 == SX1276_BW_125_KHZ
        and (modem1 >> 1) & 7 == radio["coding_rate"] - 4
        and bool(modem1 & 1) != radio["explicit_header"]
        and modem2 >> 4 == radio["spreading_factor"]
        and bool(modem2 & 4) == radio["crc_enabled"]
        and bool(modem3 & 4) == (radio["automatic_gain"] == 0)
        and int(preamble) == radio["preamble_symbols"]
        and bool(int(iq, 16) & 0x40) == radio["iq_inverted"]
        and int(sync, 16) == radio["sync_word"]
        and int(dio, 16) & 0xC0 == 0
        and int(mask, 16) & 0x40 == 0
    )


def power_matches(text: str, role: str, radio: Json, version_probes: int) -> bool:
    """Require repeated version reads, PA_BOOST power, current limit and LNA boost."""
    pattern = (
        rf"^\[{role}\] RADIO_POWER VERSIONS=(\d+) PA=([0-9A-F]{{2}}) "
        r"OCP=([0-9A-F]{2}) LNA=([0-9A-F]{2}) DAC=([0-9A-F]{2})$"
    )
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return False
    versions, pa, ocp, lna, dac = match.groups()
    current = radio["current_limit_ma"]
    trim = (current + 30) // 10 if current > OCP_FINE_STEP_LIMIT_MA else (current - 45) // 5
    return (
        int(versions) == version_probes
        and int(pa, 16) & 0x8F == 0x80 | (radio["tx_power_dbm"] - 2)
        and int(ocp, 16) & 0x3F == 0x20 | trim
        and int(lna, 16) & LNA_HF_BOOST == LNA_HF_BOOST
        and int(dac, 16) & 0x07 == PA_NORMAL_POWER_DAC
    )
