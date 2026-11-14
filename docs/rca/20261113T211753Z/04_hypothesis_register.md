# Hypothesis register

Confidence describes evidence for the mechanism, not a numerical probability.

| ID | Hypothesis | Supporting evidence | Contradictory / limiting evidence | Status | Next discriminating test |
|---|---|---|---|---|---|
| G01 | Gate 1 STATUS silence came from wrong UPDI STS address width for AVR128DA GPR mailbox writes | GPIOR1 short STS ACKed but readback stayed 0x00; 16-bit STS wrote 0xFF, both LDS forms read it, restore verified. Corrected host then passed 20/20 STATUS. | Does not explain later UPDI response loss during active radio tests. | **CONFIRMED; HOST FIX APPLIED** | Keep transport regression tests. |
| G02 | Monitor disconnect proves MCU reset | Old disconnects had no reset evidence. Later POR was directly read from core-saved GPIOR0. | A process exit alone has no reset semantics. | **REJECTED as an inference rule** | Keep reset-source capture separate. |
| R01 | Tracker experienced POR during SEND tests | Two reader-free runs changed GPIOR0 0x20→0x01; the 15 s no-RF idle control was stable. | Reset instant is not synchronized to TX_START. | **CONFIRMED POR during both test intervals** | Scope MCU VDD and 3V3-LORA. |
| R02 | POR is associated with radio-operation power demand | POR reproduced only in the two SEND tests; 15 s idle control on the same Tracker/UPDI path did not reset. BODCFG=0x00 disables BOD ACTIVE/SLEEP; POR remains enabled. | No voltage minimum, current, or ground-bounce waveform; no TX_START event. | **HIGHLY SUPPORTED; exact supply path UNKNOWN** | Synchronized scope capture during SEND. |
| R03 | Continuous Tracker Monitor polling is required for the failure | Attached Monitor runs also ended in UPDI response errors. | Reader-free trials still had POR and Gateway timeout. | **REJECTED as sole cause** | Scope UPDI and rails if behavior differs with Monitor attached. |
| R04 | Tracker entered radio TX and radiated, but Gateway missed it | Historical Incident A had local TxDone. | Both POR trials lack Tracker RAW_TX/TX_DONE; no independent receiver or RF instrument. | **UNKNOWN** | Tracker TX → known-good 915 MHz receiver. |
| R05 | Gateway was not in RX | No supporting evidence in the new trials. | Gateway logged RAW_RX_READY in mode 0x8D, ModemStat 0x04, then timed out. | **REJECTED for captured RX state; front-end UNKNOWN** | Known-good 915 MHz TX → Gateway RX. |
| R06 | Static board pin-map swap | No source evidence. | Static SSOT and compiled board mapping agree; physical continuity remains unmeasured. | **REJECTED at source level** | Electrical continuity only if later evidence contradicts SSOT. |
| R07 | PHY mismatch / AutomaticIFOn / errata caused non-reception | AutomaticIFOn is set and errata fix is disabled. | No controlled receiver IF A/B; POR is a separate observation; no active Tracker TX registers captured. | **POSSIBLE, NOT CONFIRMED** | After power is stable, one receiver-only IF A/B with full register readback. |
| R08 | Gateway packet counter zero proves no RF | Gateway counters and flags were zero at timeout. | Counter errata and absence of external RF observation prevent that conclusion. | **REJECTED as a proof claim** | Observe RxDone/ValidHeader and an independent receiver. |
| R09 | ACK/NACK protocol failed | No ACK/NACK physical success was captured. | Reverse-raw is a one-way unframed 11-byte payload with no ACK. | **NOT TESTED** | First prove reverse raw reception. |
| R10 | Several independent defects exist | Host GPR write defect is confirmed; POR is also confirmed in separate RF trials. | Historical 12:15 TxDone/no-RX mechanism remains unisolated. | **SUPPORTED** | Close power/reset issue, then isolate RF endpoints. |

## Expanded subsystem checks

| Area | Hypothesis family | Evidence / disposition |
|---|---|---|
| Host/tooling | Wrong repository, firmware image, role, or serial port | **REJECTED for these trials:** active repository is SENIOR_PROJECT_RCA; device signature/serial, firmware build IDs, and config hashes matched the expected Tracker/Gateway images. |
| Host/tooling | Port contention or USB disconnection | **NOT OBSERVED:** fuser preflight found no other owner. No USB disconnect event was captured. |
| Host/tooling | Parity/stop-bit mismatch | **NOT SUPPORTED:** Monitor used the installed 38,400-baud 8E2 path; the tested transport performed low-level UPDI exchanges before the runtime timeout. Electrical framing remains unmeasured. |
| Host/tooling | Host parser discarded events | **PARTLY OBSERVED:** earlier capture closed both monitors on one exit and could truncate the peer’s final line; capture code now preserves the remaining Gateway window. The reader-free reset result is independent of that parser issue. |
| Firmware | Wrong hardware pin map or role compiled into image | **REJECTED at source level:** SSOT is consistent; raw images were programmed to their corresponding identified boards. Physical wiring remains UNKNOWN. |
| Firmware | Firmware never received any command byte | **NARROWED, NOT FULLY REJECTED:** Host writes and mailbox backpressure accepted 28/28 bytes; final newline consumption is UNKNOWN after POR because GPIOR flags reset. |
| Firmware | Command parser or TX handler completed | **UNKNOWN:** no Tracker RAW_TX or RAW_TX_DONE survived the POR; firmware source predicts these logs after startTransmit but no live event confirms entry. |
| Firmware | MCU reset during SEND | **CONFIRMED PORF in 2/2 reader-free RF trials;** no POR in 1/1 matched idle control. Exact reset time within the receive window is UNKNOWN. |
| Radio/SPI | Gateway radio unpowered or not in RX | **REJECTED for captured trials:** Gateway RAW_RX_READY showed mode 141 and modem status 4 before SEND. |
| Radio/SPI | Tracker radio initialization / SPI failed | **UNKNOWN during active SEND:** pre-SEND snapshots in attached trials were sane, but no active Tracker TX snapshot was captured in the POR tests. |
| RF | Frequency/PHY mismatch | **NOT SUPPORTED by nominal snapshots:** both radios showed 915 MHz, BW125, SF7, CR4/5, sync 0x12, normal IQ. Actual crystal offset and RF path remain UNKNOWN. |
| RF | TX completed but radiation was ineffective | **POSSIBLE for historical Incident A:** TxDone was captured there, but no independent RF receiver or power measurement was used. |
| RF | Gateway DIO/ISR or packet parser lost a valid receive | **UNKNOWN:** no Gateway RxDone/header event or FIFO payload was captured. |
| RF | Antenna/feedline/front-end defect | **UNKNOWN:** visual inspection only; no continuity, impedance, or reference-radio substitution. |
| Protocol | Receiver was not ready before the reverse SEND | **REJECTED for controlled raw trials:** Gateway RX_READY preceded the Host SEND command; clocks were not compared across devices. |
| Protocol | ACK/NACK turnaround or parser failure | **NOT TESTED:** reverse raw is one-way and no hardware ACK/NACK result exists. |
| Observation | Zero packet counter proves no reception | **REJECTED as an inference:** the counter has silicon limitations; the directly captured result is a Gateway RX timeout with no logged RxDone/header event. |
| Observation | Monitor reader caused the POR | **REJECTED as sole cause:** the same POR was observed in reader-free tests; an idle reader-free control remained stable. |
