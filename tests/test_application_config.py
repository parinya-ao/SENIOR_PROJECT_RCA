"""Validate configurable application policy independently of hardware SSOT."""

import copy
import unittest


class ApplicationConfigTests(unittest.TestCase):
    def test_generated_policy_matches_configuration(self):
        from tools.config.application_config import ROOT, load, render

        config = load()
        self.assertEqual(config["diagnostics"]["payload"], "HELLO_LORA")
        self.assertEqual(config["diagnostics"]["max_retries"], 0)
        self.assertEqual(
            (ROOT / "include/application_config.h").read_text(), render(config)
        )

    def test_rejects_invalid_or_unbounded_policy(self):
        from tools.config.application_config import load, validate

        config = load()
        cases = [
            ("diagnostics", "payload", "x" * 33),
            ("diagnostics", "payload", "bad\x00payload"),
            ("diagnostics", "max_retries", 1),
            ("logging", "slot_count", 256),
            ("logging", "slot_bytes", 1),
            ("commands", "capacity", 8),
            ("commands", "capacity", True),
            ("commands", "unknown", 1),
            ("ssot", "campaign_messages", 256),
            ("gateway", "result_buffer_bytes", 3000),
            ("diagnostics", "negative_payload", "HELLO_LORA"),
            ("raw", "payload", "x" * 33),
        ]
        for section, key, value in cases:
            with self.subTest(section=section, key=key):
                bad = copy.deepcopy(config)
                bad[section][key] = value
                with self.assertRaises(ValueError):
                    validate(bad)

    def test_policy_changes_alter_generated_cpp(self):
        from tools.config.application_config import load, render

        config = load()
        previous = render(config)
        config["commands"]["inter_byte_timeout_ms"] = 1500
        self.assertNotEqual(previous, render(config))
        self.assertIn("1500", render(config))

    def test_host_diagnostics_use_the_configured_payloads(self):
        from unittest.mock import patch
        from tools import arq_trial
        from tools.config.application_config import load

        config = load()
        config["diagnostics"]["payload"] = "CUSTOM"
        config["diagnostics"]["gateway_payload"] = "CUSTOM_GW"
        config["diagnostics"]["tracker_payload"] = "CUSTOM_TR"
        with patch.object(arq_trial, "load_application", return_value=config, create=True):
            self.assertEqual(arq_trial.diagnostic_case()["payload"], b"CUSTOM")
            self.assertEqual(arq_trial.diagnostic_case("T01")["payload"], b"CUSTOM_GW")
            self.assertEqual(arq_trial.diagnostic_case("T03")["payload"], b"CUSTOM_TR")

    def test_maximum_configured_raw_payload_fits_real_command_input(self):
        import subprocess
        import tempfile
        from pathlib import Path
        from tools.config.application_config import ROOT, load, render

        config = load()
        config["raw"]["payload"] = "Z" * 32
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "application_config.h").write_text(render(config))
            (path / "test.cpp").write_text(f'''#include <assert.h>
#include "{ROOT}/stable_lib/arq/src/arq/diagnostics.cpp"
#include "{ROOT}/stable_lib/reverse_raw_app/reverse_raw_app.cpp"
using namespace reverse_raw_app;
const arq_board board_ssot = {{3,4,5,6}};
void board_ssot_init() {{}}
int main() {{
  Initialize();
  const char text[] = "SEND {'5A' * 32}\\n";
  for (char value : text) if (value) FeedCommandByte(value);
  assert(tx_starts == 1 && sent_length == 32);
  for (unsigned i = 0; i < 32; ++i) assert(sent[i] == 'Z');
}}
''')
            binary = str(path / "test")
            result = subprocess.run(
                ["clang", "--driver-mode=g++", "-std=c++17", "-DLORA_ROLE_RECEIVER=1",
                 '-DLORA_BUILD_ID="configured-host"', "-I" + directory,
                 "-Itests/arq/stub", "-Itests/raw_mvp_stub", "-Iinclude",
                 "-Istable_lib/arq/src", "-Istable_lib/arq/src/arq",
                 str(path / "test.cpp"), "-o", binary],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run([binary], cwd=directory, check=True)

    def test_host_raw_commands_and_validation_share_the_payload(self):
        from unittest.mock import patch
        from tools import arq_trial, rf_proof
        from tools.config.application_config import load, raw_send_command

        config = load()
        config["raw"]["payload"] = "BENCH"
        encoded = b"BENCH".hex().upper()
        with patch("tools.config.application_config.load", return_value=config):
            self.assertEqual(raw_send_command(), "SEND " + encoded)
            events = [
                {"role": "receiver", "e": "RAW_TX", "rc": "0", "flags": "5"},
                {"role": "receiver", "e": "RAW_TX_DONE", "rc": "0", "flags": "8"},
                {"role": "sender", "e": "RAW_RX", "rc": "0", "flags": "64",
                 "len": "5", "match": "1", "bytes": encoded, "rssi": "-1", "snr": "2"},
            ]
            self.assertTrue(arq_trial.validate_reverse(events)["complete"])
            sender = ("[MVP SENDER] TX_START attempt=1 len=5 rc=0 cleanup=0\n"
                      "[MVP SENDER] TX_DONE attempt=1 cleanup=0 irq=8\n")
            receiver = ("[MVP RECEIVER] RX_READY rc=0\n"
                        "[MVP RECEIVER] RX len=5 rc=0 restart=0 irq=64 rssi=-1 snr=2"
                        " PASS bytes=" + encoded + "\n")
            self.assertTrue(rf_proof.parse_raw_mvp_logs(sender, receiver)["passed"])
