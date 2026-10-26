# AVR128DA28 UPDI console engineering report

## 1. Outcome

The software lifecycle fix is implemented and tested. **The console is not yet
accepted:** no valid target output arrived at 38400, so reconnection and soak
gates cannot advance. The receiver remains the guarded `H` every two seconds
probe. Flash was uploaded once and verified; fuses were not changed.

## 2. Proven findings and remaining cause

Untouched upstream first failed at its default 921600 baud on `55 40 1e`
(STS, address `0x1e`, enabling the virtual UART). Echo validation succeeded;
the following one-byte ACK should be `40`, but the response was empty.
The same first failure occurred intermittently at 115200.
The final patched 38400 attempt also failed at the same first STS ACK, with
exit 1, one diagnostic, and both termios and `stty -g` settings restored.

At 38400, the 15-second trace showed 269 CPU-stopped reports and RUN commands,
with no OCD-message reads and no echo/short-read failure. A separate 10-second
`-r` trace showed the same behavior. Twelve separate status snapshots reported
`OCD_STATUS=01`, `ASI_SYS_STATUS=a2`, `RSTCTRL.RSTFR=02`, `GPR0=00`.
The installed header identifies `02` as the brownout reset flag. It is a
latched flag, not a voltage measurement; the physical cause remains unproven.

The repeated-error software cause is proven by source and regression tests:
upstream catches worker `SystemExit` and continues polling, while main waits
on a writer blocked on stdin. The patch propagates the first failure and stops
the session. No startup sequence, register address, retry or BOD change is
justified by the current evidence.

## 3. Hardware and baud

`udevadm` identifies `/dev/ttyUSB0` as Silicon Labs CP2102, VID:PID `10c4:ea60`,
serial `0001`, driver `cp210x`. `lsusb` lists two CP210x adapters. These IDs do
not identify a particular board schematic or its isolation network.

Expected topology from [upditerm](https://github.com/streef/upditerm): common
ground, RX directly to UPDI, TX through 1 kΩ to that node. Actual ground/RX
connections, TX circuit and resistor, target VCC, adapter logic level and cable
length remain unverified. Successful programming and SIB reads establish that
some UPDI communication works; they do not establish electrical margins.
[AVRDUDE](https://avrdudes.github.io/avrdude/8.1/avrdude_23.html) also documents
a diode/resistor arrangement and links
[DxCore hardware guidance](https://github.com/SpenceKonde/AVR-Guidance/blob/master/UPDI/jtag2updi.md).
No physical change was made based on guessed parameters.

38400 is the lowest tested **candidate**, not an accepted stable baud.
Programming remains 115200. The CLI default remains upstream's 921600.

## 4. Implementation and compatibility

Upstream baseline: `f2222b02ceeff7668caab0f240d2e13298116356`.
AVRDUDE 8.1, DxCore 1.6.2, PlatformIO and pyserial are retained.

The local target library includes upstream C/header directly, mapping only
`GPIOR2/3` to `GPR_GPR2/3`. Installed AVR128DA28 headers confirm
`0x001e/0x001f` and OCD registers `0x0f18/0x0f19`; these are preserved.
The ready check matches the structure of Microchip's
[blocking messaging example](https://onlinedocs.microchip.com/oxy/GUID-F897CF19-8EAC-457A-BE11-86BDAC9B59CF-en-US-10/GUID-A2AA4352-2351-435F-AA22-E33A1EE68FCA.html).
No messaging discrepancy has been demonstrated.

The host patch preserves protocol transactions and echo validation. It adds
contextual transport exceptions, worker cancellation, main-thread propagation,
explicit serial/log closure and terminal restoration. Failed-session cleanup
does not transact over UPDI. Normal exit disables the UART and UPDI as upstream
does. Known ACK values improve diagnostics without new ACK-value validation.
No dependency or retry wrapper was added. Upstream attribution and LICENSE remain.

## 5. Verification and acceptance

| Gate | Observed result |
| --- | --- |
| Build/upload | Pass: receiver 774 bytes verified at 115200; sender and receiver build |
| Local warnings | No new local warnings; DxCore emits its existing PROGMEM_MAPPED informational note |
| SIB baseline | 20/20 each at 115200, 57600, 38400; zero echo/short errors |
| SIB patched | 20/20 each at 115200, 57600, 38400; zero echo/short errors |
| Terminal connections | Failed first valid-output prerequisite at 38400; 20/20 not achieved |
| H, ≥120 s, 60/60 | Not entered: zero H output; earlier startup timeout and final missing STS ACK |
| HELLO, ≥120 s, 120/120 | Not entered; firmware not changed/uploaded for this stage |
| HELLO WORLD, ≥600 s, 600/600 | Not entered; firmware not changed/uploaded for this stage |
| Host regression tests | 11 pass; fake serial, workers, real PTY restoration/escape and mocked Windows input |
| Patch reproduction | Both diffs apply to clean pre-task files/pinned upstream; reproduced host matches byte-for-byte and all 11 tests pass |
| Real failure handling | 38400, 115200 and 921600 sessions exited 1, one stderr diagnostic, terminal restored |
| Real clean exit | Ctrl+E then e exited 0 and restored terminal attributes |
| Port ownership after tests | `fuser /dev/ttyUSB0` returned no owner (exit 1, no PIDs) |

The unchanged uploaded/built HEX SHA256 is
`88c03596bab443c74015d8dfb04e1985f6d14940d227b84a4a943b3d5f47807e`.
Startup is separate from soak windows in the PTY harness. A requested duration
in a failed-startup JSON is not an elapsed soak. Original baseline timeout
captures were terminated externally and are not accepted restoration tests.

Evidence: [baseline attempts](../evidence/updi/baseline-sib/results.csv),
[patched attempts](../evidence/updi/final-sib/results.csv),
[first upstream failure](../evidence/updi/baseline-default-trace.stdout),
[status snapshot](../evidence/updi/status-snapshot.txt), and
[terminal gate](../evidence/updi/final-terminal-gate.json).
Each attempt retains stdout/stderr separately, and each capture records the
firmware hash, baud, reset setting, unverified wiring and first failure.

## 6. Commands and reproducible diffs

Run from the project root:

```sh
pio run
# Already performed once for H; do not repeat during reconnection tests:
pio run -e receiver -t upload
bash tools/updi-sib.sh evidence/updi/new-sib
.venv/bin/python external/upditerm/upditerm.py /dev/ttyUSB0 38400
# Exit: press Ctrl+E, release, then press e.
.venv/bin/python tools/updi-session.py 38400 120 H evidence/updi/new-H
.venv/bin/python -m unittest discover -s test -v
fuser /dev/ttyUSB0
graphify update .
```

After H acceptance, change only receiver output/cadence to HELLO every second,
build/upload once, and capture with `... 38400 120 HELLO ...`. Only after that
passes, use HELLO WORLD plus CRLF every second and `... 38400 600 WORLD ...`.
Retain host settings and wiring. Do not treat a count or transport failure as
an accepted session.

The [upstream patch](../patches/upditerm/0001-fail-fast.patch) contains every
upstream delta; [application instructions](../patches/upditerm/README.md) pin
the baseline. The [project diff](../evidence/updi/project.diff) compares the
three changed original files against their pre-task contents and includes
new tests and measurement tools. Reports, evidence and pinning instructions
are separate new artifacts rather than part of that source diff.
Both patches also pass reverse-application checks against the delivered files.

## 7. Delivery limits and next required evidence

This parent repository has no commits: all project files were already untracked
before implementation. Ordinary `git diff` therefore omits the project.
The new `stabilize-updi-console` branch preserves the active workspace; no
files were staged or committed. Changed original files are
`src/receiver/main.cpp`, `lib/updi_uart/updi_uart.c` and its header. New artifacts
are under `test/`, `tools/`, `docs/`, `patches/` and `evidence/updi/`.
The nested upstream checkout independently reports only `upditerm.py` modified.
An explicit [untracked-file inventory](../evidence/updi/untracked-files.txt)
records paths instead of treating the empty parent diff as a clean tree.

Graphify was updated with AST extraction; it reports parser limitations in the
upstream C headers and the pre-task header snapshot, and no symbols for the thin include adapters. The source and
build remain authoritative. The original compact bundle was not valid XML and
was not used as authoritative evidence.

Next required evidence is an inspected/measured physical topology and target
reset condition, including VCC at the target and adapter logic levels. No
successful established session has been observed, so classification as a
residual startup-only fault or a sustained-messaging fault is unsupported.
Native Windows execution, electrical measurements and all three soaks remain
unverified. The probe remains loaded; console stability is not claimed.
