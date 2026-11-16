"""Generated provenance must describe the actual compiled firmware, not a stale object."""

import re
import unittest
from pathlib import Path

from tools.device_detection.firmware_identity import normalize_ihex_region
from tools.rf_proof import parse_ihex_range

ROOT = Path(__file__).resolve().parents[1]


class BuildIdentityImagesTests(unittest.TestCase):
    def test_all_investigation_images_embed_their_declared_identity(self) -> None:
        for role in ("sender", "receiver"):
            for suffix in ("_arq", "_arq_test", "_reverse_raw"):
                with self.subTest(environment=role + suffix):
                    directory = ROOT / ".pio/build" / (role + suffix)
                    match = re.search(
                        r'LORA_BUILD_ID "([0-9a-f]{64})"',
                        (directory / "lora_build_identity.h").read_text(),
                    )
                    if match is None:
                        self.fail(f"build identity missing in {directory}")
                    build = match.group(1)
                    image = (directory / "firmware.hex").read_bytes()
                    region = parse_ihex_range(image)
                    binary = normalize_ihex_region(
                        image.decode(), region["start"], region["end_exclusive"]
                    )
                    self.assertTrue(
                        build.encode() in binary, "stale compiled build identity: " + role + suffix
                    )
