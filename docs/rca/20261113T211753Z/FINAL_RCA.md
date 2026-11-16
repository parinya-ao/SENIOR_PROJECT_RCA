# Final RCA — Tracker to Gateway LoRa ARQ V1

## Executive summary

Two separate defects are established. Gate 1 STATUS silence came from the Host UPDI writer using an 8-bit STS address form that did not store AVR128DA28 GPR mailbox bytes despite link ACKs; changing it to the 16-bit form restored STATUS, with 20/20 live non-RF requests passing. Separately, two reader-free Tracker SEND tests produced a POR reset-source change (GPIOR0 0x20→0x01) and Gateway RX timeouts; a matched 15-second no-RF idle control did not reset. This establishes a POR during the SEND experiment and strongly implicates Tracker power under radio operation. The actual voltage minimum and whether POR occurred before or after radio TX_START were not captured. No Tracker TX_DONE or independent RF reception was observed in those POR trials. The 12:15 historical TxDone/no-RX incident remains unisolated. The boards are restored to verified normal standby.

## STAR — Situation

The system uses AVR128DA28 MCUs and RFM95W/SX127x radios. In the failing reverse direction, Tracker is the physical radio transmitter and Rudolph/Gateway is the receiver. Historical Incident A at 12:15 UTC recorded Tracker local TxDone and a Gateway 15-second RX timeout. Incident B at 12:36 UTC recorded an UPDI empty-response failure before any confirmed Tracker TX event, so RF was inconclusive.

## STAR — Task

Determine the earliest failed boundary for Gate1 STATUS and reverse RF using live hardware, preserve prior evidence, avoid speculative RF changes, and leave both boards in verified normal standby.

## STAR — Action and decision logic

1. Verified the active repository and read historical evidence. Static SSOT and firmware pin maps agree; no source-level role/pin swap was found.
2. Tested the mailbox write boundary directly. A halted-CPU GPIOR1 A/B showed the short STS form acknowledged but did not store; the 16-bit form stored/read/restored the byte.
3. Applied the smallest Host-side correction and ran 20 non-RF STATUS transactions. All passed.
4. Repeated reverse-raw with the Tracker Monitor attached. The Tracker UPDI response failed while the Gateway continued to RX timeout, so a reader-free trial was added.
5. Sent the same command through the existing UPDI writer without starting the Tracker output-reader thread. Repeated twice with reset-state capture, plus a matched 15.029-second no-RF idle control.
6. Compared core-saved reset cause. In both SEND trials, GPIOR0 changed from UPDIRF 0x20 to PORF 0x01. In the idle control, GPIOR0 remained 0x20. DxCore reads RSTFR, clears it, and saves the original flags in GPIOR0 before application startup.
7. Restored normal firmware and verified both boards in standby.

No radio PHY, errata setting, fuse, BOOTSIZE, EEPROM content, or hardware change was applied.

## STAR — Result

| Metric | Actual result |
|---|---:|
| Gate1 STATUS | 20/20 passed |
| STATUS response mismatch / timeout / Monitor exit | 0 / 0 / 0 |
| Reader-free SEND attempts | 7 |
| Reader-free Gateway RX timeouts | 7 |
| Reader-free command bytes accepted | 28 per attempt |
| POR source changes after SEND | 2/2 reader-free repeats |
| POR in matched 15 s no-RF idle control | 0/1 |
| Tracker RAW_TX_START/TX_DONE captured in POR runs | 0 |
| Valid Gateway RX payloads captured in POR runs | 0 |
| Instrumented voltage/current/RF captures | 0 |
| Original incident bundle hash mismatches | 0 across 221 files |
| Normal images restored / verified | 2/2 |
| Focused tests | 67 passed |
| Full Python test discovery | 272 run, 2 skipped, 7 errors due missing host g++ |
| PlatformIO images | 6/6 builds succeeded |

## Confirmed causes

### RC-01 — UPDI STATUS mailbox write-width defect

- **Affected component:** Host third_party/upditerm/upditerm.py.
- **Observed symptom:** STATUS command bytes were accepted by the Host, but the Monitor produced no STATUS output.
- **Causal mechanism:** Short STS address encoding did not update AVR128DA28 GPR/mailbox registers even though UPDI ACKs were returned.
- **Direct evidence:** The GPIOR1 A/B trace at artifacts/arq/gate1-updi/20261113T184115Z-tracker-wide-gpr-sts/transport-trace.jsonl. Short STS left the byte at 0x00; wide STS wrote 0xFF and restoration to 0x00 verified.
- **Corrective action:** Host sts8 now transmits the 16-bit data-space address and preserves both ACK checks.
- **Counterfactual:** Tracker STATUS output returned and 20/20 live non-RF STATUS requests passed.

### RC-02 — Tracker POR during SEND experiments

- **Affected component:** Tracker AVR128DA28 power/reset domain.
- **Observed symptom:** Gateway was in continuous RX, but no packet event was captured; Tracker's post-window UPDI response failed.
- **Causal mechanism observed:** The Tracker's core-saved reset cause changed from GPIOR0 0x20 (UPDIRF baseline) to 0x01 (PORF) in two SEND runs. The no-RF idle control did not change reset state.
- **Manufacturer interpretation:** AVR128DA POR is always enabled and reasserts when VDD falls below VPORR. This is a confirmed power-on reset condition at the MCU. A load-related VDD transient is the strongest explanation, but the rail waveform was not measured.
- **Direct evidence:** artifacts/arq/20261113T210613Z-reverse-raw/tracker-direct-command.json and artifacts/arq/20261113T211753Z-reverse-raw/tracker-direct-command.json.
- **Reset-safety configuration:** the preserved fuse block contains BODCFG=0x00. The AVR128DA datasheet maps ACTIVE=DIS and SLEEP=DIS for this value; no fuse write was performed. POR remains always enabled.
- **Counterfactual:** The 15.029-second idle control retained GPIOR0=0x20, RSTFR=0, UART_FLAGS=1.
- **Corrective action:** Not applied pending synchronized VDD/3V3-LORA measurement.

## Remaining uncertainty

- Did POR occur before Tracker radio TX_START or after an unobserved TX?
- Which board supply node or component drove VDD below VPORR?
- Did Tracker radiate in the historical 12:15 incident that logged local TxDone?
- Is Rudolph's RX front end, antenna/feedline, or receiver configuration limiting that older TxDone trial?
- Is there a separate receiver IF/errata issue? No A/B was performed.
- ACK/NACK has not been validated on physical hardware.

## Final verdict

**PARTIALLY_ISOLATED.** The Host STATUS cause is confirmed and fixed. A Tracker POR during the active SEND experiment is confirmed twice and is the strongest supported cause of the reproduced reverse failure. The supply path and exact timing remain unresolved; the historical TxDone/no-RX incident is not fully isolated.

## Business impact

The Host-side STATUS defect is fixed, removing a known blocker from future diagnostics. The repeated POR can cause a Tracker reboot and erase volatile radio state during a send attempt; this can prevent a packet or its diagnostic event from completing. The field failure rate and repair cost cannot be quantified from two one-packet reproductions. A scope measurement is lower risk than changing the power path speculatively and should reduce the chance of masking the actual weak node.

## Next decision

Run one synchronized scope capture on Tracker MCU VDD, 3V3-LORA, PA7, and UPDI/DIO0 during a bounded SEND, with Gateway RX-ready and post-window GPIOR0/RSTFR capture. Do not change radio settings before the measurement.

## Evidence index

- Gate1 20/20: artifacts/arq/gate1-updi/20261113T191315Z-tracker-gate1-20-fixed/
- GPR STS A/B: artifacts/arq/gate1-updi/20261113T184115Z-tracker-wide-gpr-sts/
- Reader-free POR run 1: artifacts/arq/20261113T210613Z-reverse-raw/
- No-RF idle control: artifacts/arq/20261113T211610Z-updi-idle-control/
- Reader-free POR repeat: artifacts/arq/20261113T211753Z-reverse-raw/
- Verified restore: artifacts/arq/20261113T212027Z-standby/
- Original incidents and integrity manifests: artifacts/arq/20261113T121506Z-reverse-raw/, artifacts/arq/20261113T123620Z-reverse-raw/, artifacts/arq/20261113T123837Z-standby/
