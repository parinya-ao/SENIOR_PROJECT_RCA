"""Acquisition boundary: command recovery cannot authorize incomplete evidence."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

from tools.arq_trial import (
    Capture,
    capture_tracker_diagnostics,
    close_updi_without_recovery,
    drain_updi_messages,
    read_reset_state,
    sample_updi_idle,
    write_virtual_uart,
)


class CaptureTests(unittest.TestCase):
    def test_reverse_rx_rejects_lf_bank_before_send(self) -> None:
        from tools import arq_trial

        c = Mock()
        c.seen.side_effect = lambda role, name: (
            [{"rc": "0", "mode": str(0x8D)}] if name == "RAW_RX_READY" else []
        )
        with self.assertRaisesRegex(ValueError, "RX continuous"):
            arq_trial.reverse_exchange(c)
        self.assertEqual(c.command.call_args_list, [unittest.mock.call("sender", "RX")])

    def test_campaign_rejects_evidence_directory_outside_artifact_root(self) -> None:
        from tools import arq_trial

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(arq_trial, "ROOT", root), patch("generate_lora_config.generate"):
                try:
                    arq_trial.campaign(run_dir=root / "outside")
                except TypeError as error:
                    self.fail(
                        "campaign must validate its output directory before hardware access: "
                        + str(error)
                    )
                except ValueError as error:
                    self.assertIn("artifacts/arq", str(error))
                else:
                    self.fail("campaign accepted an evidence path outside artifacts/arq")

    def test_virtual_uart_writer_waits_for_mailbox_space_and_preserves_order(self) -> None:
        class Writer:
            def __init__(self) -> None:
                self.responses = [False, True, True]
                self.calls: list[tuple[Any, Any]] = []

            def send1(self, byte: Any, blocking: Any) -> Any:
                self.calls.append((byte, blocking))
                return self.responses.pop(0)

        writer = Writer()
        accepted = bytearray()
        with (
            patch("tools.arq_trial.time.monotonic", return_value=0),
            patch("tools.arq_trial.time.sleep"),
        ):
            result = write_virtual_uart(writer, b"AB", accepted=accepted)
        self.assertEqual(result, b"AB")
        self.assertEqual(accepted, b"AB")
        self.assertEqual(writer.calls, [(ord("A"), False), (ord("A"), False), (ord("B"), False)])

    def test_virtual_uart_writer_times_out_and_keeps_partial_evidence(self) -> None:
        class Writer:
            def __init__(self) -> None:
                self.responses = [True, False]

            def send1(self, byte: Any, blocking: Any) -> Any:
                return self.responses.pop(0)

        accepted = bytearray()
        with (
            patch("tools.arq_trial.time.monotonic", side_effect=[0, 0, 2]),
            patch("tools.arq_trial.time.sleep"),
        ):
            with self.assertRaisesRegex(TimeoutError, "byte 1 was not accepted"):
                write_virtual_uart(Writer(), b"AB", per_byte_timeout=1, accepted=accepted)
        self.assertEqual(accepted, b"A")

    def test_updi_output_drain_reads_messages_without_cpu_control_writes(self) -> None:
        class Protocol:
            ASI_OCD_STATUS = 5
            ASI_OCD_MESSAGE = 13
            OCDMV = 0x10

        class Link:
            def __init__(self) -> None:
                self.messages = [ord("A"), ord("B")]
                self.calls: list[Any] = []

            def ldcs(self, address: Any) -> Any:
                self.calls.append(address)
                if address == Protocol.ASI_OCD_STATUS:
                    return Protocol.OCDMV if self.messages else 0
                return self.messages.pop(0)

        link = Link()
        raw, statuses = drain_updi_messages(link, Protocol, max_bytes=2)
        self.assertEqual(raw, b"AB")
        self.assertEqual(statuses, [Protocol.OCDMV, Protocol.OCDMV])
        self.assertEqual(link.calls, [5, 13, 5, 13])

    def test_updi_output_drain_waits_for_newline_after_a_quiet_gap(self) -> None:
        class Clock:
            now = 0.0

            def monotonic(self) -> Any:
                return self.now

            def sleep(self, seconds: Any) -> None:
                self.now += seconds

        clock = Clock()

        class Protocol:
            ASI_OCD_STATUS = 5
            ASI_OCD_MESSAGE = 13
            OCDMV = 0x10

        line = b"A t=1 e=STATUS s=1\n"

        class Link:
            def __init__(self) -> None:
                self.first = bytearray(line[:8])
                self.rest = bytearray(line[8:])

            def ldcs(self, address: Any) -> Any:
                if address == Protocol.ASI_OCD_STATUS:
                    return Protocol.OCDMV if self.first or (clock.now >= 6.0 and self.rest) else 0
                if self.first:
                    return self.first.pop(0)
                return self.rest.pop(0)

        with (
            patch("tools.arq_trial.time.monotonic", clock.monotonic),
            patch("tools.arq_trial.time.sleep", clock.sleep),
        ):
            raw, _ = drain_updi_messages(Link(), Protocol, timeout=8.0, quiet_period=0.1)
        self.assertEqual(raw, line)

    def test_tracker_diagnostics_read_mailbox_and_buffered_output_without_reset(self) -> None:
        class Protocol:
            UART_FLAGS = 0x1E
            FLAG_RX = 0x02
            ASI_OCD_STATUS = 5
            ASI_OCD_MESSAGE = 13
            OCDMV = 0x10

        message = b"A t=1 e=RAW_TX_DONE s=0 rc=0 flags=8\n"

        class Link:
            def __init__(self) -> None:
                self.output = bytearray(message)

            def lds8(self, address: Any) -> int:
                if address != Protocol.UART_FLAGS:
                    raise AssertionError(address)
                return 1

            def ldcs(self, address: Any) -> Any:
                if address == Protocol.ASI_OCD_STATUS:
                    return Protocol.OCDMV if self.output else 0
                return self.output.pop(0)

        c = Capture(None)
        with tempfile.TemporaryDirectory() as directory:
            proof = SimpleNamespace(run_dir=Path(directory))
            record: dict[str, Any] = {}
            output = capture_tracker_diagnostics(c, proof, Link(), Protocol, record, "post_window")
            self.assertEqual(output, message)
            self.assertEqual(
                (Path(directory) / "tracker-updi-output-post_window.bin").read_bytes(), message
            )
        self.assertFalse(record["post_window_uart_rx_pending"])
        self.assertNotIn("post_window_final_newline_consumed", record)
        event = c.events[0]
        self.assertEqual(
            (event["role"], event["e"], event["buffered_after_window"]),
            ("receiver", "RAW_TX_DONE", True),
        )

    def test_close_updi_without_recovery_closes_port_without_transport_write(self) -> None:
        for wrapped in (False, True):
            with self.subTest(wrapped=wrapped):
                device = Mock()
                link = SimpleNamespace(ser=SimpleNamespace(dev=device))
                session = SimpleNamespace(updi=link) if wrapped else link
                close_updi_without_recovery(session)
                device.close.assert_called_once_with()
                self.assertIsNone(link.ser)
                if wrapped:
                    self.assertIsNone(session.updi)

    def test_reset_state_capture_reads_gprior0_rstfr_and_uart_flags_only(self) -> None:
        class Protocol:
            UART_FLAGS = 0x1E

        class Link:
            def __init__(self) -> None:
                self.calls: list[tuple[Any, ...]] = []

            def lds8(self, address: Any) -> Any:
                self.calls.append(address)
                return {0x1C: 0x02, 0x40: 0, 0x1E: 1}[address]

        link = Link()
        self.assertEqual(
            read_reset_state(link, Protocol), {"gpior0": 0x02, "rstfr": 0, "uart_flags": 1}
        )
        self.assertEqual(link.calls, [0x1C, 0x40, 0x1E])

    def test_reset_state_resync_opens_one_ocd_session_without_reset(self) -> None:
        class Device:
            def __init__(self) -> None:
                self.closed = False

            def close(self) -> None:
                self.closed = True

        device = Device()
        old_link = SimpleNamespace(ser=SimpleNamespace(dev=device))
        old_session = SimpleNamespace(updi=old_link)
        calls: list[tuple[Any, ...]] = []

        class Protocol:
            KEY_OCD = b"OCD"
            UART_FLAGS = 0x1E

            class UPDI:
                def __init__(self, port: Any, baud: Any) -> None:
                    calls.append(("open", port, baud))
                    self.reads: list[Any] = []

                def key(self, value: Any) -> None:
                    calls.append(("key", value))

                def lds8(self, address: Any) -> Any:
                    calls.append(("read", address))
                    return {0x1C: 1, 0x40: 0, 0x1E: 0}[address]

        resync = getattr(
            __import__("tools.arq_trial", fromlist=["resync_reset_state_once"]),
            "resync_reset_state_once",
            None,
        )
        if not callable(resync):
            self.fail("read-only reset-state resync helper is missing")
        session, state = resync(old_session, Protocol, "/dev/test-tracker")

        self.assertTrue(device.closed)
        self.assertIsInstance(session, Protocol.UPDI)
        self.assertEqual(state, {"gpior0": 1, "rstfr": 0, "uart_flags": 0})
        self.assertEqual(
            calls,
            [
                ("open", "/dev/test-tracker", 38400),
                ("key", b"OCD"),
                ("read", 0x1C),
                ("read", 0x40),
                ("read", 0x1E),
            ],
        )

    def test_updi_idle_control_takes_two_read_only_samples_with_bounded_wait(self) -> None:
        class Protocol:
            UART_FLAGS = 0x1E

        class Link:
            def __init__(self) -> None:
                self.values = iter([32, 0, 1, 32, 0, 1])

            def lds8(self, address: Any) -> Any:
                return next(self.values)

        with (
            patch("tools.arq_trial.time.sleep") as sleep,
            patch("tools.arq_trial.time.monotonic_ns", side_effect=[100, 250]),
        ):
            result = sample_updi_idle(Link(), Protocol, 15)
        self.assertEqual(result["before"], {"gpior0": 32, "rstfr": 0, "uart_flags": 1})
        self.assertEqual(result["after"], result["before"])
        self.assertEqual(result["duration_ns"], 150)
        sleep.assert_called_once_with(15)

    def test_programming_failure_still_attempts_verified_normal_restore(self) -> None:
        from tools import arq_trial

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "generated").mkdir()
            (root / "generated/arq_manifest.json").write_text("{}")
            build = root / ".pio/build/receiver_arq_radio_only"
            build.mkdir(parents=True)
            for suffix in ("hex", "elf"):
                (build / ("firmware." + suffix)).write_text("image")
            with (
                patch.object(arq_trial, "ROOT", root),
                patch("generate_lora_config.generate"),
                patch.object(
                    getattr(arq_trial, "subprocess"), "check_output", return_value="config"
                ),
                patch.object(getattr(arq_trial, "rf"), "check_port_owners", return_value=[]),
                patch.object(getattr(arq_trial, "rf"), "program_application", return_value=1),
                patch.object(arq_trial, "prepare", return_value=root / "standby") as restore,
            ):
                with self.assertRaisesRegex(ValueError, "programming failed"):
                    arq_trial.campaign()
                restore.assert_called_once()

    def make_capture(self, responses: Any = True) -> Any:
        c = Capture(None)
        get = c.queue.get
        setattr(c.queue, "get", lambda **kwargs: get(block=False))
        c.monitors = {
            r: {"process": SimpleNamespace(poll=lambda: None)} for r in ("sender", "receiver")
        }
        self.clock: float = 0.0

        def monotonic() -> Any:
            self.clock += 0.25
            return self.clock

        def command(role: Any, text: Any) -> None:
            c.commands.append({"role": role, "text": text})
            if responses and text == "STATUS":
                for event in self.status(role):
                    c.queue.put((role, "stdout", event.encode()))

        setattr(c, "command", command)
        return c, monotonic

    def status(self, role: Any, overflow: Any = 0, build: Any = "build") -> Any:
        return [
            "A t=1 e=BOOT s=0 rc=0 v=4",
            f"A t=1 e=IDENTITY s=0 build={build} config=config",
            f"A t=1 e=STATUS s=0 ready=1 overflow={overflow}",
            "A t=1 e=REG s=0 bytes=8100",
            f"A t=1 e=STATUS_END s=0 v={overflow}",
        ]

    def acquire(self, c: Any, clock: Any) -> None:
        with patch("tools.arq_trial.time.monotonic", clock):
            c.acquire({r: {"build_id": "build"} for r in c.monitors}, "config")

    def test_missing_startup_recovers_once_and_drains_each_role(self) -> None:
        c, clock = self.make_capture()
        self.acquire(c, clock)
        self.assertEqual(
            c.commands, [{"role": r, "text": "STATUS"} for r in ("sender", "receiver")]
        )
        self.assertLess(self.clock, 45)

    def test_absent_and_partial_responses_stop_without_arm(self) -> None:
        for partial in (False, True):
            c, clock = self.make_capture(False)
            if partial:
                c.queue.put(("sender", "stdout", b"A t=1 e=STATUS s=0 ready=1 overflow=0"))
            with self.assertRaisesRegex(ValueError, "capture deadline"):
                self.acquire(c, clock)
            self.assertTrue(all(x["text"] == "STATUS" for x in c.commands))
            self.assertLessEqual(self.clock, 46)

    def test_complete_startup_needs_no_recovery(self) -> None:
        c, clock = self.make_capture()
        for role in c.monitors:
            for e in self.status(role):
                c.queue.put((role, "stdout", e.encode()))
        self.acquire(c, clock)
        self.assertEqual(c.commands, [])

    def test_next_gate_requires_complete_status_from_previous_session(self) -> None:
        c, clock = self.make_capture()
        for role in c.monitors:
            for e in self.status(role):
                c.queue.put((role, "stdout", e.replace("s=0", "s=10").encode()))
        with patch("tools.arq_trial.time.monotonic", clock):
            c.acquire({r: {"build_id": "build"} for r in c.monitors}, "config", expected_session=16)
        self.assertEqual(c.commands, [])

    def test_overflow_identity_and_monitor_exit_fail_closed(self) -> None:
        for problem in ("overflow", "identity", "exit"):
            c, clock = self.make_capture()
            for role in c.monitors:
                for e in self.status(
                    role,
                    overflow=int(problem == "overflow"),
                    build="wrong" if problem == "identity" else "build",
                ):
                    c.queue.put((role, "stdout", e.encode()))
            if problem == "exit":
                c.monitors["sender"]["process"].poll = lambda: 1
            with self.assertRaises(ValueError):
                self.acquire(c, clock)
            self.assertEqual(c.commands, [])

    def test_reverse_capture_can_keep_gateway_window_after_tracker_monitor_exit(self) -> None:
        c, clock = self.make_capture()
        c.monitors["receiver"]["process"].poll = lambda: 1
        c.queue.put(("sender", "stdout", b"A t=2 e=RAW_RX_TIMEOUT s=0"))
        with patch("tools.arq_trial.time.monotonic", clock):
            c.wait(
                lambda: bool(c.seen("sender", "RAW_RX_TIMEOUT")),
                5,
                ignore_exited_roles=("receiver",),
            )
        self.assertEqual(c.monitor_exits, [{"role": "receiver", "exit_code": 1}])

    def test_cleanup_stops_all_monitors_and_retains_partial_evidence(self) -> None:
        c, _ = self.make_capture()
        c.queue.put(("sender", "stdout", b"A t=1 e=STATUS s=0 ready=1 overflow=0"))
        with patch("tools.arq_trial.rf.stop_rf_monitor") as stop:
            c.close()
        self.assertEqual(stop.call_count, 2)
        self.assertEqual(c.events[0]["e"], "STATUS")

    def test_cleanup_records_truncated_tail_without_masking_original_failure(self) -> None:
        c, _ = self.make_capture()
        c.queue.put(("sender", "stdout", b"A t=1 e=IDEN"))
        with patch("tools.arq_trial.rf.stop_rf_monitor"):
            c.close()
        self.assertTrue(c.errors)
