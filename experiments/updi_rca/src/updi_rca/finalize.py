"""Rebuild the RCA tables and handoff from the preserved raw observations."""

import csv
from datetime import datetime, timezone
import json
import hashlib
from collections import Counter
from pathlib import Path

from .metrics import metric_summary, wilson_interval
from .reporting import (
    EVENT_COLUMNS,
    FLASH_COLUMNS,
    FUSE_COLUMNS,
    HYPOTHESIS_COLUMNS,
    HYPOTHESIS_SEED_COLUMNS,
    PAIRWISE_COLUMNS,
    RANKING_COLUMNS,
    RUN_COLUMNS,
    write_csv,
)
from .paths import ARTIFACTS_ROOT, REPOSITORY_ROOT


def _data_path(root: Path, kind: str) -> Path:
    root = Path(root).resolve()
    if root == REPOSITORY_ROOT / "experiments/updi_rca":
        return REPOSITORY_ROOT / "artifacts/updi/legacy" / f"experiment-{kind}"
    return root / kind


PRIMARY_RUNS = {
    "lane_a": "baseline-20261026T171644Z-1a031f37",
    "lane_b": "baseline-20261026T171633Z-88c741a8",
}
FLAG_RX_RUN_ID = "flag-rx-20261026T174820Z"
SUPPORTED_IDS = {"H107", "H131", "H132", "H162", "H163", "H164", "H165", "H167"}
DOMAIN_SCORES = {
    "Power/GND board-local": 19,
    "Board-side UPDI path": 10,
    "Reset/watchdog": 20,
    "AVR silicon": 19,
    "Fuse/configuration": 0,
    "Firmware/runtime": 15,
    "Adapter/host/software": 1,
    "PCB/assembly/BOM": 6,
    "Environment": 0,
    "Methodology/interpretation": 0,
}
BLOCKED_DOMAINS = {
    "Power/GND board-local",
    "Board-side UPDI path",
    "Reset/watchdog",
    "AVR silicon",
    "PCB/assembly/BOM",
    "Environment",
}
LANE_INFO = {
    "lane_a": {
        "tty": "/dev/ttyUSB0",
        "id_path": "pci-0000:00:14.0-usb-0:4:1.0",
        "sysfs": "/sys/devices/pci0000:00/0000:00:14.0/usb3/3-4/3-4:1.0/ttyUSB0/tty/ttyUSB0",
        "usb_device": "18",
        "by_path": "pci-0000:00:14.0-usb-0:4:1.0-port0",
    },
    "lane_b": {
        "tty": "/dev/ttyUSB1",
        "id_path": "pci-0000:00:14.0-usb-0:1:1.0",
        "sysfs": "/sys/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0/ttyUSB1/tty/ttyUSB1",
        "usb_device": "19",
        "by_path": "pci-0000:00:14.0-usb-0:1:1.0-port0",
    },
}
CAUSE_TRANSLATIONS = dict(
    line.split(" ", 1)
    for line in """
H001 VDD solder joint open, cracked, or unsoldered
H002 GND solder joint open, cracked, or unsoldered
H003 One AVR VDD/GND pin has poor or no contact
H004 Missing 100 nF decoupling capacitor
H005 Wrong decoupling capacitor value or package
H006 Cracked MLCC from board flex
H007 Cold solder joint on decoupling capacitor
H008 Capacitor too far from pin (long trace or high inductance)
H009 MLCC DC-bias derating lowers effective capacitance
H010 Missing or degraded bulk capacitor; ESR too high
H011 Regulator dropout or output droop under heavy load
H012 Regulator oscillation caused by unsuitable capacitor or ESR
H014 Wrong regulator output due to feedback resistor value
H015 Failed or marginal regulator
H016 Insufficient input supply from a current-limited 3.3 V adapter
H017 High contact resistance in VDD/GND jumper wires
H018 Poor ground connection between adapter and board
H019 Ground loop or multiple ground return paths
H020 PCB ground bounce
H021 Ground plane gap interrupts the return path
H022 Broken via or cracked via barrel
H023 VDD/GND trace too narrow or too resistive
H024 Ripple or noise on VDD
H025 Slow rail rise causes poor POR/BOD startup
H026 Power-up inrush current
H027 Incorrect power sequencing
H028 High resistance in power-path fuse, ferrite, diode, or switch
H029 Excessive drop across reverse-protection diode
H030 Low battery voltage or high internal resistance, if a battery is fitted
H031 Board peripheral draws high current or is partially shorted (radio, sensor, LED, level shifter)
H032 Faulty peripheral pulls down the supply rail
H033 VDD-GND leakage from flux, moisture, or contamination
H034 VDD is below specification for the selected clock (for example, 24 MHz)
H035 Adapter/board voltage mismatch (3.3 V versus 5 V)
H036 Cold or cracked header-pin solder joint
H037 Header pin fails to contact jumper (oxidized, bent, or loose)
H038 Loose jumper contact changes after each reconnection
H039 Broken or hairline-cracked UPDI trace
H040 Cold solder joint on AVR UPDI pad
H041 UPDI pad bridged to adjacent pin
H042 UPDI trace shorted to another trace
H043 Leakage on UPDI line
H044 Excessive parasitic capacitance on UPDI line
H045 Unintended pull-up, pull-down, or series resistor on board UPDI line
H046 Leaky ESD/TVS diode on UPDI line
H047 Other component attached to UPDI line (LED, sensor, connector)
H048 Long UPDI trace or noisy parallel trace causes crosstalk
H049 AVR UPDI pin damaged by ESD or overvoltage
H050 UPDI voltage level does not match target VDD
H051 Unstable UPDI ground reference
H052 Loose or drifting resistor in UPDI chain
H053 EMI or crosstalk from radio or switching circuitry couples onto UPDI
H055 Missing or incorrect reset pull-up
H056 Incorrect capacitor on reset line
H057 Reset button or switch leakage
H059 RSTPINCFG fuse differs
H060 Watchdog fuse is enabled
H061 Firmware watchdog timeout
H062 Firmware-triggered software reset (SWRF)
H068 AVR unit has a factory defect
H070 Prior overvoltage or reverse-polarity event
H071 Partial UPDI PHY failure
H072 Internal oscillator tolerance differs
H073 Oscillator unstable at low VDD or changing temperature
H074 Counterfeit or remarked chip, or different lot
H075 Different silicon revision
H076 Erratum triggered by environmental conditions
H077 Flash endurance degradation or bit error
H078 Incomplete flash write that still passes UPDI verification
H079 Abnormal data retention
H080 Other chip pin damaged or poorly soldered (not UPDI/VDD/GND)
H081 Overheating during soldering or rework
H083 Chip overheats during runtime
H084 BODCFG differs (level, active/sleep mode, or sample frequency)
H091 CRC-at-reset check fails
H092 USERROW or EEPROM contents differ
H093 UPDI clock selection (UPDICLKSEL) differs
H094 UPDI control bits differ (GTVAL, IBDLY, CCDETDIS, PARD, etc.)
H095 Firmware changes clock or prescaler during runtime
H096 Firmware enters sleep mode
H097 Firmware peripheral activity creates high bus load (DMA, event system, interrupt storm)
H098 ACC access collides with CPU/bus (bus arbitration timeout)
H099 NVMCTRL is busy during ACC access
H100 Write to CCP-protected register fails
H101 Firmware reads floating pin or unconnected peripheral, changing behavior
H103 Incorrect interrupt vector or bootloader configuration
H104 Firmware sends virtual-UART/OCD messages faster than host can read
H105 Good and suspect boards have different firmware versions
H106 Unintended compile or link differences
H107 Firmware fails to clear reset flag and misinterprets it
H108 Intermittent CP2102 adapter unit
H109 Counterfeit or clone CP2102 adapter
H110 Adapter TX drive strength too weak under higher suspect-board load
H111 Adapter 3.3 V droops when suspect board is connected
H113 Baud-rate rounding error at 38400
H114 Incorrect UART framing (even parity, two stop bits)
H115 Half-duplex echo handling causes RX/TX collision
H116 Timing race between echo read and target response
H117 FIFO overrun or incorrect buffer flush
H118 upditerm timeout too short for suspect board
H119 upditerm retry or error-recovery logic
H125 Another process claims serial port (ModemManager, brltty, etc.)
H126 Different USB hub or port
H128 Laptop charger connection changes common-mode noise
H129 Loose or degraded USB cable moved during test
H130 Different plug/unplug sequence
H131 Previous session leaves target state behind (OCD, halt, or reset state)
H132 Target is not power-cycled between tests
H133 Different PCB revision on reference and suspect boards
H134 Different BOM component values or brands
H135 Wrong component value or package
H136 Reversed component orientation (diode, LED, polarized capacitor)
H137 Missing component or missing 0-ohm link (incorrect DNP)
H139 Insufficient solder paste, void, or head-in-pillow joint
H140 Cold hand-solder joint
H141 Hidden solder bridge under package
H142 Flux residue causes leakage or corrosion
H143 Solder-mask residue on pad
H145 Defective plated through-hole
H146 Broken inner PCB layer on multilayer board
H147 Loose bodge wire or modification
H148 Crystal or external-clock components load a chip pin
H150 Thermal cycling cracks a solder joint
H151 Prior experiment damaged board (short, reverse connection, 5 V on 3.3 V)
H152 Board contaminated by sweat, water, or dust
H153 Temperature variation or warm-up drift
H154 Humidity or condensation
H155 ESD from person, clothing, or bench
H156 EMI from phone, Wi-Fi, motor, switching charger, or on-board radio
H157 Hand or finger near board causes capacitive coupling
H158 Board rests on conductive surface (metal table or tray)
H159 Vibration or cable movement
H160 AC supply-line noise
H161 Reference/suspect labels swapped
H162 Reference board had too few trials (it may be intermittent at a low rate)
H163 Test conditions differ (power-up delay, temperature, or order)
H164 Logs come from different sessions or firmware builds
H165 Fuses, firmware, or USERROW were not actually compared between boards
H166 Probe or test lead adds electrical load
H167 Multiple symptoms have multiple causes, not one root cause
H168 Symptom is a tool artifact (logging or retries hide behavior)
""".strip().splitlines()
)


def translate_hypothesis_text(hypothesis_id: str, text: str) -> str:
    if not any("\u0e00" <= char <= "\u0e7f" for char in text):
        return text
    try:
        return CAUSE_TRANSLATIONS[hypothesis_id]
    except KeyError as error:
        raise ValueError(f"missing English cause translation for {hypothesis_id}") from error


def summarize_flag_rx_attempts(attempts: list[dict]) -> dict:
    if not attempts:
        raise ValueError("FLAG_RX summary requires at least one read attempt")
    metrics = metric_summary([
        {"success": item.get("exit") == 0, "failure_stage": item.get("failure_stage"),
         "latency_ms": item.get("latency_ms")}
        for item in attempts
    ])
    values = [
        item.get("values", {}).get("LDS 1e")
        for item in attempts
        if item.get("exit") == 0 and isinstance(item.get("values"), dict)
        and isinstance(item.get("values", {}).get("LDS 1e"), int)
    ]
    counts = Counter(values)
    return {
        "metrics": metrics,
        "value_counts": dict(sorted(counts.items())),
        "flag_rx_set": sum(bool(value & 0x02) for value in values),
        "flag_enable_set": sum(bool(value & 0x01) for value in values),
        "valid_flag_samples": len(values),
    }


def canonical_attempt_paths(baseline_root: Path) -> dict[tuple[str, str], list[Path]]:
    """Select only the commissioned 1..100 attempts from each primary condition."""
    selected = {}
    for lane, run_id in PRIMARY_RUNS.items():
        for test_id in ("sib", "control"):
            folder = baseline_root / lane / test_id
            paths = [folder / f"{run_id}-{test_id}-{n:04}.json" for n in range(1, 101)]
            missing = [path.name for path in paths if not path.is_file()]
            if missing:
                raise FileNotFoundError(f"{lane}/{test_id}: missing {len(missing)} canonical attempt files")
            selected[(lane, test_id)] = paths
    return selected


def classify_raw_event(event: dict) -> tuple[str, str]:
    kind = event.get("kind")
    if kind == "tx":
        return "HOST_TX", "HOST_TO_TARGET"
    if kind == "echo":
        return "LOCAL_ECHO", "TARGET_TO_HOST"
    if kind == "response":
        return event.get("stage") or "TARGET_RESPONSE", "TARGET_TO_HOST"
    return "UNKNOWN", "UNKNOWN"


def _status_for(hypothesis_id: str, domain: str) -> str:
    if hypothesis_id == "H166" or domain in BLOCKED_DOMAINS:
        return "BLOCKED"
    if hypothesis_id in SUPPORTED_IDS:
        return "SUPPORTED"
    return "UNRESOLVED"


def _score_for(hypothesis_id: str, domain: str) -> int:
    score = DOMAIN_SCORES[domain]
    if hypothesis_id == "H098":
        return 13
    if hypothesis_id == "H102":
        return 12
    return score


def _failure_stage(item: dict) -> str:
    if item.get("failure_stage"):
        return item["failure_stage"]
    anomaly = str(item.get("first_anomaly") or "").lower()
    if "echo" in anomaly:
        return "LOCAL_ECHO"
    if "ack" in anomaly:
        return "ACC_ACK"
    if "response" in anomaly or "timeout" in anomaly:
        return "UPDI_CONTROL_RESPONSE"
    return ""


def _hex_length(value: str) -> int:
    try:
        return len(bytes.fromhex(value or ""))
    except ValueError:
        return 0


def protocol_event_rows(
    *, run_id: str, lane: str, board_id: str, source_log: str, test_id: str, item: dict
) -> list[dict]:
    rows = []
    last_tx = ""
    for index, event in enumerate(item.get("events") or [], 1):
        stage, direction = classify_raw_event(event)
        value = event.get("hex", "")
        kind = event.get("kind")
        if kind == "tx":
            last_tx = value
            operation = "BREAK_SYNC" if event.get("baud") == 300 and value == "00" else (
                "SIB_REQUEST" if value.startswith("55e6") else (
                    "ACC_LDS_REQUEST" if value.startswith("5500") else "UPDI_CONTROL_READ_REQUEST"
                )
            )
            tx_hex, echo_hex, response_hex = value, "", ""
            expected_len = event.get("count", _hex_length(value))
            actual_len = _hex_length(value)
            classification = "HOST_WRITE_RECORDED"
        elif kind == "echo":
            operation = "half_duplex_echo"
            tx_hex, echo_hex, response_hex = last_tx, value, ""
            expected_len = event.get("requested", _hex_length(last_tx))
            actual_len = _hex_length(value)
            classification = "EXACT_ECHO" if value == last_tx else ("EMPTY_ECHO" if not value else "CORRUPT_ECHO")
        elif kind == "response":
            operation = {"OCD_STATUS": "read_ASI_OCD_STATUS", "OCD_MESSAGE": "read_ASI_OCD_MESSAGE"}.get(stage, "target_response")
            tx_hex, echo_hex, response_hex = "", "", value
            expected_len = event.get("requested", "")
            actual_len = _hex_length(value)
            classification = "TARGET_RESPONSE_RECEIVED" if actual_len else "EMPTY_TARGET_RESPONSE"
        else:
            continue
        rows.append({
            "timestamp_monotonic": event.get("ns", ""),
            "run_id": run_id,
            "event_id": f"{run_id}:{Path(source_log).stem}:{index:03}",
            "lane": lane,
            "board_id": board_id,
            "stage": stage,
            "direction": direction,
            "operation": operation,
            "address": item.get("address") or {"OCD_STATUS": "0x05", "OCD_MESSAGE": "0x0d"}.get(stage, ""),
            "tx_hex": tx_hex,
            "echo_hex": echo_hex,
            "response_hex": response_hex,
            "expected_len": expected_len,
            "actual_len": actual_len,
            "status_raw": event.get("stage", ""),
            "errno": "",
            "classification": classification,
            "raw_log_path": source_log,
        })
    return rows


def _status_value(values: dict, *keys: str) -> str:
    if not isinstance(values, dict):
        return ""
    normalized = {str(k).lower(): v for k, v in values.items()}
    for key in keys:
        value = normalized.get(key.lower())
        if isinstance(value, int):
            return f"0x{value:02x}"
        if isinstance(value, list):
            return ";".join(f"0x{item:02x}" if isinstance(item, int) else str(item) for item in value)
        if value is not None:
            return str(value)
    return ""


def _run_row(root: Path, path: Path, lane: str, test_id: str, item: dict, attempt: int) -> dict:
    info = LANE_INFO.get(lane, {})
    board = f"UNKNOWN_TARGET_{lane.upper()}" if lane in LANE_INFO else "UNKNOWN_TARGET"
    inventory = {}
    inventory_path = _data_path(root, "reports") / "device_inventory.csv"
    if inventory_path.exists():
        with inventory_path.open(newline="", encoding="utf-8") as stream:
            inventory = next((r for r in csv.DictReader(stream) if r["lane"] == lane), {})
    events = item.get("events") or []
    if "baseline-20261026T1655Z" in path.parts and lane in PRIMARY_RUNS:
        run_id = PRIMARY_RUNS[lane]
    elif lane in LANE_INFO and lane in path.parts:
        run_id = path.parent.parent.name
    else:
        run_id = path.stem
    tx = next((e.get("hex", "") for e in events if e.get("kind") == "tx"), "")
    echo = next((e.get("hex", "") for e in events if e.get("kind") == "echo"), "")
    stage = _failure_stage(item)
    passed = item.get("exit") == 0
    values = item.get("values") or {}
    if "baseline-20261026T1655Z" in path.parts:
        test_id = f"{test_id}_{item.get('baud', 38400)}"
    elif item.get("mode") == "ocd-message":
        test_id = "ocd_message_snapshot"
    elif item.get("mode") == "read" and item.get("address") == 0x1E:
        test_id = "flag_rx_gpr2_read_0x1e"
    else:
        test_id = f"legacy_{item.get('mode', test_id)}_{item.get('address', '')}"
    address = item.get("address")
    data_value = values.get(f"LDS {address:02x}") if isinstance(values, dict) and isinstance(address, int) else None
    return {
        "timestamp": item.get("utc", ""),
        "run_id": run_id,
        "test_id": test_id,
        "lane": lane,
        "board_id": inventory.get("board_id", board),
        "adapter_id": f"CP2102 VID:PID=10c4:ea60 serial=0001 (duplicate); ID_PATH={info.get('id_path', '')}",
        "current_tty": inventory.get("current_tty", info.get("tty", "")),
        "baud": item.get("baud", ""),
        "cpu_state": "RUNNING_OR_UNCONTROLLED",
        "firmware_sha256": "UNKNOWN_NOT_SNAPSHOTTED",
        "attempt": attempt,
        "result": "PASS" if passed else "FAIL",
        "latency_ms": item.get("latency_ms", ""),
        "failure_stage": "" if passed else (stage or "UNKNOWN"),
        "error_type": "" if passed else ("ECHO_MISMATCH" if stage == "LOCAL_ECHO" else "TARGET_RESPONSE_TIMEOUT"),
        "expected_hex": tx if not passed else "",
        "observed_hex": echo if not passed else (f"{data_value:02x}" if isinstance(data_value, int) else ""),
        "rstfr_raw": "",
        "ocd_status_raw": _status_value(values, "CS05", "ASI_OCD_STATUS_SEQUENCE", "ASI_OCD_STATUS"),
        "sys_status_raw": _status_value(values, "CS0b", "ASI_SYS_STATUS"),
        "kernel_usb_error": "",
        "source_log": path.relative_to(root).as_posix(),
        "raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _all_run_rows(root: Path, canonical: dict) -> tuple[list[dict], dict[str, dict]]:
    rows = []
    raw_root = _data_path(root, "evidence") / "raw"
    raw_to_row = {}
    for (lane, test_id), paths in canonical.items():
        for attempt, path in enumerate(paths, 1):
            item = json.loads(path.read_text(encoding="utf-8"))
            row = _run_row(root, path, lane, test_id, item, attempt)
            rows.append(row)
            raw_to_row[path.relative_to(root).as_posix()] = row
    legacy = sorted(p for p in raw_root.rglob("*.json") if "baseline-20261026T1655Z" not in p.parts)
    for attempt, path in enumerate(legacy, 1):
        item = json.loads(path.read_text(encoding="utf-8"))
        lane = next((part for part in path.parts if part in LANE_INFO), None)
        if lane is None:
            lane = next((name for name, info in LANE_INFO.items() if item.get("id_path") == info["id_path"]), "UNKNOWN")
        row = _run_row(root, path, lane, "legacy", item, attempt)
        rows.append(row)
        raw_to_row[path.relative_to(root).as_posix()] = row
    terminal_log = _data_path(root, "evidence") / "raw" / "terminal-observation-20261026.md"
    if not terminal_log.exists():
        terminal_log = _data_path(root, "evidence") / "raw" / "terminal-observation-20261027.md"
    rows.append({
        "timestamp": "UNKNOWN_TIMESTAMP",
        "run_id": "terminal-observation-unknown-time",
        "test_id": "terminal_text_and_process_exit",
        "lane": "UNKNOWN",
        "board_id": "UNKNOWN_TARGET",
        "adapter_id": "UNKNOWN_FROM_TRANSCRIPT",
        "current_tty": "",
        "baud": "",
        "cpu_state": "UNKNOWN",
        "firmware_sha256": "UNKNOWN",
        "attempt": "",
        "result": "OBSERVATION_ONLY_PROCESS_SIGKILL",
        "latency_ms": "",
        "failure_stage": "HOST_PROCESS",
        "error_type": "SIGKILL",
        "expected_hex": "",
        "observed_hex": "",
        "rstfr_raw": "",
        "ocd_status_raw": "",
        "sys_status_raw": "",
        "kernel_usb_error": "",
        "source_log": terminal_log.relative_to(root).as_posix() if terminal_log.exists() else "",
        "raw_sha256": hashlib.sha256(terminal_log.read_bytes()).hexdigest() if terminal_log.exists() else "",
    })
    return rows, raw_to_row


def _event_rows(root: Path, canonical: dict, raw_to_row: dict[str, dict]) -> list[dict]:
    rows = []
    for (lane, test_id), paths in canonical.items():
        for path in paths:
            item = json.loads(path.read_text(encoding="utf-8"))
            rel = path.relative_to(root).as_posix()
            run = raw_to_row[rel]
            last_tx = ""
            for index, event in enumerate(item.get("events") or [], 1):
                stage, direction = classify_raw_event(event)
                value = event.get("hex", "")
                kind = event.get("kind")
                if kind == "tx":
                    last_tx = value
                    operation = "BREAK_SYNC" if event.get("baud") == 300 and value == "00" else (
                        "SIB_REQUEST" if value.startswith("55e6") else "UPDI_CONTROL_READ_REQUEST"
                    )
                    tx_hex, echo_hex, response_hex = value, "", ""
                    expected_len = event.get("count", _hex_length(value))
                    actual_len = _hex_length(value)
                    classification = "HOST_WRITE_RECORDED"
                elif kind == "echo":
                    operation = "half_duplex_echo"
                    tx_hex, echo_hex, response_hex = last_tx, value, ""
                    expected_len = event.get("requested", _hex_length(last_tx))
                    actual_len = _hex_length(value)
                    classification = "EXACT_ECHO" if value == last_tx else ("EMPTY_ECHO" if not value else "CORRUPT_ECHO")
                else:
                    operation = "target_response"
                    tx_hex, echo_hex, response_hex = "", "", value
                    expected_len = event.get("requested", "")
                    actual_len = _hex_length(value)
                    classification = "TARGET_RESPONSE_RECEIVED" if actual_len else "EMPTY_TARGET_RESPONSE"
                rows.append({
                    "timestamp_monotonic": event.get("ns", ""),
                    "run_id": run["run_id"],
                    "event_id": f"{run['run_id']}:{test_id}:{path.stem[-4:]}:{index:03}",
                    "lane": lane,
                    "board_id": run["board_id"],
                    "stage": stage,
                    "direction": direction,
                    "operation": operation,
                    "address": item.get("address", ""),
                    "tx_hex": tx_hex,
                    "echo_hex": echo_hex,
                    "response_hex": response_hex,
                    "expected_len": expected_len,
                    "actual_len": actual_len,
                    "status_raw": event.get("stage", ""),
                    "errno": "",
                    "classification": classification,
                    "raw_log_path": rel,
                })
    canonical_logs = {path.relative_to(root).as_posix() for paths in canonical.values() for path in paths}
    for rel, run in raw_to_row.items():
        if rel in canonical_logs:
            continue
        item = json.loads((root / rel).read_text(encoding="utf-8"))
        source_events = protocol_event_rows(
            run_id=run["run_id"], lane=run["lane"], board_id=run["board_id"],
            source_log=rel, test_id=run["test_id"], item=item,
        )
        if source_events:
            rows.extend(source_events)
            continue
        rows.append({
            "timestamp_monotonic": "",
            "run_id": run["run_id"],
            "event_id": f"{run['run_id']}:{Path(rel).stem}:summary",
            "lane": run["lane"],
            "board_id": run["board_id"],
            "stage": run["failure_stage"] or "LEGACY_PROBE_OUTCOME",
            "direction": "UNKNOWN",
            "operation": "legacy bounded probe summary; event bytes remain in raw JSON",
            "address": "",
            "tx_hex": "",
            "echo_hex": "",
            "response_hex": "",
            "expected_len": "",
            "actual_len": "",
            "status_raw": "",
            "errno": "",
            "classification": run["result"],
            "raw_log_path": rel,
        })
    terminal_run = "terminal-observation-unknown-time"
    terminal_path = _data_path(root, "evidence") / "raw" / "terminal-observation-20261026.md"
    source = terminal_path.relative_to(root).as_posix() if terminal_path.exists() else ""
    rows.extend([
        {"timestamp_monotonic": "", "run_id": terminal_run, "event_id": f"{terminal_run}:text", "lane": "UNKNOWN", "board_id": "UNKNOWN_TARGET", "stage": "OCD_MESSAGE_CANDIDATE", "direction": "UNKNOWN", "operation": "9 terminal lines; later Lane A read captured one matching line", "address": "", "tx_hex": "", "echo_hex": "", "response_hex": "", "expected_len": "", "actual_len": "", "status_raw": "UNKNOWN", "errno": "", "classification": "FOLLOWUP_MATCHED_TEXT_ORIGINAL_SESSION_UNIDENTIFIED", "raw_log_path": source},
        {"timestamp_monotonic": "", "run_id": terminal_run, "event_id": f"{terminal_run}:sigkill", "lane": "UNKNOWN", "board_id": "UNKNOWN_TARGET", "stage": "HOST_PROCESS", "direction": "HOST", "operation": "upditerm.py terminated by SIGKILL", "address": "", "tx_hex": "", "echo_hex": "", "response_hex": "", "expected_len": "", "actual_len": "", "status_raw": "", "errno": "SIGKILL", "classification": "HOST_PROCESS_EXIT_NOT_TARGET_RESET", "raw_log_path": source},
    ])
    return rows


def _pairwise_rows(canonical: dict) -> list[dict]:
    rows = []
    for test_id in ("sib", "control"):
        samples = {}
        for lane in ("lane_a", "lane_b"):
            attempts = []
            for path in canonical[(lane, test_id)]:
                item = json.loads(path.read_text(encoding="utf-8"))
                attempts.append({"success": item.get("exit") == 0, "latency_ms": item.get("latency_ms"), "failure_stage": _failure_stage(item)})
            samples[lane] = (attempts, metric_summary(attempts))
        for metric in ("success_rate", "failure_rate", "median_latency_ms", "p95_latency_ms"):
            a = samples["lane_a"][1][metric]
            b = samples["lane_b"][1][metric]
            delta = b - a
            relative = delta / a if a else "UNDEFINED_A_ZERO"
            va = samples["lane_a"][1]
            vb = samples["lane_b"][1]
            if metric in ("success_rate", "failure_rate"):
                wi_a = va["wilson_95"] if metric == "success_rate" else (1 - va["wilson_95"][1], 1 - va["wilson_95"][0])
                wi_b = vb["wilson_95"] if metric == "success_rate" else (1 - vb["wilson_95"][1], 1 - vb["wilson_95"][0])
                value_a = f"{va['successes'] if metric == 'success_rate' else va['failures']}/100 ({a:.1%}; Wilson95 [{wi_a[0]:.1%},{wi_a[1]:.1%}])"
                value_b = f"{vb['successes'] if metric == 'success_rate' else vb['failures']}/100 ({b:.1%}; Wilson95 [{wi_b[0]:.1%},{wi_b[1]:.1%}])"
            else:
                value_a, value_b = f"{a:.3f} ms", f"{b:.3f} ms"
            rows.append({
                "test_id": f"{test_id}_38400_unheld",
                "metric": metric,
                "board_a_value": value_a,
                "board_b_value": value_b,
                "absolute_delta": f"{delta:.6f}",
                "relative_delta": f"{relative:.6f}" if isinstance(relative, float) else relative,
                "interpretation": "Observed Lane A/B adapter-plus-target paths differ; the fixed pairing confounds physical board and adapter attribution.",
                "n_a": 100,
                "n_b": 100,
            })
    return rows


def _update_hypotheses(root: Path, report_dir: Path | None = None) -> tuple[dict[str, int], Counter]:
    seed_path = root / "config" / "hypotheses_seed.csv"
    with seed_path.open(newline="", encoding="utf-8") as stream:
        seed = list(csv.DictReader(stream))
    for item in seed:
        item["text"] = translate_hypothesis_text(item["hypothesis_id"], item["text"])
        if any("\u0e00" <= char <= "\u0e7f" for char in item["text"]):
            raise ValueError(f"cause label remains untranslated: {item['hypothesis_id']}")
    status_rows = []
    ranking_rows = []
    counts = Counter()
    for item in seed:
        hid, domain = item["hypothesis_id"], item["domain"]
        status = _status_for(hid, domain)
        score = _score_for(hid, domain)
        item["evidence_score"] = str(score)
        item["current_status"] = status
        counts[status] += 1
        if hid in SUPPORTED_IDS:
            evidence_for = {
                "H107": "Historical BORF persisted after clear while a marker survived 20 samples; no independent new boot was observed.",
                "H131": "Lane A GPR2 direct reads returned 0x03 in 100/100 attempts with no virtual-UART payload writes; the separate OCD snapshot captured 15 message bytes after OCDMV=1. Persistent carryover is plausible, not causal proof.",
                "H132": "Targets were not power-cycled between all sessions; no controlled power-cycle comparison was run.",
                "H162": "Fresh baseline used n=100 per lane and condition; target-side success was 100/100 on A and 0/100 on B, with identities unresolved.",
                "H163": "CPU RUNNING/STOPPED, power-up delay, and other environmental conditions were not crossed in the fresh baseline.",
                "H164": "Historical and current evidence spans separate sessions; raw artifacts are now linked but firmware identity remains unknown.",
                "H165": "Current fuse/firmware/USERROW snapshots were not obtained for either target (n=0 paired snapshots).",
                "H167": "Historical ACC data-response misses (19/60 after exact echo), fresh local-echo failures (100/100 on Lane B), fresh Lane A GPR2 reads (100/100), and one captured 15-byte OCD message occupy different stages.",
            }[hid]
        else:
            evidence_for = "Fresh 38400 baseline: Lane A passed 100/100 SIB and 100/100 control; Lane B failed 100/100 in LOCAL_ECHO before any target response. Lane A GPR2 reads returned 0x03 in 100/100 samples; this shows persistent FLAG_RX state, not its source. Historical unheld LDS had 19/60 missing ACC data responses after exact echo. One bounded Lane A OCD read (n=1) captured 15 message bytes."
        if domain == "Adapter/host/software":
            against = "Kernel logs showed 0 matching CP210x/USB protocol errors during the 4m01s Lane B baseline window; no adapter crossover was run."
        elif domain == "Fuse/configuration":
            against = "No current paired fuse snapshots (n=0); the historical BODCFG=0x54 observation cannot be assigned to either current target."
        elif domain == "Firmware/runtime":
            against = "Current firmware SHA is unknown for both targets; no SILENT/HEARTBEAT image was flashed and no RUNNING/STOPPED crossover was completed."
        elif domain == "Methodology/interpretation":
            against = "The fresh baseline is controlled for baud, method, and attempt count (n=100 per lane/condition), but board identity and adapter path remain confounded."
        elif domain == "Environment":
            against = "No instrumented voltage, temperature, ground-offset, or reset-correlation measurements are available."
        else:
            against = "No board/adapter crossover or physical trace was recorded; target identity is UNKNOWN_TARGET, so component attribution is unavailable."
        next_test = "Perform one no-programming adapter crossover with both boards labeled; if the failure follows a board, capture VDD/local GND, ground offset, RESET, UPDI at both sides of the series element, and adapter TX during attach and RUN at >=20 MS/s."
        status_rows.append({
            "hypothesis_id": hid,
            "domain": domain,
            "cause": item["text"],
            "status": status,
            "evidence_score": score,
            "confidence_label": status,
            "predictions": item["observable_prediction"],
            "discriminator": item["cheapest_discriminator"],
            "evidence_for": evidence_for,
            "evidence_against": against,
            "next_test": next_test,
            "requires_flash": item["requires_flash"],
            "requires_physical_measurement": item["requires_instrument"],
            "last_updated": "2026-10-27",
        })
        ranking_rows.append({
            "rank": 0,
            "hypothesis_id": hid,
            "domain": domain,
            "cause": item["text"],
            "status": status,
            "evidence_score": score,
            "decisive_evidence": evidence_for,
            "contrary_evidence": against,
            "remaining_uncertainty": "Evidence score ranks the next discriminating tests; it is not a probability or causal finding.",
            "next_required_measurement": next_test,
        })
    status_rows.sort(key=lambda r: (int(r["hypothesis_id"][1:]),))
    ranking_rows.sort(key=lambda r: (-int(r["evidence_score"]), int(r["hypothesis_id"][1:])))
    for rank, row in enumerate(ranking_rows, 1):
        row["rank"] = rank
    write_csv(root / "config" / "hypotheses_seed.csv", HYPOTHESIS_SEED_COLUMNS, seed)
    report_dir = report_dir or _data_path(root, "reports")
    write_csv(report_dir / "hypothesis_status.csv", HYPOTHESIS_COLUMNS, status_rows)
    write_csv(report_dir / "root_cause_ranking.csv", RANKING_COLUMNS, ranking_rows)
    return {r["hypothesis_id"]: int(r["evidence_score"]) for r in status_rows}, counts


def _hash_summary(root: Path) -> tuple[int, int]:
    entries = bad = 0
    baseline = _data_path(root, "evidence") / "raw" / "baseline-20261026T1655Z"
    summaries = list(baseline.rglob("*-summary.json"))
    for summary in summaries:
        for attempt in json.loads(summary.read_text(encoding="utf-8")).get("attempts", []):
            entries += 1
            target = Path(attempt.get("source_log", ""))
            digest = attempt.get("raw_sha256", "")
            if not target.is_absolute():
                target = root.parent.parent / target
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                bad += 1
    return entries, bad


def _source_hash_summary(root: Path, run_rows: list[dict]) -> tuple[int, int]:
    entries = bad = 0
    for row in run_rows:
        source, digest = row.get("source_log", ""), row.get("raw_sha256", "")
        if not source or not digest:
            bad += 1
            continue
        entries += 1
        path = root / source
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            bad += 1
    return entries, bad


def _write_fuse_comparison(root: Path, report_dir: Path | None = None) -> None:
    report_dir = report_dir or _data_path(root, "reports")
    write_csv(report_dir / "fuse_compare.csv", FUSE_COLUMNS, [
        {"field": "All current fuse bytes", "side_a": "UNKNOWN_TARGET_LANE_A", "side_b": "UNKNOWN_TARGET_LANE_B", "value_a": "NOT_READ", "value_b": "NOT_READ", "comparison_status": "NOT_COMPARABLE", "source_run_a": PRIMARY_RUNS["lane_a"], "source_run_b": PRIMARY_RUNS["lane_b"], "notes": "No current fuse reads; target identity, firmware, and programming state are unknown. Historical BODCFG=0x54 is not mapped to these lanes."},
        {"field": "Historical BODCFG", "side_a": "UNKNOWN_TARGET", "side_b": "UNKNOWN_TARGET", "value_a": "0x54 (historical)", "value_b": "NOT_READ", "comparison_status": "NOT_COMPARABLE", "source_run_a": "docs/updi-root-cause-report.md", "source_run_b": "", "notes": "Preserved historical observation; cannot assign to either current adapter path."},
    ])


def _write_report(
    root: Path, summaries: dict, counts: Counter, hash_entries: int, hash_bad: int,
    source_hash_entries: int, source_hash_bad: int, run_count: int, event_count: int,
    report_dir: Path | None = None,
) -> None:
    report_dir = report_dir or _data_path(root, "reports")
    a_sib, b_sib = summaries[("lane_a", "sib")], summaries[("lane_b", "sib")]
    a_ctl, b_ctl = summaries[("lane_a", "control")], summaries[("lane_b", "control")]
    flag_rx_paths = sorted((_data_path(root, "evidence") / "raw" / "flag-rx-20261026T174820Z" / "lane_a").glob("*.json"))
    if len(flag_rx_paths) != 100:
        raise ValueError(f"expected 100 Lane A FLAG_RX reads, found {len(flag_rx_paths)}")
    flag_rx = summarize_flag_rx_attempts([json.loads(path.read_text(encoding="utf-8")) for path in flag_rx_paths])
    flag_rx_metrics = flag_rx["metrics"]
    flag_rx_ci = wilson_interval(flag_rx["flag_rx_set"], flag_rx["valid_flag_samples"])
    ocd_path = _data_path(root, "evidence") / "raw" / "ocd-message-20261026T173917Z-lane_a.json"
    ocd = json.loads(ocd_path.read_text(encoding="utf-8"))
    ocd_message = bytes.fromhex(ocd["values"]["ASI_OCD_MESSAGE_HEX"])
    ocd_statuses = ocd["values"]["ASI_OCD_STATUS_SEQUENCE"]
    ocd_echoes = [e for e in ocd["events"] if e["kind"] == "echo"]
    ocd_tx = [e for e in ocd["events"] if e["kind"] == "tx"]
    exact_echoes = sum(e["hex"] == tx["hex"] for e, tx in zip(ocd_echoes, ocd_tx))
    ocd_metrics = metric_summary([{"success": ocd.get("exit") == 0, "latency_ms": ocd.get("latency_ms")}])
    status_text = ", ".join(f"{k}={counts.get(k, 0)}" for k in ("PROVEN", "STRONGLY_SUPPORTED", "SUPPORTED", "UNRESOLVED", "DISFAVORED", "FALSIFIED", "BLOCKED"))
    body = f'''# AVR128DA28 Dual-Board UPDI Root-Cause Analysis

Date: 2026-10-27  
Scope: isolated investigation under `experiments/updi_rca/`; no production UPDI or FOTA/application code changed.

## Situation

The historical report recorded 19 missing unheld LDS ACC data responses in 60 attempts (31.67%; Wilson 95% failure interval 21.31%–44.23%) after exact local echo. Its SIB/ASI control transactions remained reliable. In the fresh 38400-baud read-only baseline, Lane A passed SIB {a_sib['successes']}/{a_sib['attempts']} and control {a_ctl['successes']}/{a_ctl['attempts']}; Lane B passed SIB {b_sib['successes']}/{b_sib['attempts']} and control {b_ctl['successes']}/{b_ctl['attempts']}. Lane B failed before a target response, at local echo. These are distinct failure stages.

## Task

Reduce all 168 supplied hypotheses to the narrowest layer supported by reproducible evidence, while preserving firmware and fuse state and separating serial/USB, host TX, local echo, UPDI response, ACC ACK/data, OCD, and runtime/reset behavior.

## Action

- Read `../../../../docs/development/PROMPT.md`, preserved historical evidence, the existing UPDI implementation, and primary Microchip/Linux/upstream references recorded in `../../../../experiments/updi_rca/memory/SOURCES.md`.
- Used exactly two lane workers, one per stable adapter `ID_PATH`. The CP2102 devices share USB serial `0001`; tty names are recorded only as ephemeral locators. Target signature, REVID, and unique serial remain unavailable, so both targets are `UNKNOWN_TARGET`.
- Wrote and observed a failing test before implementing strict raw-event classification and canonical run selection. The baseline probe used two 300-baud BREAK sync bytes followed by SIB or LDCS reads at 38400; no STCS, STS, key, reset, NVM, fuse, or flash writes.
- Captured 100 attempts for each of SIB and selected control reads on each lane. Raw attempt files map to run IDs and stable lane identity. SHA verification: {hash_entries} per-attempt entries, {hash_entries - hash_bad} verified, {hash_bad} failed.
- Final ledgers contain {run_count} run rows and {event_count} event rows; event IDs are unique and map to run IDs. All {source_hash_entries} run sources were hash-checked; {source_hash_bad} mismatches or missing hashes were found.
- The SILENT/HEARTBEAT diagnostic target was built once (SHA-256 `729162b13f65bdcd464a20f8305857dde3d1f91b90e9084ff003a251268ba055`) and not flashed because target identity, current firmware/fuse snapshots, and safe readback gates were unavailable. No fuse write, chip erase, `-F`, BOD change, or new flash write occurred.
- Scored the 168 hypotheses with the explicit additive weights in `../../../../docs/development/PROMPT.md` §12. Scores rank discriminating tests; they are not probabilities. Statuses: {status_text}.

## Result

### Fresh read-only baseline (100 attempts per lane and condition)

| Condition | Lane | Pass/fail | Rate and Wilson 95% success interval | Median / p95 latency |
|---|---|---:|---|---:|
| SIB | A | {a_sib['successes']}/{a_sib['failures']} | {a_sib['success_rate']:.1%}; [{a_sib['wilson_95'][0]:.2%}, {a_sib['wilson_95'][1]:.2%}] | {a_sib['median_latency_ms']:.3f} / {a_sib['p95_latency_ms']:.3f} ms |
| SIB | B | {b_sib['successes']}/{b_sib['failures']} | {b_sib['success_rate']:.1%}; [{b_sib['wilson_95'][0]:.2%}, {b_sib['wilson_95'][1]:.2%}] | {b_sib['median_latency_ms']:.3f} / {b_sib['p95_latency_ms']:.3f} ms |
| Control | A | {a_ctl['successes']}/{a_ctl['failures']} | {a_ctl['success_rate']:.1%}; [{a_ctl['wilson_95'][0]:.2%}, {a_ctl['wilson_95'][1]:.2%}] | {a_ctl['median_latency_ms']:.3f} / {a_ctl['p95_latency_ms']:.3f} ms |
| Control | B | {b_ctl['successes']}/{b_ctl['failures']} | {b_ctl['success_rate']:.1%}; [{b_ctl['wilson_95'][0]:.2%}, {b_ctl['wilson_95'][1]:.2%}] | {b_ctl['median_latency_ms']:.3f} / {b_ctl['p95_latency_ms']:.3f} ms |

Lane A generated 300/300 exact echo frames and 100/100 SIB responses (3,200/3,200 SIB bytes); control reads generated 1,500/1,500 exact echo frames and 1,300/1,300 response bytes. Its control snapshots observed `ASI_OCD_STATUS=0x10` and `ASI_SYS_STATUS=0x82` in all 100 attempts. The masked OCD state was `OCDMV=1`, `OCD_STOPPED=0`; no `ASI_OCD_MESSAGE` bytes were consumed.

### FLAG_RX read-only follow-up

The separate Lane A campaign made {flag_rx_metrics['attempts']} sequential direct LDS reads of GPR2 at `0x001e`, with {flag_rx_metrics['successes']} pass, {flag_rx_metrics['failures']} fail, a {flag_rx_metrics['success_rate']:.1%} read-success rate (Wilson 95% interval [{flag_rx_metrics['wilson_95'][0]:.2%}, {flag_rx_metrics['wilson_95'][1]:.2%}]), and median/p95 latency {flag_rx_metrics['median_latency_ms']:.3f}/{flag_rx_metrics['p95_latency_ms']:.3f} ms. The returned value was `0x03` in {flag_rx['value_counts'].get(0x03, 0)}/{flag_rx['valid_flag_samples']} valid reads; `FLAG_RX` (bit 1) was set in {flag_rx['flag_rx_set']}/{flag_rx['valid_flag_samples']} reads ({flag_rx['flag_rx_set'] / flag_rx['valid_flag_samples']:.1%}, descriptive Wilson interval [{flag_rx_ci[0]:.2%}, {flag_rx_ci[1]:.2%}]) and `FLAG_ENABLE` (bit 0) in {flag_rx['flag_enable_set']}/{flag_rx['valid_flag_samples']}. No virtual-UART payload writes or target writes were made. These sequential reads observe persistent flag state; they do not prove {flag_rx['flag_rx_set']} new RX events or identify who set the flag. The interval is descriptive only because samples were sequential, correlated observations of one uncontrolled state. The inspected upstream `updi_uart.c` defines `FLAG_RX` as “RX buffer full” and clears it only after its `updi_uart_rx()` reads GPIOR3; the LDS probe does not clear it. Current target firmware is unknown, so this is an interpretation aid, not proof that either target runs that handler. `FLAG_RX` is distinct from target-to-host OCD message activity. H131 evidence score: 1 (ranking weight, not probability).

Lane B's 100/100 SIB and 100/100 control attempts failed at `LOCAL_ECHO`; no SIB, LDCS, or target response was reached. For the first BREAK echo, 86/100 SIB and 85/100 control attempts were empty; the remaining first echoes were exact, then the second BREAK echo was absent. The observed TX/echo mismatch is a serial/half-duplex/link-stage failure. It is not the historical exact-echo/target-response failure.

Historical state comparison: prior upstream evidence reported running-state response loss in 19/180 attempts (10.56%) and stopped/programming-held success in 540/540 attempts (Wilson 95% success interval 99.29%–100.00%). The fresh 400-attempt baseline did not control RUNNING versus STOPPED and used only SIB/LDCS; therefore it does not reproduce that ACC state comparison.

No matching kernel CP210x/USB protocol errors were found during the approximately 4m01s Lane B window (n=0 correlated errors). Because each adapter remained paired with its target, these data isolate a lane-bound path, not a physical board or adapter. No controlled adapter crossover, current fuse/firmware comparison, STOPPED/programming-held campaign, independent reset marker, or scope trace exists.

### OCD text and reset interpretation

The supplied terminal transcript contained nine visible `HEYYY fuckkkk` lines followed by host process SIGKILL. A later bounded read-only Lane A snapshot (`{ocd['utc']}`, n=1, {ocd_metrics['successes']}/{ocd_metrics['attempts']} pass, {ocd_metrics['failures']} fail, Wilson 95% success interval [{ocd_metrics['wilson_95'][0]:.2%}, {ocd_metrics['wilson_95'][1]:.2%}], latency {ocd_metrics['median_latency_ms']:.3f} ms, H131 evidence score 1) read `ASI_OCD_STATUS` before each `ASI_OCD_MESSAGE` byte. It captured {len(ocd_message)} bytes, `{ocd_message!r}`, hex `{ocd_message.hex()}`; `OCDMV=1` on all {sum(bool(value & 0x10) for value in ocd_statuses)} pre-byte status reads and the final status was `0x{ocd_statuses[-1]:02x}`. The captured `HEYYY fuckkkk\\r\\n` matches the visible line text. All {len(ocd_tx)}/{len(ocd_tx)} request frames had exact local echo ({exact_echoes}/{len(ocd_echoes)}); 16 status and 15 message responses were received, and `OCD_STOPPED` stayed clear. The read consumed a 15-byte volatile OCD message queue; it made no target register write, UART write, NVM write, fuse write, or flash write. The original nine-line session still has no per-line timing or independent target identity. The host's SIGKILL is not evidence of a target reset. Historical BORF without a new boot marker remains historical state, not proof of a fresh brown-out. No SILENT firmware was flashed, so target-to-host OCD traffic in the intentional no-output condition remains untested.

### Narrowest defensible conclusion

There are at least two distinct observed failure classes: (1) fresh Lane B TX-to-echo failure before target protocol response, N=200 attempts across two conditions with 200/200 failures; and (2) historical unheld LDS exact-echo transactions with 19/60 missing ACC data responses. Neither class identifies a component. The fixed lane pairing prevents board-versus-adapter attribution; the specific board-local power, ground, UPDI, reset, AVR, and assembly causes remain BLOCKED. Current test-priority scores are Reset/watchdog 20, Power/GND 19, AVR silicon 19, Firmware/runtime 15 (H098=13, H102=12), board-side UPDI 10, PCB/assembly 6, adapter/host 1, fuse/environment/methodology 0. These are evidence-weighted test priorities, not probabilities; the investigation proves no single root cause.

### Smallest next action

With boards unpowered, perform one labeled adapter crossover while keeping host, baud, firmware, fuses, and wiring conditions fixed; repeat 100 SIB and 100 control attempts per resulting pairing. This distinguishes a lane-following adapter path from a target-following effect without programming. If failure follows a board, capture simultaneously during attachment and RUN: MCU VDD relative to local GND, adapter-to-board ground offset, RESET at the MCU, UPDI on both sides of the series element, and adapter TX, with low-capacitance probes, at least 100 ms pre/post trigger, and at least 20 MS/s. A stable VDD plus adapter TX without target-side UPDI/echo narrows toward the board-side link; VDD droop aligned with an independently observed reset narrows toward power/reset. Do not infer a specific component from either result alone.

## Evidence files

- Inventory: `device_inventory.csv`
- Run/event records: `runs.csv`, `events.csv`
- Hypotheses and ranking: `hypothesis_status.csv`, `root_cause_ranking.csv`
- Pairwise/fuse/flash records: `pairwise_board_comparison.csv`, `fuse_compare.csv`, `flash_budget.csv`
- Raw evidence and checksums: `../experiment-evidence/raw/`
- Causal map: `../diagrams/cause_evidence_map.svg`
- Handoff: `memory/HANDOFF.md`
'''
    (report_dir / "STAR_RCA.md").write_text(body, encoding="utf-8")
    handoff = f'''# Investigation Handoff

## Current finding

The fresh 38400 baseline has Lane A SIB/control at 100/100 pass each and Lane B at 0/100 each, failing at local echo before target response. Wilson 95% success intervals are Lane A 96.30%–100.00% and Lane B 0.00%–3.70%. This is lane-bound evidence; adapter and target remain paired and target identity is unknown.

Historical unheld LDS evidence remains separate: 19/60 ACC data responses missing after exact echo (31.67% failure, Wilson 95% failure interval 21.31%–44.23%). Do not merge it with the current TX/echo failures.

A separate bounded Lane A OCD snapshot passed 1/1 in 284.286 ms (Wilson 95% success interval 20.65%–100.00%) and read 15 valid message bytes: `HEYYY fuckkkk\\r\\n` (hex `4845595959206675636b6b6b6b0d0a`). Status was 0x10 before every byte and 0x00 after. This matches the visible console line, but the original 9-line terminal session still lacks timestamps and identity. The read consumed the volatile 15-byte message queue.

The separate GPR2 campaign returned `0x03` in 100/100 LDS reads; `FLAG_RX` was set in 100/100 (descriptive Wilson interval 96.30%–100.00%), median/p95 147.597/150.083 ms. No virtual-UART payload was written. This confirms persistent flag state during those sequential observations, not 100 new receive events or the source of the flag. In the inspected upstream virtual-UART helper, `FLAG_RX` means RX buffer full and is cleared when firmware reads GPIOR3; current target firmware is unknown. This register is separate from the captured target-to-host OCD message bytes.

## Safety/state

No current fuse or firmware snapshots were obtained and the built diagnostic image (SHA-256 `729162b13f65bdcd464a20f8305857dde3d1f91b90e9084ff003a251268ba055`) was not flashed. No new flash writes occurred. The prior verified historical write remains in `flash_budget.csv`.

## Next discriminator

Perform one no-programming adapter crossover with boards labeled, then repeat the 100-attempt SIB/control conditions. If the failure follows a target, obtain the simultaneous capture specified in `STAR_RCA.md`: MCU VDD/local GND, ground offset, RESET, UPDI at both sides of the series element, and adapter TX during attach and RUN, low-capacitance probes, >=20 MS/s.

## Interpretation cautions

- The terminal transcript has 9 lines and no per-line timing/identity. A later Lane A read captured 15 bytes matching one line, with OCDMV=1 before each byte and 0x00 afterward; SIGKILL is a host process exit, not a target reset.
- GPR2 `0x001e` returned `0x03` and `FLAG_RX` remained set in 100/100 sequential Lane A reads; this is persistent observed state, not proof of 100 fresh receive events or “always active” behavior. The inspected upstream helper defines it as RX buffer full and clears it only after an RX read; current firmware is unknown. It does not represent the target-to-host OCD output channel.
- `OCDMV=1`, `OCD_STOPPED=0`, raw status 0x10, and SYS_STATUS 0x82 were observed on Lane A. One message snapshot read 15 bytes; intentional no-output SILENT firmware was not flashed, so that condition remains untested.
- BORF without an independently observed new boot marker is historical state.
- All 168 hypothesis rows remain in the inventory; current statuses: {status_text}.
'''
    (root / "memory" / "HANDOFF.md").write_text(handoff, encoding="utf-8")


def finalize(project_root: str | Path) -> dict:
    root = Path(project_root).resolve()
    report_dir = _data_path(root, "reports")
    if root == REPOSITORY_ROOT / "experiments/updi_rca":
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-finalize"
        report_dir = ARTIFACTS_ROOT / "runs" / run_id / "reports"
        report_dir.mkdir(parents=True, exist_ok=False)
        (report_dir / "flash_budget.csv").write_bytes((_data_path(root, "reports") / "flash_budget.csv").read_bytes())
    baseline = _data_path(root, "evidence") / "raw" / "baseline-20261026T1655Z"
    canonical = canonical_attempt_paths(baseline)
    run_rows, raw_to_row = _all_run_rows(root, canonical)
    source_hash_entries, source_hash_bad = _source_hash_summary(root, run_rows)
    if source_hash_entries != len(run_rows) or source_hash_bad:
        raise ValueError(f"expected every run source to have a valid SHA-256, checked {source_hash_entries}/{len(run_rows)} with {source_hash_bad} failures")
    events = _event_rows(root, canonical, raw_to_row)
    if len({event["event_id"] for event in events}) != len(events):
        raise ValueError("event IDs must be unique")
    if {event["run_id"] for event in events} - {run["run_id"] for run in run_rows}:
        raise ValueError("every event must map to a run record")
    write_csv(report_dir / "runs.csv", RUN_COLUMNS, run_rows)
    write_csv(report_dir / "events.csv", EVENT_COLUMNS, events)
    write_csv(report_dir / "pairwise_board_comparison.csv", PAIRWISE_COLUMNS, _pairwise_rows(canonical))

    summaries = {}
    for key, paths in canonical.items():
        attempts = []
        for path in paths:
            item = json.loads(path.read_text(encoding="utf-8"))
            attempts.append({"success": item.get("exit") == 0, "latency_ms": item.get("latency_ms"), "failure_stage": _failure_stage(item)})
        summaries[key] = metric_summary(attempts)

    _, status_counts = _update_hypotheses(root, report_dir)
    _write_fuse_comparison(root, report_dir)
    with (report_dir / "flash_budget.csv").open(newline="", encoding="utf-8") as stream:
        flash_rows = list(csv.DictReader(stream))
    if tuple(flash_rows[0].keys()) != FLASH_COLUMNS or len(flash_rows) != 3:
        raise ValueError("flash budget must preserve both zero-write lanes and one historical write")
    hash_entries, hash_bad = _hash_summary(root)
    if hash_entries != 400 or hash_bad:
        raise ValueError(f"expected 400 valid baseline hashes, got {hash_entries} entries and {hash_bad} failures")
    _write_report(root, summaries, status_counts, hash_entries, hash_bad, source_hash_entries, source_hash_bad, len(run_rows), len(events), report_dir)
    return {"runs": len(run_rows), "events": len(events), "hypotheses": sum(status_counts.values()), "statuses": dict(status_counts), "hash_entries": hash_entries, "hash_bad": hash_bad, "source_hash_entries": source_hash_entries, "source_hash_bad": source_hash_bad}

