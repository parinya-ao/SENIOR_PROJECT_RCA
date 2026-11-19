"""Synthetic replay only: none of these tests accesses a target."""

import ast
import copy
import hashlib
import inspect
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from tools.rca import gate1
from tools.rca.gate1_live import (
    MAILBOX_PROBE_TIMEOUT_S,
    STATUS_STABILITY_TIMEOUT_S,
    Gate1Audit,
    TracePort,
    _read_block,
    controlled_cpu_reset,
    firmware_identity_from_events,
    gpr_roundtrip_succeeded,
    halted_gpr_roundtrip,
    mailbox_snapshot,
    part_from_signature,
    preservation_diff,
    read_data_space_byte,
    read_updi_pesig,
    reenable_uart_output,
    resume_cpu_if_stopped,
    roundtrip_gpr,
    roundtrip_gpr_16,
    startup_profile,
    store_data_space_byte,
    sts8_with_wide_gpr_address,
    target_profile,
    wait_for_reader_idle,
)

Json = Any

IDENTITY = {
    "signature": "1e970a",
    "serial": "synthetic-tracker",
    "build": "synthetic-build",
    "config": "synthetic-config",
    "role": "receiver",
}
EVENTS = [
    "BOOT",
    "IDENTITY",
    "STATUS",
    "RESULT",
    "RTT_LAST",
    "RTT_MIN",
    "RTT_MAX",
    "RTT_COUNT",
    "RX_DONE_COUNT",
    "DECODE_ERRORS",
    "CONTROL_REJECTS",
    "REG",
    "STATUS_END",
]


def transaction(index: int) -> Json:
    lines = []
    for name in EVENTS:
        extra = " rc=0 v=0"
        if name == "IDENTITY":
            extra = " build=synthetic-build config=synthetic-config"
        if name == "STATUS":
            extra = " ready=1 overflow=0"
        lines.append(f"A t=1 e={name} s=0{extra}\n")
    return {
        "transaction_index": index,
        "monotonic_start_ns": index * 100,
        "monotonic_end_ns": index * 100 + 50,
        "identity": IDENTITY.copy(),
        "request_tx_hex": "5354415455530a",
        "status_payload_raw": "".join(lines),
        "transport_exchanges": [{"expected_length": 1, "expected_hex": "40", "actual_hex": "40"}],
        "monitor_exit_code": None,
        "transport_error": None,
        "timeout_reason": None,
    }


class Gate1Tests(unittest.TestCase):
    def assess(self, rows: Iterable[Json], **kwargs: Json) -> Json:
        kwargs.setdefault("safe_path", True)
        return gate1.assess(rows, IDENTITY, **kwargs)

    def test_T01_twenty_successes(self) -> None:
        self.assertTrue(callable(getattr(gate1, "assess", None)), "offline Gate 1 assessor missing")
        result = self.assess([transaction(i) for i in range(1, 21)])
        self.assertEqual(
            (result["verdict"], result["passed"], result["attempted"]), ("GATE1_PASS", 20, 20)
        )

    def test_T02_first_failure_stops_consumption(self) -> None:
        def rows() -> Iterator[Json]:
            yield transaction(1)
            row = transaction(2)
            row["timeout_reason"] = "reader deadline"
            yield row
            self.fail("read beyond first failure")

        result = self.assess(rows())
        self.assertEqual(
            (result["attempted"], result["first_failure"]["transaction_index"]), (2, 2)
        )
        self.assertEqual(result["latency_ms"]["median"], 0.00005)

    def test_T03_empty_bytes_are_zero_length(self) -> None:
        result = gate1.response(1, None, b"")
        self.assertEqual((result["actual_response_hex"], result["actual_response_length"]), ("", 0))
        self.assertEqual(result["classification"], "UPDI_RESPONSE_LENGTH_MISMATCH")

    def test_T04_original_exception_preserved(self) -> None:
        row = transaction(1)
        message = "UPDI response mismatch: expected None, received b''\n"
        row["transport_error"] = message
        result = self.assess([row])
        self.assertEqual(result["first_failure"]["transport_error"], message)
        self.assertEqual(result["first_failure"]["parsed_error"]["response_length"], 0)

    def test_T05_incomplete_status_fails(self) -> None:
        row = transaction(1)
        row["status_payload_raw"] = row["status_payload_raw"].replace("e=STATUS_END", "e=MISSING")
        self.assertEqual(self.assess([row])["classification"], "EVIDENCE_INCOMPLETE")
        self.assertEqual(
            gate1.response(2, None, b"\x40")["classification"], "UPDI_RESPONSE_LENGTH_MISMATCH"
        )

    def test_T06_response_value_mismatch(self) -> None:
        row = transaction(1)
        row["transport_exchanges"][0]["actual_hex"] = "62"
        self.assertEqual(self.assess([row])["classification"], "UPDI_RESPONSE_VALUE_MISMATCH")

    def test_T07_timeout_is_failure(self) -> None:
        row = transaction(1)
        row["timeout_reason"] = "deadline"
        self.assertEqual(
            (self.assess([row])["verdict"], self.assess([row])["timed_out"]), ("GATE1_FAIL", 1)
        )

    def test_T08_monitor_exit_is_not_usb_disconnect(self) -> None:
        row = transaction(1)
        row["monitor_exit_code"] = 1
        result = self.assess([row])
        self.assertEqual(result["classification"], "MONITOR_EXIT")
        self.assertEqual(result["usb_disconnected"], "UNKNOWN")

    def test_T09_wrong_identity_rejected(self) -> None:
        row = transaction(1)
        row["identity"]["serial"] = "other"
        self.assertEqual(self.assess([row])["classification"], "IDENTITY_MISMATCH")

    def test_T10_existing_owner_blocks_without_consuming(self) -> None:
        self.assertEqual(
            self.assess(iter(()), owners=[123])["classification"], "PORT_OWNERSHIP_CONFLICT"
        )

    def test_T11_non_status_and_rf_commands_rejected(self) -> None:
        row = transaction(1)
        row["request_tx_hex"] = b"SEND 4869\n".hex()
        self.assertEqual(self.assess([row])["classification"], "UNSAFE_COMMAND_PATH")

    def test_T12_offline_tool_has_no_hardware_or_process_api(self) -> None:
        tree = ast.parse(inspect.getsource(gate1))
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertFalse(
            any(
                x in ast.unparse(n)
                for n in imports
                for x in ["serial", "subprocess", "pymcuprog", "receiver_boot"]
            )
        )
        self.assertFalse(
            any(
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr
                in {"write_bytes", "write_text", "send_break", "reset", "program_application"}
                for n in ast.walk(tree)
            )
        )

    def test_T13_unsafe_initialization_blocks_without_read(self) -> None:
        class ExplodingRows:
            def __init__(self, fail: Any) -> None:
                self.fail = fail

            def __iter__(self) -> Iterator[Json]:
                self.fail("blocked path consumed a transaction")
                return iter(())

        self.assertEqual(
            self.assess(ExplodingRows(self.fail), safe_path=False)["verdict"],
            "GATE1_BLOCKED",
        )

    def test_T14_detects_hash_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            p = Path(name) / "raw"
            p.write_bytes(b"original")
            hashes = {"raw": hashlib.sha256(p.read_bytes()).hexdigest()}
            p.write_bytes(b"changed")
            self.assertEqual(gate1.verify_hashes(Path(name), hashes), ["raw"])

    def test_T15_verification_never_modifies_originals(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            p = Path(name) / "raw"
            p.write_bytes(b"original")
            hashes = {"raw": hashlib.sha256(p.read_bytes()).hexdigest()}
            self.assertEqual(gate1.verify_hashes(Path(name), hashes), [])
            self.assertEqual(p.read_bytes(), b"original")
            self.assertEqual(
                gate1.verify_hashes(Path(name), {"missing": hashes["raw"]}), ["missing"]
            )

    def test_T16_monotonic_order_and_duplicate_index(self) -> None:
        for field, value in [("transaction_index", 1), ("monotonic_start_ns", 149)]:
            row = transaction(2)
            row[field] = value
            self.assertEqual(
                self.assess([transaction(1), row])["classification"], "EVIDENCE_INCOMPLETE"
            )

    def test_T17_missing_response_is_unknown(self) -> None:
        result = gate1.response(1, None, None)
        self.assertEqual(result["actual_response_length"], "UNKNOWN")
        self.assertEqual(result["actual_response_hex"], "UNKNOWN")
        self.assertEqual(result["classification"], "EVIDENCE_INCOMPLETE")

    def test_T18_deterministic_json_and_no_input_mutation(self) -> None:
        import json

        rows = [transaction(1)]
        before = copy.deepcopy(rows)
        first = self.assess(rows)
        self.assertEqual(first, self.assess(rows))
        self.assertEqual(rows, before)
        self.assertEqual(json.loads(json.dumps(first)), first)
        self.assertNotEqual(first["verdict"], "GATE1_PASS")

    def test_T19_normal_two_break_startup_is_authorized(self) -> None:
        profile = startup_profile(Path("third_party/upditerm/upditerm.py"))
        self.assertEqual(profile["break_calls"], 2)
        self.assertFalse(profile["startup_reset"])
        self.assertTrue(profile["normal_monitor_startup_authorized"])

    def test_T20_trace_port_preserves_raw_empty_and_nonempty_reads(self) -> None:
        class Sink:
            current_transaction = 1
            expected_length = 1
            expected_value = b"@"

            def __init__(self) -> None:
                self.rows: list[Json] = []

            def transport(self, **row: Json) -> None:
                self.rows.append(
                    {
                        "transaction_index": self.current_transaction,
                        "expected_response_length": self.expected_length,
                        **row,
                    }
                )

        class Port:
            baudrate = 38400
            parity = "E"
            stopbits = 2
            timeout = 1
            write_timeout = None

            def __init__(self) -> None:
                self.reads: list[bytes] = [b"", b"@"]
                self.writes: list[bytes] = []

            def read(self, n: int) -> bytes:
                return self.reads.pop(0)

            def write(self, data: bytes) -> int:
                self.writes.append(bytes(data))
                return len(data)

        sink: Any = Sink()
        raw = Port()
        traced = TracePort(raw, sink)
        self.assertEqual(traced.read(1), b"")
        self.assertEqual(traced.read(1), b"@")
        self.assertEqual((sink.rows[0]["actual_rx_hex"], sink.rows[0]["actual_rx_length"]), ("", 0))
        self.assertEqual(
            (sink.rows[1]["actual_rx_hex"], sink.rows[1]["actual_rx_length"]), ("40", 1)
        )
        self.assertTrue(all(row["expected_response_length"] == 1 for row in sink.rows))

    def test_T21_port_trace_records_exact_write_and_timestamps(self) -> None:
        class Sink:
            current_transaction = 7
            expected_length = None
            expected_value = None

            def __init__(self) -> None:
                self.rows: list[Json] = []

            def transport(self, **row: Json) -> None:
                self.rows.append(
                    {
                        "transaction_index": self.current_transaction,
                        "expected_response_length": self.expected_length,
                        **row,
                    }
                )

        class Port:
            baudrate = 38400
            parity = "E"
            stopbits = 2
            timeout = 1
            write_timeout = None

            def write(self, data: bytes) -> int:
                return len(data)

        sink: Any = Sink()
        traced = TracePort(Port(), sink)
        self.assertEqual(traced.write(b"\x55\x85"), 2)
        row = sink.rows[0]
        self.assertEqual(
            (row["transaction_index"], row["host_tx_hex"], row["host_tx_length"]), (7, "5585", 2)
        )
        self.assertLessEqual(row["serial_write_start_ns"], row["serial_write_end_ns"])

    def test_T22_read_only_extended_LDS_uses_verified_sigrow_address(self) -> None:
        class Link:
            def __init__(self) -> None:
                self.frames: list[Json] = []
                self.lengths: list[int] = []

            def instr(self, frame: Json) -> None:
                self.frames.append(frame)

            def recv(self, length: int) -> bytes:
                self.lengths.append(length)
                return b"\x1e"

        link = Link()
        self.assertEqual(read_data_space_byte(link, 0x1110), 0x1E)
        self.assertEqual(link.frames, [[0x04, 0x10, 0x11]])
        self.assertEqual(link.lengths, [1])

    def test_T23_live_cli_help_loads_without_opening_hardware(self) -> None:
        proc = subprocess.run(
            [sys.executable, "tools/rca/gate1_live.py", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--execute-gate1", proc.stdout)
        self.assertIn("--target", proc.stdout)
        self.assertIn("--halt-write-probe", proc.stdout)
        self.assertIn("--wide-gpr-access", proc.stdout)
        self.assertIn("--controlled-cpu-reset", proc.stdout)

    def test_gate1_provenance_covers_migrated_arq_sources(self) -> None:
        from tools.rca import gate1_live

        for name in ("src/app/arq/application.cpp", "src/app/arq/radio.cpp"):
            with self.subTest(source=name):
                self.assertIn(name, gate1_live.SOURCE_HASH_PATHS)
                self.assertTrue((gate1_live.ROOT / name).is_file())

    def test_T24_part_identity_comes_from_read_signature_not_SIB_label(self) -> None:
        self.assertEqual(part_from_signature(bytes.fromhex("1e970a")), "AVR128DA28")
        self.assertIsNone(part_from_signature(bytes.fromhex("1e9709")))
        self.assertIsNone(part_from_signature(None))

    def test_T25_status_output_timeout_is_not_a_low_level_updi_response_error(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            audit = Gate1Audit(Path(name))
            audit.current_transaction = 1
            audit.status_command_hex = b"STATUS\n".hex()
            audit.current_status_output = bytearray()
            audit.fail(
                TimeoutError("STATUS response deadline"),
                "STATUS_RESPONSE_WAIT",
                failure_layer="STATUS_RESPONSE",
            )
            if audit.first_failure is None:
                self.fail("first failure was not recorded")
            self.assertEqual(audit.first_failure["failure_boundary"], "STATUS_MONITOR_OUTPUT")
            self.assertEqual(audit.first_failure["actual_monitor_stdout_hex"], "")
            self.assertEqual(audit.first_failure["actual_monitor_stdout_length"], 0)
            self.assertIsNone(audit.first_failure["expected_response_length"])

    def test_T26_mailbox_snapshot_reads_flags_fifo_reset_and_ocd_without_writes(self) -> None:
        class Link:
            def __init__(self) -> None:
                self.addresses: list[Any] = []
                self.cs: list[int] = []

            def lds8(self, address: Any) -> Any:
                self.addresses.append(address)
                return {0x1E: 1, 0x1F: 0x0A, 0x1C: 4, 0x40: 2}[address]

            def ldcs(self, address: Any) -> int:
                self.cs.append(address)
                return 0x10

            def instr(self, frame: Any) -> None:
                self.addresses.append(tuple(frame))

            def recv(self, n: Any) -> bytes:
                return b"\x00"

        link = Link()
        result = mailbox_snapshot(link)
        self.assertEqual(
            result,
            {
                "uart_flags": 1,
                "uart_rx": 0x0A,
                "app_reset_flags": 4,
                "rstfr": 2,
                "ocd_status": 0x10,
                "ocd_message_status": 0,
            },
        )
        self.assertEqual(link.addresses[:4], [0x1E, 0x1F, 0x1C, 0x40])
        self.assertEqual(link.addresses[-1], (0x04, 0x19, 0x0F))
        self.assertEqual(link.cs, [0x05])

    def test_T27_missing_status_identity_is_not_reported_as_runtime_firmware_identity(self) -> None:
        self.assertIsNone(firmware_identity_from_events([]))
        self.assertEqual(
            firmware_identity_from_events(
                [
                    {
                        "e": "IDENTITY",
                        "role": "receiver",
                        "build": "observed-build",
                        "config": "observed-config",
                    }
                ]
            ),
            {"build_id": "observed-build", "config_hash": "observed-config", "role": "receiver"},
        )

    def test_T28_reenable_uart_preserves_pending_rx_flag_and_reads_back(self) -> None:
        class Link:
            def __init__(self) -> None:
                self.flags = 2
                self.writes: list[tuple[int, int]] = []

            def lds8(self, address: Any) -> Any:
                self.assert_flags_address = address
                return self.flags

            def sts8(self, address: Any, value: Any) -> None:
                self.writes.append((address, value))
                self.flags = value

        link = Link()
        self.assertEqual(
            reenable_uart_output(link, 0x1E, 0x01), {"before": 2, "after": 3, "write": 3}
        )
        self.assertEqual(link.writes, [(0x1E, 3)])

    def test_T29_gateway_target_uses_gateway_identity_and_sender_application(self) -> None:
        hardware = {
            "receiver": {"port_path": "/dev/receiver", "device_serial_hex": "tracker-id"},
            "gateway": {"port_path": "/dev/gateway", "device_serial_hex": "gateway-id"},
        }
        verified = {
            "receiver": {"build_id": "receiver-build"},
            "sender": {"build_id": "sender-build"},
        }
        result = target_profile("gateway", hardware, verified, "config-hash")
        self.assertEqual(result["port_path"], "/dev/gateway")
        self.assertEqual(result["device_serial_hex"], "gateway-id")
        self.assertEqual(result["firmware_role"], "sender")
        self.assertEqual(
            result["expected_identity"],
            {"build_id": "sender-build", "config_hash": "config-hash", "role": "sender"},
        )

    def test_T30_gpr_roundtrip_restores_original_volatile_value(self) -> None:
        class Link:
            def __init__(self) -> None:
                self.value = 0x12
                self.writes: list[tuple[int, int]] = []
                self.read_pending = False

            def lds8(self, address: Any) -> Any:
                self.address = address
                return self.value

            def sts8(self, address: Any, value: Any) -> None:
                self.writes.append((address, value))
                self.value = value

            def instr(self, frame: Any) -> None:
                self.read_pending = True

            def recv(self, n: Any, expected: Any=None) -> Any:
                if expected is not None:
                    return expected
                self.read_pending = False
                return bytes([self.value])

            def send(self, data: Any) -> None:
                self.value = data[0]

        link = Link()
        self.assertEqual(
            roundtrip_gpr(link, 0x1D),
            {
                "address": 0x1D,
                "before": 0x12,
                "test_value": 0xED,
                "readback": 0xED,
                "readback16": 0xED,
                "restored": 0x12,
                "restored16": 0x12,
            },
        )
        self.assertEqual(link.writes, [(0x1D, 0xED), (0x1D, 0x12)])

    def test_T31_pesig_is_read_once_from_statusb(self) -> None:
        class Link:
            def __init__(self) -> None:
                self.addresses: list[Any] = []

            def ldcs(self, address: Any) -> int:
                self.addresses.append(address)
                return 6

        link = Link()
        self.assertEqual(read_updi_pesig(link), 6)
        self.assertEqual(link.addresses, [0x01])

    def test_T32_halted_gpr_probe_resumes_cpu_after_roundtrip(self) -> None:
        class Link:
            def __init__(self) -> None:
                self.status = 0
                self.gpr = 0x12
                self.controls: list[tuple[int, int]] = []

            def ldcs(self, address: Any) -> Any:
                return self.status

            def stcs(self, address: Any, value: Any) -> None:
                self.controls.append((address, value))
                self.status = 1 if value == 1 else 0

            def lds8(self, address: Any) -> Any:
                return self.gpr

            def sts8(self, address: Any, value: Any) -> None:
                self.gpr = value

            def instr(self, frame: Any) -> None:
                pass

            def recv(self, n: Any, expected: Any=None) -> Any:
                return expected if expected is not None else bytes([self.gpr])

            def send(self, data: Any) -> None:
                self.gpr = data[0]

        link = Link()
        result = halted_gpr_roundtrip(link, 0x1D, 0x04, 0x05, 0x01, 0x02, 0x01)
        self.assertEqual(result["scratch"]["readback"], 0xED)
        self.assertEqual(result["scratch"]["restored"], 0x12)
        self.assertEqual(result["resumed_status"] & 0x01, 0)
        self.assertEqual(link.controls, [(0x04, 0x01), (0x04, 0x02)])

    def test_T33_store_data_space_byte_uses_16_bit_address_and_strict_acks(self) -> None:
        class Link:
            def __init__(self) -> None:
                self.frames: list[Any] = []
                self.sent: list[Any] = []
                self.expected: list[bytes | None] = []

            def instr(self, frame: Any) -> None:
                self.frames.append(frame)

            def recv(self, n: Any, expected: Any=None) -> Any:
                self.expected.append(expected)
                return expected

            def send(self, data: Any) -> None:
                self.sent.append(data)

        link = Link()
        store_data_space_byte(link, 0x001D, 0xA5)
        self.assertEqual(link.frames, [[0x44, 0x1D, 0x00]])
        self.assertEqual(link.sent, [[0xA5]])
        self.assertEqual(link.expected, [b"\x40", b"\x40"])

    def test_T34_roundtrip_gpr16_restores_the_original_value(self) -> None:
        class Link:
            def __init__(self) -> None:
                self.value = 0x12
                self.read_data = False

            def lds8(self, address: Any) -> Any:
                return self.value

            def instr(self, frame: Any) -> None:
                if frame[0] == 0x04:
                    self.read_data = True
                elif frame[0] == 0x44:
                    self.address = frame[1] | (frame[2] << 8)

            def recv(self, n: Any, expected: Any=None) -> Any:
                if expected is not None:
                    return expected
                self.read_data = False
                return bytes([self.value])

            def send(self, data: Any) -> None:
                self.value = data[0]

        result = roundtrip_gpr_16(Link(), 0x001D)
        self.assertEqual(
            result,
            {
                "address": 0x001D,
                "before": 0x12,
                "test_value": 0xED,
                "readback": 0xED,
                "readback8": 0xED,
                "restored": 0x12,
                "restored8": 0x12,
            },
        )

    def test_T35_address_mode_probe_accepts_cross_mode_readback_only_when_restored(self) -> None:
        result = {"before": 0, "test_value": 0xFF, "readback": 0, "restored": 0}
        self.assertTrue(gpr_roundtrip_succeeded(result, 0xFF, 0))
        self.assertFalse(gpr_roundtrip_succeeded(result, 0xFF, 1))

    def test_T36_wide_gpr_counterfactual_uses_16_bit_sts_only_for_gprs(self) -> None:
        class Link:
            def __init__(self) -> None:
                self.frames: list[Any] = []
                self.sent: list[Any] = []
                self.other_writes: list[tuple[int, int]] = []

            def instr(self, frame: Any) -> None:
                self.frames.append(frame)

            def recv(self, n: Any, expected: Any=None) -> Any:
                return expected

            def send(self, data: Any) -> None:
                self.sent.append(data)

        link = Link()

        def base(updi: Any, address: Any, value: Any) -> None:
            updi.other_writes.append((address, value))

        sts8_with_wide_gpr_address(link, 0x1E, 1, base)
        sts8_with_wide_gpr_address(link, 0x40, 2, base)
        self.assertEqual(link.frames, [[0x44, 0x1E, 0x00]])
        self.assertEqual(link.sent, [[1]])
        self.assertEqual(link.other_writes, [(0x40, 2)])

    def test_T37_reader_idle_wait_is_bounded(self) -> None:
        lock = threading.Lock()
        self.assertTrue(wait_for_reader_idle(lock, 0))
        lock.acquire()
        try:
            self.assertFalse(wait_for_reader_idle(lock, 0))
        finally:
            lock.release()

    def test_T38_preservation_report_separates_explicit_host_fix_from_other_changes(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "host.py").write_text("fixed")
            (root / "other.txt").write_text("changed")
            expected = {
                "host.py": hashlib.sha256(b"old").hexdigest(),
                "other.txt": hashlib.sha256(b"old").hexdigest(),
            }
            report = preservation_diff(root, expected, {"host.py"})
            self.assertEqual(report["unexpected"], ["other.txt"])
            self.assertEqual(list(report["authorized_changes"]), ["host.py"])

    def test_T39_startup_block_discards_and_preserves_partial_prefix_before_boot(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            audit = Gate1Audit(root)
            console = type("Console", (), {"output": queue.Queue()})()
            for byte in b"=stale-prefix\n" + transaction(1)["status_payload_raw"].encode():
                console.output.put((byte, 1))
            terminal = type("Terminal", (), {"failure": None})()
            output = (root / "monitor.stdout.log").open("wb")
            try:
                lines, events, _raw = _read_block(
                    console,
                    audit,
                    terminal,
                    {
                        "role": "receiver",
                        "build_id": "synthetic-build",
                        "config_hash": "synthetic-config",
                    },
                    time.monotonic() + 2,
                    output,
                    startup=True,
                )
            finally:
                output.close()
            self.assertEqual(lines[0].split(" e=")[1].split()[0], "BOOT")
            self.assertIn(b"=stale-prefix\n", (root / "monitor.stdout.log").read_bytes())
            self.assertTrue(any(event["e"] == "STATUS_END" for event in events))

    def test_T40_controlled_cpu_reset_is_one_reset_followed_by_ocd_rekey(self) -> None:
        class Link:
            def __init__(self) -> None:
                self.actions: list[Any] = []

            def reset(self) -> None:
                self.actions.append("reset")

            def key(self, value: Any) -> None:
                self.actions.append(("key", value))

        link = Link()
        controlled_cpu_reset(link, "OCD")
        self.assertEqual(link.actions, ["reset", ("key", "OCD")])

    def test_T41_resume_helper_only_runs_a_confirmed_stopped_cpu(self) -> None:
        class Link:
            def __init__(self, statuses: Any) -> None:
                self.statuses = list(statuses)
                self.controls: list[tuple[int, int]] = []

            def ldcs(self, address: Any) -> Any:
                return self.statuses.pop(0)

            def stcs(self, address: Any, value: Any) -> None:
                self.controls.append((address, value))

        stopped = Link([1, 0])
        result = resume_cpu_if_stopped(stopped, 0x04, 0x05, 0x02, 0x01)
        self.assertEqual(result, {"before_status": 1, "run_requested": True, "after_status": 0})
        self.assertEqual(stopped.controls, [(0x04, 0x02)])
        running = Link([0])
        self.assertEqual(
            resume_cpu_if_stopped(running, 0x04, 0x05, 0x02, 0x01),
            {"before_status": 0, "run_requested": False, "after_status": 0},
        )
        self.assertEqual(running.controls, [])

    def test_T42_deadline_covers_twenty_measured_status_blocks(self) -> None:
        self.assertEqual(MAILBOX_PROBE_TIMEOUT_S, 10)
        self.assertEqual(STATUS_STABILITY_TIMEOUT_S, 180)


if __name__ == "__main__":
    unittest.main()
