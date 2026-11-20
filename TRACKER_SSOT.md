# Tracker Hardware SSOT — LoRa Tracker RFM

**Version:** 1.0 (2026-11-07)  
**Target:** `LoRa Tracker RFM`, schematic revision 1.0, dated **2025-02-16**.  
**Status:** schematic-verified design intent; **not** physical assembly or live electrical verification.  
**Experiment role:** Tracker = **Receiver** (`receiver` / `receiver_spi`); Gateway = Sender.  
**Authority order:** (1) correct board revision schematic + PCB, (2) manufacturer datasheets for behavior/limits, (3) measured physical board observations, (4) firmware as an implementation to audit—not as hardware truth. When physical wiring differs, record a new revision/exception instead of silently changing this file.

## 1. Board identity and components

- MCU: **U6 AVR128DA28**.
- Radio: **U4 RFM95W**, SPI, separately power switched.
- GNSS: **U1 SAM-M10Q**; IMU: **U2 LSM6DSOXTR**; EEPROM: **U3 24C512**; SD card: **CARD1 SD-01A**.
- Power input: **JP1 Battery → U7 TPS7A0233DBV → 3V3**. U7 is a **200 mA** LDO by manufacturer rating. **This limit applies only to a current path actually supplied through U7.**
- Switched rails: **3V3-LORA (Q1)**, **3V3-GPS (Q2)**, **3V3-SD (Q3)**; Q1/Q2/Q3 `RQ5C060BCTCL` P-channel high-side switches, with pull-up gates and 200 Ω MCU drive resistance.
- External header **H1**: schematic shows 3V3, UART_TX, UART_RX, UPDI and GND. **H1 feeding 3V3 bypasses U7's input-to-output current path**. Verify which H1 pin, cable and voltage source actually powers the tested board; do not transpose the Gateway H1 pinout.

## 2. AVR128DA28 pin and net SSOT

| MCU | Board net | Function | Output/input, reset-safe guidance |
|---|---|---|---|
| PA7 | EN-LORA | Q1 high-side radio power gate | Output; **LOW = ON, HIGH = OFF** (active-low). Preload HIGH before output-enable if OFF is intended. |
| PA6 | LED1 | LED1 via 1 kΩ to 3V3 | Output, **LOW = LED ON** (LED is tied toward 3V3). |
| PA5 | LED2 | LED2 via 1 kΩ to 3V3 | Output, **LOW = LED ON**. |
| PA4 | SD_DETECT | SD-card detect switch | **Input**, never use as LED or generic output. |
| PA3 | SCL | TWI/I2C clock | Peripheral/TWI as used; shared IMU, EEPROM, GNSS. |
| PA2 | SDA | TWI/I2C data | Peripheral/TWI as used. |
| PA1 | UART_TX | UART net (schematic label) | Route/configure USART according to hardware/core mapping; inspect actual TX direction before enabling. |
| PA0 | UART_RX | UART net (schematic label) | Route/configure USART according to hardware/core mapping; inspect actual RX direction before enabling. |
| PC0 | MOSI | SPI to LoRa and SD | SPI master MOSI. |
| PC1 | MISO | SPI from LoRa and SD | SPI master MISO. |
| PC2 | SCLK | Shared SPI clock | SPI master SCK. |
| PC3 | SD_SS | SD chip select | Output, idle inactive HIGH for active-low CS. |
| PD0 | RF_SS | LoRa NSS/chip select | Output, idle **HIGH**. |
| PD1 | RF_RST | LoRa hardware reset | Keep INPUT/high impedance during power-on reset; after power is valid the driver may pulse LOW/release for manual reset. Never drive an unpowered radio. |
| PD2 | RF_DIO1 | LoRa DIO1 | Input (radio signaling). |
| PD3 | RF_IRQ | LoRa DIO0 / IRQ | Input; attach the proper interrupt according to library. |
| PD4 | GPS_PPS | GNSS timepulse | Input. |
| PD5 | EN-GPS | Q2 GNSS power | Output, **LOW = ON, HIGH = OFF** by same P-channel topology. |
| PD6 | EN-SD | Q3 SD power | Output, **LOW = ON, HIGH = OFF** by same P-channel topology. |
| PD7 | BATT_PROBE | Battery divider R14=100k / R15=10k | Analog input; nominal divider ratio **1/11** ignoring loading and tolerance. |
| PF0 | GPS_RX | MCU-side GPS receive net label | Check UART peripheral direction against schematic on integration. |
| PF1 | GPS_TX | MCU-side GPS transmit net label | Check UART peripheral direction against schematic on integration. |
| PF6 | IMU_INT | IMU interrupt | Input. **PF6 is also MCU RESET-capable according to device package labeling**; verify fuse/reset configuration before assuming ordinary GPIO. |
| UPDI | UPDI | Programming/debug | Reserved for UPDI, not free GPIO. |

### Exact LoRa RFM95W signal map

| RFM95W pin | Radio signal | AVR pin |
|---:|---|---|
| 2 | MISO | PC1 |
| 3 | MOSI | PC0 |
| 4 | SCK | PC2 |
| 5 | NSS | **PD0** |
| 6 | RESET | **PD1** |
| 13 | 3.3V | **3V3-LORA** switched rail |
| 14 | DIO0 | **PD3** (`RF_IRQ`) |
| 15 | DIO1 | **PD2** (`RF_DIO1`) |
| 9 | ANT | Antenna net J1 |

SPI is shared with SD; **radio NSS is PD0 and SD CS is PC3**. Ensure both chip-selects are inactive when the other slave is accessed.

## 3. Power and startup contract

1. The **3V3** base rail powers the MCU. Radio, GPS and SD are behind separately controlled high-side power switches.
2. To keep switched peripherals OFF, set **PA7/PD5/PD6 HIGH before configuring their direction OUTPUT**. To enable a peripheral, drive its enable LOW; allow rail stabilization, then perform peripheral RESET or SPI operations. Actual rail rise/settling is **TBD by measurement**, not established by a fixed delay. The Receiver candidate includes the manufacturer's 10 ms POR guard, keeps RF_RST high impedance, and leaves GPS/SD power disabled; that software wait is not proof that the physical rail has settled.
3. `3V3-LORA` has local 100 µF (`C11`) plus 100 nF (`C8`) decoupling in the schematic. Bulk capacitance does not prove the supply survives turn-on inrush.
4. U7 `TPS7A0233DBV` is rated for **200 mA**, but when 3V3 is injected at **H1 downstream of U7**, the LDO rating is **not the available current budget**. The upstream external supply, cable, connector, regulator and return path become the relevant limits.
5. A **BORF** reset flag supports an undervoltage/reset investigation, **not** proof that a particular regulator is undersized. Record oscilloscope min voltage at MCU VDD, 3V3-LORA and source during cold start and power-enable.

The external USB -> CP2102 -> UPDI/UART SWITCHER -> H1 path is operator-reported. Switcher BOARD header mapping and power/signal selections remain unverified; do not infer them from wire colours or PASS/CUT labels. No further UPDI/OCD or programming is implied by this design mapping.

## 4. Minimal firmware implementation contract

```cpp
// Board mapping only. Validate the correct DxCore PIN_P* aliases before build.
#define TRK_LORA_EN    PIN_PA7  // active LOW
#define TRK_LED1       PIN_PA6  // active LOW
#define TRK_LED2       PIN_PA5  // active LOW
#define TRK_SD_DETECT  PIN_PA4  // INPUT
#define TRK_SPI_MOSI   PIN_PC0
#define TRK_SPI_MISO   PIN_PC1
#define TRK_SPI_SCK    PIN_PC2
#define TRK_SD_CS      PIN_PC3
#define TRK_LORA_CS    PIN_PD0
#define TRK_LORA_RST   PIN_PD1
#define TRK_LORA_DIO1  PIN_PD2
#define TRK_LORA_IRQ   PIN_PD3 // DIO0
#define TRK_GPS_EN     PIN_PD5 // active LOW
#define TRK_SD_EN      PIN_PD6 // active LOW
```

Do **not** copy Gateway radio pin macros into this Tracker build. The correct SPI peripheral routing for PC0–PC2 must be selected explicitly in the installed core, rather than assuming a default SPI bus.

## 5. Acceptance criteria / physical evidence

- [ ] Physical PCB revision and assembled module markings match this 2025-02-16 schematic.
- [ ] H1 power source, MCU 3V3, common GND, and backfeed paths measured and documented.
- [ ] With radio OFF, PA7=HIGH and 3V3-LORA is off; with radio ON, PA7=LOW and rail settles before SPI access.
- [ ] LED1 PA6 / LED2 PA5 toggle; **PA4 SD_DETECT remains input**.
- [ ] SPI chip select inactive idle; read-only RFM register `0x42` returns a plausible device version **on real hardware**.
- [ ] Reset cause captured; MCU VDD waveform checked for sag at switch-on.
- [ ] No RF transmission until fitted antenna/module frequency are confirmed.

## 6. Firmware configuration

The separate 17-field tracker configuration model is documented in
[`TRACKER_CONFIG_SSOT.md`](TRACKER_CONFIG_SSOT.md) and defined in
`include/tracker_config.h`. It does not override the active one-shot receiver
profile or the hardware facts in this file.

## Sources

- Local design: `Schematic_LoRa-Tracker-RFM_2025-02-16.pdf` (2025-02-16, sheet 1/1), `pcb-top.pdf`, `pcb-bottom.pdf`.
- TI TPS7A02 official specs: https://www.ti.com/product/TPS7A02
- HopeRF RFM95W manufacturer datasheet: https://www.hoperf.com/uploads/RFM95W-V2.0_1695351437.pdf
- Microchip AVR128DA datasheet: https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-40002183C.pdf
