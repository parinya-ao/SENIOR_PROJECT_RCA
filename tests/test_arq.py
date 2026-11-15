"""Portable ARQ assertions, strict config and bounded evidence tests."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/config"))


class ArqTests(unittest.TestCase):
    def test_adapter(self) -> None:
        self.assertTrue((ROOT / "src/arq/main.cpp").exists(), "ARQ adapter missing")
        with tempfile.TemporaryDirectory() as directory:
            objects = []
            for source in ("codec", "sender", "receiver"):
                obj = str(Path(directory) / (source + ".o"))
                objects.append(obj)
                subprocess.run(
                    [
                        "clang",
                        "-std=c11",
                        "-Isrc/arq",
                        "-Iinclude",
                        "-c",
                        f"src/arq/{source}.c",
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
                        "-std=c++11",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-Wno-unused-variable",
                        "-Wno-unused-function",
                        "-Itests/arq/stub",
                        "-Itests/raw_mvp_stub",
                        "-Iinclude",
                        "-Isrc/arq",
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
        self.assertTrue((ROOT / "src/arq/arq.h").exists(), "ARQ core missing")
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "core"
            subprocess.run(
                [
                    "clang",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-Wno-misleading-indentation",
                    "-g",
                    "-fsanitize=address,undefined",
                    "-fno-omit-frame-pointer",
                    "-Isrc/arq",
                    "-Iinclude",
                    "tests/arq/core_test.c",
                    "src/arq/codec.c",
                    "src/arq/sender.c",
                    "src/arq/receiver.c",
                    "-o",
                    str(binary),
                ],
                cwd=ROOT,
                check=True,
            )
            subprocess.run([str(binary)], check=True)

    def test_config_and_board_generation(self) -> None:
        from arq_config import arq_artifacts, load_arq, validate_arq
        from generate_lora_config import load_radio_profile
        from validate_lora_ssot import load

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
        self.assertIn("PIN_PD0", outputs["src/arq/board_ssot.c"])
        self.assertIn("SPI1_SWAP_DEFAULT", outputs["include/generated/board_ssot.h"])
        self.assertNotIn("SPI1_SWAP_DEFAULT", outputs["src/arq/board_ssot.c"])
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
        self.assertEqual(event["s"], "12345678")
        self.assertEqual(parse_event("A t=1 e=BOOT s=0")["s"], "0")
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

            events = [dict(parse_event(line), role=r, host_ns=1) for r in ("sender", "receiver")]
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
            dict(role="sender", e="STATUS", s="0"),
            dict(role="sender", e="STATUS_END", s="0", v="0"),
        ]
        self.assertFalse(status_complete(events, "sender", 1))
        events.append(dict(role="sender", e="STATUS", s="1"))
        events.append(dict(role="sender", e="STATUS_END", s="1", v="1"))
        self.assertFalse(status_complete(events, "sender", 1))
        events.append(dict(role="sender", e="STATUS_END", s="1", v="0"))
        self.assertTrue(status_complete(events, "sender", 1))
        events.append(dict(role="sender", e="STATUS", s="1"))
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

    def test_application_bounds_include_arq(self) -> None:
        from tools.rf_proof import application_bounds_for_environment

        config = subprocess.check_output(
            ["pio", "project", "config", "--json-output"], cwd=ROOT, text=True
        )
        for role in ("sender", "receiver"):
            for suffix in ("", "_test"):
                self.assertEqual(
                    application_bounds_for_environment(config, role + "_arq" + suffix), (0, 130048)
                )


if __name__ == "__main__":
    unittest.main()
