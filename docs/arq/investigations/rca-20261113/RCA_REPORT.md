# Forensic RCA — reverse raw LoRa, 2026-11-13

## 1. Executive summary

The Tracker→Rudolph failure is not yet attributable to a specific physical cause.
Incident A established local Tracker TxDone and no Rudolph RxDone within its
15-second observation. Incident B instead lost Tracker UPDI observation after
the host issued SEND, before MCU command delivery or TX was confirmed.
These are separate failures and must not be counted as two RF losses.
Both original event journals and recorded hashes verify. A configuration concern
was independently identified: installed RadioLib disables SX127x errata fixes by
default, leaving AutomaticIFOn set in the captured RX state. Offline real-driver
tests characterize that concern but do not establish that it caused RF loss.
The strongest defensible verdict is **HARDWARE_MEASUREMENT_REQUIRED**.

## 2. Scope

ROOT CAUSE ANALYSIS ONLY. Offline tools/tests/documentation were added. No live
port opened, recovery/BREAK/reset sent, firmware flashed, RF transmitted, fuse or
production source changed. Earlier remediation text is not authorization under
the final RCA-only instruction. No subagents or other LLM investigators used.

## 3. Verified facts

See [evidence index](EVIDENCE_INDEX.md) and [findings](FINDINGS.md). A's62 and
B's74 original recorded hashes verify, with12 and8 raw/journal events respectively.
Archived sources, firmware hashes/embedded IDs and available configuration-source
identity relationships check. Six before/after image and protected-memory
comparisons pass across A, B and B's rollback. B's final standby remains a
historical observation; no fresh live-state claim is made here.

## 4. Incident timeline

| Incident | Confirmed chain | Unobserved boundary |
| --- | --- | --- |
|A `20261113T121506Z`|Host RX → RX_READY → SEND → RAW_TX → RAW_TX_DONE → Rudolph15000ms timeout|RF radiation, preamble/header history, defective endpoint |
|B `20261113T123620Z`|RX command103523328665310ns → active snapshot103524165113559 → READY103525089015341 → SEND103525089152263 → empty-response monitor failure|Complete MCU command delivery and every downstream TX/RX operation |
|B rollback `20261113T123837Z`|Application readback/preservation and fresh session0/ready1/overflow0/standby89|Prior transient power/reset history |

DERIVED B READY→SEND interval136922ns=0.136922ms. A's corresponding host interval
is64275ns. These are host receipt/issue ordering, not synchronized radio event
timing. Every MCU-local stream is kept separately in machine reports. Exact
monitor-exit timestamp and request start/end were not captured.

## 5. System architecture

Host Python runner → subprocess UPDIterm → USB adapter/switcher → dedicated
AVR128DA28 UPDI → one-byte firmware mailbox → command parser → RadioLib7.1.2
→ SPI1 → RFM95W → antenna path → remote RFM95W/AVR → UPDI log mailbox → host.
Physical names matter: role `receiver` is Tracker, transmitting in reverse raw;
role `sender` is Rudolph, receiving. Legacy loraboard code in iwing-tracker is
not this ARQ image. [Firmware](FIRMWARE_ANALYSIS.md), [power](POWER_ANALYSIS.md)
and [hardware](HARDWARE_ANALYSIS.md) analyses identify exact source/net boundaries.

## 6. Failure boundaries

For A: radio TX state machine completion is confirmed; radiation→remote RF
detection is UNKNOWN; software RxDone is not observed within the captured bound.
No received-packet metrics exist. For B:

```text
Host pipe SEND: CONFIRMED
Full command at MCU: UNKNOWN
Parser / startTransmit: UNKNOWN
TxDone / radiation / remote detection / payload: UNKNOWN
UPDI response read: FAILED (empty bytes)
Monitor process: EXIT OBSERVED (numeric status not retained)
Subsequent rollback: CONFIRMED from archived evidence
```

The exact first failed UPDI instruction is not recoverable: both mailbox LDS
and OCD LDCS use expected=None; no last request/thread trace exists for B.
An empty Python read does not itself identify a dead MCU, disconnected USB or
failed RF transmitter. See [UPDI analysis](UPDI_ANALYSIS.md).

## 7. Root cause hypotheses

[Matrix](HYPOTHESIS_MATRIX.md) ranks causal confidence separately from diagnostic
priority. P0: isolate the UPDI read boundary and supply/reset alternatives.
P1: inspect errata configuration concern and physically separate Tracker output
from Rudolph reception using a reference endpoint. H14 (insufficient mechanism
evidence) is strongly supported. H2 cleanup defect is confirmed but secondary.
No waveform evidence separates H3/H5/H6. No reference RF observation separates
H8/H9/H10/H12. OpMode bit3 alone does not justify a firmware edit.

## 8. Tests and analysis performed

E01: read original manifests, verify hashes, journal/raw equality, archived
source/config/image relationships and independent memory preservation.
E02/E03: inspect exact transport exception, candidate call paths, subprocess
lifecycle, trace capture limits and dead-peer cleanup behavior.
E04: offline byte-parser fixtures distinguish empty/partial/unexpected/truncated
responses; existing fake-serial tests exercise echo/ACK/read and thread failures.
E05: execute real SEND parser with fake radio for partial/wrong/repeated/overflow
commands and disconnected/full logger; no RF hardware linked.
E06: inspect core early reset capture, DA-specific flags/fuses and schematic
power path; no new supply/reset measurement.
E07: installed7.1.2 public fake-HAL characterization with errata switch0/1;
manufacturer register audit and upstream exact-diff applicability review.
E08/E09: conditional hardware decision table and synthesis in this report.

Commands and fresh outcomes are recorded in [VERIFICATION.md](VERIFICATION.md).
RED logs prove missing analyzer/harness behavior before implementation; GREEN
and full-suite logs are retained separately. Model results never establish RF.
Each offline command is bounded by input caps or subprocess timeout; on invalid
input the analyzer emits integrity failure/exit2 without changing input files.
Future physical experiments remain proposals, with explicit gates and stops.

## 9. Confirmed findings

See [FINDINGS.md](FINDINGS.md). New, relevant source finding: errata macro
disabled + captured DetectOptimize C3 vs documented AutomaticIFOn-clear rule.
Real-driver HAL tests show the existing switch changes modeled C3→43 and2F20→40
without changing915MHz or OpMode8D. This demonstrates configuration behavior,
not that the alternative receives real packets. No production flag changed.

## 10. Unresolved questions

Which LDS/LDCS failed? Was the complete SEND delivered? Did the target drive a
response that the adapter missed? Did MCU VDD or3V3-LORA collapse? Was there a
fresh reset, and did core logging survive it? Did Tracker radiate the intended
modulated packet? Could Rudolph receive a known-good reference source? Does
enabling the documented errata workaround alter the physical outcome?
Each missing discriminator is specified in the supporting power/hardware tables.

## 11. Root cause verdict

**HARDWARE_MEASUREMENT_REQUIRED.** Software/capture boundaries are partially
localized; RF root cause remains UNKNOWN. No evidence supports declaring a
specific component broken, a new BORF, or multiple independent physical defects.

## 12. Recommended corrective action

No physical repair is currently justified. First propose operation/address/thread
and monotonic transaction telemetry on the UPDI boundary, without relaxing ACK,
echo or length validation; the pre-existing last-request patch only partly
covers this requirement. Capture analog UPDI at target/adapter and both rails
before recovery. If stable transport/power is proven, propose a single-variable
evaluation of RadioLib's existing errata switch; do not simultaneously change
bit3, IQ, power, frequency or protocol. These proposals are **not implemented**.

## 13. Verification plan

Future authorization required for every live step. First passive schematic-aware
continuity and source-path checks with power off. Then a bounded non-RF command
exercise with first-failure trace and core-aware reset evidence;50 clean cycles
is a future acceptance target, not a result. Stop on any unexplained voltage,
reset, ownership or identity error. Preserve first failure before BREAK/reconnect.
Only after transport/supply evidence passes, use one bounded external-reference
RF test, then an isolated errata-switch comparison if warranted. Record actual
TX/RX snapshots, headers/packets/IRQ before cleanup and exact11-byte CRC-valid
payload. Reverse3/3 and H01–H04 remain future acceptance targets. Never rerun an
unchanged failed campaign merely to replace evidence.

## 14. Risks and limitations

Offline code cannot measure rail minima, antenna impedance, RF power or receiver
sensitivity. Published register semantics do not prove silicon behavior.
Original trial manifests are integrity records, not cryptographic authenticity
proof. Requests/response timings, process IDs/exit codes and in-trial continuous
ownership telemetry are missing. Detailed Semtech Rev7 was inspected; its old
standalone errata URL is unavailable via the supplied link. Third-party current
figures and generic adapter thresholds were not used as measurements.
No fresh hardware standby verification was attempted under RCA-only scope.

## 15. STAR summary

**Situation:** reverse RF failure followed by a distinct UPDI observation failure.
**Task:** isolate defensible boundaries without changing production or hardware.
**Action:** verify immutable evidence; trace firmware/transport; research primary
datasheets and exact driver; test read-only analyzer and isolated HAL/parser models.
**Result:** reproducible incident separation, confirmed errata configuration
concern, and precise missing measurements; physical root cause remains unconfirmed.
