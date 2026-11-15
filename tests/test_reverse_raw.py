import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ReverseRawTests(unittest.TestCase):
    def test_radio_profile_audit_accepts_the_915_mhz_arq_candidate(self):
        from tools.arq_trial import audit_raw_configuration

        values = bytes.fromhex("1281E4C000F084727404000812271D00000023C3000009")
        audit_raw_configuration(dict(bytes=values.hex()))

    def test_cleanup_parks_live_peer_when_other_monitor_has_exited(self):
        from unittest.mock import Mock

        from tools import arq_trial as a

        c = Mock()
        c.monitors = {"receiver": {}, "sender": {}}
        c.command.side_effect = [ValueError("monitor disconnected"), None]
        errors = a.park_reverse(c)
        self.assertEqual(
            c.command.call_args_list,
            [unittest.mock.call("receiver", "X"), unittest.mock.call("sender", "X")],
        )
        self.assertTrue(any("monitor disconnected" in e for e in errors))

    def test_radio_profile_audit_rejects_iq_modem_and_carrier_mismatch(self):
        from tools.arq_trial import audit_raw_configuration

        values = bytes.fromhex("1281E4C000F084727404000812271D00000023C3000009")
        for index in (2, 7, 8, 9, 10, 11, 12, 13, 14):
            altered = bytearray(values)
            altered[index] ^= 1
            with self.assertRaisesRegex(ValueError, "configuration"):
                audit_raw_configuration(dict(bytes=altered.hex()))
        audit_raw_configuration(dict(bytes=values.hex()))

    def test_send_waits_for_active_rx_and_retains_device_timeout(self):
        from types import SimpleNamespace

        from tools import arq_trial as a

        for mode in (0x85, 0x81):
            c = a.Capture(None)
            c.monitors = {
                r: {"process": SimpleNamespace(poll=lambda: None)} for r in ("sender", "receiver")
            }

            def command(role, text):
                c.commands.append(dict(role=role, text=text))
                rows = []
                if text == "RX":
                    rows = [
                        "A t=0 e=RAW_RX_ACTIVE s=0 bytes=1285E4C000F084727404000812271D00000023C3000009",
                        f"A t=0 e=RAW_RX_READY s=0 rc=0 mode={mode} overflow=0",
                    ]
                if text.startswith("SEND"):
                    self.assertTrue(c.seen("sender", "RAW_RX_READY"))
                    self.assertEqual(int(c.seen("sender", "RAW_RX_READY")[-1]["mode"]), 0x85)
                    rows = [
                        "A t=1 e=RAW_TX s=0 rc=0 flags=11",
                        "A t=2 e=RAW_TX_DONE s=0 rc=0 flags=8",
                    ]
                for row in rows:
                    c.queue.put((role, "stdout", row.encode()))
                if text.startswith("SEND"):
                    c.queue.put(
                        ("sender", "stdout", b"A t=15000 e=RAW_RX_TIMEOUT s=0 rc=0 flags=0")
                    )

            c.command = command
            with self.assertRaisesRegex(
                ValueError,
                "missing single actual raw reception" if mode == 0x85 else "RX continuous",
            ):
                a.reverse_exchange(c)
            self.assertEqual(bool(c.seen("sender", "RAW_RX_TIMEOUT")), mode == 0x85)
            self.assertEqual(any(x["text"].startswith("SEND") for x in c.commands), mode == 0x85)

    def test_expired_window_never_sends(self):
        from tools import arq_trial as a

        c = a.Capture(None)
        c.events = [dict(role="sender", e="RAW_RX_READY", rc="0", mode="133")]
        with (
            patch.object(c, "command") as command,
            patch.object(c, "wait"),
            patch.object(a.time, "monotonic", side_effect=[0, 11]),
        ):
            with self.assertRaisesRegex(ValueError, "window expired"):
                a.reverse_exchange(c)
        command.assert_called_once_with("sender", "RX")

    def test_rf_validation_requires_actual_matching_packet_and_txdone(self):
        from tools.arq_trial import validate_reverse

        events = [
            dict(role="receiver", e="RAW_TX", rc="0", flags="11", overflow="0"),
            dict(role="receiver", e="RAW_TX_DONE", rc="0", flags="8", overflow="0"),
            dict(
                role="sender",
                e="RAW_RX",
                rc="0",
                flags="64",
                len="11",
                match="1",
                bytes="48656C6C6F20576F726C64",
                rssi="-8350",
                snr="-125",
            ),
        ]
        self.assertTrue(validate_reverse(events)["complete"])
        for key, value in [("flags", "96"), ("bytes", "00"), ("rc", "-7"), ("match", "0")]:
            bad = [dict(e) for e in events]
            bad[-1][key] = value
            with self.assertRaises(ValueError):
                validate_reverse(bad)
        with self.assertRaises(ValueError):
            validate_reverse(events[1:])
        with self.assertRaises(ValueError):
            validate_reverse(events + [events[0]])

    def test_reverse_cli_requires_physical_gate(self):
        from tools import arq_trial

        with (
            patch.object(sys, "argv", ["arq_trial", "--reverse-raw"]),
            patch.object(arq_trial, "reverse_raw") as run,
        ):
            with self.assertRaises(SystemExit):
                arq_trial.main()
            run.assert_not_called()

    def test_command_gating_payload_crc_timeout_and_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            for role in ("SENDER", "RECEIVER"):
                binary = str(Path(d) / role)
                subprocess.run(
                    [
                        "clang",
                        "--driver-mode=g++",
                        "-std=c++11",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-Wno-unused-function",
                        "-Wno-unused-variable",
                        "-Itests/arq/stub",
                        "-Itests/raw_mvp_stub",
                        "-Iinclude",
                        "-DLORA_ROLE_" + role,
                        '-DLORA_BUILD_ID="host-test"',
                        "tests/reverse_raw_test.cpp",
                        "-o",
                        binary,
                    ],
                    cwd=ROOT,
                    check=True,
                )
                subprocess.run([binary], check=True)
                for case in (
                    ("rx-error", "timeout", "bad-length", "diagnostics")
                    if role == "SENDER"
                    else ("tx-error", "done")
                ):
                    subprocess.run([binary, case], check=True)

    def test_registered_target_bounds(self):
        from tools.rf_proof import application_bounds_for_environment

        config = subprocess.check_output(
            ["pio", "project", "config", "--json-output"], cwd=ROOT, text=True
        )
        for role in ("sender", "receiver"):
            self.assertEqual(
                application_bounds_for_environment(config, role + "_reverse_raw"), (0, 130048)
            )
