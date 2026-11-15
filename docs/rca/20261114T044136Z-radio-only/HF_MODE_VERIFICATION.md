# SX127x HF-mode verification

## Register rule and candidate

Semtech's SX1276/77/78/79 Rev.5 defines RegOpMode `0x01` bit 3 as LowFrequencyModeOn. The active ARQ profile now uses 923 MHz, which is in the HF band; bit 3 must be clear. This is separate from RegDetectOptimize `0x31` bit 7 AutomaticIFOn. See [SOURCE_LOG.md](references/SOURCE_LOG.md).

The installed RadioLib 7.1.2 `begin()` preserves the reset-default LF selection. Both ARQ and reverse-raw setup now use the generated 923 MHz profile and, after successful `begin()` in standby, call `SPIsetRegValue(..., 0, 3, 3)`. This read-modify-write verifies the field and preserves the mode and unrelated bits. A failed write prevents the radio from being marked ready.

| State | HF candidate expectation when other mode bits match |
|---|---:|
| Standby | 0x81 |
| TX | 0x83 |
| RX Continuous | 0x85 |
| RX Single | 0x86 |

These are decoded state expectations; firmware does not write whole-byte constants. The historical 915 MHz `radio_915.toml` general profile remains unchanged. The ARQ diagnostic profile is 923 MHz, +2 dBm, BW125, SF7, CR4/5, sync 0x12, CRC enabled, explicit header, and normal IQ.

The derived FRF for 923 MHz with a nominal 32 MHz reference is `E6 C0 00`. This is a calculated register value, not a hardware readback.

## Preserved-firmware hardware baseline

[Live summary](live-summary.json) records both preserved radios in standby with snapshot:

`89 E4 C0 00 F0 84 72 74 04 12 27 1D 00 00 00 00 00 00 10 C3`

The register order is `01 06 07 08 09 4D 1D 1E 26 39 33 3B 12 13 10 1B 40 11 18 31`. The standby OpMode `0x89` and FRF `E4 C0 00` are preserved-firmware observations from the 915 MHz setup. Historical RX Continuous was `0x8D`. The diagnostic candidate was not flashed, so its real-radio HF bit and 923 MHz FRF are **UNKNOWN**.

## Software verification

- ARQ and reverse-raw tests verify 923 MHz initialization and clear bit 3; RX Continuous reads `0x85` in the test model.
- [RadioLib 7.1.2 HAL test](tests/radiolib-923-frf-green.txt) computes FRF `E6C000`, checks IRQ/FIFO behavior, and runs 12 modeled TX/RX cycles across two reset-mode models. This is an electrical-HAL simulation, not RF evidence.
- Eight ARQ/reverse-raw candidate images build with safe static application ranges; see [candidate-builds-923.json](candidate-builds-923.json).
- No candidate image was flashed; physical HF/FRF readback remains **UNVERIFIED**.

The source configuration mismatch is established. Its causal contribution to the historical packet failure or POR remains unproven without a controlled hardware comparison.
