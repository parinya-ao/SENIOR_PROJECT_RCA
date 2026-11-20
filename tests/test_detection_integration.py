from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any, Never
from unittest.mock import patch

if TYPE_CHECKING:
    from types import ModuleType

evidence = importlib.import_module("tools.device_detection.evidence")
identity = importlib.import_module("tools.device_detection.firmware_identity")
detector = importlib.import_module("tools.device_detection.role_detector")
output = importlib.import_module("tools.device_detection.output")
updi_probe = importlib.import_module("tools.device_detection.updi_probe")
Json = Any


def require(test: unittest.TestCase, module: ModuleType, name: str) -> Json:
    value = getattr(module, name, None)
    test.assertIsNotNone(value, f"{module.__name__}.{name} must exist")
    return value


class DetectionIntegrationTests(unittest.TestCase):
    def test_json_output_keeps_unknown_role_unknown_and_has_exit_two(self) -> None:
        usb_cls = require(self, evidence, "USBDevice")
        classify = require(self, detector, "classify_devices")
        encode = require(self, output, "result_to_json")
        exit_code = require(self, output, "exit_code_for")
        if any(x is None for x in (usb_cls, classify, encode, exit_code)):
            return
        result = classify(
            [
                usb_cls(
                    device_node="/dev/ttyUSB1",
                    real_device_path="/dev/ttyUSB1",
                    usb_path="usb-0:4:1.0",
                    vid="10c4",
                    pid="ea60",
                    serial_number="0001",
                    present=True,
                )
            ]
        )
        payload = json.loads(encode(result))
        self.assertEqual(payload["status"], "UNKNOWN")
        self.assertEqual(payload["devices"][0]["role"], "UNKNOWN")
        self.assertEqual(payload["devices"][0]["identity_status"], "UNKNOWN")
        self.assertEqual(exit_code(result), 2)

    def test_human_output_explains_mcu_identity_is_not_role(self) -> None:
        usb_cls = require(self, evidence, "USBDevice")
        probe_cls = require(self, evidence, "ProbeEvidence")
        classify = require(self, detector, "classify_devices")
        render = require(self, output, "format_text")
        if any(x is None for x in (usb_cls, probe_cls, classify, render)):
            return
        dev = usb_cls(
            device_node="/dev/ttyUSB0",
            real_device_path="/dev/ttyUSB0",
            usb_path="usb-0:1:1.0",
            present=True,
        )
        result = classify([dev], {dev.device_node: probe_cls(mcu_identity="AVR128DA28")})
        text = render(result, explain=True)
        self.assertIn("UNKNOWN", text)
        self.assertIn("MCU identity does not establish firmware role", text)

    def test_passive_scan_does_not_open_a_serial_port(self) -> None:
        cli = importlib.import_module("tools.detect_devices")
        inventory_cls = require(
            self, importlib.import_module("tools.device_detection.usb_inventory"), "InventoryResult"
        )
        usb_cls = require(self, evidence, "USBDevice")
        if inventory_cls is None or usb_cls is None:
            return
        args = cli.build_parser().parse_args(["--scan"])
        inventory = inventory_cls(
            (
                usb_cls(
                    device_node="/dev/ttyUSB0",
                    real_device_path="/dev/ttyUSB0",
                    usb_path="usb-1",
                    present=True,
                ),
            ),
            (),
            {},
        )
        with patch.object(
            cli, "_probe_device", side_effect=AssertionError("passive scan opened UPDI")
        ):
            result, _ = cli._scan(args, inventory_fn=lambda: inventory)
        self.assertEqual(result.devices[0].role, "UNKNOWN")

    def test_exit_codes_separate_conflict_from_probe_error(self) -> None:
        scan = require(self, detector, "classify_devices")
        code = require(self, output, "exit_code_for")
        if scan is None or code is None:
            return
        self.assertEqual(code(scan([])), 2)
        self.assertEqual(
            code(
                type(
                    "Result",
                    (),
                    {
                        "status": "CONFLICT",
                        "devices": (),
                    },
                )()
            ),
            3,
        )
        self.assertEqual(
            code(
                type(
                    "Result",
                    (),
                    {
                        "status": "ERROR",
                        "devices": (),
                    },
                )()
            ),
            4,
        )

    def test_cli_refuses_target_probe_without_hardware_safety_assertion(self) -> None:
        cli = importlib.import_module("tools.detect_devices")
        parse = require(self, cli, "build_parser")
        if parse is None:
            return
        with self.assertRaises(SystemExit):
            parse().parse_args(["--scan", "--probe-updi"])

    def test_updi_probe_and_flash_read_are_blocked_without_explicit_safety(self) -> None:
        sib = require(self, updi_probe, "probe_target_sib")
        flash = require(self, updi_probe, "read_firmware_flash")
        if sib is None or flash is None:
            return
        calls = []

        def runner(*args: Json, **_kwargs: Json) -> Never:
            calls.append(args[0])
            msg = "blocked probe must not run a command"
            raise AssertionError(msg)

        with self.assertRaises(PermissionError):
            sib("/dev/fake", hardware_safe=False, command_runner=runner)
        with self.assertRaises(PermissionError):
            flash("/dev/fake", hardware_safe=False, flash_size=1024, command_runner=runner)
        self.assertEqual(calls, [])

    def test_occupied_port_is_not_opened_for_an_updi_probe(self) -> None:
        probe = require(self, updi_probe, "probe_target_sib")
        if probe is None:
            return
        opened = []

        def runner(_argv: list[str], **_kwargs: Json) -> Json:
            return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": "python 42"})()

        def pio(argv: list[str], **_kwargs: Json) -> Never:
            opened.append(argv)
            msg = "busy device must not be opened"
            raise AssertionError(msg)

        result = probe("/dev/fake", hardware_safe=True, command_runner=runner, popen=pio)
        self.assertEqual(result.access_status, "INACCESSIBLE")
        self.assertEqual(opened, [])

    def test_sib_uses_upditerm_without_reset_and_mcu_does_not_set_role(self) -> None:
        probe = require(self, updi_probe, "probe_target_sib")
        if probe is None:
            return
        seen = []

        class Process:
            returncode = 0

            def communicate(self, timeout: float | None = None) -> tuple[str, str]:
                return "AVR128DA28 SIB", ""

        def pio(argv: list[str], **_kwargs: Json) -> Json:
            seen.append(argv)
            return Process()

        def runner(_argv: list[str], **_kwargs: Json) -> Json:
            return type("Completed", (), {"returncode": 1, "stdout": "", "stderr": ""})()

        result = probe("/dev/fake", hardware_safe=True, command_runner=runner, popen=pio)
        self.assertEqual(result.mcu_identity, "AVR128DA28")
        self.assertEqual(result.firmware_identity, None)
        self.assertIn("-i", seen[0])
        self.assertNotIn("-r", seen[0])

    def test_firmware_probe_uses_upditerm_log_without_reset(self) -> None:
        probe = require(self, updi_probe, "probe_firmware_identity")
        if probe is None:
            return
        seen = []

        class Process:
            returncode = 0

            def communicate(self, timeout: float | None = None) -> tuple[str, str]:
                return "", ""

        def pio(argv: list[str], **_kwargs: Json) -> Json:
            seen.extend(argv)
            log_path = argv[argv.index("-l") + 1]
            with Path(log_path).open("wb") as stream:
                stream.write(b"[SENDER] ID V1 sender Nov  6 2026 05:00:00 CRC=15\r\n")
            return Process()

        def runner(_argv: list[str], **_kwargs: Json) -> Json:
            return type("Completed", (), {"returncode": 1, "stdout": "", "stderr": ""})()

        result = probe("/dev/fake", hardware_safe=True, command_runner=runner, popen=pio)
        self.assertEqual(result.firmware_status, "OK")
        self.assertIsNotNone(result.firmware_identity)
        self.assertNotIn("-r", seen)

    def test_complete_firmware_identity_survives_bounded_monitor_stop(self) -> None:
        import subprocess

        probe = require(self, updi_probe, "probe_firmware_identity")
        if probe is None:
            return

        class Process:
            returncode = 0
            calls = 0

            def communicate(self, timeout: float | None = None) -> tuple[str, str]:
                """Simulate one timed-out probe followed by a clean retry."""
                self.calls += 1
                if self.calls == 1:
                    if timeout is None:
                        message = "the UPDI probe must supply a timeout"
                        raise AssertionError(message)
                    command = "upditerm"
                    raise subprocess.TimeoutExpired(command, timeout)
                return "", ""

            def send_signal(self, _signal: int) -> None:
                return

        def popen(argv: list[str], **_kwargs: Json) -> Process:
            logfile = Path(argv[argv.index("-l") + 1])
            logfile.write_bytes(b"[SENDER] ID V1 sender Nov  6 2026 05:00:00 CRC=15\r\n")
            return Process()

        result = probe(
            "/dev/fake",
            hardware_safe=True,
            timeout=0.1,
            command_runner=lambda *_args, **_kwargs: type(
                "Completed", (), {"returncode": 1, "stdout": "", "stderr": ""}
            )(),
            popen=popen,
        )
        self.assertEqual(result.firmware_status, "OK")
        self.assertEqual(result.parse_status, "VALID")
        self.assertEqual(result.firmware_identity.role, "SENDER")


if __name__ == "__main__":
    unittest.main()
