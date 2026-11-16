"""Generate application policy without touching protected hardware outputs."""

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate(config: dict) -> dict:
    """Reject unknown settings and capacities outside existing AVR budgets."""
    fields = {
        "diagnostics": {"max_retries", "payload", "gateway_payload", "tracker_payload", "negative_payload"},
        "logging": {"slot_count", "slot_bytes"},
        "commands": {"capacity", "inter_byte_timeout_ms", "fault_limit"},
        "ssot": {"campaign_messages"},
        "startup": {"radio_settle_ms", "version_probe_attempts"},
        "raw": {"payload", "transmit_interval_ms", "receive_timeout_ms",
                "log_byte_timeout_ms", "log_batch_timeout_ms", "packet_event_limit"},
        "gateway": {"result_buffer_bytes", "uart_baud", "i2c_reset_interval_ms"},
    }
    if set(config) != {"schema_version", *fields} or type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise ValueError("unsupported application schema or settings")
    for section, keys in fields.items():
        if type(config[section]) is not dict or set(config[section]) != keys:
            raise ValueError(f"missing/unknown application {section} settings")
    ranges = {
        ("diagnostics", "max_retries"): (0, 0),
        ("logging", "slot_count"): (1, 16),
        ("logging", "slot_bytes"): (192, 255),
        ("commands", "capacity"): (70, 255),
        ("commands", "inter_byte_timeout_ms"): (1, 1_000_000),
        ("commands", "fault_limit"): (1, 100),
        ("ssot", "campaign_messages"): (2, 255),
        ("startup", "radio_settle_ms"): (10, 1000),
        ("startup", "version_probe_attempts"): (1, 8),
        ("raw", "transmit_interval_ms"): (3000, 1_000_000),
        ("raw", "receive_timeout_ms"): (10000, 1_000_000),
        ("raw", "log_byte_timeout_ms"): (1, 1000),
        ("raw", "log_batch_timeout_ms"): (1, 10000),
        ("raw", "packet_event_limit"): (1, 255),
        ("gateway", "result_buffer_bytes"): (1, 4096),
        ("gateway", "uart_baud"): (1200, 115200),
        ("gateway", "i2c_reset_interval_ms"): (1, 1_000_000),
    }
    for (section, key), (minimum, maximum) in ranges.items():
        value = config[section][key]
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f"invalid application {section}.{key}")
    if config["logging"]["slot_count"] * config["logging"]["slot_bytes"] > 3072:
        raise ValueError("logging exceeds the existing 3 KiB queue budget")
    capacity = config["gateway"]["result_buffer_bytes"]
    if capacity & (capacity - 1):
        raise ValueError("gateway result buffer must be a power of two")
    for key in ("payload", "gateway_payload", "tracker_payload", "negative_payload"):
        value = config["diagnostics"][key]
        if type(value) is not str or not value.isascii() or not 1 <= len(value) <= 32 or not value.isprintable():
            raise ValueError(f"invalid diagnostic {key}")
    if config["diagnostics"]["negative_payload"] in (
        config["diagnostics"][key] for key in ("payload", "gateway_payload", "tracker_payload")
    ):
        raise ValueError("negative diagnostic payload must differ from accepted payloads")
    raw_payload = config["raw"]["payload"]
    if type(raw_payload) is not str or not raw_payload.isascii() or not 1 <= len(raw_payload) <= 32 or not raw_payload.isprintable():
        raise ValueError("invalid raw payload")
    return config


def load(path: Path = ROOT / "config/application.toml") -> dict:
    """Load and validate policy; retain no file handle after returning."""
    with path.open("rb") as stream:
        return validate(tomllib.load(stream))


def render(config: dict) -> str:
    """Return deterministic C++17 constants from validated TOML policy."""
    validate(config)
    lines = [
        "// No repository-wide license is declared; existing rights are unchanged.",
        "",
        "// Generated application policy; edit config/application.toml.",
        "",
        "#ifndef SENIOR_PROJECT_RCA_APPLICATION_CONFIG_H_",
        "#define SENIOR_PROJECT_RCA_APPLICATION_CONFIG_H_",
        "#include <stdint.h>",
        "namespace application_config {",
    ]
    for section, values in config.items():
        if section == "schema_version":
            continue
        lines.append(f"namespace {section} {{")
        for key, value in values.items():
            name = "k" + "".join(word[:1].upper() + word[1:] for word in key.split("_"))
            if isinstance(value, str):
                lines.append(f"inline constexpr char {name}[] = {json.dumps(value)};")
            else:
                lines.append(f"inline constexpr uint32_t {name} = {value}UL;")
        lines.append(f"}}  // namespace {section}")
    lines += ["}  // namespace application_config", "#endif  // SENIOR_PROJECT_RCA_APPLICATION_CONFIG_H_", ""]
    return "\n".join(lines)


def raw_payload() -> bytes:
    """Return the same ASCII bytes used by the raw firmware diagnostics."""
    return load()["raw"]["payload"].encode("ascii")


def raw_send_command() -> str:
    """Build the existing canonical uppercase SEND command from raw policy."""
    return "SEND " + raw_payload().hex().upper()


if __name__ == "__main__":
    (ROOT / "include/application_config.h").write_text(render(load()))
