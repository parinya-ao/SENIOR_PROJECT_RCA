import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Never, cast
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from tools import rf_proof
from tools.rf_proof import hardware_blockers, parse_test_counts, unresolved_adapter_paths


def dynamic_attr(name: str) -> Any:
    return getattr(rf_proof, name, None)


def packet_event(
    role: str,
    name: str,
    campaign: int,
    sequence: int | None = None,
    attempt: int | None = None,
    rtt: int | None = None,
    toa_us: int | None = None,
) -> str:
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


def payload_event(
    role: str, name: str, campaign: int, sequence: int, payload: bytes = b"hello world"
) -> str:
    return (
        f"[{role}] {name} C={campaign:04X} S={sequence:02X} "
        f"LEN={len(payload)} HEX={payload.hex().upper()} "
        f"ASCII={payload.decode('ascii')}"
    )


def complete_campaign_logs(
    campaign: int = 0x1234,
    stop_after_preflight: bool = False,
    omit_final_ack: bool = False,
) -> tuple[str, str]:
    gateway = [
        "[GATEWAY] BOOT sender_hello Nov  6 2026 00:00:00",
        "[GATEWAY] CONFIG_FINGERPRINT="
        + json.loads((dynamic_attr("ROOT") / "generated/lora_manifest.json").read_text())[
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
        + json.loads((dynamic_attr("ROOT") / "generated/lora_manifest.json").read_text())[
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


def ihex_record(address: int, record_type: int, data: bytes) -> bytes:
    record = bytes([len(data), address >> 8, address & 0xFF, record_type]) + data
    checksum = (-sum(record)) & 0xFF
    return b":" + (record + bytes([checksum])).hex().upper().encode()


def effective_platformio_config(
    sender_flags: list[str] | None = None,
    sender_hello_flags: list[str] | None = None,
    receiver_flags: list[str] | None = None,
    sender_hello_spi_flags: list[str] | None = None,
    receiver_spi_flags: list[str] | None = None,
    upload_flags: tuple[str, ...] = ("-D",),
    gateway_app_start: str = "0x00000",
    receiver_app_start: str = "0x05800",
) -> str:
    shared = ["-DAPPLICATION_BUILD", "-DLORA_SSOT_GENERATED=1", "-Isrc/shared"]
    sender_flags = list(sender_flags or shared)
    sender_hello_flags = list(
        sender_hello_flags or [*shared, "-DHELLO_TEST_MODE=1", "-DHELLO_RAM_ONLY_TEST=1"]
    )
    receiver_flags = list(receiver_flags or shared)
    sender_hello_spi_flags = list(
        sender_hello_spi_flags
        or [
            *shared,
            "-DHELLO_TEST_MODE=1",
            "-DHELLO_RAM_ONLY_TEST=1",
            "-DHELLO_RF_DIAGNOSTIC_ONLY=1",
        ]
    )
    receiver_spi_flags = list(receiver_spi_flags or [*shared, "-DHELLO_RF_DIAGNOSTIC_ONLY=1"])

    def environment(flags: list[str], port: str, app_start: str) -> tuple[list[Any], ...]:
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
    def test_target_layout_uses_live_per_board_fuses_and_application_boundaries(self) -> None:
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

    def test_receiver_image_must_start_at_the_live_boot_boundary(self) -> None:
        config = effective_platformio_config(receiver_app_start="0x04000")

        self.assertIsNone(rf_proof.application_bounds_for_environment(config, "receiver"))


class HardwareGateTests(unittest.TestCase):
    def setUp(self) -> None:
        readiness = patch.object(rf_proof, "physical_readiness_errors", return_value=[])
        readiness.start()
        self.addCleanup(readiness.stop)

    def test_hello_radio_images_keep_sx127x_hf_errata_enabled(self) -> None:
        config = subprocess.check_output(
            ["pio", "project", "config", "--json-output"], cwd=dynamic_attr("ROOT"), text=True
        )
        sections = rf_proof.effective_project_sections(config)
        if sections is None:
            self.fail("effective PlatformIO configuration did not parse")
        for environment in ("env:sender_hello", "env:receiver"):
            with self.subTest(environment=environment):
                self.assertIn(
                    "-DRADIOLIB_FIX_ERRATA_SX127X=1",
                    cast("list[str]", sections[environment]["build_flags"]),
                )

    def test_full_application_receiver_does_not_need_boot_handoff(self) -> None:
        proof: Any = SimpleNamespace(note=lambda *_: None)
        args: Any = SimpleNamespace(boot_layout_verified=True, receiver_boot_evidence=None)
        with (
            patch.object(rf_proof, "application_bounds_for_environment", return_value=(0, 0x1FC00)),
            patch.object(
                rf_proof,
                "target_fuses",
                return_value={"bootsize": 0, "codesize": 0, "bodcfg": 0},
            ),
            patch.object(dynamic_attr("subprocess"), "check_output", return_value=""),
        ):
            self.assertTrue(rf_proof.receiver_boot_handoff_supported(proof, args, "active config"))

    def test_sender_uses_only_supported_stable_lora_calls(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "src/sender/lib/lora_rx.cpp").read_text()
        self.assertIn("../../../stable_lib/lora/lora.h", source)
        self.assertIn("ReliableTransport<LoRa>", source)
        self.assertIn("transport.send_reliable_data", source)
        for legacy in ("read_chip_version", "last_error", "time_on_air_us",
                       "start_receive", "recover", "EEPROM"):
            with self.subTest(legacy=legacy):
                self.assertNotIn(legacy, source)

    def test_sender_and_receiver_lora_pins_match_board_revision_1(self) -> None:
        gateway = {
            "CS": "PIN_PC3",
            "RST": "PIN_PD0",
            "IRQ": "PIN_PD2",
            "DIO1": "PIN_PD3",
        }
        root = Path(__file__).resolve().parents[1]
        profile = tomllib.loads((root / "config/radio_915.toml").read_text())
        self.assertEqual(profile["sender"]["pins"]["cs"], gateway["CS"].removeprefix("PIN_"))
        self.assertEqual(profile["sender"]["pins"]["rst"], gateway["RST"].removeprefix("PIN_"))
        self.assertEqual(profile["sender"]["pins"]["irq"], gateway["IRQ"].removeprefix("PIN_"))
        self.assertEqual(profile["sender"]["pins"]["dio1"], gateway["DIO1"].removeprefix("PIN_"))
        self.assertEqual(
            profile["receiver"]["pins"],
            {"mosi":"PC0","miso":"PC1","sck":"PC2","cs":"PD0",
             "rst":"PD1","irq":"PD3","dio1":"PD2","enable":"PA7"},
        )
        constructor = "LoRa lora(LORA_PIN_CS,LORA_PIN_IRQ,LORA_PIN_RST,LORA_PIN_DIO1)"
        self.assertIn(constructor,(root/"src/sender/lib/lora_rx.cpp").read_text())
        self.assertIn(constructor,(root/"src/reliable/main.cpp").read_text())
        self.assertIn(constructor,(root/"src/receiver/main.cpp").read_text())

    def test_both_radio_setups_keep_dio1_input_and_reset_deasserted(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sender = (root / "src/sender/lib/io.cpp").read_text()
        self.assertIn("pinModeFast(PIN_LORA_DIO1, INPUT);", sender)
        self.assertIn("digitalWriteFast(PIN_LORA_RST, HIGH);", sender)
        receiver = (root / "src/receiver/main.cpp").read_text()
        self.assertIn("pinModeFast(LORA_PIN_RST,INPUT);", receiver)
        self.assertIn("pinModeFast(LORA_PIN_DIO1,INPUT);", receiver)

    def test_led_and_debug_uart_macros_follow_schematic_and_dxcore_directions(self) -> None:
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

    def test_shared_rf_profile_only_accepts_the_generated_915_mhz_profile(self) -> None:
        validator = dynamic_attr("valid_rf_profile_config")
        self.assertTrue(callable(validator), "shared RF profile validation is required")
        config = effective_platformio_config()
        self.assertTrue(validator(config))
        self.assertEqual(
            rf_proof.shared_rf_profile(config),
            {
                "frequency_hz": 915_000_000,
                "frequency_mhz": 915.0,
                "tx_power_dbm": 2,
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

    def test_spi_diagnostic_environments_are_separate_and_rf_disabled(self) -> None:
        disabled = effective_platformio_config()
        checker = dynamic_attr("rf_spi_diagnostic_config")
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

    def test_effective_profile_validator_rejects_role_specific_overrides(self) -> None:
        validator = dynamic_attr("valid_rf_profile_config")
        self.assertTrue(callable(validator))
        profile = effective_platformio_config()
        shared_profile = rf_proof.shared_rf_profile(profile)
        if shared_profile is None:
            self.fail("shared RF profile did not parse")
        self.assertEqual(shared_profile["frequency_mhz"], 915.0)
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

    def test_wrapper_host_compile_uses_effective_platformio_profile(self) -> None:
        flags = rf_proof.radio_profile_compile_flags(effective_platformio_config())
        self.assertEqual(flags, ["-DLORA_ROLE_SENDER=1"])

    def test_host_test_stage_uses_only_checked_in_sources(self) -> None:
        class RecordingProof:
            def __init__(self, run_dir: Path) -> None:
                self.run_dir = run_dir
                self.commands: list[tuple[str, list[str]]] = []

            def command(
                self, name: str, argv: list[str], *args: Any, **kwargs: Any
            ) -> tuple[int, bytes, bytes]:
                self.commands.append((name, list(argv)))
                missing = [
                    arg
                    for arg in argv
                    if arg.endswith((".cpp", ".c"))
                    and not (dynamic_attr("ROOT") / arg).is_file()
                ]
                if missing:
                    return 1, b"", f"missing source: {missing[0]}".encode()
                return 0, b"PASS 1 checks", b"Ran 1 tests"

        with tempfile.TemporaryDirectory() as directory:
            proof: Any = RecordingProof(Path(directory))
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

    def test_effective_upload_flags_and_ports_are_checked(self) -> None:
        config = effective_platformio_config()
        preserves = dynamic_attr("upload_config_preserves_flash")
        ports_match = dynamic_attr("upload_ports_match")
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

    def test_rf_enabled_upload_programs_receiver_before_boot_campaign_sender(self) -> None:
        class RecordingProof:
            def __init__(self) -> None:
                self.commands: list[Any] = []
                self.notes: list[Any] = []

            def command(
                self, name: str, argv: list[str], *args: Any, **kwargs: Any
            ) -> tuple[int, bytes, bytes]:
                self.commands.append((name, argv))
                return 0, b"", b""

            def note(self, _name: str, message: str) -> None:
                self.notes.append(message)

        proof: Any = RecordingProof()
        args: Any = SimpleNamespace(
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

    def test_rf_enabled_upload_does_not_require_rf_authorization(self) -> None:
        class RecordingProof:
            def __init__(self) -> None:
                self.commands: list[Any] = []
                self.notes: list[Any] = []

            def command(
                self, name: str, argv: list[str], *args: Any, **kwargs: Any
            ) -> tuple[int, bytes, bytes]:
                self.commands.append((name, argv))
                return 0, b"", b""

            def note(self, _name: str, message: str) -> None:
                self.notes.append(message)

        proof: Any = RecordingProof()
        args: Any = SimpleNamespace(
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

    def test_hardware_blockers_only_represent_physical_and_action_gates(self) -> None:
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

    def test_radio_spi_log_requires_version_and_diagnostic_only_marker(self) -> None:
        parser = dynamic_attr("parse_radio_spi_log")
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

    def test_radio_spi_capture_reads_bounded_updi_log_stream(self) -> None:
        class Proof:
            run_dir = Path()

        def start_monitor(
            _proof: Any, role: str, _port: str, output_queue: Any
        ) -> object:
            output_queue.put((role, "stdout", b"[GATEWAY] RADIO_SPI_VERSION=0x12\r\n"))
            output_queue.put((role, "stdout", b"[GATEWAY] RF_TX_DISABLED_DIAGNOSTIC\r\n"))
            return object()

        with (
            patch.object(rf_proof, "start_rf_monitor", side_effect=start_monitor),
            patch.object(rf_proof, "stop_rf_monitor", return_value=0),
        ):
            proof: Any = Proof()
            evidence = rf_proof.capture_radio_spi_log(
                proof, "GATEWAY", "/dev/serial/by-path/gateway"
            )
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["version"], 0x12)
        self.assertEqual(len(evidence["log_lines"]), 2)

    def test_spi_smoke_stage_refuses_non_diagnostic_builds_before_commands(self) -> None:
        class Proof:
            commands: list[Any] = []
            notes: list[Any] = []

            def command(self, *args: Any, **kwargs: Any) -> Never:
                self.commands.append((args, kwargs))
                msg = "unsafe config must block before hardware commands"
                raise AssertionError(msg)

            def note(self, _name: str, value: Any) -> None:
                self.notes.append(value)

        proof: Any = Proof()
        args: Any = SimpleNamespace(
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

    def test_spi_smoke_uploads_receiver_then_rf_disabled_diagnostic_sender(self) -> None:
        class RecordingProof:
            def __init__(self, run_dir: str) -> None:
                self.run_dir = Path(run_dir)
                self.commands: list[Any] = []
                self.notes: list[Any] = []

            def command(
                self, name: str, argv: list[str], *args: Any, **kwargs: Any
            ) -> tuple[int, bytes, bytes]:
                self.commands.append((name, argv))
                return 0, b"", b""

            def note(self, _name: str, message: str) -> None:
                self.notes.append(message)

        with tempfile.TemporaryDirectory() as run_dir:
            proof: Any = RecordingProof(run_dir)
            args: Any = SimpleNamespace(
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

    def test_preflight_reports_missing_stable_adapter_paths(self) -> None:
        self.assertEqual(
            unresolved_adapter_paths([("gateway", 0), ("receiver", 1)]),
            ["receiver adapter path"],
        )

    def test_usb_topology_capture_records_read_only_inventory_commands(self) -> None:
        class RecordingProof:
            def __init__(self) -> None:
                self.commands: list[tuple[str, list[str]]] = []

            def command(self, name: str, argv: list[str]) -> tuple[int, bytes, bytes]:
                self.commands.append((name, argv))
                return 0, b"", b""

        proof: Any = RecordingProof()
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

    def test_test_counts_parse_protocol_stdout_and_unittest_stderr(self) -> None:
        self.assertEqual(
            parse_test_counts(b"PASS 142 checks\n", b"Ran 3 tests in 0.001s\n"),
            (142, 3),
        )

    def test_hardware_stages_list_unverified_setup_and_missing_authorization(self) -> None:
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

    def test_rf_test_requires_separate_authorization(self) -> None:
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

    def test_stage_unblocks_only_when_every_gate_is_explicit(self) -> None:
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

    def test_only_fuser_exit_one_means_port_is_clear(self) -> None:
        checker = dynamic_attr("unavailable_ports")
        self.assertTrue(callable(checker), "serial ownership preflight is required")
        self.assertEqual(
            checker([("gateway", 1), ("receiver", 0), ("unknown", 2)]),
            ["receiver", "unknown"],
        )

    def test_role_log_test_count_is_parsed_from_its_actual_result_line(self) -> None:
        parser = dynamic_attr("parse_role_log_count")
        self.assertTrue(callable(parser), "role-log proof count parser is required")
        self.assertEqual(parser(b"PASS 4 role-log checks\n"), 4)
        self.assertIsNone(parser(b"no test summary\n"))

    def test_radio_wrapper_test_count_is_parsed_from_its_actual_result_line(self) -> None:
        parser = dynamic_attr("parse_wrapper_check_count")
        self.assertTrue(callable(parser), "radio-wrapper proof count parser is required")
        self.assertEqual(parser(b"PASS 24 radio-wrapper checks\n"), 24)
        self.assertIsNone(parser(b"no test summary\n"))

    def test_serialupdi_upload_config_disables_chip_erase_without_fuse_writes(self) -> None:
        checker = dynamic_attr("upload_config_preserves_flash")
        self.assertTrue(callable(checker), "safe serialupdi upload config check is required")
        self.assertTrue(checker("[env]\nupload_flags = -D\n"))
        self.assertFalse(checker("[env]\nupload_flags = -e\n"))
        self.assertFalse(checker("[env]\nupload_flags = -D -U lfuse:w:0x00:m\n"))

    def test_repository_upload_config_preserves_flash_and_fuses(self) -> None:
        config = (Path(__file__).resolve().parents[1] / "platformio.ini").read_text()
        self.assertTrue(rf_proof.upload_config_preserves_flash(config))


class RfEvidenceTests(unittest.TestCase):
    def parser(self) -> Any:
        parser = dynamic_attr("parse_rf_campaign")
        self.assertTrue(callable(parser), "campaign evidence parser is required")
        return parser

    def test_preflight_is_proven_before_campaign_continuation(self) -> None:
        gateway, receiver = complete_campaign_logs(stop_after_preflight=True)
        evidence = self.parser()(gateway, receiver)
        self.assertTrue(evidence["preflight_complete"])
        self.assertEqual(evidence["issues"], [])
        self.assertFalse(evidence["continued"])
        self.assertFalse(evidence["passed"])

    def test_single_packet_acceptance_rejects_a_retried_data_frame(self) -> None:
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

    def test_campaign_requires_all_correlated_data_and_ack_events(self) -> None:
        gateway, receiver = complete_campaign_logs(omit_final_ack=True)
        evidence = self.parser()(gateway, receiver)
        self.assertFalse(evidence["passed"])
        self.assertEqual(evidence["delivery_sequences"], list(range(1, 20)))
        self.assertEqual(evidence["missing_sequences"], [20])

    def test_campaign_requires_payload_validation_for_every_sequence(self) -> None:
        gateway, receiver = complete_campaign_logs()
        receiver = receiver.replace(packet_event("RECEIVER", "PAYLOAD_MATCH", 0x1234, 7) + "\n", "")
        evidence = self.parser()(gateway, receiver)
        self.assertFalse(evidence["passed"])
        self.assertNotIn(7, evidence["delivery_sequences"])
        self.assertIn(7, evidence["missing_sequences"])

    def test_campaign_requires_exact_first_payload_bytes_on_both_sides(self) -> None:
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

    def test_campaign_reports_attempts_duplicates_timeouts_and_rtt(self) -> None:
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

    def test_mixed_campaign_ids_cannot_be_counted_as_one_success(self) -> None:
        gateway, receiver = complete_campaign_logs()
        receiver += "\n" + packet_event("RECEIVER", "DATA_RX", 0x9999, 1)
        evidence = self.parser()(gateway, receiver)
        self.assertFalse(evidence["passed"])
        self.assertIn("multiple campaign IDs", evidence["issues"])

    def test_sender_no_longer_uses_the_removed_eeprom_campaign_gate(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "src/sender/lib/lora_rx.cpp").read_text()
        self.assertNotIn("EEPROM", source)
        self.assertNotIn("CampaignBuildGateResult", source)
        self.assertIn("lora_rx_start_lora", source)


class RfTestContinuationTests(unittest.TestCase):
    def test_rf_test_blocks_without_verified_upload_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof: Any = SimpleNamespace(run_dir=Path(directory), note=lambda *_: None)
            args: Any = SimpleNamespace(
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
    def test_no_meter_identity_uses_live_unique_serial_without_checklist(self) -> None:
        backup = json.loads((dynamic_attr("ROOT") / "config/current_hardware.json").read_text())
        for wrong_serial in (False, True):
            with (
                self.subTest(wrong_serial=wrong_serial),
                tempfile.TemporaryDirectory() as directory,
            ):
                commands: list[Any] = []
                proof: Any = SimpleNamespace(run_dir=Path(directory), note=lambda *_: None)

                def command(
                    name: str,
                    argv: list[str],
                    *unused: Any,
                    commands: list[Any] = commands,
                    wrong_serial: bool = wrong_serial,
                ) -> tuple[int, Any, Any]:
                    commands.append(argv)
                    if argv[0] == "fuser":
                        return 1, "", ""
                    if "-U" in argv:
                        self.assertIn("-N", argv)
                        role = "receiver" if "receiver" in name else "gateway"
                        original = backup[role]
                        memories = {
                            "bootsize": bytes.fromhex(original["fuses_hex"])[8:9],
                            "codesize": b"\0",
                            "bodcfg": bytes.fromhex(original["fuses_hex"])[1:2],
                            "signature": bytes.fromhex("1e970a"),
                            "sernum": bytes(16)
                            if wrong_serial
                            else bytes.fromhex(original["device_serial_hex"]),
                        }
                        for i, value in enumerate(argv):
                            if value == "-U":
                                memory, mode, path, _encoding = argv[i + 1].split(":")
                                self.assertEqual(mode, "r")
                                Path(path).write_bytes(memories[memory])
                    return 0, "live response", ""

                proof.command = command
                args: Any = SimpleNamespace(
                    no_meter_mode=True, physical_mapping_verified=True, power_verified=True
                )
                with patch.object(
                    rf_proof,
                    "target_fuses",
                    return_value={"bootsize": 0, "codesize": 0, "bodcfg": 0},
                ):
                    self.assertEqual(
                        rf_proof.identify_targets(proof, args, effective_platformio_config()),
                        2 if wrong_serial else 0,
                    )
                self.assertTrue(any("-U" in argv for argv in commands))
                self.assertTrue(args.no_meter_mode)

    def test_no_meter_retains_authorization_and_boot_gates(self) -> None:
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

    def test_no_meter_does_not_skip_rf_hardware_suitability(self) -> None:
        args: Any = SimpleNamespace(
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

    def test_no_meter_does_not_bypass_mapping_or_electrical_safety(self) -> None:
        for key in ("physical_mapping_verified", "power_verified"):
            with self.subTest(key=key):
                args: Any = SimpleNamespace(
                    no_meter_mode=True, physical_mapping_verified=True, power_verified=True
                )
                setattr(args, key, False)
                proof: Any = SimpleNamespace(
                    note=lambda *_: None,
                    command=lambda *_: self.fail("unsafe target must not be accessed"),
                )
                self.assertTrue(rf_proof.physical_readiness_errors(args))
                self.assertEqual(rf_proof.identify_targets(proof, args), 2)

    def test_intel_hex_parser_checks_checksum_and_address_range(self) -> None:
        parser = dynamic_attr("parse_ihex_range")
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

    def test_application_link_origins_follow_each_targets_live_boot_fuse(self) -> None:
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

    def test_firmware_hex_must_fit_only_inside_generated_appcode(self) -> None:
        checker = dynamic_attr("image_fits_application")
        self.assertTrue(callable(checker), "BOOT-overwrite range check is required")
        gateway_bounds = (0x00000, 0x1FC00)
        receiver_bounds = (0x05800, 0x1FC00)
        self.assertTrue(checker({"start": 0x00000, "end_exclusive": 0x9000}, gateway_bounds))
        self.assertFalse(checker({"start": 0x04000, "end_exclusive": 0x9000}, gateway_bounds))
        self.assertTrue(checker({"start": 0x05800, "end_exclusive": 0xC000}, receiver_bounds))
        self.assertFalse(checker({"start": 0x04000, "end_exclusive": 0x9000}, receiver_bounds))
        self.assertFalse(checker({"start": 0x05800, "end_exclusive": 0x20000}, receiver_bounds))

    def test_target_boot_and_bod_fuses_match_their_live_layouts(self) -> None:
        parse_fuses = dynamic_attr("target_fuses")
        compare_fuses = dynamic_attr("boot_fuses_match")
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

    def test_target_identification_opens_no_port_without_physical_gates(self) -> None:
        class Proof:
            commands = 0
            notes: list[Any] = []

            def command(self, *args: Any, **kwargs: Any) -> Never:
                self.commands += 1
                msg = "serial command must remain blocked"
                raise AssertionError(msg)

            def note(self, _name: str, value: Any) -> None:
                self.notes.append(value)

        for mapping, power in ((False, False), (True, False), (False, True)):
            proof: Any = Proof()
            args: Any = SimpleNamespace(
                physical_mapping_verified=mapping,
                power_verified=power,
            )
            self.assertEqual(rf_proof.identify_targets(proof, args), 2)
            self.assertEqual(proof.commands, 0)
            self.assertIn("no serial ports opened", proof.notes[-1])


if __name__ == "__main__":
    unittest.main()
