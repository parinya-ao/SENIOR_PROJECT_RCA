# Experiment plan and next decision

## Completed discriminating experiments

| Experiment | Question | Result |
|---|---|---|
| GATE1-STS-AB | Does Host STS address-size encoding store to AVR128DA GPR? | Short-address STS ACKed but did not store; 16-bit STS wrote/read/restored the value. |
| GATE1-20 | Can corrected Host transport complete non-RF STATUS? | Real Tracker completed 20/20 STATUS requests. |
| RF-READER-ATTACHED | Does the normal Tracker Monitor capture survive SEND? | Repeated empty UPDI response; Gateway timeout in runs that continued capture. |
| RF-READER-FREE | Is the continuous Tracker reader required for POR/no receive? | No. One-shot writer accepted 28 bytes; Gateway timed out; PORF was captured in two repeats. |
| UPDI-IDLE-15S | Does the same interface reset after 15 s without RF command? | No reset observed; GPIOR0/RSTFR/UART_FLAGS were unchanged. |

## Next experiment — synchronized power/reset capture

Do not change firmware, fuses, radio PHY, output power, or antenna configuration. Use one controlled Tracker SEND with the verified raw test image and Gateway RX:

1. CH1: Tracker MCU VDD at the MCU decoupling capacitor.
2. CH2: Tracker switched 3V3-LORA at the RFM95W VCC decoupling capacitor.
3. CH3: PA7 at the MCU pin.
4. CH4: Tracker UPDI or radio DIO0; use a logic analyzer for 38,400-baud UPDI decode if available.
5. Trigger on PA7 assertion / SEND start and retain the complete 15-second RX window.
6. After the window, read GPIOR0 and RSTFR without CPU reset and correlate them with the same scope timebase.

**Decision:** A VDD trace crossing below the AVR128DA POR falling threshold during SEND confirms the supply transient. If MCU VDD stays above the datasheet threshold, inspect RESET and UPDI waveforms while preserving the POR evidence. The exact minimum voltage must be measured; the current record does not contain one.

After power/reset is stable, separately test Tracker TX into a known-good 915 MHz receiver and a known-good 915 MHz TX into Gateway RX. That separates endpoints without changing the PHY.

## Business ranking

| Next action | Hypotheses separated | Time to decision | Direct cost | Reliability risk |
|---|---|---:|---|---|
| Borrow 4-channel scope; capture MCU VDD, 3V3-LORA, PA7, UPDI/DIO0 | Supply transient vs reset/transport alternatives | 1–2 lab hours (planning estimate) | $0 if lab equipment is available; purchase cost unknown | Low with probes attached before power-on |
| Known-good 915 MHz receiver/transmitter substitution | Tracker TX vs Gateway RX | 1–2 hours after stable power (planning estimate) | $0 if compatible lab radios are available; otherwise quote unknown | Low |
| Receiver-only IF/errata A/B | Receiver configuration hypothesis | About 1 hour after power/UPDI are stable (planning estimate) | No new parts | Medium; requires verified rollback |

The scope capture is the cheapest first discriminator given two POR observations. No capacitor, BOD fuse, RadioLib errata, or PA change is recommended before the measurement.
