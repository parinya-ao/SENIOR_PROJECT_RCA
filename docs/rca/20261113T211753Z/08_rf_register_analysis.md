# SX127x register and RF evidence

The reverse-raw snapshot order is defined in src/reverse_raw/main.cpp. Tracker standby and Gateway active-RX snapshots include:

| Register | Address | Tracker standby | Gateway active RX | Comparison / interpretation |
|---|---:|---:|---:|---|
| RegVersion | 0x42 | 0x12 | 0x12 | MATCH; SX127x-compatible version |
| RegOpMode | 0x01 | 0x89 | 0x8D / 141 | EXPECTED DIFFERENCE: standby vs RX continuous |
| RegFrf | 0x06–0x08 | E4 C0 00 | E4 C0 00 | MATCH; nominal 915.000 MHz at 32 MHz reference |
| RegPaConfig / RegPaDac | 0x09 / 0x4D | F0 / 84 | F0 / 84 | MATCH; PA_BOOST selected, configured +2 dBm; not an RF output measurement |
| RegModemConfig1/2/3 | 0x1D / 0x1E / 0x26 | 72 / 74 / 04 | 72 / 74 / 04 | MATCH; BW125, CR4/5, SF7, CRC on |
| Preamble / SyncWord | 0x20–0x21 / 0x39 | 0008 / 12 | 0008 / 12 | MATCH; preamble 8, sync 0x12 |
| RegInvertIQ / RegInvertIQ2 | 0x33 / 0x3B | 27 / 1D | 27 / 1D | MATCH; normal IQ configuration |
| RegLna / RegDetectOptimize | 0x0C / 0x31 | 23 / C3 | 23 / C3 | MATCH; G1/HF boost; AutomaticIFOn=1, not changed |
| RegModemStat | 0x18 | 0x10 in standby | 0x04 in active RX | EXPECTED DIFFERENCE; Gateway reported modem RX ongoing |
| RegIrqFlags at RX timeout | 0x12 | Not comparable | 0x00 | No RX IRQ was captured in that RX window |
| Tracker active-TX snapshot | N/A | NOT CAPTURED | N/A | Do not infer a match or TX mode |
| Gateway timeout counters | 0x14–0x17 | N/A | headers=0, packets=0 | No header/packet event was reported; counter zero alone is not proof of no RF energy |

The Tracker active-TX register snapshot and TX IRQ were not captured in the two POR trials. The MCU reset and unavailable output leave that boundary unknown.

## Forward-link sanity check

A separate historical forward raw capture logged valid 11-byte CRC-OK packets with reported RSSI around -107 to -109 dBm and SNR around +8 to +9 dB ([raw Monitor log](../../../artifacts/rf-proof/20261113T062148Z/receiver-final.upditerm.log)). This proves the forward direction decoded packets in that run; it does not establish reverse TX output power or current antenna condition. The exact distance is not independently confirmed in the raw capture metadata reviewed here.

**DERIVED, conditional:** At 915 MHz and 1 m, free-space path loss is 31.676 dB. If TX output were +2 dBm and both antennas were 0 dBi, ideal free-space received power would be about -29.676 dBm. That is roughly 77.3 dB above a reported -107 dBm reading. This is an anomaly, not a measured path loss: the distance, actual radiated output, antenna gains, and RSSI calibration were not independently measured. It cannot identify a bad radio or antenna by itself.

RADIOLIB_FIX_ERRATA_SX127X=0, AutomaticIFOn=1, and RegOpMode bit 3 are prior configuration observations. No IF workaround, RegOpMode change, IQ change, output-power change, or errata A/B was performed here. They remain hypotheses, not demonstrated causes of the POR.
