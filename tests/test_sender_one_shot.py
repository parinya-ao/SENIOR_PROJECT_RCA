from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import rf_proof
from test_rf_proof import effective_platformio_config


class SenderOneShotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        directory = Path(cls.directory.name)
        source = (ROOT / 'src/sender/lib/lora_rx.cpp').read_text()
        enum_start = source.index('enum class CampaignBuildGateResult')
        enum_end = source.index('};', enum_start) + 2
        first = source.index('static CampaignBuildGateResult claim_campaign_build()')
        last = source.index('\n}\n', first) + 3
        address = next(line for line in source.splitlines()
                       if line.startswith('static constexpr int kCampaignBuildMarkerAddress'))
        # Compile the actual gate; only the physical EEPROM boundary is replaced.
        (directory / 'sender_guard_under_test.h').write_text(
            address + '\n' + source[enum_start:enum_end] + '\n' + source[first:last])
        cls.binaries = {}
        for mode in (0, 1):
            binary = directory / ('sender_one_shot_' + str(mode))
            c_object = directory / ('ssot_' + str(mode) + '.o')
            defines = ['-DHELLO_TEST_MODE=1', '-DLORA_ROLE_SENDER=1']
            if mode:
                defines.append('-DHELLO_RAM_ONLY_TEST=1')
            c_result = subprocess.run([
                'gcc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                *defines, '-I' + str(ROOT / 'src'), '-I' + str(ROOT / 'include'),
                '-c', str(ROOT / 'src/ssot.c'), '-o', str(c_object),
            ], capture_output=True, text=True)
            if c_result.returncode:
                raise AssertionError(c_result.stdout + c_result.stderr)
            result = subprocess.run([
                'g++', '-std=c++11', '-Wall', '-Wextra', '-Werror',
                *defines, '-I' + str(ROOT / 'src/shared'),
                '-I' + str(ROOT / 'src'), '-I' + str(ROOT / 'include'),
                '-I' + str(directory),
                str(ROOT / 'tests/sender_one_shot_test.cpp'),
                str(c_object), '-o', str(binary),
            ], capture_output=True, text=True)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            cls.binaries[mode] = binary

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def check_case(self, name, mode=1):
        result = subprocess.run([str(self.binaries[mode]), name],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_first_valid_session_is_accepted(self):
        self.check_case('first')

    def test_repeated_and_new_sessions_are_rejected_in_same_boot(self):
        self.check_case('repeat')

    def test_invalid_sessions_are_rejected(self):
        self.check_case('invalid')

    def test_ram_test_allows_one_data_attempt_and_no_retry(self):
        self.check_case('one_attempt')

    def test_new_boot_waits_for_explicit_start(self):
        self.check_case('boot')

    def test_ram_claim_never_reads_or_writes_eeprom(self):
        self.check_case('no_eeprom')

    def test_default_persistent_claim_still_consumes_four_byte_marker(self):
        self.check_case('persistent', mode=0)

    def test_ack_correlation_remains_strict(self):
        self.check_case('ack')

    def test_runner_rejects_missing_disabled_or_conflicting_ram_test_flag(self):
        safe = effective_platformio_config()
        self.assertTrue(rf_proof.valid_rf_profile_config(safe))
        for flags in ([], ['-DHELLO_RAM_ONLY_TEST=0'],
                      ['-DHELLO_RAM_ONLY_TEST=1', '-DHELLO_RAM_ONLY_TEST=0']):
            config = safe.replace('"-DHELLO_RAM_ONLY_TEST=1"',
                                  ', '.join('"' + flag + '"' for flag in flags))
            if not flags:
                config = safe.replace(', "-DHELLO_RAM_ONLY_TEST=1"', '')
            with self.subTest(flags=flags):
                self.assertFalse(rf_proof.valid_rf_profile_config(config))


if __name__ == '__main__':
    unittest.main()
