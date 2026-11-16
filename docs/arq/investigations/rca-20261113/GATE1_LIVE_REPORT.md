# Gate 1 live UPDI report — 20261113T153146Z

## S — Situation

The earlier reverse-RF failure (`20261113T121506Z`) and UPDI monitor failure
(`20261113T123620Z`) remain separate. The original UPDI incident returned
`b''` from a required low-level UPDI response and captured no TX_START/TX_DONE;
its reset, power and USB causes remain unknown. The formerly blocked Gate 1
(`20261113T142138Z`) issued0 STATUS requests because that authorization
prohibited the Monitor's standard two BREAK characters.

This live trial used the corrected authorization. The Tracker's identity was
verified. The Host sent the first `STATUS\n` request (`53 54 41 54 55 53 0A`)
through the UPDI mailbox. No Monitor output arrived in the120-second response
window, so the run stopped after request1.

## T — Task

Complete20 consecutive non-RF STATUS operations through the existing UPDI
Monitor path. Stop at the first failed operation, preserve raw transport and
Host evidence, and leave RF/programming/fuse functions untouched.

## A — Action

Source inspection and the reason for avoiding reset-capable identity probing
are recorded in [source audit](GATE1_SOURCE_AUDIT.md). The actual Monitor did
the authorized two BREAKs, SYNCH/ASI setup, read-only SIB and SIGROW identity
reads, OCD/mailbox setup, and one STATUS request. SIGROW returned signature
`1E 97 0A` and serial `42032240221092150158013400000000`, matching the Tracker
configuration. The adapter path was `/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0`
(`/dev/ttyUSB1`), CP2102, and no current port owner was observed.

Offline regression coverage passed **25 focused tests**. The full repository
suite passed **256 tests with1 skipped** before the live acquisition; a later
post-run verification passed **257 tests (256 passed,1 skipped)** after the
reporting correction. These are host tests, not hardware evidence. The run's original
preflight test log is in the evidence bundle; the later verification is also
preserved there.

The Host write trace contains the seven STATUS characters in order, and the
strict UPDI echo/ACK traffic completed without a low-level serial exception
before the deadline. The Monitor stdout file contains0 bytes. The transaction
did not produce BOOT/IDENTITY/STATUS/STATUS_END events, so the running
firmware build and application role were not confirmed. The exact acquired
MCU identity and the expected baseline firmware identity are in
[verdict.json](../../../../artifacts/arq/gate1-updi/20261113T153146Z/verdict.json).

At the response deadline, the bounded Host cleanup closed the serial handle;
normal UPDI-disable cleanup then reported `PortNotOpenError`. This cleanup
detail is preserved in `monitor.stderr.log`. After the deadline the Host did
not reconnect, reset the MCU or retry STATUS; only the existing normal cleanup
writes were attempted, and they failed because the port had already closed. The MCU's
post-disconnect OCD/UPDI state is UNKNOWN.

## R — Result

| Metric | Measured result |
| --- | --- |
| Gate 1 verdict | **GATE1_FAIL — STATUS_RESPONSE_TIMEOUT** |
| Tracker USB path | `/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0` |
| MCU signature / serial | `1E 97 0A` / `42032240221092150158013400000000` |
| Runtime firmware build and role | UNKNOWN; no STATUS identity event arrived |
| Monitor BREAKs / SYNCH operations | **2 / 8,114** |
| OCD setup / CPU reset call / resume events | PASS / **0** / **0**; observed reset cause UNKNOWN |
| STATUS attempted / passed / failed | **1/20 / 0 / 1** |
| STATUS application response timeout | **1** |
| Low-level UPDI response timeouts / mismatches before deadline | **0 / 0** |
| Unexpected Monitor exits | **0**; Monitor was embedded in the Host process, separate exit code not applicable |
| STATUS request bytes | `53 54 41 54 55 53 0A` (`STATUS\n`), all seven writes observed |
| Monitor stdout bytes | **0** |
| Failed request duration | **120,004.039 ms** from monotonic timestamps |
| Successful STATUS min/median/max latency | UNKNOWN; there were no successful STATUS responses |
| Focused offline tests | **25 passed, 0 failed** |
| Full suite | **257 run, 256 passed, 1 skipped, 0 failed** |
| Original archived files changed | **0/1,553** |
| Original incident bundles | **62 +74 +67** manifest entries checked; **0 hash mismatches** |
| Gate 1 evidence files / verified hashes / mismatches | 32 / 30 / 0 |
| RF transmissions / flash operations / fuse writes / EEPROM writes | **0 /0 /0 /0** |
| Root cause | **UNKNOWN** |

The first known failed boundary is the Monitor's application-output wait after
the Host submitted STATUS. Raw serial traffic records successful UPDI control
exchanges; it does not prove the firmware consumed the mailbox command or ran
its STATUS handler. The evidence therefore does **not** establish a low-level
UPDI framing fault, MCU reset, power failure, USB disconnect or firmware defect.
PESIG was not read. No low-level UPDI transport exception occurred before the
STATUS timeout; no recovery or diagnostic command followed the failed request.

The raw request/response stream is
[transport-trace.jsonl](../../../../artifacts/arq/gate1-updi/20261113T153146Z/transport-trace.jsonl).
The failed transaction is
[status-transactions.jsonl](../../../../artifacts/arq/gate1-updi/20261113T153146Z/status-transactions.jsonl),
and file integrity is recorded in
[integrity-report.json](../../../../artifacts/arq/gate1-updi/20261113T153146Z/integrity-report.json).

## Findings

**OBSERVED:** correct Tracker port, AVR128DA28 signature and serial; standard
two-BREAK setup; Monitor/OCD mailbox initialization; one complete Host STATUS
command transmitted; low-level UPDI polling responses continued until timeout;
no Monitor output bytes; the first STATUS timed out and the run stopped.

**DERIVED:** the STATUS command took120.004039 seconds to reach the Host deadline.
Its seven command bytes were captured in order. Earlier `0x00` bytes are valid
OCD status polls in the transport trace; they are not empty or malformed UPDI
responses.

**UNKNOWN:** whether application firmware consumed STATUS, whether the expected
firmware build is installed now, the CPU's reset history, target voltage during
the test, PESIG, and the target's UPDI/OCD state after the Host closed the port.

## Next step

Stop Gate 1 at its first failed STATUS, as required. Preserve this result. A
future, separately bounded diagnostic should capture the volatile mailbox flags
and RX byte around STATUS together with OCD message readiness before changing
the command path. This run does not establish 20/20 STATUS stability. Gate2,
Gate3, RF and ACK/NACK were not attempted.
