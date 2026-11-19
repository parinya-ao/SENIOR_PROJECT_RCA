import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE_DEFINITION = re.compile(r"^\s*void\s+(setup|loop|onPreMain)\s*\(", re.MULTILINE)


class SingleFirmwareEntryTests(unittest.TestCase):
    def test_only_role_entries_define_arduino_lifecycle(self) -> None:
        """Keep exactly one setup, loop, and pre-main entry per role."""
        definitions: dict[str, list[str]] = {}
        for source_root in (ROOT / "src", ROOT / "stable_lib"):
            for source in sorted(source_root.rglob("*.cpp")):
                for match in LIFECYCLE_DEFINITION.finditer(source.read_text()):
                    relative = source.relative_to(ROOT).as_posix()
                    definitions.setdefault(match.group(1), []).append(relative)

        entries = [
            "src/receiver/appcode/main.cpp",
            "src/sender/appcode/main.cpp",
        ]
        self.assertEqual(definitions, dict.fromkeys(("onPreMain", "setup", "loop"), entries))

    def test_project_firmware_implementations_live_under_stable_lib(self) -> None:
        """Keep project libraries in the single configured library root."""
        sources = [
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "lib").rglob("*")
            if path.is_file() and path.suffix in {".c", ".cc", ".cpp", ".h", ".hpp"}
        ]

        self.assertEqual(sources, [])

    def test_platformio_uses_one_entry_and_one_library_root(self) -> None:
        """Select one role-specific entry point and the shared library root."""
        result = subprocess.check_output(
            ["pio", "project", "config", "--json-output"], cwd=ROOT, text=True
        )
        config = {section: dict(options) for section, options in json.loads(result)}
        self.assertTrue(config["platformio"]["lib_dir"].endswith("stable_lib"))
        profiles = {"debug", "release"}
        roles = {"sender", "receiver"}
        targets = {
            section[4:]: options
            for section, options in config.items()
            if section.startswith("env:")
        }
        self.assertLessEqual(profiles, targets.keys())
        self.assertEqual(len(targets) - len(profiles), 19)
        for target, options in targets.items():
            with self.subTest(target=target):
                filters = options["build_src_filter"]
                sources = [entry[2:-1] for entry in filters if entry.startswith("+<")]
                entries = [source for source in sources if source.endswith("main.cpp")]
                if target in profiles:
                    self.assertEqual(entries, [])
                else:
                    role = target.split("_", 1)[0]
                    self.assertIn(role, roles)
                    self.assertEqual(entries, [f"{role}/appcode/main.cpp"])
                    self.assertTrue((ROOT / "src" / entries[0]).is_file())
                    arq_sources = [source for source in sources if "/arq/" in source]
                    if "_arq" in target:
                        direction = (roles - {role}).pop() if target.endswith("_reverse") else role
                        self.assertEqual(arq_sources, [f"{direction}/appcode/arq/{direction}.cpp"])
                    else:
                        self.assertEqual(arq_sources, [])
                self.assertTrue(all((ROOT / "src" / source).is_file() for source in sources))
                self.assertFalse(
                    any(source.startswith(("app/", "features/")) for source in sources)
                )
                self.assertIn("-<receiver/bootloader/**>", filters)
                self.assertNotIn("lib_extra_dirs", options)


if __name__ == "__main__":
    unittest.main()
