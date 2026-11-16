# Implementation summary

## Implemented

- Moved the active ARQ test profile to 923 MHz at the existing +2 dBm, preserving the other PHY fields. The separate 915 MHz general-radio profile is unchanged.
- The ARQ adapter and reverse-raw test path clear only SX127x OpMode bit 3 after successful RadioLib 7.1.2 initialization, preserving mode/unrelated bits and propagating register-write errors.
- Added the opt-in `ARQ_RADIO_ONLY_DIAGNOSTIC` configuration and Gateway/Tracker build environments. It leaves the existing ARQ protocol and production environments intact.
- Tracker diagnostic startup disables USART2, releases GPS UART and TIMEPULSE lines before commanding SAM-M10Q main power off, commands SD power off, and keeps LoRa active through responses.
- Tracker diagnostic startup fails closed before radio SPI if its SD card-detect input reports an inserted card on the unisolated shared SPI bus.
- Updated generated board initialization to retain a pull-up for the card-detect switch only in diagnostic builds.
- Added adapter tests against the actual generated GPIO setup and expanded the installed RadioLib HAL test through RX/TX/retry/reinitialization.
- Fixed the RF-proof host-test stage's obsolete references to removed Hello protocol source files and supplied its role-specific compile flags to the diagnostic build.

Comments and evidence explain that GPS V_BCKP and main-rail IMU/EEPROM remain powered. GPIO levels are commands/readbacks, not measured rail voltages.

## Verification

- ARQ configuration regression: **11 passed**; radio-only programmer mapping RED/GREEN preserved.
- Active firmware PlatformIO targets: **15/15 built**. The eight ARQ/reverse-raw candidates use 923 MHz; all HEX files pass static application bounds and reset-vector checks.
- Full host suite through the repaired RF-proof stage with project-bundled GCC 16.2.1 on PATH: **302 run, 1 skipped, 0 failures, 0 errors**. Role-log, RadioLib wrapper, diagnostic-protection compile/tests all passed.
- Installed RadioLib 7.1.2 HAL simulation verified 923 MHz FRF `E6C000` and HF transitions for 12 modeled TX/RX cycles.
- Live non-RF control: Tracker STATUS **20/20**, Gateway **1/1**. Both retained images reported their archived identities.
- Candidate images flashed: **0**. New RF sessions: **0**. No fuse, BOOT or EEPROM writes.

The uploader-map omission for the new radio-only environment names is fixed: a RED regression showed missing application bounds and GREEN confirms Gateway/Tracker bounds `(0, 130048)`. The host-test stage's stale source and missing role flags were also reproduced and fixed test-first. No write was issued; existing identity, safety, layout and application-page preservation checks remain in force.

See the [English final RCA](FINAL_RCA.md), [power topology](POWER_TOPOLOGY.md), [physical preflight](HARDWARE_PREFLIGHT.json), [923 MHz candidate builds](candidate-builds-923.json), [all target builds](FIRMWARE_BUILD_RESULTS.json), [full regression detail](REGRESSION_RESULTS.md), [integrity record](integrity-verification.json) and [source log](references/SOURCE_LOG.md).

## Remaining physical work

The historical Tracker POR mechanism and RF DATA/ACK boundary remain unproven. The 923 MHz source configuration and images are not physical validation. No candidate was flashed or RF transmitted. Supply/back-feed wiring, SD socket state, module/antenna EIRP and applicable equipment/trial conditions remain unverified; no receiver or matching ACK was observed on hardware.
