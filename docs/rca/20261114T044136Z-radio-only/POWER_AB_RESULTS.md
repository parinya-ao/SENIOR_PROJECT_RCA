# Power A/B/A Results

**Status: NOT RUN.** No safe alternate source, measured power path, or voltage/current instrument was established for this continuation.

| Condition | Evidence | Result |
|---|---|---|
| Historical H01 supply arrangement | Gateway logged 10 DATA TX_DONE and 10 ACK-window timeouts across sessions 8/9; session 9 later recorded saved PORF | No MCU VDD or 3V3-LORA waveform/current; source topology and exact reset time UNKNOWN |
| Historical RX-only control | Tracker remained in RX Continuous for 120.029947 s with no Gateway DATA; no new saved PORF observed | Not a power-source A/B condition and not a TX load test |
| Independent 3.3 V supply (B) | No source and no instrumented connection documented | NOT RUN |
| Return to original source (A2) | No controlled source reversal | NOT RUN |

The operator reports 3.3 V from the UPDI adapter. USB enumeration identified two CP2102 devices and a USB descriptor limit of 100 mA per device; neither fact measures the adapter's target output path or Tracker load. The Tracker schematic also shows a battery/TPS7A0233 source on the main 3V3 net. Whether that source is connected while the UPDI adapter supplies 3.3 V is UNKNOWN.

No measured voltage minimum, transient duration, or current exists. The historical POR mechanism therefore remains **UNKNOWN**; this report does not attribute it to the CP2102, TPS7A0233, Q1, or RF PA.

The next safe causal experiment requires identifying and isolating the single active 3.3 V source, confirming common ground and no back-feed, then capturing MCU VDD and 3V3-LORA through a bounded radio event. If original and independent supplies are both safe and measurable, compare A/B/A with firmware, RF profile, antennas, and packet timing held constant.
