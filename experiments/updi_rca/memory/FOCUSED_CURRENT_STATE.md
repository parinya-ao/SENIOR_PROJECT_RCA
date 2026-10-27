# Focused Current State

Epoch: `RCA_PHY_01`; 2026-10-27 local date.

- **Boundary:** LEVEL 1, host-observed LOCAL_ECHO loss at first/second 300-baud BREAK. External path versus target/reference remains unisolated; component RCA BLOCKED.
- **Mapping:** P=`pci-0000:00:14.0-usb-0:4:1.0`; Q=`pci-0000:00:14.0-usb-0:1:1.0`. X/Y are provisional historical connected-target labels; current pairing continuity and both target fingerprints UNKNOWN. Tty is a locator.
- **Proven observations:** preserved 509+40=549 run rows / 6387+546=6933 events; 0 new hardware runs/events in this epoch. Hashes verified. No causal component proven.
- **Top 3 unresolved domains:** external CP2102/bridge/harness/USB path; target UPDI network; VDD/GND/voltage reference. Interaction remains possible.
- **Last experiment:** earlier `RCA_CROSSOVER_01` original-pairing precheck, not a new test: P+X 10/10 SIB and 10/10 control; Q+Y 0/10 each. Per-condition Wilson success CI P 72.25–100%, Q 0–27.75%.
- **New analysis:** inherited Q 171/200 BREAK1 empty, 29/200 BREAK2 empty after exact BREAK1; continuation Q 17/20 and 3/20. No valid target request after failed synchronization. These are host reads, not measured electrical waveforms.
- **Next discriminator:** qualified bench operator verifies safe power isolation, actual pinout, and the PCB-only crossover boundary. Keep port/cable/CP2102/bridge/resistor/adapter-side jumper with P/Q. User previously could not perform crossover safely; no physical action repeated.
- **If crossover inaccessible:** simultaneous TX/shared-UPDI/target-UPDI/local-VDD plus ground-offset capture at failed first/second BREAK; ≥20 MS/s investigation floor. Topology and probe safety must be verified first.
- **Safety:** new flash=0, fuse=0, chip erase=0, BOD change=0; no repair, reset command or serial-open operation in this epoch.
- **Artifacts:** `reports/FOCUSED_STAR_RCA.md`, focused CSVs, both focused D2/SVG diagrams; 75 host tests passed. 33 physical candidates BLOCKED; 8 methodology guards UNRESOLVED. Historical 168-row tables preserved.
