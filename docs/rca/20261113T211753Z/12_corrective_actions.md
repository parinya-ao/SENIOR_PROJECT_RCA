# Corrective actions

## Applied and verified

1. **Host UPDI GPR write correction:** UPDI.sts8 now uses 16-bit data-space addressing for AVR128DA28 GPR/mailbox writes. ACK validation remains strict. A regression test asserts the frame, and the real Tracker passed 20/20 non-RF STATUS requests.
2. **Transport diagnostics:** mismatch errors preserve request/response bytes, lengths, serial timeout, read duration, and last request. Errors remain fatal; no retries or relaxed checks were added.
3. **Capture completeness:** arq_trial can preserve a Gateway RX window if the Tracker Monitor exits. Reader-free mode records the exact Host command and reset snapshots.
4. **Restoration:** temporary reverse-raw application images were removed after each trial; normal firmware was read back and verified in standby.

## Not applied

No production firmware behavior, radio PHY, errata setting, antenna, PA power, fuse, BOOTSIZE, EEPROM content, or hardware was modified. No capacitor or regulator change was attempted.

## Minimum proposed repair

Capture MCU VDD and 3V3-LORA during a single SEND. If the MCU rail falls below the POR threshold, repair only the measured failing supply path (source, regulator, switch, ground, or decoupling). If MCU VDD remains above threshold, capture RESET and UPDI and reassess the reset-source path. Then verify Tracker TX with a known-good 915 MHz receiver and Gateway RX with a known-good transmitter before changing SX127x configuration.
