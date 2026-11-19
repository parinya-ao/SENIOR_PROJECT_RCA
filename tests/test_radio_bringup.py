"""Operation gates and physical snapshot validation for the one-packet lab diagnostic."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

from tools import arq_trial as trial
from tools import rf_proof as rf


class RadioBringupTests(unittest.TestCase):
    @staticmethod
    def snapshot(mode: Any = 0x85) -> Any:
        return {
            "e": "REG",
            "bytes": bytes(
                [
                    mode,
                    0xE4,
                    0xC0,
                    0,
                    0xF0,
                    0x84,
                    0x72,
                    0x74,
                    4,
                    0x12,
                    0x27,
                    0x1D,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0x10,
                    0x43,
                    0x12,
                    0,
                    8,
                    0,
                ]
            ).hex(),
        }

    def test_phy_validates_every_selected_field(self) -> None:
        self.assertEqual(
            trial.audit_radio_configuration(self.snapshot(), rx=True)["frequency_hz"], 915000000
        )
        for index in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 16, 17, 19, 20, 21, 22, 23):
            with self.subTest(index=index):
                event = self.snapshot()
                data = bytearray.fromhex(event["bytes"])
                data[index] = 0 if index == 20 else data[index] ^ (0x80 if index == 19 else 1)
                event["bytes"] = data.hex()
                with self.assertRaises(ValueError):
                    trial.audit_radio_configuration(event, rx=True)
        event = self.snapshot(0x8D)
        with self.assertRaises(ValueError):
            trial.audit_radio_configuration(event, rx=True)
        with self.assertRaises(ValueError):
            trial.audit_radio_configuration({"bytes": "85"}, rx=True)

    def test_deadline_checked_before_rf(self) -> None:
        from tools.config.arq_config import load_arq

        config = load_arq()
        budget = trial.hello_airtime_budget(config)
        self.assertEqual(budget["payload_hex"], "48454c4c4f5f4c4f5241")
        self.assertEqual(budget["max_attempts"], 1)
        config = dict(config, ack_min_ms=1)
        with self.assertRaises(ValueError):
            trial.hello_airtime_budget(config)

    def test_bringup_cli_uses_only_programming_gate(self) -> None:
        with (
            patch(
                "sys.argv",
                [
                    "arq_trial",
                    "--radio-only-bringup",
                    "--physical-mapping-verified",
                    "--power-verified",
                ],
            ),
            patch.object(trial, "radio_only_bringup") as run,
        ):
            trial.main()
        run.assert_called_once()

    def test_hello_cli_requires_rf_release_after_programming_readiness(self) -> None:
        with (
            patch(
                "sys.argv",
                ["arq_trial", "--hello-lora", "--physical-mapping-verified", "--power-verified"],
            ),
            patch.object(trial, "radio_only_bringup") as run,
            self.assertRaises(SystemExit),
        ):
            trial.main()
        run.assert_not_called()

    def test_bringup_cli_blocks_missing_power_before_hardware(self) -> None:
        with (
            patch("sys.argv", ["arq_trial", "--radio-only-bringup"]),
            patch.object(trial, "radio_only_bringup") as run,
            self.assertRaises(SystemExit),
        ):
            trial.main()
        run.assert_not_called()

    @staticmethod
    def exchange_events() -> Any:
        data = "010101020700000000000A0048454C4C4F5F4C4F5241"
        ack = "010202010700000000000000"

        def event(role: Any, name: Any, **kw: Any) -> Any:
            return dict(role=role, e=name, s="7", q="0", rc="0", **kw)

        return [
            event("sender", "TX", bytes=data),
            event("sender", "TX_DONE", v="8"),
            event("receiver", "RX", bytes=data),
            event("receiver", "ACCEPT", v="1"),
            event("receiver", "TX", bytes=ack),
            event("receiver", "TX_DONE", v="8"),
            event("sender", "RX", bytes=ack),
            event("sender", "DELIVERED", v="1"),
        ]

    def test_exchange_requires_matching_data_ack_and_done(self) -> None:
        events = self.exchange_events()
        self.assertTrue(trial.validate_hello_exchange(events, 7)["complete"])
        for index, key in (
            (2, "tracker_data_rx"),
            (3, "tracker_data_accepted"),
            (5, "tracker_ack_tx_done"),
            (6, "gateway_ack_rx"),
            (7, "gateway_ack_accepted"),
        ):
            with self.subTest(index=index):
                result = trial.validate_hello_exchange(events[:index] + events[index + 1 :], 7)
                self.assertFalse(result["complete"])
                self.assertIsNone(result[key])
        wrong_sequence = copy.deepcopy(events)
        wrong_sequence[-1]["q"] = "1"
        self.assertFalse(trial.validate_hello_exchange(wrong_sequence, 7)["complete"])
        wrong = copy.deepcopy(events)
        wrong[6]["bytes"] = wrong[6]["bytes"].replace("07000000", "08000000")
        with self.assertRaises(ValueError):
            trial.validate_hello_exchange(wrong, 7)
        with self.assertRaises(ValueError):
            trial.validate_hello_exchange([events[0], *events], 7)

    def test_exchange_rejects_duplicate_frames_and_impossible_local_order(self) -> None:
        events = self.exchange_events()
        for index in (2, 4, 6):
            duplicate = copy.deepcopy(events)
            duplicate.insert(index, duplicate[index].copy())
            with self.subTest(duplicate=index):
                self.assertFalse(trial.validate_hello_exchange(duplicate, 7)["complete"])
        for left, right in ((0, 1), (6, 7), (2, 3), (4, 5)):
            reordered = copy.deepcopy(events)
            reordered[left], reordered[right] = reordered[right], reordered[left]
            with self.subTest(order=(left, right)):
                self.assertFalse(trial.validate_hello_exchange(reordered, 7)["complete"])
        # Independent serial streams may be drained in either order.
        grouped = [e for e in events if e["role"] == "receiver"] + [
            e for e in events if e["role"] == "sender"
        ]
        self.assertTrue(trial.validate_hello_exchange(grouped, 7)["complete"])

    def test_zero_transmit_bringup_programs_tracker_first_and_parks_without_reflash(self) -> None:
        self.check_bringup_cleanup(fail_rx=False)

    def test_partial_arm_failure_drains_stop_and_parks_each_actual_session(self) -> None:
        self.check_bringup_cleanup(fail_rx=True)

    def test_four_one_shots_select_images_rx_first_and_dispatch_one_exact_send(self) -> None:
        for test_id in ("T01", "T02", "T03", "T04"):
            with self.subTest(test_id=test_id):
                self.check_bringup_cleanup(fail_rx=False, test_id=test_id)

    def test_reverse_non_transmitting_bringup_has_no_send(self) -> None:
        self.check_bringup_cleanup(fail_rx=False, reverse=True)

    def check_bringup_cleanup(
        self, *, fail_rx: Any, test_id: Any = None, reverse: Any = False
    ) -> None:
        reverse = reverse or test_id in ("T03", "T04")
        suffix = "_reverse" if reverse else ""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "generated").mkdir()
            (root / "generated/arq_manifest.json").write_text(json.dumps({"config_hash": "config"}))
            from tools.config.generate_lora_config import digest
            from tools.receiver_boot import ihex

            for role in ("receiver", "sender"):
                env = role + "_arq_radio_only" + suffix
                build = root / ".pio/build" / env
                build.mkdir(parents=True)
                build_id = digest({"environment": env, "arq": {"config_hash": "config"}})
                (build / "firmware.hex").write_text(
                    ihex(b"\x0c\x94\x02\x00" + build_id.encode(), 0)
                )
                (build / "lora_build_identity.h").write_text(
                    '#define LORA_BUILD_ID "' + build_id + '"'
                )

            class Capture:
                def __init__(inner: Any, proof: Any) -> None:
                    inner.events: list[Any] = []
                    inner.commands: list[Any] = []
                    inner.errors: list[str] = []
                    inner.monitors: dict[str, Any] = {}
                    inner.mode = {"receiver": 0x81, "sender": 0x81}
                    inner.session = {"receiver": 0, "sender": 0}
                    inner.pending_stop = False

                def start(inner: Any) -> None:
                    inner.monitors = {"receiver": {}, "sender": {}}

                def acquire(inner: Any, *_: Any) -> None:
                    for role in inner.monitors:
                        inner.events.append(dict(self.snapshot(0x81), role=role, s="0"))

                def command(inner: Any, role: Any, text: Any) -> None:
                    inner.commands.append({"role": role, "text": text})
                    if text.startswith("ARM "):
                        inner.mode[role] = 0x8D if fail_rx else 0x85
                        inner.session[role] = int(text[4:], 16)
                        inner.events.append(
                            {"role": role, "e": "ARM", "s": f"{inner.session[role]:X}", "rc": "0"}
                        )
                    elif text == "X":
                        inner.mode[role] = 0x81
                        inner.pending_stop = True
                        inner.events.append(
                            {"role": role, "e": "STOP", "s": f"{inner.session[role]:X}", "rc": "0"}
                        )
                    elif text == "STATUS":
                        if inner.pending_stop:
                            msg = "STATUS before STOP drained overflows the 16-slot logger"
                            raise AssertionError(msg)
                        inner.events.extend(
                            [
                                {
                                    "role": role,
                                    "e": "STATUS",
                                    "s": f"{inner.session[role]:X}",
                                    "ready": "1",
                                    "overflow": "0",
                                },
                                dict(
                                    self.snapshot(inner.mode[role]),
                                    role=role,
                                    s=f"{inner.session[role]:X}",
                                ),
                                {
                                    "role": role,
                                    "e": "STATUS_END",
                                    "s": f"{inner.session[role]:X}",
                                    "v": "0",
                                },
                            ]
                        )
                    elif text.startswith("SEND "):
                        from tests.test_arq_directional import DirectionalHostTests

                        inner.events.extend(
                            DirectionalHostTests.events(test_id, inner.session[role])
                        )

                def wait(inner: Any, predicate: Any, *_: Any) -> None:
                    if not predicate():
                        msg = "capture predicate not met"
                        raise AssertionError(msg)
                    inner.pending_stop = False

                def seen(inner: Any, role: Any, name: Any) -> Any:
                    return [e for e in inner.events if e["role"] == role and e["e"] == name]

                def close(inner: Any) -> None:
                    pass

            args = SimpleNamespace(
                physical_mapping_verified=True,
                power_verified=True,
                rf_path_confirmed=True,
                rf_hardware_verified=True,
                authorize_rf_test=True,
                diagnostic_test=test_id,
                reverse_direction=reverse and test_id is None,
            )
            with (
                patch.object(trial, "ROOT", root),
                patch("generate_lora_config.generate"),
                patch.object(getattr(trial, "subprocess"), "check_output", return_value="config"),
                patch.object(getattr(trial, "rf"), "upload_ports_match", return_value=True),
                patch.object(
                    getattr(trial, "rf"), "upload_config_preserves_flash", return_value=True
                ),
                patch.object(getattr(trial, "rf"), "check_port_owners", return_value=[]),
                patch.object(getattr(trial, "rf"), "identify_targets", return_value=0),
                patch.object(
                    getattr(trial, "rf"), "program_application", return_value=0
                ) as program,
                patch.object(trial, "Capture", Capture),
                patch.object(trial, "prepare") as normal,
            ):
                if fail_rx:
                    with self.assertRaisesRegex(ValueError, "configuration mismatch"):
                        trial.radio_only_bringup(args)
                    run = next(path for path in (root / "artifacts/arq").iterdir() if path.is_dir())
                else:
                    run = trial.radio_only_bringup(args, exchange=bool(test_id))
            self.assertEqual(
                [call.args[1] for call in program.call_args_list],
                ["receiver_arq_radio_only" + suffix, "sender_arq_radio_only" + suffix],
            )
            normal.assert_not_called()
            report = json.loads((run / "bringup.json").read_text())
            self.assertEqual(report["status"], "UNKNOWN" if fail_rx else "PASS")
            self.assertEqual(report["cleanup"], {"receiver": "PARKED", "sender": "PARKED"})
            sends = [c for c in report["commands"] if c["text"].startswith("SEND")]
            if test_id:
                payload = (
                    b"REJECT_LORA"
                    if test_id in ("T02", "T04")
                    else (b"HELLO_LORA_TR" if reverse else b"HELLO_LORA_GW")
                )
                self.assertEqual(
                    sends,
                    [
                        {
                            "role": "receiver" if reverse else "sender",
                            "text": "SEND " + payload.hex().upper(),
                        }
                    ],
                )
                self.assertTrue(report["exchange"]["complete"])
                arms = [c["role"] for c in report["commands"] if c["text"].startswith("ARM ")]
                self.assertEqual(
                    arms, ["sender", "receiver"] if reverse else ["receiver", "sender"]
                )
            else:
                self.assertEqual(sends, [])

    def test_stale_candidate_is_rejected_before_programming(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "generated").mkdir()
            (root / "generated/arq_manifest.json").write_text(json.dumps({"config_hash": "config"}))
            build = root / ".pio/build/receiver_arq_radio_only"
            build.mkdir(parents=True)
            (build / "firmware.hex").write_text("stale")
            args = SimpleNamespace(physical_mapping_verified=True, power_verified=True)
            with (
                patch.object(trial, "ROOT", root),
                patch("generate_lora_config.generate"),
                patch.object(getattr(trial, "subprocess"), "check_output", return_value="config"),
                patch.object(getattr(trial, "rf"), "upload_ports_match", return_value=True),
                patch.object(
                    getattr(trial, "rf"), "upload_config_preserves_flash", return_value=True
                ),
                patch.object(getattr(trial, "rf"), "check_port_owners", return_value=[]),
                patch.object(getattr(trial, "rf"), "identify_targets", return_value=0),
                patch.object(trial, "reader_free_h01_firmware", return_value={"build_id": "stale"}),
                patch.object(
                    getattr(trial, "rf"),
                    "program_application",
                    side_effect=ValueError("programming reached"),
                ) as program,
                self.assertRaisesRegex(ValueError, "stale candidate"),
            ):
                trial.radio_only_bringup(args)
            program.assert_not_called()

    def test_live_image_verifier_accepts_current_tracker_and_rejects_other_device(self) -> None:
        from tools.receiver_boot import ihex

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            hardware = json.loads((rf.ROOT / "config/current_hardware.json").read_text())
            (root / "config/current_hardware.json").write_text(json.dumps(hardware))
            manifest = {
                "environments": {
                    env: {"build_id": "a" * 64} for env in ("sender_hello", "receiver")
                }
            }
            payload = b"\x0c\x94\x02\x00" + b"a" * 64
            for env in manifest["environments"]:
                build = root / ".pio/build" / env
                build.mkdir(parents=True)
                (build / "firmware.hex").write_text(ihex(payload, 0))
            proof: Any = SimpleNamespace(run_dir=root, note=Mock())
            wrong = False

            def command(name: Any, argv: Any, *_: Any) -> Any:
                role = "receiver" if name.startswith("receiver") else "gateway"
                memories = {
                    "signature": bytes.fromhex("1e970a"),
                    "sernum": bytes(16)
                    if wrong
                    else bytes.fromhex(hardware[role]["device_serial_hex"]),
                    "flash": payload + bytes(131072 - len(payload)),
                }
                for i, value in enumerate(argv):
                    if value == "-U":
                        memory, _, path, _ = argv[i + 1].split(":")
                        Path(path).write_bytes(memories[memory])
                return 0, b"", b""

            proof.command = command
            with (
                patch.object(rf, "ROOT", root),
                patch.object(rf, "application_bounds_for_environment", return_value=(0, 130048)),
            ):
                self.assertIsNotNone(rf.verify_installed_images(proof, "", manifest, "run"))
                wrong = True
                self.assertIsNone(rf.verify_installed_images(proof, "", manifest, "run"))


if __name__ == "__main__":
    unittest.main()
