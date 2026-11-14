# Hardware measurements and gaps

| Measurement | Result |
|---|---|
| Tracker/Gateway MCU identity | Tracker verified in Gate 1; Gateway only historical identity |
| UPDI protocol | low-level transactions responsive in Gate 1; no waveform capture |
| UPDI / H1 signal amplitude | NOT MEASURED |
| Tracker MCU VDD / 3V3-LORA during STATUS | NOT MEASURED |
| Radio rail during TX | NOT MEASURED |
| Tracker RF emission at 915 MHz | NOT independently measured |
| Gateway RxDone / CRC on reverse trial | no RxDone in Incident A; no independent RF source test |
| Antenna path visual confirmation | operator confirmed previously; no continuity/impedance reading |

The 3.3 V supply is design/operator context, not a captured electrical waveform. A synchronized scope trace would be needed to claim rail stability during RF load.
