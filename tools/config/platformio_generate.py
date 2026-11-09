"""PlatformIO pre-build validation and deterministic generation."""
import sys
from pathlib import Path

Import('env')
sys.path.insert(0, str(Path(env['PROJECT_DIR']) / 'tools/config'))
from generate_lora_config import generate, load_radio_profile, _write_atomic
from validate_lora_ssot import load, ROOT
import json

# Parsed INI values must match the source before compilation or linking.
generate()
config = load(ROOT / 'config/lora_system.json')
radio = load_radio_profile(ROOT / 'config/radio_915.toml')
roles_by_environment = {
    environment: role
    for role, environments in radio['environments'].items()
    for environment in environments
}
try:
    role = roles_by_environment[env['PIOENV']]
except KeyError as error:
    raise ValueError(f"PlatformIO environment has no radio role: {env['PIOENV']}") from error
board = config[f'{role}_board']
if int(env.GetProjectOption('board_build.text_section_start'), 0) != board['image_start']:
    raise ValueError('PlatformIO parsed a stale image start; run generation and rebuild')
flags = env.GetProjectOption('build_flags')
for flag in flags:
    if '-DHELLO_RF_' in flag and not flag.startswith('-DHELLO_RF_DIAGNOSTIC_ONLY='):
        raise ValueError(f'Conflicting radio macro: {flag}; configure config/radio_915.toml')
    if flag.startswith(('-DLORA_ROLE_SENDER', '-DLORA_ROLE_RECEIVER')):
        raise ValueError(f'Role is generated from config/radio_915.toml: {flag}')
defines = [(f'LORA_ROLE_{role.upper()}', 1)]
if role == 'receiver':
    defines.append(('LORA_RECEIVER_BOARD', 1))
env.Append(CPPDEFINES=defines)
manifest = json.loads((ROOT / 'generated/lora_manifest.json').read_text())
identity = Path(env.subst('$BUILD_DIR')) / 'lora_build_identity.h'
contents = '#pragma once\n#define LORA_BUILD_ID "' + manifest['environments'][env['PIOENV']]['build_id'] + '"\n'
_write_atomic(identity, contents)
env.Append(CCFLAGS=['-include', str(identity)])
