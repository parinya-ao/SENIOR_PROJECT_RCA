import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/config"))


class ReceiverHardwareTests(unittest.TestCase):
    def test_receiver_configuration_matches_rfm_rev1_and_keeps_gateway_separate(self) -> None:
        config = json.loads((ROOT / "config/lora_system.json").read_text())
        from tools.config.generate_lora_config import load_radio_profile

        radio = load_radio_profile()
        self.assertEqual(
            radio["receiver"]["pins"],
            {
                "mosi": "PC0",
                "miso": "PC1",
                "sck": "PC2",
                "cs": "PD0",
                "rst": "PD1",
                "irq": "PD3",
                "dio1": "PD2",
                "enable": "PA7",
            },
        )
        self.assertEqual(
            config["receiver_board"]["pins"],
            {
                "sd_cs": "PC3",
                "led1": "PA6",
                "led2": "PA5",
                "gps_enable": "PD5",
                "sd_enable": "PD6",
                "sd_detect": "PA4",
            },
        )
        self.assertEqual(radio["receiver"]["radio_power_active_level"], 0)
        self.assertEqual(
            radio["sender"]["pins"],
            {
                "mosi": "PC0",
                "miso": "PC1",
                "sck": "PC2",
                "cs": "PC3",
                "rst": "PD0",
                "irq": "PD2",
                "dio1": "PD3",
            },
        )

    def test_validator_accepts_receiver_hardware_without_relaxing_gateway_spi(self) -> None:
        from tools.config.validate_lora_ssot import validate

        config = json.loads((ROOT / "config/lora_system.json").read_text())
        error = None
        try:
            validate(config)
        except ValueError as exc:
            error = str(exc)
        self.assertIsNone(error, error)
        for section, pin, value in [
            ("receiver_board", "sd_cs", "PA6"),
            ("receiver_board", "enable", "PA6"),
        ]:
            changed = copy.deepcopy(config)
            changed[section]["pins"][pin] = value
            with self.subTest(section=section, pin=pin), self.assertRaises(ValueError):
                validate(changed)

    def test_gpio_powers_radio_before_spi_without_touching_sd_or_reset(self) -> None:
        # Compile the actual static GPIO function, replacing only Arduino I/O.
        source = (ROOT / "src/receiver/main.cpp").read_text()
        first = source.index("static void InitializeReceiverGpio()")
        last = source.index("\nvoid setup()", first)
        aliases = "\n".join(
            line
            for line in source[:first].splitlines()
            if line.startswith(("#define PIN_", "#define LED"))
        )
        fixture = (
            '#include "include/application_config.h"\n'
            '#include "include/generated/lora_receiver_board.h"\n'
            '#include "include/generated/radio_915_config.h"\n'
            + aliases
            + "\n"
            + source[first:last]
        )
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            (directory_path / "receiver_gpio_under_test.h").write_text(fixture)
            binary = directory_path / "receiver_gpio_test"
            result = subprocess.run(
                [
                    "clang",
                    "--driver-mode=g++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I" + str(ROOT),
                    "-I" + str(directory),
                    "-DLORA_ROLE_RECEIVER=1",
                    str(ROOT / "tests/receiver_gpio_test.cpp"),
                    "-o",
                    str(binary),
                ],
                capture_output=True,
                text=True,
            check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
