# Final RCA — LoRa ARQ Hardware Recovery

**Run:** 2026-11-14 continuation  
**Repository:** `/home/parinya/university/SENIOR_PROJECT_RCA`  
**Verdict:** `PARTIALLY_ISOLATED` — source defects corrected and software candidates validated; physical DATA/ACK and POR causality remain unverified.

## Executive summary

Historical H01 runs recorded ten Gateway DATA `TX_DONE` events, ten ACK-window timeouts, and zero accepted ACKs. Tracker session 9 changed the saved reset-cause value from `0x20` to `0x01` (PORF), but its reset time and electrical cause were not captured. No Tracker `RX_DONE`, DATA acceptance, or ACK transmission evidence survived. A 120.029947-second RX-only control did not show the same saved PORF transition.

The source contained an SX127x high-band configuration defect: RadioLib preserved the reset-default LF selection, and the 915 MHz RX state was observed as `0x8D`. The code now clears only OpMode bit 3, and the active ARQ/reverse-raw diagnostic profile is 923 MHz at +2 dBm. A separate programmer role-map gap and two host-test-stage defects were fixed test-first. All 15 target environments build and the 302-test suite passes. No candidate was flashed and no RF was transmitted because the adapter power/back-feed arrangement and equipment/EIRP conditions are not established. The HF defect is proven as a configuration mismatch, not proven as the cause of H01 or the POR.

## S — Situation

The Tracker is an AVR128DA28 with an RFM95W, SAM-M10Q GPS, SD socket, IMU, and 24C512 EEPROM. The Gateway has its own AVR128DA28/RFM95 radio board. In the failing H01 direction the Gateway sends DATA and the Tracker must receive it and return ACK.

Incident A remains `PHYSICAL_RF_FAILURE_UNISOLATED`; Incident B remains `HOST_TRANSPORT_ERROR / RF INCONCLUSIVE`. The earlier UPDI STATUS write defect was fixed separately; preserved-firmware live STATUS later passed Tracker 20/20 and Gateway 1/1. These STATUS transactions are not RF evidence.

## T — Task

Keep a minimal Tracker radio-only candidate, correct high-band radio setup, validate programmer bounds and host regressions, and establish a safe path to physical DATA → ACK tests without overwriting protected memory or inventing hardware results.

## A — Action

### Source and configuration changes

- Retained the GPS UART isolation, GPS main-power shutdown, SD power-off policy, card-detect guard, and LoRa-on-through-ACK behavior in the diagnostic build. IMU/EEPROM remain on main 3V3; software inactivity is not claimed to remove their power.
- Changed `config/arq_test.toml` and generated ARQ settings from 915 to 923 MHz; kept +2 dBm and all other ARQ PHY settings. `config/radio_915.toml` remains unchanged.
- Updated reverse-raw initialization to use the generated ARQ radio profile and the same bit-3 HF selection. Both radio roles therefore use the same candidate frequency and profile.
- Fixed the guarded programmer's missing role mapping for radio-only images. RED/GREEN tests verify both radio-only environments resolve to their configured application bounds `(0, 130048)`.
- Fixed the RF-proof host-test stage's removed-source references and missing role compile flag. Both issues were reproduced by tests before the corresponding source changes.

### Research and schematic review

Semtech defines SX127x RegOpMode `0x01` bit 3 as LowFrequencyModeOn; clearing only that bit selects the HF bank while retaining mode bits. RadioLib 7.1.2 `begin()` does not correct the reset-default bank in this path. The 923 MHz FRF value `E6 C0 00` is a calculation from the nominal 32 MHz reference, not a readback. The Tracker schematic shows VBAT → TPS7A0233 → main 3V3 and Q1/Q2/Q3 switched LoRa/GPS/SD rails. It also shows a separate SAM-M10Q V_BCKP supply. The Gateway has a distinct radio/power layout. See [source log](references/SOURCE_LOG.md) and [power topology](POWER_TOPOLOGY.md).

NBTC's online SDoC summary lists LoRa Non-RFID at 920–925 MHz and a 50 mW power category; the 2025 official listing identifies the corresponding technical standard. This supports 923 MHz as a candidate test profile, but does not prove this assembled equipment's conformity, antenna EIRP, or authorization for the proposed lab trial. At nominal +2 dBm conducted output, the 50 mW EIRP ceiling leaves about 14.99 dB net antenna/feed gain before output tolerance. Actual antenna gain and radiated output were not measured. [NBTC SDoC listing](https://standard.nbtc.go.th/%E0%B8%9A%E0%B8%A3%E0%B8%B4%E0%B8%81%E0%B8%B2%E0%B8%A3%E0%B8%AD%E0%B8%AD%E0%B8%99%E0%B9%84%E0%B8%A5%E0%B8%99%E0%B9%8C/SDoC-Online.aspx), [NBTC 2025 technical-standard notice](https://www.nbtc.go.th/law/announce/688543/688545/701196/688752/).

### Software verification

- ARQ profile test: 11 tests passed; its RED run caught the stale 915 MHz setting.
- Reverse-raw test: RED caught hardcoded 915 MHz, then RED caught the uncleared LF bit. GREEN verifies the 923 MHz profile and modeled RX OpMode `0x85`.
- Installed RadioLib 7.1.2 HAL test: 12 modeled TX/RX cycles across two reset-mode models, with 923 MHz FRF `E6C000`.
- RF-proof host stage: role-log, wrapper, and diagnostic-protection compile/tests passed; the full unit suite ran 302 tests, 1 skipped, 0 failures, 0 errors.
- PlatformIO: 15/15 active target environments built. All HEX images pass static application-range and reset-vector checks. The eight ARQ/reverse-raw candidate images at 923 MHz are indexed in [candidate-builds-923.json](candidate-builds-923.json) and [FIRMWARE_BUILD_RESULTS.json](FIRMWARE_BUILD_RESULTS.json).

These are software and modeled-HAL results, not physical RF results.

### Physical inventory and gates

The host currently enumerates two CP2102 devices (`10c4:ea60`) on the configured USB paths, with no process owning either port. Each USB descriptor is bus-powered with `MaxPower 100mA`; this is not a measurement of board-rail current and does not identify the adapter's 3V3 output topology. Unique MCU serials and fuses were previously read through the separate read-only LDS path: both signatures match AVR128DA28, both BODCFG/CODESIZE/BOOTSIZE were `0/0/0`, silicon revision raw was `0x17`, and no NVM write or CPU reset was requested.

The operator reports 3.3 V from the UPDI adapter and installed antennas. The adapter power path, any battery/regulator connection, common ground, back-feed isolation, Tracker SD socket state, RF module/antenna compliance, and antenna gain remain unverified. No oscilloscope, logic analyzer, independent RF receiver, voltage logger, MCU VDD minimum, 3V3-LORA minimum, or current measurement is available in this session. The latest guarded preflight blocked before serial open; see [HARDWARE_PREFLIGHT.json](HARDWARE_PREFLIGHT.json) and `artifacts/rf-proof/20261114T062831Z/preflight.log`.

## R — Result

| Metric | Result |
|---|---:|
| ARQ-focused test run | 11 passed |
| Host full suite | 302 run, 1 skipped, 0 failures, 0 errors |
| Active target environments built | 15/15 |
| Static image ranges/reset vectors | 15/15 safe |
| Preserved-firmware STATUS | Tracker 20/20; Gateway 1/1 |
| Candidate images flashed | 0 |
| New physical RF trials | 0 |
| Historical Gateway DATA TX_DONE | 10 |
| Historical ACK timeouts / accepted ACKs | 10 / 0 |
| Tracker RX_DONE / DATA_ACCEPTED / ACK_TX_DONE in historical H01 evidence | NOT CAPTURED / NOT CAPTURED / NOT CAPTURED |
| NACK hardware trials | 0 |
| New POR during a candidate RF trial | NOT MEASURED; no candidate RF trial ran |
| MCU VDD / 3V3-LORA minimum | NOT MEASURED / NOT MEASURED |

### Confirmed software defects

1. **SX127x high-band bank selection mismatch:** the preserved 915 MHz RX state was observed at `0x8D`, with bit 3 set. Source now clears only bit 3 for the HF profile. The corrected 923 MHz candidates build and pass software/HAL checks. A causal link to H01 or POR is **not established** because no candidate was flashed or compared on hardware.
2. **Radio-only programmer role map omission:** the two radio-only build names previously returned no application bounds. The TDD regression now verifies their correct bounds. This was a tooling defect, not a demonstrated RF cause.
3. **RF-proof host-test stage defects:** it referenced removed Hello test sources and omitted role-derived compile flags for diagnostic tests. TDD regressions reproduce and prevent both faults; the stage now passes. This was not a device failure cause.

## Remaining root-cause questions

- Did Gateway `TX_DONE` correspond to a radiated packet? UNKNOWN; no independent RF capture.
- Did Tracker detect or accept DATA? UNKNOWN; no Tracker `RX_DONE` or accepted-frame record survived.
- Did Tracker transmit ACK, and did Gateway receive/validate it? UNKNOWN; no physical ACK path was captured.
- Did session 9 cause a new MCU POR? A saved PORF transition was observed after the session; exact reset timing and trigger are UNKNOWN.
- Was a rail transient responsible? UNKNOWN; no MCU VDD or 3V3-LORA waveform/current data.
- Did correcting HF mode solve the packet loss? UNKNOWN; no hardware A/B comparison.
- Are POR and ARQ failures related? UNKNOWN; evidence does not distinguish shared from independent causes.

The earliest directly established H01 failure is a missing accepted ACK at the Gateway after its local DATA `TX_DONE`. The remote RF receive, Tracker firmware, ACK generation, reverse RF, and Gateway parser boundaries remain unobserved; no narrower physical boundary can be claimed.

## Final verdict

**ROOT CAUSE 1:** Confirmed source-level HF register-bank configuration defect; contribution to H01 is unproven.  
**ROOT CAUSE 2:** No physical power/RESET cause confirmed. Historical session 9 recorded PORF, but the trigger and timing are unknown.  
**ADDITIONAL ROOT CAUSES:** Programmer role mapping and RF-proof host-test-stage defects were corrected; neither is proven to cause the RF incident.  
**PROGRAMMER STATUS:** Role mapping and all 15 image bounds tested; no image flashed.  
**POWER SUPPLY STATUS:** UNKNOWN; source path/back-feed not verified and rails not measured.  
**RF CONFIGURATION STATUS:** Source candidate is 923 MHz / +2 dBm with HF bit 3 cleared; physical register readback and equipment/EIRP compliance unverified.  
**TRACKER DATA RX STATUS:** UNKNOWN.  
**TRACKER ACK TX STATUS:** UNKNOWN.  
**GATEWAY ACK ACCEPTANCE STATUS:** Historical 0/10 accepted; no new hardware trial.  
**NACK STATUS:** Protocol behavior is host-tested; physical trial not run.  
**POR STATUS:** Historical PORF transition observed after H01 session 9; no candidate-RF reset observation.  
**RELIABILITY RESULT:** No physical reliability sample. The system is **not ready for FOTA or deployment**.

**Final classification: `PARTIALLY_ISOLATED`.** The smallest next physical step is to verify one isolated, adequate 3.3 V supply and ground/back-feed arrangement, confirm the SD socket is empty, and document the applicable 923 MHz equipment/antenna/EIRP condition. Then flash only the verified application images and capture one bounded Gateway DATA → Tracker accepted DATA → Tracker ACK TX → Gateway ACK accepted exchange, with rail/reset evidence.

## Evidence index

- [Power topology](POWER_TOPOLOGY.md)
- [Hardware preflight](HARDWARE_PREFLIGHT.json)
- [Source references](references/SOURCE_LOG.md)
- [HF-mode analysis](HF_MODE_VERIFICATION.md)
- [Programmer verification](PROGRAMMER_VERIFICATION.md)
- [923 MHz candidate images](candidate-builds-923.json)
- [All active target build results](FIRMWARE_BUILD_RESULTS.json)
- [Flash status](FLASH_VERIFICATION.json)
- [Radio register status](RADIO_REGISTER_READBACK.json)
- [DATA/RF status](RF_DATA_RESULTS.json)
- [ACK/NACK status](ACK_NACK_RESULTS.json)
- [Reset results](RESET_RESULTS.json)
- [Power A/B status](POWER_AB_RESULTS.md)
- [Hypothesis matrix](HYPOTHESIS_MATRIX.md)
- [Reliability results](RELIABILITY_RESULTS.md)
- [Regression results](REGRESSION_RESULTS.md)
- [Integrity verification](integrity-verification.json) and [SHA-256 file list](final_hashes.json)
- Historical H01 bundles: `artifacts/arq/20261114T023251Z-h01-reader-free/bundle.json`, `artifacts/arq/20261114T022413Z-h01-reader-free/bundle.json`; RX idle control: `artifacts/arq/20261114T025241Z-rx-idle-control/bundle.json`.
