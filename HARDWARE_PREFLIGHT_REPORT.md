# Hardware Preflight Report

## Design evidence

The supplied schematic/BOM describe an AVR128DA28 and an RFM95W footprint on
a shared VCC rail, with no onboard regulator shown and a 3.3 V intended supply.
Radio wiring is SPI1: PC0/MOSI, PC1/MISO, PC2/SCK, PC3/NSS; PD0/RESET,
PD2/DIO0, and PD3/DIO1. H1 pin 1 is VCC, pin 2 GND, and pin 5 UPDI. The
antenna can use SB1-to-SMA or SB2-to-U.FL. These documents establish design
intent, not assembly or live electrical state.

## Live observations

- Passive USB scan [20261106T095821Z](artifacts/rf-proof/20261106T095821Z):
  by-path `usb-0:4:1.0` resolves to `/dev/ttyUSB1`; `usb-0:1:1.0` resolves to
  `/dev/ttyUSB0`. Both adapters identify as CP2102 with serial `0001`.
- The operator reports USB1=Sender and USB0=Receiver. The detector has no
  firmware identity evidence and reports `UNKNOWN`; USB path and adapter
  enumeration do not independently prove board role.
- The passive port-owner check found no process holding either port.
- No physical voltage, continuity, wiring, fitted-module, or antenna
  measurement was collected by this run.
- The fresh detector reports both adapters as `UNKNOWN` because CP2102
  metadata contains no firmware identity. The operator reports USB1=Sender
  and USB0=Receiver; that report is retained separately from detector evidence.
- The operator supplied an `upditerm` transcript containing
  `HEY HELLO WORLD FROM AVR128DA28` twice. The displayed port is truncated, so
  the output cannot be assigned to path :1 or :4. The string is absent from
  current project source and all five current firmware ELF files, so it cannot
  be associated with these builds. It does not identify a firmware role or
  prove an AVR signature/SIB response. It is partial evidence that a VUART
  output stream was observed, not a target-identification result.

## Firmware payload evidence

Receiver `decode_payload` checks the exact 11-byte length and bytes before it
logs DATA. The current build logs sequence-1 payload bytes from the actual
Sender buffer and Receiver buffer, and logs a payload-match marker for every
accepted sequence. The proof parser requires the exact sequence-1 bytes from
both sides and payload-match evidence for sequences 1–20. Host proof exercises
this logic; no hardware payload has been received yet.

## Prior UPDI evidence

The historical investigation
[RCA_FRESH_01](artifacts/updi/fresh/STAR_RCA.md), updated 2026-10-27, records
80 read-only SIB attempts across two adapter paths, with zero target response
bytes. Many attempts echoed the local UPDI bytes but received no target SIB;
the report explicitly says supply values, target pinout, common ground,
power-on state, and waveform were unverified. It did not establish an MCU
identity or a root cause. This is historical evidence, not today's live
hardware state, and it means another SIB attempt should wait for electrical
and UPDI-path inspection.

## Required physical checks

| Check | Current evidence | Result |
|---|---|---|
| Sender/Receiver physical labels and board-to-adapter mapping | Operator-reported tty mapping; pasted VUART path is truncated | NOT VERIFIED |
| MCU VCC on each board | No meter reading | NOT VERIFIED |
| Radio VCC on each board | No meter reading | NOT VERIFIED |
| Common ground | No continuity/connection observation | NOT VERIFIED |
| UPDI wiring to H1 pin 5 | Not inspected | NOT VERIFIED |
| CP2102 VCC and backfeed arrangement | Not inspected | NOT VERIFIED |
| Installed radio full marking | Not observed | NOT VERIFIED |
| Selected SB1/SB2 path and compatible antenna | Not observed | NOT VERIFIED |
| Antenna gain/feed loss and applicable NBTC EIRP/conformity | No documentation supplied | NOT VERIFIED |

The configured `923.0 MHz / 10 dBm / SF7` values are a software candidate.
HOPERF's RFM95W product page lists 868/915 MHz variants; without the fitted
module marking, its compatibility with 923 MHz is unknown. NBTC's non-RFID
920–925 MHz technical standard defines EIRP and spectrum-access requirements,
and its current frequency-use criteria notice is dated 2025-06-25. Conducted
TX power alone does not establish eligibility or conformity: EIRP includes
antenna gain and feed loss. The fitted antenna gain/loss and device conformity
evidence are unknown. See the
[HOPERF product page](https://secure.hoperf.com/modules/lora/RFM95W.html),
[NBTC 920–925 MHz technical standard](https://standard.nbtc.go.th/getattachment/Standards/%E0%B8%A1%E0%B8%B2%E0%B8%95%E0%B8%A3%E0%B8%90%E0%B8%B2%E0%B8%99%E0%B8%97%E0%B8%B2%E0%B8%87%E0%B9%80%E0%B8%97%E0%B8%84%E0%B8%99%E0%B8%B4%E0%B8%84%E0%B8%82%E0%B8%AD%E0%B8%87%E0%B9%80%E0%B8%84%E0%B8%A3%E0%B8%B7%E0%B9%88%E0%B8%AD%E0%B8%87%E0%B9%82%E0%B8%97%E0%B8%A3%E0%B8%84%E0%B8%A1%E0%B8%99%E0%B8%B2%E0%B8%84%E0%B8%A1/1033-2565.pdf.aspx?lang=th-TH),
and [NBTC's 2025 frequency-use criteria](https://www.nbtc.go.th/th/law/announce/688543/688544/701197/688634/).
Host diagnostics use separate `sender_hello_spi` and `receiver_spi` images
that never initialize packet TX; no RF transmission has occurred.

## Safe next step

Target identification was attempted without physical-verification flags and
blocked before any serial port opened:
[20261106T092627Z](artifacts/rf-proof/20261106T092627Z). After the electrical
checks above are physically completed, run:

```bash
uv run python tools/rf_proof.py --stage target-identification \
  --physical-mapping-verified --power-verified
```

The `radio-spi-smoke` stage remains an upload and must wait for confirmed
target identity, power, and UPDI wiring. If the bounded SIB probe still fails,
stop further retries and inspect the UPDI/power waveform path; the historical
80-probe batch had zero SIB responses. RF-enabled upload and transmission also
require the installed module/antenna and applicable RF profile to be verified.
