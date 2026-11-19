# Sender APPCODE

Sender is the AVR128DA28 on the Gateway LoRa daughterboard. The ESP32 carrier
and its host interface are separate hardware components. Port names alone do
not identify which AVR is attached.

## Source path

- main.cpp delegates setup and loop to the application selected by the build.
- appcode/gateway owns the Gateway scheduler, I2C mailbox, serial interface,
  LEDs, and normal Gateway radio transaction.
- appcode/reliable.cpp implements the Sender half of the addressed SSOT
  DATA/ACK/NACK test.
- appcode/arq/sender.cpp owns the Sender-specific ARQ session and radio polling.
- shared/radio/radio_link.cpp is the addressed RadioLib adapter.
- stable_lib/ssot owns the shared frame codec and campaign rules.

The reliable test path requests the configured payload, waits for radio TX
completion, then accepts only an ACK matching the expected peer, campaign, and
sequence. A matching NACK or timeout schedules a bounded retry. It reports
ACK_RX separately from ACK_ACCEPTED.

## Builds and hardware

The default sender environment builds the Gateway application. sender_hello
builds the SSOT reliable test, sender_arq and sender_arq_test build the ARQ
transaction source, and sender_mvp and sender_reverse_raw preserve their
separate legacy test behavior. Radio-only and reverse diagnostic variants are
listed in platformio.ini.

The Gateway radio uses PC0-PC3 for SPI1, with CS on PC3, reset on PD0, DIO0 on
PD2, and DIO1 on PD3. PA7 is the A0 address/control net. It is not a radio
power-enable. Consult the [pin audit](../../PIN_MAPPING_AUDIT.md) and
[Gateway SSOT](../../GATEWAY_SSOT.md) before wiring or interpreting connector
labels.

Build with pio run -e sender. Run the
[ACK/NACK host tests](../../docs/testing/LORA_ACK_NACK.md) before any physical
trial. This checkout has no detected Sender hardware.
