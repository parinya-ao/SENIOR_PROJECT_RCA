import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/config"))


class ConfigurationTests(unittest.TestCase):
    def test_protocol_and_board_configuration_rejects_invalid_or_radio_fields(self) -> None:
        from tools.config.validate_lora_ssot import load, validate

        config = load(ROOT / "config/lora_system.json")
        self.assertNotIn("radio", config)
        self.assertNotIn("spi_route", config["sender_board"])
        for section, key, value in (
            ("protocol", "payload", "wrong"),
            ("receiver_board", "image_start", 22528),
            ("sender_board", "bootsize", 44),
        ):
            changed = copy.deepcopy(config)
            changed[section][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(changed)
        changed = copy.deepcopy(config)
        changed["radio"] = {}
        with self.assertRaises(ValueError):
            validate(changed)

    def test_duplicate_keys(self) -> None:
        from tools.config.validate_lora_ssot import unique_object

        with self.assertRaises(ValueError):
            json.loads('{"sf":7,"sf":8}', object_pairs_hook=unique_object)

    def test_identity_requires_exact_unique_hash_and_protocol(self) -> None:
        sys.path.insert(0, str(ROOT / "tools"))
        from tools.rf_proof import shared_identity_matches

        fingerprint = "a" * 64
        logs = {
            role: f"[{role}] CONFIG_FINGERPRINT={fingerprint}\n[{role}] PROTOCOL_VERSION=1"
            for role in ("GATEWAY", "RECEIVER")
        }
        self.assertTrue(shared_identity_matches(logs, fingerprint, 1))
        for invalid in (
            "",
            logs["RECEIVER"] + "\n" + logs["RECEIVER"],
            logs["RECEIVER"].replace(fingerprint, "b" * 64),
            logs["RECEIVER"].replace("VERSION=1", "VERSION=2"),
        ):
            self.assertFalse(shared_identity_matches(dict(logs, RECEIVER=invalid), fingerprint, 1))

    def test_generation_is_deterministic_and_check_rejects_missing_or_stale_artifacts(self) -> None:
        import tools.config.generate_lora_config as generator
        from tools.config import validate_lora_ssot

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
                config = validate_lora_ssot.load(root / "config/lora_system.json")
                radio = generator.load_radio_profile(root / "config/radio_915.toml")
                self.assertEqual(
                    generator.artifacts(config, radio), generator.artifacts(config, radio)
                )
                generator.generate()
                generator.generate(check=True)
                path = root / "include/generated/radio_915_config.h"
                self.assertIn("HELLO_RF_FREQUENCY_MHZ 915.0f", path.read_text())
                path.write_text("stale\n")
                with self.assertRaises(ValueError):
                    generator.generate(check=True)
                path.unlink()
                with self.assertRaises(ValueError):
                    generator.generate(check=True)


if __name__ == "__main__":
    unittest.main()
