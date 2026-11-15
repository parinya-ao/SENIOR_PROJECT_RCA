import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/config"))
import generate_lora_config


class SourceFingerprintTests(unittest.TestCase):
    def test_fingerprint_tracks_local_library_sources_not_sibling_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            sibling = Path(temporary) / "iwing-tracker/device-lora_dev"
            local = project / "lib/example/src/example.h"
            external = sibling / "lib/example/example.h"
            local.parent.mkdir(parents=True)
            external.parent.mkdir(parents=True)
            local.write_text("local v1")
            external.write_text("sibling v1")
            (project / "platformio.ini").write_text("[platformio]\n")
            original_root = generate_lora_config.ROOT
            generate_lora_config.ROOT = project
            try:
                before = generate_lora_config.source_fingerprint()
                external.write_text("sibling v2")
                self.assertEqual(generate_lora_config.source_fingerprint(), before)
                local.write_text("local v2")
                self.assertNotEqual(generate_lora_config.source_fingerprint(), before)
            finally:
                generate_lora_config.ROOT = original_root


if __name__ == "__main__":
    unittest.main()
