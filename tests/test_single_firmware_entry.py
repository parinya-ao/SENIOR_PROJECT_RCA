import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE_DEFINITION = re.compile(
    r"^\s*void\s+(setup|loop|onPreMain)\s*\(", re.MULTILINE
)


class SingleFirmwareEntryTests(unittest.TestCase):
    def test_only_src_main_defines_arduino_lifecycle(self):
        definitions = {}
        for source_root in (ROOT / "src", ROOT / "stable_lib"):
            for source in sorted(source_root.rglob("*.cpp")):
                for match in LIFECYCLE_DEFINITION.finditer(source.read_text()):
                    relative = source.relative_to(ROOT).as_posix()
                    definitions.setdefault(match.group(1), []).append(relative)

        self.assertEqual(
            definitions,
            {
                "onPreMain": ["src/main.cpp"],
                "setup": ["src/main.cpp"],
                "loop": ["src/main.cpp"],
            },
        )

    def test_project_firmware_implementations_live_under_stable_lib(self):
        sources = [
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "lib").rglob("*")
            if path.is_file() and path.suffix in {".c", ".cc", ".cpp", ".h", ".hpp"}
        ]

        self.assertEqual(sources, [])


if __name__ == "__main__":
    unittest.main()
