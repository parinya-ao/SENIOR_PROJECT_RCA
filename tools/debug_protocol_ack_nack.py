"""Interactive checkpoints around the existing physical UPDI/RF proof interfaces."""

from __future__ import annotations

import contextlib
import json
import queue
import re
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, TextIO, TypeVar

from serial.tools import list_ports

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

from tools import rf_proof as rf

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

Json = dict[str, Any]
T = TypeVar("T")
OPTIONAL_FIRST = 5

STEPS = (
    "Connect Hardware",
    "Initialize Receiver",
    "Gateway Sends DATA",
    "Verify Receiver DATA",
    "Verify ACK",
    "Controlled NACK Test",
    "Timeout and Retry",
    "Full Bidirectional Loop",
)
HELP = (
    "ENTER = next/retry failed step | r = retry | b = back | s = skip optional\n"
    "l = logs | h = help | q = quit"
)


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


def assess(rows: list[Json], images: dict[str, Json], run_id: str, *, nack: bool = False) -> Json:
    """Use the proof runner's two-sided packet/sequence/identity/retry checks."""
    result = rf.validate_stable_transport(rows, images, run_id, "T02" if nack else "T01")
    result.update(
        status="PASS" if result["valid"] else "FAIL",
        detail="DATA → NACK → RETRY → ACK" if nack else "DATA → ACK",
    )
    if not result["valid"]:
        result["detail"] = "; ".join(result["issues"])
    return result


def assess_exhaustion(rows: list[Json], max_attempts: int) -> Json:
    """Require explicit bounded failure for an intentional no-response test."""
    config = json.loads((ROOT / "config/lora_system.json").read_text())
    protocol = config["protocol"]
    packet = re.compile(r"^\[GATEWAY\] ([A-Z_]+) T=(\d+) TYPE=(\d+) Q=(\d+) E=(-?\d+)$")
    events = [
        match.groups()
        for row in rows
        if row["role"] == "GATEWAY" and (match := packet.fullmatch(row["line"]))
    ]
    clean_events = all(
        int(type_) == protocol["data_type"]
        and int(sequence) == protocol["sequence"]
        and int(error) == (-1 if name == "TRANSACTION_FAILED" else 0)
        for name, _, type_, sequence, error in events
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


class Session:
    """Persist every actual response and checkpoint; host timestamps are receipt times."""

    def __init__(self, path: Path) -> None:
        """Create one isolated evidence directory."""
        self.path = path
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
                "mode": "REAL RF",
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
            report = ["# Interactive LoRa debugger", "", "Mode: REAL RF", ""]
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


class Hardware:
    """Real serial monitors only; no flashing, replay mode, or simulated radio."""

    def __init__(
        self, log: Session, read: Callable[[], str] = input, out: TextIO = sys.stdout
    ) -> None:
        """Use the existing project's serial and proof mechanisms."""
        self.log, self.read, self.out = log, read, out
        self.monitors: dict[str, Json] = {}
        self.incoming: queue.Queue[tuple[str, str, bytes | None]] = queue.Queue()
        self.stop = threading.Event()
        self.reader: threading.Thread | None = None
        self.images: dict[str, Json] = {}
        self.exchange_rows: list[Json] = []
        self.last: Json | None = None
        self.fault: str | None = None
        self.run_id = log.path.name
        self.config = json.loads((ROOT / "config/lora_system.json").read_text())
        self.proof: rf.ProofRun | None = None
        self.transmitting = False
        self.closing = False

    def quiet(self, function: Callable[..., T], *args: object) -> T:
        """Keep verbose hardware diagnostics in the session directory."""
        # ProofRun retains raw output on disk; keep the interactive screen readable.
        with (
            (self.log.path / "preflight.log").open("a") as file,
            contextlib.redirect_stdout(file),
            contextlib.redirect_stderr(file),
        ):
            return function(*args)

    def connect(self) -> Json:
        """Verify devices and installed images before opening firmware consoles."""
        self.close()
        self._select_ports()
        return self._connect_verified()

    def _select_ports(self) -> None:
        ports = discover_ports()
        if len(ports) < len(rf.PORTS):
            raise OSError("Need two available serial devices; found " + str(len(ports)))
        for role, configured in rf.PORTS.items():
            matches = [p for p in ports if Path(p).resolve() == Path(configured).resolve()]
            if not matches:
                print(
                    f"Select {role} candidate (MCU identity will still be verified):", file=self.out
                )
                for index, port in enumerate(ports, 1):
                    print(f"  {index}. {port}", file=self.out)
                choice = self.read().strip()
                if choice == "q":
                    raise KeyboardInterrupt
                if not choice.isdigit() or not 1 <= int(choice) <= len(ports):
                    msg = "Invalid port selection"
                    raise OSError(msg)
                if Path(ports[int(choice) - 1]).resolve() != Path(configured).resolve():
                    msg = (
                        "Selected adapter differs from the verified hardware mapping; "
                        "no role guessed. See config/current_hardware.json."
                    )
                    raise OSError(msg)

    def _connect_verified(self) -> Json:
        self.proof = rf.ProofRun(self.log.path / f"identity-{time.monotonic_ns()}")
        code, data, _ = self.quiet(
            self.proof.command, "configuration", ["pio", "project", "config", "--json-output"], 30
        )
        if code:
            msg = "PlatformIO configuration unavailable; see preflight.log"
            raise OSError(msg)
        effective = data.decode()
        manifest = json.loads((ROOT / "generated/lora_manifest.json").read_text())
        if not (
            rf.valid_rf_profile_config(effective)
            and rf.application_layout_verified(("sender_hello", "receiver"), effective)
            and rf.upload_ports_match(effective)
        ):
            msg = "Radio profile, application bounds or configured ports failed verification"
            raise OSError(msg)
        evidence = sorted(
            (ROOT / "artifacts/rf-proof").glob("*/upload-evidence.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not any(rf.upload_evidence_matches(path, manifest) for path in evidence):
            msg = "No upload receipt matches current firmware; no automatic flashing"
            raise OSError(msg)
        args = SimpleNamespace(
            physical_mapping_verified=True,
            power_verified=True,
            rf_hardware_verified=True,
            no_meter_mode=False,
        )
        print(
            "[WAITING] Reading MCU identities and fuses (no Flash writes)...",
            file=self.out,
            flush=True,
        )
        if self.quiet(rf.identify_targets, self.proof, args, effective):
            msg = "MCU serial/fuse/port verification failed; see preflight.log"
            raise OSError(msg)
        print(
            "[WAITING] Comparing installed Flash with both images (about one minute)...",
            file=self.out,
            flush=True,
        )
        images = self.quiet(
            rf.verify_installed_images, self.proof, effective, manifest, self.run_id
        )
        if not images:
            msg = "Installed Flash differs from the verified compatible image"
            raise OSError(msg)
        self.images = images
        self.fault = None
        self.closing = False
        self.stop.clear()
        self.incoming = queue.Queue()
        start = len(self.log.snapshot())
        for role, port in rf.PORTS.items():
            self.monitors[role] = rf.start_rf_monitor(self.proof, role, port, self.incoming)
        self.reader = threading.Thread(target=self._capture, daemon=True)
        self.reader.start()
        for role in self.monitors:
            self.command(role, "?")
        self.wait(
            lambda: all(
                firmware_role(self.text(role, start), self.images) == role for role in self.images
            ),
            12,
            "firmware role/build ID",
        )
        self._park()
        return {
            "status": "PASS",
            "detail": " | ".join(
                f"{role.upper()}: {Path(port).resolve()} [CONNECTED, MCU/image/firmware verified]"
                for role, port in rf.PORTS.items()
            ),
        }

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
                if self.transmitting and " BOOT " in line:
                    self.fault = (
                        f"{role} restarted during the RF transaction; "
                        "reset flags unavailable on this UART"
                    )
                if stream == "stderr" and any(
                    x in line.lower()
                    for x in ("mismatch", "transporterror", "cannot open", "short read")
                ):
                    self.fault = f"{role} UPDI lost: {line}"

    def text(self, role: str, start: int = 0) -> str:
        """Return actual observations from one endpoint."""
        return "\n".join(row["line"] for row in self.log.snapshot(start) if row["role"] == role)

    def command(self, role: str, value: str) -> None:
        """Send a supported firmware byte and record its request."""
        monitor = self.monitors[role]["process"]
        if monitor.poll() is not None or not monitor.stdin:
            msg = f"{role.upper()} serial monitor disconnected"
            raise OSError(msg)
        if monitor.stdin.write(value.encode("ascii")) != len(value):
            msg = "Incomplete serial command write"
            raise OSError(msg)
        monitor.stdin.flush()
        self.log.record("HOST_" + role.upper(), value)

    def wait(self, condition: Callable[[], bool], seconds: float, description: str) -> None:
        """Wait for hardware evidence with a finite deadline."""
        deadline = time.monotonic() + seconds
        while not condition():
            if self.fault:
                raise OSError(self.diagnostic(self.fault))
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

    def ready(self) -> Json:
        """Rearm Receiver and require a fresh ready response."""
        start = len(self.log.snapshot())
        self.command("receiver", "?")
        self.wait(lambda: "RADIO_" in self.text("RECEIVER", start), 5, "Receiver status")
        self.command("receiver", "R")
        self.wait(
            lambda: "[RECEIVER] RX_READY" in self.text("RECEIVER", start), 5, "fresh RX_READY"
        )
        return {"status": "PASS", "detail": "Receiver RX_READY (fresh hardware response)"}

    def _park(self) -> None:
        errors = []
        for role in self.monitors:
            try:
                start = len(self.log.snapshot())
                self.command(role, "P")

                def parked(role: str = role, start: int = start) -> bool:
                    return f"[{role.upper()}] PARKED E=0" in self.text(role.upper(), start)

                self.wait(
                    parked,
                    3,
                    role + " standby",
                )
            except (OSError, TimeoutError) as error:
                errors.append(str(error))
        if errors:
            raise OSError("; ".join(errors))

    def exchange(self, *, nack: bool = False, drop: bool = False, exhaust: bool = False) -> Json:
        """Capture one complete timing-sensitive transaction without prompting."""
        if not self.monitors or self.fault:
            msg = "Reconnect at step 1 before transmitting"
            raise OSError(msg)
        start = len(self.log.snapshot())
        try:
            self.command("receiver", "?")
            self.wait(lambda: "RADIO_" in self.text("RECEIVER", start), 5, "Receiver status")
            if nack:
                self.command("receiver", "N")
            self.command("receiver", "R")
            self.wait(lambda: "[RECEIVER] RX_READY" in self.text("RECEIVER", start), 5, "RX_READY")
            if drop:
                self.command("receiver", "D")
            if exhaust:
                parked = len(self.log.snapshot())
                self.command("receiver", "P")
                self.wait(
                    lambda: "[RECEIVER] PARKED E=0" in self.text("RECEIVER", parked),
                    3,
                    "controlled Receiver silence",
                )
            self.command("gateway", "R")
            gateway_start = len(self.log.snapshot())
            self.command("gateway", "?")
            self.wait(
                lambda: "[GATEWAY] RADIO_READY" in self.text("GATEWAY", gateway_start),
                5,
                "Gateway ready",
            )
            self.transmitting = True
            self.command("gateway", "S")
            sent = len(self.log.snapshot()) - 1
            budget = (self.config["timeouts"]["ack_ms"] + self.config["timeouts"]["tx_ms"]) * (
                self.config["retries"]["max_retries"] + 1
            ) / 1000 + 5
            self.wait(
                lambda: (
                    any(
                        x in self.text("GATEWAY", sent)
                        for x in ("ACK_ACCEPTED ", "TRANSACTION_FAILED ")
                    )
                    or any(" BOOT " in row["line"] for row in self.log.snapshot(sent))
                ),
                budget,
                "bounded DATA/ACK transaction",
            )
            # Event logging is deferred during TX; drain it before checking either board.
            time.sleep(rf.RF_COMPLETION_LOG_SETTLE_SECONDS)
        finally:
            try:
                self._park()
            finally:
                self.exchange_rows = self.log.snapshot(start)
                self.transmitting = False
        self.last = (
            assess_exhaustion(self.exchange_rows, self.config["retries"]["max_retries"] + 1)
            if exhaust
            else assess(self.exchange_rows, self.images, self.run_id, nack=nack)
        )
        self.last["events"] = self.protocol_events()
        return self.last

    def step(self, index: int) -> Json:
        """Execute the explicitly selected checkpoint."""
        if index and not self.monitors:
            msg = "Connect both boards at step 1 first"
            raise OSError(msg)
        actions = (
            self.connect,
            self.ready,
            self._data,
            self._payload,
            self._ack,
            self._nack,
            self._timeout,
            self._loop,
        )
        return actions[index]()

    def _data(self) -> Json:
        result = self.exchange()
        if result["status"] != "PASS":
            return result
        return {
            **result,
            "detail": "DATA TX complete; seq=1, payload=11 bytes. "
            "ACK captured without a host pause; inspect steps 4-5.",
        }

    def _payload(self) -> Json:
        rows = [
            row["line"]
            for row in self.exchange_rows
            if row["role"] == "RECEIVER" and " PAYLOAD_BYTES " in row["line"]
        ]
        payload = self.config["protocol"]["payload"]
        expected = f"LEN={len(payload)} HEX={payload.encode().hex().upper()} ASCII={payload}"
        if self.last is None or len(rows) != 1 or expected not in rows[0]:
            return {"status": "FAIL", "detail": "Receiver payload: NOT OBSERVED or mismatched"}
        return {
            **self.last,
            "detail": f"Receiver DATA: {payload}, "
            f"{len(payload)}/{len(payload)} bytes; seq=1. " + " | ".join(rows),
        }

    def _ack(self) -> Json:
        if self.last is None:
            msg = "No transaction captured; execute step 3"
            raise OSError(msg)
        return {
            **self.last,
            "detail": "Receiver ACK TX / Gateway ACK accepted: " + self.last["status"],
            "events": self.protocol_events(),
        }

    def _nack(self) -> Json:
        return self.exchange(nack=True)

    def _timeout(self) -> Json:
        print(
            "ENTER = withhold one ACK, retry, then verify recovery\n"
            "2 = intentional retry exhaustion, then verify recovery | q = quit",
            file=self.out,
        )
        choice = self.read().strip().lower()
        if choice == "q":
            raise KeyboardInterrupt
        if choice not in ("", "2"):
            msg = "Select ENTER, 2, or q"
            raise ValueError(msg)
        result = self.exchange(exhaust=True) if choice == "2" else self.exchange(drop=True)
        if result["status"] != "PASS":
            return result
        recovery = self.exchange()
        return {
            **recovery,
            "detail": "Bounded timeout/retry and next transaction: " + recovery["status"],
            "fault_transaction": result,
        }

    def _loop(self) -> Json:
        first = self.exchange()
        if first["status"] != "PASS":
            return first
        second = self.exchange(nack=True)
        return {
            **second,
            "detail": "DATA/ACK then DATA/NACK/RETRY/ACK: " + second["status"],
            "first_transaction": first,
            "sequence_policy": "Existing R command starts each independent transaction at seq=1",
        }

    def protocol_events(self) -> list[str]:
        """Return firmware timestamps from the captured transaction."""
        return [row["line"] for row in self.exchange_rows if " T=" in row["line"]]

    def close(self) -> None:
        """Attempt standby on both radios, then release both serial monitors."""
        self.closing = True
        if self.monitors:
            try:
                self._park()
            except (OSError, TimeoutError) as error:
                self.log.record("HOST", str(error), "FAIL", str(error))
        for monitor in self.monitors.values():
            try:
                rf.stop_rf_monitor(monitor)
            except OSError as error:
                self.log.record("HOST", "Serial cleanup failed: " + str(error), "FAIL", str(error))
        self.stop.set()
        if self.reader:
            self.reader.join(timeout=2)
        self.monitors.clear()
        self.reader = None


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
        print(HELP, file=self.out)

    def _skip(self) -> bool:
        if self.index < OPTIONAL_FIRST:
            print("[BLOCKED] This checkpoint is required", file=self.out)
            return True
        self.log.results[str(self.index + 1)] = {"status": "SKIPPED", "detail": "operator choice"}
        self.log.finish()
        if self.index == len(STEPS) - 1:
            return False
        self.index += 1
        return True

    def _execute(self, key: str) -> None:
        current = self.log.results.get(str(self.index + 1))
        if key == "" and current and current["status"] == "PASS":
            if self.index == len(STEPS) - 1:
                print("All checkpoints reviewed. r = repeat, q = quit", file=self.out)
                return
            self.index += 1
        self.log.step = self.index
        # Repeating an earlier operation invalidates all dependent checkpoints.
        self.log.results = {
            key: value for key, value in self.log.results.items() if int(key) <= self.index + 1
        }
        print("[WAITING] Executing; Ctrl-C stops safely...", file=self.out, flush=True)
        try:
            result = self.hardware.step(self.index)
        except TimeoutError as error:
            result = {"status": "TIMEOUT", "detail": str(error)}
        except (OSError, ValueError, KeyError) as error:
            result = {"status": "BLOCKED", "detail": str(error)}
        self.log.results[str(self.index + 1)] = result
        self.log.record(
            "HOST",
            result["detail"],
            result["status"],
            result["detail"] if result["status"] != "PASS" else None,
        )
        self.log.finish()

    def _input(self, key: str) -> bool:
        if key == "q":
            return False
        if key == "h":
            print(
                "b/l/h never repeat RF. r explicitly repeats the displayed step. "
                "Failures stay on the same step. Steps 6-8 are optional. "
                "q also stops after a failure. Ctrl-C stops a running step.",
                file=self.out,
            )
        elif key == "l":
            for row in self.log.snapshot()[-15:]:
                print(row["timestamp"], row["role"], row["line"], file=self.out)
        elif key == "b":
            self.index = max(0, self.index - 1)
        elif key == "s":
            return self._skip()
        elif key in ("", "r"):
            self._execute(key)
        else:
            print("[WAITING] Unknown input; h for help", file=self.out)
        return True

    def run(self) -> None:
        """Advance only in response to terminal input and always clean up."""
        print(
            "========================================\n"
            "       LoRa ACK/NACK DEBUG CONSOLE\n"
            "========================================\n"
            "Mode: REAL RF | Protocol: DATA / ACK / NACK\n"
            "No automatic flashing. Each ENTER runs one checkpoint.\n"
            "Known bench fault: Receiver previously restarted with replies enabled.\n"
            "RF begins only at step 3; press q any time to park and close.\n",
            file=self.out,
        )
        try:
            while True:
                self._display()
                if not self._input(self.read().strip().lower()):
                    break
        except EOFError, StopIteration, KeyboardInterrupt:
            print("\nStopping safely...", file=self.out)
        finally:
            self.hardware.close()
            self.log.finish()
            print(f"\nLogs: {self.log.path}", file=self.out)
            for index, result in self.log.results.items():
                print(f"Step {index}: {result['status']}", file=self.out)


def main() -> None:
    """Start the console without command-line port or flashing options."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    log = Session(ROOT / "artifacts/rf-debug" / stamp)
    Console(Hardware(log), log).run()


if __name__ == "__main__":
    main()
