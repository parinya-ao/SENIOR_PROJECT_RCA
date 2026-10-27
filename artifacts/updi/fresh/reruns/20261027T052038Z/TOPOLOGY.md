# Current rerun topology — RCA_FRESH_01 / 20261027T052038Z

Labels assigned from this rerun's freshly sorted current ID_PATH discovery, before probing. Current paths match the first fresh campaign; no physical unit continuity is inferred from that match.

| Lane | Frozen ID_PATH | Current locator | Separate power-board branch | Target |
|---|---|---|---|---|
| P | pci-0000:00:14.0-usb-0:1:1.0 | /dev/ttyUSB1 | PowerBoard P | UNKNOWN |
| Q | pci-0000:00:14.0-usb-0:4:1.0 | /dev/ttyUSB0 | PowerBoard Q | UNKNOWN |

Each path: USB host port → CP2102 adapter → unverified harness/series element → target UPDI; separate branch power board → target VDD/GND. Both USB descriptors report VID:PID10c4:ea60, serial0001. Adapter-unit identity is UNRESOLVED, including replacement by a descriptor-identical unit. PowerBoard P/Q are branch labels based on the user's two-board report, not verified unit fingerprints. Board supplies, common upstream connections, ground topology, target fingerprint, firmware/fuses, pinout and instrument availability remain unverified. No previous X/Y board identity is assigned.

No agent-issued wiring, power-board, adapter, harness, target, resistor, firmware, fuse or BOD change occurred. The user subsequently confirmed a power change/cycle on P / ttyUSB1 during this rerun; exact event time and per-attempt power state are unknown. The campaign cannot be labeled an untouched physical baseline. Strict38400/8E2/timeout1s, two300-baud BREAK exchanges, no retries. Lane lock/owner check/current rediscovery/exclusive-open/close/release are unchanged. Both ports were idle at discovery. See mapping.json, mapping.sha256, usb_inventory.json, host_snapshot.json and source_sha256.csv.
