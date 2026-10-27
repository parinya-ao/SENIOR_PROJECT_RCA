"""Sequential independent trials; every trial uses the bounded existing-library harness."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
from updi_rca.paths import REPOSITORY_ROOT as ROOT, EXPERIMENT_ROOT



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output')
    parser.add_argument('--backend', choices=['upstream', 'oracle24', 'oracle16'], default='upstream')
    parser.add_argument('--trials', type=int, default=20)
    parser.add_argument('--double-break', action='store_true')
    args = parser.parse_args()
    assert 1 <= args.trials <= 20
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.mkdir(exist_ok=False)
    addresses = (0x1c, 0x1d, 0x1e, 0x1f, 0x40, 0x63)
    if args.backend != 'upstream':
        addresses += (0x4000, 0xf01, 0x1051)
    operations = [('sib', None), ('control', None)] + [('read', a) for a in addresses] + [('scratch', None)]
    summary = []
    for baud in (38400, 57600, 115200):
        for mode, address in operations:
            counts = Counter()
            for trial in range(args.trials):
                name = f'{baud}-{mode}-{address if address is not None else 0:04x}-{trial:02d}.json'
                path = output / name
                cmd = [sys.executable, str(EXPERIMENT_ROOT / 'scripts/updi-diagnose.py'), mode, str(path),
                    '--backend', args.backend, '--baud', str(baud),
                    '--hypothesis', 'Equivalent operation depends on observed target state and transport baud',
                    '--falsifier', 'Failure invariant across states or isolated to one address/backend',
                    '--variable', f'{mode} independent attachment; baud block {baud}; address {address}']
                if address is not None:
                    cmd += ['--address', str(address)]
                if args.double_break:
                    cmd += ['--double-break']
                proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=30)
                assert path.exists(), proc.stderr.decode(errors='replace')
                data = json.loads(path.read_text())
                assert proc.returncode == data['exit'], (proc.returncode, data['exit'])
                counts['trials'] += 1
                counts['success' if data['exit'] == 0 else 'failure'] += 1
                if data['exit'] and mode == 'scratch':
                    # A lost ACK may leave GPR1 changed. Require explicit restoration before proceeding.
                    print(f'STOP: scratch failure, inspect/restore GPR1 using {path}', flush=True)
                    return 1
            row = dict(backend=args.backend, baud=baud, mode=mode, address=address, **counts)
            summary.append(row)
            print(json.dumps(row), flush=True)
            (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
