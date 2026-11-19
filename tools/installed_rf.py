"""Run the installed SRAM-only DATA/ACK and controlled DATA/NACK bench."""

from __future__ import annotations

import argparse
import hashlib
import json
import queue
import time
import tomllib
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from tools import rf_proof as rf

if TYPE_CHECKING:
    from collections.abc import Callable

TRIALS = 10
AVR128DA28_FLASH_BYTES = 128 * 1024


class Capture:
    """Own both UPDI monitors and retain the connection provenance of each line."""

    def __init__(self, proof: rf.ProofRun) -> None:
        """Create a shared event stream without opening either adapter."""
        self.proof = proof
        self.incoming: queue.Queue[tuple[str, str, bytes | None]] = queue.Queue()
        self.monitors: dict[str, rf.Json] = {}
        self.generations = dict.fromkeys(rf.PORTS, 0)
        self.connections: dict[str, tuple[str, int]] = {}
        self.lines: list[str] = []
        self.after_rf: set[tuple[str, int]] = set()

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
            "received_utc": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "received_monotonic_ns": time.monotonic_ns(),
        }
        with (self.proof.run_dir / "events.jsonl").open("a") as out:
            out.write(json.dumps(row) + "\n")
        if stream == "stdout":
            self.lines.append(line)

    def connect(self, role: str, *, after_rf: bool = False) -> None:
        """Open a new capture segment without explicitly resetting the target."""
        self.close(role)
        self.generations[role] += 1
        generation = self.generations[role]
        label = f"{role}-{generation}"
        self.connections[label] = (role, generation)
        if after_rf:
            self.after_rf.add((role, generation))
        self.monitors[role] = rf.start_rf_monitor(self.proof, label, rf.PORTS[role], self.incoming)
        self.record(role, "capture_open", label, generation)

    def close(self, role: str) -> None:
        """Release a monitor while leaving already queued output attributable."""
        monitor = self.monitors.pop(role, None)
        if monitor is not None:
            code = rf.stop_rf_monitor(monitor)
            self.record(role, "capture_close", str(code), self.generations[role])

    def disconnected(self, role: str) -> bool:
        """Return whether the active monitor can no longer take commands."""
        return role not in self.monitors or self.monitors[role]["process"].poll() is not None

    def send(self, role: str, command: str) -> int:
        """Queue one command once. A DATA command is never replayed on disconnect."""
        if self.disconnected(role):
            self.connect(role)
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

    def wait(self, predicate: Callable[[], object], timeout: float) -> bool:
        """Poll until evidence arrives, with at most two reconnects per role per wait."""
        deadline = time.monotonic() + timeout
        start = self.generations.copy()
        while time.monotonic() < deadline:
            if predicate():
                return True
            self.drain_one(0.1)
            for role in tuple(self.monitors):
                if self.disconnected(role) and self.generations[role] < start[role] + 2:
                    self.connect(role)
        return bool(predicate())

    def exchange(self, start: int, *, nack: bool) -> rf.Json | None:
        """Assess only the lines received since the DATA trigger."""
        return rf.assess_installed_exchange(self.lines[start:], nack)

    def marker(self, role: str, command: str, marker: str) -> None:
        """Send a control and require its role-specific completion."""
        start = self.send(role, command)
        if not self.wait(lambda: f"[{role.upper()}] {marker}" in self.lines[start:], 20):
            msg = f"{role}: missing {marker} after {command}"
            raise TimeoutError(msg)


def verify_snapshots(snapshot: Path, receipt_path: Path) -> dict[str, rf.Json]:
    """Require enrolled serials and full saved Flash matching the known bench pair."""
    images: dict[str, rf.Json] = json.loads(receipt_path.read_text())["images"]
    inventory = json.loads((rf.ROOT / "config/current_hardware.json").read_text())
    for role, environment in (("gateway", "sender_hello"), ("receiver", "receiver")):
        image = images[role.upper()]
        flash = (snapshot / f"{role}-flash.bin").read_bytes()
        historical = (receipt_path.parent / f"{role}-live-flash.bin").read_bytes()
        serial = (snapshot / f"{role}-sernum.bin").read_bytes().hex()
        signature = (snapshot / f"{role}-signature.bin").read_bytes().hex()
        digest = hashlib.sha256(flash[image["start"] : image["end"]]).hexdigest()
        if (
            len(flash) != AVR128DA28_FLASH_BYTES
            or flash != historical
            or serial != image["serial_number"]
            or serial != inventory[role]["device_serial_hex"]
            or signature != "1e970a"
            or image["environment"] != environment
            or image["port"] != rf.PORTS[role]
            or not image["verified"]
            or digest != image["readback_region_sha256"]
        ):
            msg = f"{role}: readback differs from the reviewed installed bench image"
            raise ValueError(msg)
    return images


def verify_console(capture: Capture, role: str, image: rf.Json, profile: rf.Json) -> None:
    """Require the live build ID and matching radio profile before any DATA trigger."""
    start = capture.send(role, "?")
    label = role.upper()

    def matches() -> bool:
        """Check live build identity, protocol, silicon version and PHY together."""
        lines = capture.lines[start:]
        return (
            f"[{label}] BUILD_ID={image['build_id']}" in lines
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
        for line in capture.lines[start:]
    )


def run(capture: Capture, images: dict[str, rf.Json], profile: rf.Json) -> int:
    """Run each bounded case sequentially and park both radios on exit."""
    outcomes: list[rf.Json] = []
    parked = {}
    error = None
    try:
        for role in ("receiver", "gateway"):
            capture.marker(role, "R", "RX_READY")
            verify_console(capture, role, images[role.upper()], profile)
        for nack in (False, True):
            for trial in range(1, TRIALS + 1):
                capture.marker("receiver", "R", "RX_READY")
                capture.marker("gateway", "R", "RX_READY")
                capture.send("receiver", "N" if nack else "A")
                if nack:
                    verify_console(capture, "receiver", images["RECEIVER"], profile)
                # Keep OCD traffic off the Tracker while it receives and replies.
                capture.close("receiver")
                start = capture.send("gateway", "S")
                capture.wait(partial(gateway_finished, capture, start), 30)
                capture.connect("receiver", after_rf=True)
                assess = partial(capture.exchange, start, nack=nack)
                capture.wait(assess, 45)
                result = assess()
                row = {"case": "NACK" if nack else "ACK", "trial": trial, "result": result}
                outcomes.append(row)
                capture.proof.note("trials.json", json.dumps(outcomes, indent=2) + "\n")
                if result is None:
                    msg = f"{row['case']} {trial}/{TRIALS}: incomplete two-sided RF evidence"
                    raise TimeoutError(msg)
    except (OSError, ValueError) as exc:
        error = str(exc)
    finally:
        for role in rf.PORTS:
            try:
                capture.marker(role, "P", "PARKED E=0")
                parked[role] = True
            except OSError:
                parked[role] = False
            finally:
                capture.close(role)
        owners = rf.check_port_owners(capture.proof, "postflight")
        report = {"trials": outcomes, "error": error, "parked": parked, "port_owners": owners}
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
