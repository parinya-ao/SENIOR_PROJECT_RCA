# Proposed discriminating experiments — NOT executed or authorized here

FACT: RCA-only scope prohibits live serial access, programming, resets, RF and
repairs. This document specifies reviewable future work; it does not enable it.
Operator antenna/module/bridge confirmation remains recorded and is not being
requested again. Continuity, impedance, radiation and supply stability remain UNKNOWN.

## Evidence-ranked hypothesis matrix

FACT: six grouped mechanisms below cover the original H1–H14 matrix. None has a
confirmed physical cause. HIGH means directly observed support for a boundary,
MEDIUM a source-supported candidate, LOW a plausible unmeasured mechanism;
INSUFFICIENT_EVIDENCE means causal ranking cannot be resolved. No probabilities.

| Group / original IDs | Supporting FACT | Contradicting / limiting FACT | HYPOTHESIS confidence | Measurement supporting the mechanism | Observation rejecting/narrowing it |
| --- | --- | --- | --- | --- | --- |
| G1 endpoint TX/RX path / H7–H9 | A: one TxDone, one15000ms timeout | No reference endpoint or RF measurement; TxDone is local | INSUFFICIENT_EVIDENCE | Tracker fails a calibrated compatible reference while Rudolph passes one, or converse, with RF/transport/config controls valid | Both endpoints exchange exact CRC-valid payloads with the reference at controlled levels; gross endpoint failure rejected, pairwise mechanisms remain |
| G2 feedline/matching/PA/power / H6,H12 | Weak reported forward RSSI; switched radio rail by design | Visual antenna checks passed; register PA_BOOST selection matches intent; H1 may bypass U7 | LOW | Synchronized abnormal rail waveform at failure, or measured insertion loss/output deficit localized across connector/matching path | Rails remain within device/clock limits through failure and calibrated feedline/output measurements pass; only those measured submechanisms rejected |
| G3 receiver IF / H10 | ActiveRX C3, workaround disabled, documented BW125 IF tuple | Default intentionally disabled; forward interoperability exists; no matching off-channel interferer recorded | MEDIUM configuration candidate, LOW causal | Reproducible A-fail/B-pass/A-fail with only receiver IF treatment changed, complete evidence and readback | Both variants fail identically with valid evidence; or A succeeds equally. This rejects sufficiency/necessity under tested conditions, not every IF interaction |
| G4 carrier/PHY / H10 | No measured oscillator offset or Tracker active-TX snapshot in B | Nominal standby PHY matches, E4C000 on both; active Rudolph RX profile consistent | LOW | Independent actual carrier/PHY capture shows an incompatible setting or excessive offset during failed transfer | Reference instrument verifies compatible waveform/carriers with appropriate margin while failure persists |
| G5 UPDI/MCU reset / H1,H3,H5 | B: empty response and monitor exit after hostSEND | No failed instruction/bytes, PESIG, reset generation or voltage capture; A completedTX | HIGH transport boundary; INSUFFICIENT_EVIDENCE mechanism | Common-time trace: target response lost between MCU and adapter, malformed host frame, or direct fresh reset/rail event correlated with silence | Clean decoded UPDI frames and continuous target execution through an independently captured failure reject a reset in that observation; they do not retrospectively settle B |
| G6 receive event lifecycle / H4,H11 | Missing RxDone could occur upstream or be consumed | Source polls IRQ, captures before read/clear, rejects repeatRX, givesRxDone priority; host regressions pass | LOW | SPI shows RxDone set then cleared/overwritten before handler consumption, or captured valid event is lost by logger/parser | Independent radio/SPI evidence shows no RxDone despite verified compatible input; move investigation upstream |

UNKNOWN: all six groups remain possible; the parent matrix's H2 peer-cleanup
defect is already source-localized and secondary. H13 multiple causes and H14
insufficient evidence remain logical alternatives, not extra demonstrated faults.
No binary reference test by itself proves a specific solder joint/module defective.

## Gate 1 — transport and power evidence

HYPOTHESIS / proposed test: after separate hardware authorization, make **20/20**
non-RF STATUS transactions, one outstanding command at a time, deadline120s
after startup acquisition (separately bounded45s). Require complete status/build
identity and zero overflow/response mismatch. End on the first failure, preserve
it and stop. STATUS involves mailbox writes and the monitor initializes UPDI/OCD;
it is not electrically passive or reset-free by definition. No automatic recovery
or repeated BREAK may erase the first error state. Passing idle STATUS does not
prove stability during TX load.

HYPOTHESIS / proposed measurement: capture analog UPDI at the MCU pin and adapter
RX, MCU VDD at its decoupling, and radio3V3-LORA across C11/C8 on a common timeline.
Use measured adapter supply/datasheet thresholds and decode38400/8E2. Preserve
last complete host request, expected length/value, received bytes, thread and
transaction timestamps. Read PESIG only with an explicit record that the read
clears it; do not disable strict echo/ACK checking. Correlate core-saved GPIOR0
with a startup generation before any programmer reset. Without this evidence,
host disconnect remains an unknown electrical/target/adapter cause.

FACT: PA7 is enabled in board_ssot_init during setup, not toggled by SEND.
HYPOTHESIS: TX load can still expose a rail problem; Q1 switching precisely at
SEND is not established by source. UNKNOWN: runtime BOD state and supply minima.
Do not change BOD/SUT fuses, bypass Q1, add capacitors or disconnect UPDI as an
RCA shortcut. Existing --reverse-raw controls SEND over UPDI; unplugging its cable
does not create a working UART-controlled experiment.

## Gate 2 — receiver-only IF A/B

HYPOTHESIS / proposed minimum candidate: build an isolated **Rudolph reverse-raw
RX** image with the installed7.1.2 `RADIOLIB_FIX_ERRATA_SX127X=1` option; baseline
A uses0. At fixedBW125 the driver executes only relevant receiver IF treatment
from its errata path. It does not execute BW500 sensitivity writes. Do not set
the option globally or change Tracker TX. No candidate image was built/flashed here.

HYPOTHESIS / proposed controls:

1. Separate explicit hardware-test authorization, stable transport evidence,
   still-valid antenna confirmation, exact MCU serial/signature/USB path and port
   ownership; verify fuses/unlocked lock and bounded application region.
2. Independently read back baseline and candidate images and compare protected
   flash/EEPROM/fuses. Keep Tracker's exact binary SHA256 unchanged; record new
   Rudolph build identities. No chip erase, fuse write or BOOTSIZE change.
3. Same diagnostic observations in A/B: activeRX01/06–08/0B/0C/11/1D/1E/26/2F/30/31/
   33/36/37/39/3A/3B/40/42/4D and IRQ/counter timeline. Existing23-byte snapshot lacks
   several of these: separately authorize an identical isolated diagnostic extension
   in both variants if required. A/B is invalid until required readbacks exist.
4. A records its actual baseline IF values; do not substitute model2F=20 for a
   physical measurement. B requires31=43 (given baselineC3),2F=40,30=00 and36=03.
   Keep OpMode8D, FrfE4C000, SF7/BW125/CR4/5, preamble8, sync12, CRC/normalIQ and
   Tracker+2dBm. Keep position, antennas, power source and packet count unchanged.
5. Verify actual RX_READY rc0 and active continuous mode on the host timeline
   before SEND, within the still-open15000ms RX interval. Preserve the interval,
   not independent MCU uptime differences. Snapshot registers in standby before
   starting RX or buffer compact observations; never block active RX on serial logs.

HYPOTHESIS / proposed initial pair: **one A packet and one B packet**, exactly
11 raw bytes `48656C6C6F20576F726C64`, no framing/ACK/retry. RX deadline15s per arm,
TX deadline3s, full host acquisition/drain deadlines and preserved terminal events.
Both require TxDone plus intact RX evidence; only RxDone, CRC present/valid and
exact payload constitute a reception. A zero packet counter is not a failure
criterion. Preserve timeout before cleanup. Independently attempt X for both
peers; restore/readback normal unarmed standby and preservation afterward.

HYPOTHESIS / preregistered decisions:

- A fails / B passes: IF treatment is supported as a candidate. If separately
  authorized for replication, two further alternating pairs (maximum6 total
  packets) test repeatability and reversal. A single success is not root cause.
- Both fail with complete evidence: stop this comparison after2 packets and
  use reference isolation; no unchanged repeats.
- Both pass: IF workaround is not necessary for that observation; intermittent
  transport/environment remains unresolved.
- A passes / B fails: reject candidate for this condition, restore baseline.
- Missing terminal log, overflow, new reset, identity mismatch, uncertain antenna
  or unexplained state: INCONCLUSIVE; stop, preserve, restore. Do not score RF loss.

## Gate 3 — reference isolation and business ranking

HYPOTHESIS / proposed endpoints: use a verified compatible915MHz reference with
samePHY. One bounded11-byte burst per direction: Tracker→reference, then
reference→Rudolph (15s RX each, no automatic repeats). ExactCRC-valid payload is
PASS. Spectrum energy alone verifies radiation/frequency/envelope, not payload
or receiver compatibility. A failed reference test is interpretable only after
reference calibration, timing and capture integrity pass.

| FACT: future outcome definition | HYPOTHESIS narrowed | Still UNKNOWN |
| --- | --- | --- |
| Tracker→reference PASS, reference→Rudolph FAIL | Rudolph-side RX/feed/config under these conditions | Exact failed component, sensitivity and environmental effects |
| Tracker→reference FAIL, reference→Rudolph PASS | Tracker-side TX/feed/config under these conditions | PA output vs feedline vs waveform without instrument localization |
| Both PASS, original pair fails | Pairwise offset, interference, timing or marginal conditions | Which mechanism until simultaneous measurement |
| Both FAIL | No endpoint isolated | Reference validity, common config, multiple faults |

HYPOTHESIS / planning estimates below assume existing/borrowed instruments and
one engineer; they are not measured durations, price quotes or guaranteed
eliminations. USD0 means **incremental hardware spend only**, excludes labor.
If equipment is unavailable its cost is UNKNOWN—obtain a local quote rather than
inventing an instrument price. Rates are possible branch decisions/hour, not
probabilities that a fault will be found.

| Priority / proposed action | Estimated hours | Incremental hardware USD | Potential decisions / hour | Reliability risk |
| --- | --- | --- | --- | --- |
| 1: idle20/20 status + synchronized UPDI/rail capture setup |0.5–1.5|0 if available; otherwise UNKNOWN quote|1–3 branches /0.5–1.5h ≈0.7–6; idle pass alone eliminates0 TX-load causes|Low non-RF; monitor/OCD changes must be accounted for |
| 2: one receiverIF A/B pair after gates |1–2|0 with existing boards|1 candidate /1–2h =0.5–1; physical improvement may remain ambiguous|Moderate programming/RF; bounded writer/readback/rollback mandatory |
| 3: two reference-direction tests |0.5–1.5 with configured reference|0 borrowed; otherwise UNKNOWN quote|Up to2 endpoint branches /0.5–1.5h ≈1.3–4|Moderate RF/instrument coupling; attenuation/range required |
| 4: calibrated output/carrier/feedline/sensitivity localization |1–3|0 existing lab; otherwise UNKNOWN quote|1–3 mechanism branches /1–3h ≈0.3–3|Moderate probe/load damage risk; competent bench setup |

HYPOTHESIS / recommendation: use available scope/logic capture first because it
addresses the current P0 transport boundary with no RF. A compatible borrowed
reference can isolate endpoints faster than a full A/B campaign; after transport
gates choose it first if available. Without a reference, the specified receiver
A/B is the smallest software treatment. None of these steps authorizes increased
power, antenna swaps, fuse changes or a new protocol. ACK/NACK remains outside
scope until physical reverse raw is demonstrated.
