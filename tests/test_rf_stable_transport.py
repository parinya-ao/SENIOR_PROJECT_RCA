"""Host contracts for the stable LoRa ACK/NACK hardware proof path."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from tools import rf_proof

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_ID = 0x1234
PAYLOAD_LINE = (
    f"PAYLOAD_BYTES C={CAMPAIGN_ID:04X} S=01 LEN=11 "
    "HEX=68656C6C6F20776F726C64 ASCII=hello world"
)


def event(name: str, timestamp: int, packet_type: int, sequence: int = 1,
          error: int = 0) -> str:
    return (
        f"{name} SID={CAMPAIGN_ID:04X} T={timestamp} TYPE={packet_type} "
        f"Q={sequence} E={error}"
    )


def image_evidence(run_id: str = "run-1") -> dict[str, dict[str, Any]]:
    manifest = json.loads((ROOT / "generated/lora_manifest.json").read_text())
    return {
        role: {
            "origin": "PHYSICAL_UPDI",
            "run_id": run_id,
            "verified": True,
            "signature": "1e970a",
            "port": rf_proof.PORTS[role.lower()],
            "firmware_sha256": role.lower() + "-sha256",
            "build_id": manifest["environments"][environment]["build_id"],
        }
        for role, environment in (("GATEWAY", "sender_hello"), ("RECEIVER", "receiver"))
    }


def journal(nack: bool = False) -> list[dict[str, Any]]:
    manifest = json.loads((ROOT / "generated/lora_manifest.json").read_text())
    rows = []
    for role, environment in (("GATEWAY", "sender_hello"), ("RECEIVER", "receiver")):
        rows.extend(
            [
                (role, f"BUILD_ID={manifest['environments'][environment]['build_id']}"),
                (role, f"CONFIG_FINGERPRINT={manifest['shared_fingerprint']}"),
                (role, f"PROTOCOL_VERSION={manifest['shared']['protocol']['version']}"),
                (role, "RADIO_INIT_OK"),
                (role, "RADIO_SPI_VERSION=0x12"),
                (role, "RADIO_PROFILE F100=91500 P=2"),
                (role, "RADIO_MOD SF=7 BW=125 CR=5"),
                (role, "RADIO_FRAME SW=12 PRE=8 CRC=1 HDR=E IQ=0"),
            ]
        )
    rows.extend(
        [
        ("HOST_RECEIVER", "?"),
        ("RECEIVER", "RADIO_READY"),
        ]
    )
    if nack:
        rows.append(("HOST_RECEIVER", "N"))
    rows.extend(
        [
            ("HOST_RECEIVER", "R"),
            ("RECEIVER", "RX_READY"),
            ("HOST_GATEWAY", "R"),
            ("HOST_GATEWAY", "?"),
            ("GATEWAY", "RADIO_READY"),
            ("HOST_GATEWAY", "S"),
        ]
    )
    attempts = 2 if nack else 1
    for attempt in range(attempts):
        rows.extend(
            [
                ("GATEWAY", event("DATA_TX_BEGIN", attempt * 10 + 1, 8)),
            ]
        )
        if attempt == 0:
            rows.append(("GATEWAY", event("DATA_TX_REQUESTED", 1, 8)))
        rows.append(("GATEWAY", event("DATA_TX_DONE", attempt * 10 + 2, 8)))
        if nack and attempt == 0:
            rows.extend(
                [
                    ("RECEIVER", event("NACK_TX_BEGIN", attempt * 10 + 3, 9)),
                    ("RECEIVER", event("NACK_TX_DONE", attempt * 10 + 4, 9)),
                ]
            )
            if attempt < attempts - 1:
                rows.append(("GATEWAY", event("NACK_RX", attempt * 10 + 5, 9)))
        else:
            rows.extend(
                [
                    ("RECEIVER", event("DATA_VALIDATED", attempt * 10 + 3, 8)),
                    ("RECEIVER", PAYLOAD_LINE),
                    ("RECEIVER", event("ACK_TX_BEGIN", attempt * 10 + 4, 3)),
                    ("RECEIVER", event("ACK_TX_DONE", attempt * 10 + 5, 3)),
                    ("GATEWAY", event("ACK_ACCEPTED", attempt * 10 + 6, 3)),
                ]
            )
    rows.extend(
        [
            ("HOST_RECEIVER", "P"),
            ("RECEIVER", "PARKED E=0"),
            ("HOST_GATEWAY", "P"),
            ("GATEWAY", "PARKED E=0"),
        ]
    )
    return [
        {
            "role": role,
            "line": line if role.startswith("HOST_") else f"[{role}] {line}",
            "observed_monotonic_ns": i,
        }
        for i, (role, line) in enumerate(rows)
    ]


def wrong_destination_journal() -> list[dict[str, Any]]:
    manifest = json.loads((ROOT / "generated/lora_manifest.json").read_text())
    rows = [
        ("HOST_RECEIVER", "?"),
        ("RECEIVER", "RADIO_READY"),
        ("HOST_RECEIVER", "R"),
        ("RECEIVER", "RX_READY"),
        ("HOST_GATEWAY", "R"),
        ("GATEWAY", "RX_READY"),
        ("HOST_GATEWAY", "?"),
        ("GATEWAY", "RADIO_READY"),
        ("GATEWAY", "RADIO_INIT_OK"),
        ("RECEIVER", "RADIO_INIT_OK"),
        ("GATEWAY", "RADIO_SPI_VERSION=0x12"),
        ("RECEIVER", "RADIO_SPI_VERSION=0x12"),
        ("GATEWAY", "RADIO_PROFILE F100=91500 P=2"),
        ("RECEIVER", "RADIO_PROFILE F100=91500 P=2"),
        ("GATEWAY", "RADIO_MOD SF=7 BW=125 CR=5"),
        ("RECEIVER", "RADIO_MOD SF=7 BW=125 CR=5"),
        ("GATEWAY", "RADIO_FRAME SW=12 PRE=8 CRC=1 HDR=E IQ=0"),
        ("RECEIVER", "RADIO_FRAME SW=12 PRE=8 CRC=1 HDR=E IQ=0"),
        ("GATEWAY", f"BUILD_ID={manifest['environments']['sender_hello']['build_id']}"),
        ("RECEIVER", f"BUILD_ID={manifest['environments']['receiver']['build_id']}"),
        ("GATEWAY", f"CONFIG_FINGERPRINT={manifest['shared_fingerprint']}"),
        ("RECEIVER", f"CONFIG_FINGERPRINT={manifest['shared_fingerprint']}"),
        ("GATEWAY", f"PROTOCOL_VERSION={manifest['shared']['protocol']['version']}"),
        ("RECEIVER", f"PROTOCOL_VERSION={manifest['shared']['protocol']['version']}"),
    ]
    for trial in range(10):
        rows.extend(
            [
                ("HOST_GATEWAY", "W"),
                ("GATEWAY", "WRONG_DEST_TX_BEGIN DST=2 TYPE=08 Q=1 APP=11"),
                ("GATEWAY", "WRONG_DEST_TX_DONE"),
                (
                    "RECEIVER",
                    event("RX_DISCARD_DEST", trial + 10, 0, sequence=0)
                    .replace("SID=1234", "SID=0000"),
                ),
            ]
        )
    rows.extend(
        [
            ("HOST_RECEIVER", "P"),
            ("RECEIVER", "PARKED E=0"),
            ("HOST_GATEWAY", "P"),
            ("GATEWAY", "PARKED E=0"),
        ]
    )
    return [
        {
            "role": role,
            "line": line if role.startswith("HOST_") else f"[{role}] {line}",
            "observed_monotonic_ns": index,
        }
        for index, (role, line) in enumerate(rows)
    ]


class StableTransportProofTests(unittest.TestCase):
    def test_one_packet_requires_payload_ack_on_both_boards(self) -> None:
        result = rf_proof.validate_stable_transport(journal(), image_evidence(), "run-1", "T01")
        self.assertTrue(result["valid"], result["issues"])
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(result["ack_tx"], 1)

    def test_structured_request_must_match_transaction_and_order(self) -> None:
        request = event("DATA_TX_REQUESTED", 1, 8)
        for invalid in (
            request.replace("TYPE=8", "TYPE=3"),
            request.replace("Q=1", "Q=2"),
            request.replace(f"SID={CAMPAIGN_ID:04X}", "SID=0000"),
            request.replace("E=0", "E=-1"),
            "DATA_TX_REQUESTED",
        ):
            with self.subTest(invalid=invalid):
                rows = journal()
                match = next(row for row in rows if request in row["line"])
                match["line"] = f"[GATEWAY] {invalid}"
                result = rf_proof.validate_stable_transport(rows, image_evidence(), "run-1", "T01")
                self.assertFalse(result["valid"])

        for position in ("before start", "after TX completion", "duplicate"):
            with self.subTest(position=position):
                rows = journal()
                i = next(i for i, row in enumerate(rows) if request in row["line"])
                if position == "duplicate":
                    rows.insert(i, rows[i].copy())
                else:
                    row = rows.pop(i)
                    rows.insert(i - 2 if position == "before start" else i + 1, row)
                result = rf_proof.validate_stable_transport(rows, image_evidence(), "run-1", "T01")
                self.assertFalse(result["valid"])

    def test_controlled_nack_requires_retry_then_ack(self) -> None:
        result = rf_proof.validate_stable_transport(
            journal(nack=True), image_evidence(), "run-1", "T02"
        )
        self.assertTrue(result["valid"], result["issues"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["nack_tx"], 1)
        self.assertEqual(result["retries"], 1)

    def test_parked_receiver_is_rearmed_before_start(self) -> None:
        rows = journal()
        ready_row = next(row for row in rows if row["line"] == "[RECEIVER] RADIO_READY")
        ready_row["line"] = "[RECEIVER] RADIO_NOT_READY"
        result = rf_proof.validate_stable_transport(rows, image_evidence(), "run-1", "T01")
        self.assertTrue(result["valid"], result["issues"])

    def test_receiver_not_ready_without_successful_rearm_fails(self) -> None:
        rows = journal()
        ready_row = next(row for row in rows if row["line"] == "[RECEIVER] RADIO_READY")
        ready_row["line"] = "[RECEIVER] RADIO_NOT_READY"
        rx_ready_row = next(row for row in rows if row["line"] == "[RECEIVER] RX_READY")
        rows.remove(rx_ready_row)
        result = rf_proof.validate_stable_transport(rows, image_evidence(), "run-1", "T01")
        self.assertFalse(result["valid"], "a radio that never re-enters RX must fail")

    def test_wrong_sequence_cannot_complete_the_exchange(self) -> None:
        rows = journal()
        for row in rows:
            if "ACK_ACCEPTED " in row["line"]:
                row["line"] = row["line"].replace("Q=1", "Q=2")
        result = rf_proof.validate_stable_transport(rows, image_evidence(), "run-1", "T01")
        self.assertFalse(result["valid"])
        rows = journal()
        at = next(i for i, row in enumerate(rows) if "DATA_VALIDATED" in row["line"])
        rows.insert(at, {"role": "RECEIVER", "line": "[RECEIVER] BOOT receiver after-reset"})
        result = rf_proof.validate_stable_transport(rows, image_evidence(), "run-1", "T01")
        self.assertFalse(result["valid"], "a reset during DATA/ACK cannot pass")

    def test_session_id_must_match_across_both_radio_directions(self) -> None:
        rows = journal()
        for row in rows:
            if "[RECEIVER] ACK_TX_BEGIN " in row["line"]:
                row["line"] = row["line"].replace("SID=1234", "SID=5678")
        result = rf_proof.validate_stable_transport(rows, image_evidence(), "run-1", "T01")
        self.assertFalse(result["valid"])

    def test_wrong_destination_trials_require_ten_discards_and_no_response(self) -> None:
        result = rf_proof.validate_wrong_destination_trials(
            wrong_destination_journal(), image_evidence(), "run-1"
        )
        self.assertTrue(result["valid"], result["issues"])
        self.assertEqual(result["transmitted"], 10)
        self.assertEqual(result["destination_discards"], 10)
        self.assertEqual(result["deliveries"], 0)
        self.assertEqual(result["responses"], 0)

        rows = wrong_destination_journal()
        at = next(i for i, row in enumerate(rows) if "RX_DISCARD_DEST" in row["line"])
        rows.insert(
            at + 1,
            {
                "role": "RECEIVER",
                "line": f"[RECEIVER] {event('ACK_TX_BEGIN', 11, 3)}",
                "observed_monotonic_ns": at + 1,
            },
        )
        failed = rf_proof.validate_wrong_destination_trials(rows, image_evidence(), "run-1")
        self.assertFalse(failed["valid"])

    def test_packet_log_overflow_invalidates_physical_evidence(self) -> None:
        rows = journal()
        rows.insert(-4, {"role": "GATEWAY", "line": "LOG_OVERFLOW N=1"})
        result = rf_proof.validate_stable_transport(rows, image_evidence(), "run-1", "T01")
        self.assertFalse(result["valid"])

    def test_lost_ack_requires_one_drop_one_timeout_and_duplicate_suppression(self) -> None:
        rows = journal()
        at = next(i for i, row in enumerate(rows) if row["role"] == "HOST_GATEWAY")
        rows.insert(at, {"role": "HOST_RECEIVER", "line": "D", "observed_monotonic_ns": 0})
        at = next(i for i, row in enumerate(rows) if "ACK_TX_BEGIN" in row["line"])
        extra = [
            ("RECEIVER", event("RESPONSE_DROPPED", 4, 3)),
            ("GATEWAY", event("RETRY_SCHEDULED", 3002, 8)),
            ("GATEWAY", event("DATA_TX_BEGIN", 3003, 8)),
            ("GATEWAY", event("DATA_TX_DONE", 3004, 8)),
            ("RECEIVER", event("DATA_DUP", 3005, 8)),
        ]
        rows[at:at] = [{"role": role, "line": f"[{role}] {line}"} for role, line in extra]
        for row in rows:
            if "ACK_TX_BEGIN" in row["line"]: row["line"] = row["line"].replace("T=4", "T=3006")
            if "ACK_TX_DONE" in row["line"]: row["line"] = row["line"].replace("T=5", "T=3007")
            if "ACK_ACCEPTED" in row["line"]: row["line"] = row["line"].replace("T=6", "T=3008")
        result = rf_proof.validate_stable_transport(rows, image_evidence(), "run-1", "T01")
        self.assertTrue(result["valid"], result["issues"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["timeouts"], 1)

    def test_campaign_stops_before_nack_or_stress_after_failed_t01(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = SimpleNamespace(run_dir=Path(directory))
            with patch.object(rf_proof, "run_stable_ack_rf_test", return_value=1) as execute:
                result = rf_proof.run_stable_campaign(proof, SimpleNamespace(), "run-1", image_evidence())
            self.assertEqual(result, 1)
            self.assertEqual(execute.call_count, 1)
            summary = json.loads((proof.run_dir / "campaign.json").read_text())
            self.assertEqual(summary["cases"][0]["name"], "T01")
            self.assertFalse(summary["passed"])

    def test_campaign_counts_failed_attempts_without_claiming_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = SimpleNamespace(run_dir=Path(directory))
            calls = []
            def execute(child: Any, options: Any, _run: str, _images: Any) -> int:
                calls.append(options.transport_test)
                index = len(calls)
                result = {"attempts": index, "ack_tx": int(index < 3), "nack_tx": int(index == 2),
                          "retries": index - 1, "timeouts": int(index == 3),
                          "rtt_ms": index * 100 if index < 3 else None}
                (child.run_dir / "rf-test.json").write_text(json.dumps(result))
                return int(index == 3)
            with patch.object(rf_proof, "run_stable_ack_rf_test", side_effect=execute):
                self.assertEqual(rf_proof.run_stable_campaign(proof, SimpleNamespace(), "run-1", image_evidence()), 1)
            summary = json.loads((proof.run_dir / "campaign.json").read_text())
            self.assertEqual(summary["executed"], 3)
            self.assertEqual(summary["successful"], 2)
            self.assertEqual(summary["data_tx"], 6)
            self.assertEqual(summary["ack_tx"], 2)
            self.assertEqual(summary["average_rtt_ms"], 150)
            self.assertEqual(summary["p99_rtt_ms"], 200)

    def test_runner_uses_receiver_ready_then_one_gateway_start(self) -> None:
        class Proof:
            def __init__(self, directory: Path) -> None:
                self.run_dir = directory

            def note(self, name: str, content: str) -> None:
                (self.run_dir / name).write_text(content)

        class MonitorInput:
            def __init__(self, key: str, output: Any, nack: bool) -> None:
                self.key, self.output, self.nack = key, output, nack
                self.closed = False

            def _line(self, line: str) -> None:
                self.output.put((self.key, "stdout", (line + "\n").encode()))

            def write(self, data: bytes) -> int:
                command = data.decode("ascii")
                role = "GATEWAY" if self.key == "gateway" else "RECEIVER"
                if command == "?":
                    self._line(f"[{role}] RADIO_READY")
                elif command == "R":
                    self._line("[RECEIVER] RX_READY")
                elif command == "S":
                    rows = journal(self.nack)
                    for item in rows:
                        if item["role"] in ("GATEWAY", "RECEIVER"):
                            self.output.put(
                                (item["role"].lower(), "stdout", (item["line"] + "\n").encode())
                            )
                elif command == "P":
                    self._line(f"[{role}] PARKED E=0")
                return len(data)

            def flush(self) -> None:
                pass

        class Process:
            def __init__(self, key: str, output: Any, nack: bool) -> None:
                self.stdin = MonitorInput(key, output, nack)

            def poll(self) -> None:
                return None

        for test_id in ("T01", "T02"):
            with self.subTest(test=test_id), tempfile.TemporaryDirectory() as directory:
                proof = Proof(Path(directory))
                processes: dict[str, Process] = {}

                def start(_proof: Any, key: str, _port: str, output: Any) -> dict[str, Any]:
                    process = Process(key, output, test_id == "T02")
                    processes[key] = process
                    return {"process": process, "threads": []}

                with (
                    patch.object(rf_proof, "start_rf_monitor", side_effect=start),
                    patch.object(rf_proof, "stop_rf_monitor", return_value=0),
                    patch.object(rf_proof, "check_port_owners", return_value=[]),
                    patch.object(rf_proof, "RF_COMPLETION_LOG_SETTLE_SECONDS", 0),
                ):
                    status = rf_proof.run_stable_ack_rf_test(
                        proof,
                        SimpleNamespace(transport_test=test_id),
                        "run-1",
                        image_evidence(),
                    )
                result = json.loads((proof.run_dir / "rf-test.json").read_text())
                self.assertEqual(status, 0, result["issues"])
                commands = [
                    (row["role"], row["line"])
                    for row in json.loads((proof.run_dir / "rf-test-events.json").read_text())
                    if row["role"].startswith("HOST_")
                ]
                expected = [
                    ("HOST_RECEIVER", "?"),
                    ("HOST_RECEIVER", "R"),
                    ("HOST_GATEWAY", "R"),
                    ("HOST_GATEWAY", "?"),
                    ("HOST_GATEWAY", "S"),
                    ("HOST_RECEIVER", "P"),
                    ("HOST_GATEWAY", "P"),
                ]
                if test_id == "T02":
                    expected.insert(1, ("HOST_RECEIVER", "N"))
                self.assertEqual(commands, expected)


if __name__ == "__main__":
    unittest.main()
