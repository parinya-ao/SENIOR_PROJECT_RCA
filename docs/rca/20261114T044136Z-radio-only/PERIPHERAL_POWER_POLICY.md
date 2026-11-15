# Tracker peripheral power policy

OBSERVED schematic intent: Tracker RFM revision 1.0, 2025-02-16, sheet 1/1. [Extracted schematic](references/tracker-schematic.txt). Q1/Q2/Q3 are P-channel high-side switches with gate pull-ups: PA7, PD5 and PD6 respectively are active-low enables. Gateway has different wiring; its PA7 is an address signal.

| Item | Diagnostic policy | Electrical limit |
|---|---|---|
| RFM95W / Q1 | PA7 low after safe startup; retained through DATA and ACK | GPIO intent does not establish rail voltage |
| SAM-M10Q / Q2 | Disable USART2; PF0/PF1 and PD4 inputs without pull-ups; then PD5 high | PF0 is MCU TX to GPS RXD; PF1 is MCU RX from GPS TXD. VCC and V_IO share switched 3V3-GPS |
| GNSS backup | No modification | V_BCKP remains connected to its independent backup network |
| SD / Q3 | PD6 high; empty socket required before radio SPI starts | PC0/PC1/PC2 and PC3 are directly wired to CARD1; CS alone cannot isolate unpowered signal pins |
| IMU and 24C512 | No application acquisition/I2C/EEPROM activity | Both remain physically powered by main 3V3 |
| LEDs | PA5/PA6 released; no generic LED activity | DxCore `LED_BUILTIN` maps to PA7 and must not control LEDs on Tracker |
| MCU / timers / UPDI | Existing core and diagnostics retained | No fuse, BOOT, watchdog or persistent-memory changes |

The policy is a cold-start ARQ policy: this source target contains no active GPS/SD transactions to drain. It must not be reused as a shutdown routine for a running filesystem or GNSS task. `Serial.end()` is not relied upon for pin isolation.

The schematic leaves SAM-M10Q SDA/SCL, EXTINT, RESET_N and SAFEBOOT_N unconnected. Thus its UART and TIMEPULSE are the connected MCU interfaces needing attention. The main-rail I2C pull-ups serve IMU/EEPROM, not the GPS. The shared SD SPI bus has no buffer or isolator shown.

## New live baseline observations

The candidate was not flashed. [Tracker before](raw/receiver/registers-before.json) and [after](raw/receiver/registers-after.json) are direct UPDI reads from the preserved firmware:

| Register | Before → after | Derived interpretation |
|---|---|---|
| PORTD.DIR | 0x63 → 0x63 | PD5 and PD6 outputs |
| PORTD.OUT / IN | 0x63 → 0x63 | GPS/SD enables commanded and sampled high |
| PORTA.DIR / OUT | 0x80 / 0x00, unchanged | PA7 output low, commanding LoRa on |
| PORTC.DIR / OUT | 0x0D / 0x08, unchanged | SD CS PC3 output high; SPI MOSI/SCK outputs |
| USART2.CTRLA / CTRLB | 0 / 0, unchanged | UART interrupt/transceiver enables off |
| PORTF.DIR / OUT | 0 / 0, unchanged | GPS UART pins inputs |
| PF0/PF1 PINCTRL | 0 / 0, unchanged | No internal pull-up enabled |

These observations show that the preserved ARQ baseline already commands GPS/SD off. A proposed peripheral-only comparison cannot claim that their load was newly removed. The candidate adds explicit pin-release ordering and the SD guard.

UNKNOWN: actual 3V3-GPS/3V3-SD voltage, leakage, shared-bus injection with an inserted card, MCU VDD minimum, 3V3-LORA minimum/current, adapter regulator source and cable resistance. No voltage instrument was available. SD_DETECT without the diagnostic pull-up does not independently establish an empty socket.

## Physical release conditions

The latest [ARQ debugging hold](../../arq/DEBUGGING.md) requires physical antenna/module/bridge verification before RF. H1 source selection, common ground and absence of competing power outputs also need verification; USB identity and a nominal 3.3 V report cannot establish that topology. Keep the SD socket empty for this candidate. Do not bypass these conditions by supplying an RF-confirmation CLI flag from software.
