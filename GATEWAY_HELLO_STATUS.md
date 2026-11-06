# Gateway-to-Receiver LoRa Hello World

## Current result

The shared Hello World profile is now an explicit SF7 candidate: 923.0 MHz,
10 dBm, BW125 kHz, CR4/5, sync word `0x12`, preamble 8, CRC on, explicit
header, and normal IQ. `HELLO_RF_PROFILE_VERIFIED` and its startup rejection
were removed. This changes the firmware configuration; it does **not** prove
that the installed modules, antennas, power rails, or regulatory profile are
suitable for transmission.

No UPDI target read, diagnostic upload, physical SPI response, radio
initialization, LoRa DATA/ACK, or RF campaign has run. The candidate is not
cleared for RF because the board supply and fitted radio/antenna remain
unverified.

## Shared profile and protocol

The single source of candidate values is the common `[env]` build profile in
[platformio.ini](platformio.ini); PlatformIO's effective configuration shows
the same values for `sender_hello`, `receiver`, and both diagnostic images.
[hello_config.h](src/shared/hello_config.h) requires those values and checks
SF7/profile constraints at compile time. The shared SX1276 wrapper explicitly
applies bandwidth, coding rate, sync word, preamble, CRC, explicit header, and
IQ settings; it selects SPI1 before RadioLib initialization. A successful
radio init is required before the Sender starts its bounded campaign or the
Receiver enters RX.

The regular `sender` remains I2C-configurable through `CONFIG_LORA` and
`START_LORA`. The standalone `sender_hello` uses the shared candidate and
starts its one-shot campaign after successful radio initialization. DATA
contains the four-byte radio header, type `0x08`, sequence, and the exact
11-byte `hello world` payload. The Receiver validates the payload and sends a
matching ACK. It now logs `PAYLOAD_MATCH` after every successful byte-for-byte
decode, plus the actual sequence-1 ASCII/HEX bytes on both Sender and Receiver.
The proof parser requires those sequence-1 bytes and a receiver payload-match
event for all 20 sequences. The runner sends `C` only after the correlated
sequence-1 DATA/ACK and byte evidence.

`sender_hello_spi` and `receiver_spi` are separate diagnostic builds. They
read/log the radio version but skip RadioLib init and packet TX. Their firmware
logs `RF_TX_DISABLED_DIAGNOSTIC`; they are the only images used by the
`radio-spi-smoke` stage.

## Software verification

- Full Python suite: `uv run python -m unittest discover -s tests -q` — **78
  passed** ([captured output](artifacts/rf-proof/20261106T095802Z/python-unittest.log)).
- Host proof: [20261106T095802Z](artifacts/rf-proof/20261106T095802Z) — 155
  protocol, 77 wrapper, 10 role-log, and 40 proof-runner checks (**282 total**).
- Clean builds: [20261106T095821Z](artifacts/rf-proof/20261106T095821Z) —
  `sender`, `sender_hello`, `receiver`, `sender_hello_spi`, and `receiver_spi`
  built successfully; all HEX images fit APPCODE. RAM/Flash usage and HEX/ELF
  SHA-256 values are in `firmware-measurements.json`.
- Effective PlatformIO config confirms `sender_hello` test mode and distinct
  RF-disabled diagnostic environments. Shared profile validation, upload
  preservation, and stable port mapping checks pass.

## Live USB inventory

The latest passive scan is in
[the 095821Z proof run](artifacts/rf-proof/20261106T095821Z/usb-role-scan.stdout.log):

- by-path `usb-0:4:1.0` resolves to `/dev/ttyUSB1`.
- by-path `usb-0:1:1.0` resolves to `/dev/ttyUSB0`.
- Both are CP2102 adapters with duplicate serial `0001`; neither adapter
  serial nor tty numbering independently proves board role.
- The user reports USB1 as Sender and USB0 as Receiver. The passive firmware
  role detector still reports both as `UNKNOWN`.
- `fuser` found no process holding either port.
- The user supplied an `upditerm` snippet with two
  `HEY HELLO WORLD FROM AVR128DA28` lines, but its port path is truncated and
  the string is absent from current source and all five current firmware ELFs.
  Treat it as user-reported VUART output from an unassociated image; it does
  not establish SIB/MCU identity or Sender/Receiver role.

The latest target-identification attempt is recorded in
[092627Z](artifacts/rf-proof/20261106T092627Z): it blocked before opening
serial because physical mapping and power/UPDI wiring were not verified. No
SIB or fuse-read command was issued.

Separate historical investigation [RCA_FRESH_01](artifacts/updi/fresh/STAR_RCA.md),
last updated 2026-10-27, records 80 read-only SIB attempts and zero target
responses across two adapter paths. Local byte echoes succeeded, but no MCU
identity or fuse values were obtained. The investigation found supply values,
physical pinout, common ground, and target power state unverified; its mapping
and failures are historical and do not establish today's board roles or state.

## Hardware stages

| Stage | Result |
|---|---|
| Host tests and five clean builds | PASS |
| USB topology and occupancy | PASS; roles remain UNKNOWN to the detector |
| Physical board mapping and electrical preflight | NOT VERIFIED |
| Current target identification | BLOCKED before serial open; historical SIB attempts were 0/80 |
| BOOT layout | NOT RUN |
| Physical RegVersion read over SPI1 | NOT RUN |
| Diagnostic upload and radio smoke | NOT RUN |
| RF-enabled upload | NOT RUN |
| Real DATA/ACK and 20-message campaign | NOT RUN |

The user reports USB1 as Sender and USB0 as Receiver; record this as operator
mapping, not independent board-identity evidence. Before opening UPDI, provide
measured MCU VCC and radio VCC for both boards, common-ground and UPDI-to-H1
pin 5 confirmation, and the CP2102 VCC/backfeed arrangement. No pin mapping is
needed. Before RF, also inspect the module's full marking, selected SB1/SB2
antenna path, antenna band/model/gain and feed loss, and applicable NBTC
conformity/EIRP evidence. BOM calls the module RFM95W, but does not prove the
fitted module variant or its compatibility with 923 MHz. See
[HARDWARE_PREFLIGHT_REPORT.md](HARDWARE_PREFLIGHT_REPORT.md).

After physical electrical checks, the next command is:

```bash
uv run python tools/rf_proof.py --stage target-identification \
  --physical-mapping-verified --power-verified
```

Then run the RF-disabled SPI stage with `--authorize-upload`. Actual
RF-enabled upload requires both `--authorize-upload` and
`--authorize-rf-test` because `sender_hello` begins its campaign at boot; the
campaign must not be uploaded or run until the module, antenna, and regulatory
conditions are verified.
