# Receiver APPCODE

Receiver is the AVR128DA28 on the Tracker board. It validates addressed DATA
frames in software because SX127x LoRa mode does not provide FSK-style address
filtering. Malformed packets, CRC failures, wrong destinations, unexpected
peers, and unrelated campaigns are discarded before application acceptance.

## Source path

- main.cpp delegates setup and loop to the application selected by the build.
- appcode/reliable.cpp owns Tracker startup, payload validation, duplicate
  handling, and SSOT ACK/NACK transmission.
- appcode/arq/receiver.cpp owns the Receiver half of the separate ARQ test.
- shared/protocol/reliable_transport.h contains the shared transaction states.
- stable_lib/ssot owns the packet codec and duplicate-session helpers.

For the SSOT test, the application accepts only the configured 11-byte
hello-world payload. Repeated accepted DATA gets an ACK without a second
application delivery. Invalid addressed payloads receive a correlated NACK.
Wrong-destination or wrong-peer traffic receives no application response.

## Hardware and power

The Tracker uses PC0-PC2 for SPI, PC3 for SD CS, PD0 for radio NSS, PD1 for
radio reset, PD2 for DIO1, PD3 for DIO0/IRQ, and PA7 as the active-low radio
power gate. Startup keeps GNSS and SD power disabled during radio-only tests.
See the [pin audit](../../PIN_MAPPING_AUDIT.md) and
[Tracker SSOT](../../TRACKER_SSOT.md) for connector and peripheral nets.

Build with pio run -e receiver. Radio-only variants are separate environments.
The current checkout detected no Receiver hardware, so no physical packet
exchange was attempted.
