"""Portable ARQ assertions, strict config and bounded evidence tests."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/config"))


class ArqTests(unittest.TestCase):
    def test_adapter(self) -> None:
        for role in ("sender", "receiver"):
            self.assertTrue((ROOT / f"src/{role}/appcode/arq/{role}.cpp").is_file())
        with tempfile.TemporaryDirectory() as directory:
            objects = []
            for source in ("codec", "sender", "receiver"):
                obj = str(Path(directory) / (source + ".o"))
                objects.append(obj)
                subprocess.run(
                    [
                        "clang",
                        "--driver-mode=g++",
                        "-std=c++17",
                        "-Istable_lib/arq",
                        "-Iinclude",
                        "-c",
                        f"stable_lib/arq/{source}.cpp",
                        "-o",
                        obj,
                    ],
                    cwd=ROOT,
                    check=True,
                )
                symbols = subprocess.check_output(["nm", "-u", obj], text=True)
                for name in (" malloc", " calloc", " realloc", " free"):
                    self.assertNotIn(name, symbols)
            for role in ("SENDER", "RECEIVER"):
                binary = str(Path(directory) / role)
                subprocess.run(
                    [
                        "clang",
                        "--driver-mode=g++",
                        "-std=c++17",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-Wno-unused-variable",
                        "-Wno-unused-function",
                        "-Itests/arq/stub",
                        "-Isrc",
                        "-Itests/raw_mvp_stub",
                        "-Iinclude",
                        "-Istable_lib/arq",
                        "-DLORA_ROLE_" + role,
                        "-DARQ_TEST_MODE",
                        '-DLORA_BUILD_ID="host-test"',
                        "tests/arq/adapter_test.cpp",
                        *objects,
                        "-o",
                        binary,
                    ],
                    cwd=ROOT,
                    check=True,
                )
                subprocess.run([binary], check=True)
                if role == "SENDER":
                    subprocess.run([binary, "expired-ack"], check=True)
                    subprocess.run([binary, "ack-sequences"], check=True)
                for failure in ("begin", "power", "header", "crc", "iq", "rx", "standby"):
                    subprocess.run([binary, failure], check=True)

    def test_portable_core(self) -> None:
        self.assertTrue((ROOT / "stable_lib/arq/arq.h").exists(), "ARQ core missing")
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "core"
            subprocess.run(
                [
                    "clang",
                    "--driver-mode=g++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-Wno-misleading-indentation",
                    "-g",
                    "-fsanitize=address,undefined",
                    "-fno-omit-frame-pointer",
                    "-Istable_lib/arq",
                    "-Iinclude",
                    "tests/arq/core_test.cpp",
                    "stable_lib/arq/codec.cpp",
                    "stable_lib/arq/sender.cpp",
                    "stable_lib/arq/receiver.cpp",
                    "-o",
                    str(binary),
                ],
                cwd=ROOT,
                check=True,
            )
            subprocess.run([str(binary)], check=True)

    def test_config_and_board_generation(self) -> None:
        from tools.config.arq_config import arq_artifacts, load_arq, validate_arq
        from tools.config.generate_lora_config import load_radio_profile
        from tools.config.validate_lora_ssot import load

        cfg = load_arq()
        self.assertEqual(cfg["frequency_hz"], 915_000_000)
        self.assertEqual(cfg["tx_power_dbm"], 2)
        # 44-byte SX127x frame is 92,416 us at SF7/BW125/CR4/5; require a 1% guard.
        self.assertGreaterEqual(cfg["spacing_ms"], 9242)
        for key, value in [
            ("sender_id", True),
            ("receiver_id", 1),
            ("ack_min_ms", 0),
            ("ack_max_ms", 1999),
            ("max_retries", 31),
            ("tx_ms", 2**31),
            ("payload", "x" * 33),
            ("frequency_hz", 868000000),
            ("frequency_hz", 923000000),
        ]:
            bad = copy.deepcopy(cfg)
            bad[key] = value
            with self.assertRaises(ValueError, msg=key):
                validate_arq(bad)
        radio = load_radio_profile()
        board = load(ROOT / "config/lora_system.json")
        outputs = arq_artifacts(cfg, radio, board, "test-source")
        self.assertEqual(outputs, arq_artifacts(cfg, radio, board, "test-source"))
        self.assertIn("PIN_PD0", outputs["stable_lib/arq/board_ssot.c"])
        self.assertIn("SPI1_SWAP_DEFAULT", outputs["include/generated/board_ssot.h"])
        self.assertNotIn("SPI1_SWAP_DEFAULT", outputs["stable_lib/arq/board_ssot.c"])
        manifest_radio = json.loads(outputs["generated/arq_manifest.json"])["radio"]
        self.assertEqual(manifest_radio["frequency_hz"], 915_000_000)
        self.assertEqual(manifest_radio["tx_power_dbm"], 2)

    def test_evidence_rejects_text_and_synthetic(self) -> None:
        from tools.arq_trial import validate_bundle

        for value in ({}, {"physical": True}, {"synthetic": True, "events": []}):
            with self.assertRaises(ValueError):
                validate_bundle(value)

    def test_event_and_session_boundaries(self) -> None:
        from tools.arq_trial import parse_event, reserve_session, wire_frame

        self.assertIsNone(parse_event("transport banner"))
        event = parse_event("A t=42 e=ARM s=12345678 q=0 a=0 rc=0 v=1")
        if event is None:
            self.fail("valid ARM event did not parse")
        self.assertEqual(event["s"], "12345678")
        boot_event = parse_event("A t=1 e=BOOT s=0")
        if boot_event is None:
            self.fail("valid BOOT event did not parse")
        self.assertEqual(boot_event["s"], "0")
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(reserve_session(Path(d)), 1)
            self.assertEqual(reserve_session(Path(d)), 2)
        f = wire_frame("010101027856341200000B0048656C6C6F20576F726C64")
        self.assertEqual(
            (f["session"], f["sequence"], f["payload"]), (0x12345678, 0, b"Hello World")
        )
        for raw in ("00", "010101027856341200002100", "01020102785634120000010000"):
            with self.assertRaises(ValueError):
                wire_frame(raw)

    def test_evidence_events_must_match_raw_capture(self) -> None:
        from tools.arq_trial import checked_events

        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            line = "A t=1 e=ARM s=00000001 q=0 a=0 rc=0 v=1\n"
            for role in ("sender", "receiver"):
                (directory / f"rf-monitor-{role}.stdout.log").write_text(line)
            with self.assertRaises(ValueError):
                checked_events([], directory)
            from tools.arq_trial import parse_event

            events: list[dict[str, Any]] = []
            for role in ("sender", "receiver"):
                event = parse_event(line)
                if event is None:
                    self.fail("valid event did not parse")
                events.append({**event, "role": role, "host_ns": 1})
            self.assertEqual(len(checked_events(events, directory)), 2)
            events[0]["rc"] = "-1"
            with self.assertRaises(ValueError):
                checked_events(events, directory)

    def test_capture_close_keeps_final_stream_events(self) -> None:
        from tools.arq_trial import Capture

        capture = Capture(None)
        capture.queue.put(("sender", "stdout", b"A t=1 e=REG s=1 bytes=00\n"))
        capture.close()
        self.assertEqual(len(capture.events), 1)

    def test_final_status_requires_current_session_and_no_overflow(self) -> None:
        from tools.arq_trial import status_complete

        events = [
            {"role": "sender", "e": "STATUS", "s": "0"},
            {"role": "sender", "e": "STATUS_END", "s": "0", "v": "0"},
        ]
        self.assertFalse(status_complete(events, "sender", 1))
        events.append({"role": "sender", "e": "STATUS", "s": "1"})
        events.append({"role": "sender", "e": "STATUS_END", "s": "1", "v": "1"})
        self.assertFalse(status_complete(events, "sender", 1))
        events.append({"role": "sender", "e": "STATUS_END", "s": "1", "v": "0"})
        self.assertTrue(status_complete(events, "sender", 1))
        events.append({"role": "sender", "e": "STATUS", "s": "1"})
        self.assertFalse(status_complete(events, "sender", 1))

    def test_rf_cli_requires_physical_confirmation(self) -> None:
        from tools import arq_trial

        for mode in ("--mvp", "--campaign"):
            with (
                patch.object(sys, "argv", ["arq_trial", mode]),
                patch.object(arq_trial, "campaign") as campaign,
            ):
                with self.assertRaises(SystemExit) as error:
                    arq_trial.main()
                self.assertEqual(error.exception.code, 2)
                campaign.assert_not_called()

    def test_mvp_order_is_one_then_negative_recovery_then_ten(self) -> None:
        from tools import arq_trial

        with (
            patch.object(
                sys,
                "argv",
                [
                    "arq_trial",
                    "--mvp",
                    "--rf-path-confirmed",
                    "--physical-mapping-verified",
                    "--power-verified",
                    "--rf-hardware-verified",
                    "--authorize-rf-test",
                ],
            ),
            patch.object(arq_trial, "campaign") as campaign,
        ):
            arq_trial.main()
            campaign.assert_called_once_with((("H01", 1), ("H02", 1), ("H03", 1), ("H04", 10)))

    def test_unregistered_arq_environments_have_no_flash_write_bounds(self) -> None:
        from tools.rf_proof import application_bounds_for_environment

        config = subprocess.check_output(
            ["pio", "project", "config", "--json-output"], cwd=ROOT, text=True
        )
        for role in ("sender", "receiver"):
            for suffix in ("", "_test"):
                self.assertIsNone(
                    application_bounds_for_environment(config, role + "_arq" + suffix)
                )


if __name__ == "__main__":
    unittest.main()
