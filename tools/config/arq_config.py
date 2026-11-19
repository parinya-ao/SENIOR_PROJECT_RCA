"""Strict ARQ experiment settings and board C generated from authoritative pins."""

import json
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
Json = Any
_MAX_PAYLOAD_LENGTH = 32
_TEST_COUNT_SLOTS = 6
_MAX_TEST_COUNT = 100


def load_arq() -> Json:
    """Load the ARQ test settings and validate their fixed radio profile."""
    with (ROOT / "config/arq_test.toml").open("rb") as stream:
        return validate_arq(tomllib.load(stream))


def validate_arq(c: Json) -> Json:
    """Reject unsupported ARQ settings before generating firmware artifacts."""
    fixed = {
        "schema_version": 1,
        "payload_limit": 32,
        "frequency_hz": 915000000,
        "tx_power_dbm": 2,
        "bandwidth_khz": 125,
        "spreading_factor": 7,
        "coding_rate": 5,
        "sync_word": 18,
        "preamble_symbols": 8,
        "crc_enabled": True,
        "explicit_header": True,
        "iq_inverted": False,
        "spi_hz": 1000000,
    }
    integers = {
        "sender_id": (1, 255),
        "receiver_id": (1, 255),
        "initial_sequence": (0, 65535),
        "ack_min_ms": (1, 1000000),
        "ack_max_ms": (1, 1000000),
        "max_retries": (0, 10),
        "tx_ms": (1, 1000000),
        "response_guard_ms": (0, 1000000),
        "spacing_ms": (1, 1000000),
        "fault_ack_stride": (1, 100),
        "fault_drop_budget": (0, 100),
    }
    if set(c) != set(fixed) | set(integers) | {"payload", "negative_payload", "test_counts"}:
        msg = "ARQ missing/unknown settings"
        raise ValueError(msg)
    for k, v in fixed.items():
        if type(c[k]) is not type(v) or c[k] != v:
            msg = f"unsupported ARQ {k}"
            raise ValueError(msg)
    for k, (lo, hi) in integers.items():
        if type(c[k]) is not int or not lo <= c[k] <= hi:
            msg = f"invalid ARQ {k}"
            raise ValueError(msg)
    for k in ("payload", "negative_payload"):
        if (
            type(c[k]) is not str
            or not c[k].isascii()
            or not 1 <= len(c[k]) <= _MAX_PAYLOAD_LENGTH
        ):
            msg = f"invalid ARQ {k}"
            raise ValueError(msg)
    if c["payload"] == c["negative_payload"] or c["sender_id"] == c["receiver_id"]:
        msg = "ARQ payloads/IDs must differ"
        raise ValueError(msg)
    if c["ack_max_ms"] < c["ack_min_ms"]:
        msg = "ARQ RTO range"
        raise ValueError(msg)
    counts = c["test_counts"]
    if (
        type(counts) is not list
        or len(counts) != _TEST_COUNT_SLOTS
        or any(type(n) is not int or not 1 <= n <= _MAX_TEST_COUNT for n in counts)
    ):
        msg = "ARQ test counts"
        raise ValueError(msg)
    # Include all local TX bounds and spacing, not only the exponential waits.
    bound = sum(
        (c["ack_max_ms"] << i) + c["tx_ms"] + c["spacing_ms"] for i in range(c["max_retries"] + 1)
    )
    if bound >= 2**31 or c["response_guard_ms"] >= c["ack_min_ms"]:
        msg = "ARQ timer arithmetic"
        raise ValueError(msg)
    return c


def arq_artifacts(c: Json, radio: Json, system: Json, source: str) -> dict[str, str]:
    """Generate ARQ and board header contents from validated configuration."""
    from generate_lora_config import (  # type: ignore[import-not-found]
        digest,
    )

    validate_arq(c)
    h = ["#pragma once", "// Generated from config/arq_test.toml."]
    h.extend(
        f"#define ARQ_{k.upper()} {int(v)}UL"
        for k, v in c.items()
        if type(v) in (int, bool)
    )
    h.extend(
        f"#define ARQ_{k.upper()} {json.dumps(c[k])}" for k in ("payload", "negative_payload")
    )
    h.append(f'#define ARQ_CONFIG_HASH "{digest(c)}"')
    board_h = [
        "#pragma once",
        "#include <stdint.h>",
        "#ifdef __cplusplus",
        'extern "C" {',
        "#endif",
        "typedef struct { uint8_t cs, rst, irq, dio1; } arq_board;",
        "extern const arq_board board_ssot;",
        "void board_ssot_init(void);",
        "#ifdef __cplusplus",
        "}",
        "#endif",
    ]
    board_c = [
        "// Generated from config/radio_915.toml and config/lora_system.json.",
        "#include <Arduino.h>",
        '#include "generated/board_ssot.h"',
    ]
    for i, role in enumerate(("sender", "receiver")):
        directive = "#if" if i == 0 else "#elif"
        board_h += [
            f"{directive} defined(LORA_ROLE_{role.upper()})",
            f"#define ARQ_SPI_ROUTE {radio[role]['spi_route']}",
        ]
        pins = radio[role]["pins"]
        board_c += [
            f"{directive} defined(LORA_ROLE_{role.upper()})",
            "const arq_board board_ssot = {"
            + ", ".join("PIN_" + pins[k] for k in ("cs", "rst", "irq", "dio1"))
            + "};",
            "void board_ssot_init(void) {",
        ]
        if role == "receiver":
            extras = system["receiver_board"]["pins"]
            for k in ("gps_enable", "sd_enable", "sd_cs"):
                board_c += [
                    f" digitalWrite(PIN_{extras[k]}, HIGH);",
                    f" pinMode(PIN_{extras[k]}, OUTPUT);",
                ]
            board_c += [
                "#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC)",
                f" pinMode(PIN_{extras['sd_detect']}, INPUT_PULLUP);",
                "#else",
                f" pinMode(PIN_{extras['sd_detect']}, INPUT);",
                "#endif",
                f" digitalWrite(PIN_{pins['enable']}, HIGH);",
                f" pinMode(PIN_{pins['enable']}, OUTPUT);",
                f" digitalWrite(PIN_{pins['enable']}, {radio[role]['radio_power_active_level']});",
            ]
        board_c += [
            " digitalWrite(board_ssot.cs, HIGH);",
            " pinMode(board_ssot.cs, OUTPUT);",
            " pinMode(board_ssot.rst, INPUT);",
            " pinMode(board_ssot.irq, INPUT);",
            " pinMode(board_ssot.dio1, INPUT);",
            "}",
        ]
    board_h += ["#else", '#error "ARQ requires one role"', "#endif"]
    board_c += ["#endif"]
    manifest = {
        "config": c,
        "config_hash": digest(c),
        "source_hash": source,
        "radio": {
            k: c[k]
            for k in (
                "frequency_hz",
                "tx_power_dbm",
                "bandwidth_khz",
                "spreading_factor",
                "coding_rate",
                "sync_word",
                "preamble_symbols",
                "crc_enabled",
                "explicit_header",
                "iq_inverted",
                "spi_hz",
            )
        },
        "boards": {k: radio[k] for k in ("sender", "receiver")},
    }
    return {
        "include/generated/arq_config.h": "\n".join(h) + "\n",
        "include/generated/board_ssot.h": "\n".join(board_h) + "\n",
        "stable_lib/arq/board_ssot.c": "\n".join(board_c) + "\n",
        "generated/arq_manifest.json": json.dumps(manifest, sort_keys=True, indent=2) + "\n",
    }
