"""Summarize raw experiment records and preserve final host/source verification."""
from collections import Counter, defaultdict
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/updi/deep-debug'
groups = defaultdict(Counter)
states = defaultdict(Counter)
for path in sorted(OUT.glob('**/*.json')):
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or 'events' not in data:
        continue
    group = str(path.parent.relative_to(OUT))
    counts = groups[group]
    counts['sessions'] += 1
    counts['success' if data['exit'] == 0 else 'failure'] += 1
    state = data.get('target_state')
    if isinstance(state, dict):
        states[group][json.dumps(state, sort_keys=True)] += 1
    last_tx = b''
    pending_sts = 0
    for event in data['events']:
        raw = bytes.fromhex(event['hex'])
        if event['kind'] == 'tx':
            last_tx = raw
            if len(raw) >= 3 and raw[0] == 0x55 and raw[1] & 0xe0 == 0x40:
                pending_sts = 1
        elif event['kind'] == 'echo':
            counts['echo_reads'] += 1
            if raw != last_tx:
                counts['echo_errors'] += 1
        elif event['kind'] == 'response':
            counts['response_reads'] += 1
            if pending_sts:
                if raw != b'\x40':
                    counts[f'ack{pending_sts}_errors'] += 1
                else:
                    counts[f'ack{pending_sts}_ok'] += 1
                pending_sts = 2 if pending_sts == 1 and raw == b'\x40' else 0
            elif data['mode'] == 'sib' and data['backend'] != 'upstream' and last_tx == b'\x55\xe6' and raw == b'':
                counts['sib_readline_terminators'] += 1
            elif len(raw) != event['requested']:
                counts['missing_data'] += 1
summary = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               groups={k: dict(v) for k, v in groups.items()},
               states={k: dict(v) for k, v in states.items()})
oracle_valid = []
excluded = []
for group in ('stopped-oracle-break', 'oracle-sib-repeat'):
    for path in (OUT / group).glob('*.json'):
        if path.name == 'summary.json':
            continue
        data = json.loads(path.read_text())
        if group == 'stopped-oracle-break' and data['baud'] == 38400 and data['mode'] == 'sib' and data['exit']:
            excluded.append(str(path.relative_to(OUT)))
        else:
            oracle_valid.append(data)
assert len(excluded) == 20
assert len(oracle_valid) == 720 and all(d['exit'] == 0 for d in oracle_valid)
summary['valid_oracle_matrix'] = dict(trials=len(oracle_valid), success=720, excluded_observer_records=excluded)
commands = {
    'final-tests': ['.venv/bin/python', '-m', 'unittest', 'discover', '-s', 'test', '-v'],
    'final-build': ['pio', 'run'],
    'final-project-check': ['git', 'diff', '--check'],
    'final-nested-check': ['git', '-C', 'external/upditerm', 'diff', '--check'],
    'final-nested-diff': ['git', '-C', 'external/upditerm', 'diff', '--binary', 'HEAD'],
    'receiver-disassembly': [str(Path.home() / '.platformio/packages/toolchain-atmelavr/bin/avr-objdump'), '-d', '-t', '.pio/build/receiver/firmware.elf'],
    'final-port-users': ['fuser', '/dev/ttyUSB0'],
    'rtk-discover': ['rtk', 'discover'],
    'graph-update': ['graphify', 'update', '.'],
}
summary['checks'] = {}
for name, command in commands.items():
    proc = subprocess.run(command, cwd=ROOT, capture_output=True)
    (OUT / (name + '.txt')).write_bytes(proc.stdout + proc.stderr)
    summary['checks'][name] = dict(command=command, exit=proc.returncode)
summary['firmware_sha256'] = hashlib.sha256((ROOT / '.pio/build/receiver/firmware.hex').read_bytes()).hexdigest()
assert summary['firmware_sha256'] == json.loads((OUT / 'baseline.json').read_text())['firmware_sha256']
assert (OUT / 'nested-diff.txt').read_bytes() == (OUT / 'final-nested-diff.txt').read_bytes()
sources = [Path('external/upditerm/upditerm.py'), Path('external/upditerm/updi_uart.c'),
    Path('lib/updi_uart/updi_uart.c'), Path('src/receiver/main.cpp')]
sources += [p.relative_to(ROOT) for p in (ROOT / 'tools').glob('updi-*.py')]
sources += [p.relative_to(ROOT) for p in (ROOT / 'test').glob('test*.py')]
sources += [p.relative_to(ROOT) for p in (ROOT / '.automation/research/pymcuprog/pymcuprog/serialupdi').glob('*.py')]
summary['source_hashes'] = {str(p): hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}
for name in ('main.cpp', 'wiring.c', 'hooks.c'):
    path = Path.home() / '.platformio/packages/framework-arduino-megaavr-dxcore/cores/dxcore' / name
    summary['source_hashes'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
summary['oracle_commit'] = subprocess.check_output(['git', '-C', '.automation/research/pymcuprog', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
new_files = [p.relative_to(ROOT) for p in (ROOT / 'tools').glob('updi-*.py')
             if p.name not in ('updi-session.py',)]
new_files += [Path('test/test_updi_diagnose.py'), Path('docs/updi-root-cause-report.md')]
diff = bytearray()
for path in new_files:
    proc = subprocess.run(['git', 'diff', '--no-index', '--', '/dev/null', str(path)], cwd=ROOT, capture_output=True)
    assert proc.returncode in (0, 1), proc.stderr
    diff.extend(proc.stdout)
    check = subprocess.run(['git', 'diff', '--no-index', '--check', '--', '/dev/null', str(path)], cwd=ROOT, capture_output=True)
    assert not check.stdout and not check.stderr, (str(path), check.stdout, check.stderr)
(OUT / 'investigation-additions.diff').write_bytes(diff)
summary['no_overlap'] = True
ranges = []
for path in OUT.glob('**/*.json'):
    record = json.loads(path.read_text())
    if isinstance(record, dict) and record.get('events'):
        events = record['events']
        ranges.append((events[0]['ns'], events[-1]['end_ns'], str(path.relative_to(OUT))))
ranges.sort()
overlaps = [(a[2], b[2]) for a, b in zip(ranges, ranges[1:]) if b[0] < a[1]]
summary['serial_session_overlaps'] = overlaps
summary['no_overlap'] = not overlaps
assert summary['no_overlap'], overlaps
for name in ('final-tests', 'final-build', 'final-project-check', 'final-nested-check', 'graph-update'):
    assert summary['checks'][name]['exit'] == 0, summary['checks'][name]
assert summary['checks']['final-port-users']['exit'] == 1
(OUT / 'verification.json').write_text(json.dumps(summary, indent=2) + '\n')
inventory = {}
for raw in subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT).split(b'\0'):
    if not raw:
        continue
    path = ROOT / raw.decode()
    if path.is_file() and path.name != 'final-untracked-inventory.json':
        inventory[str(path.relative_to(ROOT))] = dict(bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(OUT / 'final-untracked-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
print(json.dumps({k: summary[k] for k in ('groups', 'firmware_sha256', 'checks')}, indent=2))
