"""Record the pre-experiment host baseline without opening a serial port."""
import hashlib
import json
from pathlib import Path
import subprocess
import datetime

root = Path(__file__).resolve().parents[1]
out = root / 'evidence/updi/deep-debug'
out.mkdir(parents=True, exist_ok=True)
if (out / 'baseline.json').exists():
    raise SystemExit('baseline already frozen; choose a new evidence directory for another baseline')
commands = {
    'status': ['git', 'status', '--short', '--untracked-files=all'],
    'project-diff': ['git', 'diff', '--binary'],
    'nested-diff': ['git', '-C', 'external/upditerm', 'diff', '--binary', 'HEAD'],
    'nested-status': ['git', '-C', 'external/upditerm', 'status', '--short'],
    'nested-head': ['git', '-C', 'external/upditerm', 'rev-parse', 'HEAD'],
    'versions': ['bash', '-c', '.venv/bin/python --version; pio --version; uname -a; git --version; lsusb'],
    'host-tests': ['.venv/bin/python', '-m', 'unittest', 'discover', '-s', 'test', '-v'],
    'receiver-build': ['pio', 'run', '-e', 'receiver'],
}
results = {}
for name, command in commands.items():
    result = subprocess.run(command, cwd=root, capture_output=True)
    (out / (name + '.txt')).write_bytes(result.stdout + result.stderr)
    results[name] = {'command': command, 'exit': result.returncode}
files = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=root).split(b'\0')
inventory = {}
for raw in files:
    if not raw:
        continue
    path = root / raw.decode()
    if path.is_file() and out not in path.parents:
        inventory[str(path.relative_to(root))] = {'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
(out / 'untracked-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
firmware = hashlib.sha256((root / '.pio/build/receiver/firmware.hex').read_bytes()).hexdigest()
assert firmware == '88c03596bab443c74015d8dfb04e1985f6d14940d227b84a4a943b3d5f47807e', firmware
(out / 'baseline.json').write_text(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'firmware_sha256': firmware, 'commands': results, 'untracked_files': len(inventory)}, indent=2) + '\n')
assert all(v['exit'] == 0 for v in results.values()), results
print(f'Baseline saved: {len(inventory)} untracked files; receiver hash preserved; build and tests passed')
