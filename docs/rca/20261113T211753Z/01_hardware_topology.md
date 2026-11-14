# Hardware topology

## Runtime roles

| Physical board | Host port | MCU identity | Normal ARQ role | Reverse-raw role | Radio function in reverse raw |
|---|---|---|---|---|---|
| Tracker | port1, CP210x, `/dev/ttyUSB1` | AVR128DA28, `1e970a`, serial `42032240221092150158013400000000` | Receiver | `receiver_reverse_raw` image | **TX** |
| Rudolph/Gateway | port4, CP210x, `/dev/ttyUSB0` | AVR128DA28, `1e970a`, serial `42032240221023150129012600000000` | Sender | `sender_reverse_raw` image | **RX** |

**FACT:** These identities and image roles are supported by the pre-write and post-write programmer snapshots, expected firmware hashes, and build IDs in raw-run provenance. Port mapping agrees with [`tools/rf_proof.py`](../../../tools/rf_proof.py) and hardware SSOT.

## Board pin maps

| Function | Tracker | Rudolph/Gateway |
|---|---|---|
| SPI MOSI/MISO/SCLK | PC0 / PC1 / PC2 | PC0 / PC1 / PC2 |
| Radio NSS | PD0 | PC3 |
| Radio RESET | PD1 | PD0 |
| Radio DIO0 | PD3 | PD2 |
| Radio DIO1 | PD2 | PD3 |
| PA7 | Active-low radio power enable | Address strap A0 |

**FACT:** Static maps agree across the generated SSOT and firmware. The source-level pin-swap hypothesis is rejected. **UNKNOWN:** Physical continuity, logic levels, antenna continuity, and the live PA7/3V3-LORA waveform were not measured.

## Power tree

**FACT:** Tracker PA7 controls the switched `3V3-LORA` radio supply and is active-low; Gateway PA7 is an address strap and is not a radio-power switch.

**UNKNOWN:** The voltage at Tracker MCU VDD, radio VCC, or USB/adapter supply during SEND. The operator’s 3.3 V confidence establishes nominal design intent only.

## Image identity

- Normal restored Tracker firmware SHA-256: `e80d918bfb5174052cbda07287d7b77574492ee0a0158cf9b06520844e29d50a`.
- Normal restored Gateway firmware SHA-256: `e292a45790a68d588ee97864e309aa16e2510d704ed7c8b4bf1c2baa3912ad52`.
- Reader-free test Tracker image: `receiver_reverse_raw`, build ID `55ed3ca7c0cfb37ec1437c2c6d9d4bedef9c065b1ca20a11c030d247254bba3a`.
- Reader-free test Gateway image: `sender_reverse_raw`, build ID `74fb16455c8076c0c57866591adce79b44dac014d80045aede74d603422d65ea`.

See [raw image and readback evidence](../../../artifacts/arq/20261113T211753Z-reverse-raw/).
