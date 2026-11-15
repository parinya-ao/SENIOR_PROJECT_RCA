import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rf_proof
from rf_proof import hardware_blockers, parse_test_counts, unresolved_adapter_paths


def packet_event(role, name, campaign, sequence=None, attempt=None, rtt=None, toa_us=None):
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
    return (
        f"[{role}] {name} C={campaign:04X} S={sequence:02X} "
        f"LEN={len(payload)} HEX={payload.hex().upper()} "
        f"ASCII={payload.decode('ascii')}"
    )


def complete_campaign_logs(campaign=0x1234, stop_after_preflight=False, omit_final_ack=False):
    gateway = [
        "[GATEWAY] BOOT sender_hello Nov  6 2026 00:00:00",
        "[GATEWAY] CONFIG_FINGERPRINT="
        + json.loads((rf_proof.ROOT / "generated/lora_manifest.json").read_text())[
            "shared_fingerprint"
        ],
        "[GATEWAY] PROTOCOL_VERSION=1",
        payload_event("GATEWAY", "DATA_PAYLOAD", campaign, 1),
        packet_event("GATEWAY", "DATA_TX", campaign, 1, 1, toa_us=1200000),
        packet_event("GATEWAY", "DATA_DONE", campaign, 1, 1),
    ]
    receiver = [
        "[RECEIVER] BOOT receiver Nov  6 2026 00:00:01",
        "[RECEIVER] CONFIG_FINGERPRINT="
        + json.loads((rf_proof.ROOT / "generated/lora_manifest.json").read_text())[
            "shared_fingerprint"
        ],
        "[RECEIVER] PROTOCOL_VERSION=1",
        payload_event("RECEIVER", "PAYLOAD_BYTES", campaign, 1),
        packet_event("RECEIVER", "PAYLOAD_MATCH", campaign, 1),
        packet_event("RECEIVER", "DATA_RX", campaign, 1),
        packet_event("RECEIVER", "ACK_TX", campaign, 1, toa_us=800000),
        packet_event("RECEIVER", "ACK_DONE", campaign, 1),
    ]
    gateway.extend(
        [
            packet_event("GATEWAY", "ACK_RX", campaign, 1, rtt=51),
            packet_event("GATEWAY", "PREFLIGHT_OK", campaign, 1),
        ]
    )
    if stop_after_preflight:
        return "\n".join(gateway), "\n".join(receiver)

    gateway.append(packet_event("GATEWAY", "CAMPAIGN_CONTINUE", campaign))
    for sequence in range(2, 21):
        gateway.extend(
            [
                packet_event("GATEWAY", "DATA_TX", campaign, sequence, 1, toa_us=1200000),
                packet_event("GATEWAY", "DATA_DONE", campaign, sequence, 1),
            ]
        )
        receiver.extend(
            [
                packet_event("RECEIVER", "PAYLOAD_MATCH", campaign, sequence),
                packet_event("RECEIVER", "DATA_RX", campaign, sequence),
                packet_event("RECEIVER", "ACK_TX", campaign, sequence, toa_us=800000),
                packet_event("RECEIVER", "ACK_DONE", campaign, sequence),
            ]
        )
        if not (omit_final_ack and sequence == 20):
            gateway.append(packet_event("GATEWAY", "ACK_RX", campaign, sequence, rtt=50 + sequence))
    gateway.append(packet_event("GATEWAY", "TEST_COMPLETED", campaign))
    return "\n".join(gateway), "\n".join(receiver)


def ihex_record(address, record_type, data):
    record = bytes([len(data), address >> 8, address & 0xFF, record_type]) + data
    checksum = (-sum(record)) & 0xFF
    return b":" + (record + bytes([checksum])).hex().upper().encode()


def effective_platformio_config(
    sender_flags=None,
    sender_hello_flags=None,
    receiver_flags=None,
    sender_hello_spi_flags=None,
    receiver_spi_flags=None,
    upload_flags=("-D",),
    gateway_app_start="0x00000",
    receiver_app_start="0x05800",
):
    shared = ["-DAPPLICATION_BUILD", "-DLORA_SSOT_GENERATED=1", "-Isrc/shared"]
    sender_flags = list(sender_flags or shared)
    sender_hello_flags = list(
        sender_hello_flags or shared + ["-DHELLO_TEST_MODE=1", "-DHELLO_RAM_ONLY_TEST=1"]
    )
    receiver_flags = list(receiver_flags or shared)
    sender_hello_spi_flags = list(
        sender_hello_spi_flags
        or shared
        + ["-DHELLO_TEST_MODE=1", "-DHELLO_RAM_ONLY_TEST=1", "-DHELLO_RF_DIAGNOSTIC_ONLY=1"]
    )
    receiver_spi_flags = list(receiver_spi_flags or shared + ["-DHELLO_RF_DIAGNOSTIC_ONLY=1"])

    def environment(flags, port, app_start):
        return (
            [
                "build_flags",
                flags,
            ],
            [
                "board_build.text_section_start",
                app_start,
            ],
            [
                "upload_flags",
                list(upload_flags),
            ],
            [
                "upload_protocol",
                "serialupdi",
            ],
            [
                "upload_port",
                port,
            ],
        )

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
    return json.dumps(
        [
            [
                "target_layout",
                [
                    ["gateway_bootsize", "0x00"],
                    ["gateway_codesize", "0x00"],
                    ["gateway_bodcfg", "0x00"],
                    ["gateway_app_start", gateway_app_start],
                    ["receiver_bootsize", "0x2C"],
                    ["receiver_codesize", "0x00"],
                    ["receiver_bodcfg", "0x54"],
                    ["receiver_app_start", receiver_app_start],
                ],
            ],
            [
                "flash_geometry",
                [
                    ["total_bytes", "131072"],
                    ["application_end", "0x1FC00"],
                ],
            ],
            ["env:sender", list(sender)],
            ["env:sender_hello", list(sender_hello)],
            ["env:receiver", list(receiver)],
            ["env:sender_hello_spi", list(sender_hello_spi)],
            ["env:receiver_spi", list(receiver_spi)],
        ]
    )


class TargetLayoutTests(unittest.TestCase):
    def test_target_layout_uses_live_per_board_fuses_and_application_boundaries(self):
        config = effective_platformio_config()

        self.assertEqual(
            rf_proof.target_fuses(config, "gateway"),
            {
                "bootsize": 0x00,
                "codesize": 0x00,
                "bodcfg": 0x00,
            },
        )
        self.assertEqual(
            rf_proof.target_fuses(config, "receiver"),
            {
                "bootsize": 0x2C,
                "codesize": 0x00,
                "bodcfg": 0x54,
            },
        )
        self.assertEqual(
            rf_proof.application_bounds_for_environment(config, "sender_hello"), (0x00000, 0x1FC00)
        )
        self.assertEqual(
            rf_proof.application_bounds_for_environment(config, "receiver"), (0x05800, 0x1FC00)
        )

    def test_receiver_image_must_start_at_the_live_boot_boundary(self):
        config = effective_platformio_config(receiver_app_start="0x04000")

        self.assertIsNone(rf_proof.application_bounds_for_environment(config, "receiver"))


class HardwareGateTests(unittest.TestCase):
    def setUp(self):
        readiness = patch.object(rf_proof, "physical_readiness_errors", return_value=[])
        readiness.start()
        self.addCleanup(readiness.stop)

    def test_campaign_build_skip_keeps_ready_gateway_on_normal_rx_path(self):
        source = (Path(__file__).resolve().parents[1] / "src/sender/lib/lora_rx.cpp").read_text()
        boot_gate = source.index("if (test_campaign.state == SSOT_TEST_IDLE)")
        for decision in ("AlreadyRun", "ReadbackFailed"):
            marker = f"if (_campaign_build_gate_result ==\n                    CampaignBuildGateResult::{decision})"
            start = source.index(marker, boot_gate)
            end = source.index("\n                }", start)
            branch = source[start:end]
            self.assertIn("ssot_campaign_fail(&test_campaign);", branch)
            self.assertIn("continue;", branch)
            self.assertNotIn("_started = false;", branch)

    def test_sender_and_receiver_lora_pins_match_board_revision_1(self):
        gateway = {
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
            expected = (
                dict(CS="PIN_PD0", RST="PIN_PD1", IRQ="PIN_PD3", DIO1="PIN_PD2")
                if "receiver" in str(path)
                else gateway
            )
            bindings = {}
            for line in path.read_text().splitlines():
                parts = line.split()
                if len(parts) == 3 and parts[:1] == ["#define"]:
                    name = parts[1].removeprefix("PIN_LORA_")
                    if name in expected:
                        bindings[name] = parts[2]
            self.assertEqual(bindings, {name: f"LORA_PIN_{name}" for name in expected}, str(path))
        header = (root / "include/generated/radio_915_config.h").read_text()
        for pin in (*gateway.values(), "PIN_PD0", "PIN_PD1", "PIN_PD3", "PIN_PD2"):
            self.assertIn(pin, header)
        receiver = sources[1].read_text()
        self.assertIn("#define PIN_LORA_EN LORA_PIN_ENABLE", receiver)

    def test_both_radio_setups_keep_dio1_input_and_reset_deasserted(self):
        root = Path(__file__).resolve().parents[1]
        sender = (root / "src/sender/lib/io.cpp").read_text()
        self.assertIn("pinModeFast(PIN_LORA_DIO1, INPUT);", sender)
        self.assertIn("digitalWriteFast(PIN_LORA_RST, HIGH);", sender)
        receiver = (root / "src/receiver/main.cpp").read_text()
        self.assertIn("pinModeFast(PIN_LORA_RST, INPUT);", receiver)

    def test_led_and_debug_uart_macros_follow_schematic_and_dxcore_directions(self):
        root = Path(__file__).resolve().parents[1]
        expected_leds = {"PIN_LED1": "PIN_PA5", "PIN_LED2": "PIN_PA4"}
        for relative in ("src/sender/lib/io.h",):
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

    def test_shared_rf_profile_only_accepts_the_generated_915_mhz_profile(self):
        validator = getattr(rf_proof, "valid_rf_profile_config", None)
        self.assertTrue(callable(validator), "shared RF profile validation is required")
        config = effective_platformio_config()
        self.assertTrue(validator(config))
        self.assertEqual(
            rf_proof.shared_rf_profile(config),
            {
                "frequency_hz": 915_000_000,
                "frequency_mhz": 915.0,
                "tx_power_dbm": 10,
                "long_range": 0,
                "spreading_factor": 7,
                "bandwidth_khz": 125,
                "coding_rate": 5,
                "sync_word": 0x12,
                "preamble_symbols": 8,
                "crc_enabled": True,
                "explicit_header": True,
                "iq_inverted": False,
                "current_limit_ma": 200,
                "automatic_gain": 0,
            },
        )
        self.assertFalse(
            validator("""[env]\nbuild_flags =\n    -DHELLO_RF_FREQUENCY_MHZ=923.0f\n""")
        )

    def test_spi_diagnostic_environments_are_separate_and_rf_disabled(self):
        disabled = effective_platformio_config()
        checker = getattr(rf_proof, "rf_spi_diagnostic_config", None)
        self.assertTrue(callable(checker), "dedicated RF-disabled SPI config check is required")
        self.assertTrue(checker(disabled))
        self.assertFalse(
            checker(effective_platformio_config(sender_hello_spi_flags=["-DHELLO_TEST_MODE=1"]))
        )
        self.assertFalse(
            checker(effective_platformio_config(receiver_spi_flags=["-DAPPLICATION_BUILD"]))
        )
        self.assertFalse(
            checker(
                effective_platformio_config(
                    sender_hello_flags=["-DHELLO_TEST_MODE=1", "-DHELLO_RF_DIAGNOSTIC_ONLY=1"]
                )
            )
        )

    def test_effective_profile_validator_rejects_role_specific_overrides(self):
        validator = getattr(rf_proof, "valid_rf_profile_config", None)
        self.assertTrue(callable(validator))
        profile = effective_platformio_config()
        self.assertEqual(rf_proof.shared_rf_profile(profile)["frequency_mhz"], 915.0)
        changed_receiver = effective_platformio_config(
            receiver_flags=[
                "-DAPPLICATION_BUILD",
                "-DLORA_SSOT_GENERATED=1",
                "-DHELLO_RF_LONG_RANGE=1",
                "-Isrc/shared",
            ]
        )
        self.assertFalse(validator(changed_receiver))
        self.assertFalse(
            validator(
                effective_platformio_config(
                    sender_hello_flags=[
                        "-DAPPLICATION_BUILD",
                        "-DLORA_SSOT_GENERATED=1",
                        "-DHELLO_TEST_MODE=1",
                        "-DHELLO_RAM_ONLY_TEST=1",
                        "-DHELLO_RF_FREQUENCY_MHZ=923.0f",
                    ]
                )
            )
        )

    def test_wrapper_host_compile_uses_effective_platformio_profile(self):
        flags = rf_proof.radio_profile_compile_flags(effective_platformio_config())
        self.assertEqual(flags, ["-DLORA_ROLE_SENDER=1"])

    def test_host_test_stage_uses_only_checked_in_sources(self):
        class RecordingProof:
            def __init__(self, run_dir):
                self.run_dir = run_dir
                self.commands = []

            def command(self, name, argv, *args, **kwargs):
                self.commands.append((name, list(argv)))
                missing = [
                    arg
                    for arg in argv
                    if isinstance(arg, str)
                    and arg.endswith((".cpp", ".c"))
                    and not (rf_proof.ROOT / arg).is_file()
                ]
                if missing:
                    return 1, b"", f"missing source: {missing[0]}".encode()
                return 0, b"PASS 1 checks", b"Ran 1 tests"

        with tempfile.TemporaryDirectory() as directory:
            proof = RecordingProof(Path(directory))
            with (
                patch.object(rf_proof, "parse_test_counts", return_value=(None, 1)),
                patch.object(rf_proof, "parse_role_log_count", return_value=1),
                patch.object(rf_proof, "parse_wrapper_check_count", return_value=1),
            ):
                result = rf_proof.host_tests(proof, effective_platformio_config())
            self.assertEqual(result, 0)
            measurements = json.loads((proof.run_dir / "host-measurements.json").read_text())
            self.assertEqual(measurements["runner_unit_tests"], 1)
            diagnostic_argv = next(
                argv for name, argv in proof.commands if name == "diagnostic-protection-compile"
            )
            self.assertIn("-DLORA_ROLE_SENDER=1", diagnostic_argv)

    def test_effective_upload_flags_and_ports_are_checked(self):
        config = effective_platformio_config()
        preserves = getattr(rf_proof, "upload_config_preserves_flash", None)
        ports_match = getattr(rf_proof, "upload_ports_match", None)
        self.assertTrue(callable(ports_match), "effective upload-port mapping check is required")
        self.assertTrue(preserves(config))
        self.assertTrue(ports_match(config))
        self.assertFalse(
            rf_proof.upload_config_preserves_flash(
                effective_platformio_config(upload_flags=("-D", "-e"))
            )
        )
        self.assertFalse(
            rf_proof.upload_config_preserves_flash(
                effective_platformio_config(upload_flags=("-D", "-U", "fuse:w:0x00:m"))
            )
        )
        self.assertFalse(
            ports_match(
                effective_platformio_config().replace(
                    "/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0", "/dev/ttyUSB0"
                )
            )
        )

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
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(rf_proof, "program_application", return_value=0) as program,
            patch.object(rf_proof, "receiver_boot_handoff_supported", return_value=True),
            patch.object(rf_proof, "verify_installed_images", return_value={}),
            patch.object(rf_proof, "application_layout_verified", return_value=True),
            patch.object(rf_proof, "upload_config_preserves_flash", return_value=True),
            patch.object(rf_proof, "upload_ports_match", return_value=True),
            patch.object(rf_proof, "check_port_owners", return_value=[]),
        ):
            proof.run_dir = Path(directory)
            self.assertEqual(rf_proof.upload(proof, args, True, "effective"), 0)
        self.assertEqual(
            [call.args[1] for call in program.call_args_list], ["receiver", "sender_hello"]
        )

    def test_rf_enabled_upload_does_not_require_rf_authorization(self):
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
            authorize_rf_test=False,
            rf_hardware_verified=False,
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(rf_proof, "program_application", return_value=0) as program,
            patch.object(rf_proof, "receiver_boot_handoff_supported", return_value=True),
            patch.object(rf_proof, "verify_installed_images", return_value={}),
            patch.object(rf_proof, "application_layout_verified", return_value=True),
            patch.object(rf_proof, "upload_config_preserves_flash", return_value=True),
            patch.object(rf_proof, "upload_ports_match", return_value=True),
            patch.object(rf_proof, "check_port_owners", return_value=[]),
        ):
            proof.run_dir = Path(directory)
            self.assertEqual(rf_proof.upload(proof, args, True, "effective"), 0)
        self.assertEqual(
            [call.args[1] for call in program.call_args_list], ["receiver", "sender_hello"]
        )

    def test_hardware_blockers_only_represent_physical_and_action_gates(self):
        self.assertEqual(
            hardware_blockers(
                "radio-spi-smoke",
                mapping_verified=True,
                power_verified=True,
                boot_layout_verified=True,
                authorized=True,
            ),
            [],
        )
        self.assertEqual(
            hardware_blockers(
                "radio-spi-smoke",
                mapping_verified=False,
                power_verified=False,
                boot_layout_verified=False,
                authorized=False,
            ),
            [
                "physical board mapping",
                "power conditions",
                "BOOTSIZE/CODESIZE/BODCFG fuse verification",
                "upload authorization",
            ],
        )
        self.assertEqual(
            hardware_blockers(
                "upload",
                mapping_verified=True,
                power_verified=True,
                boot_layout_verified=True,
                authorized=True,
            ),
            [],
        )

    def test_radio_spi_log_requires_version_and_diagnostic_only_marker(self):
        parser = getattr(rf_proof, "parse_radio_spi_log", None)
        self.assertTrue(callable(parser), "SPI smoke evidence parser is required")
        result = parser(
            "[GATEWAY] RADIO_SPI_VERSION=0x12\n[GATEWAY] RF_TX_DISABLED_DIAGNOSTIC\n",
            "GATEWAY",
        )
        self.assertEqual(result["version"], 0x12)
        self.assertTrue(result["tx_disabled"])
        self.assertTrue(result["passed"])
        self.assertFalse(parser("[GATEWAY] RADIO_SPI_VERSION=0x12\n", "GATEWAY")["passed"])
        self.assertFalse(
            parser(
                "[GATEWAY] RADIO_SPI_VERSION=0x12\n"
                "[GATEWAY] RADIO_VERSION_MISMATCH\n"
                "[GATEWAY] RF_TX_DISABLED_DIAGNOSTIC\n",
                "GATEWAY",
            )["passed"]
        )

    def test_radio_spi_capture_reads_bounded_updi_log_stream(self):
        class Proof:
            run_dir = Path()

        def start_monitor(_proof, role, _port, output_queue):
            output_queue.put((role, "stdout", b"[GATEWAY] RADIO_SPI_VERSION=0x12\r\n"))
            output_queue.put((role, "stdout", b"[GATEWAY] RF_TX_DISABLED_DIAGNOSTIC\r\n"))
            return object()

        with (
            patch.object(rf_proof, "start_rf_monitor", side_effect=start_monitor),
            patch.object(rf_proof, "stop_rf_monitor", return_value=0),
        ):
            evidence = rf_proof.capture_radio_spi_log(
                Proof(), "GATEWAY", "/dev/serial/by-path/gateway"
            )
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
            effective_platformio_config(
                sender_hello_spi_flags=[
                    "-DHELLO_TEST_MODE=1",
                ]
            ),
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
            with (
                patch.object(rf_proof, "receiver_boot_handoff_supported", return_value=True),
                patch.object(rf_proof, "program_application", return_value=0) as program,
                patch.object(rf_proof, "application_layout_verified", return_value=True),
                patch.object(rf_proof, "upload_config_preserves_flash", return_value=True),
                patch.object(rf_proof, "upload_ports_match", return_value=True),
                patch.object(rf_proof, "check_port_owners", return_value=[]),
                patch.object(
                    rf_proof,
                    "capture_radio_spi_log",
                    return_value={"passed": True, "version": 0x12},
                ),
            ):
                self.assertEqual(
                    rf_proof.radio_spi_smoke(proof, args, effective_platformio_config()), 0
                )
            self.assertEqual(
                [call.args[1] for call in program.call_args_list],
                ["receiver_spi", "sender_hello_spi"],
            )
            report = json.loads((Path(run_dir) / "radio-spi-measurements.json").read_text())
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
        self.assertEqual(
            names,
            [
                "usb-by-path-listing",
                "usb-gateway-path",
                "usb-receiver-path",
                "usb-ttyUSB0-udev",
                "usb-ttyUSB1-udev",
                "usb-tree",
                "pio-device-list",
                "usb-port-owners",
                "usb-role-scan",
            ],
        )
        commands = dict(proof.commands)
        self.assertEqual(
            commands["usb-gateway-path"], ["readlink", "-e", rf_proof.PORTS["gateway"]]
        )
        self.assertEqual(
            commands["usb-receiver-path"], ["readlink", "-e", rf_proof.PORTS["receiver"]]
        )
        self.assertEqual(commands["pio-device-list"], ["pio", "device", "list"])
        self.assertEqual(
            proof.commands[-1],
            (
                "usb-role-scan",
                ["uv", "run", "python", "tools/detect_devices.py", "--scan", "--json"],
            ),
        )
        self.assertFalse(
            any(command[0] in {"upditerm", "avrdude"} for _, command in proof.commands)
        )
        self.assertEqual(
            [command for _, command in proof.commands if command[0] == "pio"],
            [["pio", "device", "list"]],
        )

    def test_test_counts_parse_protocol_stdout_and_unittest_stderr(self):
        self.assertEqual(
            parse_test_counts(b"PASS 142 checks\n", b"Ran 3 tests in 0.001s\n"),
            (142, 3),
        )

    def test_hardware_stages_list_unverified_setup_and_missing_authorization(self):
        self.assertEqual(
            hardware_blockers(
                "upload",
                mapping_verified=False,
                power_verified=False,
                boot_layout_verified=False,
                authorized=False,
            ),
            [
                "physical board mapping",
                "power conditions",
                "BOOTSIZE/CODESIZE/BODCFG fuse verification",
                "upload authorization",
            ],
        )

    def test_rf_test_requires_separate_authorization(self):
        self.assertEqual(
            hardware_blockers(
                "rf-test",
                mapping_verified=True,
                power_verified=True,
                boot_layout_verified=False,
                authorized=False,
            ),
            ["BOOTSIZE/CODESIZE/BODCFG fuse verification", "RF-test authorization"],
        )

    def test_stage_unblocks_only_when_every_gate_is_explicit(self):
        self.assertEqual(
            hardware_blockers(
                "upload",
                mapping_verified=True,
                power_verified=True,
                boot_layout_verified=True,
                authorized=True,
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
        retry = packet_event("GATEWAY", "DATA_TX", 0x1234, 1, 2, toa_us=1200000)
        gateway = gateway.replace(
            packet_event("GATEWAY", "DATA_DONE", 0x1234, 1, 1),
            packet_event("GATEWAY", "DATA_DONE", 0x1234, 1, 1) + "\n" + retry,
        )
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
        receiver = receiver.replace(packet_event("RECEIVER", "PAYLOAD_MATCH", 0x1234, 7) + "\n", "")
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
            payload_event("GATEWAY", "DATA_PAYLOAD", 0x1234, 1, b"hello worle"),
        )
        wrong_evidence = self.parser()(wrong_gateway, receiver)
        self.assertFalse(wrong_evidence["passed"])
        self.assertFalse(wrong_evidence["sender_payload_bytes_match"])
        self.assertIn("sender sequence-1 payload mismatch", wrong_evidence["issues"])

    def test_campaign_reports_attempts_duplicates_timeouts_and_rtt(self):
        gateway, receiver = complete_campaign_logs()
        gateway = gateway.replace(
            packet_event("GATEWAY", "DATA_TX", 0x1234, 1, 1, toa_us=1200000),
            "\n".join(
                [
                    packet_event("GATEWAY", "DATA_TX", 0x1234, 1, 1, toa_us=1200000),
                    packet_event("GATEWAY", "ACK_TIMEOUT", 0x1234, 1, 1),
                    packet_event("GATEWAY", "DATA_TX", 0x1234, 1, 2, toa_us=1200000),
                    packet_event("GATEWAY", "DATA_DONE", 0x1234, 1, 2),
                ]
            ),
        )
        receiver = receiver.replace(
            packet_event("RECEIVER", "DATA_RX", 0x1234, 1),
            "\n".join(
                [
                    packet_event("RECEIVER", "DATA_RX", 0x1234, 1),
                    packet_event("RECEIVER", "DATA_DUP", 0x1234, 1),
                ]
            ),
        )
        evidence = self.parser()(gateway, receiver)
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["campaign_id"], 0x1234)
        self.assertEqual(evidence["data_tx_started"], 21)
        self.assertEqual(evidence["retry_count"], 1)
        self.assertEqual(evidence["receiver_duplicates"], 1)
        self.assertEqual(evidence["ack_timeouts"], 1)
        self.assertEqual(
            evidence["airtime_estimates_us"],
            {
                "gateway": 25200000,
                "receiver": 16000000,
            },
        )
        self.assertEqual(
            evidence["latency_ms"],
            {
                "min": 51,
                "max": 70,
                "average": 60.5,
            },
        )

    def test_mixed_campaign_ids_cannot_be_counted_as_one_success(self):
        gateway, receiver = complete_campaign_logs()
        receiver += "\n" + packet_event("RECEIVER", "DATA_RX", 0x9999, 1)
        evidence = self.parser()(gateway, receiver)
        self.assertFalse(evidence["passed"])
        self.assertIn("multiple campaign IDs", evidence["issues"])

    def test_build_marker_is_committed_before_session_start(self):
        source = (Path(__file__).resolve().parents[1] / "src/sender/lib/lora_rx.cpp").read_text()
        marker_write = source.find("EEPROM.put(kCampaignBuildMarkerAddress")
        counter_allocation = source.find("if (!ssot_campaign_arm(&test_campaign, _campaign_id)")
        self.assertGreater(marker_write, -1, "firmware-build marker must be persistent")
        self.assertGreater(counter_allocation, -1, "fresh session arming is required")
        self.assertLess(
            marker_write,
            counter_allocation,
            "consume the one-shot boot token before allocating the ID",
        )


class RfTestContinuationTests(unittest.TestCase):
    def test_rf_test_blocks_without_verified_upload_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            proof = SimpleNamespace(run_dir=Path(directory), note=lambda *_: None)
            args = SimpleNamespace(
                physical_mapping_verified=True,
                power_verified=True,
                boot_layout_verified=True,
                authorize_rf_test=True,
            )
            with (
                patch.object(rf_proof, "application_layout_verified", return_value=True),
                patch.object(rf_proof, "upload_ports_match", return_value=True),
                patch.object(rf_proof, "check_port_owners", return_value=[]),
                patch.object(rf_proof, "physical_readiness_errors", return_value=[]),
                patch.object(rf_proof, "start_rf_monitor") as monitor,
            ):
                self.assertEqual(rf_proof.rf_test(proof, args, True, "config"), 2)
                monitor.assert_not_called()


class FlashSafetyTests(unittest.TestCase):
    def test_no_meter_identity_uses_live_unique_serial_without_checklist(self):
        backup = json.loads((rf_proof.ROOT / "config/current_hardware.json").read_text())
        for wrong_serial in (False, True):
            with (
                self.subTest(wrong_serial=wrong_serial),
                tempfile.TemporaryDirectory() as directory,
            ):
                commands = []
                proof = SimpleNamespace(run_dir=Path(directory), note=lambda *_: None)

                def command(name, argv, *unused):
                    commands.append(argv)
                    if argv[0] == "fuser":
                        return 1, "", ""
                    if "-U" in argv:
                        self.assertIn("-N", argv)
                        role = "receiver" if "receiver" in name else "gateway"
                        original = backup[role]
                        memories = dict(
                            bootsize=bytes.fromhex(original["fuses_hex"])[8:9],
                            codesize=b"\0",
                            bodcfg=bytes.fromhex(original["fuses_hex"])[1:2],
                            signature=bytes.fromhex("1e970a"),
                            sernum=bytes(16)
                            if wrong_serial
                            else bytes.fromhex(original["device_serial_hex"]),
                        )
                        for i, value in enumerate(argv):
                            if value == "-U":
                                memory, mode, path, encoding = argv[i + 1].split(":")
                                self.assertEqual(mode, "r")
                                Path(path).write_bytes(memories[memory])
                    return 0, "live response", ""

                proof.command = command
                args = SimpleNamespace(
                    no_meter_mode=True, physical_mapping_verified=True, power_verified=True
                )
                with patch.object(
                    rf_proof, "target_fuses", return_value=dict(bootsize=0, codesize=0, bodcfg=0)
                ):
                    self.assertEqual(
                        rf_proof.identify_targets(proof, args, effective_platformio_config()),
                        2 if wrong_serial else 0,
                    )
                self.assertTrue(any("-U" in argv for argv in commands))
                self.assertTrue(args.no_meter_mode)

    def test_no_meter_retains_authorization_and_boot_gates(self):
        blockers = hardware_blockers(
            "radio-spi-smoke",
            mapping_verified=False,
            power_verified=False,
            boot_layout_verified=False,
            authorized=False,
            no_meter=True,
        )
        self.assertEqual(
            blockers, ["BOOTSIZE/CODESIZE/BODCFG fuse verification", "upload authorization"]
        )

    def test_no_meter_does_not_skip_rf_hardware_suitability(self):
        args = SimpleNamespace(
            no_meter_mode=True,
            physical_mapping_verified=True,
            power_verified=True,
            rf_hardware_verified=False,
        )
        self.assertEqual(rf_proof.physical_readiness_errors(args), [])
        self.assertEqual(
            rf_proof.physical_readiness_errors(args, require_rf=True),
            ["radio/module/antenna compatibility and safe RF power"],
        )
        args.rf_hardware_verified = True
        self.assertEqual(rf_proof.physical_readiness_errors(args, require_rf=True), [])

    def test_no_meter_does_not_bypass_mapping_or_electrical_safety(self):
        for key in ("physical_mapping_verified", "power_verified"):
            with self.subTest(key=key):
                args = SimpleNamespace(
                    no_meter_mode=True, physical_mapping_verified=True, power_verified=True
                )
                setattr(args, key, False)
                proof = SimpleNamespace(
                    note=lambda *_: None,
                    command=lambda *_: self.fail("unsafe target must not be accessed"),
                )
                self.assertTrue(rf_proof.physical_readiness_errors(args))
                self.assertEqual(rf_proof.identify_targets(proof, args), 2)

    def test_intel_hex_parser_checks_checksum_and_address_range(self):
        parser = getattr(rf_proof, "parse_ihex_range", None)
        self.assertTrue(callable(parser), "upload hex range verifier is required")
        image = (
            b"\n".join(
                [
                    ihex_record(0, 4, b"\x00\x00"),
                    ihex_record(0x4000, 0, b"\xaa\xbb\xcc"),
                    ihex_record(0, 1, b""),
                ]
            )
            + b"\n"
        )
        self.assertEqual(
            parser(image),
            {
                "start": 0x4000,
                "end_exclusive": 0x4003,
                "data_bytes": 3,
            },
        )
        bad_image = image.replace(b"AA", b"AB", 1)
        with self.assertRaises(ValueError):
            parser(bad_image)

    def test_application_link_origins_follow_each_targets_live_boot_fuse(self):
        config = effective_platformio_config()
        self.assertEqual(
            rf_proof.application_bounds_for_environment(config, "sender_hello"), (0x00000, 0x1FC00)
        )
        self.assertEqual(
            rf_proof.application_bounds_for_environment(config, "receiver"), (0x05800, 0x1FC00)
        )
        self.assertIsNone(
            rf_proof.application_bounds_for_environment(
                effective_platformio_config(receiver_app_start="0x04000"), "receiver"
            )
        )

    def test_firmware_hex_must_fit_only_inside_generated_appcode(self):
        checker = getattr(rf_proof, "image_fits_application", None)
        self.assertTrue(callable(checker), "BOOT-overwrite range check is required")
        gateway_bounds = (0x00000, 0x1FC00)
        receiver_bounds = (0x05800, 0x1FC00)
        self.assertTrue(checker({"start": 0x00000, "end_exclusive": 0x9000}, gateway_bounds))
        self.assertFalse(checker({"start": 0x04000, "end_exclusive": 0x9000}, gateway_bounds))
        self.assertTrue(checker({"start": 0x05800, "end_exclusive": 0xC000}, receiver_bounds))
        self.assertFalse(checker({"start": 0x04000, "end_exclusive": 0x9000}, receiver_bounds))
        self.assertFalse(checker({"start": 0x05800, "end_exclusive": 0x20000}, receiver_bounds))

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
        self.assertFalse(compare_fuses({"bootsize": 0x20, "codesize": 0, "bodcfg": 0x54}, gateway))

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
