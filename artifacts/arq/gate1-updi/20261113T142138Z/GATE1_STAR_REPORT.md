# Gate 1 STAR report — 20261113T142138Z

**GATE1_BLOCKED — UNSAFE_COMMAND_PATH. STATUS attempted: 0/20.**
Specific preflight disposition: **GATE1_BLOCKED_UNSAFE_COMMAND_PATH**.
The existing UPDI constructor unconditionally sends two BREAKs. These are
explicitly prohibited by this Gate 1 authorization. No target connection was
opened, no monitor was started and no STATUS request was issued.

## S — Situation

OBSERVED: Incident A, `20261113T121506Z`, recorded one local Tracker TxDone and
one Rudolph 15000 ms RX timeout: PHYSICAL_RF_FAILURE_UNISOLATED. Incident B,
`20261113T123620Z`, recorded `UPDI response mismatch: expected None, received
b''`: HOST_TRANSPORT_ERROR, RF INCONCLUSIVE. The latter represents zero returned
bytes at a response check, not evidence of an MCU reset, literal byte62, USB
removal or RF transmission. No TX_START/TxDone was captured in Incident B.

OBSERVED: these classifications were reproduced offline in
[Incident A analysis](20261113T121506Z-reverse-raw-analysis.json) and
[Incident B analysis](20261113T123620Z-reverse-raw-analysis.json).
Incident B's 74 original recorded file hashes match, with 0 mismatches and 8
journal events. Supplemental follow-up evidence is identified separately by
the existing analyzer; historical files were not rewritten.

OBSERVED: the historical follow-up log really says **232 run, 231 passed,
1 skipped**. Its preservation record enumerates **1553 original files**;
all 1553 matched again before this task. These are historical results, not
Gate 1 measurements. See [historical verification](historical-verification.json).

## T — Task

Establish 20 consecutive non-RF STATUS transactions, maximum45 seconds for
acquisition and120 seconds after acquisition, stopping at the first failure.
Hard constraints prohibit automatic BREAK/recovery, forced resets, RF,
programming and persistent-memory changes. Safe acquisition and verified
identity must precede STATUS. A documented BLOCKED result is the required
outcome when this command path cannot satisfy those constraints.

## A — Action

### Source inspection and safety decision

OBSERVED: repository HEAD is `1e2dd303e2ca63b93826df030e8fd116683d7284`,
branch `fix/receiver-rfm-rev1-pins`; 590 pre-existing dirty/untracked entries
were recorded before changes. Full status is in
[source revision](source-revision.json). The active ARQ implementation and
archives are in `SENIOR_PROJECT_RCA`; the supplied `loraboard` path is in the
separate `iwing-tracker` repository. The firmware currently installed on a
physical board was **not** established from a filename or historical report.

OBSERVED: [command-audit.md](command-audit.md) answers all ten safety questions
with file/line references. The decisive source is
`third_party/upditerm/upditerm.py:172–180`: opening UPDI sends two BREAKs and
disables contention detection. `SerialUPDI` additionally presents the OCD key
and writes virtual-UART enable. Its polling path at253–258 can restart a stopped
CPU automatically; destructors also write to the target. Omitting the `-r` flag
does not suppress these operations. The `-i` identity path has the same BREAK
constructor. Therefore neither monitor startup nor identity probing was run.

OBSERVED: STATUS itself is `53 54 41 54 55 53 0A` through volatile GPIOR2/3
mailboxes. Its firmware handler logs state and reads radio registers without
starting TX/RX or writing NVM. This source observation does not prove the
current target is unarmed, or override unsafe acquisition.

### OS-only port identification

OBSERVED: sysfs/udevadm discovery found two CP2102 adapters:

| Device | USB location | Reported USB serial |
| --- | --- | --- |
| `/dev/ttyUSB0` | `usb-0:4:1.0` | `0001` |
| `/dev/ttyUSB1` | `usb-0:1:1.0` | `0001` |

OBSERVED: there were 0 visible port owners and 0 matching live monitor/programmer
processes. Permission restrictions prevented inspection of330 process
directories; ownership is therefore **not fully verified**. Duplicate adapter
serials do not establish a target MCU identity. Current Tracker device path,
MCU signature/serial, firmware identity and readiness remain UNKNOWN. Historical
expected identity is preserved separately in [preflight.json](preflight.json),
including the last restored Tracker image hash; it was not promoted to a live
identity check. No process was killed. See [port discovery](port-discovery.json).

### Offline diagnostics and tests

OBSERVED: added only `tools/rca/gate1.py` and `tests/test_gate1_rca.py` as new
host-only diagnostic source. The assessor reuses existing STATUS parsing and
UPDI-error parsing, defaults to BLOCKED unless an external safety audit is
supplied, and has no serial, programming or recovery execution API. The tests
use synthetic records exclusively. The pure assessor validates response
length/value, complete status events, identity, zero overflow/unarmed session,
sequential indices and monotonic times; it stops consuming a replay at the
first failure. Missing response bytes remain UNKNOWN; captured empty bytes
remain length0. A monitor exit is never promoted to USB removal or reset.

OBSERVED: RED first failed because the assessor did not exist. A second focused
RED exposed missing latency reporting for successful records before a replayed
failure; a minimal host-only change fixed it. **18/18 focused tests pass**,
covering T01–T18; **250 total tests run =249 passed +1 skipped,0 failures/errors**.
The existing obsolete BOOT-repair class remains skipped. Two existing C++
warnings about `tests/radiolib_hal_test.cpp:69` occur in the older RCA harness;
they are recorded in the full log and were not hidden or repaired here.

Exact verification commands, executed through RTK:

```sh
uv run python -m unittest tests.test_gate1_rca.Gate1Tests.test_T01_twenty_successes
uv run python -m unittest tests.test_gate1_rca.Gate1Tests.test_T02_first_failure_stops_consumption
uv run python -m unittest -v tests.test_gate1_rca
timeout 120s uv run python -m unittest discover -v -s tests
```

The full suite used the already available host toolchain:

```sh
export PATH="$PWD/.automation/ack-investigation/toolchain/root/usr/bin:$PATH"
export CPLUS_INCLUDE_PATH="$PWD/.automation/ack-investigation/toolchain/root/usr/include/c++/16:$PWD/.automation/ack-investigation/toolchain/root/usr/include/c++/16/x86_64-redhat-linux:$PWD/.automation/ack-investigation/toolchain/root/usr/include/c++/16/backward"
export LIBRARY_PATH="$PWD/.automation/ack-investigation/toolchain/root/usr/lib/gcc/x86_64-redhat-linux/16"
```

OBSERVED: [runtime versions](runtime-versions.json) distinguishes shell
Python3.12.16 from the `uv run` test interpreter Python3.14.10. Pyserial3.5,
UPDIterm source1.1, uv0.13.7 were recorded. Pymcuprog and PlatformIO package
metadata are absent in that test interpreter; a first metadata query failed
and was recorded. No dependencies were installed/upgraded. No programmer was
started. Existing configured programmer environments were not invoked.

OBSERVED: `graphify update .` refreshed the AST graph; no LLM labeling was run.
`git diff --check` and the evidence checks are recorded in
[integrity report](integrity-report.json).

### Forensic preservation

OBSERVED: `transactions.jsonl`, `transport-trace.jsonl`, monitor stdout and
stderr are deliberately empty because **no live transaction/monitor exists**.
They are not missing captures from an attempted trial. No new
`first-failure.json` was manufactured; `verdict.json` records first_failure=null.
The archived Incident B error remains linked historical evidence.

OBSERVED: no PESIG read was attempted. STATUSB is read-to-clear according to
the device-specific Microchip DS40002183C p553. There was no live failure to
justify disturbing target error state; **PESIG_NOT_CAPTURED** is explicit.
No new MCU reset, supply voltage or electrical waveform observation exists.

OBSERVED: all1553 historical baseline files and an extended1929-file snapshot
of existing sources, tests, tools, configuration, documentation and artifacts
are compared before/after. Source hashes, actual command descriptions, raw
historical exception and monotonic audit-recording events are preserved.
Hashes are finalized after reporting; the hash map excludes itself and its
verification report, explicitly avoiding a circular self-hash.

## R — Result

| Metric | Actual result |
| --- | --- |
| STATUS attempted | **0/20** |
| STATUS passed / failed / timed out | **0 /0 /0**; none attempted |
| New monitor starts / unexpected exits | **0 /0** |
| New response mismatches / identity mismatches | **0 /0**; no live checks attempted |
| Current target identity / ownership fully verified | **UNKNOWN / no** |
| First failed live transaction | **NONE — no attempts** |
| STATUS minimum / median / maximum latency | **UNKNOWN / UNKNOWN / UNKNOWN**, no live timestamps |
| Focused offline tests passed / failed | **18 /0** |
| Full suite run / passed / skipped / failed | **250 /249 /1 /0** |
| Original historical files changed | **0/1553** |
| Extended original snapshot files changed | **0/1929** |
| Evidence files / recorded hashes / mismatches | **33 files /31 recorded hashes /0 mismatches**; [integrity-report.json](integrity-report.json) |
| Existing production files changed | **0** |
| RF transmissions / firmware flashes / target resets initiated by this run | **0 /0 /0** |
| Gate1 verdict | **GATE1_BLOCKED**, classification **UNSAFE_COMMAND_PATH** |
| Root cause of historical transport failure | **UNKNOWN** |

DERIVED: a 20/20 non-RF stability claim cannot be made from0 transactions.
Integrity PASS means recorded files match hashes; it does not make live
evidence complete. Live evidence completeness is INCOMPLETE/NOT_EXECUTED;
the blocked preflight report is complete and independently reviewable.
No 45-second acquisition or120-second STATUS timer was started because safety
preflight failed first. No Gate2/Gate3 operation was performed.

## Findings and hypothesis review

OBSERVED: the **blocking command path** is source-isolated; this is not the
physical cause of Incident B. The original response check failed, but the
specific historical UPDI operation/request is unavailable. Later last_tx
instrumentation cannot recover it. Later restoration does not establish
absence of an earlier reset or transient.

| Hypothesis | Current evidence / confidence | Single discriminating observation |
| --- | --- | --- |
| H1 serial framing | HYPOTHESIS; empty response, no waveform. INSUFFICIENT_EVIDENCE | Synchronized raw8E2 trace identifying a corrupted turnaround/frame versus a clean reply |
| H2 adapter/port | HYPOTHESIS; two adapters visible now, no historical disconnect proof. INSUFFICIENT_EVIDENCE | MCU-pin reply compared with adapter RX and host receive bytes at the same failure |
| H3 MCU reset | UNKNOWN; no new reset generation captured | Retained startup generation/reset cause captured before recovery/programming |
| H4 firmware mailbox | UNKNOWN; full historical command delivery unconfirmed | Confirmed mailbox writes and matching MCU command/response trace |
| H5 host parser | No reproduced parser defect; strict length check rejects b''. INSUFFICIENT_EVIDENCE for blaming parser | Same complete captured wire response rejected reproducibly by the unchanged parser |
| H6 power integrity | HYPOTHESIS only; no voltage measurement | Synchronized MCU VDD/3V3-LORA waveform at exact empty response |

UNKNOWN: current MCU/firmware identity, electrical signaling, reset cause,
PESIG, current radio state, STATUS reliability and historical physical failure
mechanism. No oscilloscope measurement was invented. The offline synthetic
latencies and injected failures are not physical results.

## Recommendation — exactly one next experiment, not executed

Propose **one separately authorized, instrumented, non-RF UPDI acquisition**:
explicitly authorize the two necessary startup BREAKs and documented OCD/mailbox
setup, with automatic CPU restart/recovery excluded and offline-verified before
execution. Record every request/echo/response and stop at the first error; use
the45-second acquisition bound. Confirm the MCU and firmware identity through
the audited permitted path. This would test whether the earliest unsafe-to-run
boundary here can be crossed reliably and localize a startup transport failure.
Do not infer permission from this recommendation. No RF, programming, power
cycle, fuse operation or Gate2/Gate3 action is part of it.
