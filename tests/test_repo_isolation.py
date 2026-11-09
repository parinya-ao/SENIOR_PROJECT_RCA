import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    from tools.validate_repo_isolation import validate_repo
except ImportError:
    validate_repo = lambda root: ["validator module is missing"]


class RepositoryIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "repo"
        self.root.mkdir()
        self.write("platformio.ini", "[platformio]\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def write(self, path, contents=""):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)
        return target

    def test_local_paths_and_parent_paths_staying_in_repo_pass(self):
        self.write(
            "platformio.ini",
            "[platformio]\nextra_configs = generated/layout.ini\n"
            "[env]\nbuild_flags = -Iinclude -Isrc/../include\n"
            "lib_deps = symlink://lib/local_lib\n"
            "extra_scripts = pre:tools/build.py\n",
        )
        self.write("generated/layout.ini", "[env:layout]\nbuild_flags = -Iinclude\n")
        self.write("include/local.h")
        self.write("lib/local_lib/src/local.cpp")
        self.write("tools/build.py")
        (self.root / "src").mkdir()
        (self.root / "src/local.h").symlink_to("../include/local.h")

        self.assertEqual(validate_repo(self.root), [])

    def test_external_relative_and_absolute_build_paths_are_rejected(self):
        outside = Path(self.temp_dir.name) / "outside"
        outside.mkdir()
        (outside / "extra.ini").write_text("[env]\n")
        self.write(
            "platformio.ini",
            "[platformio]\nextra_configs = ../outside/extra.ini\n"
            f"[env]\nbuild_flags = -I{outside}\n",
        )

        errors = validate_repo(self.root)

        self.assertTrue(any("extra_configs" in error for error in errors), errors)
        self.assertTrue(any("build include" in error for error in errors), errors)

    def test_nested_generated_ini_references_are_checked(self):
        self.write(
            "platformio.ini",
            "[platformio]\nextra_configs = generated/lora_platformio.ini\n",
        )
        self.write(
            "generated/lora_platformio.ini",
            "[env:generated]\nbuild_flags = -I../../../outside/include\n",
        )

        errors = validate_repo(self.root)

        self.assertTrue(any("build include" in error for error in errors), errors)

    def test_missing_root_or_nested_config_is_reported(self):
        (self.root / "platformio.ini").unlink()
        self.assertTrue(any("platformio.ini" in error for error in validate_repo(self.root)))

        self.write(
            "platformio.ini",
            "[platformio]\nextra_configs = generated/missing.ini\n",
        )
        self.assertTrue(any("missing.ini" in error for error in validate_repo(self.root)))

    def test_forbidden_first_party_library_manifests_are_reported(self):
        self.write("lib/first/library.json", "{}")
        self.write("lib/second/module.json", "{}")
        self.write("lib/third/library.properties", "name=Third")

        errors = validate_repo(self.root)

        self.assertTrue(any("library.json" in error for error in errors), errors)
        self.assertTrue(any("module.json" in error for error in errors), errors)
        self.assertTrue(any("library.properties" in error for error in errors), errors)

    def test_broken_and_nested_external_source_symlinks_are_reported(self):
        outside = Path(self.temp_dir.name) / "outside.h"
        outside.write_text("header")
        (self.root / "src").mkdir()
        (self.root / "src/broken.h").symlink_to("missing.h")
        (self.root / "src/first.h").symlink_to("second.h")
        (self.root / "src/second.h").symlink_to(outside)

        errors = validate_repo(self.root)

        self.assertTrue(any("broken" in error for error in errors), errors)
        self.assertTrue(any("outside" in error for error in errors), errors)

    def test_tracked_symlink_is_checked_even_when_missing_from_worktree(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Test"], check=True)
        (self.root / "src").mkdir()
        tracked = self.root / "src/tracked.h"
        tracked.symlink_to("../../../outside.h")
        subprocess.run(["git", "-C", str(self.root), "add", "platformio.ini", "src/tracked.h"], check=True)
        tracked.unlink()

        errors = validate_repo(self.root)

        self.assertTrue(any("tracked symlink" in error and "escapes the repository" in error
                            for error in errors), errors)

    def test_agent_environment_symlinks_are_excluded(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        tracked = self.root / ".claude/skills/remote"
        tracked.parent.mkdir(parents=True)
        tracked.symlink_to("../../../outside")
        subprocess.run(["git", "-C", str(self.root), "add", ".claude/skills/remote"], check=True)

        self.assertEqual(validate_repo(self.root), [])

    def test_generated_ini_local_references_outside_repo_are_rejected(self):
        self.write(
            "platformio.ini",
            "[platformio]\nextra_configs = generated/lora_platformio.ini\n",
        )
        self.write(
            "generated/lora_platformio.ini",
            "[env:generated]\nextra_scripts = pre:/tmp/external.py\n",
        )

        errors = validate_repo(self.root)

        self.assertTrue(any("extra_scripts" in error for error in errors), errors)

    def test_examples_in_test_data_are_not_treated_as_build_configuration(self):
        self.write("tests/fixtures/example.ini", "symlink://../../outside\n-I../../../outside\nlibrary.json\n")

        self.assertEqual(validate_repo(self.root), [])


if __name__ == "__main__":
    unittest.main()
