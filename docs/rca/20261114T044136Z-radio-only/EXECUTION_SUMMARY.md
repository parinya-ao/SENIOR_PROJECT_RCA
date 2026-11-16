# Execution Summary

## Completed in software

- ARQ and reverse-raw diagnostic paths now use the 923 MHz, +2 dBm ARQ profile.
- SX127x HF selection clears only OpMode bit 3 after successful radio initialization; modeled RX Continuous is `0x85`.
- Tracker radio-only startup keeps LoRa active, isolates GPS UART before main-power shutdown, disables GPS/SD application activity, and retains the SD shared-SPI guard.
- Programmer role mapping handles the radio-only Gateway/Tracker environments and static application bounds.
- RF-proof host test stage no longer references removed Hello sources and supplies role compile flags to the diagnostic compile.
- Current host suite: 302 run, 1 skipped, 0 failures/errors. Current active target builds: 15/15.

## Physical work and result

Preserved-firmware STATUS previously passed 20/20 on Tracker and 1/1 on Gateway. Fresh separate read-only LDS evidence matched both configured MCU serials and read BODCFG/CODESIZE/BOOTSIZE 0/0/0. No candidate was programmed, no RF transmitted, and no candidate radio register readback or DATA/ACK/NACK event was captured.

The guarded preflight remains blocked before serial open because the adapter/board power and back-feed arrangement is not verified. RF transmission also remains blocked because the actual antenna gain/equipment compliance and applicable trial conditions are not established. No scope, logic analyzer, independent RF receiver, current probe, or voltage logger was available.

## Next physical action

Verify one isolated, adequate 3.3 V source and common reference, ensure the battery/TPS7A path cannot back-feed the adapter, inspect the SD socket against the existing guard, and document the applicable 923 MHz equipment/antenna/EIRP condition. Then program only the verified application images and perform one bounded DATA/ACK exchange with radio registers and reset/rail evidence.
