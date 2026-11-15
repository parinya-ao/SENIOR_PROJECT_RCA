"""Validate the LoRa inputs and generate deterministic firmware and host profiles."""

import argparse
import hashlib
import json
import os
import tempfile
import tomllib
from pathlib import Path

from validate_lora_ssot import ROOT, load, validate

RADIO_PROFILE = {
    "schema_version": 1,
    "radio": {
        "frequency_hz": 915_000_000,
        "bandwidth_khz": 125,
        "spreading_factor": 7,
        "coding_rate": 5,
        "sync_word": 0x12,
        "tx_power_dbm": 2,
        "preamble_symbols": 8,
        "crc_enabled": True,
        "explicit_header": True,
        "iq_inverted": False,
        "current_limit_ma": 200,
        "automatic_gain": 0,
        "long_range": 0,
    },
    "sender": {
        "spi_route": "SPI1_SWAP_DEFAULT",
        "pins": {
            "mosi": "PC0",
            "miso": "PC1",
            "sck": "PC2",
            "cs": "PC3",
            "rst": "PD0",
            "irq": "PD2",
            "dio1": "PD3",
        },
    },
    "receiver": {
        "spi_route": "SPI1_SWAP_DEFAULT",
        "radio_power_active_level": 0,
        "pins": {
            "mosi": "PC0",
            "miso": "PC1",
            "sck": "PC2",
            "cs": "PD0",
            "rst": "PD1",
            "irq": "PD3",
            "dio1": "PD2",
            "enable": "PA7",
        },
    },
    "environments": {
        "sender": ["sender", "sender_hello", "sender_hello_spi", "sender_mvp"],
        "receiver": ["receiver", "receiver_spi", "receiver_mvp"],
    },
}


def validate_radio_profile(profile):
    def check(value, expected, path):
        if isinstance(expected, dict):
            if not isinstance(value, dict) or value.keys() != expected.keys():
                raise ValueError(f"{path}: missing or unknown fields")
            for key, expected_value in expected.items():
                check(value[key], expected_value, f"{path}.{key}")
        elif path == "radio_915.environments.sender" or path == "radio_915.environments.receiver":
            if (
                type(value) is not list
                or any(type(item) is not str for item in value)
                or len(value) != len(set(value))
                or set(value) != set(expected)
            ):
                raise ValueError(f"{path}: environment mapping must be unique and complete")
        elif type(value) is not type(expected):
            raise ValueError(f"{path}: invalid type")
        elif value != expected:
            raise ValueError(f"{path}: unsupported fixed radio setting")

    check(profile, RADIO_PROFILE, "radio_915")
    return profile


def load_radio_profile(path=None):
    path = Path(path) if path is not None else ROOT / "config/radio_915.toml"
    try:
        with path.open("rb") as source:
            profile = tomllib.load(source)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"invalid radio profile: {error}") from error
    return validate_radio_profile(profile)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def source_fingerprint():
    paths = list((ROOT / "src").rglob("*")) + list((ROOT / "tools/config").glob("*.py"))
    paths += [ROOT / "platformio.ini"]
    for directory in ("lib", "include", "third_party"):
        paths += list((ROOT / directory).rglob("*"))
    return digest(
        {
            "project/" + str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)
            if path.is_file()
            and path.suffix in (".h", ".c", ".cpp", ".py", ".ini")
            and not path.is_relative_to(ROOT / "include/generated")
            and path != ROOT / "src/arq/board_ssot.c"
        }
    )


def _radio_manifest(profile):
    radio = profile["radio"]
    return dict(
        frequency_hz=radio["frequency_hz"],
        frequency_mhz=radio["frequency_hz"] / 1_000_000,
        tx_power_dbm=radio["tx_power_dbm"],
        long_range=radio["long_range"],
        spreading_factor=radio["spreading_factor"],
        bandwidth_khz=radio["bandwidth_khz"],
        coding_rate=radio["coding_rate"],
        sync_word=radio["sync_word"],
        preamble_symbols=radio["preamble_symbols"],
        crc_enabled=radio["crc_enabled"],
        explicit_header=radio["explicit_header"],
        iq_inverted=radio["iq_inverted"],
        current_limit_ma=radio["current_limit_ma"],
        automatic_gain=radio["automatic_gain"],
    )


def _profile_python(radio):
    names = {
        "FREQUENCY_HZ": "frequency_hz",
        "BANDWIDTH_KHZ": "bandwidth_khz",
        "SPREADING_FACTOR": "spreading_factor",
        "CODING_RATE": "coding_rate",
        "SYNC_WORD": "sync_word",
        "TX_POWER_DBM": "tx_power_dbm",
        "PREAMBLE_SYMBOLS": "preamble_symbols",
        "CRC_ENABLED": "crc_enabled",
        "EXPLICIT_HEADER": "explicit_header",
        "IQ_INVERTED": "iq_inverted",
        "CURRENT_LIMIT_MA": "current_limit_ma",
        "AUTOMATIC_GAIN": "automatic_gain",
        "LONG_RANGE": "long_range",
    }
    lines = ["# Generated from config/radio_915.toml."]
    for name, key in names.items():
        lines.append(f"{name} = {radio[key]!r}")
    lines.append("FREQUENCY_MHZ = FREQUENCY_HZ / 1_000_000")
    return "\n".join(lines) + "\n"


def artifacts(config, radio_profile=None):
    validate(config)
    radio_profile = validate_radio_profile(radio_profile or load_radio_profile())
    radio = _radio_manifest(radio_profile)
    shared = {
        "schema_version": config["schema_version"],
        "radio": radio,
        "protocol": config["protocol"],
        "timeouts": config["timeouts"],
        "retries": config["retries"],
    }
    fingerprint = digest(shared)
    source_hash = source_fingerprint()
    manifest = dict(
        shared=shared,
        shared_fingerprint=fingerprint,
        boards={},
        environments={},
        source_fingerprint=source_hash,
    )

    lines = [
        "#pragma once",
        "// Generated from config/lora_system.json and config/radio_915.toml.",
        f'#define LORA_CONFIG_FINGERPRINT "{fingerprint}"',
        f"#define LORA_PROTOCOL_VERSION {config['protocol']['version']}",
        f'#define LORA_PROTOCOL_VERSION_TEXT "{config["protocol"]["version"]}"',
        f"#define LORA_MAX_RETRIES {config['retries']['max_retries']}",
        f'#define LORA_HELLO_PAYLOAD "{config["protocol"]["payload"]}"',
        f"#define LORA_ACK_TIMEOUT_MS {config['timeouts']['ack_ms']}",
        f"#define LORA_TX_TIMEOUT_MS {config['timeouts']['tx_ms']}",
    ]
    for name in (
        "sender_address",
        "receiver_address",
        "sequence",
        "data_type",
        "ack_type",
        "nack_type",
    ):
        lines.append(f"#define LORA_{name.upper()} {config['protocol'][name]}")
    outputs = {"include/generated/lora_shared_config.h": "\n".join(lines) + "\n"}

    radio_source = radio_profile["radio"]
    cpp_profile = {
        "FREQUENCY_MHZ": f"{radio['frequency_mhz']:.1f}f",
        "TX_POWER_DBM": radio["tx_power_dbm"],
        "LONG_RANGE": radio["long_range"],
        "SPREADING_FACTOR": radio["spreading_factor"],
        "BANDWIDTH_KHZ": radio["bandwidth_khz"],
        "CODING_RATE": radio["coding_rate"],
        "SYNC_WORD": hex(radio["sync_word"]),
        "PREAMBLE_SYMBOLS": radio["preamble_symbols"],
        "CRC_ENABLED": int(radio["crc_enabled"]),
        "EXPLICIT_HEADER": int(radio["explicit_header"]),
        "IQ_INVERTED": int(radio["iq_inverted"]),
        "CURRENT_LIMIT_MA": radio["current_limit_ma"],
        "AUTOMATIC_GAIN": radio["automatic_gain"],
    }
    lines = ["#pragma once", "// Generated from config/radio_915.toml."]
    lines.extend(f"#define HELLO_RF_{name} {value}" for name, value in cpp_profile.items())
    lines += [
        "#if (defined(LORA_ROLE_SENDER) + defined(LORA_ROLE_RECEIVER)) != 1",
        '#error "Define exactly one radio role through the PlatformIO profile mapping."',
        "#endif",
        "#if defined(LORA_ROLE_SENDER)",
    ]
    sender = radio_profile["sender"]
    lines.append(f"#define LORA_SPI_ROUTE {sender['spi_route']}")
    lines.extend(
        f"#define LORA_PIN_{name.upper()} PIN_{pin}" for name, pin in sender["pins"].items()
    )
    lines += ["#elif defined(LORA_ROLE_RECEIVER)"]
    receiver = radio_profile["receiver"]
    lines.append(f"#define LORA_SPI_ROUTE {receiver['spi_route']}")
    lines.extend(
        f"#define LORA_PIN_{name.upper()} PIN_{pin}" for name, pin in receiver["pins"].items()
    )
    lines.append(f"#define LORA_POWER_ACTIVE_LEVEL {receiver['radio_power_active_level']}")
    lines += ["#endif", ""]
    outputs["include/generated/radio_915_config.h"] = "\n".join(lines)

    layout = ["[target_layout]"]
    for role, target in (("sender", "gateway"), ("receiver", "receiver")):
        board = config[f"{role}_board"]
        for key in ("bootsize", "codesize", "bodcfg"):
            layout.append(f"{target}_{key} = {hex(board[key])}")
        layout.append(f"{target}_app_start = {hex(board['image_start'])}")
    layout += [
        "[flash_geometry]",
        "total_bytes = 131072",
        f"application_end = {hex(config['receiver_board']['image_end_exclusive'])}",
    ]
    outputs["generated/lora_platformio.ini"] = "\n".join(layout) + "\n"

    for role in ("sender", "receiver"):
        board = config[f"{role}_board"]
        radio_board = radio_profile[role]
        full = digest(dict(shared=shared, board=board, radio_board=radio_board, role=role))
        manifest["boards"][role] = dict(board, radio_board=radio_board, build_fingerprint=full)
        board_lines = [
            "#pragma once",
            "// Generated from config/lora_system.json.",
            f'#define LORA_BUILD_FINGERPRINT "{full}"',
            f"#define LORA_IMAGE_START {board['image_start']}",
            f"#define LORA_IMAGE_END {board['image_end_exclusive']}",
        ]
        for name, pin in board.get("pins", {}).items():
            board_lines.append(f"#define LORA_PIN_{name.upper()} PIN_{pin}")
        outputs[f"include/generated/lora_{role}_board.h"] = "\n".join(board_lines) + "\n"

    for role, environments in radio_profile["environments"].items():
        for environment in environments:
            manifest["environments"][environment] = dict(
                role=role,
                build_id=digest(
                    dict(
                        environment=environment,
                        source=source_hash,
                        board=manifest["boards"][role]["build_fingerprint"],
                    )
                ),
            )
    outputs["generated/lora_manifest.json"] = json.dumps(manifest, sort_keys=True, indent=2) + "\n"

    python_profile = _profile_python(radio_source)
    outputs["generated/radio_915_profile.py"] = python_profile
    for integration in ("gateway-lora", "gateway-lora_dev"):
        outputs[f"../iwing-tracker/{integration}/mainboard/src/radio_915_profile.py"] = (
            python_profile
        )
    from arq_config import arq_artifacts, load_arq

    outputs.update(arq_artifacts(load_arq(), radio_profile, config, source_hash))
    return outputs


def _write_atomic(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_text() == contents:
        return
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w") as output:
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def generate(check=False):
    config = load(ROOT / "config/lora_system.json")
    radio_profile = load_radio_profile(ROOT / "config/radio_915.toml")
    outputs = artifacts(config, radio_profile)
    for name, contents in outputs.items():
        path = ROOT / name
        if check:
            if not path.is_file() or path.read_text() != contents:
                raise ValueError(f"stale or missing generated artifact: {name}")
        else:
            _write_atomic(path, contents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="fail if generated files are stale or missing"
    )
    mode.add_argument("--validate", action="store_true", help="validate both source configurations")
    args = parser.parse_args()
    try:
        if args.validate:
            load(ROOT / "config/lora_system.json")
            load_radio_profile(ROOT / "config/radio_915.toml")
        else:
            generate(check=args.check)
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
