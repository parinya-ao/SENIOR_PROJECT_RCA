"""Reject build and source references that escape this repository."""

import configparser
import os
import shlex
import subprocess
import sys
from pathlib import Path

LIBRARY_MANIFESTS = {"library.json", "library.properties", "module.json"}
SOURCE_DIRS = ("src", "lib", "include", "generated", "config", "third_party", "tools")
INCLUDE_FLAGS = ("-I", "-isystem", "-iquote")


def _inside(root, path):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _label(root, path):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _resolved(root, source, value, kind, errors, must_exist=False):
    value = value.strip().strip("\"'")
    for variable in ("${PROJECT_DIR}", "${project_dir}", "${platformio.project_dir}"):
        value = value.replace(variable, str(root))
    if "$" in value:
        errors.append(f"{_label(root, source)}: unresolved {kind} reference {value!r}")
        return None

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    try:
        result = path.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        errors.append(f"{_label(root, source)}: invalid {kind} reference {value!r}: {error}")
        return None
    if not _inside(root, result):
        errors.append(
            f"{_label(root, source)}: {kind} reference {value!r} escapes the repository ({result})"
        )
        return None
    if must_exist and not result.exists():
        errors.append(f"{_label(root, source)}: missing {kind} reference {value!r}")
        return None
    return result


def _source_symlinks(root):
    for name in SOURCE_DIRS:
        start = root / name
        if start.is_symlink():
            yield start
            continue
        if not start.is_dir():
            continue
        for current, directories, files in os.walk(start, followlinks=False):
            for name in directories + files:
                path = Path(current) / name
                if path.is_symlink():
                    yield path
            directories[:] = [
                name for name in directories if not (Path(current) / name).is_symlink()
            ]


def _check_symlink(root, path, errors, label):
    try:
        target = path.resolve(strict=True)
    except (OSError, RuntimeError):
        errors.append(f"{label} {_label(root, path)} is broken or cyclic")
        return
    if not _inside(root, target):
        errors.append(f"{label} {_label(root, path)} escapes the repository ({target})")


def _tracked_symlinks(root, errors, physical):
    result = subprocess.run(
        ["git", "ls-files", "-s", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode:
        return
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, object_id, _ = metadata.split()
        relative = Path(os.fsdecode(raw_path))
        if mode != b"120000" or not relative.parts or relative.parts[0] not in SOURCE_DIRS:
            continue
        path = root / relative
        if path in physical and path.is_symlink():
            continue
        try:
            target_text = (
                subprocess.run(
                    ["git", "cat-file", "blob", object_id.decode("ascii")],
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                .stdout.decode("utf-8")
                .strip()
            )
        except (subprocess.CalledProcessError, UnicodeError):
            errors.append(f"tracked symlink {_label(root, path)} cannot be read from the index")
            continue
        target = Path(target_text)
        if not target.is_absolute():
            target = path.parent / target
        try:
            resolved = target.resolve(strict=False)
        except (OSError, RuntimeError):
            errors.append(f"tracked symlink {_label(root, path)} is broken or cyclic")
            continue
        if not _inside(root, resolved):
            errors.append(
                f"tracked symlink {_label(root, path)} escapes the repository ({resolved})"
            )
        elif not path.is_symlink():
            errors.append(f"tracked symlink {_label(root, path)} is missing from the worktree")


def _items(value):
    return [
        item.strip().strip("\"'")
        for line in value.splitlines()
        for item in line.split(",")
        if item.strip()
    ]


def _local_dependency(value):
    for scheme in ("symlink://", "file://"):
        if value.startswith(scheme):
            return value[len(scheme) :]
    if value.startswith(("./", "../", "/", "~/")):
        return value
    return None


def _check_config(root, path, errors, visited):
    path = _resolved(root, path, str(path), "configuration", errors, must_exist=True)
    if path is None or path in visited:
        return
    visited.add(path)
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read_string(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, configparser.Error) as error:
        errors.append(f"{_label(root, path)}: cannot read PlatformIO configuration: {error}")
        return

    if parser.has_section("platformio"):
        for value in _items(parser.get("platformio", "extra_configs", fallback="")):
            nested = _resolved(root, path, value, "extra_configs", errors, must_exist=True)
            if nested is not None:
                _check_config(root, nested, errors, visited)

    for section in parser.sections():
        if not (section == "env" or section.startswith("env:")):
            continue
        for value in _items(parser.get(section, "extra_scripts", fallback="")):
            _, separator, script = value.partition(":")
            script = script if separator else value
            _resolved(root, path, script, "extra_scripts", errors, must_exist=True)

        for value in _items(parser.get(section, "lib_deps", fallback="")):
            local = _local_dependency(value)
            if local is not None:
                _resolved(root, path, local, "local library dependency", errors, must_exist=True)

        try:
            flags = shlex.split(
                parser.get(section, "build_flags", fallback="").replace("\\\n", " ")
            )
        except ValueError as error:
            errors.append(f"{_label(root, path)}: invalid build_flags in [{section}]: {error}")
            continue
        index = 0
        while index < len(flags):
            token = flags[index]
            include = None
            if token in INCLUDE_FLAGS and index + 1 < len(flags):
                index += 1
                include = flags[index]
            else:
                for flag in INCLUDE_FLAGS:
                    if token.startswith(flag) and len(token) > len(flag):
                        include = token[len(flag) :]
                        break
            if include is not None:
                _resolved(root, path, include, "build include", errors, must_exist=True)
            index += 1


def validate_repo(project_root):
    root = Path(project_root).resolve()
    errors = []

    for directory, _, files in os.walk(root / "lib") if (root / "lib").is_dir() else ():
        for name in files:
            if name in LIBRARY_MANIFESTS:
                errors.append(
                    f"first-party library metadata is forbidden: {_label(root, Path(directory) / name)}"
                )

    physical = set(_source_symlinks(root))
    for path in sorted(physical):
        _check_symlink(root, path, errors, "source symlink")
    _tracked_symlinks(root, errors, physical)

    config = root / "platformio.ini"
    if not config.is_file():
        errors.append("missing PlatformIO configuration: platformio.ini")
    else:
        _check_config(root, config, errors, set())
    return errors


def main():
    errors = validate_repo(Path(__file__).resolve().parents[1])
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print("Repository isolation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
