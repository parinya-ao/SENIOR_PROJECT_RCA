"""Contracts for the interactive console; fake only the physical interface."""

import io
import json
import tempfile
import time
import tomllib
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.test_rf_stable_transport import image_evidence, journal
from tools import debug_protocol_ack_nack as debug
from tools import production_bench as bench
from tools import rf_proof


class DebugConsoleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.log = debug.Session(Path(self.temp.name) / "run")
        self.addCleanup(self.log.finish)

    def console(
        self, commands: list[str], hardware: Mock | None = None
    ) -> tuple[debug.Console, Mock, str]:
        hardware = hardware or Mock()
        hardware.step.return_value = {"status": "PASS", "detail": "observed"}
        output = io.StringIO()
        console = debug.Console(hardware, self.log, read=iter(commands).__next__, out=output)
        console.run()
        return console, hardware, output.getvalue()

    def test_mise_registers_exact_task_without_flash(self) -> None:
        config = tomllib.loads((debug.ROOT / "mise.toml").read_text())
        task = config["tasks"]["debug_protocol_ACK_NACK"]
        self.assertIn("-m tools.debug_protocol_ack_nack", task["run"])
        self.assertNotIn("upload", task["run"])

    def test_matching_live_readback_does_not_require_a_receipt(self) -> None:
        hardware = debug.Hardware(self.log)
        images = {role: {"verified": True} for role in ("GATEWAY", "RECEIVER")}
        with (
            patch.object(hardware, "_read_images", return_value=images) as read,
            patch.object(hardware, "_prepare_images") as prepare,
        ):
            self.assertEqual(hardware._verify_or_prepare(), images)
        read.assert_called_once()
        prepare.assert_not_called()

    def test_mismatched_images_enter_preparation_once(self) -> None:
        hardware = debug.Hardware(self.log)
        images = {role: {"verified": False} for role in ("GATEWAY", "RECEIVER")}
        verified = {role: {"verified": True} for role in images}
        with (
            patch.object(hardware, "_read_images", side_effect=[images, verified]),
            patch.object(hardware, "_prepare_images") as prepare,
        ):
            self.assertEqual(hardware._verify_or_prepare(), verified)
        prepare.assert_called_once_with(images)

    def test_bootsize_zero_excludes_every_write_even_with_exact_approval(self) -> None:
        mismatch = {
            "GATEWAY": {
                "serial_number": "serial",
                "firmware_sha256": "hash",
                "start": 0,
                "end": 512,
            }
        }
        approval = self.log.path / "approval.json"
        approval.write_text(json.dumps(mismatch))
        with self.assertRaisesRegex(bench.BenchBlockedError, "BOOTSIZE=0x00"):
            bench.approve_writes(mismatch, {"GATEWAY": {"bootsize": 0, "codesize": 0}}, approval)
        self.assertTrue(bench.write_span_is_application(512, 1024, 1, 2))
        self.assertFalse(bench.write_span_is_application(512, 1536, 1, 2))

    def test_interrupted_preparation_never_opens_monitors_or_publishes_receipt(self) -> None:
        hardware = debug.Hardware(self.log)
        with (
            patch.object(bench, "build", return_value=("", {})),
            patch.object(bench, "read_layouts", return_value={}),
            patch.object(hardware, "_read_images", return_value={"GATEWAY": {"verified": False}}),
            patch.object(hardware, "_prepare_images", side_effect=KeyboardInterrupt),
            patch.object(bench, "publish_receipt") as publish,
            patch.object(rf_proof, "start_rf_monitor") as open_monitor,
            self.assertRaises(KeyboardInterrupt),
        ):
            hardware._connect_verified()
        publish.assert_not_called()
        open_monitor.assert_not_called()

    def test_swapped_port_overrides_never_reach_live_identification(self) -> None:
        hardware = debug.Hardware(self.log)
        hardware.port_overrides = {"gateway": rf_proof.PORTS["receiver"]}
        with (
            patch.object(debug, "discover_ports", return_value=list(rf_proof.PORTS.values())),
            patch.object(hardware, "_connect_verified") as connect,
            self.assertRaisesRegex(bench.BenchBlockedError, "enrolled USB adapter"),
        ):
            hardware.connect()
        connect.assert_not_called()

    def test_dry_run_builds_without_opening_serial(self) -> None:
        with (
            patch.object(debug, "ROOT", Path(self.temp.name)),
            patch.object(bench, "build") as build,
            patch.object(debug, "Hardware") as hardware,
        ):
            self.assertEqual(debug.main(["--dry-run"]), 0)
        build.assert_called_once()
        hardware.assert_not_called()

    def test_enter_executes_one_checkpoint_and_quit_cleans_up(self) -> None:
        console, hardware, output = self.console(["", "q"])
        self.assertEqual(hardware.step.call_args_list[0].args, (0,))
        self.assertEqual(hardware.step.call_count, 1)
        hardware.close.assert_called_once()
        self.assertEqual(console.index, 0)
        self.assertIn("STEP 1/8", output)

    def test_back_does_not_repeat_transmission_and_retry_is_explicit(self) -> None:
        _, hardware, _ = self.console(["", "", "b", "l", "h", "r", "q"])
        self.assertEqual([x.args[0] for x in hardware.step.call_args_list], [0, 1, 0])

    def test_failed_step_never_advances(self) -> None:
        hardware = Mock()
        hardware.step.side_effect = [
            {"status": "FAIL", "detail": "no Gateway"},
            {"status": "PASS", "detail": "connected"},
        ]
        _, hardware, output = self.console(["", "", "q"], hardware)
        self.assertEqual([x.args[0] for x in hardware.step.call_args_list], [0, 0])
        self.assertIn("no Gateway", output)

    def test_missing_device_timeout_and_interrupt_have_clear_status(self) -> None:
        for error, status in [
            (OSError("missing device"), "BLOCKED"),
            (TimeoutError("RX_READY absent"), "TIMEOUT"),
        ]:
            with self.subTest(status=status):
                hardware = Mock()
                hardware.step.side_effect = error
                _, hardware, output = self.console(["", "q"], hardware)
                self.assertIn(status, output)
                hardware.close.assert_called_once()
        hardware = Mock()
        hardware.step.side_effect = KeyboardInterrupt
        self.console([""], hardware)
        hardware.close.assert_called_once()

    def test_cannot_skip_mandatory_checkpoint(self) -> None:
        _, hardware, output = self.console(["s", "q"])
        hardware.step.assert_not_called()
        self.assertIn("required", output)

    def test_retrying_earlier_step_invalidates_later_evidence(self) -> None:
        console, _, _ = self.console(["", "", "b", "r", "q"])
        self.assertNotIn("2", console.log.results)

    def test_trial_group_stops_on_first_failed_transaction(self) -> None:
        hardware = debug.Hardware(self.log)
        hardware.monitors = {"gateway": {}, "receiver": {}}
        with patch.object(
            hardware, "exchange", return_value={"status": "FAIL", "detail": "no ACK"}
        ) as exchange:
            self.assertEqual(hardware.step(5)["status"], "FAIL")
        exchange.assert_called_once()

    def test_intentional_exhaustion_must_have_exact_bounded_attempt_count(self) -> None:
        rows = []
        for i in range(4):
            rows += [
                {"role": "GATEWAY", "line": f"[GATEWAY] DATA_TX_BEGIN T={i * 4000} TYPE=8 Q=1 E=0"},
                {
                    "role": "GATEWAY",
                    "line": f"[GATEWAY] DATA_TX_DONE T={i * 4000 + 50} TYPE=8 Q=1 E=0",
                },
            ]
            if i < 3:
                rows.append(
                    {
                        "role": "GATEWAY",
                        "line": f"[GATEWAY] RETRY_SCHEDULED T={i * 4000 + 3050} TYPE=8 Q=1 E=0",
                    }
                )
        rows.append(
            {"role": "GATEWAY", "line": "[GATEWAY] TRANSACTION_FAILED T=15050 TYPE=8 Q=1 E=-1"}
        )
        rows += [{"role": role, "line": f"[{role}] PARKED E=0"} for role in ("GATEWAY", "RECEIVER")]
        result = debug.assess_exhaustion(rows, 4)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["timeouts"], 4)
        self.assertEqual(debug.assess_exhaustion(rows, 3)["status"], "FAIL")
        unsafe = [dict(row) for row in rows]
        unsafe[0]["line"] = unsafe[0]["line"].replace("E=0", "E=-7")
        self.assertEqual(debug.assess_exhaustion(unsafe, 4)["status"], "FAIL")
        rows.append({"role": "GATEWAY", "line": "[GATEWAY] ACK_ACCEPTED T=15051 TYPE=3 Q=1 E=0"})
        self.assertEqual(debug.assess_exhaustion(rows, 4)["status"], "FAIL")

    def test_malformed_payload_line_is_logged_without_crashing_capture(self) -> None:
        self.log.record("RECEIVER", "[RECEIVER] HEX=00 ASCII=bad")
        self.assertIsNone(self.log.snapshot()[-1]["sequence"])

    def test_rf_authorization_gate_does_not_send_commands(self) -> None:
        hardware = debug.Hardware(self.log, out=io.StringIO())
        hardware.monitors = {"gateway": {}, "receiver": {}}
        with patch.object(hardware, "command") as command:
            with self.assertRaisesRegex(bench.BenchBlockedError, "authorize-rf-test"):
                hardware.exchange()
        command.assert_not_called()

    def test_standby_timeout_does_not_mask_ctrl_c(self) -> None:
        hardware = debug.Hardware(self.log)
        hardware.authorize_rf = True
        hardware.monitors = {"gateway": {}, "receiver": {}}
        with (
            patch.object(hardware, "_arm_radio", side_effect=KeyboardInterrupt),
            patch.object(hardware, "_park", side_effect=TimeoutError("standby timed out")),
            patch.object(hardware, "close") as close,
        ):
            console = debug.Console(hardware, self.log, read=lambda: "", out=io.StringIO())
            console.index = 2
            self.log.results = {str(i): {"status": "PASS", "detail": "verified"} for i in (1, 2)}
            self.assertEqual(console.run(), 130)
        close.assert_called_once()
        self.assertTrue(any(row["line"] == "standby timed out" for row in self.log.snapshot()))

    def test_wrong_destination_requires_correlated_discard_and_no_reply_attempt(self) -> None:
        protocol = debug.Hardware(self.log).config["protocol"]
        rows = [
            {"role": "GATEWAY", "line": "[GATEWAY] BENCH_PROBE_BEGIN SID=1234 Q=1 DST=2 APP=11"},
            {"role": "GATEWAY", "line": "[GATEWAY] BENCH_PROBE_DONE E=1"},
            {"role": "RECEIVER", "line": "[RECEIVER] RX_DISCARD_DEST SID=1234 T=1 TYPE=8 Q=1 E=0"},
        ]
        self.assertEqual(debug.assess_probe(rows, protocol, 1, malformed=False)["status"], "PASS")
        self.assertEqual(debug.assess_probe(rows, protocol, 2, malformed=False)["status"], "FAIL")
        rows.append(
            {"role": "RECEIVER", "line": "[RECEIVER] NACK_TX_BEGIN SID=1234 T=2 TYPE=9 Q=1 E=0"}
        )
        self.assertEqual(debug.assess_probe(rows, protocol, 1, malformed=False)["status"], "FAIL")

    def test_logs_have_structured_fields_and_files(self) -> None:
        self.log.record(
            "RECEIVER",
            "[RECEIVER] "
            "PAYLOAD_BYTES C=0000 S=01 LEN=11 "
            "HEX=68656C6C6F20776F726C64 ASCII=hello world",
        )
        self.log.finish()
        event = json.loads((self.log.path / "events.jsonl").read_text().splitlines()[0])
        for key in (
            "timestamp",
            "role",
            "step",
            "event_type",
            "sequence",
            "payload",
            "response",
            "status",
            "error",
        ):
            self.assertIn(key, event)
        self.assertEqual(event["payload"], "hello world")
        for name in ("gateway.log", "receiver.log", "summary.json", "report.md"):
            self.assertTrue((self.log.path / name).exists(), name)

    def test_discovery_prefers_stable_identifiers_and_deduplicates_aliases(self) -> None:
        with patch.object(debug, "Path") as path:
            path.return_value.resolve.side_effect = lambda: Path("/dev/ttyUSB1")
            ports = debug.discover_ports(["/dev/serial/by-id/known"], ["/dev/ttyUSB1"])
        self.assertEqual(ports, ["/dev/serial/by-id/known"])

    def test_role_requires_actual_role_and_matching_build_id(self) -> None:
        text = "[RECEIVER] RADIO_READY\n[RECEIVER] BUILD_ID=abc\n"
        self.assertEqual(debug.firmware_role(text, {"RECEIVER": {"build_id": "abc"}}), "RECEIVER")
        self.assertIsNone(debug.firmware_role(text, {"RECEIVER": {"build_id": "wrong"}}))
        self.assertIsNone(debug.firmware_role("CP2102", image_evidence()))
        self.assertIsNone(
            debug.firmware_role(text.replace("=abc", "=abcdef"), {"RECEIVER": {"build_id": "abc"}})
        )

    def test_data_ack_and_nack_matching_reuses_real_validator(self) -> None:
        for nack in (False, True):
            result = debug.assess(journal(nack), image_evidence(), "run-1", nack=nack)
            self.assertEqual(result["status"], "PASS", result)
            self.assertEqual(result["attempts"], 2 if nack else 1)

    def test_missing_ack_wrong_payload_and_reboot_never_pass(self) -> None:
        for marker in ("ACK_ACCEPTED", "PAYLOAD_BYTES"):
            rows = [x for x in journal() if marker not in x["line"]]
            self.assertEqual(debug.assess(rows, image_evidence(), "run-1")["status"], "FAIL")
        rows = journal()
        rows.append({"role": "RECEIVER", "line": "[RECEIVER] BOOT receiver"})
        result = debug.assess(rows, image_evidence(), "run-1")
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("reset", result["detail"])

    def test_ack_event_with_data_type_cannot_pass(self) -> None:
        rows = journal()
        for row in rows:
            if "ACK_ACCEPTED" in row["line"]:
                row["line"] = row["line"].replace("TYPE=3", "TYPE=8")
        self.assertEqual(debug.assess(rows, image_evidence(), "run-1")["status"], "FAIL")

    def test_reboot_is_detected_while_radio_transaction_is_active(self) -> None:
        hardware = debug.Hardware(self.log)
        hardware.transmitting = True
        hardware.stop = Mock()
        hardware.stop.is_set.side_effect = [False, True]
        hardware.incoming.put(("receiver", "stdout", b"[RECEIVER] BOOT receiver\n"))
        hardware._capture()
        self.assertIn("restarted", str(hardware.fault))

    def test_timeout_wait_is_bounded_and_reports_last_observation(self) -> None:
        hardware = debug.Hardware(self.log)
        with patch.object(time, "monotonic", side_effect=[0, 1]):
            with self.assertRaisesRegex(TimeoutError, "RX_READY"):
                hardware.wait(lambda: False, 0.1, "RX_READY")

    def test_payload_checkpoint_displays_actual_bytes(self) -> None:
        hardware = debug.Hardware(self.log)
        hardware.monitors = {"gateway": {}, "receiver": {}}
        hardware.first_rows = journal()
        hardware.first_exchange = debug.assess(hardware.first_rows, image_evidence(), "run-1")
        result = hardware.step(3)
        self.assertIn("hello world", result["detail"])
        self.assertIn("11/11", result["detail"])
        hardware.first_rows = []
        hardware.first_exchange = {"status": "FAIL", "detail": "missing payload"}
        result = hardware.step(3)
        self.assertNotIn("11/11", result["detail"])
        self.assertIn("missing", result["detail"])

    def test_summary_explicitly_records_unexecuted_steps(self) -> None:
        self.log.finish()
        summary = json.loads((self.log.path / "summary.json").read_text())
        self.assertEqual(summary["steps"]["8"]["status"], "NOT RUN")

    def test_hardware_cleanup_parks_both_even_after_first_command_error(self) -> None:
        hardware = debug.Hardware(self.log)
        hardware.monitors = {"gateway": {"process": Mock()}, "receiver": {"process": Mock()}}
        with (
            patch.object(hardware, "command", side_effect=[OSError("lost"), None]) as send,
            patch.object(rf_proof, "stop_rf_monitor") as stop,
        ):
            hardware.close()
        self.assertEqual(send.call_count, 2)
        self.assertEqual(stop.call_count, 2)

    def test_missing_ports_raises_instead_of_using_historical_role_mapping(self) -> None:
        hardware = debug.Hardware(self.log)
        with patch.object(debug, "discover_ports", return_value=[]):
            with self.assertRaisesRegex(OSError, "two"):
                hardware.connect()

    def test_real_exchange_keeps_timing_sensitive_commands_in_one_checkpoint(self) -> None:
        for nack in (False, True):
            with self.subTest(nack=nack):
                hardware = debug.Hardware(self.log)
                hardware.authorize_rf = True
                hardware.manifest = json.loads(bench.MANIFEST.read_text())
                hardware.images = image_evidence(hardware.run_id)
                hardware.monitors = {"receiver": {}, "gateway": {}}
                commands: list[tuple[str, str]] = []

                def wire(
                    role: str,
                    value: str,
                    nack: bool = nack,
                    commands: list[tuple[str, str]] = commands,
                ) -> None:
                    commands.append((role, value))
                    self.log.record("HOST_" + role.upper(), value)
                    if value == "?":
                        if role == "receiver":
                            self.log.record("RECEIVER", "[RECEIVER] TRACKER_GPIO LORA_EN=0 SD_CS=1")
                        identity = (
                            " BUILD_ID=",
                            " CONFIG_FINGERPRINT=",
                            " PROTOCOL_VERSION=",
                            " RADIO_INIT_OK",
                            " RADIO_SPI_VERSION=",
                            " RADIO_PROFILE ",
                            " RADIO_MOD ",
                            " RADIO_FRAME ",
                            " RADIO_READY",
                        )
                        for row in journal(nack):
                            if row["role"] == role.upper() and any(
                                marker in row["line"] for marker in identity
                            ):
                                self.log.record(role.upper(), row["line"])
                        self.log.record(
                            role.upper(),
                            f"[{role.upper()}] RADIO_POWER VERSIONS=3 PA=F0 OCP=37 LNA=23 DAC=84",
                        )
                        self.log.record(
                            role.upper(),
                            f"[{role.upper()}] RADIO_REG MODE=85 FRF=E4C000 MC=727404 PRE=8 "
                            "IQ=27 SYNC=12 DIO=00 MASK=00",
                        )
                    elif marker := {
                        "R": "RX_READY" if role == "receiver" else "RADIO_READY",
                        "T": "BENCH_TX_READY",
                        "P": "PARKED E=0",
                    }.get(value):
                        self.log.record(role.upper(), f"[{role.upper()}] {marker}")
                    elif value == "S":
                        for row in journal(nack):
                            if (
                                " T=" in row["line"]
                                or "PAYLOAD_BYTES" in row["line"]
                                or "DATA_TX_REQUESTED" in row["line"]
                            ):
                                self.log.record(row["role"], row["line"])
                                if "PAYLOAD_BYTES" in row["line"]:
                                    self.log.record(
                                        "RECEIVER",
                                        "[RECEIVER] DATA_ADDRESS SID=1234 Q=1 SRC=0 DST=1 CRC=OK",
                                    )
                                for old, new in (
                                    ("DATA_TX_DONE", "RX_REARMED"),
                                    ("ACK_ACCEPTED", "ACK_RX"),
                                ):
                                    if old in row["line"]:
                                        self.log.record(row["role"], row["line"].replace(old, new))

                with (
                    patch.object(hardware, "command", side_effect=wire),
                    patch.object(time, "sleep"),
                ):
                    result = hardware.exchange(nack=nack)
                self.assertEqual(result["status"], "PASS", result)
                self.assertTrue(any("DATA_TX_BEGIN SID=" in event for event in result["events"]))
                self.assertEqual(commands.count(("gateway", "S")), 1)
                self.assertEqual(commands[-2:], [("receiver", "P"), ("gateway", "P")])

    def test_cleanup_continues_when_one_monitor_cannot_stop(self) -> None:
        hardware = debug.Hardware(self.log)
        hardware.monitors = {"receiver": {}, "gateway": {}}
        with (
            patch.object(hardware, "_park"),
            patch.object(rf_proof, "stop_rf_monitor", side_effect=[OSError("gone"), 0]) as stop,
        ):
            hardware.close()
        self.assertEqual(stop.call_count, 2)
        self.assertEqual(hardware.monitors, {})


if __name__ == "__main__":
    unittest.main()
