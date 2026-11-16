# Hardware measurements and gaps

| Quantity | Observation | Classification | Needed measurement |
|---|---|---|---|
| Tracker MCU VDD during SEND | No voltage sample captured | UNKNOWN | Minimum/max waveform at MCU decoupling capacitor |
| Tracker 3V3-LORA | No voltage sample captured | UNKNOWN | Voltage at RFM95W VCC decoupling capacitor |
| PA7 / Q1 | Design says PA7 low enables radio; live voltage not measured | UNKNOWN electrically | PA7 and switched rail on common scope timebase |
| Tracker UPDI | Host got zero-byte response after 1.0 s; no line waveform | OBSERVED transport timeout; electrical cause UNKNOWN | UPDI at MCU pin and adapter RX, decoded at 38,400 8E2 |
| BOD configuration | Captured fuse block has BODCFG byte 0x00; ACTIVE and SLEEP mode bits are DIS | OBSERVED from fuse readback | Do not treat absence of BORF as proof that VDD stayed above a safe operating level |
| MCU reset state | Baseline GPIOR0 0x20; post-window 0x01; RSTFR cleared by core | OBSERVED PORF after SEND interval | Correlate scope VDD/RESET with retained startup GPIOR0 |
| Gateway RX | RAW_RX_READY, mode 141, ModemStat 4, then timeout | OBSERVED RX window | Independent known-good 915 MHz transmitter |
| Tracker radiated RF | No independent receiver or analyzer | UNKNOWN | Known-good 915 MHz LoRa receiver or spectrum analyzer |
| Antenna/feedline | Operator visually inspected previously; no continuity, impedance, or conducted RF reading | UNKNOWN electrically | Unpowered continuity check; RF measurement only after power is stable |
| Current / ground bounce | No current probe or differential measurement | UNKNOWN | Current probe and differential VDD/ground measurement |

**FACT:** Microchip documents POR as always enabled and reasserting reset if VDD falls below VPORR. The captured PORF therefore establishes a power-on reset event at the MCU; it does not reveal minimum VDD, rail location, duration, or supply component.

No oscilloscope, logic analyzer, SDR, or RF analyzer was connected to this host. The 3.3 V nominal value is operator-reported design context, not a measurement.
