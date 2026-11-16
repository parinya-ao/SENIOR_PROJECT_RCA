"""Log structure checks only: these fixtures never establish physical provenance."""

import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from tests.test_live_rf_proof import fixture
from tools import rf_proof as rf


def symmetric_fixture(test_id: Any) -> Any:
    manifest, old, images = fixture()
    reverse = test_id in ("T03", "T04")
    nack = test_id in ("T02", "T04")
    sender, receiver = ("RECEIVER", "GATEWAY") if reverse else ("GATEWAY", "RECEIVER")
    journal = []

    def add(role: Any, text: Any) -> None:
        journal.append({"role": role, "line": text if role == "HOST" else f"[{role}] {text}"})

    for role in (receiver, sender):
        for item in old:
            if (
                item["role"] == role
                and " C=" not in item["line"]
                and not any(x in item["line"] for x in ("RX_READY", "WAIT_START", "WAIT_SESSION"))
            ):
                journal.append(item)
        add(role, "TRANSPORT=SSOT_SYMMETRIC_V1")
        add(role, "WAIT_START" if role == "GATEWAY" else "WAIT_SESSION")
        if role == receiver:
            add("HOST", ("N" if nack else "R") + "1234")
            add(role, "SESSION_READY C=1234")
            add(role, "RX_READY")
    add("HOST", "S1234")
    src, dst = (1, 0) if reverse else (0, 1)

    def event(role: Any, name: Any, type_: Any, irq: Any, response: Any=False) -> None:
        source, destination = (dst, src) if response else (src, dst)
        add(
            role,
            f"{name} T={len(journal)} SID=1234 SRC={source} DST={destination} "
            f"TYPE={type_:02X} Q=1 E=0 IRQ={irq:02X}",
        )

    event(sender, "DATA_TX_BEGIN", 8, 0)
    payload = "C=1234 S=01 LEN=11 HEX=68656C6C6F20776F726C64 ASCII=hello world"
    add(sender, "DATA_PAYLOAD " + payload)
    event(sender, "DATA_TX_DONE", 8, 8)
    event(receiver, "DATA_RX", 8, 0x40)
    if not nack:
        event(receiver, "DATA_VALIDATED", 8, 0x40)
        add(receiver, "PAYLOAD_BYTES " + payload)
    response = "NACK" if nack else "ACK"
    type_ = 9 if nack else 3
    event(receiver, response + "_TX_BEGIN", type_, 0x40, True)
    event(receiver, response + "_TX_DONE", type_, 8, True)
    event(sender, response + "_RX", type_, 0x40, True)
    event(sender, response + "_ACCEPTED", type_, 0x40, True)
    event(sender, "TRANSACTION_FAILED" if nack else "TRANSACTION_COMPLETE", type_, 0x40, True)
    return manifest, journal, images


class SymmetricProofTests(unittest.TestCase):
    def test_runner_selects_receiver_first_and_parks_both(self) -> None:
        for test_id in ("T01", "T02", "T03", "T04"):
            _manifest, records, images = symmetric_fixture(test_id)
            reverse = test_id in ("T03", "T04")
            receiving = "gateway" if reverse else "receiver"
            sending = "receiver" if reverse else "gateway"
            writes: list[Any] = []

            class Process:
                def __init__(self, role: Any, output: Any) -> None:
                    self.role, self.output, self.stdin = role, output, self

                def poll(self) -> None:
                    return None

                def flush(self) -> None:
                    pass

                def write(
                    self: Any,
                    data: Any,
                    *,
                    writes: list[Any] = writes,
                    receiving: str = receiving,
                    records: Any = records,
                ) -> Any:
                    writes.append((self.role, data))
                    board = "GATEWAY" if self.role == "gateway" else "RECEIVER"
                    if data == b"P":
                        self.output.put((self.role, "stdout", f"[{board}] PARKED E=0\n".encode()))
                    elif self.role == receiving:
                        for line in (f"[{board}] SESSION_READY C=1234", f"[{board}] RX_READY"):
                            self.output.put((self.role, "stdout", (line + "\n").encode()))
                    else:
                        for item in records:
                            if " SID=" in item["line"] or " LEN=" in item["line"]:
                                role = "gateway" if item["role"] == "GATEWAY" else "receiver"
                                self.output.put((role, "stdout", (item["line"] + "\n").encode()))
                    return len(data)

            def start(
                proof: Any,
                role: Any,
                port: Any,
                output: Any,
                *,
                records: Any = records,
            ) -> Any:
                board = "GATEWAY" if role == "gateway" else "RECEIVER"
                for item in records:
                    if item["role"] == board and not any(
                        x in item["line"] for x in (" C=", " SID=", "RX_READY")
                    ):
                        output.put((role, "stdout", (item["line"] + "\n").encode()))
                return {"process": Process(role, output), "threads": []}

            with tempfile.TemporaryDirectory() as directory:
                proof: Any = SimpleNamespace(
                    run_dir=Path(directory),
                    note=lambda name, text: (Path(directory) / name).write_text(text),
                )
                args: Any = SimpleNamespace(
                    physical_mapping_verified=True,
                    power_verified=True,
                    boot_layout_verified=True,
                    authorize_rf_test=True,
                    transport_test=test_id,
                )
                with (
                    patch.object(rf, "application_layout_verified", return_value=True),
                    patch.object(rf, "upload_ports_match", return_value=True),
                    patch.object(rf, "check_port_owners", return_value=[]),
                    patch.object(rf, "physical_readiness_errors", return_value=[]),
                    patch.object(rf, "upload_evidence_matches", return_value=True),
                    patch.object(rf, "verify_installed_images", return_value=images),
                    patch("secrets.randbelow", return_value=0x1233),
                    patch("secrets.token_hex", return_value="unit-run"),
                    patch.object(rf, "start_rf_monitor", side_effect=start),
                    patch.object(rf, "stop_rf_monitor", return_value=0),
                    patch.object(rf, "RF_COMPLETION_LOG_SETTLE_SECONDS", 0),
                    patch.object(rf, "RF_SINGLE_PACKET_TIMEOUT_SECONDS", 0.2),
                ):
                    code = rf.rf_test(proof, args, True, "config")
                    self.assertEqual(
                        code, 0, test_id + (Path(directory) / "rf-measurements.json").read_text()
                    )
            command = b"N1234" if test_id in ("T02", "T04") else b"R1234"
            self.assertEqual(
                writes,
                [(receiving, command), (sending, b"S1234"), (receiving, b"P"), (sending, b"P")],
            )

    def check(self, test_id: Any, journal: Any=None) -> Any:
        manifest, records, images = symmetric_fixture(test_id)
        return rf.validate_live_proof(
            records if journal is None else journal,
            manifest,
            images,
            "unit-run",
            0x1234,
            diagnostic_test=test_id,
        )

    def test_both_directions_ack_and_nack(self) -> None:
        for test_id in ("T01", "T02", "T03", "T04"):
            with self.subTest(test_id=test_id):
                self.assertTrue(self.check(test_id)["valid"])

    def test_each_physical_boundary_required(self) -> None:
        _, journal, _ = symmetric_fixture("T01")
        for name in (
            "DATA_TX_BEGIN",
            "DATA_TX_DONE",
            "DATA_RX",
            "DATA_VALIDATED",
            "ACK_TX_BEGIN",
            "ACK_TX_DONE",
            "ACK_RX",
            "ACK_ACCEPTED",
            "TRANSACTION_COMPLETE",
            "PAYLOAD_BYTES",
        ):
            with self.subTest(name=name):
                reduced = [i for i in journal if f"] {name} " not in i["line"]]
                self.assertFalse(self.check("T01", reduced)["valid"])

    def test_wrong_identity_sequence_and_crc_are_not_accepted(self) -> None:
        _, journal, _ = symmetric_fixture("T01")
        for before, after in (
            ("SID=1234", "SID=1235"),
            ("SRC=1", "SRC=8"),
            ("DST=0", "DST=9"),
            ("TYPE=03", "TYPE=01"),
            ("Q=1", "Q=2"),
            ("IRQ=40", "IRQ=60"),
        ):
            records = copy.deepcopy(journal)
            for item in records:
                if "] ACK_RX " in item["line"]:
                    item["line"] = item["line"].replace(before, after)
            with self.subTest(after=after):
                self.assertFalse(self.check("T01", records)["valid"])


if __name__ == "__main__":
    unittest.main()
