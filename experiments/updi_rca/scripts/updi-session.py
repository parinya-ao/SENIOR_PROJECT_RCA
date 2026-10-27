"""PTY capture for upstream traces and acceptance gates; no UPDI implementation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import termios
import time
import sys
from updi_rca.paths import REPOSITORY_ROOT as ROOT, VENDOR_ROOT


def capture(baud, seconds, message, output, trace=False, reset=False):
    output = Path(output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    master, slave = pty.openpty()
    attr = termios.tcgetattr(slave)
    attr[1] &= ~termios.OPOST
    termios.tcsetattr(slave, termios.TCSANOW, attr)
    before = termios.tcgetattr(slave)
    stty_before = subprocess.check_output(['stty', '-g'], stdin=slave, text=True).strip()
    command = [sys.executable, '-u', str(VENDOR_ROOT / 'upditerm/upditerm.py'),
               '/dev/ttyUSB0', str(baud), '-q'] + (['-t'] if trace else []) + (['-r'] if reset else [])
    start = time.monotonic()
    proc = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=subprocess.PIPE, cwd=ROOT)
    data, errors, pending = bytearray(), bytearray(), bytearray()
    startup = None
    count = 0
    failure = None
    sent_exit = False
    exit_time = None
    try:
        while proc.poll() is None:
            now = time.monotonic()
            if not sent_exit:
                if trace and now - start >= seconds or (
                        startup is not None and now - startup >= seconds):
                    os.write(master, b'\x05e')
                    sent_exit, exit_time = True, now
                elif startup is None and now - start > (seconds if trace else 10):
                    failure = 'startup timeout'
                    os.write(master, b'\x05e')
                    sent_exit, exit_time = True, now
            elif now - exit_time > 5:
                failure = 'exit timeout'
                break
            for fd in select.select([master, proc.stderr], [], [], 0.05)[0]:
                chunk = os.read(fd if isinstance(fd, int) else fd.fileno(), 65536)
                if fd == master:
                    data.extend(chunk)
                    if not trace and not sent_exit:
                        pending.extend(chunk)
                        while len(pending) >= len(message):
                            actual = bytes(pending[:len(message)])
                            del pending[:len(message)]
                            if actual != message:
                                failure = f'corrupt message: {actual!r}'
                                break
                            if startup is None:
                                startup = time.monotonic()
                            else:
                                count += 1
                else:
                    errors.extend(chunk)
            if errors:
                failure = 'first transport diagnostic (see capture)'
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    failure = 'failure propagation timeout'
                break
            if b'No echo' in data or b'Short read' in data:
                failure = 'first transport diagnostic (see capture)'
            if failure and not sent_exit:
                break
        if failure and proc.poll() is None:
            proc.terminate()  # stop upstream spam at the first observed error
        proc.wait(timeout=6)
        errors.extend(proc.stderr.read())
        while select.select([master], [], [], 0)[0]:
            data.extend(os.read(master, 65536))
        if not trace and pending and not failure:
            failure = f'partial message: {bytes(pending)!r}'
        expected = int(seconds / (2 if message == b'H' else 1))
        if not trace and not failure and count != expected:
            failure = f'message count: expected {expected}, received {count}'
        result = dict(baud=baud, reset=reset, wiring='unverified',
                      firmware_sha256=hashlib.sha256(Path('.pio/build/receiver/firmware.hex').read_bytes()).hexdigest(),
                      seconds=seconds, startup_seconds=None if startup is None else startup-start,
                      messages=count, message=message.decode('ascii'), exit=proc.returncode,
                      restored=before == termios.tcgetattr(slave), first_failure=failure,
                      stty_restored=stty_before == subprocess.check_output(
                          ['stty', '-g'], stdin=slave, text=True).strip(),
                      stderr=errors.decode(errors='replace'))
        output.with_suffix('.stdout').write_bytes(data)
        output.with_suffix('.stderr').write_bytes(errors)
        output.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
        return result
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        proc.stderr.close()
        os.close(master)
        os.close(slave)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baud', type=int)
    parser.add_argument('seconds', type=float)
    parser.add_argument('message', choices=['H', 'HELLO', 'WORLD'])
    parser.add_argument('output')
    parser.add_argument('--trace', action='store_true')
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()
    result = capture(args.baud, args.seconds,
                     {'H': b'H', 'HELLO': b'HELLO', 'WORLD': b'HELLO WORLD\r\n'}[args.message],
                     args.output, args.trace, args.reset)
    print(json.dumps(result))
    raise SystemExit(bool(result['first_failure'] or result['exit'] or not result['restored']))
