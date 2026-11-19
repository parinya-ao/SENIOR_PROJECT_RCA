"""Hardware-free quality gate for the operational LoRa and ARQ firmware."""

import csv
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path.cwd()
REPORT = Path(os.environ.get("CPP_QUALITY_REPORT_DIR", "reports/static_analysis")).resolve()
DOCS = Path(os.environ.get("CPP_QUALITY_DOCS_DIR", "docs/generated")).resolve()
TARGETS = ("sender_hello", "receiver", "sender", "sender_arq_test", "receiver_arq_test")
SOURCE_DIRS = ("src", "stable_lib/ssot", "stable_lib/arq")
SOURCES = sorted(
    str(path)
    for directory in SOURCE_DIRS
    for path in Path(directory).rglob("*")
    if path.suffix in {".cpp", ".h"}
)
TOOLS = (
    "pio", "clang", "clang++", "clang-format", "clang-tidy", "doxygen",
    "lizard", "jscpd", "include-what-you-use", "clang-doc", "g++", "nm",
)
RESULTS = []
# Keep the existing status-line sequence and hardware initialization intact.
# A new function over 15, or growth in an existing exception, fails the gate.
COMPLEXITY_LIMITS = {
    ("src/shared/diagnostics/arq_bench.cpp", "arq::app::FlushBenchStatus"): 20,
    ("src/shared/radio/arq_radio.cpp", "arq::app::InitializeRadio"): 16,
    # The checked FAULT parser also rejects trailing non-whitespace input.
    ("stable_lib/arq/commands.cpp", "arq::ParseCommand"): 22,
    ("stable_lib/arq/receiver.cpp", "arq::HandleDataFrame"): 17,
    ("stable_lib/arq/sender.cpp", "arq::HandleControlFrame"): 20,
}


def record(name, status, detail):
    RESULTS.append((name, status, detail))
    print(f"{status:11} {name} ({detail})", flush=True)


def run(command, log, *, append=False, input_text=None, env=None):
    path = REPORT / log
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a" if append else "w") as stream:
        print("$", shlex.join(map(str, command)), file=stream, flush=True)
        result = subprocess.run(
            command, input=input_text, text=True, stdout=stream,
            stderr=subprocess.STDOUT, env=env, check=False,
        )
        print(f"[exit={result.returncode}]", file=stream)
    return result.returncode


def check(name, command, log, **kwargs):
    code = run(command, log, **kwargs)
    record(name, "FAIL" if code else "PASS", f"exit={code}, {log}")
    return code


def resolve_tools():
    missing = []
    (REPORT / "tools.txt").write_text("")
    for tool in TOOLS:
        path = shutil.which(tool)
        if not path:
            missing.append(tool)
            continue
        if run([str(Path(path).absolute()), "--version"], "tools.txt", append=True):
            missing.append(tool)
    if missing:
        record("tool preflight", "BLOCKED", ", ".join(missing))
    else:
        record("tool preflight", "PASS", "paths and versions in tools.txt")
    return not missing


def complexity_check():
    code = run(["lizard", "--csv", *SOURCES], "lizard.csv")
    with (REPORT / "lizard.txt").open("w") as report:
        if not code:
            output = (REPORT / "lizard.csv").read_text().splitlines()
            for row in csv.reader(output[1:-1]):
                nloc, ccn, _, params = map(int, row[:4])
                path, name = row[6:8]
                limit = COMPLEXITY_LIMITS.get((path, name), 15)
                if ccn > limit:
                    code = 1
                if ccn > 10 or nloc > 60 or params > 5:
                    print(f"{row[5]} CCN={ccn} NLOC={nloc} parameters={params} gate={limit}",
                          file=report)
        print(f"[exit={code}]", file=report)
    record("Lizard", "FAIL" if code else "PASS", f"exit={code}, lizard.txt and lizard.csv")


def capture_host_commands():
    # The existing host tests own the stub selection, defines, and compiler flags.
    records = {}
    original_run = subprocess.run
    loader = unittest.TestLoader()
    sys.path.insert(0, str(ROOT / "tests"))
    suite = loader.loadTestsFromNames([
        "test_reliable_transport", "test_arq.ArqTests.test_adapter",
        "test_arq.ArqTests.test_portable_core",
        "test_arq_directional.DirectionalTests.test_adapter_ack_nack_and_expiry_in_both_directions",
        "test_cpp_interfaces.CppInterfaceTests.test_command_grammar_and_overflow_recovery",
        "test_cpp_interfaces.CppInterfaceTests.test_diagnostics_queue_is_bounded_and_nonblocking",
        "test_radio_diagnostics",
    ])

    def capture(command, *args, **kwargs):
        result = original_run(command, *args, **kwargs)
        if result.returncode or command[0] not in ("clang", "g++"):
            return result
        inputs = command[1:command.index("-o")]
        units = [arg for arg in inputs if arg.endswith(".cpp")]
        flags = tuple(
            arg for arg in inputs if arg not in units
            and arg not in ("-c", "-nostdlib++", "--driver-mode=g++", "-fno-sanitize-link-c++-runtime")
            and not arg.endswith(".o") and not arg.startswith("-fsanitize=")
        )
        for unit in units:
            records[unit, flags] = {
                "directory": str(ROOT), "file": unit,
                "arguments": [shutil.which("clang++"), *flags, "-c", unit],
            }
        return result

    with (REPORT / "host-compilation-basis.txt").open("w") as log:
        with patch("subprocess.run", side_effect=capture), patch("sys.stdout", log):
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    if not result.wasSuccessful() or not records:
        record("host compilation database", "FAIL", "see host-compilation-basis.txt")
        return {}
    groups = defaultdict(list)
    for (_, flags), entry in sorted(records.items()):
        groups[flags].append(entry)
    record("host compilation database", "PASS", f"{len(records)} commands / {len(groups)} flag variants")
    return groups


def run_host_analysis(groups):
    if not groups:
        for tool in ("Clang-Tidy", "Clang Static Analyzer", "IWYU", "clang-doc"):
            record(tool, "BLOCKED", "host compilation database unavailable")
        return
    logs = ("clang_tidy.txt", "clang_analyzer/diagnostics.txt", "iwyu.txt", "clang-doc.txt")
    statuses = {log: [] for log in logs}
    for log in logs:
        path = REPORT / log
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    resource = subprocess.check_output(["clang++", "-print-resource-dir"], text=True).strip()
    for index, entries in enumerate(groups.values(), 1):
        variant = f"variant-{index:02}"
        db = REPORT / "compile_commands/host" / variant
        db.mkdir(parents=True, exist_ok=True)
        (db / "compile_commands.json").write_text(json.dumps(entries, indent=2) + "\n")
        units = [entry["file"] for entry in entries]
        tidy = ["clang-tidy", "-p", db, "--header-filter=(src/|stable_lib/(ssot|arq)/)", *units]
        api = DOCS / "clang-doc" / variant
        clang_doc = ["clang-doc", "-p", db, "--format=yaml", f"--output={api}", *units]
        for command, log in ((tidy, logs[0]), (clang_doc, logs[3])):
            statuses[log].append(run(command, log, append=True))
        for entry in entries:
            compiler, *args = entry["arguments"]
            analyze = [compiler, "--analyze", "-Xanalyzer", "-analyzer-output=text",
                       "-Xanalyzer", "-analyzer-werror", *(arg for arg in args if arg != "-c")]
            iwyu = ["include-what-you-use", f"-resource-dir={resource}", *args]
            for command, log in ((analyze, logs[1]), (iwyu, logs[2])):
                statuses[log].append(run(command, log, append=True))
    for name, log in zip(("Clang-Tidy", "Clang Static Analyzer", "IWYU", "clang-doc"), logs):
        values = statuses[log]
        record(name, "FAIL" if any(values) else "PASS",
               f"{len(values)} invocations, exits={sorted(set(values))}, {log}")


def firmware_checks():
    # PlatformIO writes one project-root DB. Preserve any editor database even if
    # a target fails, and archive each AVR database before the next invocation.
    top_db = ROOT / "compile_commands.json"
    db_dir = REPORT / "compile_commands/avr"
    db_dir.mkdir(parents=True, exist_ok=True)
    build_dir = REPORT / "avr-build"
    env = dict(os.environ, PLATFORMIO_BUILD_DIR=str(build_dir))
    config = subprocess.run(["pio", "project", "config", "--json-output"],
                            text=True, stdout=subprocess.PIPE, check=False)
    environments = dict(json.loads(config.stdout)) if not config.returncode else {}
    with (db_dir / "inventory.tsv").open("w") as inventory, (REPORT / "firmware.tsv").open("w") as sizes:
        print("environment\twarnings\tflash\tsram\thex_sha256", file=sizes)
        previous = top_db.read_bytes() if top_db.exists() else None
        try:
            for target in TARGETS:
                if "env:" + target not in environments:
                    record(target, "BLOCKED", "missing PlatformIO environment")
                    continue
                db_log = f"compile_commands/avr/{target}.txt"
                if not check(f"{target} compile database", ["pio", "run", "-e", target,
                             "-t", "compiledb"], db_log, env=env):
                    data = top_db.read_bytes()
                    (db_dir / f"{target}.json").write_bytes(data)
                    for source in sorted({item["file"] for item in json.loads(data)}):
                        print(target, source, sep="\t", file=inventory)
                # Clean this isolated target so incremental builds cannot hide warnings.
                build_log = f"firmware/{target}.txt"
                clean = run(["pio", "run", "-e", target, "-t", "clean"], build_log, env=env)
                code = clean or run(["pio", "run", "-e", target], build_log, env=env, append=True)
                output = (REPORT / build_log).read_text()
                warnings = len(re.findall(r"\bwarning:", output, re.IGNORECASE))
                image = build_dir / target / "firmware.hex"
                flash = re.search(r"^Flash:.*used (\d+) bytes", output, re.MULTILINE)
                ram = re.search(r"^RAM:.*used (\d+) bytes", output, re.MULTILINE)
                complete = not code and image.is_file() and flash is not None and ram is not None
                if complete:
                    print(target, warnings, flash[1], ram[1],
                          hashlib.sha256(image.read_bytes()).hexdigest(), sep="\t", file=sizes)
                record(f"{target} build", "PASS" if complete and not warnings else "FAIL",
                       f"exit={code}, {warnings} warnings, {build_log}")
        finally:
            if previous is None:
                top_db.unlink(missing_ok=True)
            elif not top_db.exists() or top_db.read_bytes() != previous:
                top_db.write_bytes(previous)
    record("native AVR LLVM analysis", "UNSUPPORTED", "AVR-GCC databases retained; LLVM runs on host commands with stubs")


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    # Report or build options are local to this gate. One invocation per checkout.
    with (ROOT / ".pio").joinpath("cpp-quality.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if resolve_tools():
            (REPORT / "source-scope.txt").write_text("\n".join(SOURCES) + "\n")
            check("clang-format", ["clang-format", "--dry-run", "--Werror", *SOURCES], "clang_format.txt")
            run_host_analysis(capture_host_commands())
            complexity_check()
            check("jscpd", ["jscpd", "--format", "cpp", "--formats-exts", "cpp:h", "--no-colors",
                   "--reporters", "console,json", "--fail-on-empty", "--output", REPORT / "jscpd", *SOURCES],
                  "jscpd/console.txt")
            doxyfile = Path("scripts/quality/Doxyfile").read_text()
            check("Doxygen", ["doxygen", "-"], "doxygen_warnings.txt",
                  input_text=f'{doxyfile}\nOUTPUT_DIRECTORY = "{DOCS / "doxygen"}"\n')
            firmware_checks()
            # The existing AVR build hook refreshes the source provenance IDs
            # that the host profile and proof fixtures verify.
            check("host tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests"], "host_tests.txt")
        else:
            record("dependent checks", "SKIPPED", "tool preflight blocked")
        report = ["# C++ quality gate", "", "| Check | Status | Evidence |", "| --- | --- | --- |"]
        report.extend(f"| {name} | {status} | {detail} |" for name, status, detail in RESULTS)
        (REPORT / "summary.md").write_text("\n".join(report) + "\n")
        return int(any(status in ("FAIL", "BLOCKED") for _, status, _ in RESULTS))


if __name__ == "__main__":
    (ROOT / ".pio").mkdir(exist_ok=True)
    sys.exit(main())
