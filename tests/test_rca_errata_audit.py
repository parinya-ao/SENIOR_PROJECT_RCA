"""Offline receiver-errata diagnostics; no device or RF interface."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.rca import errata_audit as audit


class ErrataDiagnosticsTests(unittest.TestCase):
    def test_real_driver_bw125_register_writes(self):
        root = Path(__file__).resolve().parents[1]
        lib = root / ".pio/libdeps/sender_arq/RadioLib/src"
        sources = [
            "Hal.cpp",
            "Module.cpp",
            "protocols/PhysicalLayer/PhysicalLayer.cpp",
            "modules/SX127x/SX127x.cpp",
            "modules/SX127x/SX1278.cpp",
            "modules/SX127x/SX1276.cpp",
            "utils/Utils.cpp",
        ]
        with tempfile.TemporaryDirectory() as directory:
            for enabled in (0, 1):
                executable = str(Path(directory) / str(enabled))
                subprocess.run(
                    [
                        "g++",
                        "-std=c++11",
                        "-ffunction-sections",
                        "-fdata-sections",
                        "-Wl,--gc-sections",
                        "-I" + str(lib),
                        "-DRADIOLIB_FIX_ERRATA_SX127X=" + str(enabled),
                        "tests/rca_errata_audit.cpp",
                        *[str(lib / f) for f in sources],
                        "-o",
                        executable,
                    ],
                    cwd=root,
                    check=True,
                    timeout=30,
                )
                result = subprocess.run(
                    [executable], check=True, capture_output=True, text=True, timeout=5
                )
                self.assertIn("PASS errata=" + str(enabled), result.stdout)
                # Optional destination is used only by offline verification runs.
                if os.environ.get("RCA_WRITE_TRACE"):
                    (
                        Path(os.environ["RCA_WRITE_TRACE"]) / f"driver-writes-{enabled}.log"
                    ).write_text(result.stdout)

    def test_first_valid_packet_can_have_zero_hardware_count(self):
        result = audit.interpret_rx(0x50, 0, crc_present=True)
        self.assertEqual(result["valid_packet_increment"], 1)
        self.assertFalse(result["zero_counter_proves_no_reception"])

    def test_crc_failure_is_not_a_valid_packet(self):
        result = audit.interpret_rx(0x70, 0, crc_present=True)
        self.assertTrue(result["crc_error"])
        self.assertEqual(result["valid_packet_increment"], 0)

    def test_missing_irq_remains_unknown(self):
        result = audit.interpret_rx(None, None)
        self.assertIsNone(result["rx_done"])
        self.assertIsNone(result["valid_packet_increment"])
        self.assertIsNone(result["hardware_packets"])

    def test_crc_absence_is_not_crc_success(self):
        self.assertIsNone(audit.interpret_rx(0x40, 0)["valid_packet_increment"])
        self.assertEqual(
            audit.interpret_rx(0x40, 0, crc_present=False)["valid_packet_increment"], 0
        )

    def test_no_rx_done_does_not_count_a_packet(self):
        result = audit.interpret_rx(0x90, 0, crc_present=True)
        self.assertTrue(result["valid_header"])
        self.assertTrue(result["rx_timeout_irq"])
        self.assertEqual(result["valid_packet_increment"], 0)

    def test_reject_malformed_register_input(self):
        for flags, packets in ((-1, 0), (256, 0), (True, 0), (0, -1), (0, 65536)):
            with self.subTest(flags=flags, packets=packets):
                with self.assertRaises(ValueError):
                    audit.interpret_rx(flags, packets)

    def test_active_snapshot_keeps_missing_if_registers_unknown(self):
        result = audit.decode_snapshot("128DE4C000F084727404000812271D00000023C30A0009")
        self.assertEqual(result["31"], 0xC3)
        self.assertEqual(result["01"], 0x8D)
        self.assertIsNone(result["2F"])
        self.assertIsNone(result["30"])
        self.assertIsNone(result["0B"])

    def test_missing_snapshot_is_not_filled_with_defaults(self):
        self.assertTrue(all(value is None for value in audit.decode_snapshot(None).values()))
        with self.assertRaises(ValueError):
            audit.decode_snapshot("00")

    def test_link_budget_is_conditional_on_two_dbm(self):
        result = audit.link_budget(915e6, 1, 2, -107)
        self.assertAlmostEqual(result["fspl_db"], 31.676, places=2)
        self.assertAlmostEqual(result["ideal_rx_dbm"], -29.676, places=2)
        self.assertAlmostEqual(result["conditional_difference_db"], 77.324, places=2)
        self.assertIsNone(result["measured_path_loss_db"])

    def test_link_budget_rejects_invalid_physics_input(self):
        for frequency, distance in ((0, 1), (915e6, 0), (float("nan"), 1)):
            with self.assertRaises(ValueError):
                audit.link_budget(frequency, distance, 2, -107)
