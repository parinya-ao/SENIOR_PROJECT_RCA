# Long-Duration Hardware Soak Readiness — Final RCA Continuation

## S — Situation

Historical H01 tests produced 10 Gateway DATA `TX_DONE` events, 10 ACK-window timeouts, zero accepted ACKs, and a saved Tracker PORF transition in session 9. The Tracker RX-only control stayed in RX Continuous for 120.029947 seconds without a new observed POR. Tracker RX_DONE, DATA acceptance, and ACK TX were not captured in H01; the reset time and electrical cause remain unknown. The 915 MHz HF register-bank defect was corrected in source, and the diagnostic ARQ profile is now configured for 923 MHz at +2 dBm, but neither the radio registers nor RF exchange has been verified on hardware.

## T — Task

Implement a paced, restart-aware soak runner for one verified DATA/ACK session, then 10, 100, 1,000 sessions, and 1-, 8-, and 24-hour stages. Preserve the existing ARQ protocol, log every session, gate unsafe hardware conditions, and avoid claiming physical recovery without physical events.

## A — Action

1. Inspected the existing `tools/arq_trial.py` transaction, evidence bundle validation, firmware role mapping, and current regression tests. Reused the existing UPDI-monitor capture and live ARQ `campaign()` path.
2. Added the soak plan and stage ledger in `tools/arq_trial.py`: PHY airtime calculation, 60-second minimum pacing, sequential pass receipts, per-session validated retry/timeout metrics, monotonic duration checks, durable progress records, and `FAILED`/`INTERRUPTED` receipts with partial progress.
3. Kept hardware gates fail-closed. A no-confirmation soak CLI probe exited with code 2 before a physical campaign. The latest available preflight still reports unverified Tracker power/back-feed, SD socket state, and RF equipment/EIRP/authorization; see [SOAK_RESULTS.json](SOAK_RESULTS.json).
4. Raised DATA spacing to 10 seconds to keep the maximum 44-byte frame below the conservative 1% modeled airtime target. Updated the portable ARQ timing test to use the generated `ARQ_SPACING_MS` boundary.
5. Ran focused soak tests, the complete host validation stage, and clean firmware builds. The final host run passed 324 tests with one skip and no failures/errors; 15/15 target environments built, and eight candidate images were archived with matching hashes. Candidate images remain not flashed.
6. Checked official Semtech, RadioLib 7.1.2, Microchip, NBTC, Silicon Labs, and u-blox sources; details and applicability are in [SOURCE_RESEARCH.md](SOURCE_RESEARCH.md).

## R — Result

**Software readiness:** verified. Focused soak tests: 18 passed. Full host suite: 324 run, 1 skipped, 0 failed, 0 errors. Firmware: 15/15 target builds passed. Eight 923 MHz candidate image pairs were archived and hash-checked.

**Physical validation:** not started. No candidate was flashed; no radio register was read from hardware; no DATA, ACK, NACK, or retry occurred; no reset snapshot, voltage/current measurement, or independent RF observation was collected. All soak stages remain `NOT_RUN`, and no confidence interval is computed without hardware trials. The prior 120.029947-second RX-only control is historical and is not a completed soak stage.

**Root cause verdict: `PARTIALLY_ISOLATED`.** The known HF register-bank source defect and a soak-runner/test timing mismatch are addressed in source. The historical RF causality of the HF defect is unverified. The historical POR remains `POR_OBSERVED / ELECTRICAL_CAUSE_UNKNOWN`. Gateway DATA reception, Tracker ACK transmission, and Gateway ACK acceptance remain unknown.

**Deployment readiness:** not ready for FOTA integration. First obtain a physically verified, isolated Tracker supply/ground/UPDI arrangement, establish the SD guard condition, and document the compliant RF equipment/EIRP test setup. Then run the gated one-session stage before advancing the ledger.

## Required answers

| # | Question | Result in this run |
|---:|---|---|
| 1 | Were new diagnostic images flashed? | No. `FLASH_NOT_ATTEMPTED`; all candidate images are archived only. |
| 2 | Were actual radio registers verified? | No. There was no hardware readback. |
| 3 | Did Gateway DATA reach Tracker? | UNKNOWN; no RF transaction ran. |
| 4 | Did Tracker accept DATA? | UNKNOWN; no Tracker RX/application evidence was captured. |
| 5 | Did Tracker transmit ACK? | UNKNOWN; no RF transaction ran. |
| 6 | Did Gateway receive and accept ACK? | UNKNOWN; no RF transaction ran. |
| 7 | Did NACK work? | Host protocol tests cover NACK logic; physical NACK is UNKNOWN. |
| 8 | Did retransmission work? | Host tests cover retry logic; physical retry behavior is UNKNOWN. |
| 9 | How many sessions completed? | 0 new physical soak sessions. Historical H01 records two failed sessions. |
| 10 | How many sessions failed? | 0 attempted in this run; historical H01 had 2 `TIMEOUT_EXHAUSTED` sessions. |
| 11 | First-attempt success rate? | Undefined: no new physical sessions. |
| 12 | Eventual success rate? | Undefined: no new physical sessions. |
| 13 | Longest verified continuous operation? | No new interval measured. Historical RX-only control: 120.029947 seconds. |
| 14 | Did an unexpected reset occur in this run? | UNKNOWN; no target reset snapshot was taken. Do not interpret this as zero resets. |
| 15 | Which reset source was recorded? | No new source. Historical H01 session 9 recorded PORF; its physical cause is unknown. |
| 16 | Was reset time localized? | No; historical POR time is unknown and this run did not probe hardware. |
| 17 | Was MCU VDD measured? | No. |
| 18 | Was 3V3-LORA measured? | No. |
| 19 | Was actual Tracker power topology verified? | No; CP2102 3.3 V output path, ground, and back-feed remain unverified. |
| 20 | Did power A/B/A establish causality? | No; not run. |
| 21 | Did the HF correction improve RF? | UNKNOWN; source/build correction exists, but no physical A/B result exists. |
| 22 | Were multiple independent physical defects established? | UNKNOWN. The known Gate 1 host defect is separate; the HF defect's RF effect and POR mechanism remain unproven. |
| 23 | Which failures were fixed? | Soak host-runner behavior and timing-test assumptions were corrected. The HF bit correction and programmer role mapping are source/build verified only. The physical RF/POR failure is not fixed or verified. |
| 24 | Which hypotheses were falsified? | Host tests reject stage skipping, under-paced plans, and loss of old stage receipts. No RF or electrical hypothesis was physically falsified. |
| 25 | Which hypotheses remain unknown? | Tracker supply/transient, RF emission/reception, IRQ/application boundary, ACK path, and POR mechanism. |
| 26 | Lowest-level confirmed failure boundary? | Still unresolved. Historical evidence stops after Gateway TX_DONE and lacks Tracker RX_DONE capture; this run adds no physical boundary evidence. |
| 27 | Is the system reliable enough for FOTA? | No. End-to-end DATA/ACK has not passed on hardware. |
| 28 | Which soak stages passed? | None. All seven stages are `NOT_RUN`. |
| 29 | What is the next measurable risk? | First close physical power/back-feed, SD guard, antenna/EIRP, and RF authorization preflight, then execute one bounded DATA/ACK trial with reset and rail evidence. |
| 30 | What evidence supports this verdict? | This report, [SOAK_RESULTS.json](SOAK_RESULTS.json), [SHA256_MANIFEST.json](SHA256_MANIFEST.json), final host/build artifacts, and the linked historical RCA/preflight. |

## Evidence index

- [Soak stage plan](SOAK_PLAN.md) and [machine-readable schedule](SOAK_PLAN.json)
- [Physical stage outcomes](SOAK_RESULTS.json)
- [Implementation/TDD/build record](IMPLEMENTATION.md)
- [Primary-source log](SOURCE_RESEARCH.md)
- [15-target build results](../20261114T092808Z-soak-readiness-retry2/FIRMWARE_BUILD_RESULTS.json)
- [Eight archived candidate images](../20261114T092808Z-soak-readiness-retry2/candidate-builds-923.json)
- [Final host test log](../20261114T092808Z-soak-readiness-retry2/host-tests-final4.log)
- [Machine host measurements](../../../artifacts/rf-proof/20261114T095758Z/host-measurements.json)
- [SHA-256 evidence manifest](SHA256_MANIFEST.json)
- [Latest prior physical preflight](../20261114T044136Z-radio-only/HARDWARE_PREFLIGHT.json)
- [Historical incident report](../20261114T023251Z/FINAL_RCA.md)
