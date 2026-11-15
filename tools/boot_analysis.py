"""Conservative reachable-control-flow audit of an AVR Flash backup (no target access)."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def analyze(disassembly, application_start):
    instructions = {}
    for line in disassembly.splitlines():
        match = re.match(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)\s*([a-z]+)\s*(.*)", line)
        if match:
            address, data, opcode, operands = match.groups()
            instructions[int(address, 16)] = (len(data.split()), opcode, operands)
    pending = [0]
    visited = set()
    transfers = []
    unresolved = []
    while pending:
        address = pending.pop()
        if address in visited:
            continue
        visited.add(address)
        if address >= application_start:
            transfers.append(address)
            continue
        if address not in instructions:
            unresolved.append(f"missing instruction at {address:#x}")
            continue
        size, opcode, operands = instructions[address]
        following = address + size
        if opcode in ("ret", "reti"):
            continue
        if opcode in ("ijmp", "eijmp", "icall", "eicall"):
            unresolved.append(f"indirect transfer at {address:#x}: {opcode}")
            continue
        if opcode in ("jmp", "rjmp", "call", "rcall") or opcode.startswith("br"):
            target = re.search(r"(?:;\s*)?0x([0-9a-f]+)", operands)
            if not target:
                unresolved.append(f"unknown branch at {address:#x}")
            else:
                pending.append(int(target.group(1), 16))
            if opcode not in ("jmp", "rjmp"):
                pending.append(following)
        elif opcode in ("cpse", "sbic", "sbis", "sbrc", "sbrs"):
            pending.append(following)
            if following in instructions:
                pending.append(following + instructions[following][0])
            else:
                unresolved.append(f"unknown skip at {address:#x}")
        else:
            pending.append(following)
    return dict(
        reachable_instruction_count=len(visited),
        application_transfers=sorted(set(transfers)),
        unresolved=sorted(set(unresolved)),
        verdict="UNRESOLVED"
        if unresolved
        else ("TRANSFER_PRESENT" if transfers else "NO_APPLICATION_HANDOFF"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--application-start", type=lambda text: int(text, 0), default=0x5800)
    parser.add_argument(
        "--objdump",
        default=str(Path.home() / ".platformio/packages/toolchain-atmelavr/bin/avr-objdump"),
    )
    args = parser.parse_args()
    output = subprocess.check_output(
        [args.objdump, "-D", "-b", "binary", "-m", "avr", str(args.backup)], text=True
    )
    result = analyze(output, args.application_start)
    result.update(
        backup_sha256=hashlib.sha256(args.backup.read_bytes()).hexdigest(),
        application_start=args.application_start,
        limit="Static reachability only; indirect targets and on-target boot require independent evidence.",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
