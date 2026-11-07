import copy
import json
from pathlib import Path
import sys
import unittest
import tempfile
import subprocess
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/config'))


class ConfigurationTests(unittest.TestCase):
    def test_candidate_and_invalid_profiles(self):
        from validate_lora_ssot import load, validate
        config = load(Path('config/lora_system.json'))
        for section, key, value in [('radio', 'spreading_factor', 8),
                                    ('radio', 'tx_power_dbm', True),
                                    ('receiver_board', 'image_start', 0),
                                    ('protocol', 'payload', 'wrong')]:
            changed = copy.deepcopy(config)
            changed[section][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(changed)

    def test_duplicate_keys(self):
        from validate_lora_ssot import unique_object
        with self.assertRaises(ValueError):
            json.loads('{"sf":7,"sf":8}', object_pairs_hook=unique_object)

    def test_identity_requires_exact_unique_hash_and_protocol(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
        from rf_proof import shared_identity_matches
        fingerprint = 'a' * 64
        logs = {role: f'[{role}] CONFIG_FINGERPRINT={fingerprint}\n[{role}] PROTOCOL_VERSION=1'
                for role in ('GATEWAY', 'RECEIVER')}
        self.assertTrue(shared_identity_matches(logs, fingerprint, 1))
        for invalid in ('', logs['RECEIVER'] + '\n' + logs['RECEIVER'],
                        logs['RECEIVER'].replace(fingerprint, 'b' * 64),
                        logs['RECEIVER'].replace('VERSION=1', 'VERSION=2')):
            self.assertFalse(shared_identity_matches(dict(logs, RECEIVER=invalid), fingerprint, 1))

    def test_generation_is_deterministic_and_board_independent(self):
        from validate_lora_ssot import load
        from generate_lora_config import artifacts
        config = load(Path('config/lora_system.json'))
        self.assertEqual(artifacts(config), artifacts(config))
        manifest = json.loads(artifacts(config)['generated/lora_manifest.json'])
        self.assertEqual(len(manifest['shared_fingerprint']), 64)
        self.assertNotEqual(manifest['boards']['sender']['build_fingerprint'],
                            manifest['boards']['receiver']['build_fingerprint'])

    def test_receiver_pin_and_shared_radio_changes_have_correct_scope(self):
        from validate_lora_ssot import load, validate
        from generate_lora_config import artifacts
        config = load(Path('config/lora_system.json'))
        original = artifacts(config)
        config['receiver_board']['pins']['dio1'] = 'PD4'
        changed = artifacts(validate(config))
        self.assertEqual(original['include/generated/lora_sender_board.h'], changed['include/generated/lora_sender_board.h'])
        self.assertNotEqual(original['include/generated/lora_receiver_board.h'], changed['include/generated/lora_receiver_board.h'])
        before_ids = json.loads(original['generated/lora_manifest.json'])['environments']
        after_ids = json.loads(changed['generated/lora_manifest.json'])['environments']
        for environment in before_ids:
            if environment.startswith('receiver'):
                self.assertNotEqual(before_ids[environment], after_ids[environment])
            else:
                self.assertEqual(before_ids[environment], after_ids[environment])
        self.assertEqual(json.loads(original['generated/lora_manifest.json'])['shared_fingerprint'],
                         json.loads(changed['generated/lora_manifest.json'])['shared_fingerprint'])
        config['radio']['frequency_mhz'] = 924.0
        radio = artifacts(validate(config))
        for role in ('sender', 'receiver'):
            self.assertNotEqual(changed[f'include/generated/lora_{role}_board.h'], radio[f'include/generated/lora_{role}_board.h'])
        self.assertIn('924.0f', radio['include/generated/lora_shared_config.h'])

    def test_missing_unknown_types_ranges_and_sf8_through_sf12(self):
        from validate_lora_ssot import load, validate
        config = load(Path('config/lora_system.json'))
        cases = [('radio', 'spreading_factor', sf) for sf in range(8,13)]
        cases += [('radio', 'frequency_mhz', float('nan')), ('radio', 'tx_power_dbm', 21),
                  ('timeouts', 'ack_ms', 0), ('retries', 'max_retries', 4),
                  ('sender_board', 'bootsize', 44), ('receiver_board', 'image_end_exclusive', 999999)]
        for section, key, value in cases:
            changed = copy.deepcopy(config)
            changed[section][key] = value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                validate(changed)
        for pin in ('PA5', 'PD3', 'PC8'):
            changed = copy.deepcopy(config)
            changed['receiver_board']['pins']['dio1'] = pin
            with self.assertRaises(ValueError):
                validate(changed)
        changed = copy.deepcopy(config)
        del changed['radio']['sync_word']
        with self.assertRaises(ValueError):
            validate(changed)

    def test_generator_check_rejects_stale_artifact(self):
        import generate_lora_config as generator
        config = Path('config/lora_system.json').read_text()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'config').mkdir()
            (root/'config/lora_system.json').write_text(config)
            with patch.object(generator, 'ROOT', root):
                generator.generate()
                generator.generate(check=True)
                (root/'include/generated/lora_shared_config.h').write_text('stale')
                with self.assertRaises(ValueError):
                    generator.generate(check=True)

    def test_conflicting_compile_macro_is_rejected(self):
        result = subprocess.run(['g++', '-std=c++11', '-x', 'c++', '-fsyntax-only',
            '-DHELLO_RF_SPREADING_FACTOR=12', '-'], input='#include "include/generated/lora_shared_config.h"\n',
            text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Conflicting SPREADING_FACTOR', result.stderr)
