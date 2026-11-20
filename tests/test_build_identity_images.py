"""Generated provenance must describe the actual compiled firmware, not a stale object."""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

from tools.device_detection.firmware_identity import normalize_ihex_region
from tools.rf_proof import parse_ihex_range

ROOT = Path(__file__).resolve().parents[1]


class BuildIdentityImagesTests(unittest.TestCase):
    environments: ClassVar[tuple[str, ...]] = tuple(
        role + suffix
        for role in ("sender", "receiver")
        for suffix in ("_arq", "_arq_test", "_reverse_raw")
    )
    directory: ClassVar[tempfile.TemporaryDirectory[str]]
    project: ClassVar[Path]

    @classmethod
    def setUpClass(cls) -> None:
        """Build investigation images in a clean copy with cached dependencies."""
        pio = shutil.which("pio")
        if pio is None:
            message = "PlatformIO is required for build-identity image verification"
            raise RuntimeError(message)
        dependencies = ROOT / ".pio/libdeps"
        if not dependencies.is_dir():
            message = "cached PlatformIO libdeps are required; tests do not download deps"
            raise RuntimeError(message)

        cls.directory = tempfile.TemporaryDirectory(prefix="build-identity-images-")
        cls.project = Path(cls.directory.name) / "project"
        shutil.copytree(
            ROOT,
            cls.project,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                ".git",
                ".pio",
                ".automation",
                ".codegraph",
                "graphify-out",
                "artifacts",
                "__pycache__",
                ".venv",
                "venv",
                "dist",
                "target",
                "build",
                ".pytest_cache",
            ),
        )
        shutil.copytree(dependencies, cls.project / ".pio/libdeps", symlinks=True)
        for environment in cls.environments:
            result = subprocess.run(
                [pio, "run", "-e", environment],
                cwd=cls.project,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            if result.returncode:
                cls.directory.cleanup()
                raise AssertionError(
                    f"isolated offline build failed for {environment}:\n"
                    + result.stdout[-4000:]
                    + result.stderr[-4000:]
                )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def test_all_investigation_images_embed_their_declared_identity(self) -> None:
        for environment in self.environments:
            with self.subTest(environment=environment):
                directory = self.project / ".pio/build" / environment
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
                    build.encode() in binary, "stale compiled build identity: " + environment
                )
