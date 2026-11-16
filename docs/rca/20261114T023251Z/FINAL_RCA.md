# Final RCA — AVR128DA28 Tracker / RFM95W ARQ V1

## Executive summary

Gate 1 STATUS and reverse RF are separate issues. The prior Gate 1 root cause was a short-address STS encoding that did not write AVR-DA GPR mailbox bytes; the corrected 16-bit STS path passed 20/20 live non-RF STATUS transactions. A later source audit found a separate confirmed SX127x configuration defect: the 915 MHz program left `RegOpMode` bit 3 set (`0x8D`, LF bank selected). A test-first correction now selects HF mode in an unflashed candidate; its effect on RF remains untested. In two reader-free H01 sessions, Tracker was verified in RX Continuous before DATA; Gateway logged five DATA `TX_DONE`s per session and ended `TIMEOUT_EXHAUSTED` without accepting an ACK. Session 8’s post-window reset read was incomplete; session 9’s fresh UPDI/OCD session with no CPU reset read `GPIOR0=0x01`, confirming a new POR. A matched 120.03-second Tracker RX-Continuous idle control with the same Tracker image kept `GPIOR0=0x20` and showed no POR. This associates the reset with packet-exchange activity, but no Tracker RX_DONE/ACK event survived and the reset time within the exchange is unknown. The operator reports the board is powered from the UPDI adapter’s 3.3 V feed; CP2102’s specified regulator output limit is 100 mA, making that supply path a plausible hypothesis. No rail voltage, current, or radiated RF was measured. The electrical cause remains unproven.

## STAR — Situation

Tracker is physically the AVR128DA28 board with the RFM95W and active-low PA7 radio power gate. Gateway is the other AVR128DA28/RFM95W board. The reverse experiment is Tracker DATA TX → Gateway RX; H01 is Gateway DATA TX → Tracker RX, followed by Tracker ACK TX → Gateway RX.

Historical Incident A (`20261113T121506Z`) remains `PHYSICAL_RF_FAILURE_UNISOLATED`. Historical Incident B (`20261113T123620Z`) remains `HOST_TRANSPORT_ERROR / RF INCONCLUSIVE`. They were not rewritten or merged.

## STAR — Task

Find the earliest observed failure boundary for STATUS and radio ARQ, use the hardware available, and avoid speculative production fixes. No oscilloscope, logic analyzer, SDR, spectrum analyzer, or voltage logger was available. All Python tests and tools were run with `uv`.

## STAR — Action

1. Read the previous RCA, active SSOT, host runner, Monitor, firmware path, local RadioLib package, and the original evidence before new experiments.
2. Verified the active project uses Tracker image start 0/BOOTSIZE 0 and that the build matches current SSOT. The legacy `receiver_boot.py` 0x5800 layout was not used.
3. Evaluated upstream RadioLib 7.1.2, its build options/release notes, Upditerm, pySerial miniterm, and pymcuprog. Reused the installed RadioLib and local Upditerm; imported no new library.
4. Added test-first, host-only H01 summary and reader-free diagnostic paths. The tests cover unknown missing events, POR transitions, safe CLI dispatch, firmware identity binding, reset resync without CPU reset, and complete-line output drain. A six-second split-line test first failed on the old drain behavior, then passed after the reader waited for line completion or timeout.
5. Ran one reader-attached H01 trial. The Tracker Monitor lost an UPDI response while the event stream was incomplete; the runner refused a protocol verdict.
6. Ran reader-free H01 with same Tracker/Gateway ARQ test images, verified identities, STATUS, and RX Continuous modes. Gateway DATA reached local `TX_DONE` five times, then exhausted retries. Tracker’s first post-window GPIOR read failed with an UPDI echo mismatch. One fresh double-BREAK/OCD connection, with no CPU reset, read PORF in GPIOR0.
7. Ran a matched 120-second Tracker RX-only control using the same Tracker test image and no Gateway RF transmit. Tracker remained in `0x8D` RX Continuous; reset flags did not change.
8. Restored normal ARQ images and verified standby on both boards. Fuses, EEPROM, lock, signature, and serial readbacks were unchanged in the bounded programming snapshots.
9. After the hardware phase, compared the captured 915 MHz radio state with the installed RadioLib 7.1.2 and Semtech datasheet. Added a failing register assertion, then corrected the application’s HF/LF mode bit. Focused tests and six builds passed; the candidate was not flashed and no RF test followed.

The repository HEAD advanced from the starting commit `cad40a9` to `f8092bc` during this investigation through repository commits. The investigator did not commit; each physical bundle records the source revision used for its firmware.

## STAR — Result

### Confirmed findings

- **Gate 1 STATUS:** the STS-width defect is confirmed and corrected in the host UPDI writer. The preserved live bundle records 20/20 STATUS passes. This is not RF evidence.
- **Program configuration:** the old ARQ source left `LowFrequencyModeOn=1` at 915 MHz; the H01 readback was `RegOpMode=0x8D`. The source candidate now clears bit 3; this config defect is confirmed, but its causal contribution to H01/reverse RF is not yet tested.
- **H01:** across two reader-free sessions, Gateway recorded ten DATA TX completions, ten ACK-window timeouts, and two `TIMEOUT_EXHAUSTED` terminals; no ACK was accepted.
- **Tracker reset:** before H01, `GPIOR0=0x20`, `RSTFR=0`; after the H01 window and a no-CPU-reset fresh UPDI/OCD session, `GPIOR0=0x01`, `RSTFR=0`. This confirms a POR occurred during the interval. It does not date the reset to a specific frame or instruction.
- **Matched control:** the same Tracker firmware stayed in RX Continuous for 120.029947 seconds with `GPIOR0=0x20`, `RSTFR=0`, and zero RF transmissions.
- **Historical forward PHY:** the earlier raw log contains explicit CRC-clean `Hello World` RX rows 15, 16, and 17; the counter began at 14. This proves forward PHY reception in that earlier run, not ARQ ACK success now.
- **Preservation:** the three historical manifests covered 221 files with 0 missing and 0 hash mismatches. The final H01 bundle has 75/75 matching listed files; the RX-idle bundle has 44/44. At the end of the physical experiment phase, the 1,553-file project baseline had 7 changed entries. A later source audit added a test-first correction for the 915 MHz SX127x HF/LF selection bit; it is not flashed on hardware. See [program source findings](09_PROGRAM_SOURCE_FINDINGS.md).
- **Tests/builds:** the source follow-up focused suite passed **82/82**. All **6/6** PlatformIO environments built successfully. Full unittest discovery ran **285 tests**, with **2 skipped** and **7 errors** because host `g++` is unavailable; the errors are compiler-start failures, not assertion failures. The register test was observed red before the source correction and green afterward.

### Remaining hypotheses

- **HIGHLY_SUPPORTED:** a Tracker power/reset event is associated with packet-exchange activity. POR was observed in three active-radio windows across reverse-raw and H01; the matched RX-only control did not POR.
- **POSSIBLE:** the reported CP2102-fed 3.3 V source, H1 path, cable, connector, or ground lacks transient margin. The CP2102 100 mA regulator rating and H1 bypass path make this measurable, but actual wiring/current/voltage are unknown.
- **UNKNOWN:** whether Tracker detected DATA, entered application parsing, accepted it, or began ACK TX before POR. No post-window Tracker RX/ACK event survived.
- **UNKNOWN:** whether Gateway radiated RF despite its local TxDone. No independent receiver or RF instrument was available.
- **POSSIBLE:** SX127x receiver configuration/IF behavior contributes to missed reception. It does not explain POR by itself; no errata A/B was run.

### Evidence index

- [Reader-free H01 session 8 bundle](../../../artifacts/arq/20261114T022413Z-h01-reader-free/bundle.json) and [session 9 bundle](../../../artifacts/arq/20261114T023251Z-h01-reader-free/bundle.json)
- [RX-only idle control raw bundle](../../../artifacts/arq/20261114T025241Z-rx-idle-control/bundle.json)
- [Verified normal standby restore](../../../artifacts/arq/20261114T025609Z-standby/standby-verified.json)
- [Historical RCA](../20261113T211753Z/FINAL_RCA.md)
- [Historical forward raw monitor log](../../../artifacts/rf-proof/20261113T062148Z/receiver-final.upditerm.log)
- [Regression results](08_REGRESSION_RESULTS.md)
- [Primary-source log](references/SOURCE_LOG.md)

### Root-cause verdict

**PARTIALLY_ISOLATED.** Tracker POR during the H01 packet-exchange window is confirmed. The RX-idle counterfactual shows continuous RX alone did not reset during its 120-second sample. The reset may have occurred before Tracker RxDone, during application parsing, or while entering a possible ACK TX; no surviving checkpoint places it more precisely. A supply-path transient is plausible, but the responsible source/rail and the H01 RF receive stage remain unproven.

### What is not proven

- Tracker actually detected Gateway RF in the final H01 run.
- Tracker entered `receive()` or accepted the DATA frame.
- Tracker began or completed ACK TX.
- Gateway radiated the measured RF field implied by its local `TX_DONE`.
- The reported CP2102 3.3 V source exceeded its current limit or dipped below a reset threshold.
- The reset occurred during Gateway TX, Tracker RX, DATA parsing, or ACK TX.
- The current reverse failure is caused by RadioLib errata, antenna path, or a particular module.

## Corrective action

A source-level configuration defect is now corrected in the unflashed candidate: clear `RegOpMode.LowFrequencyModeOn` for the fixed 915 MHz profile. This is datasheet-aligned but is not yet proven to fix H01 or reverse RF; the controlled H01 A/B described in [program source findings](09_PROGRAM_SOURCE_FINDINGS.md) is required. The POR still needs synchronized MCU VDD and `3V3-LORA` measurements; no supply fix is justified yet.

## Business impact

Gate 1’s Host control path now passed its 20-transaction acceptance run. The physical H01 path still failed after five DATA transmissions with no accepted ACK. Deployment reliability is not established until power and radio event boundaries are measured and repeatable packet/ACK trials pass.

## STAR — Learnings

Keep `UPDI transport`, `MCU reset`, `radio TxDone`, `radiated RF`, `radio RxDone`, and `ARQ acceptance` as separate evidence boundaries. The Monitor can lose UPDI while radio behavior continues, and a reset flag read after a normal core startup must use the core-saved GPIOR value. A nominal “3.3 V” source is not a dynamic voltage measurement.

## Program-source addendum

The later source audit found a confirmed radio configuration defect: RadioLib 7.1.2 preserves the SX127x reset-default LF-bank bit, and the project’s 915 MHz setup did not clear it. The captured armed state `0x8D` confirms the field was set. A test-first source correction now selects HF mode and produces `RegOpMode=0x85` in the host radio model. This is **not** causal proof for the H01 packet failure or POR; no candidate image was flashed. Full evidence and limits are in [09_PROGRAM_SOURCE_FINDINGS.md](09_PROGRAM_SOURCE_FINDINGS.md).
