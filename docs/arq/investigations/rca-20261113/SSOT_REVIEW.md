# SSOT review — Tracker, Gateway and reverse-raw role mapping

Review date: 2026-11-14. Scope: read-only comparison of the hardware SSOT,
current device mapping, generated manifests, compiled board-selector source and
archived reverse-raw programming evidence.

## Finding

**OBSERVED: the static board maps are internally consistent.** The Tracker and
Gateway use different radio pins. The reverse-raw test intentionally reverses
functional TX/RX duties while selecting each image's actual board pin map. No
SSOT pin-map swap is indicated by these files as the cause of Incident A.
Physical continuity, signal amplitude and radio behavior remain unmeasured.

## Board-level SSOT versus firmware roles

| Physical board | SSOT hardware identity | RFM95W NSS / RESET / DIO0 / DIO1 | Radio power |
| --- | --- | --- | --- |
| Tracker | current_hardware receiver; serial 42032240221092150158013400000000; USB location usb-0:1:1.0 | PD0 / PD1 / PD3 / PD2 | PA7 controls Q1; LOW=ON |
| Rudolph Gateway daughterboard | current_hardware gateway; serial 42032240221023150129012600000000; USB location usb-0:4:1.0 | PC3 / PD0 / PD2 / PD3 | No per-daughterboard PA7 radio power switch; PA7 is address strap A0 |

Both boards share SPI signals PC0/PC1/PC2, but their chip-select, reset and IRQ
pins differ. The authoritative board documents are
[Tracker SSOT](../../../ssot/TRACKER_SSOT.md) and
[Gateway SSOT](../../../ssot/GATEWAY_SSOT.md). They describe schematic
design intent and explicitly leave physical assembly/electrical confirmation
open.

generated/arq_manifest.json, src/arq/board_ssot.c,
include/generated/board_ssot.h, and the PlatformIO role generator agree with
these pin maps. The active Tracker role is receiver; the Gateway role is
sender. The read-only static comparison passed for both boards.

## Reverse-raw image assignment

In tools/arq_trial.py, reverse_raw() programs sender_reverse_raw to the
Gateway port and receiver_reverse_raw to the Tracker port. The platform
generator maps those environment names to the corresponding sender/receiver
board SSOT. src/reverse_raw/main.cpp makes the LORA_ROLE_RECEIVER image
transmit Hello World and the other role receive. Thus the reversed raw
experiment uses:

    Tracker physical board + receiver board pins + reverse-raw TX function
    Rudolph physical board + sender board pins + reverse-raw RX function

This is intentional role reversal with board-specific pins preserved; the
functional role name alone should not be mistaken for a physical-board map.
The Incident A programmer command records the Tracker image on the receiver
USB path and the Rudolph image on the gateway path. Its terminal events report
the expected reverse direction: receiver-role RAW_TX_DONE, then sender-role
RAW_RX_TIMEOUT. That establishes the software's intended assignment; it does
not establish RF emission or physical pin continuity.

The separate historical lora_manifest radio profile specifies +10 dBm for
legacy/MVP environments. The ARQ test profile config/arq_test.toml and
generated/arq_manifest.json specify +2 dBm. These are distinct generated
profiles, not a single generated-value mismatch. Reverse-raw source explicitly
uses the ARQ profile's +2 dBm. Both
uv run python tools/config/generate_lora_config.py --check and
uv run python tools/config/validate_lora_ssot.py config/lora_system.json
passed during this review. The validator itself warns that physical suitability
remains unverified.

## 3.3 V, H1 and UPDI interpretation

The operator reports confidence that 3.3 V is present on the UPDI/LoRa-board
path. The SSOT distinguishes several electrical nets:

- Tracker 3V3 is the MCU base rail.
- Tracker 3V3-LORA is behind Q1 and controlled by active-low PA7.
- H1 power, common ground, external switcher selections and the actual UPDI
  signal path are operator-reported but marked physically unverified in the
  SSOT.
- Rudolph's 3V3-LORA is on the shared Gateway Main Board supply; it does not
  use Tracker's PA7 radio-enable circuit.

The live Gate 1 capture confirms the UPDI link could read the AVR128DA28
signature and unique serial and complete many subsequent UPDI exchanges. It
does **not** measure a 3.3 V rail, UPDI signal-high level, voltage sag, radio
rail settling, or ground integrity. Therefore the operator's 3.3 V confidence
remains an uninstrumented report, not an electrical measurement.

Tracker firmware calls board_ssot_init(); delay(10), enabling PA7 low before
the RadioLib reset/SPI initialization. This matches the SSOT's required order;
the code delay does not prove the Q1 rail physically reached a stable voltage.
The SSOT acceptance checklist still calls for measuring MCU VDD and 3V3-LORA.

## Gate 1 boundary

The active Tracker signature and serial matched the current hardware
configuration. The Host wrote the seven STATUS newline bytes through the UPDI
mailbox, and the low-level UPDI exchanges had no transport exceptions before
the deadline. No application status output arrived. This leaves command
consumption, firmware build identity and the Monitor-to-firmware event path
unresolved. It does not identify a power or RF cause.

## Decision

**Static SSOT verdict: PASS for internal role/pin consistency.**

**Physical SSOT verdict: INCOMPLETE.** Antenna/feed path, H1 voltage selection,
3V3/3V3-LORA waveforms, UPDI signal level and PCB continuity remain unknown.
The SSOT comparison rejects a simple Tracker-versus-Gateway pin-map swap as an
explanation for the recorded reverse-raw failure, but does not reject a
physical connection fault or a separate power problem.
