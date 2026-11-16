# Root-cause analysis

## Track A — Gate 1 STATUS silence

**Confirmed cause:** Host UPDI STS writes used the short address encoding for AVR128DA28 data-space GPR/mailbox registers. A protocol ACK did not prove the target stored the byte. On a halted Tracker CPU, a short STS to GPIOR1 at 0x1D left the register at 0x00; the 16-bit address STS changed it and was cross-read successfully. Restoring the original 0x00 also verified.

**Counterfactual:** Changing the Host sts8 frame to the 16-bit form made STATUS output appear. The real Tracker then completed 20/20 non-RF STATUS requests with no response mismatch, timeout, Monitor exit, or identity mismatch. No production firmware source changed.

## Track B — reverse RF

**Confirmed event:** In two reader-free Tracker SEND tests, core-saved reset cause changed from GPIOR0=0x20 (UPDIRF at baseline) to GPIOR0=0x01 (PORF after the receive window). RSTFR was zero after re-synchronization because installed DxCore startup copies RSTFR to GPIOR0 and clears RSTFR. No CPU reset was requested by the test. The 15-second no-RF idle control kept reset state unchanged.

**Manufacturer semantics:** AVR128DA POR is always enabled and is reasserted when VDD falls below the POR falling threshold VPORR. The two PORF observations establish a power-on reset at the MCU in the SEND experiment interval. They strongly support a power interruption associated with radio operation. The minimum VDD, rail node, and instant relative to TX_START were not measured.

**FACT:** The preserved Tracker fuse block is 0000f0ffffd2f80000ffffffffffffff; its BODCFG byte is 0x00. The AVR128DA datasheet maps ACTIVE=DIS and SLEEP=DIS to this value. Thus the optional BOD is disabled, while POR remains always enabled. This makes a deep VDD transient a plausible mechanism; it does not identify the failing board component or the minimum VDD.

**Causal chain supported by direct evidence:**

1. Gateway reached RX continuous and reported RAW_RX_READY.
2. Host UPDI writer accepted all 28 bytes of the exact SEND line.
3. Gateway’s 15-second RX window expired with RAW_RX_TIMEOUT.
4. Tracker reset-source storage changed to PORF before post-window UPDI diagnostics.
5. No Tracker RAW_TX/RAW_TX_DONE or Gateway RX payload was recovered.

**Unresolved boundary:** The application may have consumed the final newline and started TX before POR, or POR may have occurred before dispatch. The reset timestamp is not synchronized to TX_START. The raw log queue was empty after restart. Therefore the POR is a confirmed failure mechanism during the SEND experiment, but its exact order relative to radio TX and the historical 12:15 TxDone trial remains unknown.

## Competing explanations and counterfactuals

- Continuous Tracker Monitor polling is not required for the reproduced POR or Gateway timeout: reader-free trials had the same outcomes.
- Ordinary UPDI idle is weakened as an explanation: the matched 15.029-second no-RF control preserved GPIOR0/RSTFR/UART_FLAGS.
- A static board pin-map swap is rejected at source/SSOT level; physical continuity remains unmeasured.
- Gateway not being in RX is rejected for the captured trials: RAW_RX_READY, mode 0x8D, and ModemStat 0x04 were observed.
- Tracker radiation is unknown: no independent receiver or analyzer observed it.
- SX127x errata settings remain possible contributors, but no A/B was run and they do not explain the observed PORF alone.

The precise next physical measurement is a synchronized scope capture of Tracker MCU VDD and 3V3-LORA during one bounded SEND, with PA7 and UPDI or DIO0 as timing channels.
