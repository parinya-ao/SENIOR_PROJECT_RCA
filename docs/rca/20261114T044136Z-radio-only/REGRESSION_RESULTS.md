# Regression Results — Current Continuation

| Layer | Result | Evidence |
|---|---|---|
| ARQ profile TDD test | **11 passed**; confirms 923 MHz, 2 dBm, generated manifest | [ARQ green](tests/arq-923-green.txt); expected RED at 915 in [ARQ red](tests/arq-923-red.txt) |
| Reverse-raw profile/HF test | **1 passed**; 923 MHz and OpMode bit 3 clear, RX Continuous mode 0x85 | [HF green](tests/reverse-raw-hf-green.txt); prior 915 and LF-bank failures in the paired red logs |
| Installed RadioLib 7.1.2 HAL test | **1 test passed**, 12 modeled TX/RX cycles; FRF `E6C000` | [923 MHz HAL green](tests/radiolib-923-frf-green.txt); simulation only |
| RF-proof host test stage | **PASS**; role-log, wrapper, diagnostic-protection compile/tests and full unit suite | [Final stage log](tests/host-tests-final2.log), [measurements](../../../artifacts/rf-proof/20261114T075519Z/host-measurements.json) |
| Full Python suite | **302 run, 1 skipped, 0 failures, 0 errors** | Captured by the host stage above; GCC 16.2.1 from the repository toolchain |
| PlatformIO target builds | **15/15 passed**; all static application ranges and reset vectors safe | [Build results](FIRMWARE_BUILD_RESULTS.json); eight 923 MHz candidates in [candidate manifest](candidate-builds-923.json) |
| Preserved-firmware live non-RF diagnostics | Tracker STATUS **20/20**, Gateway **1/1** | [Tracker JSONL](raw/receiver/status-transactions.jsonl), [Gateway JSONL](raw/gateway/status-transactions.jsonl); these were not candidate images |
| Candidate flash / physical RF | **NOT RUN**; 0 images flashed, 0 RF transmissions | [Flash verification](FLASH_VERIFICATION.json), [hardware preflight](HARDWARE_PREFLIGHT.json) |

## Test-first fixes

- ARQ profile: RED showed the loaded test profile still at 915 MHz; GREEN follows the 923 MHz generated profile while keeping the 2 dBm PHY settings.
- Reverse-raw path: RED showed a hardcoded 915 MHz carrier and LF-bank bit; GREEN uses the generated ARQ profile and clears only OpMode bit 3. The test asserts actual modeled receive mode `0x85`.
- Programmer mapping: the previous RED/GREEN evidence shows both radio-only role names resolve to `(0, 130048)` application bounds. No programming occurred.
- RF-proof host test stage: tests reproduced absent Hello-protocol source paths and a missing role compile flag. The stage now compiles only present sources and passes its host suite.

See [each RED/GREEN record](tests/) for the exact test output. The RF-related tests use a modeled HAL and do not establish radiated RF reception.

## Historical run results

The earlier 84 focused tests, 10-image builds and 301-test full-suite result are preserved in the prior logs. They are superseded for the current source state by the 302-test and 15-target results above. Historical incidents and their bundles remain unchanged.
