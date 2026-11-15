"""Command-driven physical ARQ trials; integrity checks do not prove physical origin.

python tools/arq_trial.py --campaign   # program verified pages, then sequential gates
python tools/arq_trial.py --validate artifacts/arq/<run>/H01/bundle.json
"""

import argparse
import fcntl
import hashlib
import json
import math
import os
import queue
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AVR_DA_GPIOR0 = 0x1C
AVR_DA_RSTCTRL_RSTFR = 0x40
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/config"))
import receiver_boot as boot
import rf_proof as rf


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_virtual_uart(writer, payload, *, per_byte_timeout=2.0, accepted=None):
    accepted = accepted if accepted is not None else bytearray()
    for index, byte in enumerate(payload):
        deadline = time.monotonic() + per_byte_timeout
        while not writer.send1(byte, blocking=False):
            if time.monotonic() >= deadline:
                raise TimeoutError(f"virtual UART byte {index} was not accepted")
            time.sleep(0.01)
        accepted.append(byte)
    return bytes(accepted)


def read_reset_state(session, protocol):
    link = getattr(session, "updi", session)
    return dict(
        gpior0=link.lds8(AVR_DA_GPIOR0),
        rstfr=link.lds8(AVR_DA_RSTCTRL_RSTFR),
        uart_flags=link.lds8(protocol.UART_FLAGS),
    )


def sample_updi_idle(session, protocol, seconds):
    start_ns = time.monotonic_ns()
    before = read_reset_state(session, protocol)
    time.sleep(seconds)
    after = read_reset_state(session, protocol)
    end_ns = time.monotonic_ns()
    return dict(
        before=before, after=after, start_ns=start_ns, end_ns=end_ns, duration_ns=end_ns - start_ns
    )


def parse_event(line):
    if not line.startswith("A "):
        return None
    pairs = dict(re.findall(r"(\w+)=([^\s]+)", line))
    if not {"t", "e", "s"} <= pairs.keys():
        raise ValueError("incomplete event")
    # AVR printf_min ignores zero-padding; ARM input remains exactly eight hex digits.
    if not re.fullmatch(r"[0-9A-F]{1,8}", pairs["s"]):
        raise ValueError("invalid event session")
    int(pairs["t"])
    return pairs


def wire_frame(raw):
    b = bytes.fromhex(raw)
    if (
        len(b) < 12
        or len(b) > 44
        or b[0] != 1
        or b[1] not in (1, 2, 3)
        or b[10] > 32
        or len(b) != 12 + b[10]
    ):
        raise ValueError("invalid wire frame")
    if (
        (b[1] in (1, 2) and b[11])
        or (b[1] != 1 and b[10])
        or (b[1] == 3 and b[11] not in (1, 2, 3))
    ):
        raise ValueError("invalid wire fields")
    return dict(
        type=b[1],
        src=b[2],
        dst=b[3],
        session=int.from_bytes(b[4:8], "little"),
        sequence=int.from_bytes(b[8:10], "little"),
        reason=b[11],
        payload=b[12:],
    )


SOAK_INTERVAL_MIN_SECONDS = 60
SOAK_SESSION_STAGES = {
    "1-session": 1,
    "10-sessions": 10,
    "100-sessions": 100,
    "1000-sessions": 1000,
}
SOAK_DURATION_STAGES = {"1-hour": 3600, "8-hours": 8 * 3600, "24-hours": 24 * 3600}
SOAK_STAGE_ORDER = tuple(SOAK_SESSION_STAGES) + tuple(SOAK_DURATION_STAGES)


def missing_soak_prerequisites(stage, completed):
    if stage not in SOAK_STAGE_ORDER:
        raise ValueError("unknown soak stage")

    def passed(value):
        return value == "PASS" or (isinstance(value, dict) and value.get("status") == "PASS")

    return [
        previous
        for previous in SOAK_STAGE_ORDER[: SOAK_STAGE_ORDER.index(stage)]
        if not passed(completed.get(previous))
    ]


def wilson_interval95(successes, trials):
    if (
        type(successes) is not int
        or type(trials) is not int
        or trials < 0
        or not 0 <= successes <= trials
    ):
        raise ValueError("invalid binomial counts")
    if trials == 0:
        return None
    z = 1.959963984540054
    p = successes / trials
    z2 = z * z
    scale = 1 + z2 / trials
    center = (p + z2 / (2 * trials)) / scale
    margin = z * math.sqrt((p * (1 - p) + z2 / (4 * trials)) / trials) / scale
    return dict(lower=max(0.0, center - margin), upper=min(1.0, center + margin))


def summarize_soak_results(results, target_sessions):
    if type(target_sessions) is not int or target_sessions < 1:
        raise ValueError("invalid soak target")
    attempted = len(results)
    successes = sum(r.get("complete") is True and r.get("delivered") == 1 for r in results)
    first = sum(r.get("first_attempt", 0) for r in results)
    attempts = [r.get("attempts") for r in results]
    attempts_known = all(type(n) is int and n >= 1 for n in attempts)
    retries = [r.get("retries") for r in results]
    retries_known = all(type(n) is int and n >= 0 for n in retries)
    retransmissions = (
        sum(retries) if retries_known else sum(n - 1 for n in attempts) if attempts_known else None
    )
    rtts = [
        r["rtt"]["average"]
        for r in results
        if r.get("rtt", {}).get("count", 0) > 0 and r["rtt"].get("average") is not None
    ]
    durations = [
        r["session_duration_s"]
        for r in results
        if isinstance(r.get("session_duration_s"), (int, float))
    ]

    def latency(values):
        ordered = sorted(values)
        count = len(ordered)

        def nearest(q):
            return ordered[math.ceil(q * count) - 1] if count else None

        return dict(
            count=count,
            mean=statistics.fmean(ordered) if count else None,
            median=statistics.median(ordered) if count else None,
            p50=statistics.median(ordered) if count else None,
            p90=nearest(0.90) if count >= 20 else None,
            p95=nearest(0.95) if count >= 20 else None,
            p99=nearest(0.99) if count >= 100 else None,
            maximum=max(ordered) if count else None,
            percentile_minimum_samples=dict(p90=20, p95=20, p99=100),
        )

    timeouts = [r.get("ack_timeouts") for r in results]
    reset_counts = [r.get("unexpected_resets") for r in results]
    return dict(
        target_sessions=target_sessions,
        sessions_attempted=attempted,
        successes=successes,
        failures=attempted - successes,
        sessions_not_completed=max(0, target_sessions - attempted),
        first_attempt_successes=first,
        success_rate=successes / attempted if attempted else None,
        first_attempt_success_rate=first / attempted if attempted else None,
        success_rate_95_ci=wilson_interval95(successes, attempted),
        data_attempts=sum(attempts) if attempts_known else None,
        retransmissions=retransmissions,
        ack_timeouts=sum(timeouts) if all(type(n) is int and n >= 0 for n in timeouts) else None,
        unexpected_resets=sum(reset_counts)
        if all(type(n) is int and n >= 0 for n in reset_counts)
        else None,
        ack_rtt_ms=latency(rtts),
        host_session_elapsed_s=latency(durations),
    )


def soak_result_metrics(report, bundle_path, elapsed_s):
    if report.get("complete") is not True or report.get("delivered") != 1:
        raise ValueError("soak session lacks validated DATA/ACK completion")
    events = json.loads(Path(bundle_path).read_text()).get("events")
    if not isinstance(events, list):
        raise ValueError("soak session event evidence missing")
    terminal = [e for e in events if e.get("role") == "sender" and e.get("e") == "DELIVERED"]
    if len(terminal) != 1:
        raise ValueError("soak session terminal event missing or ambiguous")
    attempts = int(terminal[0]["v"])
    sequence = int(terminal[0]["q"])
    data = []
    for event in events:
        if event.get("role") == "sender" and event.get("e") == "TX":
            frame = wire_frame(event["bytes"])
            if frame["type"] == 1 and frame["sequence"] == sequence:
                data.append(event)
    if attempts < 1 or len(data) != attempts:
        raise ValueError("soak retry count differs from captured DATA frames")
    return dict(
        report,
        attempts=attempts,
        retries=attempts - 1,
        ack_timeouts=sum(e.get("role") == "sender" and e.get("e") == "RX_TIMEOUT" for e in events),
        unexpected_resets=0,
        session_duration_s=elapsed_s,
        reset_observation="no reset/session change accepted by per-session bundle validation",
    )


def lora_time_on_air_us(payload_length, config):
    """Semtech SX127x LoRa packet airtime for the selected radio profile."""
    if type(payload_length) is not int or not 1 <= payload_length <= 255:
        raise ValueError("invalid LoRa payload length")
    sf = config["spreading_factor"]
    bw_hz = config["bandwidth_khz"] * 1000
    coding_rate = config["coding_rate"] - 4
    preamble = config["preamble_symbols"]
    if not 6 <= sf <= 12 or bw_hz <= 0 or not 1 <= coding_rate <= 4 or preamble < 0:
        raise ValueError("invalid LoRa airtime profile")
    crc = int(bool(config["crc_enabled"]))
    implicit = int(not config["explicit_header"])
    de = int((1 << sf) * 1_000_000 > 16_000 * bw_hz)
    numerator = 8 * payload_length - 4 * sf + 28 + 16 * crc - 20 * implicit
    denominator = 4 * (sf - 2 * de)
    quotient = (numerator + denominator - 1) // denominator if numerator > 0 else 0
    payload_symbols = 8 + max(quotient * (coding_rate + 4), 0)
    quarter_symbols = 4 * preamble + 17 + 4 * payload_symbols
    numerator_us = quarter_symbols * (1 << sf) * 1_000_000
    return (numerator_us + 4 * bw_hz - 1) // (4 * bw_hz)


def build_soak_plan(stage, config):
    if stage not in SOAK_SESSION_STAGES and stage not in SOAK_DURATION_STAGES:
        raise ValueError("unknown soak stage")
    data_bytes = 12 + config["payload_limit"]
    control_bytes = 12
    attempts = config["max_retries"] + 1
    data_airtime = lora_time_on_air_us(data_bytes, config)
    control_airtime = lora_time_on_air_us(control_bytes, config)
    minimum_firmware_spacing_ms = math.ceil(data_airtime / 10)
    firmware_spacing = config["spacing_ms"]
    if firmware_spacing < minimum_firmware_spacing_ms:
        raise ValueError("ARQ firmware spacing does not meet the 1% DATA airtime target")
    gateway_airtime = data_airtime * attempts
    tracker_airtime = control_airtime * attempts
    interval = max(
        SOAK_INTERVAL_MIN_SECONDS, math.ceil(max(gateway_airtime, tracker_airtime) / 10_000)
    )
    duration = SOAK_DURATION_STAGES.get(stage)
    sessions = (
        SOAK_SESSION_STAGES[stage] if duration is None else math.ceil(duration / interval) + 1
    )
    return dict(
        stage=stage,
        target_duration_s=duration,
        sessions=sessions,
        session_interval_s=interval,
        minimum_interval_s_for_one_percent=math.ceil(
            max(gateway_airtime, tracker_airtime) / 10_000
        ),
        maximum_wire_data_bytes=data_bytes,
        control_frame_bytes=control_bytes,
        max_attempts=attempts,
        data_toa_us=data_airtime,
        control_toa_us=control_airtime,
        firmware_tx_spacing_ms=firmware_spacing,
        firmware_frame_duty_percent=100 * data_airtime / (firmware_spacing * 1000),
        gateway_worst_case_session_airtime_us=gateway_airtime,
        tracker_worst_case_session_airtime_us=tracker_airtime,
        gateway_duty_percent_at_interval=100 * gateway_airtime / (interval * 1_000_000),
        tracker_duty_percent_at_interval=100 * tracker_airtime / (interval * 1_000_000),
        duty_cycle_target_percent=1.0,
        regulatory_note="1% is a conservative planning target; actual EIRP, equipment conformity and authorization must be verified separately.",
    )


def run_paced_sessions(session_count, interval_s, run_one, *, clock=None, sleep=None):
    if type(session_count) is not int or not 1 <= session_count <= 10000:
        raise ValueError("invalid soak session count")
    if type(interval_s) is not int or interval_s < SOAK_INTERVAL_MIN_SECONDS:
        raise ValueError("soak interval is below the airtime safety floor")
    clock = clock or time.monotonic
    sleep = sleep or time.sleep
    results = []
    next_start = None
    for index in range(session_count):
        if next_start is not None:
            delay = next_start - clock()
            if delay > 0:
                sleep(delay)
        started = clock()
        results.append(run_one(index))
        next_start = started + interval_s
    return results


def reader_free_h01_summary(events, reset_before=None, reset_after=None):
    """Summarize H01 boundaries without treating absent logs as failed events."""
    malformed_frames = []

    def frame_seen(role, name, frame_type) -> bool | None:
        for event in events:
            if event.get("role") != role or event.get("e") != name or "bytes" not in event:
                continue
            try:
                if wire_frame(event["bytes"])["type"] == frame_type:
                    return True
            except (TypeError, ValueError) as error:
                malformed_frames.append(dict(role=role, event=name, error=str(error)))
        return None

    def tx_done_seen(role) -> bool | None:
        rows = [
            event for event in events if event.get("role") == role and event.get("e") == "TX_DONE"
        ]
        if not rows:
            return None
        for event in rows:
            try:
                if event.get("rc") == "0" and int(event["v"]) & 0x08:
                    return True
            except KeyError, TypeError, ValueError:
                continue
        return False

    terminals = [
        event.get("e")
        for event in events
        if event.get("role") == "sender"
        and event.get("e")
        in ("DELIVERED", "REJECTED", "PROTOCOL_ERROR", "TIMEOUT_EXHAUSTED", "RADIO_ERROR")
    ]
    before_por = (
        None
        if not isinstance(reset_before, dict) or type(reset_before.get("gpior0")) is not int
        else bool(reset_before["gpior0"] & 0x01)
    )
    after_por = (
        None
        if not isinstance(reset_after, dict) or type(reset_after.get("gpior0")) is not int
        else bool(reset_after["gpior0"] & 0x01)
    )
    return dict(
        gateway_data_tx_done=tx_done_seen("sender"),
        tracker_data_rx=frame_seen("receiver", "RX", 1),
        tracker_data_accepted=next(
            (
                True
                for event in events
                if event.get("role") == "receiver" and event.get("e") == "ACCEPT"
            ),
            None,
        ),
        tracker_ack_tx_started=frame_seen("receiver", "TX", 2),
        tracker_ack_tx_done=tx_done_seen("receiver"),
        gateway_ack_rx=frame_seen("sender", "RX", 2),
        gateway_terminal=terminals[-1] if terminals else None,
        reset_state_before=reset_before,
        reset_state_after=reset_after,
        porf_before=before_por,
        porf_after=after_por,
        porf_transition_to_set=None
        if before_por is None or after_por is None
        else after_por and not before_por,
        malformed_frames=malformed_frames,
    )


def reader_free_rx_idle_summary(sample):
    before = sample.get("before") if isinstance(sample, dict) else None
    after = sample.get("after") if isinstance(sample, dict) else None
    before_por = (
        None
        if not isinstance(before, dict) or type(before.get("gpior0")) is not int
        else bool(before["gpior0"] & 1)
    )
    after_por = (
        None
        if not isinstance(after, dict) or type(after.get("gpior0")) is not int
        else bool(after["gpior0"] & 1)
    )
    if before_por is None or after_por is None or before_por:
        classification = "UNKNOWN"
    elif after_por:
        classification = "POR_OBSERVED"
    else:
        classification = "NO_POR_OBSERVED"
    return dict(
        classification=classification,
        before=before,
        after=after,
        porf_before=before_por,
        porf_after=after_por,
        porf_transition_to_set=None
        if before_por is None or after_por is None
        else after_por and not before_por,
    )


def reader_free_h01_firmware(root, role, *, reverse=False):
    if role not in ("receiver", "sender"):
        raise ValueError("unknown ARQ role")
    environment = role + "_arq_radio_only" + ("_reverse" if reverse else "")
    directory = Path(root) / ".pio/build" / environment
    identity = (directory / "lora_build_identity.h").read_text()
    match = re.search(r'LORA_BUILD_ID "([0-9a-f]{64})"', identity)
    if not match:
        raise ValueError("missing firmware build identity: " + environment)
    return dict(
        environment=environment, sha256=sha(directory / "firmware.hex"), build_id=match.group(1)
    )


def open_reader_free_h01_session(port):
    sys.path.insert(0, str(ROOT / "third_party/upditerm"))
    import upditerm

    return upditerm.SerialUPDI(port, 38400), upditerm


def reserve_session(directory):
    directory.mkdir(parents=True, exist_ok=True)
    # Lock a stable inode; replace only the counter so crashes cannot truncate it.
    with (directory / "session.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        counter = directory / "session.json"
        value = json.loads(counter.read_text()) if counter.exists() else 0
        if type(value) is not int or not 0 <= value < 0xFFFFFFFF:
            raise ValueError("session counter exhausted/corrupt")
        value += 1
        from generate_lora_config import _write_atomic

        _write_atomic(counter, json.dumps(value) + "\n")
        return value


def checked_events(events, directory):
    captured = []
    for role in ("sender", "receiver"):
        rows = []
        for line in (Path(directory) / f"rf-monitor-{role}.stdout.log").read_text().splitlines():
            event = parse_event(line.strip())
            if event:
                rows.append(dict(event, role=role))
        supplied = [
            {k: v for k, v in event.items() if k != "host_ns"}
            for event in events
            if event["role"] == role
        ]
        if supplied != rows:
            raise ValueError("event journal differs from raw captured stream")
        captured += rows
    return captured


def status_complete(events, role, session):
    rows = [e for e in events if e["role"] == role and int(e["s"], 16) == session]
    statuses = [i for i, e in enumerate(rows) if e["e"] == "STATUS"]
    ends = [i for i, e in enumerate(rows) if e["e"] == "STATUS_END"]
    return bool(statuses and ends and ends[-1] > statuses[-1] and rows[ends[-1]].get("v") == "0")


def validate_bundle(b, directory=None):
    required = {
        "acquisition",
        "session",
        "gate",
        "count",
        "events",
        "files",
        "programming",
        "config_hash",
        "firmware",
        "commands",
    }
    if (
        not isinstance(b, dict)
        or not required <= b.keys()
        or b.get("synthetic") is not False
        or b["acquisition"] != "updi-live"
    ):
        raise ValueError("not a complete live-acquisition bundle; text/simulation is insufficient")
    if not b["programming"] or set(b["firmware"]) != {"sender", "receiver"} or not b["files"]:
        raise ValueError("missing programming/firmware provenance")
    if directory is None:
        raise ValueError("bundle directory required for independent file verification")
    directory = Path(directory).resolve()
    for name, expected in b["files"].items():
        p = (directory / name).resolve()
        if not p.is_relative_to(directory) or sha(p) != expected:
            raise ValueError("evidence file integrity mismatch")
    events = checked_events(b["events"], directory)
    session = b["session"]
    count = b["count"]
    if type(count) is not int or count < 1 or count > 100:
        raise ValueError("invalid trial count")
    for role in ("sender", "receiver"):
        rows = [x for x in events if x["role"] == role]
        arms = [
            x for x in rows if x["e"] == "ARM" and int(x["s"], 16) == session and x.get("rc") == "0"
        ]
        statuses = [x for x in rows if x["e"] == "STATUS" and int(x["s"], 16) == session]
        if (
            len(arms) != 1
            or not statuses
            or statuses[-1]["overflow"] != "0"
            or statuses[-1]["ready"] != "1"
            or not status_complete(events, role, session)
        ):
            raise ValueError("missing ARM/final status or overflow/radio failure")
        if any(int(x["s"], 16) != session for x in rows[rows.index(arms[0]) + 1 :]):
            raise ValueError("reset/session changed during trial")
        identities = [x for x in rows if x["e"] == "IDENTITY"]
        if not identities or any(
            x["config"] != b["config_hash"] or x["build"] != b["programming"][role]["build_id"]
            for x in identities
        ):
            raise ValueError("firmware/config identity mismatch")
        if any(x["e"] == "BOOT" and x.get("v") != "0" for x in rows[rows.index(arms[0]) + 1 :]):
            # Retained BOOT repeats via STATUS; compare reset flags, not their nonzero value.
            boots = [x.get("v") for x in rows if x["e"] == "BOOT"]
            if len(set(boots)) > 1:
                raise ValueError("reset evidence")
    relevant = [x for x in events if int(x["s"], 16) == session]
    manifest = json.loads((directory / "provenance/manifest.json").read_text())
    if manifest["config_hash"] != b["config_hash"]:
        raise ValueError("manifest/config hash mismatch")
    for role in ("sender", "receiver"):
        env = b["programming"][role]["environment"]
        image = directory / "provenance" / (env + ".hex")
        if sha(image) != b["firmware"][role]:
            raise ValueError("firmware hash mismatch")
        before = {}
        after = {}
        for memory in ("signature", "sernum", "flash", "eeprom", "fuses", "lock"):
            for label, target in (("before", before), ("after", after)):
                target[memory] = (
                    directory / "provenance" / f"{env}-{label}-page-write-{memory}.bin"
                ).read_bytes()
        region = rf.parse_ihex_range(image.read_bytes())
        first = region["start"]
        end = (region["end_exclusive"] + 511) // 512 * 512
        boot.require_preserved(before, after, first, end)
        from device_detection.firmware_identity import normalize_ihex_region

        if after["flash"][first:end] != normalize_ihex_region(image.read_text(), first, end):
            raise ValueError("independent installed-image mismatch")
    terminals = [
        x
        for x in relevant
        if x["role"] == "sender"
        and x["e"]
        in ("DELIVERED", "REJECTED", "PROTOCOL_ERROR", "TIMEOUT_EXHAUSTED", "RADIO_ERROR")
    ]
    expected = "REJECTED" if b["gate"] == "H02" else "DELIVERED"
    if len(terminals) != count or any(x["e"] != expected for x in terminals):
        raise ValueError("missing/failed terminal outcomes")
    if len({x["q"] for x in terminals}) != count:
        raise ValueError("reused sequence")
    frames = []
    for x in relevant:
        if x["e"] in ("TX", "RX"):
            f = wire_frame(x["bytes"])
            if f["session"] != session:
                raise ValueError("stale session RF")
            frames.append((x, f))
    for terminal in terminals:
        seq = int(terminal["q"])
        data = [
            (x, f)
            for x, f in frames
            if x["role"] == "sender" and x["e"] == "TX" and f["type"] == 1 and f["sequence"] == seq
        ]
        if not data or len({x["bytes"] for x, f in data}) != 1:
            raise ValueError("missing/nonimmutable DATA")
        d = data[0][1]
        cfg = manifest["config"]
        payload = cfg["negative_payload" if b["gate"] == "H02" else "payload"].encode("ascii")
        if (
            d["src"] != cfg["sender_id"]
            or d["dst"] != cfg["receiver_id"]
            or d["payload"] != payload
        ):
            raise ValueError("incorrect DATA")
        if int(terminal["v"]) != len(data):
            raise ValueError("attempt count differs from RF frames")
        kind = 3 if expected == "REJECTED" else 2
        controls = [
            (x, f)
            for x, f in frames
            if f["type"] == kind
            and f["sequence"] == seq
            and f["src"] == cfg["receiver_id"]
            and f["dst"] == cfg["sender_id"]
            and (kind != 3 or f["reason"] == 2)
        ]
        if not any(x["role"] == "receiver" and x["e"] == "TX" for x, f in controls) or not any(
            x["role"] == "sender" and x["e"] == "RX" for x, f in controls
        ):
            raise ValueError("matching real control pair missing")
        if not any(
            x["role"] == "receiver" and x["e"] == "RX" and x["bytes"] == data[0][0]["bytes"]
            for x, f in frames
        ):
            raise ValueError("receiver DATA evidence missing")
    status = [x for x in relevant if x["role"] == "receiver" and x["e"] == "STATUS"][-1]
    if int(status["app"]) != (0 if expected == "REJECTED" else count):
        raise ValueError("application delivery count")
    if b["gate"] in ("H03", "H06"):
        drops = (
            1
            if b["gate"] == "H03"
            else min(
                count // manifest["config"]["fault_ack_stride"],
                manifest["config"]["fault_drop_budget"],
            )
        )
        if int(status["sup"]) != drops or int(status["dup"]) < drops:
            raise ValueError("injected-loss accounting")
    if int(status["gen"]) != int(status["sup"]) + int(status["att"]) or int(status["done"]) != int(
        status["att"]
    ):
        raise ValueError("response accounting incomplete")
    samples = [int(x["v"]) for x in relevant if x["role"] == "sender" and x["e"] == "RTT"]
    sample_counts = [x for x in relevant if x["role"] == "sender" and x["e"] == "RTT_COUNT"]
    if not sample_counts or int(sample_counts[-1]["v"]) != len(samples):
        raise ValueError("RTT evidence incomplete")
    samples.sort()
    return dict(
        complete=True,
        validation_scope="integrity-and-completeness; physical origin requires trusted acquisition",
        messages=count,
        delivered=sum(x["e"] == "DELIVERED" for x in terminals),
        first_attempt=sum(x["v"] == "1" and x["e"] == "DELIVERED" for x in terminals),
        rtt=dict(
            count=len(samples),
            min=min(samples) if samples else None,
            max=max(samples) if samples else None,
            average=sum(samples) / len(samples) if samples else None,
            p95=samples[math.ceil(0.95 * len(samples)) - 1] if samples else None,
        ),
    )


class Capture:
    def __init__(self, proof) -> None:
        self.proof = proof
        self.monitors = {}
        self.queue = queue.Queue()
        self.events = []
        self.commands = []
        self.errors = []
        self.monitor_exits = []

    def start(self) -> None:
        for role, target in (("receiver", "receiver"), ("sender", "gateway")):
            self.monitors[role] = rf.start_rf_monitor(
                self.proof, role, rf.PORTS[target], self.queue
            )

    def command(self, role, text) -> None:
        process = self.monitors[role]["process"]
        if process.poll() is not None:
            raise ValueError("monitor disconnected")
        data = (text + "\n").encode("ascii")
        if process.stdin.write(data) != len(data):
            raise ValueError("short command write")
        process.stdin.flush()
        self.commands.append(dict(role=role, text=text, host_ns=time.monotonic_ns()))

    def wait(self, predicate, seconds=30, *, ignore_exited_roles=()) -> None:
        deadline = time.monotonic() + seconds
        ignored = set(ignore_exited_roles)
        while time.monotonic() < deadline:
            for role, monitor in self.monitors.items():
                code = monitor["process"].poll()
                if code is not None:
                    if role not in ignored:
                        raise ValueError(f"{role} monitor exited")
                    if not any(exit["role"] == role for exit in self.monitor_exits):
                        self.monitor_exits.append(dict(role=role, exit_code=code))
            if predicate():
                return
            try:
                role, stream, raw = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if stream == "stdout" and raw:
                event = parse_event(raw.decode("ascii", errors="replace").strip())
                if event:
                    event.update(role=role, host_ns=time.monotonic_ns())
                    self.events.append(event)
        raise ValueError("incomplete evidence: capture deadline")

    def acquire(self, programming, config_hash, seconds=45, expected_session=0) -> None:
        """Drain startup, then recover each missing status once within one deadline."""
        deadline = time.monotonic() + seconds

        def complete(role):
            rows = [e for e in self.events if e["role"] == role]
            starts = [i for i, e in enumerate(rows) if e["e"] == "BOOT"]
            if not starts:
                return False
            block = rows[starts[-1] :]
            for e in block:
                if int(e["s"], 16) != expected_session:
                    raise ValueError("unexpected startup session before acquisition")
                if e["e"] == "IDENTITY" and (
                    e.get("build") != programming[role]["build_id"]
                    or e.get("config") != config_hash
                ):
                    raise ValueError("installed firmware/config mismatch before ARM")
                if e["e"] == "STATUS" and (e.get("ready") != "1" or e.get("overflow") != "0"):
                    raise ValueError("startup radio failure or logger overflow")
                if e["e"] == "STATUS_END" and e.get("v") != "0":
                    raise ValueError("startup logger overflow")
            return {"BOOT", "IDENTITY", "STATUS", "REG", "STATUS_END"} <= {
                e["e"] for e in block
            } and status_complete(block, role, expected_session)

        try:
            self.wait(lambda: all(complete(r) for r in programming), min(12, seconds))
        except ValueError as error:
            if str(error) != "incomplete evidence: capture deadline":
                raise
        for role in programming:
            if complete(role):
                continue
            self.command(role, "STATUS")
            self.wait(lambda: complete(role), max(0, deadline - time.monotonic()))

    def seen(self, role, event):
        return [x for x in self.events if x["role"] == role and x["e"] == event]

    def close(self) -> None:
        for m in self.monitors.values():
            try:
                rf.stop_rf_monitor(m)
            except Exception as error:
                self.errors.append(str(error))
        # Reader threads may finish trailing lines while stop waits for the mailbox to drain.
        while True:
            try:
                role, stream, raw = self.queue.get_nowait()
            except queue.Empty:
                break
            if stream == "stdout" and raw:
                try:
                    event = parse_event(raw.decode("ascii", errors="replace").strip())
                except ValueError as error:
                    self.errors.append(f"{role}: {error}: {raw!r}")
                    continue
                if event:
                    event.update(role=role, host_ns=time.monotonic_ns())
                    self.events.append(event)


def trial(parent, gate, count, manifest, programming, firmware, startup_session=0, run_label=None):
    run_dir = parent / gate if run_label is None else parent / Path(run_label)
    if run_label is not None and (Path(run_label).is_absolute() or ".." in Path(run_label).parts):
        raise ValueError("invalid trial run label")
    proof = rf.ProofRun(run_dir)
    c = Capture(proof)
    provenance = proof.run_dir / "provenance"
    provenance.mkdir()
    for p in parent.iterdir():
        if p.is_file():
            shutil.copy2(p, provenance / p.name)
    session = reserve_session(ROOT / "artifacts/arq")
    bundle = dict(
        acquisition="updi-live",
        synthetic=False,
        gate=gate,
        count=count,
        session=session,
        config_hash=manifest["config_hash"],
        firmware=firmware,
        programming=programming,
    )
    try:
        bundle["phase"] = "acquisition"
        c.start()
        c.acquire(programming, manifest["config_hash"], expected_session=startup_session)
        bundle["phase"] = "arming"
        for r in ("sender", "receiver"):
            c.command(r, f"ARM {session:08X}")
        c.wait(lambda: all(c.seen(r, "ARM") for r in ("sender", "receiver")))
        for r in ("sender", "receiver"):
            if c.seen(r, "ARM")[-1].get("rc") != "0":
                raise ValueError("ARM failed")
        stride, budget = (
            (1, 1)
            if gate == "H03"
            else (manifest["config"]["fault_ack_stride"], manifest["config"]["fault_drop_budget"])
            if gate == "H06"
            else (0, 0)
        )
        c.command("receiver", f"FAULT {stride} {budget}")
        c.wait(lambda: bool(c.seen("receiver", "FAULT")))
        payload = (
            manifest["config"]["negative_payload" if gate == "H02" else "payload"].encode().hex()
        )
        bundle["phase"] = "rf-trial"
        for i in range(count):
            c.command("sender", "SEND " + payload)
            c.wait(
                lambda: (
                    len(
                        [
                            x
                            for x in c.events
                            if x["role"] == "sender"
                            and x["e"]
                            in (
                                "DELIVERED",
                                "REJECTED",
                                "PROTOCOL_ERROR",
                                "TIMEOUT_EXHAUSTED",
                                "RADIO_ERROR",
                            )
                        ]
                    )
                    > i
                ),
                180,
            )
            terminal = [
                x
                for x in c.events
                if x["role"] == "sender"
                and x["e"]
                in ("DELIVERED", "REJECTED", "PROTOCOL_ERROR", "TIMEOUT_EXHAUSTED", "RADIO_ERROR")
            ][-1]
            if terminal["e"] != ("REJECTED" if gate == "H02" else "DELIVERED"):
                raise ValueError("transaction failed: " + terminal["e"])
        for r in ("sender", "receiver"):
            c.command(r, "X")
            c.wait(lambda: bool(c.seen(r, "PARKED")), 10)
            c.command(r, "STATUS")
            c.wait(lambda: status_complete(c.events, r, session), 45)
        bundle.update(events=c.events, commands=c.commands)
    except Exception as failure:
        bundle["failure_reason"] = str(failure)
        bundle["classification"] = (
            "capture-failure" if bundle.get("phase") == "acquisition" else "trial-failure"
        )
        counts = {r: len(c.seen(r, "STATUS")) for r in c.monitors}
        try:
            if bundle.get("phase") != "acquisition":
                for r in c.monitors:
                    c.command(r, "X")
                    c.command(r, "STATUS")
                c.wait(
                    lambda: all(
                        len(c.seen(r, "STATUS")) > n and status_complete(c.events, r, session)
                        for r, n in counts.items()
                    ),
                    45,
                )
        except Exception as error:
            proof.note("final-status-error.log", str(error) + "\n")
        raise
    finally:
        c.close()
        bundle.update(events=c.events, commands=c.commands, capture_errors=c.errors)
        bundle["files"] = {
            str(p.relative_to(proof.run_dir)): sha(p)
            for p in proof.run_dir.rglob("*")
            if p.is_file()
        }
        (proof.run_dir / "bundle.json").write_text(json.dumps(bundle, indent=2) + "\n")
    if c.errors:
        raise ValueError("incomplete capture cleanup: " + str(c.errors))
    report = validate_bundle(bundle, proof.run_dir)
    report["session"] = session
    (proof.run_dir / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(gate, json.dumps(report))
    return report


def campaign(gates=None, *, soak_plan=None, run_dir=None):
    from generate_lora_config import generate

    generate(check=True)
    parent = (
        Path(run_dir)
        if run_dir is not None
        else ROOT / "artifacts/arq" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    if run_dir is not None and not parent.resolve().is_relative_to(
        (ROOT / "artifacts/arq").resolve()
    ):
        raise ValueError("campaign evidence path must remain under artifacts/arq")
    proof = rf.ProofRun(parent)
    manifest = json.loads((ROOT / "generated/arq_manifest.json").read_text())
    config = subprocess.check_output(
        ["pio", "project", "config", "--json-output"], cwd=ROOT, text=True
    )
    if rf.check_port_owners(proof, "arq-preflight"):
        raise ValueError("UPDI ports owned")
    programming = {}
    firmware = {}
    results = []
    soak_state = "CREATED" if soak_plan else None
    progress_path = parent / "soak" / "soak-progress.jsonl"
    if soak_plan:
        if gates is not None:
            raise ValueError("soak plan cannot be combined with protocol gate list")
        if soak_plan["session_interval_s"] < SOAK_INTERVAL_MIN_SECONDS:
            raise ValueError("soak plan interval is below the airtime safety floor")
        (parent / "soak").mkdir()
        soak_plan = dict(
            soak_plan,
            run_id=parent.name,
            started_utc=datetime.now(UTC).isoformat(),
            firmware_profile="sender_arq_radio_only + receiver_arq_radio_only",
        )
        (parent / "soak-plan.json").write_text(json.dumps(soak_plan, indent=2) + "\n")

        def progress(event, **details) -> None:
            row = dict(
                event=event,
                utc=datetime.now(UTC).isoformat(),
                monotonic_ns=time.monotonic_ns(),
                **details,
            )
            with progress_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())

        progress(
            "SOAK_CREATED",
            stage=soak_plan["stage"],
            sessions=soak_plan["sessions"],
            session_interval_s=soak_plan["session_interval_s"],
        )
    else:
        progress = None
    try:
        for role in ("receiver", "sender"):
            environment = role + "_arq_radio_only"
            for suffix in ("hex", "elf"):
                src = ROOT / ".pio/build" / environment / ("firmware." + suffix)
                (parent / (environment + "." + suffix)).write_bytes(src.read_bytes())
            firmware[role] = sha(parent / (environment + ".hex"))
            # Fresh serial/signature/fuses plus independent full-memory comparison.
            if rf.check_port_owners(proof, environment + "-preflight"):
                raise ValueError("UPDI ports owned")
            if rf.program_application(proof, environment, config):
                raise ValueError("programming failed: " + role)
            identity = (ROOT / ".pio/build" / environment / "lora_build_identity.h").read_text()
            build_id = re.search(r'LORA_BUILD_ID "([0-9a-f]{64})"', identity).group(1)
            # Existing exact images still need an independent after snapshot for bundle validation.
            after = parent / f"{environment}-after-page-write-flash.bin"
            if not after.exists():
                boot.read_snapshot(
                    proof,
                    environment + "-after-page-write",
                    "gateway" if role == "sender" else "receiver",
                    current_target=True,
                )
            programming[role] = dict(
                environment=environment, hex_sha256=firmware[role], build_id=build_id, verified=True
            )
        (parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        startup_session = 0
        if soak_plan:
            soak_state = "RUNNING"
            progress("FIRMWARE_VERIFIED", roles=programming)

            def run_one(index):
                nonlocal startup_session
                gate = f"SOAK-{index + 1:06d}"
                started = time.monotonic()
                progress(
                    "SESSION_START",
                    index=index + 1,
                    target=soak_plan["sessions"],
                    gate=gate,
                    startup_session=startup_session,
                )
                try:
                    result = trial(
                        parent, gate, 1, manifest, programming, firmware, startup_session
                    )
                    result = soak_result_metrics(
                        result, parent / gate / "bundle.json", time.monotonic() - started
                    )
                except Exception as error:
                    progress(
                        "SESSION_FAILED",
                        index=index + 1,
                        error_type=type(error).__name__,
                        error=str(error),
                        duration_s=time.monotonic() - started,
                    )
                    raise
                results.append(result)
                startup_session = result["session"]
                progress(
                    "SESSION_COMPLETE",
                    index=index + 1,
                    target=soak_plan["sessions"],
                    gate=gate,
                    session=startup_session,
                    success=result.get("delivered") == 1,
                    duration_s=time.monotonic() - started,
                )
                return result

            run_paced_sessions(soak_plan["sessions"], soak_plan["session_interval_s"], run_one)
            soak_state = "COMPLETE"
        else:
            for gate, count in gates or tuple(
                (f"H{i:02}", n) for i, n in enumerate(manifest["config"]["test_counts"], 1)
            ):
                results.append(
                    trial(parent, gate, count, manifest, programming, firmware, startup_session)
                )
                startup_session = results[-1]["session"]
    except KeyboardInterrupt:
        if soak_plan:
            soak_state = "INTERRUPTED"
            progress("SOAK_INTERRUPTED", completed_sessions=len(results))
        raise
    except Exception as error:
        if soak_plan:
            soak_state = "FAILED"
            progress(
                "SOAK_FAILED",
                completed_sessions=len(results),
                error_type=type(error).__name__,
                error=str(error),
            )
        raise
    finally:
        (parent / "campaign.json").write_text(json.dumps(results, indent=2) + "\n")
        if soak_plan:
            progress("RESTORE_STARTED", soak_state=soak_state)
        try:
            restored = prepare()
            proof.note("restore.json", json.dumps(dict(standby_evidence=str(restored))) + "\n")
            if soak_plan:
                progress("RESTORE_VERIFIED", standby_evidence=str(restored), soak_state=soak_state)
        except Exception as error:
            if soak_plan:
                progress("RESTORE_FAILED", error_type=type(error).__name__, error=str(error))
            raise
    return parent


# Keep the first twenty addresses compatible with archived ARQ snapshots.
ARQ_REGISTER_ADDRESSES = (
    1,
    6,
    7,
    8,
    9,
    0x4D,
    0x1D,
    0x1E,
    0x26,
    0x39,
    0x33,
    0x3B,
    0x12,
    0x13,
    0x10,
    0x1B,
    0x40,
    0x11,
    0x18,
    0x31,
    0x42,
    0x20,
    0x21,
    0x41,
)
HELLO_PAYLOAD = b"HELLO_LORA"


def audit_radio_configuration(event, *, rx):
    values = bytes.fromhex(event["bytes"])
    if len(values) != len(ARQ_REGISTER_ADDRESSES):
        raise ValueError("incomplete ARQ radio snapshot")
    registers = dict(zip(ARQ_REGISTER_ADDRESSES, values))
    # Reviewed 915 MHz, SF7/BW125/CR4:5, +2 dBm PA_BOOST diagnostic profile.
    expected = {
        1: 0x85 if rx else 0x81,
        6: 0xE4,
        7: 0xC0,
        8: 0,
        9: 0xF0,
        0x4D: 0x84,
        0x1D: 0x72,
        0x1E: 0x74,
        0x26: 4,
        0x39: 0x12,
        0x33: 0x27,
        0x3B: 0x1D,
        0x40: 0,
        0x11: 0,
        0x20: 0,
        0x21: 8,
        0x41: 0,
    }
    mismatches = {
        f"{address:02X}": dict(expected=value, observed=registers[address])
        for address, value in expected.items()
        if registers[address] != value
    }
    if registers[0x42] not in (0x11, 0x12, 0x13):
        mismatches["42"] = "unsupported RegVersion"
    # RadioLib BW125 erratum clears AutomaticIFOn on RX entry; reserved bits are ignored.
    if rx and registers[0x31] & 0x87 != 3:
        mismatches["31"] = "RX erratum/SF detection mismatch"
    if mismatches:
        raise ValueError("ARQ radio configuration mismatch: " + json.dumps(mismatches))
    return dict(
        frequency_hz=int.from_bytes(values[1:4], "big") * 32000000 // (1 << 19),
        registers={f"{address:02X}": value for address, value in registers.items()},
    )


def diagnostic_case(test_id=None):
    if test_id not in (None, "T01", "T02", "T03", "T04"):
        raise ValueError("unknown diagnostic test")
    reverse = test_id in ("T03", "T04")
    nack = test_id in ("T02", "T04")
    payload = (
        HELLO_PAYLOAD
        if test_id is None
        else (b"REJECT_LORA" if nack else (b"HELLO_LORA_TR" if reverse else b"HELLO_LORA_GW"))
    )
    return dict(
        reverse=reverse,
        nack=nack,
        payload=payload,
        sender_role="receiver" if reverse else "sender",
        receiver_role="sender" if reverse else "receiver",
    )


def hello_airtime_budget(config, payload=HELLO_PAYLOAD):
    data = lora_time_on_air_us(12 + len(payload), config)
    ack = lora_time_on_air_us(12, config)
    turnaround = config["response_guard_ms"] * 1000
    if data >= config["tx_ms"] * 1000 or ack + turnaround >= config["ack_min_ms"] * 1000:
        raise ValueError("HELLO_LORA airtime/turnaround exceeds firmware deadline")
    return dict(
        payload_hex=payload.hex(),
        max_attempts=1,
        data_toa_us=data,
        ack_toa_us=ack,
        turnaround_guard_us=turnaround,
        ack_deadline_min_ms=config["ack_min_ms"],
    )


def validate_hello_exchange(events, session, *, test_id=None):
    case = diagnostic_case(test_id)
    tx, rx = case["sender_role"], case["receiver_role"]
    src, dst = (2, 1) if case["reverse"] else (1, 2)
    control_type, control_reason = (3, 2) if case["nack"] else (2, 0)
    rows = [e for e in events if int(e.get("s", "0"), 16) == session]
    frames = []
    for event in rows:
        if event.get("e") not in ("TX", "RX"):
            continue
        frame = wire_frame(event["bytes"])
        if frame["session"] != session or frame["sequence"] != 0:
            raise ValueError("HELLO_LORA stale session/sequence")
        data = frame["type"] == 1
        if (frame["src"], frame["dst"], frame["payload"], frame["type"], frame["reason"]) != (
            (src, dst, case["payload"], 1, 0)
            if data
            else (dst, src, b"", control_type, control_reason)
        ):
            raise ValueError("HELLO_LORA DATA/ACK mismatch")
        frames.append((event, frame))

    def frame_rows(role, name, kind):
        return [
            e
            for e, f in frames
            if e.get("role") == role and e.get("e") == name and f["type"] == kind
        ]

    data = frame_rows(tx, "TX", 1)
    if len(data) > 1:
        raise ValueError("more than one physical DATA attempt")

    def checkpoint(role, name, *, value=None, sequence=0, rc="0"):
        matches = [e for e in rows if e.get("role") == role and e.get("e") == name]
        if not matches:
            return None
        return (
            len(matches) == 1
            and matches[0].get("rc") == rc
            and matches[0].get("q") == str(sequence)
            and (value is None or matches[0].get("v") == value)
        )

    decision = "DATA_REJECT" if case["nack"] else "ACCEPT"
    terminal = "REJECTED" if case["nack"] else "DELIVERED"
    values = [
        True if data else None,
        checkpoint(tx, "TX_DONE", value="8"),
        True if frame_rows(rx, "RX", 1) else None,
        checkpoint(
            rx, decision, value="0" if case["nack"] else "1", rc="2" if case["nack"] else "0"
        ),
        True if frame_rows(rx, "TX", control_type) else None,
        checkpoint(rx, "TX_DONE", value="8"),
        True if frame_rows(tx, "RX", control_type) else None,
        checkpoint(tx, terminal, value="1"),
    ]
    keys = (
        (
            "data_tx",
            "data_tx_done",
            "data_rx",
            "data_rejected" if case["nack"] else "data_accepted",
            "response_tx",
            "response_tx_done",
            "response_rx",
            "response_accepted",
        )
        if test_id
        else (
            "gateway_data_tx",
            "gateway_data_tx_done",
            "tracker_data_rx",
            "tracker_data_accepted",
            "tracker_ack_tx",
            "tracker_ack_tx_done",
            "gateway_ack_rx",
            "gateway_ack_accepted",
        )
    )
    result = dict(zip(keys, values))
    # Serial streams may interleave; each board's own causal order must hold.
    chains = {
        tx: ["TX", "TX_DONE", "RX", terminal],
        rx: ["RX", decision, "TX", "TX_DONE"],
    }
    result["local_order_valid"] = all(
        [e.get("e") for e in rows if e.get("role") == role and e.get("e") in names] == names
        for role, names in chains.items()
    )
    result["complete"] = all(value is True for value in result.values())
    return result


def radio_only_bringup(args, *, exchange=False):
    """Program Tracker first, inspect both radios, and park the installed diagnostics."""
    from types import SimpleNamespace

    from arq_config import load_arq
    from device_detection.firmware_identity import normalize_ihex_region
    from generate_lora_config import digest, generate

    errors = hardware_gate_errors(args, exchange)
    if errors:
        raise ValueError("radio-only preflight incomplete: " + "; ".join(errors))
    generate(check=True)
    manifest = json.loads((ROOT / "generated/arq_manifest.json").read_text())
    test_id = getattr(args, "diagnostic_test", None)
    case = diagnostic_case(test_id)
    reverse = case["reverse"] or getattr(args, "reverse_direction", False)
    budget = hello_airtime_budget(load_arq(), case["payload"])
    run_dir = (
        ROOT / "artifacts/arq" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ-radio-only-bringup")
    )
    proof = rf.ProofRun(run_dir)
    capture = Capture(proof)
    report = dict(
        status="UNKNOWN",
        exchange_requested=exchange,
        airtime=budget,
        programming={},
        rf_release="operator-confirmed" if exchange else "PENDING",
        radio={},
        cleanup={},
        test_id=test_id,
        direction="tracker-to-gateway" if reverse else "gateway-to-tracker",
    )
    session = 0

    def read_radio(role, rx, status_session):
        start = len(capture.events)
        capture.command(role, "STATUS")
        capture.wait(lambda: status_complete(capture.events[start:], role, status_session), 45)
        rows = [e for e in capture.events[start:] if e.get("role") == role]
        statuses = [e for e in rows if e.get("e") == "STATUS"]
        registers = [e for e in rows if e.get("e") == "REG"]
        if (
            not statuses
            or not registers
            or statuses[-1].get("ready") != "1"
            or statuses[-1].get("overflow") != "0"
            or any(int(e["s"], 16) != status_session for e in rows)
        ):
            raise ValueError("fresh radio status/readiness not verified: " + role)
        return audit_radio_configuration(registers[-1], rx=rx)

    try:
        config = subprocess.check_output(
            ["pio", "project", "config", "--json-output"], cwd=ROOT, text=True
        )
        if not rf.upload_ports_match(config) or not rf.upload_config_preserves_flash(config):
            raise ValueError("upload mapping/preservation configuration mismatch")
        candidates = {}
        for role in ("receiver", "sender"):
            environment = role + "_arq_radio_only" + ("_reverse" if reverse else "")
            metadata = (
                reader_free_h01_firmware(ROOT, role, reverse=True)
                if reverse
                else reader_free_h01_firmware(ROOT, role)
            )
            if metadata["build_id"] != digest(dict(environment=environment, arq=manifest)):
                raise ValueError("stale candidate build identity: " + role)
            image = ROOT / ".pio/build" / environment / "firmware.hex"
            data = image.read_bytes()
            region = rf.parse_ihex_range(data)
            expected = normalize_ihex_region(
                data.decode("ascii"), region["start"], region["end_exclusive"]
            )
            if metadata["build_id"].encode() not in expected:
                raise ValueError("candidate image/build identity mismatch: " + role)
            (run_dir / (environment + ".hex")).write_bytes(data)
            if sha(run_dir / (environment + ".hex")) != metadata["sha256"]:
                raise ValueError("candidate image hash changed: " + role)
            candidates[role] = metadata
        for role in ("receiver", "sender"):
            environment = candidates[role]["environment"]
            if rf.check_port_owners(proof, environment + "-preflight"):
                raise ValueError("UPDI ports owned")
            identity_args = SimpleNamespace(physical_mapping_verified=True, power_verified=True)
            if rf.identify_targets(proof, identity_args, config):
                raise ValueError("current identity/fuse preflight failed")
            metadata = candidates[role]
            if rf.program_application(proof, environment, config):
                raise ValueError("programming/readback failed: " + role)
            report["programming"][role] = metadata
        capture.start()
        capture.acquire(report["programming"], manifest["config_hash"])
        for role in ("receiver", "sender"):
            report["radio"][role] = audit_radio_configuration(
                capture.seen(role, "REG")[-1], rx=False
            )
        session = reserve_session(ROOT / "artifacts/arq")
        report["session"] = session
        for role in ("sender", "receiver") if reverse else ("receiver", "sender"):
            capture.command(role, f"ARM {session:08X}")
            capture.wait(
                lambda: bool(
                    [
                        e
                        for e in capture.seen(role, "ARM")
                        if int(e["s"], 16) == session and e.get("rc") == "0"
                    ]
                ),
                15,
            )
            report["radio"][role] = read_radio(role, True, session)
        if exchange:
            capture.command(case["sender_role"], "SEND " + case["payload"].hex().upper())
            capture.wait(
                lambda: bool(
                    [
                        e
                        for e in capture.events
                        if e.get("role") == case["sender_role"]
                        and e.get("e")
                        in (
                            "DELIVERED",
                            "REJECTED",
                            "PROTOCOL_ERROR",
                            "TIMEOUT_EXHAUSTED",
                            "RADIO_ERROR",
                        )
                    ]
                ),
                30,
            )
            for role in ("receiver", "sender"):
                report["radio"][role] = read_radio(role, True, session)
            report["exchange"] = validate_hello_exchange(capture.events, session, test_id=test_id)
            if report["exchange"]["complete"] is not True:
                raise ValueError("HELLO_LORA checkpoints incomplete")
        elif any(e.get("e") in ("TX", "TX_DONE", "REQUEST") for e in capture.events):
            raise ValueError("unexpected RF activity in non-transmitting bring-up")
        report["status"] = "PASS"
    except Exception as error:
        report.update(status="UNKNOWN", failure=f"{type(error).__name__}: {error}")
        raise
    finally:
        # Park through the existing X command; never reflash normal images during cleanup.
        for role in capture.monitors:
            try:
                start = len(capture.events)
                capture.command(role, "X")
                # Drain STOP before the 14-line STATUS block to fit the 16-slot logger.
                capture.wait(
                    lambda: any(
                        e.get("role") == role and e.get("e") == "STOP"
                        for e in capture.events[start:]
                    ),
                    15,
                )
                stopped = next(
                    e
                    for e in capture.events[start:]
                    if e.get("role") == role and e.get("e") == "STOP"
                )
                read_radio(role, False, int(stopped["s"], 16))
                report["cleanup"][role] = "PARKED"
            except Exception as error:
                report["cleanup"][role] = f"UNKNOWN: {error}"
                report["status"] = "UNKNOWN"
        capture.close()
        if capture.errors:
            report["status"] = "UNKNOWN"
        if not exchange and any(e.get("e") in ("TX", "TX_DONE", "REQUEST") for e in capture.events):
            report.update(
                status="UNKNOWN", failure="unexpected RF activity in non-transmitting bring-up"
            )
        if exchange and "exchange" not in report:
            try:
                report["exchange"] = validate_hello_exchange(
                    capture.events, session, test_id=test_id
                )
            except ValueError as error:
                report["exchange"] = dict(complete=False, validation_error=str(error))
        report.update(
            events=capture.events,
            commands=capture.commands,
            capture_errors=capture.errors,
            guard_events=[e for e in capture.events if e.get("e") == "SD_PRESENT_BLOCKED"],
        )
        proof.note("bringup.json", json.dumps(report, indent=2) + "\n")
    if report["status"] != "PASS":
        raise ValueError("diagnostic cleanup incomplete: " + str(run_dir))
    return run_dir


def prepare():
    """Install unarmed normal firmware and verify standby without ARM or SEND."""
    from generate_lora_config import generate

    generate(check=True)
    proof = rf.ProofRun(
        ROOT / "artifacts/arq" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-standby")
    )
    config = subprocess.check_output(
        ["pio", "project", "config", "--json-output"], cwd=ROOT, text=True
    )
    if rf.check_port_owners(proof, "standby-preflight"):
        raise ValueError("UPDI ports owned")
    programming = {}
    for role in ("receiver", "sender"):
        env = role + "_arq"
        image = ROOT / ".pio/build" / env / "firmware.hex"
        (proof.run_dir / (env + ".hex")).write_bytes(image.read_bytes())
        if rf.check_port_owners(proof, env + "-preflight"):
            raise ValueError("UPDI ports owned")
        if rf.program_application(proof, env, config):
            raise ValueError("standby programming/readback failed: " + role)
        identity = (ROOT / ".pio/build" / env / "lora_build_identity.h").read_text()
        programming[role] = dict(
            build_id=re.search(r'LORA_BUILD_ID "([0-9a-f]{64})"', identity).group(1)
        )
    capture = Capture(proof)
    try:
        capture.start()
        capture.acquire(
            programming,
            json.loads((ROOT / "generated/arq_manifest.json").read_text())["config_hash"],
        )
        counts = {r: len(capture.seen(r, "STATUS_END")) for r in ("sender", "receiver")}
        for r in ("sender", "receiver"):
            capture.command(r, "X")
            capture.command(r, "STATUS")
            capture.wait(
                lambda: (
                    len(capture.seen(r, "STATUS_END")) > counts[r]
                    and status_complete(capture.events, r, 0)
                ),
                45,
            )
        for r in ("sender", "receiver"):
            mode = bytes.fromhex(capture.seen(r, "REG")[-1]["bytes"])[0]
            if (
                mode & 7 != 1
                or capture.seen(r, "STATUS")[-1]["ready"] != "1"
                or capture.seen(r, "STATUS_END")[-1]["v"] != "0"
            ):
                raise ValueError("radio did not verify standby: " + r)
        if capture.seen("sender", "TX") or capture.seen("receiver", "TX"):
            raise ValueError("unexpected RF transmission")
    finally:
        capture.close()
        (proof.run_dir / "status.json").write_text(json.dumps(capture.events, indent=2) + "\n")
    if capture.errors:
        proof.note("capture-errors.json", json.dumps(capture.errors) + "\n")
        raise ValueError("standby capture cleanup failed")
    proof.note(
        "standby-verified.json",
        json.dumps(
            dict(
                standby=True,
                rf_transmissions=0,
                firmware={r: sha(proof.run_dir / (r + "_arq.hex")) for r in ("sender", "receiver")},
            ),
            indent=2,
        )
        + "\n",
    )
    return proof.run_dir


def validate_reverse(events):
    if any(e.get("overflow", "0") != "0" for e in events):
        raise ValueError("raw logger overflow")
    starts = [e for e in events if e["role"] == "receiver" and e["e"] == "RAW_TX"]
    done = [
        e
        for e in events
        if e["role"] == "receiver"
        and e["e"] == "RAW_TX_DONE"
        and e.get("rc") == "0"
        and int(e["flags"]) & 8
    ]
    received = [e for e in events if e["role"] == "sender" and e["e"] == "RAW_RX"]
    if (
        len(starts) != 1
        or starts[0].get("rc") != "0"
        or starts[0].get("flags") != "11"
        or len(done) != 1
    ):
        raise ValueError("missing single successful raw transmission")
    if len(received) != 1:
        raise ValueError("missing single actual raw reception")
    packet = received[0]
    flags = int(packet["flags"])
    if (
        packet.get("rc") != "0"
        or flags & 0x60 != 0x40
        or packet.get("len") != "11"
        or packet.get("match") != "1"
        or packet.get("bytes") != "48656C6C6F20576F726C64"
    ):
        raise ValueError("raw RxDone/CRC/payload mismatch")
    return dict(
        complete=True,
        payload=packet["bytes"],
        rssi=int(packet["rssi"]),
        snr=int(packet["snr"]),
        validation_scope="captured physical UPDI; radio metrics in hundredths",
    )


def audit_raw_configuration(event) -> None:
    values = bytes.fromhex(event["bytes"])
    # Address order matches reverse_raw configuration(); compare PHY, not mode/DIO state.
    expected = bytes.fromhex("E4C000F084727404000812271D")
    if len(values) != 23 or values[0] not in (0x11, 0x12, 0x13) or values[2:15] != expected:
        raise ValueError("reverse radio configuration mismatch")


def reverse_exchange(c):
    # Host deadline starts before RX: delayed mailbox delivery cannot extend the RF window.
    armed = time.monotonic()
    c.command("sender", "RX")
    c.wait(lambda: bool(c.seen("sender", "RAW_RX_READY")), 5)
    ready = c.seen("sender", "RAW_RX_READY")[-1]
    if ready.get("rc") != "0" or int(ready.get("mode", "0")) & 0xCF != 0x85:
        raise ValueError("reverse RX continuous not verified")
    if time.monotonic() - armed >= 10 or c.seen("sender", "RAW_RX_TIMEOUT"):
        raise ValueError("reverse receive window expired before SEND")
    configs = c.seen("sender", "RAW_RX_ACTIVE")
    if not configs:
        raise ValueError("missing active RX configuration")
    audit_raw_configuration(configs[-1])
    c.command("receiver", "SEND 48656C6C6F20576F726C64")
    # Allow the bounded device timeout plus mailbox drain; preserve its actual event.
    c.wait(
        lambda: bool(
            c.seen("sender", "RAW_RX")
            or c.seen("sender", "RAW_RX_TIMEOUT")
            or c.seen("receiver", "RAW_TX_TIMEOUT")
        ),
        20,
        ignore_exited_roles=("receiver",),
    )
    c.wait(
        lambda: bool(c.seen("receiver", "RAW_TX_DONE") or c.seen("receiver", "RAW_TX_TIMEOUT")),
        5,
        ignore_exited_roles=("receiver",),
    )
    return validate_reverse(c.events)


def send_command_without_reader(proof, port, command, firmware):
    sys.path.insert(0, str(ROOT / "third_party/upditerm"))
    import upditerm

    payload = (command + "\n").encode("ascii")
    accepted = bytearray()
    record = dict(
        port=port,
        firmware=firmware,
        command=command,
        request_hex=payload.hex(),
        monitor_reader_running=False,
        normal_startup_breaks=2,
        cpu_reset_requested=False,
        monotonic_start_ns=time.monotonic_ns(),
        utc_start=datetime.now(UTC).isoformat(),
    )
    session = None
    try:
        session = upditerm.SerialUPDI(port, 38400)
        record["baseline_reset_state"] = read_reset_state(session, upditerm)
        write_virtual_uart(session, payload, accepted=accepted)
        record["result"] = "sent"
    except Exception as error:
        record.update(
            result="failed", exception_type=type(error).__name__, exception_message=str(error)
        )
        record["accepted_hex"] = accepted.hex()
        record["accepted_length"] = len(accepted)
        close_updi_without_recovery(session)
        record["monotonic_end_ns"] = time.monotonic_ns()
        record["utc_end"] = datetime.now(UTC).isoformat()
        proof.note("tracker-direct-command.json", json.dumps(record, indent=2) + "\n")
        raise
    record["accepted_hex"] = accepted.hex()
    record["accepted_length"] = len(accepted)
    record["monotonic_end_ns"] = time.monotonic_ns()
    record["utc_end"] = datetime.now(UTC).isoformat()
    proof.note("tracker-direct-command.json", json.dumps(record, indent=2) + "\n")
    return session, upditerm, record


def close_updi_without_recovery(session) -> None:
    if session:
        link = getattr(session, "updi", session)
        if not link or not link.ser:
            return
        serial_device = link.ser.dev
        link.ser = None
        if hasattr(session, "updi"):
            session.updi = None
        serial_device.close()


def resync_reset_state_once(session, protocol, port):
    """Reconnect once without CPU reset, then read only startup reset evidence."""
    close_updi_without_recovery(session)
    fresh = protocol.UPDI(port, 38400)
    fresh.key(protocol.KEY_OCD)
    return fresh, read_reset_state(fresh, protocol)


def drain_updi_messages(session, protocol, *, max_bytes=4096, timeout=5.0, quiet_period=0.1):
    link = getattr(session, "updi", session)
    start = time.monotonic()
    last_message = start
    output = bytearray()
    statuses = []
    while len(output) < max_bytes and time.monotonic() - start < timeout:
        status = link.ldcs(protocol.ASI_OCD_STATUS)
        statuses.append(status)
        if status & protocol.OCDMV:
            output.append(link.ldcs(protocol.ASI_OCD_MESSAGE))
            last_message = time.monotonic()
        elif time.monotonic() - last_message >= quiet_period and (
            not output or output.endswith((b"\n", b"\r"))
        ):
            break
        else:
            time.sleep(0.001)
    return bytes(output), statuses


def capture_tracker_diagnostics(c, proof, session, protocol, record, prefix):
    link = getattr(session, "updi", session)
    flags = link.lds8(protocol.UART_FLAGS)
    record[f"{prefix}_uart_flags"] = flags
    record[f"{prefix}_uart_rx_pending"] = bool(flags & protocol.FLAG_RX)
    output, statuses = drain_updi_messages(session, protocol)
    (proof.run_dir / f"tracker-updi-output-{prefix}.bin").write_bytes(output)
    record[f"{prefix}_ocd_status_reads"] = statuses
    record[f"{prefix}_output_hex"] = output.hex()
    observed_ns = time.monotonic_ns()
    for line in output.decode("ascii", errors="replace").splitlines():
        event = parse_event(line)
        if event:
            event.update(
                role="receiver",
                buffered_after_window=True,
                read_phase=prefix,
                host_read_ns=observed_ns,
            )
            c.events.append(event)
    return output


def reverse_exchange_without_tracker_reader(c, proof, tracker_firmware):
    armed = time.monotonic()
    c.command("sender", "RX")
    c.wait(lambda: bool(c.seen("sender", "RAW_RX_READY")), 5)
    ready = c.seen("sender", "RAW_RX_READY")[-1]
    if ready.get("rc") != "0" or int(ready.get("mode", "0")) & 0xCF != 0x85:
        raise ValueError("reverse RX continuous not verified")
    configs = c.seen("sender", "RAW_RX_ACTIVE")
    if not configs:
        raise ValueError("missing active RX configuration")
    audit_raw_configuration(configs[-1])
    if time.monotonic() - armed >= 10 or c.seen("sender", "RAW_RX_TIMEOUT"):
        raise ValueError("reverse receive window expired before SEND")
    session, protocol, command = send_command_without_reader(
        proof, rf.PORTS["receiver"], "SEND 48656C6C6F20576F726C64", tracker_firmware
    )
    output = b""
    try:
        c.wait(lambda: bool(c.seen("sender", "RAW_RX") or c.seen("sender", "RAW_RX_TIMEOUT")), 20)
        output = capture_tracker_diagnostics(c, proof, session, protocol, command, "post_window")
    except Exception as first_error:
        command["post_window_error"] = f"{type(first_error).__name__}: {first_error}"
        proof.note("tracker-direct-command.json", json.dumps(command, indent=2) + "\n")
        close_updi_without_recovery(session)
        session = None
        try:
            command["resync_break_count"] = 2
            command["resync_cpu_reset_requested"] = False
            session = protocol.UPDI(rf.PORTS["receiver"], 38400)
            session.key(protocol.KEY_OCD)
            command["resync_reset_state"] = read_reset_state(session, protocol)
            output = capture_tracker_diagnostics(c, proof, session, protocol, command, "resync")
        except Exception as recovery_error:
            command["resync_error"] = f"{type(recovery_error).__name__}: {recovery_error}"
    finally:
        command["monotonic_end_ns"] = time.monotonic_ns()
        command["utc_end"] = datetime.now(UTC).isoformat()
        proof.note("tracker-direct-command.json", json.dumps(command, indent=2) + "\n")
        close_updi_without_recovery(session)
    tracker_events = [event for event in c.events if event.get("role") == "receiver"]
    tx_done = [event for event in tracker_events if event["e"] == "RAW_TX_DONE"]
    tx_started = [event for event in tracker_events if event["e"] == "RAW_TX"]
    packets = c.seen("sender", "RAW_RX")
    if packets:
        packet = packets[-1]
        valid = (
            packet.get("rc") == "0"
            and int(packet.get("flags", "0")) & 0x60 == 0x40
            and packet.get("len") == "11"
            and packet.get("match") == "1"
            and packet.get("bytes") == "48656C6C6F20576F726C64"
        )
        return dict(
            complete=valid,
            result="RX_OBSERVED" if valid else "RX_INVALID",
            packet=packet,
            tracker_tx_started=bool(tx_started),
            tracker_tx_done=tx_done[-1] if tx_done else None,
            tracker_events=tracker_events,
            validation_scope="Gateway physically captured the payload; Tracker output was read only after the RX window",
        )
    timeout = c.seen("sender", "RAW_RX_TIMEOUT")[-1]
    return dict(
        complete=False,
        result="RX_TIMEOUT",
        receiver=timeout,
        tracker_tx_started=bool(tx_started),
        tracker_tx_done=tx_done[-1] if tx_done else None,
        tracker_events=tracker_events,
        validation_scope="Gateway timed out; Tracker buffered events were read after the RX window",
    )


def park_reverse(c):
    errors = []
    for role in c.monitors:
        try:
            c.command(role, "X")
        except Exception as error:
            errors.append(role + ": " + str(error))
    try:
        if c.monitors:
            c.wait(lambda: all(c.seen(r, "RAW_STANDBY") for r in c.monitors), 5)
    except Exception as error:
        errors.append(str(error))
    return errors


def reverse_raw(*, tracker_reader=True):
    """One explicitly commanded Tracker TX, Gateway RX; always restore normal images."""
    from generate_lora_config import generate

    generate(check=True)
    proof = rf.ProofRun(
        ROOT / "artifacts/arq" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-reverse-raw")
    )
    config = subprocess.check_output(
        ["pio", "project", "config", "--json-output"], cwd=ROOT, text=True
    )
    c = Capture(proof)
    bundle = dict(
        acquisition="updi-live",
        synthetic=False,
        phase="programming",
        tracker_monitor="reader-and-writer" if tracker_reader else "UPDI-writer-only",
        firmware={},
    )
    try:
        for role in ("sender", "receiver"):
            env = role + "_reverse_raw"
            for suffix in ("hex", "elf"):
                shutil.copy2(
                    ROOT / ".pio/build" / env / ("firmware." + suffix),
                    proof.run_dir / (env + "." + suffix),
                )
            identity = (ROOT / ".pio/build" / env / "lora_build_identity.h").read_text()
            bundle["firmware"][role] = dict(
                sha256=sha(proof.run_dir / (env + ".hex")),
                build_id=re.search(r'LORA_BUILD_ID "([0-9a-f]{64})"', identity).group(1),
            )
            if rf.check_port_owners(proof, env + "-preflight"):
                raise ValueError("UPDI ports owned")
            if rf.program_application(proof, env, config):
                raise ValueError("reverse programming failed: " + role)
        bundle["phase"] = "acquisition"
        if tracker_reader:
            c.start()
        else:
            c.monitors["sender"] = rf.start_rf_monitor(
                proof, "sender", rf.PORTS["gateway"], c.queue
            )

        def status(role) -> bool:
            ids = c.seen(role, "IDENTITY")
            rows = c.seen(role, "RAW_STATUS")
            configs = c.seen(role, "RAW_CONFIG")
            if not ids or not rows or not configs:
                return False
            if (
                ids[-1]["build"] != bundle["firmware"][role]["build_id"]
                or ids[-1]["config"]
                != json.loads((ROOT / "generated/arq_manifest.json").read_text())["config_hash"]
            ):
                raise ValueError("reverse firmware/config identity mismatch")
            if rows[-1].get("rc") != "0" or rows[-1].get("overflow") != "0":
                raise ValueError("reverse radio not ready")
            audit_raw_configuration(configs[-1])
            return True

        deadline = time.monotonic() + 45
        monitor_roles = ("sender", "receiver") if tracker_reader else ("sender",)
        try:
            c.wait(lambda: all(status(r) for r in monitor_roles), 12)
        except ValueError as error:
            if str(error) != "incomplete evidence: capture deadline":
                raise
        for role in monitor_roles:
            if not status(role):
                c.command(role, "STATUS")
                c.wait(lambda: status(role), max(0, deadline - time.monotonic()))
        bundle["phase"] = "rf-trial"
        if tracker_reader:
            bundle["result"] = reverse_exchange(c)
        else:
            bundle["result"] = reverse_exchange_without_tracker_reader(
                c, proof, bundle["firmware"]["receiver"]
            )
            if not bundle["result"]["complete"]:
                raise ValueError(
                    "Gateway did not receive a valid Tracker packet: " + bundle["result"]["result"]
                )
    except Exception as error:
        bundle["failure_reason"] = str(error)
        raise
    finally:
        cleanup_errors = park_reverse(c)
        if cleanup_errors:
            bundle["cleanup_error"] = "; ".join(cleanup_errors)
        c.close()
        bundle.update(events=c.events, commands=c.commands, monitor_exits=c.monitor_exits)
        bundle["capture_errors"] = c.errors
        bundle["files"] = {
            str(p.relative_to(proof.run_dir)): sha(p)
            for p in proof.run_dir.rglob("*")
            if p.is_file()
        }
        (proof.run_dir / "bundle.json").write_text(json.dumps(bundle, indent=2) + "\n")
        # Monitors release both ports before normal-image restoration and verification.
        restored = prepare()
        proof.note("restore.json", json.dumps(dict(standby_evidence=str(restored))) + "\n")
    if c.errors:
        raise ValueError("incomplete raw capture tail: " + str(c.errors))
    print(json.dumps(bundle["result"]))
    return proof.run_dir


def reader_free_h01(*, rx_idle_seconds=None):
    """Run one reader-free H01 exchange or a bounded Tracker RX-only control."""
    if rx_idle_seconds is not None and (
        type(rx_idle_seconds) is not int or not 1 <= rx_idle_seconds <= 120
    ):
        raise ValueError("RX idle control must be between 1 and 120 seconds")
    from generate_lora_config import generate

    generate(check=True)
    experiment = "rx-idle-control" if rx_idle_seconds is not None else "h01-reader-free"
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-" + experiment)
    run_dir = ROOT / "artifacts/arq" / run_id
    suffix = 0
    while run_dir.exists():
        suffix += 1
        run_dir = ROOT / "artifacts/arq" / f"{run_id}-{suffix}"
    proof = rf.ProofRun(run_dir)
    manifest = json.loads((ROOT / "generated/arq_manifest.json").read_text())
    config = subprocess.check_output(
        ["pio", "project", "config", "--json-output"], cwd=ROOT, text=True
    )
    c = Capture(proof)
    tracker_session = None
    protocol = None
    tracker_record = {}
    bundle = dict(
        acquisition="updi-live",
        synthetic=False,
        experiment="TRACKER_RX_IDLE" if rx_idle_seconds is not None else "H01",
        direction="Gateway DATA TX -> Tracker RX/ACK TX -> Gateway RX",
        tracker_output_reader=False,
        config_hash=manifest["config_hash"],
        firmware={},
        tracker_commands=[],
        tracker_output={},
        tracker_reset_before=None,
        tracker_reset_after=None,
        rf_transmissions=0,
    )

    def tracker_command(text, name):
        payload = (text + "\n").encode("ascii")
        accepted = bytearray()
        started = time.monotonic_ns()
        write_virtual_uart(tracker_session, payload, accepted=accepted)
        record = dict(
            command=text,
            request_hex=payload.hex(),
            accepted_hex=accepted.hex(),
            accepted_length=len(accepted),
            monotonic_start_ns=started,
            monotonic_end_ns=time.monotonic_ns(),
            result="mailbox_bytes_accepted",
        )
        bundle["tracker_commands"].append(record)
        proof.note(f"tracker-command-{name}.json", json.dumps(record, indent=2) + "\n")
        return record

    def drain_tracker(name):
        link = getattr(tracker_session, "updi", tracker_session)
        start = time.monotonic_ns()
        flags = link.lds8(protocol.UART_FLAGS)
        output, statuses = drain_updi_messages(
            tracker_session, protocol, timeout=12.0, quiet_period=0.25
        )
        path = run_dir / f"tracker-output-{name}.bin"
        path.write_bytes(output)
        events = []
        parse_errors = []
        for raw in output.splitlines():
            try:
                event = parse_event(raw.decode("ascii", errors="replace"))
            except ValueError as error:
                parse_errors.append(dict(raw_hex=raw.hex(), error=str(error)))
                continue
            if event:
                event.update(
                    role="receiver",
                    read_phase=name,
                    tracker_output_reader=False,
                    host_ns=time.monotonic_ns(),
                )
                c.events.append(event)
                events.append(event)
        result = dict(
            output_file=str(path.relative_to(ROOT)),
            output_hex=output.hex(),
            output_length=len(output),
            uart_flags=flags,
            uart_rx_pending=bool(flags & protocol.FLAG_RX),
            ocd_status_reads=statuses,
            parse_errors=parse_errors,
            monotonic_start_ns=start,
            monotonic_end_ns=time.monotonic_ns(),
        )
        bundle["tracker_output"][name] = result
        proof.note(f"tracker-output-{name}.json", json.dumps(result, indent=2) + "\n")
        return events

    try:
        if rf.check_port_owners(proof, "h01-reader-free-preflight"):
            raise ValueError("UPDI ports owned")
        programming = {}
        firmware = {}
        roles = ("receiver",) if rx_idle_seconds is not None else ("receiver", "sender")
        for role in roles:
            environment = role + "_arq_radio_only"
            for suffix in ("hex", "elf"):
                source = ROOT / ".pio/build" / environment / ("firmware." + suffix)
                destination = run_dir / (environment + "." + suffix)
                destination.write_bytes(source.read_bytes())
            metadata = reader_free_h01_firmware(ROOT, role)
            firmware_sha = sha(run_dir / (environment + ".hex"))
            if firmware_sha != metadata["sha256"]:
                raise ValueError("copied firmware hash differs: " + role)
            if rf.check_port_owners(proof, environment + "-preflight"):
                raise ValueError("UPDI port owned: " + role)
            if rf.program_application(proof, environment, config):
                raise ValueError("programming/readback failed: " + role)
            firmware[role] = metadata
            programming[role] = dict(
                environment=environment,
                hex_sha256=firmware_sha,
                build_id=metadata["build_id"],
                verified=True,
            )
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        bundle.update(
            firmware=firmware,
            programming=programming,
            source_commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
        )

        if rx_idle_seconds is None:
            c.monitors["sender"] = rf.start_rf_monitor(
                proof, "sender", rf.PORTS["gateway"], c.queue
            )

            def gateway_status():
                return status_complete(c.events, "sender", 0)

            try:
                c.wait(gateway_status, 12)
            except ValueError as error:
                if str(error) != "incomplete evidence: capture deadline":
                    raise
            if not gateway_status():
                c.command("sender", "STATUS")
                c.wait(gateway_status, 45)
            gateway_identity = c.seen("sender", "IDENTITY")
            gateway_ready = c.seen("sender", "STATUS")
            if (
                not gateway_identity
                or gateway_identity[-1].get("build") != firmware["sender"]["build_id"]
                or gateway_identity[-1].get("config") != manifest["config_hash"]
                or not gateway_ready
                or gateway_ready[-1].get("ready") != "1"
                or gateway_ready[-1].get("overflow") != "0"
            ):
                raise ValueError("Gateway identity/readiness not verified")

        tracker_session, protocol = open_reader_free_h01_session(rf.PORTS["receiver"])
        tracker_record = dict(
            port=rf.PORTS["receiver"],
            firmware_sha256=firmware["receiver"]["sha256"],
            application_command_sent=False,
            normal_startup_breaks=2,
            cpu_reset_requested=False,
            baseline_reset_state=read_reset_state(tracker_session, protocol),
            monotonic_start_ns=time.monotonic_ns(),
            utc_start=datetime.now(UTC).isoformat(),
        )
        proof.note("tracker-updi-session.json", json.dumps(tracker_record, indent=2) + "\n")
        bundle["tracker_reset_before"] = tracker_record.get("baseline_reset_state")
        drain_tracker("preflight-status")
        tracker_identity = c.seen("receiver", "IDENTITY")
        tracker_status = c.seen("receiver", "STATUS")
        if (
            not tracker_identity
            or tracker_identity[-1].get("build") != firmware["receiver"]["build_id"]
            or tracker_identity[-1].get("config") != manifest["config_hash"]
            or not tracker_status
            or tracker_status[-1].get("ready") != "1"
            or tracker_status[-1].get("overflow") != "0"
            or not status_complete(c.events, "receiver", 0)
        ):
            raise ValueError("Tracker reader-free STATUS/identity not verified")

        session_id = reserve_session(ROOT / "artifacts/arq")
        bundle["session"] = session_id
        tracker_command(f"ARM {session_id:08X}", "arm")
        arm_events = drain_tracker("arm")
        if not any(
            e.get("e") == "ARM" and e.get("rc") == "0" and int(e["s"], 16) == session_id
            for e in arm_events
        ):
            raise ValueError("Tracker ARM was not observed")
        if not any(e.get("e") == "RX_READY" and e.get("rc") == "0" for e in arm_events):
            raise ValueError("Tracker RX_READY was not observed")
        tracker_command("STATUS", "armed-status")
        armed_status = drain_tracker("armed-status")
        tracker_regs = [
            e for e in armed_status if e.get("e") == "REG" and int(e["s"], 16) == session_id
        ]
        if not tracker_regs or bytes.fromhex(tracker_regs[-1]["bytes"])[0] & 0xCF != 0x85:
            raise ValueError("Tracker radio not verified in RX Continuous")
        if not status_complete(c.events, "receiver", session_id):
            raise ValueError("Tracker armed STATUS block incomplete")

        if rx_idle_seconds is not None:
            c.close()
            idle_start = time.monotonic_ns()
            idle_before = read_reset_state(tracker_session, protocol)
            time.sleep(rx_idle_seconds)
            try:
                idle_after = read_reset_state(tracker_session, protocol)
            except Exception as read_error:
                bundle["tracker_reset_read_error"] = f"{type(read_error).__name__}: {read_error}"
                try:
                    tracker_session, idle_after = resync_reset_state_once(
                        tracker_session, protocol, rf.PORTS["receiver"]
                    )
                    bundle["tracker_reset_resync"] = dict(
                        startup_breaks=2,
                        cpu_reset_requested=False,
                        session="fresh UPDI/OCD, no application command",
                    )
                except Exception as resync_error:
                    idle_after = None
                    bundle["tracker_reset_resync_error"] = (
                        f"{type(resync_error).__name__}: {resync_error}"
                    )
            bundle["idle_sample"] = dict(
                start_monotonic_ns=idle_start,
                end_monotonic_ns=time.monotonic_ns(),
                duration_target_s=rx_idle_seconds,
                before=idle_before,
                after=idle_after,
                tracker_mode="RX_CONTINUOUS",
                rf_transmissions=0,
            )
            bundle["tracker_reset_after"] = idle_after
            drain_tracker("post-idle-window")
            bundle["result"] = reader_free_rx_idle_summary(bundle["idle_sample"])
            bundle["classification"] = bundle["result"]["classification"]
        else:
            c.command("sender", f"ARM {session_id:08X}")
            c.wait(
                lambda: bool(
                    c.seen("sender", "ARM")
                    and c.seen("sender", "ARM")[-1].get("rc") == "0"
                    and c.seen("sender", "ARM")[-1].get("v") == str(session_id)
                ),
                10,
            )
            rx_state = c.seen("sender", "RX_STATE")
            if not rx_state or bytes.fromhex(rx_state[-1]["bytes"])[0] & 0xCF != 0x85:
                raise ValueError("Gateway radio not verified in RX Continuous")

            payload = HELLO_PAYLOAD.hex()
            command = "SEND " + payload
            c.command("sender", command)
            bundle["send_command"] = {
                "role": "sender",
                "text": command,
                "host_ns": c.commands[-1]["host_ns"],
            }
            terminal_names = (
                "DELIVERED",
                "REJECTED",
                "PROTOCOL_ERROR",
                "TIMEOUT_EXHAUSTED",
                "RADIO_ERROR",
            )
            c.wait(
                lambda: any(
                    e.get("role") == "sender" and e.get("e") in terminal_names for e in c.events
                ),
                180,
            )
            bundle["gateway_terminal"] = [
                e for e in c.events if e.get("role") == "sender" and e.get("e") in terminal_names
            ][-1]
            try:
                bundle["tracker_reset_after"] = read_reset_state(tracker_session, protocol)
            except Exception as read_error:
                bundle["tracker_reset_read_error"] = f"{type(read_error).__name__}: {read_error}"
                try:
                    tracker_session, bundle["tracker_reset_after"] = resync_reset_state_once(
                        tracker_session, protocol, rf.PORTS["receiver"]
                    )
                    bundle["tracker_reset_resync"] = dict(
                        startup_breaks=2,
                        cpu_reset_requested=False,
                        session="fresh UPDI/OCD, no application command",
                    )
                except Exception as resync_error:
                    bundle["tracker_reset_resync_error"] = (
                        f"{type(resync_error).__name__}: {resync_error}"
                    )
            drain_tracker("post-transaction")
            bundle["result"] = reader_free_h01_summary(
                c.events, bundle["tracker_reset_before"], bundle["tracker_reset_after"]
            )
            bundle["classification"] = (
                "H01_DELIVERED"
                if bundle["result"]["gateway_terminal"] == "DELIVERED"
                else "H01_NOT_DELIVERED"
            )
    except Exception as error:
        bundle.update(
            classification="INCOMPLETE_CAPTURE",
            failure_type=type(error).__name__,
            failure_reason=str(error),
        )
        try:
            bundle["tracker_reset_after"] = (
                read_reset_state(tracker_session, protocol) if tracker_session else None
            )
        except Exception as reset_error:
            bundle["tracker_reset_error"] = f"{type(reset_error).__name__}: {reset_error}"
        if tracker_session and protocol:
            try:
                drain_tracker("failure-window")
            except Exception as drain_error:
                bundle["tracker_drain_error"] = f"{type(drain_error).__name__}: {drain_error}"
        bundle["result"] = reader_free_h01_summary(
            c.events, bundle.get("tracker_reset_before"), bundle.get("tracker_reset_after")
        )
    finally:
        if tracker_session:
            close_updi_without_recovery(tracker_session)
        c.close()
        bundle.update(events=c.events, monitor_exits=c.monitor_exits, capture_errors=c.errors)
        bundle["files"] = {
            str(path.relative_to(run_dir)): sha(path)
            for path in run_dir.rglob("*")
            if path.is_file()
        }
        (run_dir / "bundle.json").write_text(json.dumps(bundle, indent=2) + "\n")
        restored = prepare()
        proof.note("restore.json", json.dumps(dict(standby_evidence=str(restored))) + "\n")
    print(
        json.dumps(
            dict(
                run_dir=str(run_dir),
                classification=bundle.get("classification"),
                result=bundle.get("result"),
            ),
            indent=2,
        )
    )
    return run_dir


def soak_campaign(stage, args):
    errors = hardware_gate_errors(args, True)
    if errors:
        raise ValueError("soak preflight incomplete: " + "; ".join(errors))
    artifact_root = ROOT / "artifacts/arq"
    artifact_root.mkdir(parents=True, exist_ok=True)
    ledger_path = artifact_root / "soak-ledger.json"
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
        if ledger.get("schema_version") != 1 or not isinstance(ledger.get("stages"), dict):
            raise ValueError("invalid soak ledger; refusing to overwrite it")
    else:
        ledger = {"schema_version": 1, "stages": {}}
    missing = missing_soak_prerequisites(stage, ledger["stages"])
    if missing:
        raise ValueError("soak stage prerequisites missing: " + ", ".join(missing))
    from arq_config import load_arq

    plan = build_soak_plan(stage, load_arq())
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-soak-" + stage
    run_dir = artifact_root / run_id
    if run_dir.exists():
        raise ValueError("soak run directory already exists")
    previous = ledger["stages"].get(stage)
    history = []
    if isinstance(previous, dict):
        history.extend(previous.get("history", []))
        prior_run = {k: v for k, v in previous.items() if k != "history"}
        if prior_run.get("status") == "RUNNING":
            process_id = prior_run.get("process_id")
            if type(process_id) is not int or process_id < 1:
                raise ValueError("prior running stage has no verifiable process ID")
            try:
                os.kill(process_id, 0)
            except ProcessLookupError:
                prior_run.update(
                    status="INTERRUPTED",
                    failure="prior soak host process is absent; termination reason unknown",
                )
            except (PermissionError, OSError) as error:
                raise ValueError("cannot verify prior soak process") from error
            else:
                raise ValueError("prior soak stage process is still active")
        history.append(prior_run)
    elif previous is not None:
        history.append(dict(status=previous, legacy_receipt=True))

    def save_ledger() -> None:
        temporary = ledger_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
        os.replace(temporary, ledger_path)

    record = dict(
        status="RUNNING",
        run_directory=str(run_dir),
        started_utc=datetime.now(UTC).isoformat(),
        process_id=os.getpid(),
        plan=plan,
        summary=None,
        observed_duration_s=None,
        history=history,
    )
    ledger["stages"][stage] = record
    save_ledger()

    def read_run_evidence():
        results_path = run_dir / "campaign.json"
        progress_path = run_dir / "soak" / "soak-progress.jsonl"
        results = json.loads(results_path.read_text()) if results_path.is_file() else []
        progress = (
            [json.loads(line) for line in progress_path.read_text().splitlines() if line]
            if progress_path.is_file()
            else []
        )
        starts = [row for row in progress if row.get("event") == "SESSION_START"]
        completes = [row for row in progress if row.get("event") == "SESSION_COMPLETE"]
        span_s = (
            (starts[-1]["monotonic_ns"] - starts[0]["monotonic_ns"]) / 1_000_000_000
            if starts
            else 0
        )
        return results, progress, starts, completes, span_s

    def update_partial_record() -> None:
        try:
            results, progress, starts, completes, span_s = read_run_evidence()
            record.update(
                summary=summarize_soak_results(results, plan["sessions"]),
                completed_sessions=len(completes),
                observed_duration_s=span_s,
            )
        except (OSError, ValueError, KeyError, TypeError) as error:
            record["partial_evidence_error"] = f"{type(error).__name__}: {error}"

    try:
        run_dir = campaign(soak_plan=plan, run_dir=run_dir)
        results_path = run_dir / "campaign.json"
        progress_path = run_dir / "soak" / "soak-progress.jsonl"
        if not results_path.is_file() or not progress_path.is_file():
            raise ValueError("incomplete soak evidence: campaign or progress ledger missing")
        results, progress, starts, completes, span_s = read_run_evidence()
        if len(starts) != len(results) or len(completes) != len(results):
            raise ValueError("incomplete soak evidence: session start/completion mismatch")
        summary = summarize_soak_results(results, plan["sessions"])
        record.update(
            summary=summary,
            observed_duration_s=span_s,
            completed_sessions=len(completes),
            ended_utc=datetime.now(UTC).isoformat(),
        )
        duration = plan["target_duration_s"]
        restore_ok = any(row.get("event") == "RESTORE_VERIFIED" for row in progress)
        if (
            len(results) != plan["sessions"]
            or summary["failures"]
            or not restore_ok
            or (duration is not None and span_s < duration)
        ):
            record.update(status="FAILED", failure="soak acceptance criteria not met")
            save_ledger()
            raise ValueError(record["failure"])
        record["status"] = "PASS"
        save_ledger()
        return run_dir
    except KeyboardInterrupt:
        update_partial_record()
        record.update(status="INTERRUPTED", ended_utc=datetime.now(UTC).isoformat())
        save_ledger()
        raise
    except Exception as error:
        update_partial_record()
        if record["status"] == "RUNNING":
            record.update(
                status="FAILED",
                failure=f"{type(error).__name__}: {error}",
                ended_utc=datetime.now(UTC).isoformat(),
            )
        save_ledger()
        raise


def hardware_gate_errors(args, require_rf):
    errors = rf.physical_readiness_errors(args, require_rf=require_rf)
    if require_rf and not getattr(args, "rf_path_confirmed", False):
        errors.append("RF connector/antenna path not physically confirmed")
    if require_rf and not getattr(args, "authorize_rf_test", False):
        errors.append("applicable RF test authorization not confirmed")
    return errors


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--campaign", action="store_true")
    mode.add_argument("--mvp", action="store_true")
    mode.add_argument("--radio-only-bringup", action="store_true")
    mode.add_argument("--hello-lora", action="store_true")
    mode.add_argument("--diagnostic-test", choices=("T01", "T02", "T03", "T04"))
    p.add_argument(
        "--reverse-direction",
        action="store_true",
        help="install and inspect reverse ARQ images; requires --radio-only-bringup",
    )
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--validate", type=Path)
    mode.add_argument("--reverse-raw", action="store_true")
    mode.add_argument("--reverse-raw-no-tracker-reader", action="store_true")
    mode.add_argument("--reader-free-h01", action="store_true")
    mode.add_argument("--tracker-rx-idle-control", action="store_true")
    mode.add_argument(
        "--soak-stage", choices=tuple(SOAK_SESSION_STAGES) + tuple(SOAK_DURATION_STAGES)
    )
    p.add_argument(
        "--rf-path-confirmed",
        action="store_true",
        help="operator has physically verified antenna connector and solder bridges",
    )
    p.add_argument(
        "--physical-mapping-verified",
        action="store_true",
        help="confirm the current physical board-to-USB role mapping",
    )
    p.add_argument(
        "--power-verified",
        action="store_true",
        help="confirm safe supply, common ground, UPDI wiring and no CP2102 back-feed",
    )
    p.add_argument(
        "--rf-hardware-verified",
        action="store_true",
        help="confirm compatible radio/antenna and permitted RF power including antenna gain",
    )
    p.add_argument(
        "--authorize-rf-test",
        action="store_true",
        help="confirm this RF test is within applicable authorization and operating conditions",
    )
    args = p.parse_args()
    if args.reverse_direction and not args.radio_only_bringup:
        p.error("--reverse-direction requires non-transmitting --radio-only-bringup")
    if args.validate:
        print(
            json.dumps(
                validate_bundle(json.loads(args.validate.read_text()), args.validate.parent),
                indent=2,
            )
        )
    elif args.radio_only_bringup or args.hello_lora or args.diagnostic_test:
        exchange = bool(args.hello_lora or args.diagnostic_test)
        errors = hardware_gate_errors(args, exchange)
        if errors:
            p.error("radio-only preflight incomplete: " + "; ".join(errors))
        print(radio_only_bringup(args, exchange=exchange))
    elif args.prepare:
        errors = hardware_gate_errors(args, False)
        if errors:
            p.error("programming preflight incomplete: " + "; ".join(errors))
        print(prepare())
    elif args.tracker_rx_idle_control:
        errors = hardware_gate_errors(args, False)
        if errors:
            p.error("RX-only preflight incomplete: " + "; ".join(errors))
        print(reader_free_h01(rx_idle_seconds=120))
    else:
        if not args.rf_path_confirmed:
            p.error("RF transmission requires --rf-path-confirmed after physical inspection")
        errors = hardware_gate_errors(args, True)
        if errors:
            p.error("RF preflight incomplete: " + "; ".join(errors))
        if args.soak_stage:
            print(soak_campaign(args.soak_stage, args))
            return
        if args.reverse_raw:
            print(reverse_raw())
        elif args.reverse_raw_no_tracker_reader:
            print(reverse_raw(tracker_reader=False))
        elif args.reader_free_h01:
            print(reader_free_h01())
        else:
            print(
                campaign((("H01", 1), ("H02", 1), ("H03", 1), ("H04", 10)))
                if args.mvp
                else campaign()
            )


if __name__ == "__main__":
    main()
