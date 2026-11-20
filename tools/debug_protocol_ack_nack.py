"""Production LoRa DATA/ACK/NACK checkpoints with physical UPDI and RF evidence."""

from __future__ import annotations

import argparse
import contextlib
import json
import queue
import re
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

from serial.tools import list_ports

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

from tools import production_bench as bench
from tools import rf_proof as rf
from tools.config.application_config import load as load_application_config
from tools.device_detection.firmware_identity import RUNTIME_IDENTITY_MATCH
from tools.device_detection.hardware_registry import hardware_ports
from tools.lora_chat.protocol import (
    RETRY_EVENTS,
    TIMEOUT_EVENTS,
    DeviceRole as ChatDeviceRole,
    DeviceEvent as ChatDeviceEvent,
    EventName as ChatEventName,
    RoundTripContext,
    encode_interactive_command,
    parse_firmware_event,
    verify_round_trip,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

Json = dict[str, Any]
TRIALS = 10
BOARD_COUNT = 2

STEPS = (
    "Detect, build, and prepare",
    "Boot and radio self-test",
    "Prove the RF link",
    "Verify DATA",
    "Verify ACK",
    "Verify NACK and retry",
    "Verify negative cases and recovery",
    "Park and report",
)
HELP = "ENTER = next/retry failed step | r = retry | b = back\nl = logs | h = help | q = quit"


def discover_ports(
    stable: Iterable[str | Path] | None = None, devices: Iterable[str | Path] | None = None
) -> list[str]:
    """Prefer persistent USB identifiers; never infer a firmware role from tty numbers."""
    if stable is None:
        stable = sorted(Path("/dev/serial/by-id").glob("*")) + sorted(
            Path("/dev/serial/by-path").glob("*")
        )
    if devices is None:
        devices = [port.device for port in list_ports.comports()]
    found: dict[str, str] = {}
    for port in [*stable, *devices]:
        found.setdefault(str(Path(port).resolve()), str(port))
    return list(found.values())


def firmware_role(text: str, images: dict[str, Json]) -> str | None:
    """Require the actual firmware role and exact current build ID."""
    roles = [
        role
        for role, image in images.items()
        if f"[{role}] BUILD_ID={image['build_id']}" in text.splitlines()
        and f"[{role}] RADIO_" in text
    ]
    return roles[0] if len(roles) == 1 else None


def assess(
    rows: list[Json],
    images: dict[str, Json],
    run_id: str,
    *,
    nack: bool = False,
    sequence: int | None = None,
) -> Json:
    """Use the proof runner's two-sided packet/sequence/identity/retry checks."""
    result = rf.validate_stable_transport(
        rows, images, run_id, "T02" if nack else "T01", bench_sequence=sequence
    )
    result.update(
        status="PASS" if result["valid"] else "FAIL",
        detail="DATA → NACK → RETRY → ACK" if nack else "DATA → ACK",
    )
    if not result["valid"]:
        result["detail"] = "; ".join(result["issues"])
    return result


def assess_exhaustion(rows: list[Json], max_attempts: int, sequence: int = 1) -> Json:
    """Require explicit bounded failure for an intentional no-response test."""
    config = json.loads((ROOT / "config/lora_system.json").read_text())
    protocol = config["protocol"]
    packet = re.compile(
        r"^\[GATEWAY\] ([A-Z_]+)(?: SID=[0-9A-F]{4})? T=(\d+) TYPE=(\d+) Q=(\d+) E=(-?\d+)$"
    )
    events = [
        match.groups()
        for row in rows
        if row["role"] == "GATEWAY" and (match := packet.fullmatch(row["line"]))
    ]
    clean_events = all(
        int(type_) == protocol["data_type"]
        and int(observed_sequence) == sequence
        and int(error) == (-1 if name == "TRANSACTION_FAILED" else 0)
        for name, _, type_, observed_sequence, error in events
    )

    def count(role: str, event: str) -> int:
        return sum(
            row["role"] == role and row["line"].startswith(f"[{role}] {event} ") for row in rows
        )

    attempts = count("GATEWAY", "DATA_TX_BEGIN")
    retries = count("GATEWAY", "RETRY_SCHEDULED")
    valid = (
        clean_events
        and attempts == max_attempts
        and count("GATEWAY", "DATA_TX_DONE") == attempts
        and retries == attempts - 1
        and count("GATEWAY", "TRANSACTION_FAILED") == 1
        and not count("GATEWAY", "ACK_ACCEPTED")
        and not any(" BOOT " in row["line"] for row in rows)
        and all(
            any(row["line"] == f"[{role}] PARKED E=0" for row in rows)
            for role in ("GATEWAY", "RECEIVER")
        )
    )
    return {
        "status": "PASS" if valid else "FAIL",
        "attempts": attempts,
        "retries": retries,
        "timeouts": retries + 1,
        "detail": "Intentional retry exhaustion: "
        + ("bounded explicit failure" if valid else "expected bounded failure evidence missing"),
    }


def assess_control_fault(rows: list[Json], fault: str, sequence: int) -> Json:
    """Require the transmitted bad ACK to be ignored and one valid ACK accepted."""
    packet = re.compile(
        r"^\[(GATEWAY|RECEIVER)\] ([A-Z_]+) SID=([0-9A-F]{4}) T=(\d+) "
        r"TYPE=(\d+) Q=(\d+) E=0$"
    )
    events: dict[tuple[str, str], list[tuple[int, int, int]]] = {}
    for row in rows:
        match = packet.fullmatch(row["line"])
        if match and row["role"] == match[1]:
            role, name, campaign, _, packet_type, observed_sequence = match.groups()
            events.setdefault((role, name), []).append(
                (int(campaign, 16), int(packet_type), int(observed_sequence))
            )
    accepted = events.get(("GATEWAY", "ACK_ACCEPTED"), [])
    spec = json.loads((ROOT / "config/lora_system.json").read_text())["protocol"]
    valid = False
    if len(accepted) == 1 and accepted[0][1:] == (spec["ack_type"], sequence):
        campaign, ack_type, _ = accepted[0]
        next_campaign, next_sequence = campaign % 65535 + 1, sequence % 255 + 1
        ignored = {
            "C": (next_campaign, ack_type, sequence),
            "Q": (campaign, ack_type, next_sequence),
            "U": accepted[0],
        }[fault]
        data = (campaign, spec["data_type"], sequence)
        duplicate = fault == "U"
        expected_replies = accepted if duplicate else [ignored, accepted[0]]
        valid = (
            campaign != 0
            and events.get(("GATEWAY", "CONTROL_IGNORED")) == [ignored]
            and events.get(("GATEWAY", "ACK_RX")) == accepted
            and events.get(("GATEWAY", "DATA_TX_DONE")) == [data] * (1 if duplicate else 2)
            and events.get(("RECEIVER", "DATA_VALIDATED")) == [data]
            and events.get(("RECEIVER", "ACK_TX_DONE")) == expected_replies
            and events.get(("RECEIVER", "DATA_DUP"), []) == ([] if duplicate else [data])
            and events.get(("RECEIVER", "ACK_DUP_TX_DONE"), []) == (accepted if duplicate else [])
            and not any(" LOG_OVERFLOW " in row["line"] or " BOOT " in row["line"] for row in rows)
        )
    return {
        "status": "PASS" if valid else "FAIL",
        "detail": f"Control test {fault}: "
        + ("one matching ACK accepted." if valid else "evidence mismatch."),
    }


def assess_probe(rows: list[Json], protocol: Json, sequence: int, *, malformed: bool) -> Json:
    """Correlate one probe TX, the Tracker's boundary, and any reply attempts."""
    transmitted = re.compile(
        r"^\[GATEWAY\] BENCH_PROBE_BEGIN SID=([0-9A-F]{4}) Q=(\d+) DST=(\d+) APP=(\d+)$"
    )
    gateway = [row["line"] for row in rows if row["role"] == "GATEWAY"]
    tracker = [row["line"] for row in rows if row["role"] == "RECEIVER"]
    probes = [match for line in gateway if (match := transmitted.fullmatch(line))]
    expected = "DATA_REJECTED_PAYLOAD" if malformed else "RX_DISCARD_DEST"
    replies = [line for line in tracker if re.search(r" (?:ACK|NACK)_TX_(?:BEGIN|DONE) ", line)]
    valid = False
    if len(probes) == 1:
        campaign, observed_sequence, destination, size = probes[0].groups()
        data_type = protocol["data_type"]
        nack_type = protocol["nack_type"]
        discard = (
            rf"^\[RECEIVER\] {expected} SID={campaign} T=\d+ TYPE={data_type} Q={sequence} E=0$"
        )
        nack = (
            rf"^\[RECEIVER\] NACK_TX_(BEGIN|DONE) SID={campaign} T=\d+ "
            rf"TYPE={nack_type} Q={sequence} E=0$"
        )
        matched_replies = [match[1] for line in replies if (match := re.fullmatch(nack, line))]
        expected_replies = ["BEGIN", "DONE"] if malformed else []
        valid = (
            int(campaign, 16) != 0
            and int(observed_sequence) == sequence
            and int(size) == len(protocol["payload"]) - int(malformed)
            and (int(destination) == protocol["receiver_address"]) == malformed
            and int(destination) not in (protocol["sender_address"], 255)
            and gateway.count("[GATEWAY] BENCH_PROBE_DONE E=1") == 1
            and sum(bool(re.fullmatch(discard, line)) for line in tracker) == 1
            and len(replies) == len(matched_replies)
            and matched_replies == expected_replies
        )
    valid = valid and not any(
        token in line
        for line in tracker + gateway
        for token in (
            " BOOT ",
            " LOG_OVERFLOW ",
            " TRANSACTION_FAILED ",
            " ACK_ACCEPTED ",
            " DATA_VALIDATED ",
        )
    )
    return {
        "status": "PASS" if valid else "FAIL",
        "detail": f"{expected} with {len(replies)} reply events.",
    }


class Session:
    """Persist every actual response and checkpoint; host timestamps are receipt times."""

    def __init__(self, path: Path, *, dry_run: bool = False) -> None:
        """Create one isolated evidence directory."""
        self.path = path
        self.mode = "DRY RUN" if dry_run else "REAL RF"
        path.mkdir(parents=True, exist_ok=False)
        self.step = 0
        self.rows: list[Json] = []
        self.results: dict[str, Json] = {}
        self.lock = threading.RLock()
        for name in ("gateway.log", "receiver.log", "events.jsonl"):
            (path / name).touch()

    def record(
        self, role: str, line: str, status: str = "OBSERVED", error: str | None = None
    ) -> None:
        """Save an observation without treating it as a passing transaction."""
        sequence = re.search(r"\bQ=(\d+)", line)
        payload = re.search(r"\bHEX=([0-9A-Fa-f]*) ASCII=(.*)", line)
        row: Json = {
            "timestamp": datetime.now(UTC).isoformat(),
            "role": role,
            "step": self.step + 1,
            "event_type": line.removeprefix(f"[{role}] ").split(" ")[0],
            "sequence": int(sequence[1]) if sequence else None,
            "payload": payload[2] if payload else None,
            "response": line,
            "status": status,
            "error": error,
            "line": line,
            "observed_monotonic_ns": time.monotonic_ns(),
        }
        payload_sequence = re.search(r"\bS=([0-9A-Fa-f]+)", line)
        if payload and payload_sequence:
            row["sequence"] = int(payload_sequence[1], 16)
        with self.lock:
            self.rows.append(row)
            with (self.path / "events.jsonl").open("a") as file:
                file.write(json.dumps(row) + "\n")
            if role in ("GATEWAY", "RECEIVER"):
                with (self.path / f"{role.lower()}.log").open("a") as file:
                    file.write(f"{row['timestamp']} {line}\n")

    def snapshot(self, start: int = 0) -> list[Json]:
        """Read a consistent slice while serial capture continues."""
        with self.lock:
            return list(self.rows[start:])

    def finish(self) -> None:
        """Write current results, including every unexecuted checkpoint."""
        with self.lock:
            summary: Json = {
                "mode": self.mode,
                "steps": {
                    str(index + 1): self.results.get(
                        str(index + 1), {"status": "NOT RUN", "detail": "not executed"}
                    )
                    for index in range(len(STEPS))
                },
                "host_timestamps": "UART receipt times, not RF airtime",
                "events": len(self.rows),
            }
            (self.path / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            report = ["# Production LoRa debugger", "", f"Mode: {self.mode}", ""]
            report += [
                f"- Step {index}: {result['status']} — {result['detail']}"
                for index, result in summary["steps"].items()
            ]
            report += [
                "",
                "Raw evidence: gateway.log, receiver.log, events.jsonl.",
                "Unexecuted checkpoints are NOT RUN; a connection is not RF proof.",
            ]
            (self.path / "report.md").write_text("\n".join(report) + "\n")


@contextlib.contextmanager
def hardware_output(log: Session, *, verbose: bool) -> Iterator[None]:
    """Leave complete command output on disk; mirror it only in verbose mode."""
    if verbose:
        yield
        return
    with (
        (log.path / "preflight.log").open("a") as file,
        contextlib.redirect_stdout(file),
        contextlib.redirect_stderr(file),
    ):
        yield


class Hardware:
    """Own the physical production monitors and their readback evidence."""

    def __init__(self, log: Session, out: TextIO = sys.stdout) -> None:
        """Use the existing project's serial and proof mechanisms."""
        self.log, self.out = log, out
        self.monitors: dict[str, Json] = {}
        self.incoming: queue.Queue[tuple[str, str, bytes | None]] = queue.Queue()
        self.stop = threading.Event()
        self.reader: threading.Thread | None = None
        self.images: dict[str, Json] = {}
        self.exchange_rows: list[Json] = []
        self.first_exchange: Json | None = None
        self.first_rows: list[Json] = []
        self.fault: str | None = None
        self.run_id = log.path.name
        self.config = json.loads((ROOT / "config/lora_system.json").read_text())
        self.version_probes = load_application_config()["startup"]["version_probe_attempts"]
        self.proof: rf.ProofRun | None = None
        self.transmitting = False
        self.closing = False
        self.bench_active = False
        self.port_overrides: dict[str, str | None] = {}
        self.no_flash = True
        self.write_approval: Path | None = None
        self.authorize_rf = False
        self.verbose = False
        self.sequence = self.config["protocol"]["sequence"]
        self.effective = ""
        self.manifest: Json = {}
        self.layouts: dict[str, Json] = {}
        self.usb_present: set[str] = set()
        self.stage = "NOT_STARTED"
        self.stage_error: str | None = None

    def connect(self) -> Json:
        """Verify devices and installed images before opening firmware consoles."""
        self.close()
        self.first_exchange = None
        self.first_rows = []
        self.stage = "DEVICE_DISCOVERY"
        self.stage_error = None
        try:
            self._select_ports()
            return self._connect_verified()
        except (OSError, ValueError, KeyError, RuntimeError) as error:
            self.stage_error = str(error)
            raise

    def _select_ports(self) -> None:
        """Accept aliases of both enrolled adapters; live serial confirms the role."""
        ports = {Path(port).resolve() for port in discover_ports()}
        enrolled_ports = hardware_ports(ROOT / "config" / "current_hardware.json")
        if len(ports) < len(enrolled_ports):
            msg = f"Need two available serial devices; found {len(ports)}"
            raise bench.BenchBlockedError(msg)
        for role, configured in enrolled_ports.items():
            enrolled = Path(configured).resolve()
            selected = Path(self.port_overrides.get(role) or configured).resolve()
            if selected != enrolled or selected not in ports:
                msg = f"{role} override does not resolve to its enrolled USB adapter."
                raise bench.BenchBlockedError(msg)

    def read_chat_images(self) -> dict[str, Json]:
        """Gather read-only diagnostics independently on available enrolled ports."""
        self.images = {}
        ports = {Path(port).resolve() for port in discover_ports()}
        self.usb_present = {
            role for role, port in hardware_ports(ROOT / "config/current_hardware.json").items()
            if Path(port).resolve() in ports
        }
        self.proof = rf.ProofRun(self.log.path / f"preparation-{time.monotonic_ns()}")
        self.stage = "FIRMWARE_BUILD"
        with hardware_output(self.log, verbose=self.verbose):
            self.effective, self.manifest = bench.build(self.proof)
        self.stage = "FLASH_READBACK"
        busy = set(rf.check_port_owners(self.proof, "chat-preflight"))
        return self._read_images(diagnostic_roles=self.usb_present - busy)

    def _read_images(self, *, diagnostic_roles: set[str] | None = None) -> dict[str, Json]:
        """Read both complete image spans and report mismatches without using receipts."""
        if self.proof is None:
            msg = "Run production preparation before accessing the bench."
            raise bench.BenchBlockedError(msg)
        with hardware_output(self.log, verbose=self.verbose):
            images = rf.verify_installed_images(
                self.proof,
                self.effective,
                self.manifest,
                self.run_id,
                environments=bench.ENVIRONMENTS,
                report_mismatches=True,
                diagnostic_roles=diagnostic_roles,
            )
        if images is None:
            msg = "A fresh Flash readback or image identity check failed."
            raise bench.BenchBlockedError(msg)
        self.images = images
        return images

    def _prepare_images(self, images: dict[str, Json]) -> None:
        """Make one authorized application-only preparation attempt for all mismatches."""
        if self.proof is None:
            msg = "Run production preparation before accessing the bench."
            raise bench.BenchBlockedError(msg)
        mismatches = {role: image for role, image in images.items() if not image["verified"]}
        if len(mismatches) > 1:
            self.log.record("HOST", "Both production image spans differ from installed Flash.")
        approval = None if self.no_flash else self.write_approval
        self.stage = "APPLICATION_WRITE_PREFLIGHT"
        approved = bench.approve_writes(mismatches, self.layouts, approval)
        for role, write in approved.items():
            with hardware_output(self.log, verbose=self.verbose):
                code = rf.program_application(
                    self.proof,
                    images[role]["environment"],
                    self.effective,
                    approved_serial=write["serial_number"],
                    approved_sha=write["firmware_sha256"],
                    approved_pages=(write["start"], write["end"]),
                    protect_boot=True,
                )
            if code:
                msg = f"{role} application programming failed. See the preparation logs."
                raise bench.BenchFailedError(msg)

    def _verify_or_prepare(self) -> dict[str, Json]:
        """Read first, attempt preparation at most once, then require two fresh matches."""
        self.stage = "FLASH_READBACK"
        images = self._read_images()
        if all(image["verified"] for image in images.values()):
            return images
        self._prepare_images(images)
        images = self._read_images()
        if not all(image["verified"] for image in images.values()):
            msg = "Flash still differs after the application preparation attempt."
            raise bench.BenchFailedError(msg)
        return images

    def _connect_verified(self) -> Json:
        """Build and inspect the images, then verify the live targets before UPDI monitors."""
        self.proof = rf.ProofRun(self.log.path / f"preparation-{time.monotonic_ns()}")
        with hardware_output(self.log, verbose=self.verbose):
            self.stage = "FIRMWARE_BUILD"
            self.effective, self.manifest = bench.build(self.proof)
            self.stage = "FUSE_LAYOUT"
            self.layouts = bench.read_layouts(self.proof, self.effective)
        self.images = self._verify_or_prepare()
        bench.publish_receipt(self.proof, self.images, self.layouts, self.manifest)
        self.stage = "IMAGE_VERIFIED"
        return {
            "status": "PASS",
            "detail": "Both production images match fresh full-page readback.",
        }

    def _open_monitors(self, *, reset: bool = False) -> None:
        """Check both running builds, then acquire each foreground bench console."""
        if self.proof is None:
            msg = "Run production preparation before accessing the bench."
            raise bench.BenchBlockedError(msg)
        self.fault = None
        self.closing = False
        self.stop.clear()
        self.incoming = queue.Queue()
        self.stage = "SERIAL_MONITORS"
        start = len(self.log.snapshot())
        try:
            for role, port in hardware_ports(ROOT / "config" / "current_hardware.json").items():
                self.monitors[role] = rf.start_rf_monitor(
                    self.proof, role, port, self.incoming, reset=reset
                )
            self.reader = threading.Thread(target=self._capture, daemon=True)
            self.reader.start()
            for role in self.monitors:
                self.command(role, "?")
            self.stage = "RUNTIME_IDENTITY"
            self.wait(
                lambda: all(
                    firmware_role(self.text(role, start), self.images) == role
                    for role in self.images
                ),
                12,
                "both running production build IDs",
            )
            for image in self.images.values():
                if isinstance(image, dict):
                    image["runtime_identity_status"] = RUNTIME_IDENTITY_MATCH
            if reset:
                self.wait(
                    lambda: all(
                        f"[{role}] BOOT " in self.text(role, start) for role in self.images
                    ),
                    12,
                    "both new MCU boot markers after UPDI reset",
                )
            for role in self.monitors:
                self.stage = "BENCH_CONTROL"
                self.send_and_wait(role, "B", "BENCH_READY", 5)
            self.bench_active = True
        except BaseException:
            self.close()
            raise
        self.sequence = self.config["protocol"]["sequence"]

    def _capture(self) -> None:
        while not self.stop.is_set():
            try:
                key, stream, raw = self.incoming.get(timeout=0.05)
            except queue.Empty:
                continue
            role = key.upper()
            if raw is None:
                if self.closing:
                    continue
                self.fault = (
                    f"{role} serial monitor disconnected; restart is possible, not confirmed"
                )
                self.log.record(role, self.fault, "FAIL", self.fault)
            else:
                line = raw.decode("ascii", errors="replace").strip("\r\n")
                self.log.record(role, line)
                if self.verbose:
                    print(line, file=self.out, flush=True)
                if (self.bench_active or self.transmitting) and line.startswith(f"[{role}] BOOT "):
                    self.fault = f"{role} restarted after bench readiness"
                if stream == "stderr" and any(
                    x in line.lower()
                    for x in ("mismatch", "transporterror", "cannot open", "short read")
                ):
                    self.fault = f"{role} UPDI lost: {line}"

    def text(self, role: str, start: int = 0) -> str:
        """Return actual observations from one endpoint."""
        return "\n".join(row["line"] for row in self.log.snapshot(start) if row["role"] == role)

    def _events_since(self, start: int) -> list[ChatDeviceEvent]:
        """Parse only actual device events captured after one host marker."""
        return [
            event
            for row in self.log.snapshot(start)
            if (event := parse_firmware_event(row)) is not None
        ]

    def command(self, role: str, value: str) -> None:
        """Send a supported firmware byte and record its request."""
        monitor = self.monitors[role]["process"]
        if monitor.poll() is not None or not monitor.stdin:
            msg = f"{role.upper()} serial monitor disconnected"
            raise OSError(msg)
        self.log.record("HOST_" + role.upper(), value)
        if monitor.stdin.write(value.encode("ascii")) != len(value):
            msg = "Incomplete serial command write"
            raise OSError(msg)
        monitor.stdin.flush()

    def wait(self, condition: Callable[[], bool], seconds: float, description: str) -> None:
        """Wait for hardware evidence with a finite deadline."""
        deadline = time.monotonic() + seconds
        while True:
            if self.fault:
                raise OSError(self.diagnostic(self.fault))
            if condition():
                return
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Waiting for {description}; last event: " + self.last_event())
            time.sleep(0.02)

    def last_event(self) -> str:
        """Return the latest observed response or command."""
        rows = self.log.snapshot()
        return rows[-1]["line"] if rows else "none"

    def diagnostic(self, reason: str) -> str:
        """Describe the failed boundary without inventing an electrical measurement."""
        rows = self.log.snapshot()
        last = next(
            (row["line"] for row in reversed(rows) if " T=" in row["line"]),
            "no protocol event captured",
        )
        return (
            f"{reason}; last protocol event: {last}. "
            "If the Receiver restarted during reply, inspect VDD/RESET during TX and "
            "TX/interrupt/stack behavior. Reset flags alone do not prove an electrical cause. "
            "Reconnect with b → step 1 → r; l shows raw logs."
        )

    def send_and_wait(self, role: str, command: str, marker: str, timeout: float) -> None:
        """Require fresh output from the addressed firmware after a command."""
        start = len(self.log.snapshot())
        label = role.upper()
        self.command(role, command)
        self.wait(lambda: f"[{label}] {marker}" in self.text(label, start), timeout, marker)

    def _arm_radio(self, role: str) -> None:
        """Rearm one radio and verify its actual idle RX registers."""
        label = role.upper()
        marker = "RX_READY" if role == "receiver" else "RADIO_READY"
        self.send_and_wait(role, "R", marker, 5)
        start = len(self.log.snapshot())
        self.send_and_wait(role, "?", "RADIO_REG ", 12)
        text = self.text(label, start)
        radio = self.manifest["shared"]["radio"]
        if not bench.phy_matches(text, label, radio) or not bench.power_matches(
            text, label, radio, self.version_probes
        ):
            msg = f"{label} live SX127x register snapshot disagrees with the configured RX profile."
            raise bench.BenchFailedError(msg)
        if role == "receiver":
            active = self.manifest["boards"][role]["radio_board"]["radio_power_active_level"]
            if f"[RECEIVER] TRACKER_GPIO LORA_EN={active} SD_CS=1" not in text.splitlines():
                msg = "Tracker radio enable or SD chip select readback is incorrect."
                raise bench.BenchFailedError(msg)

    def ready(self) -> Json:
        """Open both verified builds and prove fresh Tracker RX readiness."""
        try:
            if not self.monitors:
                self._open_monitors()
            self.stage = "RADIO_READINESS"
            for role in ("receiver", "gateway"):
                self._arm_radio(role)
            self.stage = "READY"
            self.stage_error = None
            return {"status": "PASS", "detail": "Both build IDs and live RX registers verified."}
        except (OSError, TimeoutError, ValueError, KeyError, RuntimeError) as error:
            self.stage_error = str(error)
            raise

    def _park(self, *, release: bool = False) -> None:
        """Stop both endpoints and require fresh standby readback from each."""
        errors = []
        sent = {}
        timeout = 2 * self.config["timeouts"]["tx_ms"] / 1000 + 5
        for role in ("receiver", "gateway"):
            if role not in self.monitors:
                continue
            try:
                sent[role] = len(self.log.snapshot())
                command = "E" if release else "P"
                if release and role == "gateway":
                    # Exit on a command boundary even after a truncated X frame.
                    command = "\nE"
                self.command(role, command)
            except OSError as error:
                sent.pop(role, None)
                errors.append(str(error))
        for role, start in sent.items():
            label = role.upper()

            def parked(label: str = label, start: int = start) -> bool:
                return f"[{label}] PARKED E=0" in self.text(label, start).splitlines()

            try:
                self.wait(parked, timeout, f"{role} standby")
            except (OSError, TimeoutError) as error:
                errors.append(str(error))
        if errors:
            raise OSError("; ".join(errors))
        if release:
            self.bench_active = False

    def _require_rf(self) -> None:
        """Keep the first transmission behind explicit 915 MHz bench authorization."""
        if not self.authorize_rf:
            msg = "Step 3 requires --authorize-rf-test for the verified 915 MHz RF arrangement."
            raise bench.BenchBlockedError(msg)
        if len(self.monitors) != BOARD_COUNT or self.fault or any(
            monitor["process"].poll() is not None for monitor in self.monitors.values()
        ):
            msg = "Both verified production monitors must be responsive before any transmission."
            raise bench.BenchBlockedError(msg)

    @contextlib.contextmanager
    def _capture_transaction(self, start: int, *, release: bool = False) -> Iterator[None]:
        """Attempt standby while preserving the primary failure or cancellation."""
        try:
            yield
        except BaseException:
            try:
                self._park(release=release)
            except OSError as error:
                self.log.record("HOST", str(error), "FAIL", str(error))
            raise
        else:
            self._park(release=release)
        finally:
            self.exchange_rows = self.log.snapshot(start)
            self.transmitting = False

    def _wait_for_ack_capture(self, start: int, timeout: float, *, duplicate: bool) -> None:
        """Wait for final Tracker TX evidence before park can overtake deferred logs."""
        if duplicate:
            self.wait(
                lambda: (
                    "CONTROL_IGNORED " in self.text("GATEWAY", start)
                    and "ACK_DUP_TX_DONE " in self.text("RECEIVER", start)
                ),
                timeout,
                "Tracker duplicate ACK completion and Gateway discard",
            )
        elif "ACK_ACCEPTED " in self.text("GATEWAY", start):
            self.wait(
                lambda: "ACK_TX_DONE " in self.text("RECEIVER", start),
                timeout,
                "Tracker ACK transmission",
            )

    def exchange(
        self,
        *,
        nack: bool = False,
        drop: bool = False,
        exhaust: bool = False,
        control_fault: str | None = None,
    ) -> Json:
        """Capture both sides through a bounded transaction and park on every outcome."""
        self._require_rf()
        start = len(self.log.snapshot())
        sequence = self.sequence
        attempts = self.config["retries"]["max_retries"] + 1
        ack_ms, tx_ms = (self.config["timeouts"][name] for name in ("ack_ms", "tx_ms"))
        with self._capture_transaction(start):
            self._arm_radio("receiver")
            self.send_and_wait("receiver", "T", "BENCH_TX_READY", 5)
            if nack:
                self.command("receiver", "N")
            if drop:
                self.command("receiver", "D")
            if control_fault is not None:
                self.command("receiver", control_fault)
            if exhaust:
                self.send_and_wait("receiver", "P", "PARKED E=0", tx_ms / 1000 + 5)
            self._arm_radio("gateway")
            self.transmitting = True
            sent = len(self.log.snapshot())
            self._require_rf()
            self.command("gateway", "S")
            self.wait(
                lambda: any(
                    marker in self.text("GATEWAY", sent)
                    for marker in ("ACK_ACCEPTED ", "TRANSACTION_FAILED ", "DATA_START_FAILED")
                ),
                attempts * (ack_ms + tx_ms) / 1000 + 5,
                "bounded DATA transaction",
            )
            self._wait_for_ack_capture(sent, tx_ms / 1000 + 5, duplicate=control_fault == "U")
        if exhaust:
            result = assess_exhaustion(self.exchange_rows, attempts, sequence)
        elif control_fault:
            result = assess_control_fault(self.exchange_rows, control_fault, sequence)
        else:
            result = assess(
                self.exchange_rows, self.images, self.run_id, nack=nack, sequence=sequence
            )
            expected_attempts = 2 if nack or drop else 1
            if result["status"] == "PASS" and result["attempts"] != expected_attempts:
                result.update(status="FAIL", detail="Unexpected number of physical attempts.")
        if not exhaust and result["status"] == "PASS":
            self.sequence = sequence % 255 + 1
        return {**result, "events": self.protocol_events()}

    def retry_legacy_message(self) -> Json:
        """Retry the fixed payload on a fresh campaign, then use existing bounded ARQ."""
        self._require_rf()
        self._start_interactive_campaign()
        return self.exchange()

    def _start_interactive_campaign(self) -> None:
        """Start a fresh campaign so queued messages cannot reuse an old ACK identity."""
        if self.bench_active:
            self._park(release=True)
        for role in ("receiver", "gateway"):
            self.send_and_wait(role, "B", "BENCH_READY", 5)
        self.bench_active = True
        self.sequence = self.config["protocol"]["sequence"]

    def _interactive_chunk_complete(self, start: int, sequence: int) -> bool:
        """Wait for both Gateway completion and Tracker acceptance of one Echo ACK."""
        events = self._events_since(start)
        completed = next(
            (
                event
                for event in events
                if event.role is ChatDeviceRole.GATEWAY
                and event.name == ChatEventName.ROUND_TRIP_DONE
                and event.sequence == sequence
                and event.campaign_id is not None
            ),
            None,
        )
        if completed is not None and any(
            event.role is ChatDeviceRole.TRACKER
            and event.name == ChatEventName.ACK_ACCEPTED
            and event.campaign_id == completed.campaign_id
            and event.sequence == sequence
            and event.packet_type == self.config["protocol"]["ack_type"]
            for event in events
        ):
            return True
        return any(
            event.name
            in {
                "TRANSACTION_FAILED",
                ChatEventName.ACK_CONFIRM_TIMEOUT,
                ChatEventName.ECHO_TIMEOUT,
                "DATA_START_FAILED",
                "ACK_CONFIRM_START_FAILED",
                "ECHO_DATA_START_FAILED",
                "HOST_DATA_REJECTED",
            }
            and event.sequence in {None, sequence}
            for event in events
        )

    def exchange_interactive_message(self, chunks: tuple[bytes, ...], max_data_bytes: int) -> Json:
        """Send and Echo bounded chunks sequentially over the existing reliable transport."""
        self._require_rf()
        if not chunks or any(not chunk or len(chunk) > max_data_bytes for chunk in chunks):
            raise bench.BenchBlockedError("interactive message contains an invalid DATA fragment")

        start = len(self.log.snapshot())
        ack_ms = self.config["timeouts"]["ack_ms"]
        tx_ms = self.config["timeouts"]["tx_ms"]
        attempts = self.config["retries"]["max_retries"] + 1
        # Both DATA directions and the tagged handoff have bounded attempts.
        timeout = 3 * attempts * (ack_ms + tx_ms) / 1000 + 5
        max_sequence = (1 << self.config["protocol"]["sequence_bits"]) - 1
        with self._capture_transaction(start, release=True):
            self._start_interactive_campaign()
            self._arm_radio("receiver")
            self.send_and_wait("receiver", "T", "BENCH_TX_READY", 5)
            self._arm_radio("gateway")
            for role in ("receiver", "gateway"):
                ready_start = len(self.log.snapshot())
                self.send_and_wait(role, "I", "INTERACTIVE_READY", 5)
                ready_events = self._events_since(ready_start)
                if not any(
                    event.name == ChatEventName.INTERACTIVE_READY
                    and event.role is (
                        ChatDeviceRole.TRACKER if role == "receiver" else ChatDeviceRole.GATEWAY
                    )
                    and event.max_data_bytes is not None
                    and event.max_data_bytes >= max_data_bytes
                    and event.echo_supported is True
                    for event in ready_events
                ):
                    raise bench.BenchBlockedError(
                        f"{role.upper()} did not confirm interactive Echo MAX_DATA={max_data_bytes}"
                    )

            self.transmitting = True
            for chunk in chunks:
                sequence = self.sequence
                chunk_start = len(self.log.snapshot())
                command = encode_interactive_command(chunk, max_data_bytes)
                self._require_rf()
                self.command("gateway", command)

                def chunk_complete() -> bool:
                    return self._interactive_chunk_complete(chunk_start, sequence)

                self.wait(
                    chunk_complete,
                    timeout,
                    f"DATA/ACK/Echo/ACK sequence {sequence}",
                )
                events = self._events_since(chunk_start)
                first_data = next(
                    (
                        event
                        for event in events
                        if event.role is ChatDeviceRole.GATEWAY
                        and event.name == ChatEventName.DATA_TX_BEGIN
                        and event.sequence == sequence
                        and event.campaign_id is not None
                    ),
                    None,
                )
                if first_data is None or first_data.campaign_id is None:
                    raise bench.BenchFailedError(
                        f"sequence {sequence} has no Gateway DATA transaction identity"
                    )
                if not verify_round_trip(
                    events,
                    RoundTripContext(
                        campaign_id=first_data.campaign_id,
                        sequence=sequence,
                        original_payload=chunk,
                        data_type=self.config["protocol"]["data_type"],
                        ack_type=self.config["protocol"]["ack_type"],
                        gateway_address=self.config["protocol"]["sender_address"],
                        tracker_address=self.config["protocol"]["receiver_address"],
                        sequence_bits=self.config["protocol"]["sequence_bits"],
                    ),
                ):
                    raise bench.BenchFailedError(
                        f"sequence {sequence} lacks complete matching DATA/Echo/ACK evidence"
                    )
                self.sequence = sequence % max_sequence + 1

        events = self._events_since(start)
        return {
            "status": "PASS",
            "detail": f"{len(chunks)} RF fragment(s) completed in both directions",
            "attempts": sum(event.name == ChatEventName.DATA_TX_BEGIN for event in events),
            "retries": sum(event.name in RETRY_EVENTS for event in events),
            "timeouts": sum(event.name in TIMEOUT_EVENTS for event in events),
            "events": self.protocol_events(),
        }

    def step(self, index: int) -> Json:
        """Run the requested checkpoint in dependency order."""
        actions = (
            self.connect,
            self.ready,
            self._data,
            self._payload,
            self._ack,
            self._nack,
            self._negative_and_recovery,
            self._finish,
        )
        return actions[index]()

    def _data(self) -> Json:
        """Capture the first complete addressed sequence-one DATA/ACK exchange."""
        if self.sequence != self.config["protocol"]["sequence"]:
            msg = "Reconnect at checkpoint 1 to start a fresh sequence-one campaign."
            raise bench.BenchBlockedError(msg)
        result = self.exchange()
        self.first_exchange = result
        self.first_rows = self.exchange_rows
        return result

    def _payload(self) -> Json:
        """Read the exact application bytes from the first transaction capture."""
        payload = self.config["protocol"]["payload"]
        expected = f"LEN={len(payload)} HEX={payload.encode().hex().upper()} ASCII={payload}"
        rows = [
            row["line"]
            for row in self.first_rows
            if row["role"] == "RECEIVER" and " PAYLOAD_BYTES " in row["line"]
        ]
        if (
            not self.first_exchange
            or self.first_exchange["status"] != "PASS"
            or len(rows) != 1
            or not rows[0].endswith(expected)
        ):
            return {"status": "FAIL", "detail": "Receiver payload missing or mismatched."}
        return {
            **self.first_exchange,
            "detail": f"Tracker received {len(payload)}/{len(payload)} bytes. {rows[0]}",
        }

    def _trials(self, name: str, count: int, trial: Callable[[], Json]) -> Json:
        """Stop each group at its first failure and persist each individual result."""
        results = []
        for index in range(count):
            result = trial()
            self.log.record(
                "HOST", f"{name} trial {index + 1}/{count}: {result['detail']}", result["status"]
            )
            results.append(result)
            if result["status"] != "PASS":
                return {**result, "trials": results}
        return {
            "status": "PASS",
            "detail": f"{name} passed {count}/{count} trials.",
            "trials": results,
        }

    def _ack(self) -> Json:
        """Count the first captured ACK and perform the rest of the ten trials."""
        if self.first_exchange is None or self.first_exchange["status"] != "PASS":
            msg = "Capture the first transaction at step 3."
            raise bench.BenchBlockedError(msg)
        result = self._trials("Additional DATA/ACK", TRIALS - 1, self.exchange)
        if result["status"] == "PASS":
            result["detail"] = f"DATA/ACK passed {TRIALS}/{TRIALS} trials."
        return {**result, "first": self.first_exchange}

    def _nack(self) -> Json:
        """Require a real one-shot NACK and successful retransmission ten times."""
        return self._trials("NACK then ACK", TRIALS, lambda: self.exchange(nack=True))

    def _probe_data(self, *, malformed: bool = False) -> Json:
        """Transmit one fixed invalid DATA frame and observe its expected boundary."""
        self._require_rf()
        start = len(self.log.snapshot())
        tx_timeout = self.config["timeouts"]["tx_ms"] / 1000 + 5
        with self._capture_transaction(start):
            self._arm_radio("receiver")
            self.send_and_wait("receiver", "T", "BENCH_TX_READY", 5)
            self._arm_radio("gateway")
            self.transmitting = True
            sent = len(self.log.snapshot())
            self.send_and_wait(
                "gateway", "M" if malformed else "W", "BENCH_PROBE_DONE E=1", tx_timeout
            )
            expected = "DATA_REJECTED_PAYLOAD" if malformed else "RX_DISCARD_DEST"
            self.wait(lambda: f"{expected} " in self.text("RECEIVER", sent), tx_timeout, expected)
            if malformed:
                self.wait(
                    lambda: "NACK_TX_DONE " in self.text("RECEIVER", sent),
                    tx_timeout,
                    "NACK TX completion",
                )
            else:
                time.sleep(self.config["timeouts"]["ack_ms"] / 1000)
        return assess_probe(
            self.exchange_rows, self.config["protocol"], self.sequence, malformed=malformed
        )

    def _negative_and_recovery(self) -> Json:
        """Exercise filtering, idempotence, timeout bounds, and coordinated restart."""
        checks: list[tuple[str, Callable[[], Json]]] = [
            (
                "wrong destination",
                lambda: self._trials("Wrong destination", TRIALS, self._probe_data),
            ),
            (
                "duplicate DATA",
                lambda: self._trials("Duplicate DATA", TRIALS, lambda: self.exchange(drop=True)),
            ),
            ("wrong campaign", lambda: self.exchange(control_fault="C")),
            ("wrong sequence", lambda: self.exchange(control_fault="Q")),
            ("duplicate ACK", lambda: self.exchange(control_fault="U")),
            ("malformed DATA", lambda: self._probe_data(malformed=True)),
            ("retry exhaustion", lambda: self.exchange(exhaust=True)),
            ("retry recovery", self.exchange),
            ("restart recovery", self._restart),
        ]
        results = {}
        for name, check in checks:
            results[name] = check()
            if results[name]["status"] != "PASS":
                return {
                    "status": "FAIL",
                    "detail": f"{name}: {results[name]['detail']}",
                    "checks": results,
                }
        return {
            "status": "PASS",
            "detail": "All negative and recovery cases passed.",
            "checks": results,
        }

    def _restart(self) -> Json:
        """Reset both endpoints via UPDI and start a fresh coordinated campaign."""
        self._require_rf()
        self._park()
        self.close()
        self._open_monitors(reset=True)
        return self.exchange()

    def _finish(self) -> Json:
        """Park, release the bench and persist both serial captures."""
        return {
            "status": "PASS" if self.close() else "FAIL",
            "detail": "Both monitors closed. Standby evidence is recorded in the captures.",
        }

    def protocol_events(self) -> list[str]:
        """Return firmware timestamps from the captured transaction."""
        return [row["line"] for row in self.exchange_rows if " T=" in row["line"]]

    def close(self) -> bool:
        """Attempt standby on both radios, then release both serial monitors."""
        self.closing = True
        clean = bool(self.monitors)
        if self.monitors:
            try:
                self._park(release=True)
            except (OSError, TimeoutError) as error:
                clean = False
                self.log.record("HOST", str(error), "FAIL", str(error))
        for monitor in self.monitors.values():
            try:
                rf.stop_rf_monitor(monitor)
            except OSError as error:
                clean = False
                self.log.record("HOST", "Serial cleanup failed: " + str(error), "FAIL", str(error))
        self.stop.set()
        if self.reader:
            self.reader.join(timeout=2)
        self.monitors.clear()
        self.reader = None
        return clean


class Console:
    """One explicit input per checkpoint; navigation alone never transmits."""

    def __init__(
        self,
        hardware: Hardware,
        log: Session,
        read: Callable[[], str] = input,
        out: TextIO = sys.stdout,
    ) -> None:
        """Keep navigation separate from the physical transport."""
        self.hardware, self.log, self.read, self.out = hardware, log, read, out
        self.index = 0

    def _display(self) -> None:
        current = self.log.results.get(str(self.index + 1))
        print(f"\nSTEP {self.index + 1}/8 — {STEPS[self.index]}", file=self.out)
        if current:
            print(f"[{current['status']}] {current['detail']}", file=self.out)
            if current.get("rtt_ms") is not None:
                print(f"RTT: {current['rtt_ms']} ms (Gateway clock)", file=self.out)
            for event in current.get("events", []):
                print(event, file=self.out)
            for name in ("attempts", "retries", "timeouts"):
                if name in current:
                    print(f"{name.capitalize()}: {current[name]}", file=self.out)
        else:
            print("[WAITING] Press ENTER to execute", file=self.out)
        print(HELP, file=self.out, flush=True)

    def _execute(self, key: str) -> None:
        """Run the selected checkpoint and invalidate dependent evidence on retry."""
        current = self.log.results.get(str(self.index + 1))
        if key == "" and current and current["status"] == "PASS":
            if self.index == len(STEPS) - 1:
                return
            self.index += 1
        if any(
            self.log.results.get(str(i), {}).get("status") != "PASS"
            for i in range(1, self.index + 1)
        ):
            print("[BLOCKED] Complete earlier checkpoints first.", file=self.out)
            return
        self.log.step = self.index
        self.log.results = {
            key: value for key, value in self.log.results.items() if int(key) <= self.index
        }
        try:
            result = self.hardware.step(self.index)
        except TimeoutError as error:
            result = {"status": "TIMEOUT", "detail": str(error)}
        except (OSError, ValueError, KeyError) as error:
            result = {"status": "BLOCKED", "detail": str(error)}
        except bench.BenchFailedError as error:
            result = {"status": "FAIL", "detail": str(error)}
        self.log.results[str(self.index + 1)] = result
        self.log.record("HOST", result["detail"], result["status"])
        self.log.finish()
        print(f"Step {self.index + 1} [{result['status']}] {result['detail']}", file=self.out)

    def _input(self, key: str) -> bool:
        if key == "q":
            return False
        if key == "h":
            print(
                "b/l/h never repeat RF. r explicitly repeats the displayed step. "
                "Failures stay on the same step. "
                "q also stops after a failure. Ctrl-C stops a running step.",
                file=self.out,
            )
        elif key == "l":
            for row in self.log.snapshot()[-15:]:
                print(row["timestamp"], row["role"], row["line"], file=self.out)
        elif key == "b":
            self.index = max(0, self.index - 1)
        elif key == "s":
            print("[BLOCKED] All checkpoints are required.", file=self.out)
        elif key in ("", "r"):
            self._execute(key)
        else:
            print("[WAITING] Unknown input; h for help", file=self.out)
        return True

    def run(self, *, interactive: bool = True) -> int:
        """Run sequentially by default from the CLI; always release acquired monitors."""
        result = 2
        quit_requested = False
        try:
            if interactive:
                while True:
                    self._display()
                    if not self._input(self.read().strip().lower()):
                        quit_requested = True
                        break
            else:
                for index in range(len(STEPS)):
                    self.index = index
                    self._execute("r")
                    if self.log.results[str(index + 1)]["status"] != "PASS":
                        break
            result = self._exit_status(quit_requested=quit_requested)
        except EOFError, StopIteration:
            pass
        except KeyboardInterrupt:
            self.log.record("HOST", "Cancelled.", "CANCELLED")
            result = 130
        finally:
            self.hardware.close()
            self.log.finish()
            print(f"Logs: {self.log.path}", file=self.out)
        return result

    def _exit_status(self, *, quit_requested: bool) -> int:
        """Translate the completed checkpoint results into a process status."""
        statuses = [row["status"] for row in self.log.results.values()]
        if any(status in ("FAIL", "TIMEOUT") for status in statuses):
            return 1
        if any(status != "PASS" for status in statuses):
            return 2
        if len(statuses) == len(STEPS):
            return 0
        if quit_requested:
            self.log.record("HOST", "Cancelled with q.", "CANCELLED")
            return 130
        return 2


def main(argv: list[str] | None = None) -> int:
    """Parse the production bench options and return the checkpoint exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="validate and build offline, without opening ports"
    )
    parser.add_argument(
        "--interactive", action="store_true", help="advance one checkpoint at a time"
    )
    parser.add_argument("--verbose", action="store_true", help="mirror raw diagnostics")
    parser.add_argument("--gateway-port", help="alias of the enrolled Gateway adapter")
    parser.add_argument(
        "--tracker-port",
        "--receiver-port",
        dest="tracker_port",
        help="alias of the enrolled Tracker adapter",
    )
    flash = parser.add_mutually_exclusive_group()
    flash.add_argument(
        "--no-flash", action="store_true", help="require the installed production images to match"
    )
    flash.add_argument(
        "--write-approval", type=Path, help="JSON approval for exact MCU, image and APPCODE span"
    )
    parser.add_argument(
        "--authorize-rf-test",
        action="store_true",
        help="confirm the established 915 MHz RF arrangement",
    )
    args = parser.parse_args(argv)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    log = Session(ROOT / "artifacts/rf-debug" / stamp, dry_run=args.dry_run)
    if args.dry_run:
        proof = rf.ProofRun(log.path / "dry-run")
        try:
            with hardware_output(log, verbose=args.verbose):
                bench.build(proof)
        except bench.BenchFailedError as error:
            print(str(error), file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            return 130
        finally:
            log.finish()
        print(f"Offline production builds passed. Hardware checkpoints NOT RUN. Logs: {log.path}")
        return 0
    hardware = Hardware(log)
    hardware.port_overrides = {"gateway": args.gateway_port, "receiver": args.tracker_port}
    hardware.no_flash = args.no_flash or args.write_approval is None
    hardware.write_approval = args.write_approval
    hardware.authorize_rf = args.authorize_rf_test
    hardware.verbose = args.verbose
    return Console(hardware, log).run(interactive=args.interactive)


if __name__ == "__main__":
    raise SystemExit(main())
