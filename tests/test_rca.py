"""Offline RCA contracts; fixtures never contact devices."""

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.rca import analyze as r

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts/arq/20261113T121506Z-reverse-raw"
B = ROOT / "artifacts/arq/20261113T123620Z-reverse-raw"


class RCATests(unittest.TestCase):
    def test_installed_driver_errata_switch(self) -> None:
        lib = ROOT / ".pio/libdeps/sender_arq/RadioLib/src"
        sources = [
            "Hal.cpp",
            "Module.cpp",
            "protocols/PhysicalLayer/PhysicalLayer.cpp",
            "modules/SX127x/SX127x.cpp",
            "modules/SX127x/SX1278.cpp",
            "modules/SX127x/SX1276.cpp",
            "utils/Utils.cpp",
        ]
        with tempfile.TemporaryDirectory() as d:
            for enabled in (0, 1):
                exe = str(Path(d) / str(enabled))
                subprocess.run(
                    [
                        "g++",
                        "-std=c++17",
                        "-ffunction-sections",
                        "-fdata-sections",
                        "-Wl,--gc-sections",
                        "-I" + str(lib),
                        "-DRADIOLIB_FIX_ERRATA_SX127X=" + str(enabled),
                        "tests/rca_errata_test.cpp",
                        *[str(lib / f) for f in sources],
                        "-o",
                        exe,
                    ],
                    cwd=ROOT,
                    check=True,
                    timeout=30,
                )
                subprocess.run([exe], check=True, timeout=10)

    def test_fake_radio_send_path_without_hardware(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            exe = str(Path(d) / "send")
            subprocess.run(
                [
                    "clang",
                    "--driver-mode=g++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-Wno-unused-function",
                    "-Wno-unused-variable",
                    "-Itests/arq/stub",
                    "-Itests/raw_mvp_stub",
                    "-Iinclude",
                    "-Istable_lib/arq",
                    "-DLORA_ROLE_RECEIVER",
                    '-DLORA_BUILD_ID="offline-rca"',
                    "tests/rca_send_test.cpp",
                    "-o",
                    exe,
                ],
                cwd=ROOT,
                check=True,
                timeout=30,
            )
            for case in ("partial", "wrong", "overflow", "backpressure"):
                subprocess.run([exe, case], check=True, timeout=5)

    def test_t01_negative_rf(self) -> None:
        self.assertEqual(r.analyze(A)["classification"], "PHYSICAL_RF_FAILURE_UNISOLATED")

    def test_t02_transport_inconclusive(self) -> None:
        self.assertEqual(r.analyze(B)["rf_verdict"], "INCONCLUSIVE")

    def test_t03_send_is_not_tx(self) -> None:
        self.assertIsNone(r.analyze(B)["tx_started"])

    def test_t04_txdone_not_radiation(self) -> None:
        self.assertIsNone(r.analyze(A)["radiated_rf"])

    def test_t05_missing_not_zero(self) -> None:
        self.assertIsNone(r.analyze(B)["received_packet_count"])

    def test_t06_cross_mcu_clock_rejected(self) -> None:
        with self.assertRaises(ValueError):
            r.delta({"role": "sender", "t": "2"}, {"role": "receiver", "t": "1"}, clock="mcu")

    def test_t07_host_delta(self) -> None:
        self.assertEqual(
            r.delta({"host_ns": 103525089152263}, {"host_ns": 103525089015341}), 136922
        )

    def test_t08_source_and_image_hashes(self) -> None:
        self.assertEqual(r.analyze(B)["evidence_integrity"], "PASS")
        self.assertTrue(r.analyze(B)["identity_checks"])

    def fixture(self) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name)
        (p / "a").write_bytes(b"x")
        (p / "bundle.json").write_text(
            json.dumps(
                {
                    "events": [],
                    "commands": [],
                    "firmware": {},
                    "files": {"a": hashlib.sha256(b"x").hexdigest()},
                }
            )
        )
        return p

    def test_t09_missing_file(self) -> None:
        p = self.fixture()
        (p / "a").unlink()
        self.assertEqual(r.analyze(p)["evidence_integrity"], "FAIL")

    def test_t10_corrupt_journal(self) -> None:
        p = self.fixture()
        b = json.loads((p / "bundle.json").read_text())
        b["events"] = [{"e": "RAW_TX"}]
        (p / "bundle.json").write_text(json.dumps(b))
        self.assertEqual(r.analyze(p)["classification"], "EVIDENCE_CORRUPTED")

    def test_t11_exception_preserved(self) -> None:
        s = "UPDI response mismatch: expected None, received b''\n"
        self.assertEqual(r.parse_updi(s)["message"], s)

    def test_t12_raw_bytes(self) -> None:
        self.assertEqual(
            r.parse_updi("UPDI response mismatch: expected b'@', received b'\\x00'")[
                "response_hex"
            ],
            "00",
        )

    def test_t13_empty_vs_unexpected(self) -> None:
        self.assertEqual(
            r.parse_updi("UPDI response mismatch: expected None, received b''")["response_length"],
            0,
        )
        self.assertEqual(
            r.parse_updi("UPDI response mismatch: expected None, received b")["response_hex"], None
        )

    def test_t14_no_inferred_usb_disconnect(self) -> None:
        self.assertIsNone(r.analyze(B)["usb_disconnected"])

    def test_t15_no_inferred_brownout(self) -> None:
        self.assertIsNone(r.analyze(B)["reset_during_send"])

    def test_t16_restore_not_reset_evidence(self) -> None:
        result = r.analyze(ROOT / "artifacts/arq/20261113T123837Z-standby")
        self.assertIsNone(result["reset_during_send"])

    def test_t17_missing_tx_snapshot(self) -> None:
        self.assertEqual(
            r.compare_snapshots("128DE4C000F084727404000812271D00000023C30A0009", None)["status"],
            "NOT CAPTURED",
        )

    def test_t18_mode_difference(self) -> None:
        rx = "128DE4C000F084727404000812271D00000023C30A0009"
        tx = rx[:2] + "8B" + rx[4:]
        self.assertEqual(r.compare_snapshots(rx, tx)["registers"]["01"], "EXPECTED DIFFERENCE")

    def test_t19_integrity_not_completeness(self) -> None:
        x = r.analyze(B)
        self.assertEqual(
            (x["evidence_integrity"], x["evidence_completeness"]), ("PASS", "INCOMPLETE")
        )

    def test_t20_no_unjustified_root_cause(self) -> None:
        self.assertEqual(r.analyze(B)["root_cause"], "UNKNOWN")

    def test_t21_repeatable_json(self) -> None:
        self.assertEqual(
            json.dumps(r.analyze(B), sort_keys=True), json.dumps(r.analyze(B), sort_keys=True)
        )

    def test_t22_immutable(self) -> None:
        before = {str(p): p.read_bytes() for p in B.rglob("*") if p.is_file()}
        r.analyze(B)
        self.assertTrue(all(Path(p).read_bytes() == v for p, v in before.items()))

    def test_t23_untrusted_paths(self) -> None:
        p = self.fixture()
        b = json.loads((p / "bundle.json").read_text())
        b["files"] = {"../escape": "0" * 64}
        (p / "bundle.json").write_text(json.dumps(b))
        self.assertEqual(r.analyze(p)["evidence_integrity"], "FAIL")

    def test_t24_no_hardware_cli(self) -> None:
        with self.assertRaises(SystemExit):
            r.main(["--flash"])

    def test_modified_file(self) -> None:
        p = self.fixture()
        (p / "a").write_bytes(b"y")
        self.assertEqual(r.analyze(p)["classification"], "EVIDENCE_CORRUPTED")

    def test_supplemental_integrity_manifest(self) -> None:
        p = self.fixture()
        (p / "extra").write_bytes(b"changed")
        (p / "integrity-sha256.json").write_text(
            json.dumps({"extra": hashlib.sha256(b"original").hexdigest()})
        )
        self.assertIn("hash mismatch: extra", r.analyze(p)["integrity_problems"])

    def test_overflow_incomplete(self) -> None:
        b = json.loads((A / "bundle.json").read_text())
        b["events"][0]["overflow"] = "1"
        self.assertEqual(
            r.classify(b["events"], transport_error=False, integrity=True)["rf_verdict"],
            "INCONCLUSIVE",
        )

    def test_partial_delayed_echo(self) -> None:
        for s, expected in [
            ("UPDI response mismatch: expected None, received b'\\x55'", 1),
            ("UPDI echo mismatch", None),
        ]:
            self.assertEqual(r.parse_updi(s)["response_length"], expected)

    def test_malformed_json(self) -> None:
        p = self.fixture()
        (p / "bundle.json").write_text("[]")
        self.assertEqual(r.analyze(p)["classification"], "EVIDENCE_CORRUPTED")
