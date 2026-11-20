"""Offline RCA contracts; fixtures never contact devices."""

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.rca import analyze as r

ROOT = Path(__file__).resolve().parents[1]


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
        """Classify a transmission with no radio reception as an RF failure."""
        evidence = self.evidence_bundle(negative=True)
        self.assertEqual(r.analyze(evidence)["classification"], "PHYSICAL_RF_FAILURE_UNISOLATED")

    def test_t02_transport_inconclusive(self) -> None:
        """Keep a transaction inconclusive when complete radio evidence is absent."""
        self.assertEqual(r.analyze(self.evidence_bundle())["rf_verdict"], "INCONCLUSIVE")

    def test_t03_send_is_not_tx(self) -> None:
        """Distinguish a host send request from observed radio transmission."""
        self.assertIsNone(r.analyze(self.evidence_bundle())["tx_started"])

    def test_t04_txdone_not_radiation(self) -> None:
        """Avoid inferring radiation from a TX completion event alone."""
        self.assertIsNone(r.analyze(self.evidence_bundle(negative=True))["radiated_rf"])

    def test_t05_missing_not_zero(self) -> None:
        """Represent a missing receiver count as unknown rather than zero."""
        self.assertIsNone(r.analyze(self.evidence_bundle())["received_packet_count"])

    def test_t06_cross_mcu_clock_rejected(self) -> None:
        with self.assertRaises(ValueError):
            r.delta({"role": "sender", "t": "2"}, {"role": "receiver", "t": "1"}, clock="mcu")

    def test_t07_host_delta(self) -> None:
        self.assertEqual(
            r.delta({"host_ns": 103525089152263}, {"host_ns": 103525089015341}), 136922
        )

    def test_t08_source_and_image_hashes(self) -> None:
        """Verify source snapshots and firmware images against their manifests."""
        result = r.analyze(self.evidence_bundle())
        self.assertEqual(result["evidence_integrity"], "PASS")
        self.assertEqual(len(result["identity_checks"]), 2)

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

    def evidence_bundle(
        self, *, negative: bool = False, overflow: bool = False, standby: bool = False
    ) -> Path:
        """Create deterministic evidence with matching image, source, and log hashes."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        config_id = hashlib.sha256(b"fixture-config").hexdigest()
        build_ids = {"sender": "fixture-sender", "receiver": "fixture-receiver"}
        events: list[dict[str, object]] = []
        for index, (role, build_id) in enumerate(build_ids.items(), 1):
            events.append(
                {
                    "t": str(index),
                    "e": "IDENTITY",
                    "s": "00000001",
                    "build": build_id,
                    "config": config_id,
                    "role": role,
                    "host_ns": index,
                }
            )
        if negative:
            rx_ready: dict[str, object] = {
                "t": "0",
                "e": "RAW_RX_READY",
                "s": "00000001",
                "rc": "0",
                "role": "sender",
                "host_ns": 3,
            }
            if overflow:
                rx_ready["overflow"] = "1"
            events.extend(
                [
                    rx_ready,
                    {
                        "t": "1",
                        "e": "RAW_TX",
                        "s": "00000001",
                        "rc": "0",
                        "flags": "11",
                        "role": "receiver",
                        "host_ns": 4,
                    },
                    {
                        "t": "2",
                        "e": "RAW_TX_DONE",
                        "s": "00000001",
                        "rc": "0",
                        "flags": "8",
                        "role": "receiver",
                        "host_ns": 5,
                    },
                    {
                        "t": "100000000000",
                        "e": "RAW_RX_TIMEOUT",
                        "s": "00000001",
                        "role": "sender",
                        "host_ns": 6,
                    },
                ]
            )

        contents: dict[str, bytes] = {}
        for role in ("sender", "receiver"):
            role_events = [event for event in events if event["role"] == role]
            lines = [
                "A "
                + " ".join(
                    f"{key}={value}"
                    for key, value in event.items()
                    if key not in ("role", "host_ns")
                )
                for event in role_events
            ]
            contents[f"rf-monitor-{role}.stdout.log"] = (
                "\n".join(lines) + ("\n" if lines else "")
            ).encode()
            contents[f"rf-monitor-{role}.stderr.log"] = b""

        firmware_hashes = {}
        for role, build_id in build_ids.items():
            payload = build_id.encode()
            record = bytes((len(payload), 0, 0, 0)) + payload
            checksum = (-sum(record)) & 0xFF
            image = (":" + (record + bytes((checksum,))).hex().upper() + "\n:00000001FF\n").encode()
            image_name = f"{role}_{'arq' if standby else 'reverse_raw'}.hex"
            contents[image_name] = image
            firmware_hashes[role] = hashlib.sha256(image).hexdigest()

        source_files = {
            "sender/main.cpp": b"// deterministic sender source snapshot\n",
            "receiver/main.cpp": b"// deterministic receiver source snapshot\n",
        }
        source_hashes = {}
        for name, data in source_files.items():
            contents[f"source/{name}"] = data
            source_hashes[name] = hashlib.sha256(data).hexdigest()
        contents["source-hashes.json"] = json.dumps(source_hashes, sort_keys=True).encode()
        if standby:
            contents["status.json"] = json.dumps(events, sort_keys=True).encode()

        file_hashes = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
        if standby:
            contents["integrity-sha256.json"] = json.dumps(file_hashes, sort_keys=True).encode()
            standby_metadata = {"firmware": firmware_hashes}
            (directory / "standby-verified.json").write_text(
                json.dumps(standby_metadata, sort_keys=True)
            )
        else:
            firmware = {
                role: {"sha256": firmware_hashes[role], "build_id": build_id}
                for role, build_id in build_ids.items()
            }
            bundle_metadata = {
                "events": events,
                "commands": [],
                "firmware": firmware,
                "files": file_hashes,
            }
            (directory / "bundle.json").write_text(json.dumps(bundle_metadata, sort_keys=True))

        for name, data in contents.items():
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return directory

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
        """Do not infer a USB disconnect from unrelated incomplete evidence."""
        self.assertIsNone(r.analyze(self.evidence_bundle())["usb_disconnected"])

    def test_t15_no_inferred_brownout(self) -> None:
        """Do not infer a brownout from the absence of reset evidence."""
        self.assertIsNone(r.analyze(self.evidence_bundle())["reset_during_send"])

    def test_t16_restore_not_reset_evidence(self) -> None:
        """Keep a post-restore snapshot separate from reset-during-send evidence."""
        result = r.analyze(self.evidence_bundle(standby=True))
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
        """Report valid hashes and incomplete radio evidence as separate states."""
        x = r.analyze(self.evidence_bundle())
        self.assertEqual(
            (x["evidence_integrity"], x["evidence_completeness"]), ("PASS", "INCOMPLETE")
        )

    def test_t20_no_unjustified_root_cause(self) -> None:
        """Leave root cause unknown when the archived evidence cannot prove it."""
        self.assertEqual(r.analyze(self.evidence_bundle())["root_cause"], "UNKNOWN")

    def test_t21_repeatable_json(self) -> None:
        """Return stable JSON for repeated analysis of one evidence bundle."""
        evidence = self.evidence_bundle()
        self.assertEqual(
            json.dumps(r.analyze(evidence), sort_keys=True),
            json.dumps(r.analyze(evidence), sort_keys=True),
        )

    def test_t22_immutable(self) -> None:
        """Analyze a bundle without modifying its archived files."""
        evidence = self.evidence_bundle()
        before = {str(p): p.read_bytes() for p in evidence.rglob("*") if p.is_file()}
        r.analyze(evidence)
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
        """Mark an otherwise valid event sequence incomplete after log overflow."""
        evidence = self.evidence_bundle(negative=True, overflow=True)
        b = json.loads((evidence / "bundle.json").read_text())
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
