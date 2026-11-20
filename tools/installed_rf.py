"""Run the installed SRAM-only DATA/ACK and controlled DATA/NACK bench."""

from __future__ import annotations

import argparse
import hashlib
import json
import queue
import re
import time
import tomllib
from collections import Counter
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from tools import rf_proof as rf
from tools.device_detection.evidence import DeviceRole
from tools.device_detection.hardware_registry import hardware_ports, load_hardware_registry

if TYPE_CHECKING:
    from collections.abc import Callable

TRIALS = 10
STDOUT_STREAM = "stdout"
RX_READY_MARKER = "RX_READY"
TRANSACTION_FAILED_MARKER = "TRANSACTION_FAILED"


def capture_event_phase(*, after_rf_reopen: bool, ready_barrier_seen: bool) -> str:
    """Classify buffered reconnect lines separately from events after readiness."""
    if ready_barrier_seen:
        return "live_after_ready_barrier"
    if after_rf_reopen:
        return "buffered_after_rf_reopen"
    return "unclassified_before_ready"


class Capture:
    """Own both UPDI monitors and retain the connection provenance of each line."""

    def __init__(
        self, proof: rf.ProofRun, *, observe: Callable[[str, str], None] | None = None
    ) -> None:
        """Create a shared event stream without opening either adapter."""
        self.proof = proof
        self.observe = observe
        self.incoming: queue.Queue[tuple[str, str, bytes | None]] = queue.Queue()
        self.monitors: dict[str, rf.Json] = {}
        self.ports = hardware_ports(rf.ROOT / "config" / "current_hardware.json")
        self.generations = dict.fromkeys(self.ports, 0)
        self.connections: dict[str, tuple[str, int]] = {}
        self.lines: list[str] = []
        self.line_segments: list[tuple[str, int, str]] = []
        self.records: list[rf.Json] = []
        self.after_rf: set[tuple[str, int]] = set()
        self.ready_barriers: set[tuple[str, int]] = set()
        self.reset_connections: set[tuple[str, int]] = set()
        self.verified_campaigns: set[str] = set()

    def record(self, role: str, stream: str, line: str, generation: int) -> None:
        """Journal host receipt time separately from embedded firmware time."""
        delivery = "after_reconnect" if generation > 1 else "initial_connection"
        if (role, generation) in self.after_rf:
            delivery = "after_rf_reopen"
        row = {
            "role": role,
            "stream": stream,
            "line": line,
            "connection": generation,
            "delivery": delivery,
            "phase": capture_event_phase(
                after_rf_reopen=(role, generation) in self.after_rf,
                ready_barrier_seen=(role, generation) in self.ready_barriers,
            ),
            "received_utc": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "received_monotonic_ns": time.monotonic_ns(),
        }
        with (self.proof.run_dir / "events.jsonl").open("a") as out:
            out.write(json.dumps(row) + "\n")
        self.records.append(row)
        if stream == STDOUT_STREAM and line.startswith(f"[{role.upper()}] "):
            if line.startswith(f"[{role.upper()}] BOOT "):
                segment = (role, generation)
                if segment in self.ready_barriers or segment in self.after_rf:
                    self.reset_connections.add(segment)
                self.ready_barriers.discard(segment)
            if self.observe is not None:
                self.observe(role.upper(), line)
            self.lines.append(line)
            self.line_segments.append((role, generation, line))

    def connect(self, role: str, *, after_rf: bool = False) -> None:
        """Open a new capture segment without explicitly resetting the target."""
        self.close(role)
        self.generations[role] += 1
        generation = self.generations[role]
        label = f"{role}-{generation}"
        self.connections[label] = (role, generation)
        if after_rf:
            self.after_rf.add((role, generation))
        self.monitors[role] = rf.start_rf_monitor(
            self.proof, label, self.ports[role], self.incoming
        )
        self.record(role, "capture_open", label, generation)

    def close(self, role: str) -> int | None:
        """Release a monitor while leaving already queued output attributable."""
        generation = self.generations[role]
        monitor = self.monitors.pop(role, None)
        try:
            if monitor is None:
                return None
            code = rf.stop_rf_monitor(monitor)
            self.drain_pending()
            self.record(role, "capture_close", str(code), generation)
            return code
        finally:
            self.ready_barriers.discard((role, generation))

    def disconnected(self, role: str) -> bool:
        """Return whether the active monitor can no longer take commands."""
        return role not in self.monitors or self.monitors[role]["process"].poll() is not None

    def send(self, role: str, command: str) -> int:
        """Queue one command once. A DATA command is never replayed on disconnect."""
        self.drain_pending()
        if self.disconnected(role):
            raise OSError(f"{role}: monitor disconnected before {command}")
        segment = (role, self.generations[role])
        if command == "S" and segment not in self.ready_barriers:
            raise OSError(f"{role}: DATA requires fresh RX readiness")
        process = self.monitors[role]["process"]
        if process.stdin.write(command.encode("ascii")) != 1:
            msg = f"{role}: command {command} was not fully queued"
            raise OSError(msg)
        process.stdin.flush()
        self.record(role, "host", command, self.generations[role])
        return len(self.lines)

    def drain_one(self, timeout: float) -> None:
        """Consume one event while retaining lines from previously closed segments."""
        try:
            label, stream, raw = self.incoming.get(timeout=timeout)
        except queue.Empty:
            return
        role, generation = self.connections[label]
        if raw is not None:
            self.record(role, stream, raw.decode("ascii", errors="replace").strip(), generation)

    def drain_pending(self) -> None:
        """Journal queued records before indexing a new command's response."""
        for _ in range(self.incoming.qsize()):
            self.drain_one(0)

    def fresh_lines(self, role: str, start: int) -> list[str]:
        """Return addressed output from the current monitor generation."""
        return [
            line
            for origin, generation, line in self.line_segments[start:]
            if origin == role and generation == self.generations[role]
        ]

    def wait(
        self,
        predicate: Callable[[], object],
        timeout: float,
        *,
        park_role: str | None = None,
        recover_tracker: bool = False,
    ) -> bool:
        """Recover only the expected post-RF Tracker capture without sending commands."""
        deadline = time.monotonic() + timeout
        reconnects = 0
        while True:
            for role in (park_role,) if park_role else ("gateway", "receiver"):
                if role not in self.monitors and role != park_role:
                    continue
                segment = (role, self.generations[role])
                if not park_role and segment in self.reset_connections:
                    raise OSError(f"{role}: MCU reset observed")
                if self.disconnected(role):
                    self.ready_barriers.discard(segment)
                    if recover_tracker and role == "receiver" and reconnects < 2:
                        self.connect(role, after_rf=True)
                        if segment in self.reset_connections:
                            raise OSError(f"{role}: MCU reset observed")
                        reconnects += 1
                    else:
                        raise OSError(f"{role}: monitor disconnected")
            if predicate():
                return True
            if time.monotonic() >= deadline:
                return False
            self.drain_one(0.1)

    def exchange(self, start: int, *, nack: bool) -> rf.Json | None:
        """Assess current Gateway and post-RF Tracker evidence after the DATA trigger."""
        lines = [
            line
            for role, generation, line in self.line_segments[start:]
            if (role == "gateway" and generation == self.generations[role])
            or (role, generation) in self.after_rf
        ]
        return rf.assess_installed_exchange(lines, nack)

    def park(self, role: str) -> None:
        """Use a fresh monitor for standby recovery if the current connection was lost."""
        if self.disconnected(role):
            self.connect(role)
        self.marker(role, "P", "PARKED E=0")

    def marker(self, role: str, command: str, marker: str) -> None:
        """Send a control and require its role-specific completion."""
        start = self.send(role, command)
        expected_line = f"[{role.upper()}] {marker}"
        if not self.wait(
            lambda: expected_line in self.fresh_lines(role, start),
            20,
            park_role=role if marker == "PARKED E=0" else None,
        ):
            raise TimeoutError(f"{role}: missing fresh {marker} after {command}")
        segment = (role, self.generations[role])
        if marker == RX_READY_MARKER:
            self.ready_barriers.add(segment)
        elif marker == "PARKED E=0":
            self.ready_barriers.discard(segment)


def verify_snapshots(snapshot: Path, receipt_path: Path) -> dict[str, rf.Json]:
    """Require enrolled serials and full saved Flash matching the known bench pair."""
    receipt = json.loads(receipt_path.read_text())
    if (
        not isinstance(receipt, dict)
        or receipt.get("origin") != "PHYSICAL_UPDI"
        or not isinstance(receipt.get("images"), dict)
    ):
        raise ValueError("Expected a physical UPDI upload receipt")
    images: dict[str, rf.Json] = receipt["images"]
    registry = load_hardware_registry(rf.ROOT / "config" / "current_hardware.json")
    ports = hardware_ports(rf.ROOT / "config" / "current_hardware.json")
    manifest = json.loads((rf.ROOT / "generated/lora_manifest.json").read_text())
    archive = receipt_path.parent
    for role, board_role, prefix, environment in (
        (DeviceRole.GATEWAY, "sender", "gateway", "sender_hello"),
        (DeviceRole.TRACKER, "receiver", "receiver", "receiver"),
    ):
        profile = manifest["device_profiles"][manifest["boards"][board_role]["mcu"]]
        message = f"{role.value.title()}: readback differs from the reviewed installed bench image"
        try:
            image = images[prefix.upper()]
            # Production readbacks and the standalone snapshot command use different names.
            flash, serial, signature, fuses = (
                (snapshot / live).read_bytes()
                if (snapshot / live).exists()
                else (snapshot / standalone).read_bytes()
                for live, standalone in (
                    (f"{prefix}-live-flash.bin", f"{board_role}-flash.bin"),
                    (f"{prefix}-live-serial.bin", f"{board_role}-sernum.bin"),
                    (f"{prefix}-live-signature.bin", f"{board_role}-signature.bin"),
                    (f"{prefix}-live-fuses.bin", f"{board_role}-fuses.bin"),
                )
            )
            fuse_archive = archive / f"{prefix}-live-fuses.bin"
            if not fuse_archive.exists():
                fuse_archive = archive / f"{environment}-after-page-write-fuses.bin"
            start, end = image["start"], image["end"]
            if (
                len(flash) != profile["flash_bytes"]
                or flash != (archive / f"{prefix}-live-flash.bin").read_bytes()
                or serial != (archive / f"{prefix}-live-serial.bin").read_bytes()
                or serial != registry[role].serial_number
                or serial.hex() != image["serial_number"]
                or signature != (archive / f"{prefix}-live-signature.bin").read_bytes()
                or signature.hex() != image["signature"]
                or signature.hex() != profile["signature_hex"]
                or len(fuses) != 16
                or fuses != fuse_archive.read_bytes()
                or image["environment"] != environment
                or image["port"] != ports[prefix]
                or image["verified"] is not True
                or type(start) is not int
                or type(end) is not int
                or not 0 <= start < end <= len(flash)
                or hashlib.sha256(flash[start:end]).hexdigest() != image["readback_region_sha256"]
                or not re.fullmatch(r"[0-9a-f]{64}", image["build_id"])
            ):
                raise ValueError(message)
        except (OSError, KeyError, TypeError) as exc:
            raise ValueError(message) from exc
    return images


def verify_console(capture: Capture, role: str, image: rf.Json, profile: rf.Json) -> None:
    """Require the live build ID and matching radio profile before any DATA trigger."""
    start = capture.send(role, "?")
    label = role.upper()

    def matches() -> bool:
        """Check live build identity, protocol, silicon version and PHY together."""
        lines = capture.fresh_lines(role, start)
        return (
            {line for line in lines if line.startswith(f"[{label}] BUILD_ID=")}
            == {f"[{label}] BUILD_ID={image['build_id']}"}
            and f"[{label}] PROTOCOL_VERSION=2" in lines
            and f"[{label}] RADIO_SPI_VERSION=0x12" in lines
            and rf.radio_startup_matches(lines, label, profile, allow_rearm=True)
        )

    if not capture.wait(matches, 24):
        msg = f"{role}: live build ID, protocol or radio profile could not be verified"
        raise TimeoutError(msg)


def gateway_finished(capture: Capture, start: int) -> bool:
    """Wait for the observed Gateway terminal outcome before reopening Tracker UPDI."""
    return any(
        line.startswith(("[GATEWAY] ACK_ACCEPTED ", "[GATEWAY] TRANSACTION_FAILED "))
        for line in capture.fresh_lines("gateway", start)
    )


def unplanned_transaction_failures(lines: list[str], planned_campaigns: set[str]) -> list[str]:
    """Return transaction-failure events whose campaign is outside this run's cases."""
    failures = []
    for line in lines:
        if TRANSACTION_FAILED_MARKER not in line:
            continue
        match = re.search(r"\bSID=([0-9A-Fa-f]+)\b", line)
        campaign = match.group(1).upper() if match is not None else None
        if campaign not in planned_campaigns:
            failures.append(line)
    return failures


def capture_diagnostics(lines: list[str]) -> dict[str, rf.Json]:
    """Summarize only status, IRQ, signal, and airtime values present in captured lines."""
    radio_errors: Counter[int] = Counter()
    irq_flags: set[int] = set()
    rssi_dbm: list[float] = []
    snr_db: list[float] = []
    airtime_us: list[int] = []
    for line in lines:
        for value in re.findall(r"\bE=(-?\d+)\b", line):
            radio_errors[int(value)] += 1
        for value in re.findall(r"\bIRQ_FLAGS=(0x[0-9A-Fa-f]+|\d+)\b", line):
            irq_flags.add(int(value, 0))
        for key, values in (("RSSI_DBM", rssi_dbm), ("SNR_DB", snr_db)):
            values.extend(
                float(value) for value in re.findall(rf"\b{key}=(-?\d+(?:\.\d+)?)\b", line)
            )
        airtime_us.extend(int(value) for value in re.findall(r"\bAIRTIME_US=(\d+)\b", line))
    return {
        "radio_error_counts": {str(code): count for code, count in sorted(radio_errors.items())},
        "irq_flags_seen": sorted(irq_flags) or None,
        "rssi_dbm": sum(rssi_dbm) / len(rssi_dbm) if rssi_dbm else None,
        "snr_db": sum(snr_db) / len(snr_db) if snr_db else None,
        "airtime_us": sum(airtime_us) if airtime_us else None,
    }


def exchange_once(
    capture: Capture, images: dict[str, rf.Json], profile: rf.Json, *, nack: bool = False
) -> rf.Json:
    """Prove both radios ready, release Tracker UPDI for RF, then verify its buffered evidence."""
    for role in ("receiver", "gateway"):
        capture.marker(role, "R", RX_READY_MARKER)
    capture.send("receiver", "N" if nack else "A")
    for role in ("receiver", "gateway"):
        verify_console(capture, role, images[role.upper()], profile)
    capture.drain_pending()
    for role in ("receiver", "gateway"):
        if (role, capture.generations[role]) not in capture.ready_barriers or capture.disconnected(
            role
        ):
            raise OSError(f"{role}: lost verified readiness before DATA")
    receiver_segment = ("receiver", capture.generations["receiver"])
    try:
        clean_release = capture.close("receiver") == 0
        capture.drain_pending()
        if not clean_release or receiver_segment in capture.reset_connections:
            raise OSError("Tracker monitor release failed or MCU reset before DATA")
        start = capture.send("gateway", "S")
        if not capture.wait(partial(gateway_finished, capture, start), 30):
            raise TimeoutError("Gateway did not report a terminal DATA outcome")
    finally:
        capture.connect("receiver", after_rf=True)
    expected_attempts = 2 if nack else 1
    assess = partial(capture.exchange, start, nack=nack)
    capture.wait(assess, 45, recover_tracker=True)
    result = assess()
    if result is None or result["attempts"] != expected_attempts:
        raise TimeoutError("Incomplete two-sided DATA/ACK evidence or unexpected retry count")
    campaign = str(result["campaign"])
    if campaign in capture.verified_campaigns:
        raise ValueError(f"Repeated RF campaign {campaign}")
    capture.verified_campaigns.add(campaign)
    return result


def run(capture: Capture, images: dict[str, rf.Json], profile: rf.Json) -> int:
    """Run each bounded case sequentially and park both radios on exit."""
    outcomes: list[rf.Json] = []
    parked = {}
    error = None
    unplanned_failures: list[str] = []
    unplanned_failure_events: list[rf.Json] = []
    try:
        for role in ("receiver", "gateway"):
            capture.connect(role)
        for nack in (False, True):
            for trial in range(1, TRIALS + 1):
                result = exchange_once(capture, images, profile, nack=nack)
                outcomes.append(
                    {"case": "NACK" if nack else "ACK", "trial": trial, "result": result}
                )
                capture.proof.note("trials.json", json.dumps(outcomes, indent=2) + "\n")
    except (OSError, ValueError) as exc:
        error = str(exc)
    finally:
        planned_campaigns = {
            str(outcome["result"]["campaign"]).upper()
            for outcome in outcomes
            if outcome.get("result") is not None
        }
        unplanned_failures = unplanned_transaction_failures(capture.lines, planned_campaigns)
        unplanned_failure_events = [
            row
            for row in capture.records
            if row["line"] in unplanned_failures and TRANSACTION_FAILED_MARKER in row["line"]
        ]
        if unplanned_failures and error is None:
            error = "unplanned transaction failure outside the scheduled RF cases"
        for role in capture.ports:
            try:
                capture.park(role)
                parked[role] = True
            except OSError:
                parked[role] = False
            finally:
                capture.close(role)
        owners = rf.check_port_owners(capture.proof, "postflight")
        diagnostics = capture_diagnostics(capture.lines)
        report = {
            "trials": outcomes,
            "error": error,
            "unplanned_failures": unplanned_failures,
            "unplanned_failure_events": unplanned_failure_events,
            "parked": parked,
            "port_owners": owners,
            **diagnostics,
        }
        capture.proof.note("summary.json", json.dumps(report, indent=2) + "\n")
    return int(error is not None or not all(parked.values()) or bool(owners))


def main() -> int:
    """Validate inputs and explicit RF authorization before opening monitors."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readback", required=True, type=Path)
    parser.add_argument("--historical-receipt", required=True, type=Path)
    parser.add_argument("--authorize-rf-test", action="store_true", required=True)
    args = parser.parse_args()
    images = verify_snapshots(args.readback, args.historical_receipt)
    config = tomllib.loads((rf.ROOT / "config/radio_915.toml").read_text())["radio"]
    profile = {"frequency_mhz": config["frequency_hz"] / 1_000_000, **config}
    stamp = datetime.now(UTC).strftime("sram-rf-%Y%m%dT%H%M%S.%fZ")
    proof = rf.ProofRun(rf.ROOT / "artifacts/rf-debug" / stamp)
    print(proof.run_dir, flush=True)
    if rf.check_port_owners(proof, "preflight"):
        return 2
    return run(Capture(proof), images, profile)


if __name__ == "__main__":
    raise SystemExit(main())
