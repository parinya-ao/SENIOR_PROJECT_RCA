# Power and Interface Topology

This is a schematic-level map plus the current Host observation. It is not a measurement of the assembled boards.

## Tracker — Tracker RFM schematic, 2025-02-16

Source PDF: `/home/parinya/university/iwing-tracker/device-lora/pcb/2025-02-16/Schematic_LoRa-Tracker-RFM_2025-02-16.pdf`  
Extracted text: [tracker.txt](references/schematic_text/tracker.txt)  
SHA-256: `8699b9205621851e5322f16407298d2d6644d265170f18aeb800f77ba13a7612`

```text
VBAT ── TPS7A0233 ── main 3V3 ── AVR128DA28 / IMU / 24C512
                            ├── Q1 / EN-LORA (PA7) ── 3V3-LORA ── RFM95W
                            ├── Q2 / EN-GPS (PD5)  ── 3V3-GPS ── SAM-M10Q VCC + V_IO
                            └── Q3 / EN-SD (PD6)   ── 3V3-SD ── SD socket
```

The active-low switch policy in the design is LOW = rail enabled and HIGH = rail disabled. The SAM-M10Q V_BCKP connection is separate from its switched main supply. IMU and 24C512 remain on main 3V3 and cannot be fully power-gated by the GPS or SD controls.

The Tracker schematic shows H1 service pins for UART, UPDI, 3V3 and ground. The operator reports using the UPDI adapter's 3.3 V output. Linux sees the adapter as a CP2102 USB-UART device with a bus-powered 100 mA USB descriptor, but this does not reveal whether its board-level 3.3 V output is CP2102 VDDOUT or a separate regulator, nor the actual target current.

The same drawing shows the battery regulator output on the main 3V3 net. Therefore, the actual battery/regulator state and any external 3.3 V injection at H1 must be established before treating the present wiring as a verified single-source arrangement. No schematic or USB descriptor proves that two potential sources are isolated.

LoRa and SD use the MCU's shared SPI signals; SD_SS (PC3) and RF_SS (PD0) are separate selects. The radio-only SD guard remains enabled. The socket's current occupancy and rail voltage were not observed.

## Gateway — Rudolph Gateway radio and main-board schematics

Source PDFs:

- `/home/parinya/university/iwing-tracker/gateway-lora/loraboard/pcb/2025-04-26/Schematic_LoRa_Board_rudolph_gw_2025-04-26.pdf` — SHA-256 `11706846afef7a3c66394978acdeb1d0368c7de9f96a78d9c3b28603ab75b1a2`
- `/home/parinya/university/iwing-tracker/gateway-lora/mainboard/pcb/2026-02-21/Schematic_Main_Board_rudolph_gw_2026-02-21.pdf` — SHA-256 `885f53f295db6f0325acbb3e3411d2901d798c3f01eb4a6a48ad570697db581d`
- Extracted text: [gateway_radio.txt](references/schematic_text/gateway_radio.txt), [gateway_main.txt](references/schematic_text/gateway_main.txt)

The Gateway RFM95/98 daughterboard has its own pinout and 3.3 V supply interface. Its PA7 is an address strap, not the Tracker radio power gate. The two boards' GPIO power policies must remain distinct.

## Live Host evidence and limits

At 2026-11-14 07:01 UTC, two CP2102 devices (`VID:PID 10c4:ea60`) were enumerated at the configured Tracker and Gateway USB paths. Each descriptor reported `Bus Powered` and `MaxPower 100mA`; both `fuser` checks showed no owner. The duplicate CP2102 USB serial string is not unique enough to identify the boards; previously captured unique MCU serials were used for the configured role mapping.

No MCU VDD, 3V3-LORA, 3V3-GPS, 3V3-SD, adapter output, current, or transient waveform was measured. No oscilloscope, logic analyzer, independent RF receiver, or voltage logger was available through this session. GPS and SD commanded states in the diagnostic source are not measurements of their switched rails.

**Power conclusion:** supply and back-feed conditions remain UNKNOWN. The 2026-11-14 RF candidate was not flashed or transmitted. The exact physical follow-up is to inspect the adapter and battery connections, verify one isolated source and common reference, then measure the 3.3 V source and Tracker rails under the intended radio load.
