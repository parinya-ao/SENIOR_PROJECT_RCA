from pathlib import Path
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rf_proof
from rf_proof import hardware_blockers, parse_test_counts, unresolved_adapter_paths


def packet_event(role, name, campaign, sequence=None, attempt=None, rtt=None,
                 toa_us=None):
    fields = [f"C={campaign:04X}"]
    if sequence is not None:
        fields.append(f"S={sequence:02X}")
    if attempt is not None:
        fields.append(f"A={attempt}")
    if rtt is not None:
        fields.append(f"RTT={rtt}")
    if toa_us is not None:
        fields.append(f"TOA_US={toa_us}")
    return f"[{role}] {name} {' '.join(fields)}"


def payload_event(role, name, campaign, sequence, payload=b"hello world"):
    return (f"[{role}] {name} C={campaign:04X} S={sequence:02X} "
            f"LEN={len(payload)} HEX={payload.hex().upper()} "
            f"ASCII={payload.decode('ascii')}")


def complete_campaign_logs(campaign=0x1234, stop_after_preflight=False,
                           omit_final_ack=False):
    gateway = [
        "[GATEWAY] BOOT sender_hello Nov  6 2026 00:00:00",
        payload_event("GATEWAY", "DATA_PAYLOAD", campaign, 1),
        packet_event("GATEWAY", "DATA_TX", campaign, 1, 1, toa_us=1200000),
        packet_event("GATEWAY", "DATA_DONE", campaign, 1, 1),
    ]
    receiver = [
        "[RECEIVER] BOOT receiver Nov  6 2026 00:00:01",
        payload_event("RECEIVER", "PAYLOAD_BYTES", campaign, 1),
        packet_event("RECEIVER", "PAYLOAD_MATCH", campaign, 1),
        packet_event("RECEIVER", "DATA_RX", campaign, 1),
        packet_event("RECEIVER", "ACK_TX", campaign, 1, toa_us=800000),
        packet_event("RECEIVER", "ACK_DONE", campaign, 1),
    ]
    gateway.extend([
        packet_event("GATEWAY", "ACK_RX", campaign, 1, rtt=51),
        packet_event("GATEWAY", "PREFLIGHT_OK", campaign, 1),
    ])
    if stop_after_preflight:
        return "\n".join(gateway), "\n".join(receiver)

    gateway.append(packet_event("GATEWAY", "CAMPAIGN_CONTINUE", campaign))
    for sequence in range(2, 21):
        gateway.extend([
            packet_event("GATEWAY", "DATA_TX", campaign, sequence, 1,
                         toa_us=1200000),
            packet_event("GATEWAY", "DATA_DONE", campaign, sequence, 1),
        ])
        receiver.extend([
            packet_event("RECEIVER", "PAYLOAD_MATCH", campaign, sequence),
            packet_event("RECEIVER", "DATA_RX", campaign, sequence),
            packet_event("RECEIVER", "ACK_TX", campaign, sequence,
                         toa_us=800000),
            packet_event("RECEIVER", "ACK_DONE", campaign, sequence),
        ])
        if not (omit_final_ack and sequence == 20):
            gateway.append(packet_event(
                "GATEWAY", "ACK_RX", campaign, sequence,
                rtt=50 + sequence))
    gateway.append(packet_event("GATEWAY", "TEST_COMPLETED", campaign))
    return "\n".join(gateway), "\n".join(receiver)


def ihex_record(address, record_type, data):
    record = bytes([len(data), address >> 8, address & 0xff, record_type]) + data
    checksum = (-sum(record)) & 0xff
    return b":" + (record + bytes([checksum])).hex().upper().encode()


def effective_platformio_config(sender_flags=None, sender_hello_flags=None,
                                receiver_flags=None, sender_hello_spi_flags=None,
                                receiver_spi_flags=None, upload_flags=("-D",),
                                gateway_app_start="0x00000",
                                receiver_app_start="0x05800"):
    shared = [
        "-DAPPLICATION_BUILD", "-Isrc/shared",
        "-DHELLO_RF_FREQUENCY_MHZ=923.0f",
        "-DHELLO_RF_TX_POWER_DBM=10", "-DHELLO_RF_LONG_RANGE=0",
        "-DHELLO_RF_SPREADING_FACTOR=7", "-DHELLO_RF_BANDWIDTH_KHZ=125",
        "-DHELLO_RF_CODING_RATE=5", "-DHELLO_RF_SYNC_WORD=0x12",
        "-DHELLO_RF_PREAMBLE_SYMBOLS=8", "-DHELLO_RF_CRC_ENABLED=1",
        "-DHELLO_RF_IQ_INVERTED=0",
    ]
    sender_flags = list(sender_flags or shared)
    sender_hello_flags = list(sender_hello_flags or shared + ["-DHELLO_TEST_MODE=1"])
    receiver_flags = list(receiver_flags or shared)
    sender_hello_spi_flags = list(sender_hello_spi_flags or
                                  shared + ["-DHELLO_TEST_MODE=1",
                                            "-DHELLO_RF_DIAGNOSTIC_ONLY=1"])
    receiver_spi_flags = list(receiver_spi_flags or
                              shared + ["-DHELLO_RF_DIAGNOSTIC_ONLY=1"])

    def environment(flags, port, app_start):
        return [
            "build_flags", flags,
        ], [
            "board_build.text_section_start", app_start,
        ], [
            "upload_flags", list(upload_flags),
        ], [
            "upload_protocol", "serialupdi",
        ], [
            "upload_port", port,
        ]

    sender = environment(
        sender_flags,
        "/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0",
        gateway_app_start,
    )
    sender_hello = environment(
        sender_hello_flags,
        "/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0",
        gateway_app_start,
    )
    receiver = environment(
        receiver_flags,
        "/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0",
        receiver_app_start,
    )
    sender_hello_spi = environment(
        sender_hello_spi_flags,
        "/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0",
        gateway_app_start,
    )
    receiver_spi = environment(
        receiver_spi_flags,
        "/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0",
        receiver_app_start,
    )
    return json.dumps([
        ["target_layout", [
            ["gateway_bootsize", "0x00"],
            ["gateway_codesize", "0x00"],
            ["gateway_bodcfg", "0x00"],
            ["gateway_app_start", gateway_app_start],
            ["receiver_bootsize", "0x2C"],
            ["receiver_codesize", "0x00"],
            ["receiver_bodcfg", "0x54"],
            ["receiver_app_start", receiver_app_start],
        ]],
        ["flash_geometry", [
            ["total_bytes", "131072"],
            ["application_end", "0x1FC00"],
        ]],
        ["env:sender", list(sender)],
        ["env:sender_hello", list(sender_hello)],
        ["env:receiver", list(receiver)],
        ["env:sender_hello_spi", list(sender_hello_spi)],
        ["env:receiver_spi", list(receiver_spi)],
    ])


class TargetLayoutTests(unittest.TestCase):
    def test_target_layout_uses_live_per_board_fuses_and_application_boundaries(self):
        config = effective_platformio_config()

        self.assertEqual(rf_proof.target_fuses(config, "gateway"), {
            "bootsize": 0x00, "codesize": 0x00, "bodcfg": 0x00,
        })
        self.assertEqual(rf_proof.target_fuses(config, "receiver"), {
            "bootsize": 0x2C, "codesize": 0x00, "bodcfg": 0x54,
        })
        self.assertEqual(rf_proof.application_bounds_for_environment(
            config, "sender_hello"), (0x00000, 0x1FC00))
        self.assertEqual(rf_proof.application_bounds_for_environment(
            config, "receiver"), (0x05800, 0x1FC00))

    def test_receiver_image_must_start_at_the_live_boot_boundary(self):
        config = effective_platformio_config(receiver_app_start="0x04000")

        self.assertIsNone(rf_proof.application_bounds_for_environment(
            config, "receiver"))


class HardwareGateTests(unittest.TestCase):
    def test_campaign_build_skip_keeps_ready_gateway_on_normal_rx_path(self):
        source = (Path(__file__).resolve().parents[1] /
                  "src/sender/lib/lora_rx.cpp").read_text()
        boot_gate = source.index("if (test_campaign.state() == lora_hello::State::TEST_IDLE)")
        for decision in ("AlreadyRun", "ReadbackFailed"):
            marker = f"if (_campaign_build_gate_result ==\n                    CampaignBuildGateResult::{decision})"
            start = source.index(marker, boot_gate)
            end = source.index("\n                }", start)
            branch = source[start:end]
            self.assertIn("test_campaign.fail();", branch)
            self.assertIn("continue;", branch)
            self.assertNotIn("_started = false;", branch)

    def test_sender_and_receiver_lora_pins_match_board_revision_1(self):
        expected = {
            "CS": "PIN_PC3",
            "RST": "PIN_PD0",
            "IRQ": "PIN_PD2",
            "DIO1": "PIN_PD3",
        }
        root = Path(__file__).resolve().parents[1]
        sources = (
            root / "src/sender/lib/io.h",
            root / "src/receiver/main.cpp",
        )
        for path in sources:
            bindings = {}
            for line in path.read_text().splitlines():
                parts = line.split()
                if len(parts) == 3 and parts[:1] == ["#define"]:
                    name = parts[1].removeprefix("PIN_LORA_")
                    if name in expected:
                        bindings[name] = parts[2]
            self.assertEqual(bindings, expected, str(path))
        receiver = sources[1].read_text()
        self.assertNotIn("PIN_LORA_EN", receiver)

    def test_both_radio_setups_keep_dio1_input_and_reset_deasserted(self):
        root = Path(__file__).resolve().parents[1]
        sender = (root / "src/sender/lib/io.cpp").read_text()
        receiver = (root / "src/receiver/main.cpp").read_text()
        for path, source in (("sender", sender), ("receiver", receiver)):
            self.assertIn("pinModeFast(PIN_LORA_DIO1, INPUT);", source, path)
            self.assertIn("digitalWriteFast(PIN_LORA_RST, HIGH);", source, path)

    def test_led_and_debug_uart_macros_follow_schematic_and_dxcore_directions(self):
        root = Path(__file__).resolve().parents[1]
        expected_leds = {"PIN_LED1": "PIN_PA5", "PIN_LED2": "PIN_PA4"}
        for relative in ("src/sender/lib/io.h", "src/receiver/main.cpp"):
            source = (root / relative).read_text()
            bindings = {}
            for line in source.splitlines():
                parts = line.split()
                if len(parts) == 3 and parts[0] == "#define" and parts[1] in expected_leds:
                    bindings[parts[1]] = parts[2]
            self.assertEqual(bindings, expected_leds, relative)

        sender_io = (root / "src/sender/lib/io.h").read_text()
        self.assertIn("#define PIN_DEBUG_TX  PIN_PA0", sender_io)
        self.assertIn("#define PIN_DEBUG_RX  PIN_PA1", sender_io)

    def test_shared_rf_profile_is_the_sf7_bench_candidate(self):
        validator = getattr(rf_proof, "valid_rf_profile_config", None)
        self.assertTrue(callable(validator), "shared RF profile validation is required")
        config = """[env]
build_flags =
    -DAPPLICATION_BUILD
    -DHELLO_RF_FREQUENCY_MHZ=923.0f
    -DHELLO_RF_TX_POWER_DBM=10
    -DHELLO_RF_LONG_RANGE=0
    -DHELLO_RF_SPREADING_FACTOR=7
    -DHELLO_RF_BANDWIDTH_KHZ=125
    -DHELLO_RF_CODING_RATE=5
    -DHELLO_RF_SYNC_WORD=0x12
    -DHELLO_RF_PREAMBLE_SYMBOLS=8
    -DHELLO_RF_CRC_ENABLED=1
    -DHELLO_RF_IQ_INVERTED=0

[env:sender]

[env:sender_hello]
build_flags =
    ${env.build_flags}
    -DHELLO_TEST_MODE=1

[env:receiver]
"""
        self.assertTrue(validator(config))
        self.assertEqual(rf_proof.shared_rf_profile(config), {
            "frequency_mhz": 923.0,
            "tx_power_dbm": 10,
            "long_range": 0,
            "spreading_factor": 7,
            "bandwidth_khz": 125,
            "coding_rate": 5,
            "sync_word": 0x12,
            "preamble_symbols": 8,
            "crc_enabled": 1,
            "iq_inverted": 0,
        })
        self.assertFalse(validator(config.replace(
            "[env:receiver]", "[env:receiver]\nbuild_flags =\n"
            "    -DHELLO_RF_LONG_RANGE=1")))

    def test_spi_diagnostic_environments_are_separate_and_rf_disabled(self):
        disabled = effective_platformio_config()
        checker = getattr(rf_proof, "rf_spi_diagnostic_config", None)
        self.assertTrue(callable(checker), "dedicated RF-disabled SPI config check is required")
        self.assertTrue(checker(disabled))
        self.assertFalse(checker(effective_platformio_config(
            sender_hello_spi_flags=["-DHELLO_TEST_MODE=1"])))
        self.assertFalse(checker(effective_platformio_config(
            receiver_spi_flags=["-DAPPLICATION_BUILD"])))
        self.assertFalse(checker(effective_platformio_config(
            sender_hello_flags=["-DHELLO_TEST_MODE=1",
                                "-DHELLO_RF_DIAGNOSTIC_ONLY=1"])))

    def test_effective_profile_validator_rejects_role_specific_overrides(self):
        validator = getattr(rf_proof, "valid_rf_profile_config", None)
        self.assertTrue(callable(validator))
        profile = effective_platformio_config()
        self.assertEqual(rf_proof.shared_rf_profile(profile)["frequency_mhz"], 923.0)
        changed_receiver = profile.replace(
            '"-DHELLO_RF_LONG_RANGE=0"', '"-DHELLO_RF_LONG_RANGE=1"')
        self.assertFalse(validator(changed_receiver))
        self.assertFalse(validator(effective_platformio_config(
            sender_hello_flags=["-DHELLO_TEST_MODE=1",
                                "-DHELLO_RF_FREQUENCY_MHZ=923.0f"])))

    def test_wrapper_host_compile_uses_effective_platformio_profile(self):
        flags = rf_proof.radio_profile_compile_flags(
            effective_platformio_config())
        self.assertEqual(flags, [
            "-DHELLO_RF_FREQUENCY_MHZ=923.0f",
            "-DHELLO_RF_TX_POWER_DBM=10",
            "-DHELLO_RF_LONG_RANGE=0",
            "-DHELLO_RF_SPREADING_FACTOR=7",
            "-DHELLO_RF_BANDWIDTH_KHZ=125",
            "-DHELLO_RF_CODING_RATE=5",
            "-DHELLO_RF_SYNC_WORD=0x12",
            "-DHELLO_RF_PREAMBLE_SYMBOLS=8",
            "-DHELLO_RF_CRC_ENABLED=1",
            "-DHELLO_RF_IQ_INVERTED=0",
        ])

    def test_effective_upload_flags_and_ports_are_checked(self):
        config = effective_platformio_config()
        preserves = getattr(rf_proof, "upload_config_preserves_flash", None)
        ports_match = getattr(rf_proof, "upload_ports_match", None)
        self.assertTrue(callable(ports_match), "effective upload-port mapping check is required")
        self.assertTrue(preserves(config))
        self.assertTrue(ports_match(config))
        self.assertFalse(rf_proof.upload_config_preserves_flash(
            effective_platformio_config(upload_flags=("-D", "-e"))))
        self.assertFalse(rf_proof.upload_config_preserves_flash(
            effective_platformio_config(upload_flags=("-D", "-U", "fuse:w:0x00:m"))))
        self.assertFalse(ports_match(effective_platformio_config().replace(
            "/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0",
            "/dev/ttyUSB0")))

    def test_rf_enabled_upload_programs_receiver_before_boot_campaign_sender(self):
        class RecordingProof:
            def __init__(self):
                self.commands = []
                self.notes = []

            def command(self, name, argv, *args, **kwargs):
                self.commands.append((name, argv))
                return 0, b"", b""

            def note(self, _name, message):
                self.notes.append(message)

        proof = RecordingProof()
        args = SimpleNamespace(
            boot_layout_verified=True,
            target_identification_attempted=True,
            physical_mapping_verified=True,
            power_verified=True,
            authorize_upload=True,
            authorize_rf_test=True,
        )
        with patch.object(rf_proof, "application_layout_verified", return_value=True), \
                patch.object(rf_proof, "upload_config_preserves_flash", return_value=True), \
                patch.object(rf_proof, "upload_ports_match", return_value=True), \
                patch.object(rf_proof, "check_port_owners", return_value=[]):
            self.assertEqual(rf_proof.upload(proof, args, True, "effective"), 0)
        self.assertEqual([name for name, _ in proof.commands], [
            "receiver-upload", "sender_hello-upload",
        ])

    def test_rf_enabled_upload_requires_campaign_authorization(self):
        class Proof:
            commands = []
            notes = []

            def command(self, *args, **kwargs):
                self.commands.append((args, kwargs))
                return 0, b"", b""

            def note(self, _name, message):
                self.notes.append(message)

        proof = Proof()
        args = SimpleNamespace(
            boot_layout_verified=True, target_identification_attempted=True,
            physical_mapping_verified=True, power_verified=True,
            authorize_upload=True, authorize_rf_test=False,
        )
        with patch.object(rf_proof, "application_layout_verified", return_value=True), \
                patch.object(rf_proof, "upload_config_preserves_flash", return_value=True), \
                patch.object(rf_proof, "upload_ports_match", return_value=True):
            self.assertEqual(rf_proof.upload(proof, args, True, "effective"), 2)
        self.assertEqual(proof.commands, [])
        self.assertIn("RF-test authorization", proof.notes[-1])

    def test_hardware_blockers_only_represent_physical_and_action_gates(self):
        self.assertEqual(hardware_blockers(
            "radio-spi-smoke", mapping_verified=True, power_verified=True,
            boot_layout_verified=True, authorized=True,
        ), [])
        self.assertEqual(hardware_blockers(
            "radio-spi-smoke", mapping_verified=False, power_verified=False,
            boot_layout_verified=False, authorized=False,
        ), ["physical board mapping", "power conditions",
            "BOOTSIZE/CODESIZE/BODCFG fuse verification", "upload authorization"])
        self.assertEqual(hardware_blockers(
            "upload", mapping_verified=True, power_verified=True,
            boot_layout_verified=True, authorized=True,
        ), [])

    def test_radio_spi_log_requires_version_and_diagnostic_only_marker(self):
        parser = getattr(rf_proof, "parse_radio_spi_log", None)
        self.assertTrue(callable(parser), "SPI smoke evidence parser is required")
        result = parser(
            "[GATEWAY] RADIO_SPI_VERSION=0x12\n"
            "[GATEWAY] RF_TX_DISABLED_DIAGNOSTIC\n",
            "GATEWAY",
        )
        self.assertEqual(result["version"], 0x12)
        self.assertTrue(result["tx_disabled"])
        self.assertTrue(result["passed"])
        self.assertFalse(parser(
            "[GATEWAY] RADIO_SPI_VERSION=0x12\n", "GATEWAY")["passed"])
        self.assertFalse(parser(
            "[GATEWAY] RADIO_SPI_VERSION=0x12\n"
            "[GATEWAY] RADIO_VERSION_MISMATCH\n"
            "[GATEWAY] RF_TX_DISABLED_DIAGNOSTIC\n", "GATEWAY")["passed"])

    def test_radio_spi_capture_reads_bounded_updi_log_stream(self):
        class Proof:
            run_dir = Path(".")

        def start_monitor(_proof, role, _port, output_queue):
            output_queue.put((role, "stdout", b"[GATEWAY] RADIO_SPI_VERSION=0x12\r\n"))
            output_queue.put((role, "stdout", b"[GATEWAY] RF_TX_DISABLED_DIAGNOSTIC\r\n"))
            return object()

        with patch.object(rf_proof, "start_rf_monitor", side_effect=start_monitor), \
                patch.object(rf_proof, "stop_rf_monitor", return_value=0):
            evidence = rf_proof.capture_radio_spi_log(
                Proof(), "GATEWAY", "/dev/serial/by-path/gateway")
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["version"], 0x12)
        self.assertEqual(len(evidence["log_lines"]), 2)

    def test_spi_smoke_stage_refuses_non_diagnostic_builds_before_commands(self):
        class Proof:
            commands = []
            notes = []

            def command(self, *args, **kwargs):
                self.commands.append((args, kwargs))
                raise AssertionError("unsafe config must block before hardware commands")

            def note(self, _name, value):
                self.notes.append(value)

        proof = Proof()
        args = SimpleNamespace(
            physical_mapping_verified=True,
            power_verified=True,
            boot_layout_verified=True,
            target_identification_attempted=True,
            authorize_upload=True,
        )
        code = rf_proof.radio_spi_smoke(
            proof,
            args,
            effective_platformio_config(sender_hello_spi_flags=[
                "-DHELLO_TEST_MODE=1",
            ]),
        )
        self.assertEqual(code, 2)
        self.assertEqual(proof.commands, [])
        self.assertIn("diagnostic", proof.notes[-1].lower())

    def test_spi_smoke_uploads_receiver_then_rf_disabled_diagnostic_sender(self):
        class RecordingProof:
            def __init__(self, run_dir):
                self.run_dir = Path(run_dir)
                self.commands = []
                self.notes = []

            def command(self, name, argv, *args, **kwargs):
                self.commands.append((name, argv))
                return 0, b"", b""

            def note(self, _name, message):
                self.notes.append(message)

        with tempfile.TemporaryDirectory() as run_dir:
            proof = RecordingProof(run_dir)
            args = SimpleNamespace(
                physical_mapping_verified=True,
                power_verified=True,
                boot_layout_verified=True,
                target_identification_attempted=True,
                authorize_upload=True,
            )
            with patch.object(rf_proof, "application_layout_verified", return_value=True), \
                    patch.object(rf_proof, "upload_config_preserves_flash", return_value=True), \
                    patch.object(rf_proof, "upload_ports_match", return_value=True), \
                    patch.object(rf_proof, "check_port_owners", return_value=[]), \
                    patch.object(rf_proof, "capture_radio_spi_log",
                                 return_value={"passed": True, "version": 0x12}):
                self.assertEqual(rf_proof.radio_spi_smoke(
                    proof, args, effective_platformio_config()), 0)
            self.assertEqual([name for name, _ in proof.commands], [
                "receiver_spi-radio-spi-diagnostic-upload",
                "sender_hello_spi-radio-spi-diagnostic-upload",
            ])
            report = json.loads((Path(run_dir) /
                                 "radio-spi-measurements.json").read_text())
            self.assertFalse(report["rf_transmission_enabled"])

    def test_preflight_reports_missing_stable_adapter_paths(self):
        self.assertEqual(
            unresolved_adapter_paths([("gateway", 0), ("receiver", 1)]),
            ["receiver adapter path"],
        )

    def test_usb_topology_capture_records_read_only_inventory_commands(self):
        class RecordingProof:
            def __init__(self):
                self.commands = []

            def command(self, name, argv):
                self.commands.append((name, argv))
                return 0, b"", b""

        proof = RecordingProof()
        rf_proof.capture_usb_topology(proof)
        names = [name for name, _ in proof.commands]
        self.assertEqual(names, [
            "usb-by-path-listing", "usb-gateway-path", "usb-receiver-path",
            "usb-ttyUSB0-udev", "usb-ttyUSB1-udev", "usb-tree",
            "pio-device-list", "usb-port-owners", "usb-role-scan",
        ])
        commands = dict(proof.commands)
        self.assertEqual(commands["usb-gateway-path"],
                         ["readlink", "-e", rf_proof.PORTS["gateway"]])
        self.assertEqual(commands["usb-receiver-path"],
                         ["readlink", "-e", rf_proof.PORTS["receiver"]])
        self.assertEqual(commands["pio-device-list"], ["pio", "device", "list"])
        self.assertEqual(proof.commands[-1], (
            "usb-role-scan",
            ["uv", "run", "python", "tools/detect_devices.py", "--scan", "--json"],
        ))
        self.assertFalse(any(command[0] in {"upditerm", "avrdude"}
                             for _, command in proof.commands))
        self.assertEqual([command for _, command in proof.commands
                          if command[0] == "pio"], [["pio", "device", "list"]])

    def test_test_counts_parse_protocol_stdout_and_unittest_stderr(self):
        self.assertEqual(
            parse_test_counts(b"PASS 142 checks\n", b"Ran 3 tests in 0.001s\n"),
            (142, 3),
        )

    def test_hardware_stages_list_unverified_setup_and_missing_authorization(self):
        self.assertEqual(
            hardware_blockers(
                "upload", mapping_verified=False, power_verified=False,
                boot_layout_verified=False,
                authorized=False,
            ),
            ["physical board mapping", "power conditions",
             "BOOTSIZE/CODESIZE/BODCFG fuse verification",
             "upload authorization"],
        )

    def test_rf_test_requires_separate_authorization(self):
        self.assertEqual(
            hardware_blockers(
                "rf-test", mapping_verified=True, power_verified=True,
                boot_layout_verified=False,
                authorized=False,
            ),
            ["BOOTSIZE/CODESIZE/BODCFG fuse verification", "RF-test authorization"],
        )

    def test_stage_unblocks_only_when_every_gate_is_explicit(self):
        self.assertEqual(
            hardware_blockers(
                "upload", mapping_verified=True, power_verified=True,
                boot_layout_verified=True, authorized=True,
            ),
            [],
        )

    def test_only_fuser_exit_one_means_port_is_clear(self):
        checker = getattr(rf_proof, "unavailable_ports", None)
        self.assertTrue(callable(checker), "serial ownership preflight is required")
        self.assertEqual(
            checker([("gateway", 1), ("receiver", 0), ("unknown", 2)]),
            ["receiver", "unknown"],
        )

    def test_role_log_test_count_is_parsed_from_its_actual_result_line(self):
        parser = getattr(rf_proof, "parse_role_log_count", None)
        self.assertTrue(callable(parser), "role-log proof count parser is required")
        self.assertEqual(parser(b"PASS 4 role-log checks\n"), 4)
        self.assertIsNone(parser(b"no test summary\n"))

    def test_radio_wrapper_test_count_is_parsed_from_its_actual_result_line(self):
        parser = getattr(rf_proof, "parse_wrapper_check_count", None)
        self.assertTrue(callable(parser), "radio-wrapper proof count parser is required")
        self.assertEqual(parser(b"PASS 24 radio-wrapper checks\n"), 24)
        self.assertIsNone(parser(b"no test summary\n"))

    def test_serialupdi_upload_config_disables_chip_erase_without_fuse_writes(self):
        checker = getattr(rf_proof, "upload_config_preserves_flash", None)
        self.assertTrue(callable(checker), "safe serialupdi upload config check is required")
        self.assertTrue(checker("[env]\nupload_flags = -D\n"))
        self.assertFalse(checker("[env]\nupload_flags = -e\n"))
        self.assertFalse(checker("[env]\nupload_flags = -D -U lfuse:w:0x00:m\n"))

    def test_repository_upload_config_preserves_flash_and_fuses(self):
        config = (Path(__file__).resolve().parents[1] / "platformio.ini").read_text()
        self.assertTrue(rf_proof.upload_config_preserves_flash(config))


class RfEvidenceTests(unittest.TestCase):
    def parser(self):
        parser = getattr(rf_proof, "parse_rf_campaign", None)
        self.assertTrue(callable(parser), "campaign evidence parser is required")
        return parser

    def test_preflight_is_proven_before_campaign_continuation(self):
        gateway, receiver = complete_campaign_logs(stop_after_preflight=True)
        evidence = self.parser()(gateway, receiver)
        self.assertTrue(evidence["preflight_complete"])
        self.assertEqual(evidence["issues"], [])
        self.assertFalse(evidence["continued"])
        self.assertFalse(evidence["passed"])

    def test_single_packet_acceptance_rejects_a_retried_data_frame(self):
        gateway, receiver = complete_campaign_logs(stop_after_preflight=True)
        retry = packet_event("GATEWAY", "DATA_TX", 0x1234, 1, 2,
                             toa_us=1200000)
        gateway = gateway.replace(
            packet_event("GATEWAY", "DATA_DONE", 0x1234, 1, 1),
            packet_event("GATEWAY", "DATA_DONE", 0x1234, 1, 1) + "\n" + retry)
        evidence = self.parser()(gateway, receiver)

        self.assertTrue(evidence["preflight_complete"])
        self.assertEqual(evidence["retry_count"], 1)
        self.assertFalse(rf_proof.single_packet_evidence_passed(evidence))


    def test_campaign_requires_all_correlated_data_and_ack_events(self):
        gateway, receiver = complete_campaign_logs(omit_final_ack=True)
        evidence = self.parser()(gateway, receiver)
        self.assertFalse(evidence["passed"])
        self.assertEqual(evidence["delivery_sequences"], list(range(1, 20)))
        self.assertEqual(evidence["missing_sequences"], [20])

    def test_campaign_requires_payload_validation_for_every_sequence(self):
        gateway, receiver = complete_campaign_logs()
        receiver = receiver.replace(
            packet_event("RECEIVER", "PAYLOAD_MATCH", 0x1234, 7) + "\n", "")
        evidence = self.parser()(gateway, receiver)
        self.assertFalse(evidence["passed"])
        self.assertNotIn(7, evidence["delivery_sequences"])
        self.assertIn(7, evidence["missing_sequences"])

    def test_campaign_requires_exact_first_payload_bytes_on_both_sides(self):
        gateway, receiver = complete_campaign_logs()
        evidence = self.parser()(gateway, receiver)
        self.assertTrue(evidence["sender_payload_bytes_match"])
        self.assertTrue(evidence["receiver_payload_bytes_match"])

        wrong_gateway = gateway.replace(
            payload_event("GATEWAY", "DATA_PAYLOAD", 0x1234, 1),
            payload_event("GATEWAY", "DATA_PAYLOAD", 0x1234, 1,
                          b"hello worle"),
        )
        wrong_evidence = self.parser()(wrong_gateway, receiver)
        self.assertFalse(wrong_evidence["passed"])
        self.assertFalse(wrong_evidence["sender_payload_bytes_match"])
        self.assertIn("sender sequence-1 payload mismatch", wrong_evidence["issues"])

    def test_campaign_reports_attempts_duplicates_timeouts_and_rtt(self):
        gateway, receiver = complete_campaign_logs()
        gateway = gateway.replace(
            packet_event("GATEWAY", "DATA_TX", 0x1234, 1, 1, toa_us=1200000),
            "\n".join([
                packet_event("GATEWAY", "DATA_TX", 0x1234, 1, 1,
                             toa_us=1200000),
                packet_event("GATEWAY", "ACK_TIMEOUT", 0x1234, 1, 1),
                packet_event("GATEWAY", "DATA_TX", 0x1234, 1, 2,
                             toa_us=1200000),
                packet_event("GATEWAY", "DATA_DONE", 0x1234, 1, 2),
            ]),
        )
        receiver = receiver.replace(
            packet_event("RECEIVER", "DATA_RX", 0x1234, 1),
            "\n".join([
                packet_event("RECEIVER", "DATA_RX", 0x1234, 1),
                packet_event("RECEIVER", "DATA_DUP", 0x1234, 1),
            ]),
        )
        evidence = self.parser()(gateway, receiver)
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["campaign_id"], 0x1234)
        self.assertEqual(evidence["data_tx_started"], 21)
        self.assertEqual(evidence["retry_count"], 1)
        self.assertEqual(evidence["receiver_duplicates"], 1)
        self.assertEqual(evidence["ack_timeouts"], 1)
        self.assertEqual(evidence["airtime_estimates_us"], {
            "gateway": 25200000, "receiver": 16000000,
        })
        self.assertEqual(evidence["latency_ms"], {
            "min": 51, "max": 70, "average": 60.5,
        })

    def test_mixed_campaign_ids_cannot_be_counted_as_one_success(self):
        gateway, receiver = complete_campaign_logs()
        receiver += "\n" + packet_event("RECEIVER", "DATA_RX", 0x9999, 1)
        evidence = self.parser()(gateway, receiver)
        self.assertFalse(evidence["passed"])
        self.assertIn("multiple campaign IDs", evidence["issues"])

    def test_build_marker_is_committed_before_campaign_counter(self):
        source = (Path(__file__).resolve().parents[1] /
                  "src/sender/lib/lora_rx.cpp").read_text()
        marker_write = source.find("EEPROM.put(kCampaignBuildMarkerAddress")
        counter_allocation = source.find("if (!next_campaign_id(&_campaign_id))")
        self.assertGreater(marker_write, -1, "firmware-build marker must be persistent")
        self.assertGreater(counter_allocation, -1, "campaign counter allocation is required")
        self.assertLess(marker_write, counter_allocation,
                        "consume the one-shot boot token before allocating the ID")


class RfTestContinuationTests(unittest.TestCase):
    def test_rf_test_sends_one_c_to_gateway_after_correlated_seq1_ack(self):
        first_gateway, first_receiver = complete_campaign_logs(
            stop_after_preflight=True)
        full_gateway, full_receiver = complete_campaign_logs()
        first_gateway_lines = first_gateway.splitlines()
        first_receiver_lines = first_receiver.splitlines()
        more_gateway_lines = full_gateway.splitlines()[len(first_gateway_lines):]
        more_receiver_lines = full_receiver.splitlines()[len(first_receiver_lines):]

        class FakeStdin:
            def __init__(self, role, output_queue, preflight_state):
                self.role = role
                self.output_queue = output_queue
                self.preflight_state = preflight_state
                self.writes = []

            def write(self, data):
                self.writes.append(data)
                if self.role == "gateway":
                    if data != b"C" or not self.preflight_state["verified"]:
                        raise AssertionError("C must follow correlated sequence-1 ACK")
                    for line in more_gateway_lines:
                        self.output_queue.put(("gateway", "stdout",
                                               (line + "\n").encode()))
                    for line in more_receiver_lines:
                        self.output_queue.put(("receiver", "stdout",
                                               (line + "\n").encode()))
                return len(data)

            def flush(self):
                pass

        class FakeProcess:
            def __init__(self, role, output_queue, preflight_state):
                self.stdin = FakeStdin(role, output_queue, preflight_state)

            def poll(self):
                return None

        preflight_state = {"verified": False}
        real_parser = rf_proof.parse_rf_campaign

        def parse_and_record(gateway, receiver):
            evidence = real_parser(gateway, receiver)
            if evidence["preflight_complete"]:
                preflight_state["verified"] = True
            return evidence

        start_order = []
        monitors = {}

        def start_monitor(proof, role, port, output_queue):
            start_order.append(role)
            process = FakeProcess(role, output_queue, preflight_state)
            monitors[role] = process
            if role == "receiver":
                lines = [first_receiver_lines[0], "[RECEIVER] RADIO_READY"]
                for line in lines:
                    output_queue.put((role, "stdout", (line + "\n").encode()))
            else:
                for line in first_receiver_lines[1:]:
                    output_queue.put(("receiver", "stdout",
                                      (line + "\n").encode()))
                for line in first_gateway_lines:
                    output_queue.put(("gateway", "stdout",
                                      (line + "\n").encode()))
            return {"process": process, "threads": []}

        with tempfile.TemporaryDirectory() as temp_dir:
            notes = []

            class Proof:
                run_dir = Path(temp_dir)

                def note(self, name, content):
                    notes.append((name, content))

            args = SimpleNamespace(
                boot_layout_verified=True,
                target_identification_attempted=False,
                physical_mapping_verified=True,
                power_verified=True,
                authorize_rf_test=True,
            )
            with (
                patch.object(rf_proof, "application_layout_verified",
                             return_value=True),
                patch.object(rf_proof, "upload_ports_match", return_value=True),
                patch.object(rf_proof, "check_port_owners", return_value=[]),
                patch.object(rf_proof, "start_rf_monitor", side_effect=start_monitor),
                patch.object(rf_proof, "stop_rf_monitor", return_value=0),
                patch.object(rf_proof, "parse_rf_campaign", side_effect=parse_and_record),
                patch.object(rf_proof, "RF_TEST_TIMEOUT_SECONDS", 2),
                patch("builtins.print"),
            ):
                result = rf_proof.rf_test(Proof(), args, True, "effective config")

            report = json.loads((Path(temp_dir) / "rf-measurements.json").read_text())
            self.assertEqual(result, 0, notes)
            self.assertEqual(start_order, ["receiver", "gateway"])
            self.assertEqual(monitors["gateway"].stdin.writes, [b"C"])
            self.assertEqual(monitors["receiver"].stdin.writes, [])
            self.assertTrue(report["continue_command_sent"])
            self.assertTrue(report["passed"])

    def test_single_packet_mode_withholds_campaign_continuation_after_seq1_ack(self):
        gateway_text, receiver_text = complete_campaign_logs(stop_after_preflight=True)
        gateway_lines = gateway_text.splitlines()
        receiver_lines = receiver_text.splitlines()

        class FakeStdin:
            def __init__(self):
                self.writes = []

            def write(self, data):
                self.writes.append(data)
                return len(data)

            def flush(self):
                pass

        class FakeProcess:
            def __init__(self):
                self.stdin = FakeStdin()

            def poll(self):
                return None

        processes = {}

        def start_monitor(_proof, role, _port, output_queue):
            process = FakeProcess()
            processes[role] = process
            if role == "receiver":
                lines = [receiver_lines[0], "[RECEIVER] RADIO_READY"]
                for line in lines:
                    output_queue.put(("receiver", "stdout", (line + "\n").encode()))
            else:
                for line in receiver_lines[1:]:
                    output_queue.put(("receiver", "stdout",
                                      (line + "\n").encode()))
                for line in gateway_lines:
                    output_queue.put(("gateway", "stdout",
                                      (line + "\n").encode()))
            return {"process": process, "threads": []}

        with tempfile.TemporaryDirectory() as temp_dir:
            class Proof:
                run_dir = Path(temp_dir)

                def note(self, _name, _content):
                    pass

            args = SimpleNamespace(
                boot_layout_verified=True,
                target_identification_attempted=False,
                physical_mapping_verified=True,
                power_verified=True,
                authorize_rf_test=True,
                single_packet=True,
            )
            with (
                patch.object(rf_proof, "application_layout_verified",
                             return_value=True),
                patch.object(rf_proof, "upload_ports_match", return_value=True),
                patch.object(rf_proof, "check_port_owners", return_value=[]),
                patch.object(rf_proof, "start_rf_monitor", side_effect=start_monitor),
                patch.object(rf_proof, "stop_rf_monitor", return_value=0),
                patch.object(rf_proof, "RF_TEST_TIMEOUT_SECONDS", 0.02),
                patch("builtins.print"),
            ):
                result = rf_proof.rf_test(Proof(), args, True, "effective config")

            report = json.loads((Path(temp_dir) / "rf-measurements.json").read_text())
            self.assertEqual(result, 0, report)
            self.assertEqual(processes["gateway"].stdin.writes, [])
            self.assertEqual(processes["receiver"].stdin.writes, [])
            self.assertTrue(report["single_packet_passed"])
            self.assertFalse(report["continue_command_sent"])


class FlashSafetyTests(unittest.TestCase):
    def test_intel_hex_parser_checks_checksum_and_address_range(self):
        parser = getattr(rf_proof, "parse_ihex_range", None)
        self.assertTrue(callable(parser), "upload hex range verifier is required")
        image = b"\n".join([
            ihex_record(0, 4, b"\x00\x00"),
            ihex_record(0x4000, 0, b"\xAA\xBB\xCC"),
            ihex_record(0, 1, b""),
        ]) + b"\n"
        self.assertEqual(parser(image), {
            "start": 0x4000, "end_exclusive": 0x4003, "data_bytes": 3,
        })
        bad_image = image.replace(b"AA", b"AB", 1)
        with self.assertRaises(ValueError):
            parser(bad_image)

    def test_application_link_origins_follow_each_targets_live_boot_fuse(self):
        config = effective_platformio_config()
        self.assertEqual(rf_proof.application_bounds_for_environment(
            config, "sender_hello"), (0x00000, 0x1FC00))
        self.assertEqual(rf_proof.application_bounds_for_environment(
            config, "receiver"), (0x05800, 0x1FC00))
        self.assertIsNone(rf_proof.application_bounds_for_environment(
            effective_platformio_config(receiver_app_start="0x04000"),
            "receiver"))

    def test_firmware_hex_must_fit_only_inside_generated_appcode(self):
        checker = getattr(rf_proof, "image_fits_application", None)
        self.assertTrue(callable(checker), "BOOT-overwrite range check is required")
        gateway_bounds = (0x00000, 0x1FC00)
        receiver_bounds = (0x05800, 0x1FC00)
        self.assertTrue(checker({"start": 0x00000, "end_exclusive": 0x9000},
                                gateway_bounds))
        self.assertFalse(checker({"start": 0x04000, "end_exclusive": 0x9000},
                                 gateway_bounds))
        self.assertTrue(checker({"start": 0x05800, "end_exclusive": 0xC000},
                                receiver_bounds))
        self.assertFalse(checker({"start": 0x04000, "end_exclusive": 0x9000},
                                 receiver_bounds))
        self.assertFalse(checker({"start": 0x05800, "end_exclusive": 0x20000},
                                 receiver_bounds))

    def test_target_boot_and_bod_fuses_match_their_live_layouts(self):
        parse_fuses = getattr(rf_proof, "target_fuses", None)
        compare_fuses = getattr(rf_proof, "boot_fuses_match", None)
        self.assertTrue(callable(parse_fuses), "target-specific BOOT fuse values are required")
        self.assertTrue(callable(compare_fuses), "target BOOT fuse comparison is required")
        config = effective_platformio_config()
        gateway = parse_fuses(config, "gateway")
        receiver = parse_fuses(config, "receiver")
        self.assertEqual(gateway, {"bootsize": 0, "codesize": 0, "bodcfg": 0})
        self.assertEqual(receiver, {"bootsize": 0x2C, "codesize": 0, "bodcfg": 0x54})
        self.assertTrue(compare_fuses(gateway, gateway))
        self.assertTrue(compare_fuses(receiver, receiver))
        self.assertFalse(compare_fuses({"bootsize": 0x20, "codesize": 0,
                                        "bodcfg": 0x54}, gateway))

    def test_target_identification_opens_no_port_without_physical_gates(self):
        class Proof:
            commands = 0
            notes = []

            def command(self, *args, **kwargs):
                self.commands += 1
                raise AssertionError("serial command must remain blocked")

            def note(self, _name, value):
                self.notes.append(value)

        for mapping, power in ((False, False), (True, False), (False, True)):
            proof = Proof()
            args = SimpleNamespace(
                physical_mapping_verified=mapping,
                power_verified=power,
            )
            self.assertEqual(rf_proof.identify_targets(proof, args), 2)
            self.assertEqual(proof.commands, 0)
            self.assertIn("no serial ports opened", proof.notes[-1])


if __name__ == "__main__":
    unittest.main()
