# Pin Mapping Audit — AVR128DA28 / RFM95W

## Evidence basis

The intended board design is the LoRa Board revision dated 2025-04-26:

- Schematic: `../iwing-tracker/gateway-lora/loraboard/pcb/2025-04-26/Schematic_LoRa_Board_rudolph_gw_2025-04-26.pdf`
- BOM: `../iwing-tracker/gateway-lora/loraboard/pcb/2025-04-26/BOM_LoRa_Board_rudolph_gw_2025-04-26.csv`
- Top/bottom layouts and Gerbers are in the same directory. The BOM lists an AVR128DA28-I/SS and an unsuffixed RFM95W module; the schematic symbol says RFM95/98. The 2025-04-26 files in `gateway-lora` match the corresponding `gateway-lora_dev` files by SHA-256. These documents establish design intent only. The assembled boards, module markings, solder bridges, power, and wiring have not been inspected.

## Radio and MCU pins

| Schematic signal | Board net / MCU pin | Current firmware | Result and action |
|---|---|---|---|
| RFM MOSI | PC0 | `SPI.swap(SPI1_SWAP_DEFAULT)` in [lora.cpp](src/lib/lora/lora.cpp:18) | Match. DxCore 1.6.2 maps SPI1 DEFAULT to PC0–PC3 on the 28-pin AVR128DA28 variant. The wrapper selects it before RadioLib initializes. |
| RFM MISO | PC1 | Same SPI1 route | Match. |
| RFM SCK | PC2 | Same SPI1 route | Match. |
| RFM NSS | PC3 | `PIN_LORA_CS PIN_PC3` in [io.h](src/sender/lib/io.h:10) and [receiver/main.cpp](src/receiver/main.cpp:15) | Match. The radio wrapper drives this as GPIO chip select. |
| RFM RESET | PD0 | `PIN_LORA_RST PIN_PD0` in both roles | Match. Both startup paths now set RESET high. |
| RFM DIO0 / IRQ | PD2 | `PIN_LORA_IRQ PIN_PD2`, passed as RadioLib's IRQ argument | Match. PD1/INT is not used for DIO0. |
| RFM DIO1 | PD3 | `PIN_LORA_DIO1 PIN_PD3`, passed as RadioLib's additional GPIO | Match. Sender and Receiver now configure it as input. |
| RFM DIO2 | PD4 | No active firmware macro or callback | Header pass-through only; unused by this firmware. |
| RFM DIO3 | PD5 | No active firmware macro or callback | Header pass-through only; unused by this firmware. |
| RFM DIO4 | PD6 | No active firmware macro or callback | Header pass-through only; unused by this firmware. |
| RFM DIO5 | PD7 | No active firmware macro or callback | Header pass-through only; unused by this firmware. |

The installed RadioLib 7.1.2 default Arduino `Module` uses the global `SPI` instance. The installed DxCore API exposes `bool SPI.swap(uint8_t)` and `SPI1_SWAP_DEFAULT`; its 28-pin variant maps SPI1 DEFAULT to MOSI PC0, MISO PC1, SCK PC2, SS PC3. A previous Receiver call to `SPI.begin()` selected the core's SPI0 default. That premature call was removed; shared radio initialization now chooses SPI1 before RadioLib calls `begin()`.

## H1 connector

| H1 pin | Schematic net | Current firmware / core direction | Result and action |
|---:|---|---|---|
| 1 | VCC | No firmware pin macro | Intended shared 3.3 V rail; actual voltage/source unmeasured. |
| 2 | GND | No firmware pin macro | Common-ground continuity is physically unverified. |
| 3 | TX net / PA1 | `PIN_DEBUG_RX` is now PA1; DxCore USART0 RX is PA1 | The H1 net label is opposite the MCU USART direction. Do not connect a conventional adapter by matching TX-to-TX labels. The bounded role logs use the UPDI virtual UART, not this pin. |
| 4 | RX net / PA0 | `PIN_DEBUG_TX` is now PA0; DxCore USART0 TX is PA0 | Same label-direction difference. Sender's existing `Serial` maps TX to PA0, the H1 net labeled RX. |
| 5 | UPDI | Used by the UPDI programmer and UPDI virtual UART; not a GPIO macro | The user reports Sender on USB1/path 4 and Receiver on USB0/path 1. UPDI connection and target identity remain unverified. |
| 6–10 | NC | No firmware definitions | No action. |

The installed DxCore 1.6.2 28-pin variant defines USART0 TX=PA0 and RX=PA1. `PIN_DEBUG_TX/RX` were corrected to those MCU directions. The local `updi_uart` adapter includes the existing upditerm virtual-UART implementation, which uses OCD messaging over UPDI and does not use PA0/PA1.

## H2 connector and board signals

| H2 pin | Schematic net | Current firmware | Result and action |
|---:|---|---|---|
| 1 | A0 / PA7 | `A0` is PA7 in Sender main and I2C setup | Match. |
| 2 | A1 / PA6 | `A1` is PA6 in Sender main and I2C setup | Match. |
| 3 | INT / PD1 | `PIN_INT` is PD1; Gateway configures it as output for the host interrupt signal | Match; distinct from LoRa DIO0. |
| 4 | SCL / PA3 | DxCore default TWI0 SCL is PA3; Gateway calls `ConfigureTwiRoute()` and `Wire.begin()` | Match; Gateway I2C path is retained. |
| 5 | SDA / PA2 | DxCore default TWI0 SDA is PA2 | Match. |
| 6 | DIO1 / PD3 | `PIN_LORA_DIO1` | Match; used by radio wrapper. |
| 7 | DIO2 / PD4 | No active firmware macro | Pass-through only. |
| 8 | DIO3 / PD5 | No active firmware macro | Pass-through only. |
| 9 | DIO4 / PD6 | No active firmware macro | Pass-through only. |
| 10 | DIO5 / PD7 | No active firmware macro | Pass-through only. |

The schematic also assigns LED1=PA5 and LED2=PA4. Receiver had LED1=PA6 and LED2=PA5; those definitions are corrected. Gateway GPIO setup now explicitly sets DIO1 PD3 to input and RESET PD0 high. `PIN_LORA_EN` is absent; PA7 remains A0.

## RF connector path

The BOM contains solder bridges SB1 and SB2, an SMA footprint, and a U.FL footprint; it does not list an antenna. The schematic routes the ANT node through the selected bridge. The PDFs/Gerbers show the intended layout and selectable paths, but do not prove which bridge is closed or whether a compatible antenna is fitted on either physical board. Inspect the assembled path before RF.

## Verification

Host tests cover the pin maps, startup DIO1/RESET state, USART0 macro directions, SPI1 selection before RadioLib initialization, and read-only register `0x42` access. Latest proof evidence is in [`artifacts/rf-proof/20261106T062403Z`](artifacts/rf-proof/20261106T062403Z). These checks validate source and a host stub; they do not verify physical continuity or radio detection.
