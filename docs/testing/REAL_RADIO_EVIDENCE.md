# Real-Radio Evidence

Status: **AWAITING_EXACT_APP_WRITE_AUTHORIZATION**. Both target MCUs are attached and identified. No firmware write or LoRa transmission has been performed in this iteration.

## Board identity and current installation

He confirmed safe supply, common ground, UPDI wiring without CP2102 backfeed, compatible antennas/modules, and the 915 MHz RF path.

| Role | Port mapping | AVR serial | SIB/signature | Firmware identity |
|---|---|---|---|---|
| Tracker / Receiver | `/dev/ttyUSB0`, `/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0` | `42032240221092150158013400000000` | AVR128DA28 / `1e970a` | Not recognized by the virtual-UART identity probe |
| Gateway / Sender | `/dev/ttyUSB1`, `/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0` | `42032240221023150129012600000000` | AVR128DA28 / `1e970a` | `sender_hello@Nov 16 2026T11:32:10`; does not match the current image |

Latest fresh target readback is in `artifacts/rf-proof/20261117T075150Z/`. Both SIBs report `AVR P:2D:1-3M2 (A7.KV001.0)`; BOOTSIZE, CODESIZE, and BODCFG all read `00`. The target-identification stage exited 0 and performed no writes. The latest project-venv firmware-identity probe remained `PARTIAL`: Gateway is the older `sender_hello@Nov 16 2026T11:32:10` build, and Tracker firmware identity is unavailable. A first firmware-probe invocation under system Python stopped before probing because PySerial was missing; no LoRa transmission has been made.

## Current application images

These are the exact images built and checked after the final source change. The declared application range is `[0x00000,0x1FC00)`; each proposed erase range is the minimal 512-byte page span containing that image.

| Role | Environment and image | Build ID | SHA-256 | Image bytes | Proposed app-only page range |
|---|---|---|---|---|---|
| Gateway | `sender_hello`, `.pio/build/sender_hello/firmware.hex` | `f7337f9095d17a9c64f3bea35ac0127ed3a96fbc7fed6c72da342508bc275517` | `7abfedfe5696a9dfd0560fec9ab4257c87d1958f1da6136bc95df496dabc6a89` | `[0x00000,0x08E10)` | `[0x00000,0x09000)` |
| Tracker | `receiver`, `.pio/build/receiver/firmware.hex` | `98e9bd2adc545be3373063fafe98eed6e50f2cdd08082b2b4f51028b6e9b404e` | `6d435654635b8bbb803f73626aa390924c3dbab2e0f263f0283e9433081fc692` | `[0x00000,0x08B1C)` | `[0x00000,0x08C00)` |

Both ranges are well inside the declared application bound. The shared writer now refuses all application writes without an exact MCU serial, image SHA-256, and page range. The combined upload stage validates both images before opening a serial port; the SPI-smoke stage requires separate approvals for its two diagnostic images. Both pass the exact approvals to the writer for a second check. It uses AVRDUDE 8.1 with `-D` and an explicit `erase flash start size`, writes and verifies only those pages, then checks full before/after snapshots to prove all other flash and protected data were preserved. It skips a write if exact page readback already matches.

## Software verification

- Full host suite: **429 passed, 1 skipped**. The skip is the archived BOOTSIZE=44 repair case, inapplicable to the current Receiver geometry.
- PlatformIO: **19/19 role-bearing environments passed**, zero compiler warnings. Largest Flash image: 39,012 bytes (`receiver_arq_radio_only`); largest static RAM: 7,049 bytes (`sender`). Current Gateway image: 36,368 B Flash / 3,939 B RAM. Current Tracker image: 35,612 B / 3,772 B.
- `clang-format --dry-run --Werror` passed on production `src/` sources and affected C++ tests. Ruff reported no findings on changed Python lines.
- Reference checkout `/home/parinya/university/iwing-tracker` remains unchanged.

## Physical RF acceptance

| Acceptance item | Result |
|---|---|
| Pre-migration physical baseline | NOT_CAPTURED; the boards were unavailable when behavior changes began |
| Current radio registers and matching PHY on both boards | NOT_RUN |
| Intended DATA/ACK trials | NOT_RUN, target 10/10 |
| Wrong-destination trials, deliveries, ACKs | NOT_RUN, target 10/10 with zero deliveries and zero ACKs |
| Both-side DATA/ACK logs, elapsed time, retries, RSSI/SNR | NOT_RUN; no RF measurements or packet results inferred |

Next: after explicit approval for the two exact app-only writes above, use the verified application writer, confirm readback, then run the controlled DATA/ACK and wrong-destination trials. Firmware identity, SPI register, packet, ACK, and RX re-arm evidence must come from both boards before `PHYSICAL_RF` can pass.
