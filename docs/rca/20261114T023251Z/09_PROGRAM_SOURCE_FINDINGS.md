# Program source finding — SX127x high-band mode

## Verdict

**CONFIRMED source configuration defect:** the ARQ firmware configures 915 MHz but leaves SX127x `RegOpMode.LowFrequencyModeOn` (register `0x01`, bit 3) at its reset default of `1`. The captured armed Tracker register snapshot is `0x8D`, which decodes as LoRa + LF-bank select + RX Continuous. Semtech documents reset default `1` and defines `0` as HF mode; the 915 MHz profile is HF. The previous software therefore selected the wrong band-specific register bank.

**NOT CONFIRMED as the sole cause of the observed packet failures:** this source defect can impair radio operation, but no physical A/B run has shown that correcting the bit restores DATA/ACK. It cannot itself explain the MCU POR. The candidate source change below is not flashed on either board.

## Evidence

### Observed runtime state

- H01 session 9, Tracker `armed-status` output, decodes the register snapshot as `RegOpMode=0x8D`; source bundle: [bundle.json](../../../artifacts/arq/20261114T023251Z-h01-reader-free/bundle.json), field `tracker_output.armed-status.output_hex`.
- The same bundle records Gateway in RX Continuous with `RegOpMode=0x8D` after each DATA TX. The two endpoints therefore shared the same wrong band-selection bit during this H01 run.
- The Tracker’s pre-ARM standby snapshot is `0x89`; after ARM/RX Continuous it is `0x8D`. The mode transition changes bits 2:0 while bit 3 stays set.

### Source path

- Project profile: `ARQ_FREQUENCY_HZ=915000000` in [arq_config.h](/home/parinya/university/SENIOR_PROJECT_RCA/include/generated/arq_config.h:14).
- Firmware calls `radio.begin(...)` in [main.cpp](/home/parinya/university/SENIOR_PROJECT_RCA/src/arq/main.cpp:199), then previously proceeded to power/modem setup without selecting HF mode.
- Installed RadioLib is 7.1.2. Its `setMode()` writes only `RegOpMode[2:0]` (`SX127x.cpp:1715`); `setActiveModem()` writes bit 7 (`SX127x.cpp:1727`); `setFrequencyRaw()` writes `RegFrf` (`SX127x.cpp:1193-1209`). Its common `config()` only disables frequency hopping (`SX127x.cpp:1622-1625`). These paths do not set bit 3.
- The installed source’s `startReceive()` changes mode to RX Continuous and clears IRQs; it does not select the HF bank (`SX127x.cpp:388-435`).
- Semtech SX1276/77/78/79 datasheet Rev. 5, Aug. 2016, Section 6.1 / 6.4, printed pp. 106 and 108: bit 3 resets to `1`; `0` selects HF and `1` LF. Section 6.3 describes the band-specific register bank. [Manufacturer datasheet](https://www.mouser.com/datasheet/2/761/sx1276-1278113.pdf), [Semtech product page and document listing](https://www.semtech.com/products/wireless-rf/lora-connect/sx1276).

`LowFrequencyModeOn` is **not** `AutomaticIFOn`: the latter is bit 7 of `RegDetectOptimize` (`0x31`). They are separate fields in separate registers.

## Test-first correction

The public test seam is the radio register state after the firmware accepts `ARM` and enters continuous RX. For this fixed 915 MHz profile, the independent expected value is `0x85` (LoRa bit 7, RX Continuous bits 2:0, HF bit 3 clear).

1. Added the assertion to `tests/arq/adapter_test.cpp` before changing firmware.
2. Ran `uv run python -m unittest tests.test_arq.ArqTests.test_adapter`: **RED**. The sender-role adapter failed at `raw_regs[1] == 0x85`; the stub showed the prior `0x8D` behavior.
3. Added a single `SPIsetRegValue(RegOpMode, 0, 3, 3)` after successful `radio.begin()` in [main.cpp](/home/parinya/university/SENIOR_PROJECT_RCA/src/arq/main.cpp:201). It runs only after radio initialization succeeds and before later `standby()`/RX/TX operations.
4. Updated the RadioLib test stub to model its observed reset-default behavior and preserve upper register bits when changing the operating mode.
5. Re-ran the same test: **GREEN**.

## Verification in this continuation

- Focused ARQ, H01, capture, and Gate 1 regression command: `uv run python -m unittest tests.test_arq tests.test_arq_reader_free tests.test_arq_capture tests.test_gate1_rca` — **82 tests passed**.
- PlatformIO builds: all six relevant environments (`sender_arq`, `receiver_arq`, `sender_arq_test`, `receiver_arq_test`, `sender_reverse_raw`, `receiver_reverse_raw`) — **6/6 succeeded**, with RadioLib 7.1.2.
- Candidate image hashes are recorded in [candidate_builds.json](candidate_builds.json).
- Full unit discovery: **285 run, 2 skipped, 7 errors**. The errors are compiler-backed tests that cannot launch because `g++` is unavailable; the captured output is [full-suite-source-followup.txt](tests/full-suite-source-followup.txt). The focused 82-test set passes.
- No image was flashed, no radio transmission was run, and no fuse/EEPROM operation occurred in this continuation. The patch is a source/build candidate only.

## What this establishes and does not establish

- **Established:** the original program’s 915 MHz runtime register configuration violated the SX127x band-selection requirement; the source and host register test now select `0x85` in RX Continuous.
- **Not established:** that this bit caused H01’s missing ACK, historical Tracker-to-Gateway failure, or POR. Both H01 radios had bit 3 set, so the experiment did not isolate one endpoint. Gateway `TX_DONE` is not independent evidence of radiation. Tracker RX_DONE, DATA acceptance, and ACK TX were not captured.
- **Reset boundary:** the existing evidence still records PORF during the H01 interval. `src/arq/main.cpp` reads the DxCore-saved flags and contains no application call to software reset; the mode-bit correction does not explain a POR. Voltage, exact reset timing, and reset trigger remain unknown.

## Smallest causal experiment

With baseline images and hashes preserved, run the same bounded H01 protocol with only the Tracker’s HF/LF bit correction changed. Capture Tracker `RX_DONE`, CRC result, DATA acceptance, ACK TX start/TX_DONE, Gateway ACK acceptance, and the post-window reset flags. A corrected receiver that begins receiving/ACKing while the baseline does not supports this mode-bit cause for the link failure; identical failures reject it as a sufficient fix. A synchronized MCU VDD and `3V3-LORA` capture is still required to explain the POR.
