"""One-attempt UPDI reads with an explicit no-register-write transaction path."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import serial

from .classify import classify_event
from .identity import ConnectionIdentity, discover_serial_ports


CONTROL_ADDRESSES = (0, 1, 2, 3, 7, 8, 9, 10, 11, 11, 12, 4, 5)
READ_POLICY = "no STCS, STS, programming key, reset, or NVM write"
ASI_OCD_STATUS = 0x05
ASI_OCD_MESSAGE = 0x0D
OCDMV = 0x10


@dataclass(frozen=True)
class ProbeResult:
    success: bool
    stage: str
    tx: bytes
    echo: bytes
    response: bytes
    latency_ms: float
    error_type: str | None
    raw_path: str
    raw_sha256: str


class ProbeFailure(RuntimeError):
    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage


class _ReadOnlyLink:
    def __init__(self, port, baud: int, timeout: float):
        self.port = port
        self.baud = baud
        self.ser = serial.Serial(
            port=str(port), baudrate=baud, parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_TWO, timeout=timeout, write_timeout=timeout,
            xonxoff=False, rtscts=False, dsrdtr=False, exclusive=True,
        )
        self.events: list[dict] = []

    def close(self) -> None:
        self.ser.close()

    def _exchange(self, frame: bytes) -> None:
        start = time.monotonic_ns()
        try:
            count = self.ser.write(frame)
        except (OSError, serial.SerialException) as error:
            self.events.append({"kind": "tx", "ns": start, "hex": frame.hex(), "count": 0})
            raise ProbeFailure("HOST_TX", f"serial write failed: {error}") from error
        self.events.append({"kind": "tx", "ns": start, "end_ns": time.monotonic_ns(),
                            "hex": frame.hex(), "count": count, "baud": self.ser.baudrate})
        if count != len(frame):
            raise ProbeFailure("HOST_TX", f"short serial write: expected {len(frame)} bytes, wrote {count}")
        echo_start = time.monotonic_ns()
        try:
            echo = self.ser.read(len(frame))
        except (OSError, serial.SerialException) as error:
            raise ProbeFailure("LOCAL_ECHO", f"echo read failed: {error}") from error
        self.events.append({"kind": "echo", "ns": echo_start, "end_ns": time.monotonic_ns(),
                            "hex": echo.hex(), "requested": len(frame), "baud": self.ser.baudrate})
        if echo != frame:
            raise ProbeFailure("LOCAL_ECHO", f"echo mismatch: expected {frame.hex()} received {echo.hex()}")

    def _response(self, length: int, stage: str) -> bytes:
        start = time.monotonic_ns()
        try:
            response = self.ser.read(length)
        except (OSError, serial.SerialException) as error:
            raise ProbeFailure(stage, f"response read failed: {error}") from error
        self.events.append({"kind": "response", "ns": start, "end_ns": time.monotonic_ns(),
                            "hex": response.hex(), "requested": length, "baud": self.ser.baudrate,
                            "stage": stage})
        if len(response) != length:
            raise ProbeFailure(stage, f"missing response: expected {length} bytes received {response.hex()}")
        return response

    def synchronize(self) -> None:
        for _ in range(2):
            self.ser.baudrate = 300
            try:
                self._exchange(b"\x00")
            finally:
                self.ser.baudrate = self.baud

    def sib(self) -> bytes:
        self._exchange(b"\x55\xe6")  # UPDI SIB request, not a programming key.
        return self._response(32, "UPDI_CONTROL_RESPONSE")

    def control(self, address: int, stage: str = "UPDI_CONTROL_RESPONSE") -> int:
        if not 0 <= address <= 0x0F:
            raise ValueError("UPDI control-space address must be 0..15")
        self._exchange(bytes((0x55, 0x80 | address)))
        return self._response(1, stage)[0]

    def data8(self, address: int) -> int:
        if not 0 <= address <= 0xFF:
            raise ValueError("strict read-only backend supports only direct 8-bit data reads")
        self._exchange(bytes((0x55, 0x00, address)))
        return self._response(1, "ACC_DATA_RESPONSE")[0]


def collect_ocd_messages(read_status, read_message, *, max_bytes: int = 256) -> dict:
    """Read only valid OCD bytes, stopping when OCDMV clears or at the bound."""
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    statuses = [read_status()]
    message = bytearray()
    while statuses[-1] & OCDMV and len(message) < max_bytes:
        message.append(read_message())
        statuses.append(read_status())
    return {"statuses": statuses, "message": bytes(message),
            "truncated": bool(statuses[-1] & OCDMV and len(message) == max_bytes)}


def _live_adapter(connection: ConnectionIdentity):
    matches = [item for item in discover_serial_ports() if item.id_path == connection.adapter.id_path]
    if len(matches) != 1:
        raise ValueError(f"expected one live adapter for ID_PATH {connection.adapter.id_path!r}; found {len(matches)}")
    live = matches[0]
    expected = connection.adapter
    if (live.vid, live.pid, live.id_path) != (expected.vid, expected.pid, expected.id_path):
        raise ValueError("live adapter identity changed; refusing ambiguous probe")
    if not live.by_path:
        raise ValueError("stable by-path link is unavailable; refusing serial open")
    return live


def _event_bytes(events: list[dict], kind: str) -> bytes:
    return b"".join(bytes.fromhex(event.get("hex", "")) for event in events if event.get("kind") == kind)


def _run_probe(connection, mode, baud, output_path, *, address=None, timeout=1.0) -> ProbeResult:
    if mode not in {"sib", "control", "read", "ocd-message"}:
        raise ValueError("only bounded SIB, control, direct data, and OCD-message reads are allowed")
    if baud <= 0 or timeout <= 0:
        raise ValueError("baud and timeout must be positive")
    if mode == "read" and address is None:
        raise ValueError("data read requires an address")
    if mode == "read" and not 0 <= address <= 0xFF:
        raise ValueError("strict read-only backend supports only direct 8-bit data reads")

    live = _live_adapter(connection)
    port = Path("/dev/serial/by-path") / live.by_path
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_ns = time.monotonic_ns()
    record = {
        "utc": datetime.now(timezone.utc).isoformat(), "baud": baud, "mode": mode,
        "address": address, "id_path": live.id_path, "by_path": live.by_path,
        "write_policy": READ_POLICY, "initialization": "two 300-baud BREAK synchronization bytes only",
        "events": [], "values": {}, "exit": 1, "first_anomaly": None,
    }
    link = None
    try:
        try:
            link = _ReadOnlyLink(port, baud, timeout)
        except (OSError, serial.SerialException) as error:
            raise ProbeFailure("SERIAL_OPEN", f"serial open failed: {error}") from error
        link.synchronize()
        if mode == "sib":
            record["values"]["SIB"] = link.sib().hex()
        elif mode == "control":
            record["values"] = {f"CS{item:02x}": link.control(item) for item in CONTROL_ADDRESSES}
        elif mode == "read":
            record["values"][f"LDS {address:02x}"] = link.data8(address)
        else:
            snapshot = collect_ocd_messages(
                lambda: link.control(ASI_OCD_STATUS, "OCD_STATUS"),
                lambda: link.control(ASI_OCD_MESSAGE, "OCD_MESSAGE"),
            )
            record["values"] = {
                "ASI_OCD_STATUS_SEQUENCE": snapshot["statuses"],
                "ASI_OCD_MESSAGE_HEX": snapshot["message"].hex(),
                "ASI_OCD_MESSAGE_TRUNCATED": snapshot["truncated"],
            }
        record["exit"] = 0
    except ProbeFailure as error:
        record["failure_stage"] = error.stage
        record["first_anomaly"] = str(error)
    finally:
        if link is not None:
            record["events"] = link.events
            link.close()
    record["latency_ms"] = (time.monotonic_ns() - start_ns) / 1_000_000
    output_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    events = record["events"]
    tx, echo, response = (_event_bytes(events, kind) for kind in ("tx", "echo", "response"))
    failure_stage = record.get("failure_stage")
    if failure_stage:
        last_response = next((e for e in reversed(events) if e["kind"] == "response"), None)
        classification = classify_event({
            "operation": failure_stage, "error_type": record["first_anomaly"],
            "tx_hex": tx.hex(), "echo_hex": echo.hex(),
            "expected_len": last_response.get("requested") if last_response else None,
            "actual_len": len(bytes.fromhex(last_response["hex"])) if last_response else None,
        })
        stage = failure_stage if classification == "UNKNOWN" else classification
    else:
        stage = "PASS"
    raw_sha256 = hashlib.sha256(output_path.read_bytes()).hexdigest()
    return ProbeResult(record["exit"] == 0, stage, tx, echo, response,
                       record["latency_ms"], record["first_anomaly"],
                       str(output_path), raw_sha256)


def run_sib_probe(connection, baud, output_path, **kwargs) -> ProbeResult:
    return _run_probe(connection, "sib", baud, output_path, **kwargs)


def run_control_read(connection, baud, output_path, **kwargs) -> ProbeResult:
    return _run_probe(connection, "control", baud, output_path, **kwargs)


def run_data_read(connection, address, baud, output_path, **kwargs) -> ProbeResult:
    return _run_probe(connection, "read", baud, output_path, address=address, **kwargs)


def run_ocd_message_probe(connection, baud, output_path, **kwargs) -> ProbeResult:
    return _run_probe(connection, "ocd-message", baud, output_path, **kwargs)
