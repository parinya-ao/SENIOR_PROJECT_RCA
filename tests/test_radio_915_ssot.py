import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/config"))


def valid_profile():
    return {
        "schema_version": 1,
        "radio": {
            "frequency_hz": 915_000_000,
            "bandwidth_khz": 125,
            "spreading_factor": 7,
            "coding_rate": 5,
            "sync_word": 0x12,
            "tx_power_dbm": 2,
            "preamble_symbols": 8,
            "crc_enabled": True,
            "explicit_header": True,
            "iq_inverted": False,
            "current_limit_ma": 200,
            "automatic_gain": 0,
            "long_range": 0,
        },
        "sender": {
            "spi_route": "SPI1_SWAP_DEFAULT",
            "pins": {
                "mosi": "PC0",
                "miso": "PC1",
                "sck": "PC2",
                "cs": "PC3",
                "rst": "PD0",
                "irq": "PD2",
                "dio1": "PD3",
            },
        },
        "receiver": {
            "spi_route": "SPI1_SWAP_DEFAULT",
            "radio_power_active_level": 0,
            "pins": {
                "mosi": "PC0",
                "miso": "PC1",
                "sck": "PC2",
                "cs": "PD0",
                "rst": "PD1",
                "irq": "PD3",
                "dio1": "PD2",
                "enable": "PA7",
            },
        },
        "environments": {
            "sender": ["sender", "sender_hello", "sender_hello_spi", "sender_mvp"],
            "receiver": ["receiver", "receiver_spi", "receiver_mvp"],
        },
    }


def write_toml(path, profile) -> None:
    # These tests mutate parsed structures; use the project's canonical TOML
    # document for syntax tests and validate dictionaries for focused cases.
    path.write_text((ROOT / "config/radio_915.toml").read_text())


class Radio915ValidationTests(unittest.TestCase):
    def test_toml_loads_and_duplicate_or_malformed_syntax_is_rejected(self) -> None:
        import generate_lora_config as generator

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "radio.toml"
            path.write_text((ROOT / "config/radio_915.toml").read_text())
            self.assertEqual(
                generator.load_radio_profile(path)["radio"]["frequency_hz"], 915_000_000
            )
            path.write_text("[radio]\nfrequency_hz = 915000000\nfrequency_hz = 915000000\n")
            with self.assertRaises(ValueError):
                generator.load_radio_profile(path)
            path.write_text("[radio\nfrequency_hz = 915000000\n")
            with self.assertRaises(ValueError):
                generator.load_radio_profile(path)

    def test_strict_schema_frequency_and_rf_invariants(self) -> None:
        from generate_lora_config import validate_radio_profile

        base = valid_profile()
        cases = []
        for section, key in (
            ("radio", "frequency_hz"),
            ("radio", "bandwidth_khz"),
            ("radio", "spreading_factor"),
            ("radio", "coding_rate"),
            ("radio", "sync_word"),
            ("radio", "tx_power_dbm"),
            ("radio", "preamble_symbols"),
            ("radio", "crc_enabled"),
            ("radio", "explicit_header"),
            ("radio", "iq_inverted"),
            ("radio", "current_limit_ma"),
            ("radio", "automatic_gain"),
            ("radio", "long_range"),
        ):
            altered = copy.deepcopy(base)
            altered[section].pop(key)
            cases.append(altered)
        for bad_frequency in (915_000_000.0, True, 923_000_000, 914_999_999):
            altered = copy.deepcopy(base)
            altered["radio"]["frequency_hz"] = bad_frequency
            cases.append(altered)
        for section, key, value in (
            ("radio", "bandwidth_khz", 250),
            ("radio", "spreading_factor", 8),
            ("radio", "coding_rate", 8),
            ("radio", "sync_word", 0x34),
            ("radio", "tx_power_dbm", 14),
            ("radio", "preamble_symbols", 10),
            ("radio", "crc_enabled", False),
            ("radio", "explicit_header", False),
            ("radio", "iq_inverted", True),
            ("radio", "current_limit_ma", 190),
            ("radio", "automatic_gain", 2),
            ("radio", "long_range", 1),
        ):
            altered = copy.deepcopy(base)
            altered[section][key] = value
            cases.append(altered)
        unknown = copy.deepcopy(base)
        unknown["radio"]["future_option"] = 1
        cases.append(unknown)
        unknown = copy.deepcopy(base)
        unknown["future_section"] = {}
        cases.append(unknown)
        for altered in cases:
            with self.subTest(profile=altered), self.assertRaises(ValueError):
                validate_radio_profile(altered)

    def test_role_pin_maps_collisions_and_environment_mapping_are_strict(self) -> None:
        from generate_lora_config import validate_radio_profile

        base = valid_profile()
        for section, change in (
            ("sender", lambda item: item["pins"].update(cs="PC2")),
            ("receiver", lambda item: item["pins"].update(enable="PA6")),
            ("sender", lambda item: item["pins"].update(extra="PD4")),
            ("receiver", lambda item: item["pins"].pop("dio1")),
            ("receiver", lambda item: item.update(spi_route="SPI1_DEFAULT")),
        ):
            altered = copy.deepcopy(base)
            change(altered[section])
            with self.subTest(section=section), self.assertRaises(ValueError):
                validate_radio_profile(altered)
        for environments in (
            {"sender": ["sender", "sender_hello"], "receiver": ["receiver", "receiver_spi"]},
            {
                "sender": ["sender", "sender", "sender_hello_spi"],
                "receiver": ["receiver", "receiver_spi"],
            },
            {
                "sender": ["sender", "sender_hello", "receiver_spi"],
                "receiver": ["receiver", "sender_hello_spi"],
            },
            {"sender": ["sender", "sender_hello", "sender_hello_spi"], "receiver": ["receiver"]},
        ):
            altered = copy.deepcopy(base)
            altered["environments"] = environments
            with self.subTest(environments=environments), self.assertRaises(ValueError):
                validate_radio_profile(altered)

    def test_generation_is_deterministic_check_detects_missing_stale_and_atomic_writes(self) -> None:
        import generate_lora_config as generator
        import validate_lora_ssot

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            (root / "config").mkdir(parents=True)
            (root / "config/lora_system.json").write_text(
                (ROOT / "config/lora_system.json").read_text()
            )
            (root / "config/radio_915.toml").write_text(
                (ROOT / "config/radio_915.toml").read_text()
            )
            with (
                patch.object(generator, "ROOT", root),
                patch.object(validate_lora_ssot, "ROOT", root),
            ):
                outputs = generator.artifacts(
                    validate_lora_ssot.load(root / "config/lora_system.json"),
                    generator.load_radio_profile(root / "config/radio_915.toml"),
                )
                self.assertEqual(
                    outputs,
                    generator.artifacts(
                        validate_lora_ssot.load(root / "config/lora_system.json"),
                        generator.load_radio_profile(root / "config/radio_915.toml"),
                    ),
                )
                generator.generate()
                generator.generate(check=True)
                header = root / "include/generated/radio_915_config.h"
                before = header.stat().st_mtime_ns
                generator.generate()
                self.assertEqual(header.stat().st_mtime_ns, before)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    list(pool.map(lambda _: generator.generate(), range(2)))
                generator.generate(check=True)
                header.unlink()
                with self.assertRaises(ValueError):
                    generator.generate(check=True)
                generator.generate()
                header.write_text("stale\n")
                with self.assertRaises(ValueError):
                    generator.generate(check=True)
                self.assertEqual(list(header.parent.glob("*.tmp")), [])

    def test_generated_host_profile_matches_header_and_role_header_compiles(self) -> None:
        import generate_lora_config as generator

        generator.generate(check=True)
        profile = json.loads((ROOT / "generated/lora_manifest.json").read_text())["shared"]["radio"]
        self.assertEqual(profile["tx_power_dbm"], 2)
        namespace = {}
        exec((ROOT / "generated/radio_915_profile.py").read_text(), namespace)
        self.assertEqual(namespace["FREQUENCY_HZ"], 915_000_000)
        self.assertEqual(namespace["FREQUENCY_MHZ"], profile["frequency_mhz"])
        self.assertEqual(namespace["TX_POWER_DBM"], profile["tx_power_dbm"])
        header = (ROOT / "include/generated/radio_915_config.h").read_text()
        self.assertIn("#if (defined(LORA_ROLE_SENDER) + defined(LORA_ROLE_RECEIVER)) != 1", header)
        self.assertIn("#if defined(LORA_ROLE_SENDER)", header)
        self.assertIn("#elif defined(LORA_ROLE_RECEIVER)", header)
        compiler = (
            shutil.which("avr-g++")
            or Path.home() / ".platformio/packages/toolchain-atmelavr/bin/avr-g++"
        )
        if not Path(compiler).is_file():
            self.skipTest("AVR C++ compiler unavailable")
        for role in ("SENDER", "RECEIVER"):
            result = subprocess.run(
                [
                    str(compiler),
                    "-std=c++11",
                    "-fsyntax-only",
                    "-x",
                    "c++",
                    "-I",
                    str(ROOT),
                    f"-DLORA_ROLE_{role}=1",
                    "-",
                ],
                input='#include "include/generated/radio_915_config.h"\n',
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        for roles in ([], ["-DLORA_ROLE_SENDER=1", "-DLORA_ROLE_RECEIVER=1"]):
            result = subprocess.run(
                [
                    str(compiler),
                    "-std=c++11",
                    "-fsyntax-only",
                    "-x",
                    "c++",
                    "-I",
                    str(ROOT),
                    *roles,
                    "-",
                ],
                input='#include "include/generated/radio_915_config.h"\n',
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_cli_validate_and_check_cover_the_radio_profile(self) -> None:
        for option in ("--validate", "--check"):
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools/config/generate_lora_config.py"), option],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_power_candidate_requires_five_dbm_and_its_own_config_identity(self) -> None:
        compiler = shutil.which("g++") or shutil.which("clang++") or shutil.which("clang")
        if compiler is None:
            self.skipTest("host C++ compiler unavailable")
        for power, identity, valid in (
            (5, True, True),
            (5, False, False),
            (2, True, False),
            (3, True, False),
            (20, True, False),
        ):
            with self.subTest(power=power, identity=identity):
                flags = [f"-DLORA_TEST_TX_POWER_DBM={power}"]
                if identity:
                    flags.append('-DLORA_TEST_CONFIG_FINGERPRINT="candidate"')
                result = subprocess.run(
                    [
                        compiler,
                        "-std=c++11",
                        "-fsyntax-only",
                        "-x",
                        "c++",
                        "-I",
                        str(ROOT),
                        "-DLORA_ROLE_SENDER=1",
                        *flags,
                        "-",
                    ],
                    input='#include "src/shared/hello_config.h"\n'
                    'static_assert(HELLO_RF_TX_POWER_DBM == 5, "candidate power");\n',
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode == 0, valid, result.stderr)

    def test_gateway_mainboards_send_profile_but_keep_address_and_eight_byte_wire_shape(self) -> None:
        import generate_lora_config as generator

        generator.generate(check=True)
        for relative in ("gateway-lora/mainboard/src", "gateway-lora_dev/mainboard/src"):
            directory = ROOT.parent / "iwing-tracker" / relative
            profile_source = (directory / "radio_915_profile.py").read_text()
            loraboard = (directory / "loraboard.py").read_text()
            main = (directory / "main.py").read_text()
            config = (directory / "config.txt").read_text()
            self.assertEqual(profile_source, (ROOT / "generated/radio_915_profile.py").read_text())
            self.assertIn('CONFIG_LORA_STRUCT_FMT = "<BfbB"', loraboard)
            self.assertIn("def configure(self, addr):", loraboard)
            self.assertRegex(main, r"b\.configure\(\s*loraboards_config\['address'\]\s*\)")
            for field in ('"frequency"', '"tx_power"', '"long_range"'):
                self.assertNotIn(field, config)
                self.assertNotIn(field, loraboard)


class I2cRadioConfigTests(unittest.TestCase):
    def test_only_exact_profile_command_initializes_and_address_is_preserved(self) -> None:
        compiler = shutil.which("g++") or shutil.which("clang++")
        if compiler is None:
            self.skipTest(
                "host C++ compiler unavailable; PlatformIO builds cover firmware compilation"
            )
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "radio_config_test"
            result = subprocess.run(
                [
                    compiler,
                    "-std=c++11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(ROOT),
                    "-DLORA_ROLE_SENDER=1",
                    str(ROOT / "tests/radio_config_test.cpp"),
                    "-o",
                    str(binary),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
