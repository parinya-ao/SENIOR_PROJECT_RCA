# Gateway Hardware SSOT — Rudolph Gateway

**Version:** 1.0 (2026-11-07)  
**Target architecture:** **Main Board Rudolph GW** rev 1.0 dated **2026-02-21** + **LoRa Board Rudolph GW** rev 1.0 dated **2025-04-26**, with **four identical LoRa daughterboard slots** U5/U6/U7/U8.  
**Status:** schematic-verified design intent. Physical population, revision, solder bridges, power and I2C host software still require verification.

**Experiment role:** Gateway = **Sender** (`sender` / `sender_hello` / `sender_hello_spi`). Tracker = Receiver; its separate pins and power gates are defined in [TRACKER_SSOT.md](TRACKER_SSOT.md).

## 1. System topology

- Main board host **U11 Lilygo ESP32 WROVER E**.
- Up to **4 × LoRa Board Rudolph GW**, U5–U8; each daughterboard contains its own **AVR128DA28 (U1)** and **RFM95/98 footprint (U2)**. The four radio boards **do not share an MCU**.
- Main board supply: **VBAT**, switch **SW1**, **U10 AP2112K-3.3TRG1** for `3V3-LORA`, **Q3 SI2393DS** power path, and **Q1 RQ5C060BCTCL** for `3V3-OLED`. Exact VIN/EN states and the host VCC rail must be tested on assembled hardware; do not equate `VCC`, `VBAT` and `3V3-LORA` without measuring.
- Daughterboard **VCC** is fed from main-board `3V3-LORA`; the daughterboard schematic itself **does not show a local regulator**.
- Main-board radio-module fanout consists of per-module serial RX0..RX3, UPDI0..UPDI3, INT0..INT3; **shared SCL and SDA** with separate board-select/address signals A0/A1 held at board-specific levels.

## 2. Daughterboard MCU and RFM95W SSOT

| MCU | Net | Purpose |
|---|---|---|
| PA7 | A0 | Gateway I2C/address strap/control signal, **not radio power-enable**. |
| PA6 | A1 | Gateway I2C/address strap/control signal. |
| PA5 | LED1 | Active-low indicator (1 kΩ path to VCC). |
| PA4 | LED2 | Active-low indicator (1 kΩ path to VCC). |
| PA3 | SCL | TWI/I2C clock, host interface. |
| PA2 | SDA | TWI/I2C data, host interface. |
| PA1 | TX schematic net | **MCU USART0 RX** on referenced DxCore 28-pin core; connector label is opposite MCU direction. |
| PA0 | RX schematic net | **MCU USART0 TX** on referenced DxCore 28-pin core; connector label is opposite MCU direction. |
| PC0 | MOSI | Radio SPI MOSI. |
| PC1 | MISO | Radio SPI MISO. |
| PC2 | SCK | Radio SPI clock. |
| PC3 | NSS | **Radio chip-select** (not Tracker SD select). |
| PD0 | RST | **Radio reset**. |
| PD1 | INT | Host-facing interrupt output; **not LoRa IRQ**. |
| PD2 | DIO0 | **Radio IRQ**. |
| PD3 | DIO1 | Radio additional GPIO. |
| PD4 | DIO2 | Header pass-through; no established current firmware use. |
| PD5 | DIO3 | Header pass-through; no established current firmware use. |
| PD6 | DIO4 | Header pass-through; no established current firmware use. |
| PD7 | DIO5 | Header pass-through; no established current firmware use. |
| UPDI | UPDI | Flash/debug per module. |

### Radio SPI and interrupt contract

```cpp
// Gateway daughterboard only, never Tracker:
#define GW_LORA_CS    PIN_PC3
#define GW_LORA_RST   PIN_PD0
#define GW_LORA_IRQ   PIN_PD2 // RFM DIO0
#define GW_LORA_DIO1  PIN_PD3
#define GW_HOST_INT   PIN_PD1 // distinct from LoRa IRQ
#define GW_LED1       PIN_PA5
#define GW_LED2       PIN_PA4
#define GW_ADDR_A0    PIN_PA7
#define GW_ADDR_A1    PIN_PA6
// SPI: MOSI=PC0, MISO=PC1, SCK=PC2.
```

The supplied repository's `PIN_MAPPING_AUDIT.md` records `SPI.swap(SPI1_SWAP_DEFAULT)` as the intended **DxCore 1.6.2 SPI1** route for PC0–PC2, before RadioLib initialization. Gateway radio NSS is PC3. `src/receiver/main.cpp` implements the **Tracker Receiver** and consumes its separately generated board pins; the common SPI peripheral does not imply common NSS, reset, interrupt or power-enable pins.

## 3. Daughterboard external connectors

### H1 (10-pin; only pins 1–5 used in the source schematic)

| Pin | Schematic signal | Constraint |
|---:|---|---|
| 1 | VCC | 3.3V design rail, **live value unmeasured**. |
| 2 | GND | common ground required. |
| 3 | TX | connected to PA1; **MCU RX** according to installed DxCore audit. Do not assume label is host TX. |
| 4 | RX | connected to PA0; **MCU TX** according to installed DxCore audit. |
| 5 | UPDI | target-specific programmer connection. |
| 6–10 | NC | not connected in referenced schematic. |

### H2 (10-pin)

| Pin | Signal | MCU |
|---:|---|---|
| 1 | A0 | PA7 |
| 2 | A1 | PA6 |
| 3 | INT | PD1 |
| 4 | SCL | PA3 |
| 5 | SDA | PA2 |
| 6 | DIO1 | PD3 |
| 7 | DIO2 | PD4 |
| 8 | DIO3 | PD5 |
| 9 | DIO4 | PD6 |
| 10 | DIO5 | PD7 |

## 4. Four module slot mappings from Main Board

| Main slot | Daughterboard | Serial net from ESP32 | UPDI | Host interrupt | Shared I2C |
|---|---|---|---|---|---|
| U5 | LoRa Board 0 | RX0 | UPDI0 | INT0 | SCL, SDA |
| U6 | LoRa Board 1 | RX1 | UPDI1 | INT1 | SCL, SDA |
| U7 | LoRa Board 2 | RX2 | UPDI2 | INT2 | SCL, SDA |
| U8 | LoRa Board 3 | RX3 | UPDI3 | INT3 | SCL, SDA |

**A0/A1 strapping:** schematic shows per-slot 200 Ω networks R3–R10, with the A0/A1 bits at alternating high/low positions. Derive and confirm each actual two-bit I2C address combination from continuity and host-firmware setup before hardcoding addresses; the schematic alone does not define a complete I2C 7-bit slave-address constant.

Main board also exposes **CN0–CN3** for RXn/UPDIn/service and **CN5** for ESP32 monitoring, along with P1/P2 power switches/connectors. The exact host ESP32 GPIO-number mapping is printed in the schematic; preserve this mapping in a separate host-software table after checking the assembled revision. In particular the host `SCL`, `SDA`, `INT0`...`INT3`, `EN-OLED` signal labels do not imply AVR pin equivalence.

## 5. Power, RF and hardware safety

- `3V3-LORA` is supplied by **AP2112K-3.3TRG1** on Main Board, not Tracker's U7 TPS7A02. The regulator is nominally a **600 mA** family, but this is an **overall shared rail rating**, **not 600 mA per installed daughterboard**. Validate datasheet limits, input voltage/dropout, power dissipation, peak simultaneous radio transmit load and temperature.
- Each daughterboard RFM95/98 is connected directly to daughterboard VCC; there is **no per-board LoRa power-enable PA7**. PA7 is A0.
- Radio ANT net selects SMA through SB1 or U.FL through SB2. Confirm which bridge is soldered and compatible antenna is attached. Module marking/frequency and applicable RF limits remain unknown.
- Preserve `BOOT` and installed firmware until physical reset/power evidence is resolved. **Source audit/host unit tests are not live hardware tests.**
- Historical report `HARDWARE_PREFLIGHT_REPORT.md`: RF-disabled Receiver APPCODE and BOOT readback passed, but normal startup remained unresolved with observed BORF resets and no physical radio response. Those are dated observations of the then-tested device, not blanket electrical proof for every board.

## 6. Minimal validation gates

- [ ] Confirm Main Board 2026-02-21 and LoRa Board 2025-04-26 on actual assemblies.
- [ ] Verify each slot receives correct `3V3-LORA`, common GND, correct MCU orientation, correct A0/A1 strap state.
- [ ] Validate 3V3-LORA current under **all populated radio boards** and inrush; do not divide AP2112K peak rating into per-board guarantees.
- [ ] Confirm only one intended I2C address per populated slot, plus pull-ups and correct bus voltage.
- [ ] Confirm correct role association of USB/UPDI per target using MCU identity; `/dev/ttyUSBn` alone is not an identity.
- [ ] On each daughterboard test SPI1 PC0–PC2, CS PC3, RESET PD0, IRQ PD2, DIO1 PD3 with **read-only** radio register transaction.
- [ ] Inspect RF module part marking and SB1/SB2 antenna path before any TX.
- [ ] Test no unexpected reset / no BORF during MCU boot and radio init.

## Sources

- `Schematic_LoRa_Board_rudolph_gw_2025-04-26.pdf` (daughterboard, rev 1.0, 2025-04-26).
- `Schematic_Main_Board_rudolph_gw_2026-02-21.pdf` (motherboard, rev 1.0, 2026-02-21).
- Supplied `compact-bundle.xml`: `PIN_MAPPING_AUDIT.md`, `HARDWARE_PREFLIGHT_REPORT.md`, `platformio.ini`.
- Microchip AVR128DA: https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-40002183C.pdf
- HopeRF: https://www.hoperf.com/uploads/RFM95W-V2.0_1695351437.pdf
