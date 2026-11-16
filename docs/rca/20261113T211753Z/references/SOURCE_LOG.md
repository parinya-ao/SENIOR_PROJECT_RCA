# Source log

## External technical sources

| Claim | Primary source | Revision / section | Confidence | Applicability |
|---|---|---|---|---|
| AVR128DA POR is always enabled and reasserts reset if VDD falls below VPORR | [Microchip AVR128DA28/32/48/64 datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/AVR128DA28-32-48-64-Data-Sheet-40002183C.pdf) | DS40002183C, section 13.3.2.1.1; POR threshold and VPORR | High | Exact MCU family; explains PORF, but does not measure the rail |
| RSTFR contains UPDIRF, SWRF, WDRF, EXTRF, BORF, PORF; flags are W1C | [Microchip AVR128DA RSTCTRL register summary](https://onlinedocs.microchip.com/oxy/GUID-BD668D46-A7E4-40CA-8B1D-4EB24BAA33C3-en-US-4/GUID-FC2B261E-5A4E-441E-890B-26EC98D015E8.html) and the datasheet above | DS40002183C, sections 13.4–13.5 | High | Exact MCU family |
| BOD ACTIVE/SLEEP values of zero mean disabled; POR remains independent and enabled | Same AVR128DA datasheet | DS40002183C, §18.3.1 BOD.CTRLA tables; §13.3.2.1.1 | High | Exact fuse block was read back as 0000f0ffffd2f80000ffffffffffffff |
| AVR128DA GPRs occupy data-space 0x1C–0x1F | [Microchip AVR DA GPR chapter](https://onlinedocs.microchip.com/oxy/GUID-3EE676DF-490E-41BC-98F0-5774B35DC989-en-US-25/GUID-0DF85C28-7E10-45F7-8DF6-2F1BBF58400E.html) | DS40002183C, section 9 | High | Exact MCU family; physical A/B established the STS behavior |
| AVR DA/DB uses a dedicated UPDI pin | [Microchip UPDI interface](https://onlinedocs.microchip.com/oxy/GUID-8D61C0B9-A97F-4F4D-99F8-1D7424264C2A-en-US-1/GUID-B29416BA-442A-461F-A90F-542C149DC9CC.html) | UPDI interface description | High | AVR DA/DB family |
| SX1276 device/register behavior | [Semtech SX1276 product and datasheet page](https://www.semtech.com/products/wireless-rf/lora-connect/sx1276) | SX1276/77/78/79 datasheet | High for device facts | Runtime state is only claimed where locally read back |
| RFM95W module behavior | [HopeRF RFM95W datasheet](https://www.hoperf.com/uploads/RFM95W-V2.0_1695351437.pdf) | RFM95W V2.0 | High for module facts | No board-specific electrical or RF measurement was captured |

## Local implementation sources

- Active UPDI implementation: third_party/upditerm/upditerm.py.
- Virtual UART firmware: third_party/upditerm/updi_uart.c.
- Raw TX/RX state machine: src/reverse_raw/main.cpp.
- Board role and pin maps: config/current_hardware.json, docs/ssot/TRACKER_SSOT.md, docs/ssot/GATEWAY_SSOT.md.
- DxCore reset startup: /home/parinya/.platformio/packages/framework-arduino-megaavr-dxcore/cores/dxcore/main.cpp:145–150 reads RSTFR, clears it, and stores the original flags in GPIOR0.
- AVR128DA toolchain header: /home/parinya/.platformio/packages/toolchain-atmelavr/avr/include/avr/ioavr128da28.h; RSTCTRL.RSTFR is data-space address 0x0040.
- Installed RadioLib: 7.1.2 from PlatformIO dependency resolution; no library upgrade was performed.

## Claim limits

No datasheet claim is used to assert RF emission or a valid RF link. TxDone is a local radio event, not an independent radiation measurement. The user's 3.3 V statement is not an electrical measurement.
