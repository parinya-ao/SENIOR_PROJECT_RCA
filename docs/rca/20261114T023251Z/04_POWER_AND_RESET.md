# Power, reset, and measurement limits

## Reset-cause capture

The installed DxCore startup in `framework-arduino-megaavr-dxcore/cores/dxcore/main.cpp` reads `RSTCTRL.RSTFR`, clears the flags by writing the captured value, then saves the original flags in `GPIOR0`. The application reads `GPR_GPR0` in `setup()` (`src/arq/main.cpp`). Therefore a later `RSTFR=0` is expected after core startup and does not negate `GPIOR0=0x01`.

The AVR128DA flag map identifies bit 0 as PORF and bit 1 as BORF. H01’s fresh-session `GPIOR0=0x01` is direct evidence of a Power-on Reset. It does not identify the external component that caused VDD to cross the POR threshold. `BODCFG=0x00` is the observed fuse configuration; no fuse was changed.

## Tracker supply path

The Tracker SSOT describes battery input through U7 TPS7A0233, switched `3V3-LORA` through Q1, and local C11/C8 decoupling. It also says H1’s 3V3 pin is downstream of U7, so injecting 3V3 there bypasses U7. PA7 is active-low and the application asserts it in setup; `SEND` does not toggle PA7.

The operator reports that the UPDI adapter supplies the board at 3.3 V. The host enumerates CP2102 adapters. Silicon Labs’ CP2102/9 datasheet specifies a 100 mA maximum regulator output; that is a plausible current-source constraint if the adapter VDD output actually feeds H1. Actual pin wiring, total load, regulator voltage, current, ground bounce, and VDD minima were not measured. The CP2102 rating alone does not prove overload.

The local ADC library has `ReadBatteryAdc()` on PD7/AIN7. It samples the board’s battery-probe channel, not MCU VDD or `3V3-LORA`; the current ARQ application does not call it. It cannot answer the missing rail-voltage question for an H1-powered board.

## What was not measured

| Quantity | Status |
|---|---|
| Tracker MCU VDD minimum during H01 | UNKNOWN — no scope or voltage logger |
| Tracker 3V3-LORA minimum/current during H01 | UNKNOWN — no scope/current probe |
| CP2102 VDDOUT voltage under board load | UNKNOWN — no direct measurement or verified H1 wiring inspection |
| Reset-pin waveform / exact POR time | UNKNOWN — no scope/logic analyzer |
| Gateway radiated RF power or Tracker received RF energy | UNKNOWN — no independent receiver/SDR/analyzer |
| Tracker DIO0, PA7, and UPDI timing during the failure | UNKNOWN — no synchronized capture |

The next decisive physical capture is MCU VDD and `3V3-LORA` simultaneously, with Tracker UPDI plus Gateway TX-done or Tracker DIO0 as timing references. A single multimeter reading of nominal 3.3 V would not rule out a microsecond-scale dip.
