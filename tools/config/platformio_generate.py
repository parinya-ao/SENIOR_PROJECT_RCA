"""PlatformIO pre-build validation and deterministic generation."""
import sys
from pathlib import Path

Import('env')
sys.path.insert(0, str(Path(env['PROJECT_DIR']) / 'tools/config'))
from generate_lora_config import generate
from validate_lora_ssot import load, ROOT
import json

# Parsed INI values must match the source before compilation or linking.
generate()
config = load(ROOT / 'config/lora_system.json')
role = 'receiver' if env['PIOENV'].startswith('receiver') else 'sender'
board = config[f'{role}_board']
if int(env.GetProjectOption('board_build.text_section_start'), 0) != board['image_start']:
    raise ValueError('PlatformIO parsed a stale image start; run generation and rebuild')
for flag in env.GetProjectOption('build_flags'):
    if '-DHELLO_RF_' in flag and not flag.startswith('-DHELLO_RF_DIAGNOSTIC_ONLY='):
        raise ValueError(f'Conflicting diagnostic macro: {flag}; configure JSON SSOT')
manifest = json.loads((ROOT / 'generated/lora_manifest.json').read_text())
identity = Path(env.subst('$BUILD_DIR')) / 'lora_build_identity.h'
identity.parent.mkdir(parents=True, exist_ok=True)
contents = '#pragma once\n#define LORA_BUILD_ID "' + manifest['environments'][env['PIOENV']]['build_id'] + '"\n'
if not identity.exists() or identity.read_text() != contents:
    identity.write_text(contents)
env.Append(CCFLAGS=['-include', str(identity)])
