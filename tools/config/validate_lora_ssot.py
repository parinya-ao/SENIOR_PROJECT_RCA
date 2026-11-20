"""Strict diagnostic configuration validation; physical inventory is not inferred."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.device_detection.flash_layout import Section, calculate_flash_layout, page_write_range

Json = Any
_MIN_TIMEOUT_MS = 100
_MAX_TIMEOUT_MS = 60_000
_MAX_RETRIES = 3


def unique_object(pairs: list[tuple[str, Json]]) -> dict[str, Json]:
    """Build a JSON object while rejecting duplicate keys."""
    result = {}
    for key, value in pairs:
        if key in result:
            msg = f"duplicate key: {key}"
            raise ValueError(msg)
        result[key] = value
    return result


def validate(config: Json) -> Json:
    """Validate the exact diagnostic schema and supported hardware settings."""
    board_shape = {
        "mcu": "",
        "bootsize": 0,
        "codesize": 0,
        "bodcfg": 0,
        "image_start": 0,
        "image_end_exclusive": 0,
        "image_section": "",
    }
    receiver_shape = dict(
        board_shape,
        pins={
            "sd_cs": "",
            "led1": "",
            "led2": "",
            "gps_enable": "",
            "sd_enable": "",
            "sd_detect": "",
        },
    )
    reference = {
        "schema_version": 0,
        "device_profiles": {
            "AVR128DA28": {
                "signature_hex": "",
                "flash_bytes": 0,
                "flash_page_bytes": 0,
                "eeprom_bytes": 0,
                "fuse_offsets": {"bodcfg": 0, "codesize": 0, "bootsize": 0},
            }
        },
        "experiment": {"mode": "", "radio_inventory": None, "antenna_inventory": None},
        "protocol": {
            "version": 0,
            "encoding": "",
            "sender_address": 0,
            "receiver_address": 0,
            "data_type": 0,
            "ack_type": 0,
            "nack_type": 0,
            "sequence_bits": 0,
            "sequence": 0,
            "payload": "",
        },
        "sender_board": board_shape,
        "receiver_board": receiver_shape,
        "timeouts": {"ack_ms": 0, "tx_ms": 0},
        "retries": {"max_retries": 0},
    }

    def shape(value: Json, expected: Json, path: str) -> None:
        if isinstance(expected, dict):
            if not isinstance(value, dict) or value.keys() != expected.keys():
                msg = f"{path}: missing or unknown fields"
                raise ValueError(msg)
            for key in expected:
                shape(value[key], expected[key], f"{path}.{key}")
        elif (
            expected is not None
            and type(value) is not type(expected)
            and not (type(expected) is float and type(value) in (int, float))
        ):
            msg = f"{path}: invalid type"
            raise ValueError(msg)

    shape(config, reference, "config")
    if config["schema_version"] != 2:
        msg = "unsupported schema_version"
        raise ValueError(msg)
    for model, profile in config["device_profiles"].items():
        if (
            not re.fullmatch(r"[0-9A-Fa-f]{6}", profile["signature_hex"])
            or type(profile["flash_bytes"]) is not int
            or type(profile["flash_page_bytes"]) is not int
            or type(profile["eeprom_bytes"]) is not int
            or profile["flash_bytes"] <= 0
            or profile["flash_page_bytes"] <= 0
            or profile["eeprom_bytes"] < 0
            or profile["flash_bytes"] % profile["flash_page_bytes"]
            or any(
                type(offset) is not int or not 0 <= offset <= 0xFF
                for offset in profile["fuse_offsets"].values()
            )
            or len(set(profile["fuse_offsets"].values())) != len(profile["fuse_offsets"])
        ):
            msg = f"device_profiles.{model}: invalid physical memory geometry"
            raise ValueError(msg)
    protocol = config["protocol"]
    if protocol != {
        "version": 2,
        "encoding": "existing_radio_header",
        "sender_address": 0,
        "receiver_address": 1,
        "data_type": 8,
        "ack_type": 3,
        "nack_type": 9,
        "sequence_bits": 8,
        "sequence": 1,
        "payload": "hello world",
    }:
        msg = "unsupported protocol framing or payload"
        raise ValueError(msg)
    for role in ("sender", "receiver"):
        board = config[f"{role}_board"]
        geometry = config["device_profiles"].get(board["mcu"])
        if geometry is None:
            msg = f"{role}: MCU has no validated device profile"
            raise ValueError(msg)
        if role == "receiver":
            expected_pins = {
                "sd_cs": "PC3",
                "led1": "PA6",
                "led2": "PA5",
                "gps_enable": "PD5",
                "sd_enable": "PD6",
                "sd_detect": "PA4",
            }
            if board["pins"] != expected_pins:
                msg = f"{role}: unsupported board pin mapping"
                raise ValueError(msg)
        layout = calculate_flash_layout(
            device_model=board["mcu"],
            flash_bytes=geometry["flash_bytes"],
            page_bytes=geometry["flash_page_bytes"],
            bootsize_pages=board["bootsize"],
            codesize_pages=board["codesize"],
            protection_state="CONFIGURED",
        )
        try:
            section = Section(board["image_section"])
        except ValueError as error:
            msg = f"{role}: unsupported firmware image section"
            raise ValueError(msg) from error
        image_start = board["image_start"]
        image_end = board["image_end_exclusive"]
        write_span = page_write_range(layout, section, image_start, image_end)
        section_region = layout.region(section)
        if (
            layout.fuse_status.value != "FUSE_LAYOUT_VALID"
            or type(board["bodcfg"]) is not int
            or not 0 <= board["bodcfg"] <= 0xFF
            or section is Section.APPDATA
            or section_region is None
            or image_start != section_region.start
            or image_end > section_region.end_exclusive
            or write_span != (image_start, image_end)
        ):
            msg = f"{role}: firmware image or fuse geometry is incompatible with its section"
            raise ValueError(msg)
    if config["experiment"] != {
        "mode": "single_packet",
        "radio_inventory": None,
        "antenna_inventory": None,
    }:
        msg = "experiment: unsupported mode or unverified inventory assertion"
        raise ValueError(msg)
    if not all(
        _MIN_TIMEOUT_MS <= value <= _MAX_TIMEOUT_MS for value in config["timeouts"].values()
    ):
        msg = "timeouts out of range"
        raise ValueError(msg)
    if not 0 <= config["retries"]["max_retries"] <= _MAX_RETRIES:
        msg = "retry limit out of range"
        raise ValueError(msg)
    return config


def load(path: str | Path) -> Json:
    """Load and validate one diagnostic system configuration file."""
    return validate(json.loads(Path(path).read_text(), object_pairs_hook=unique_object))


def main() -> None:
    """Validate the configured SSOT and report the result to the CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=ROOT / "config/lora_system.json")
    args = parser.parse_args()
    try:
        load(args.path)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Invalid LoRa SSOT: {error}\n")
    print("LoRa SSOT valid (physical suitability remains unverified)")


if __name__ == "__main__":
    main()
