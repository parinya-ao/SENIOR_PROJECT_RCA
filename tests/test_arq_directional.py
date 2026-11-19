"""Both physical board roles run the same ARQ engine in either direction."""

import copy
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class DirectionalTests(unittest.TestCase):
    def test_adapter_ack_nack_and_expiry_in_both_directions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for reverse in (False, True):
                flags = ["-DARQ_RADIO_ONLY_DIAGNOSTIC=1"]
                if reverse:
                    flags.append("-DARQ_REVERSE_DIAGNOSTIC=1")
                objects = []
                for source in ("codec", "sender", "receiver"):
                    obj = str(Path(directory) / (source + str(reverse) + ".o"))
                    subprocess.run(
                        [
                            "clang",
                            "--driver-mode=g++",
                            "-std=c++17",
                            *flags,
                            "-Iinclude",
                            "-Istable_lib/arq",
                            "-c",
                            f"stable_lib/arq/{source}.cpp",
                            "-o",
                            obj,
                        ],
                        cwd=ROOT,
                        check=True,
                    )
                    objects.append(obj)
                for role in ("SENDER", "RECEIVER"):
                    binary = str(Path(directory) / (role + str(reverse)))
                    subprocess.run(
                        [
                            "g++",
                            "-std=c++17",
                            "-Wall",
                            "-Wextra",
                            "-Werror",
                            "-Wno-unused-variable",
                            "-Wno-unused-function",
                            "-Itests/arq/stub",
                            "-Itests/raw_mvp_stub",
                            "-Iinclude",
                            "-Istable_lib/arq",
                            "-DLORA_ROLE_" + role,
                            "-DARQ_TEST_MODE=1",
                            *flags,
                            '-DLORA_BUILD_ID="host-directional"',
                            "tests/arq/directional_test.cpp",
                            *objects,
                            "-o",
                            binary,
                        ],
                        cwd=ROOT,
                        check=True,
                    )
                    for case in ("ack", "nack", "expired"):
                        with self.subTest(reverse=reverse, role=role, case=case):
                            subprocess.run([binary, case], check=True)

    def test_reverse_images_keep_physical_board_bounds_and_errata(self) -> None:
        import json

        from tools import rf_proof

        config = subprocess.check_output(
            ["pio", "project", "config", "--json-output"], cwd=ROOT, text=True
        )
        sections = {s: dict(v) for s, v in json.loads(config)}
        for role in ("sender", "receiver"):
            env = role + "_arq_radio_only_reverse"
            self.assertEqual(rf_proof.application_bounds_for_environment(config, env), (0, 130048))
            self.assertIn("-DARQ_REVERSE_DIAGNOSTIC=1", sections["env:" + env]["build_flags"])
            self.assertIn("-DRADIOLIB_FIX_ERRATA_SX127X=1", sections["env:" + env]["build_flags"])


class DirectionalHostTests(unittest.TestCase):
    @staticmethod
    def events(test_id: str, session: int = 7) -> list[dict[str, Any]]:
        reverse = test_id in ("T03", "T04")
        nack = test_id in ("T02", "T04")
        tx, rx = ("receiver", "sender") if reverse else ("sender", "receiver")
        src, dst = (2, 1) if reverse else (1, 2)
        payload = b"REJECT_LORA" if nack else (b"HELLO_LORA_TR" if reverse else b"HELLO_LORA_GW")
        data = (
            struct.pack("<BBBBIHBB", 1, 1, src, dst, session, 0, len(payload), 0) + payload
        ).hex()
        response = struct.pack(
            "<BBBBIHBB", 1, 3 if nack else 2, dst, src, session, 0, 0, 2 if nack else 0
        ).hex()

        def row(role: str, name: str, **kw: Any) -> dict[str, Any]:
            return dict(role=role, e=name, s=f"{session:X}", q="0", rc="0", **kw)

        decision = row(rx, "DATA_REJECT", v="0") if nack else row(rx, "ACCEPT", v="1")
        if nack:
            decision["rc"] = "2"
        return [
            row(tx, "TX", bytes=data),
            row(tx, "TX_DONE", v="8"),
            row(rx, "RX", bytes=data),
            decision,
            row(rx, "TX", bytes=response),
            row(rx, "TX_DONE", v="8"),
            row(tx, "RX", bytes=response),
            row(tx, "REJECTED" if nack else "DELIVERED", v="1"),
        ]

    def test_four_matching_exchanges_require_every_checkpoint(self) -> None:
        from tools import arq_trial as trial

        for test_id in ("T01", "T02", "T03", "T04"):
            events = self.events(test_id)
            with self.subTest(test_id=test_id):
                self.assertTrue(
                    trial.validate_hello_exchange(events, 7, test_id=test_id)["complete"]
                )
                for i in range(len(events)):
                    result = trial.validate_hello_exchange(
                        events[:i] + events[i + 1 :], 7, test_id=test_id
                    )
                    self.assertFalse(result["complete"])
                for index in (0, 2, 4, 6):
                    bad = copy.deepcopy(events)
                    frame = bytearray.fromhex(bad[index]["bytes"])
                    frame[4] = 8
                    bad[index]["bytes"] = frame.hex()
                    with self.assertRaises(ValueError):
                        trial.validate_hello_exchange(bad, 7, test_id=test_id)
                with self.assertRaises(ValueError):
                    trial.validate_hello_exchange([*events, events[0]], 7, test_id=test_id)
                wrong = copy.deepcopy(events)
                frame = bytearray.fromhex(wrong[6]["bytes"])
                frame[11] = 1
                wrong[6]["bytes"] = frame.hex()
                with self.assertRaises(ValueError):
                    trial.validate_hello_exchange(wrong, 7, test_id=test_id)

    def test_each_rf_test_requires_actual_rf_release(self) -> None:
        from tools import arq_trial as trial

        for test_id in ("T01", "T02", "T03", "T04"):
            with (
                patch(
                    "sys.argv",
                    [
                        "arq_trial",
                        "--diagnostic-test",
                        test_id,
                        "--physical-mapping-verified",
                        "--power-verified",
                    ],
                ),
                patch.object(trial, "radio_only_bringup") as run,
            ):
                with self.assertRaises(SystemExit):
                    trial.main()
                run.assert_not_called()

    def test_authorized_test_dispatches_exactly_once(self) -> None:
        from tools import arq_trial as trial

        for test_id in ("T01", "T02", "T03", "T04"):
            with (
                patch(
                    "sys.argv",
                    [
                        "arq_trial",
                        "--diagnostic-test",
                        test_id,
                        "--physical-mapping-verified",
                        "--power-verified",
                        "--rf-path-confirmed",
                        "--rf-hardware-verified",
                        "--authorize-rf-test",
                    ],
                ),
                patch.object(trial, "radio_only_bringup") as run,
            ):
                trial.main()
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0].diagnostic_test, test_id)
                self.assertTrue(run.call_args.kwargs["exchange"])
