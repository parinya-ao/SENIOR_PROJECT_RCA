"""PlatformIO pre-build validation and deterministic generation."""

import sys
from pathlib import Path

Import("env")
sys.path.insert(0, str(Path(env["PROJECT_DIR"]) / "tools/config"))
import json

from application_config import load as load_application, render as render_application
from generate_lora_config import _write_atomic, artifacts, digest, load_radio_profile
from validate_lora_ssot import ROOT, load

config = load(ROOT / "config/lora_system.json")
if (ROOT / "include/application_config.h").read_text() != render_application(load_application()):
    raise ValueError("stale application policy; run tools/config/application_config.py")
radio = load_radio_profile(ROOT / "config/radio_915.toml")
# Builds verify hardware configuration without rewriting protected SSOT outputs.
# Only source provenance changes during an application migration.
outputs = artifacts(config, radio)
manifest_names = {"generated/lora_manifest.json", "generated/arq_manifest.json"}
for name, contents in outputs.items():
    if name in manifest_names or name.startswith("../"):
        continue
    path = ROOT / name
    if not path.is_file() or path.read_text() != contents:
        raise ValueError(f"stale or missing generated configuration: {name}")
for name in sorted(manifest_names):
    _write_atomic(ROOT / name, outputs[name])
power_candidates = {
    "sender_hello_5dbm": "sender_hello",
    "receiver_5dbm": "receiver",
}
base_environment = power_candidates.get(env["PIOENV"], env["PIOENV"])
roles_by_environment = {
    environment: role
    for role, environments in radio["environments"].items()
    for environment in environments
}
roles_by_environment.update(
    {
        f"{role}_arq{suffix}": role
        for role in ("sender", "receiver")
        for suffix in ("", "_test", "_radio_only", "_radio_only_reverse")
    }
)
roles_by_environment.update({role + "_reverse_raw": role for role in ("sender", "receiver")})
try:
    role = roles_by_environment[base_environment]
except KeyError as error:
    msg = f"PlatformIO environment has no radio role: {env['PIOENV']}"
    raise ValueError(msg) from error
board = config[f"{role}_board"]
if int(env.GetProjectOption("board_build.text_section_start"), 0) != board["image_start"]:
    msg = "PlatformIO parsed a stale image start; run generation and rebuild"
    raise ValueError(msg)
flags = env.GetProjectOption("build_flags")
power_flags = [flag for flag in flags if flag.startswith("-DLORA_TEST_TX_POWER_DBM")]
if power_flags != (["-DLORA_TEST_TX_POWER_DBM=5"] if env["PIOENV"] in power_candidates else []):
    msg = "TX power override is restricted to the two +5 dBm comparison targets"
    raise ValueError(msg)
for flag in flags:
    if "-DHELLO_RF_" in flag and not flag.startswith("-DHELLO_RF_DIAGNOSTIC_ONLY="):
        msg = f"Conflicting radio macro: {flag}; configure config/radio_915.toml"
        raise ValueError(msg)
    if flag.startswith(("-DLORA_ROLE_SENDER", "-DLORA_ROLE_RECEIVER")):
        msg = f"Role is generated from config/radio_915.toml: {flag}"
        raise ValueError(msg)
defines = [(f"LORA_ROLE_{role.upper()}", 1)]
if role == "receiver":
    defines.append(("LORA_RECEIVER_BOARD", 1))
env.Append(CPPDEFINES=defines)
if env.GetProjectOption("build_type") == "release":
    env.Append(LINKFLAGS=["-Wl,--strip-debug"])
manifest = json.loads((ROOT / "generated/lora_manifest.json").read_text())
identity = Path(env.subst("$BUILD_DIR")) / "lora_build_identity.h"
build_id = manifest["environments"].get(base_environment, {}).get("build_id")
if env["PIOENV"] in power_candidates:
    shared = dict(manifest["shared"], radio=dict(manifest["shared"]["radio"], tx_power_dbm=5))
    fingerprint = digest(shared)
    build_id = digest({"base_build_id": build_id, "shared_fingerprint": fingerprint})
    env.Append(CPPDEFINES=[("LORA_TEST_CONFIG_FINGERPRINT", '\\"' + fingerprint + '\\"')])
if build_id is None:
    from generate_lora_config import digest

    arq = json.loads((ROOT / "generated/arq_manifest.json").read_text())
    build_id = digest({"environment": env["PIOENV"], "arq": arq})
contents = '#pragma once\n#define LORA_BUILD_ID "' + build_id + '"\n'
_write_atomic(identity, contents)
# The identity must affect SCons' compile signature, including incremental builds.
env.Append(CPPDEFINES=[("LORA_BUILD_ID", '\\"' + build_id + '\\"')])


def checked_cpp(build_env, node):
    """Enable strict diagnostics on migrated modules without changing vendor flags."""
    checked = build_env.Clone()
    checked.ProcessUnFlags("-w -fpermissive -Wno-error=narrowing")
    checked.Append(CCFLAGS=["-Wall", "-Wextra", "-Wshadow", "-Wconversion", "-Wsign-conversion"])
    return checked.Object(node)


for source in ("stable_lib/ssot/src/ssot/codec.cpp", "stable_lib/arq/src/arq/codec.cpp", "stable_lib/arq/src/arq/sender.cpp", "stable_lib/arq/src/arq/receiver.cpp", "stable_lib/ssot/src/ssot/session.cpp", "stable_lib/ssot/src/ssot/control_input.cpp",
               "stable_lib/arq/src/arq/commands.cpp", "stable_lib/arq/src/arq/diagnostics.cpp"):
    env.AddBuildMiddleware(checked_cpp, "*" + source)
