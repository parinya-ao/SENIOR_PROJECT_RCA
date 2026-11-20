# AVR128DA28 LoRa Board Pin Audit

## Evidence basis

This audit follows the active role-specific SSOT and checked board schematics.
The Gateway and Tracker use different radio pins. MCU package pin numbers below
use the official 28-pin AVR128DA28 pinout. The Gateway BOM identifies an
AVR128DA28-I/SS and RFM95W module. The Tracker SSOT identifies an RFM95W.

| Design source | Workspace path | SHA-256 |
|---|---|---|
| Gateway LoRa daughterboard schematic, 2025-04-26 | [Schematic_LoRa_Board_rudolph_gw_2025-04-26.pdf](../iwing-tracker/gateway-lora/loraboard/pcb/2025-04-26/Schematic_LoRa_Board_rudolph_gw_2025-04-26.pdf) | 11706846afef7a3c66394978acdeb1d0368c7de9f96a78d9c3b28603ab75b1a2 |
| Gateway LoRa daughterboard BOM, 2025-04-26 | [BOM_LoRa_Board_rudolph_gw_2025-04-26.csv](../iwing-tracker/gateway-lora/loraboard/pcb/2025-04-26/BOM_LoRa_Board_rudolph_gw_2025-04-26.csv) | 5f89a9b2801204bf7b662227816b297ea8f605d02e31bca9ee7f4894af44ce01 |
| Tracker schematic, 2025-02-16 | [Schematic_LoRa-Tracker-RFM_2025-02-16.pdf](../iwing-tracker/device-lora/pcb/2025-02-16/Schematic_LoRa-Tracker-RFM_2025-02-16.pdf) | 8699b9205621851e5322f16407298d2d6644d265170f18aeb800f77ba13a7612 |
| Gateway mainboard schematic, 2026-02-21 | [Schematic_Main_Board_rudolph_gw_2026-02-21.pdf](../iwing-tracker/gateway-lora/mainboard/pcb/2026-02-21/Schematic_Main_Board_rudolph_gw_2026-02-21.pdf) | 885f53f295db6f0325acbb3e3411d2901d798c3f01eb4a6a48ad570697db581d |

The schematic files live in the sibling iwing-tracker repository. That
repository was read only at revision
2aa85001d50cf55285c97556d01fd21d622acc79. Firmware role mappings come from
[config/radio_915.toml](config/radio_915.toml), checked against
[GATEWAY_SSOT.md](GATEWAY_SSOT.md), [TRACKER_SSOT.md](TRACKER_SSOT.md), and
their generated board headers.

The pin and net connections are design-verified. Board assembly, solder
bridges, continuity, live rail voltage, antenna fit, MCU identity, and connected
devices were not inspected in this session. Those physical checks are **NOT
TESTED**.

## AVR128DA28 package pins

These numbers are from the 28-pin SPDIP, SSOP, and SOIC pinouts. The Gateway
BOM specifies SSOP-28. The exact Tracker package suffix is not independently
confirmed in its schematic.

| MCU signal | Package pin | MCU signal | Package pin |
|---|---:|---|---:|
| PA7 | 1 | PA0 / EXTCLK | 22 |
| PC0 | 2 | PA1 | 23 |
| PC1 | 3 | PA2 | 24 |
| PC2 | 4 | PA3 | 25 |
| PC3 | 5 | PA4 | 26 |
| PD0 | 6 | PA5 | 27 |
| PD1 | 7 | PA6 | 28 |
| PD2 | 8 |  |  |
| PD3 | 9 |  |  |
| PD4 | 10 |  |  |
| PD5 | 11 |  |  |
| PD6 | 12 |  |  |
| PD7 | 13 |  |  |
| AVDD | 14 | PF0 / XTAL32K1 | 16 |
| GND | 15 | PF1 / XTAL32K2 | 17 |
| PF6 / RESET | 18 | UPDI | 19 |
| VDD | 20 | GND | 21 |

Source is Microchip's [AVR128DA28/32/48/64(S) data sheet, DS40002183](https://www.microchip.com/content/dam/mchp/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-DS40002183.pdf), pinout section 2.

The schematics use a 3.3 V design rail for VDD/AVDD. The datasheet states those
domains are internally connected. GND is on package pins 15 and 21. Actual rail
voltage and ground continuity were not measured.

## Gateway LoRa daughterboard

The active profile selects SPI1_SWAP_DEFAULT for PC0-PC3. The installed
DxCore 1.6.2 maps those signals to the expected SPI1 pins on the 28-pin target.
The Gateway has no firmware radio power-enable signal. PA7 is A0, a board
address/control net, not EN-LORA.

| Signal | AVR pin / package pin | RFM95/98 U2 pin | Direction and active level | Initialization and status |
|---|---|---:|---|---|
| MOSI | PC0 / 2 | 3 | MCU output | SPI1 route selected before RadioLib initialization; design-verified |
| MISO | PC1 / 3 | 2 | MCU input | SPI1 route; design-verified |
| SCK | PC2 / 4 | 4 | MCU output | SPI1 route; design-verified |
| NSS / CS | PC3 / 5 | 5 | Output, active-low, idle HIGH | SSOT and schematic match; design-verified |
| RESET | PD0 / 6 | 6 | Output during reset; HIGH after reset | Current profile and schematic match; design-verified |
| Host INT | PD1 / 7 | — | Output, host interrupt distinct from LoRa IRQ | H2 pin 3; design-verified |
| DIO0 / IRQ | PD2 / 8 | 14 | Input | Radio IRQ, not PD1; design-verified |
| DIO1 | PD3 / 9 | 15 | Input | Additional RadioLib GPIO; design-verified |
| A0 | PA7 / 1 | — | Board address/control; strap direction/level not verified | H2 pin 1; not radio power |
| A1 | PA6 / 28 | — | Board address/control; strap direction/level not verified | H2 pin 2 |
| LED1 | PA5 / 27 | — | Output, active-low | Design-verified |
| LED2 | PA4 / 26 | — | Output, active-low | Design-verified |
| I2C SCL | PA3 / 25 | — | TWI clock | H2 pin 4; design-verified |
| I2C SDA | PA2 / 24 | — | TWI data | H2 pin 5; design-verified |
| USART0 RX | PA1 / 23 | — | MCU receives on PA1 | H1 pin 3 is labelled TX; label is host-side |
| USART0 TX | PA0 / 22 | — | MCU transmits on PA0 | H1 pin 4 is labelled RX; label is host-side |
| UPDI | UPDI / 19 | — | Programming/debug | H1 pin 5; adapter and target identity not tested |
| Module supply | — | 13 | 3.3 V design rail | Live voltage not measured |
| Antenna | — | 9 | RF net | Bridge selection and antenna fit not inspected |

H1 pins are VCC, GND, TX, RX, UPDI on pins 1-5, with 6-10 NC in the cited
schematic. H2 carries A0, A1, INT, SCL, SDA, DIO1-DIO5 on pins 1-10. The
mainboard routes daughterboard slots U5-U8 to serial nets RX0-RX3, UPDI0-UPDI3,
INT0-INT3, and shared I2C. ESP32 GPIO numbers and assembled connector
continuity are **NOT VERIFIED**.

The BOM lists both U.FL and SMA footprints, while the schematic selects the
antenna path through solder bridges. The installed bridge and antenna are
**NOT TESTED**.

## Tracker

Tracker uses the same MCU SPI signals but separate radio NSS, RESET, IRQ, DIO1,
and power control. Startup first holds the active-low radio, GNSS, and SD gates
off while configuring their controls. It then enables the radio and waits for
the configured settle interval before setting the radio IRQ/DIO1 inputs and
idling CS HIGH before SPI/radio initialization. GNSS and SD remain isolated
during radio-only tests.

| Signal | AVR pin / package pin | RFM95W U4 pin | Direction and active level | Initialization and status |
|---|---|---:|---|---|
| MOSI | PC0 / 2 | 3 | MCU output | Shared SPI1; design-verified |
| MISO | PC1 / 3 | 2 | MCU input | Shared SPI1; design-verified |
| SCK | PC2 / 4 | 4 | MCU output | Shared SPI1; design-verified |
| SD CS | PC3 / 5 | SD-01A socket pin 2, CD/DAT3 | Output, active-low, idle HIGH | SSOT and schematic match |
| Radio NSS / CS | PD0 / 6 | 5 | Output, active-low, idle HIGH | SSOT, schematic, and firmware agree |
| Radio RESET | PD1 / 7 | 6 | High-impedance during power-up; driver may pulse LOW after power is valid | Never drive an unpowered radio |
| DIO1 | PD2 / 8 | 15 | Input | Radio signaling; design-verified |
| DIO0 / IRQ | PD3 / 9 | 14 | Input | RadioLib IRQ input; design-verified |
| Radio power gate | PA7 / 1 | U4 pin 13 rail | Output, LOW = ON, HIGH = OFF | Q1 switches 3V3-LORA; live voltage not measured |
| LED1 | PA6 / 28 | — | Output, active-low | Design-verified |
| LED2 | PA5 / 27 | — | Output, active-low | Design-verified |
| SD detect | PA4 / 26 | SD-01A detect switch | Input | Design-verified |
| I2C SCL / SDA | PA3 / 25, PA2 / 24 | — | TWI | Shared IMU, EEPROM, and GNSS bus |
| GNSS PPS | PD4 / 10 | — | Input | Design-verified |
| GNSS power | PD5 / 11 | — | Output, LOW = ON | Q2 high-side gate; design-verified |
| SD power | PD6 / 12 | — | Output, LOW = ON | Q3 high-side gate; design-verified |
| Battery probe | PD7 / 13 | — | Analog input | Divider ratio nominally 1/11; live voltage not measured |
| GNSS UART nets | PF0 / 16, PF1 / 17 | GNSS module pins unavailable | Board labels GPS_RX/GPS_TX; MCU direction not independently checked | NOT VERIFIED at integration |
| IMU interrupt | PF6 / 18 | LSM6DSOX INT1 net | Input; PF6 is also RESET-capable | Fuse/reset configuration not read |
| UPDI | UPDI / 19 | — | Programming/debug | Net exists in schematic; connector and live target not checked |
| Module supply | — | 13 | Switched 3V3-LORA rail | Live voltage not measured |
| Antenna | — | 9 | ANT to J1 | Continuity and antenna fit not tested |

The microSD socket uses DAT2, CD/DAT3, CMD, VDD, CLK, VSS, DAT0, and DAT1 on
socket pins 1-8. In SPI mode the board routes CMD/MOSI, DAT0/MISO, CLK/SCK, and
CD/DAT3/SD_SS. Exact GNSS module connector pin numbers are **NOT VERIFIED** in
the cited Tracker schematic.

## Radio profile and serial identity

The active profile is in [config/radio_915.toml](config/radio_915.toml). Both
roles use 915 MHz, 125 kHz bandwidth, SF7, RadioLib coding-rate parameter 5,
sync word 0x12, configured TX power 2 dBm, 8 preamble symbols, CRC enabled,
explicit headers, and normal IQ polarity. The RadioLib adapter sets a 200 mA
current limit. long_range=0 selects the standard SF7 path.

The ARQ-only profile additionally records a 1 MHz SPI clock in
[config/arq_test.toml](config/arq_test.toml). The addressed RadioLib adapter
does not set an SPI clock in the radio profile, so its effective bus clock was
not measured in this session. No RF parameters changed during this audit.

Use uv run --no-sync python tools/detect_devices.py --scan --json --explain for
passive USB inventory. Probe MCU identity only after mapping a present adapter
to the correct UPDI connection. PlatformIO upload_port strings are configuration
examples, not role identity. This environment has no /dev/serial/by-path and the
passive scan found neither role; no target was opened and no identity was
inferred.

## Read the table

PC0 is an MCU signal and package pin 2. RFM95W pin 3 is a separate module pin
number. Connector labels such as TX/RX may describe the host side, not the AVR
USART direction. Gateway PA7 is an A0 address/control signal. Tracker PA7
controls radio power.
