# Frozen current topology — RCA_FRESH_01

Fresh discovery assigns labels by lexical ID_PATH order. These labels have no continuity with historical P/Q. USB topology identifies a path, not a distinguishable adapter unit.

| Fresh lane | Frozen ID_PATH | Discovery locator | Separate power board | Target |
|---|---|---|---|---|
| P | pci-0000:00:14.0-usb-0:1:1.0 | /dev/ttyUSB1 | PowerBoard P, current ttyUSB1 branch | UNKNOWN |
| Q | pci-0000:00:14.0-usb-0:4:1.0 | /dev/ttyUSB0 | PowerBoard Q, current ttyUSB0 branch | UNKNOWN |

User reported two separate power boards associated with the current branches. Physical power-board serials/labels, supply voltage/current/source, wiring, shared upstream supply, ground topology, target serials, firmware and fuse equivalence are unmeasured. PowerBoard P/Q are fresh branch labels, not verified physical-unit fingerprints. No old target X/Y assignment is imported.

Both adapters report VID:PID 10c4:ea60 and duplicate serial 0001. Adapter-unit identity remains UNRESOLVED. Replacing a descriptor-identical unit on the same USB path cannot be detected from these descriptors; no unit-level locality claim is permitted.

The current path comprises USB port → adapter → external harness/series element → target UPDI, with its separate power board/supply → target VDD/GND. Exact physical pinout and isolation remain unverified. No component is moved in this campaign.

Transport: existing strict CLI, nominal 38400, 8E2, one-second timeout, two 300-baud zero-byte BREAK exchanges, no retries; only SIB/LDCS frames. Each attempt checks ownership under a path lock, re-resolves the device, opens exclusively, closes and releases. Raw BREAK ordinals and per-operation bytes remain in canonical envelopes and source transport JSON.

Integrity anchors: mapping.json + mapping.sha256; usb_inventory.json; host_snapshot.json; source_sha256.csv; historical_sha256.csv. Every fresh CSV and canonical raw envelope includes epoch_id.
