# Next discriminating experiment

## One bounded A/B: Tracker supply source under H01

Use the same two firmware images, Tracker build hash `a0ab6646…`, Gateway build hash `72774ddc…`, radio profile, antenna orientation, distance, payload, session, retry configuration, and one H01 transaction.

**A:** Current reported setup, Tracker powered from the CP2102/UPDI 3.3 V feed.

**B:** Tracker powered from a separately measured, current-capable 3.3 V source through the documented board input, with CP2102 VDD disconnected and UPDI/GND retained. Do not parallel two 3.3 V sources.

Capture on one timebase:

1. Tracker MCU VDD at its local decoupling capacitor.
2. Tracker `3V3-LORA` at the RFM95W decoupling capacitor.
3. Tracker UPDI at the MCU pin.
4. Gateway TX-done or a trigger derived from the H01 command.

Also read Tracker GPIOR0/RSTFR after the trial without issuing a CPU reset. The expected measurement ranges come from the AVR128DA and RFM95W manufacturer datasheets; record actual minima rather than nominal supply values.

| Result | Interpretation |
|---|---|
| A dips into POR range and resets; B remains above operating limits and H01 delivers | Strong evidence the adapter/source path causes the reset and missed ACK; still verify repeatability before fixing production power architecture. |
| A and B both POR at the same packet stage, with both rails stable at MCU/radio pins | Reject source-current limitation; investigate reset pin/UPDI and firmware stage timing using the captured UPDI/DIO signals. |
| Rails remain stable but Tracker records RX_DONE/ACCEPT and no ACK TX | Isolate firmware response scheduling/SPI/RadioLib path. |
| Tracker records ACK TX_DONE but Gateway gets no ACK | Independently verify Tracker radiation and Gateway ACK RX configuration/path. |
| Tracker has no RX_DONE while Gateway TX_DONE occurs | Use the scope/logic capture to separate actual RF emission, receiver sensitivity, PHY mismatch, and DIO/IRQ loss. |

No production change is justified yet. If a source A/B cannot be run because there is no current-capable supply or scope, the remaining blocker is specifically the missing synchronized VDD/3V3-LORA waveform and alternate-source comparison.
