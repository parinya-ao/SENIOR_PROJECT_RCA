"""Build reproducible, host-only plans for the isolated LoRa RF stress suite."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import string
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

from tools import installed_rf
from tools.arq_trial import build_soak_plan
from tools.config.arq_config import load_arq
from tools.rf_stress.event_capture import load_event_journal
from tools.rf_stress.metrics import calculate_metrics
from tools.rf_stress.payload_generator import ALPHABET, generate_payload, split_payload
from tools.rf_stress.protocol_adapter import (
    SEQUENCE_MASK,
    SEQUENCE_ROLLOVER_WINDOW,
    FaultName,
    assess_case,
)
from tools.rf_stress.status import ResultStatus

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config/rf_stress.toml"
RADIO_PROFILE_PATH = ROOT / "config/radio_915.toml"
MINIMUM_REQUIRED_TORTURE_TRANSACTIONS = 1000


class RunProfile(StrEnum):
    """Named planning profiles accepted by the command line."""

    SMOKE = "smoke"
    TORTURE = "torture"


class RadioProfile(StrEnum):
    """Supported radio profile identifier in the runner configuration."""

    LORA_915 = "radio_915"


class RunMode(StrEnum):
    """Run modes recorded in the evidence manifest."""

    REAL_RF_REQUESTED = "REAL_RF_REQUESTED"


DIRECTIONS = ("gateway_to_tracker", "tracker_to_gateway")
FAULT_SCENARIOS = (
    ("SUPPRESS_ACK_ONCE", "ACK timeout followed by retry"),
    ("STALE_ACK", "stale response rejected by session"),
    ("WRONG_SEQUENCE", "wrong sequence response rejected"),
    ("WRONG_CAMPAIGN", "wrong campaign response rejected"),
    ("WRONG_DESTINATION", "DATA ignored without response"),
    ("INVALID_APP_PAYLOAD", "application NACK or defined rejection"),
    ("DELAYED_RESPONSE", "bounded timeout recovery"),
    ("SEQUENCE_ROLLOVER", "session-safe rollover"),
    ("PHY_CRC_CORRUPT", "timeout recovery after CRC rejection"),
    ("RECEIVER_RESET", "recovery after supported receiver restart"),
    ("CANCEL_UNDER_LOAD", "bounded cancellation and park"),
)
EXPECTED_RESULTS = {
    "NO_FAULT": "ACK",
    "FORCE_NACK_ONCE": "NACK_RETRY_ACK",
    "FORCE_NACK_TWICE": "NACK_RETRY_ACK",
    "DUPLICATE_DATA": "ACK_DUPLICATE_SUPPRESSED",
    "SUPPRESS_ACK_ONCE": "TIMEOUT_RETRY_ACK",
    "STALE_ACK": "STALE_RESPONSE_REJECTED",
    "WRONG_SEQUENCE": "WRONG_SEQUENCE_REJECTED",
    "WRONG_CAMPAIGN": "WRONG_CAMPAIGN_REJECTED",
    "WRONG_DESTINATION": "NO_REPLY_TIMEOUT",
    "INVALID_APP_PAYLOAD": "NACK",
    "DELAYED_RESPONSE": "TIMEOUT_RETRY_ACK",
    "SEQUENCE_ROLLOVER": "ROLLOVER_ACK",
    "PHY_CRC_CORRUPT": "CRC_REJECT_TIMEOUT",
    "RECEIVER_RESET": "RESET_RECOVERY_ACK",
    "CANCEL_UNDER_LOAD": "CANCELLED_AND_PARKED",
}


@dataclass(frozen=True, slots=True)
class RunOptions:
    """Validated operator choices for one bounded RF stress invocation."""

    seed: int
    maximum_minutes: int
    radio_profile: str


@dataclass(frozen=True, slots=True)
class RunPlan:
    """Host evidence prepared for one special-suite invocation."""

    output: Path
    manifest: dict[str, Any]
    cases: list[dict[str, Any]]
    metrics: dict[str, Any]
    summary: dict[str, Any]
    blockers: list[str]


@dataclass(frozen=True, slots=True)
class CaseSpec:
    """Immutable wire and campaign settings for one generated case group."""

    group_id: str
    session_id: int
    initial_sequence: int
    direction: str
    scenario: str
    fault: str
    maximum_length: int
    spacing_ms: int
    retries: int


def _validate_runner_settings(runner: object) -> None:
    """Validate the required seed, duration, and radio-profile settings."""
    runner_fields = {
        "default_seed",
        "long_duration_minutes",
        "maximum_runtime_minutes",
        "minimum_torture_transactions",
        "rf_profile",
    }
    if type(runner) is not dict or set(runner) != runner_fields:
        msg = "invalid RF stress runner settings"
        raise ValueError(msg)
    runner_settings = cast("dict[str, Any]", runner)
    if type(runner_settings["default_seed"]) is not int or runner_settings["default_seed"] < 0:
        msg = "default_seed must be a nonnegative integer"
        raise ValueError(msg)
    if (
        type(runner_settings["long_duration_minutes"]) is not int
        or type(runner_settings["maximum_runtime_minutes"]) is not int
        or not 1
        <= runner_settings["long_duration_minutes"]
        <= runner_settings["maximum_runtime_minutes"]
    ):
        msg = "invalid RF stress runtime limits"
        raise ValueError(msg)
    if (
        type(runner_settings["minimum_torture_transactions"]) is not int
        or runner_settings["minimum_torture_transactions"] < MINIMUM_REQUIRED_TORTURE_TRANSACTIONS
        or runner_settings["rf_profile"] != RadioProfile.LORA_915
    ):
        msg = "invalid torture requirement or RF profile"
        raise ValueError(msg)


def _validate_installed_pair(installed_pair: object) -> None:
    """Validate enrolled firmware environments and their capability lists."""
    installed_fields = {
        "gateway_environment",
        "tracker_environment",
        "gateway_capabilities",
        "tracker_capabilities",
    }
    if type(installed_pair) is not dict or set(installed_pair) != installed_fields:
        msg = "invalid installed firmware compatibility record"
        raise ValueError(msg)
    enrolled_pair = cast("dict[str, Any]", installed_pair)
    for key in ("gateway_capabilities", "tracker_capabilities"):
        if type(enrolled_pair[key]) is not list or any(
            type(value) is not str for value in enrolled_pair[key]
        ):
            msg = f"{key} must be a list of capability names"
            raise ValueError(msg)


def _validate_profiles(profiles: object, runner: dict[str, Any]) -> None:
    """Validate smoke, stress, and torture counts against the minimum workload."""
    if type(profiles) is not dict or set(profiles) != {"smoke", "stress", "torture"}:
        msg = "RF stress profiles must be smoke, stress and torture"
        raise ValueError(msg)
    configured_profiles = cast("dict[str, Any]", profiles)
    expected_profile = {
        "random_cases_per_direction",
        "nack_cases_total",
        "duplicate_cases_total",
    }
    for name, profile in configured_profiles.items():
        if type(profile) is not dict or set(profile) != expected_profile:
            msg = f"invalid {name} profile settings"
            raise ValueError(msg)
        if any(type(value) is not int or value < 0 for value in profile.values()):
            msg = f"{name} profile counts must be nonnegative integers"
            raise ValueError(msg)
    torture = configured_profiles["torture"]
    torture_transactions = (
        2 * torture["random_cases_per_direction"]
        + torture["nack_cases_total"]
        + torture["duplicate_cases_total"]
    )
    if torture_transactions < runner["minimum_torture_transactions"]:
        msg = "torture profile must schedule at least 1000 transactions"
        raise ValueError(msg)


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load the bounded stress profiles and reject unrecognized settings."""
    with path.open("rb") as stream:
        config = tomllib.load(stream)
    if set(config) != {"schema_version", "runner", "installed_pair", "profiles"}:
        msg = "unsupported RF stress configuration"
        raise ValueError(msg)
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        msg = "unsupported RF stress schema version"
        raise ValueError(msg)
    _validate_runner_settings(config["runner"])
    _validate_installed_pair(config["installed_pair"])
    _validate_profiles(config["profiles"], config["runner"])
    return config


def radio_configuration() -> dict[str, Any]:
    """Return the existing radio profile after matching it to ARQ test policy."""
    with RADIO_PROFILE_PATH.open("rb") as stream:
        profile = tomllib.load(stream)
    radio = profile["radio"]
    arq = load_arq()
    keys = {
        "frequency_hz": "frequency_hz",
        "bandwidth_khz": "bandwidth_khz",
        "spreading_factor": "spreading_factor",
        "coding_rate": "coding_rate",
        "sync_word": "sync_word",
        "tx_power_dbm": "tx_power_dbm",
        "preamble_symbols": "preamble_symbols",
        "crc_enabled": "crc_enabled",
        "explicit_header": "explicit_header",
        "iq_inverted": "iq_inverted",
    }
    if any(radio[key] != arq[arq_key] for key, arq_key in keys.items()):
        msg = "915 MHz radio profile differs from the configured ARQ test PHY"
        raise ValueError(msg)
    return cast("dict[str, Any]", radio)


def _append_case(
    cases: list[dict[str, Any]],
    payload: bytes,
    spec: CaseSpec,
) -> None:
    """Append bounded frame records while preserving the source case identity."""
    frames = split_payload(payload, spec.maximum_length)
    for part_index, frame in enumerate(frames, start=1):
        case_id = f"case-{len(cases) + 1:05d}"
        try:
            ascii_payload = frame.decode("ascii")
        except UnicodeDecodeError:
            ascii_payload = None
        cases.append(
            {
                "case_id": case_id,
                "group_id": spec.group_id,
                "session_id": spec.session_id,
                "sequence": (spec.initial_sequence + part_index) & SEQUENCE_MASK,
                "campaign_id": spec.session_id,
                "direction": spec.direction,
                "scenario": spec.scenario,
                "fault": spec.fault,
                "injection_point": spec.fault if spec.fault != FaultName.NO_FAULT else None,
                "expected_result": EXPECTED_RESULTS[spec.fault],
                "payload_hex": frame.hex(),
                "payload_ascii": ascii_payload,
                "payload_length_bytes": len(frame),
                "payload_sha256": hashlib.sha256(frame).hexdigest(),
                "part_index": part_index,
                "part_count": len(frames),
                "transaction_count": 1,
                "maximum_retries": spec.retries,
                "spacing_ms": spec.spacing_ms,
                "status": "NOT_RUN",
            }
        )


def _add_direction_cases(
    add_case: Callable[[bytes, str, str, str], None],
    rng: random.Random,
    profile: dict[str, Any],
    direction: str,
    maximum_length: int,
) -> None:
    """Add character, pattern, boundary, and seeded payload cases for one direction."""
    for character in ALPHABET:
        add_case(character.encode("ascii"), direction, "character_coverage", "NO_FAULT")
    patterns = (
        ("uppercase_only", string.ascii_uppercase.encode("ascii")),
        ("lowercase_only", string.ascii_lowercase.encode("ascii")),
        (
            "alternating_case",
            "".join(
                string.ascii_uppercase[index] + string.ascii_lowercase[index] for index in range(26)
            ).encode("ascii"),
        ),
        ("repeated_maximum", b"Z" * maximum_length),
        (
            "palindrome",
            (ALPHABET[: maximum_length // 2] + ALPHABET[: maximum_length // 2][::-1]).encode(
                "ascii"
            ),
        ),
        ("alphabet_forward", string.ascii_uppercase.encode("ascii")),
        ("alphabet_reverse", string.ascii_uppercase[::-1].encode("ascii")),
        ("full_alphabet", ALPHABET.encode("ascii")),
    )
    for scenario, payload in patterns:
        add_case(payload, direction, scenario, "NO_FAULT")
    for length in (1, 2, 15, 16, 31, maximum_length):
        if length <= maximum_length:
            add_case(generate_payload(length, rng), direction, "boundary_length", "NO_FAULT")
    for _ in range(profile["random_cases_per_direction"]):
        add_case(
            generate_payload(rng.randint(1, maximum_length), rng),
            direction,
            "random_ascii",
            "NO_FAULT",
        )


def build_case_plan(profile_name: str, seed: int) -> list[dict[str, Any]]:
    """Build deterministic character, boundary, random and fault cases."""
    config = load_config()
    profile = config["profiles"][profile_name]
    arq = load_arq()
    maximum_length = arq["payload_limit"]
    case_spacing_ms = int(build_soak_plan("1-session", arq)["session_interval_s"]) * 1000
    if type(seed) is not int or seed < 0:
        msg = "seed must be a nonnegative integer"
        raise ValueError(msg)
    rng = random.Random(seed)  # noqa: S311 -- seeded nonsecret test payloads require repeatability
    cases: list[dict[str, Any]] = []
    group_count = 0

    def add(payload: bytes, direction: str, scenario: str, fault: str = "NO_FAULT") -> None:
        """Attach current protocol limits to one planned application payload."""
        nonlocal group_count
        group_count += 1
        group_id = f"group-{group_count:05d}"
        session_id = ((seed + group_count - 1) % 0xFFFFFFFE) + 1
        spec = CaseSpec(
            group_id,
            session_id,
            arq["initial_sequence"],
            direction,
            scenario,
            fault,
            maximum_length,
            case_spacing_ms,
            arq["max_retries"],
        )
        _append_case(cases, payload, spec)

    def add_sequence_rollover() -> None:
        """Plan two same-session payloads at sequence 255 and 0."""
        nonlocal group_count
        group_count += 1
        session_id = ((seed + group_count - 1) % 0xFFFFFFFE) + 1
        payloads = (b"R", b"0")
        cases.append(
            {
                "case_id": f"case-{len(cases) + 1:05d}",
                "group_id": f"group-{group_count:05d}",
                "session_id": session_id,
                "campaign_id": session_id,
                "sequence": 255,
                "expected_sequences": list(SEQUENCE_ROLLOVER_WINDOW),
                "payloads_hex": [payload.hex() for payload in payloads],
                "payloads_sha256": [hashlib.sha256(payload).hexdigest() for payload in payloads],
                "payload_hex": payloads[0].hex(),
                "payload_ascii": "R",
                "payload_length_bytes": 1,
                "direction": "gateway_to_tracker",
                "scenario": "sequence_rollover",
                "fault": "SEQUENCE_ROLLOVER",
                "injection_point": "SEQUENCE_ROLLOVER",
                "expected_result": EXPECTED_RESULTS["SEQUENCE_ROLLOVER"],
                "part_index": 1,
                "part_count": 2,
                "transaction_count": 2,
                "maximum_retries": arq["max_retries"],
                "spacing_ms": case_spacing_ms,
                "status": "NOT_RUN",
            }
        )

    for direction in DIRECTIONS:
        _add_direction_cases(add, rng, profile, direction, maximum_length)

    for index in range(profile["nack_cases_total"]):
        direction = DIRECTIONS[index % len(DIRECTIONS)]
        fault = "FORCE_NACK_TWICE" if (index // len(DIRECTIONS)) % 2 else "FORCE_NACK_ONCE"
        add(generate_payload(11, rng), direction, "controlled_nack", fault)
    for index in range(profile["duplicate_cases_total"]):
        direction = DIRECTIONS[index % len(DIRECTIONS)]
        add(generate_payload(11, rng), direction, "duplicate_data", "DUPLICATE_DATA")

    add(b"\x00A\xff", "gateway_to_tracker", "binary_framing", "NO_FAULT")
    if profile_name != RunProfile.SMOKE:
        for fault, _ in FAULT_SCENARIOS:
            if fault == FaultName.SEQUENCE_ROLLOVER:
                add_sequence_rollover()
                continue
            payload = (
                arq["negative_payload"].encode("ascii")
                if fault == FaultName.INVALID_APP_PAYLOAD
                else generate_payload(11, rng)
            )
            add(payload, "gateway_to_tracker", "fault_injection", fault)
    return cases


def build_parser() -> argparse.ArgumentParser:
    """Create the standalone CLI without opening hardware or writing Flash."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("smoke", "stress", "torture"), default="smoke")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-minutes", type=int)
    parser.add_argument("--long-duration", action="store_true")
    parser.add_argument("--real-rf", action="store_true")
    parser.add_argument("--rf-profile")
    parser.add_argument("--readback", type=Path)
    parser.add_argument("--historical-receipt", type=Path)
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--case-id")
    return parser


def real_rf_blockers(
    args: argparse.Namespace, config: dict[str, Any]
) -> tuple[list[str], dict[str, Any]]:
    """Verify the supplied image evidence and compare it with stress requirements."""
    images = installed_rf.verify_snapshots(args.readback, args.historical_receipt)
    expected_pair = config["installed_pair"]
    expected_environments = {
        "GATEWAY": expected_pair["gateway_environment"],
        "RECEIVER": expected_pair["tracker_environment"],
    }
    for role, environment in expected_environments.items():
        if images[role]["environment"] != environment:
            return [
                f"{role}: installed image environment is not enrolled for this stress profile"
            ], images
    installed_capabilities = set(
        expected_pair["gateway_capabilities"] + expected_pair["tracker_capabilities"]
    )
    required_capabilities = {
        "arbitrary_payload_tx",
        "tracker_data_tx",
        "receiver_payload_hex",
        "fault_injection_controls",
        "duplicate_delivery_counter",
    }
    missing = sorted(required_capabilities - installed_capabilities)
    blockers = [f"installed firmware lacks {capability}" for capability in missing]
    blockers.append("the special host transaction transport is not implemented")
    return blockers, images


def _read_case_journal(path: Path) -> list[dict[str, Any]]:
    """Read a case journal and require the fields used by protocol assessment."""
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            msg = f"invalid case JSON at line {line_number}"
            raise ValueError(msg) from error
        required = {"case_id", "direction", "fault", "session_id", "sequence", "payload_hex"}
        if type(case) is not dict or not required <= set(case):
            msg = f"incomplete case row at line {line_number}"
            raise ValueError(msg)
        cases.append(case)
    return cases


def _output_directory(path: Path) -> Path:
    """Create a result directory without replacing earlier evidence."""
    if path.exists() and any(path.iterdir()):
        msg = f"refusing to overwrite existing RF stress evidence: {path}"
        raise FileExistsError(msg)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_replay_bundle(
    source_manifest: Path,
    output: Path,
    cases: list[dict[str, Any]],
    events: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> int:
    """Write a separate offline replay report and return its evidence status."""
    metrics = calculate_metrics(results)
    if metrics["fail"]:
        status, exit_code = "FAIL", 1
    elif metrics["unverified"]:
        status, exit_code = "UNVERIFIED", 2
    elif results:
        status, exit_code = "PASS", 0
    else:
        status, exit_code = "NOT_RUN", 2
    _output_directory(output)
    original = json.loads(source_manifest.read_text(encoding="utf-8"))
    manifest = {
        "run_id": datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ"),
        "mode": "OFFLINE_REPLAY",
        "replay_of": str(source_manifest.resolve()),
        "profile": original.get("profile"),
        "seed": original.get("seed"),
        "rf_transmissions": 0,
        "status": status,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with (output / "cases.jsonl").open("w", encoding="utf-8") as stream:
        for case in cases:
            stream.write(json.dumps(case, sort_keys=True) + "\n")
    with (output / "events.jsonl").open("w", encoding="utf-8") as stream:
        for event in events:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
    failures = [result for result in results if result["status"] != ResultStatus.SUCCESS]
    (output / "failures.jsonl").write_text(
        "".join(json.dumps(result, sort_keys=True) + "\n" for result in failures),
        encoding="utf-8",
    )
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    summary = {"status": status, "rf_transmissions": 0, **metrics}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    report = [
        "# LoRa RF Stress Replay",
        "",
        f"- Status: {status}",
        f"- Cases: {metrics['scheduled_transactions']}",
        f"- PASS: {metrics['pass']}",
        f"- FAIL: {metrics['fail']}",
        f"- UNVERIFIED: {metrics['unverified']}",
        "- RF transmissions during replay: 0",
        "",
        "## Nonpassing cases",
        "",
    ]
    report.extend(
        f"- {result['case_id']}: {result['status']} — {result['reason']}" for result in failures
    )
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return exit_code


def replay_bundle(args: argparse.Namespace, output: Path) -> int:
    """Assess a saved journal without opening a serial port or starting RF."""
    source_manifest = args.replay
    source_dir = source_manifest.parent
    cases = _read_case_journal(source_dir / "cases.jsonl")
    if args.case_id is not None:
        cases = [case for case in cases if case["case_id"] == args.case_id]
        if not cases:
            msg = f"case {args.case_id} was not found in the replay bundle"
            raise ValueError(msg)
    events = load_event_journal(source_dir / "events.jsonl")
    results = [assess_case(case, events) for case in cases]
    return _write_replay_bundle(source_manifest, output, cases, events, results)


def _validated_options(
    args: argparse.Namespace, config: dict[str, Any], parser: argparse.ArgumentParser
) -> RunOptions:
    """Validate run bounds and return an immutable set of operator choices."""
    runner = config["runner"]
    seed = runner["default_seed"] if args.seed is None else args.seed
    if seed < 0:
        parser.error("--seed must be nonnegative")
    default_runtime = (
        runner["maximum_runtime_minutes"] if args.long_duration else runner["long_duration_minutes"]
    )
    max_minutes = default_runtime if args.max_minutes is None else args.max_minutes
    if not 1 <= max_minutes <= runner["maximum_runtime_minutes"]:
        parser.error("--max-minutes exceeds the configured bound")
    if (
        max_minutes > runner["long_duration_minutes"] or args.profile == RunProfile.TORTURE
    ) and not args.long_duration:
        parser.error(
            "--long-duration is required for torture or runs over the configured short limit"
        )
    rf_profile = runner["rf_profile"] if args.rf_profile is None else args.rf_profile
    if rf_profile != runner["rf_profile"]:
        parser.error("this test configuration only supports the verified radio_915 profile")
    if args.real_rf and (
        args.rf_profile is None or args.readback is None or args.historical_receipt is None
    ):
        parser.error("--real-rf requires --readback and --historical-receipt preflight evidence")
    if args.real_rf and args.rf_profile != runner["rf_profile"]:
        parser.error("--real-rf requires explicit --rf-profile radio_915")
    return RunOptions(seed, max_minutes, rf_profile)


def _prepare_run(args: argparse.Namespace, config: dict[str, Any], options: RunOptions) -> RunPlan:
    """Build the seeded plan, verify RF inputs and calculate bounded airtime/runtime."""
    radio = radio_configuration()
    cases = build_case_plan(args.profile, options.seed)
    arq = load_arq()
    radio_airtime_plan = build_soak_plan("1-session", arq)
    spacing_budget_ms = sum(case["spacing_ms"] * case["transaction_count"] for case in cases)
    minimum_runtime_seconds = max(0, spacing_budget_ms - cases[-1]["spacing_ms"]) / 1000
    planned_transactions = sum(case["transaction_count"] for case in cases)
    maximum_attempt_ms = (arq["max_retries"] + 1) * (arq["tx_ms"] + arq["ack_max_ms"])
    worst_case_runtime_seconds = sum(
        (case["spacing_ms"] + maximum_attempt_ms) * case["transaction_count"] / 1000
        for case in cases
    )
    runtime_feasible = worst_case_runtime_seconds <= options.maximum_minutes * 60
    blockers: list[str] = []
    images: dict[str, Any] = {}
    if args.real_rf:
        try:
            blockers, images = real_rf_blockers(args, config)
        except (OSError, ValueError) as error:
            blockers = [f"installed image preflight failed: {error}"]
        if not runtime_feasible:
            blockers.append(
                "selected runtime cap cannot schedule every planned case at configured spacing"
            )
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    output = args.output or ROOT / "artifacts/rf-stress" / run_id
    manifest = {
        "run_id": run_id,
        "mode": "REAL_RF_REQUESTED" if args.real_rf else "DRY_RUN",
        "profile": args.profile,
        "seed": options.seed,
        "rf_transmissions": 0,
        "rf_profile": options.radio_profile,
        "radio": radio,
        "payload_limit_bytes": load_arq()["payload_limit"],
        "firmware_spacing_ms": load_arq()["spacing_ms"],
        "minimum_case_spacing_ms": min(case["spacing_ms"] for case in cases),
        "maximum_case_spacing_ms": max(case["spacing_ms"] for case in cases),
        "planned_cases": len(cases),
        "planned_transactions": planned_transactions,
        "minimum_runtime_seconds": minimum_runtime_seconds,
        "worst_case_runtime_seconds": worst_case_runtime_seconds,
        "radio_airtime_plan": {
            key: radio_airtime_plan[key]
            for key in (
                "maximum_wire_data_bytes",
                "control_frame_bytes",
                "max_attempts",
                "data_toa_us",
                "control_toa_us",
                "session_interval_s",
                "duty_cycle_target_percent",
                "gateway_duty_percent_at_interval",
                "tracker_duty_percent_at_interval",
            )
        },
        "max_runtime_minutes": options.maximum_minutes,
        "runtime_feasible": runtime_feasible,
        "status": "BLOCKED" if blockers else "NOT_RUN",
        "images": {
            role: {
                "environment": image["environment"],
                "build_id": image["build_id"],
                "serial_number": image["serial_number"],
                "readback_region_sha256": image["readback_region_sha256"],
            }
            for role, image in images.items()
        },
        "blockers": blockers,
    }
    if args.real_rf:
        reason = "; ".join(blockers)
    elif runtime_feasible:
        reason = "dry run only"
    else:
        reason = "dry run only; runtime cap cannot complete the plan"
    metrics = {
        "planned_cases": len(cases),
        "planned_transactions": planned_transactions,
        "rf_transmissions": 0,
        "pass": 0,
        "fail": 0,
        "unverified": 0,
        "not_run": len(cases),
        "retries": None,
        "timeouts": None,
        "duplicate_deliveries": None,
        "payload_mismatches": None,
        "unexpected_resets": None,
        "reset_count": None,
        "rssi_dbm": None,
        "snr_db": None,
        "radio_error_codes": None,
        "irq_flags_seen": None,
        "latency_ms": None,
        "airtime_us": None,
    }
    summary = {
        "status": manifest["status"],
        "reason": reason,
        "planned_cases": len(cases),
        "planned_transactions": planned_transactions,
        "rf_transmissions": 0,
        "runtime_feasible": runtime_feasible,
    }
    return RunPlan(output, manifest, cases, metrics, summary, blockers)


def _write_run_bundle(plan: RunPlan) -> None:
    """Persist a plan or preflight block without overwriting prior evidence."""
    output = _output_directory(plan.output)
    (output / "manifest.json").write_text(
        json.dumps(plan.manifest, indent=2) + "\n", encoding="utf-8"
    )
    with (output / "cases.jsonl").open("w", encoding="utf-8") as stream:
        for case in plan.cases:
            stream.write(json.dumps(case, sort_keys=True) + "\n")
    (output / "events.jsonl").write_text("", encoding="utf-8")
    (output / "failures.jsonl").write_text("", encoding="utf-8")
    (output / "metrics.json").write_text(
        json.dumps(plan.metrics, indent=2) + "\n", encoding="utf-8"
    )
    (output / "summary.json").write_text(
        json.dumps(plan.summary, indent=2) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(
        "# LoRa RF Stress Run\n\n"
        f"- Status: {plan.summary['status']}\n"
        f"- Profile: {plan.manifest['profile']}\n"
        f"- Seed: {plan.manifest['seed']}\n"
        f"- Planned cases: {len(plan.cases)}\n"
        "- RF transmissions: 0\n"
        f"- Result: {plan.summary['reason']}\n",
        encoding="utf-8",
    )


def _display_run(plan: RunPlan) -> None:
    """Print only observed preflight status and planned case counts."""
    real_rf = plan.manifest["mode"] == RunMode.REAL_RF_REQUESTED
    print(f"MODE={'REAL_RF_REQUESTED' if real_rf else 'DRY_RUN'}")
    print("RF_TRANSMISSIONS=0")
    print(f"PROFILE={plan.manifest['profile']}")
    print(f"SEED={plan.manifest['seed']}")
    print(f"CASES={len(plan.cases)}")
    print(f"TRANSACTIONS={plan.manifest['planned_transactions']}")
    if real_rf:
        print("RESULT=BLOCKED")
        for blocker in plan.blockers:
            print(f"BLOCKER={blocker}")
    print(f"ARTIFACTS={plan.output}")


def main() -> int:
    """Write a reproducible dry-run bundle and refuse unsupported live firmware."""
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()
    if args.replay is not None:
        if args.real_rf:
            parser.error("offline replay never starts RF transmission")
        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        output = args.output or ROOT / "artifacts/rf-stress" / f"replay-{run_id}"
        try:
            result = replay_bundle(args, output)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print("MODE=OFFLINE_REPLAY")
        print("RF_TRANSMISSIONS=0")
        print(f"RESULT={('PASS' if result == 0 else 'FAIL_OR_UNVERIFIED')}")
        print(f"ARTIFACTS={output}")
        return result
    if args.case_id is not None:
        parser.error("--case-id requires --replay")
    options = _validated_options(args, config, parser)
    try:
        plan = _prepare_run(args, config, options)
        _write_run_bundle(plan)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    _display_run(plan)
    return int(args.real_rf)
