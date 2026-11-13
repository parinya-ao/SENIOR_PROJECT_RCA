# Design facts and physical unknowns

Design references: [Rudolph SSOT](../../../ssot/GATEWAY_SSOT.md),
[Tracker SSOT](../../../ssot/TRACKER_SSOT.md), and the Tracker2025-02-16 schematic
identified in the power analysis. No new physical inspection was performed.

| Net | Rudolph | Tracker |
| --- | --- | --- |
| SPI MOSI/MISO/SCK | PC0/PC1/PC2, SPI1 route | PC0/PC1/PC2, shared with SD |
| NSS | PC3 | PD0; SD NSS PC3 held inactive |
| RESET | PD0 | PD1 |
| DIO0 / DIO1 | PD2 / PD3 | PD3 / PD2 |
| Radio supply | Daughterboard VCC directly |3V3-LORA via Q1, PA7 active LOW |
| Antenna | ANT→SB1 SMA or SB2 U.FL | ANT→J1 |
| Ground | Radio/connector/MCU reference | Radio/connector/MCU reference |

OBSERVED operator confirmation: attached antennas, correct selected bridge,
unused path not intentionally bridged, suitable module markings, approximately
one metre indoor separation. Preserve that confirmation; no repeated request.
It does not measure continuity, impedance, actual output power or sensitivity.
Module-internal PA_BOOST routing and passive crystal are consistent with intended
RFM95W, but no new internal module inspection establishes them electrically.

Future tests are conditional, not permission to execute:

| Candidate | Minimum discriminating evidence | Stop / alternative |
| --- | --- | --- |
| UPDI loading | Analog target UPDI vs adapter RX; actual adapter model/voltage | No resistor/capacitor changes without waveform evidence |
| Source/switch sag | Synchronized U6 VDD and U4 pin13 traces | Identify actual H1/JP1 feed before blaming U7 |
| Tracker output ineffective | One authorized burst into compatible external receiver or suitably attenuated RF instrument | TxDone alone insufficient; spectrum presence alone does not validate payload |
| Rudolph deafness | Known-good compatible source to Rudolph after transport proven | Record header/packet/IRQ before cleanup |
| Feedline/bridge | Power-off continuity vs schematic and known matching board | DC shunt networks may legitimately show ground path; no antenna swap while powered |
| PHY mismatch | Simultaneous actual TX/RX snapshots plus reference endpoint | Standby fields cannot substitute for missing TX snapshots |

No device or component is isolated as defective. Hardware repair/part swaps,
increased power and repeated unchanged RF attempts are not justified.
