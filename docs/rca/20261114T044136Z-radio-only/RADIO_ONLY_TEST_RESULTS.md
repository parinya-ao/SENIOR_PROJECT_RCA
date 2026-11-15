# Test-first and physical validation results

> Continuation update: the active ARQ/reverse-raw diagnostic profile is now 923 MHz at 2 dBm. Current test/build counts and physical limitations are in [REGRESSION_RESULTS.md](REGRESSION_RESULTS.md) and [FINAL_RCA.md](FINAL_RCA.md). The initial counts below describe the earlier 915 MHz source stage and remain as history.

## RED → GREEN

1. Added a setup/loop test for the explicit diagnostic flag, GPS electrical intent and an occupied SD socket. [RED](tests/peripheral-red.txt): Receiver failed because USART2 was not disabled. Added the startup-only policy; [initial GREEN](tests/peripheral-green.txt): 12 tests passed.
2. Added TX-state HF assertions. [RED](tests/hf-transitions-red.txt): the radio model never entered TX mode. Corrected that electrical-boundary model to follow the installed driver; no production TX logic was changed for this model defect.
3. Replaced the fake board initializer in adapter tests with the actual generated implementation. [RED](tests/generated-board-red.txt): generated setup removed the diagnostic SD-detect pull-up. Corrected the generator under the diagnostic flag and regenerated its output.
4. [Final focused GREEN](tests/focused-green.txt): **83 tests passed**, including normal/diagnostic roles, occupied-card refusal, protocol core, capture, reader-free diagnostics and Gate 1 tests.

These are simulations at explicit firmware/Host boundaries. GPIO models verify software intent and order, not actual unpowered pin voltages.

## Commands actually executed

```bash
uv run python -m unittest tests.test_arq_radio_only
uv run python -m unittest tests.test_arq.ArqTests.test_adapter
uv run python tools/config/generate_lora_config.py
uv run python -m unittest tests.test_arq tests.test_arq_radio_only tests.test_arq_reader_free tests.test_arq_capture tests.test_gate1_rca
pio run -e sender_arq -e receiver_arq -e sender_arq_test -e receiver_arq_test -e sender_reverse_raw -e receiver_reverse_raw -e sender_arq_radio_only -e receiver_arq_radio_only
uv run python -m unittest discover -s tests
uv run python tools/config/generate_lora_config.py --check
uv run python tools/config/validate_lora_ssot.py
uv run python docs/rca/20261114T044136Z-radio-only/experiments/non_rf_status.py
git diff --check
graphify update .
```

RTK wrapped shell execution. Full stdout/stderr were redirected to the linked logs. The HAL test's exact Clang compilation command is preserved in [its log](tests/real-radiolib-hal.txt).

## Software results

| Check | Actual result |
|---|---|
| Focused tests | 84 passed, 0 failed |
| PlatformIO | 10/10 relevant environments succeeded, including sender_hello and receiver for uploader preflight; [ARQ/raw log](tests/builds.txt), [additional builds](tests/rf-proof-preflight-builds.txt) |
| Installed RadioLib 7.1.2 HAL | 2 reset models, 12 candidate TX/RX cycles passed; modeled bus |
| Full unittest, default PATH | 286 tests run, 2 skipped, 7 errors because host `g++` was not on PATH; [log](tests/full-suite.txt) |
| Full unittest, bundled GCC | **301 tests run, 1 skipped, 0 failures, 0 errors**; [log](tests/full-suite-project-gcc-final.txt) |
| Compiler used | Existing project-bundled GCC **16.2.1**, exposed temporarily through a `.venv/bin/g++` wrapper and removed after the run; no toolchain package changed |
| RadioLib HAL Clang fallback | Earlier Clang result remains separately recorded; the full-suite pass used bundled GNU GCC |
| SSOT generation and validation | Passed; physical suitability remains unverified |
| Diff whitespace | Passed |
| Graph update | Completed; extractor warned about partial parsing of the radio test stub |

Existing protocol core tests already cover valid ACK, wrong session/sequence, retry exhaustion, duplicates, application-rejection NACK, BUSY, missing/late controls and wraparound. Existing capture tests retain UNKNOWN for absent RX and reset evidence and verify no-reset reconnect and reader detach. No duplicate wire format or parallel protocol implementation was added.

## Live non-RF experiment E01

Purpose: verify that both configured MCUs still respond using preserved firmware and establish actual peripheral/register intent. Independent variables: STATUS requests only. No ARM, SEND, RX command, programming, reset or power-cycle was issued.

The one-run [acquisition script](experiments/non_rf_status.py) composes existing tested `Gate1Audit`, transport instrumentation, Monitor, strict STATUS parser and cleanup. It verifies stable USB path, exclusive ownership, signature, unique serial and archived firmware identity. It stops on the first error and retains raw bytes. It does not call the historical top-level runner, whose preservation/identity assumptions predate this continuation.

| Device | Requested STATUS | Passed | Failed | Min / median / max |
|---|---:|---:|---:|---|
| Tracker, USB path port 1 | 20 | 20 | 0 | 7511.414 / 7645.854 / 7742.888 ms |
| Gateway, USB path port 4 | 1 | 1 | 0 | 7778.657 ms; one sample |

Tracker's STATUS phase lasted **152.886140 s**, using the existing recorder's **180 s** total budget. This is not a claim of passing the earlier, separate 120 s Gate 1 deadline. Identity and startup preceded the phase. Both sessions used exactly 2 startup BREAKs and requested 0 CPU resets/resumes. Both Monitor threads closed. Total raw transport records: **111,203**. [Machine summary](live-summary.json).

Both live snapshots show baseline standby **0x89**, FRF **E4C000**, PA **F0/84**, and matching modem/IQ/sync fields. No candidate firmware was flashed. Firmware embedded identities match the archived normal standby restore; a fresh full-Flash SHA-256 readback was not performed.

## 923 MHz continuation

- The ARQ settings test first failed because `load_arq()` still returned 915 MHz; after updating the test profile and generated output, **11 ARQ tests passed**. The general 915 MHz profile was left unchanged.
- The reverse-raw test first failed at the old hardcoded 915 MHz and then at the uncleared LF-bank bit. It now takes frequency/PHY values from the ARQ profile, clears only OpMode bit 3, and verifies RX Continuous `0x85` in the model.
- The installed RadioLib 7.1.2 HAL test was aligned to 923 MHz and reports derived FRF `E6C000`; it remains a bus simulation.
- Two stale host-test-stage defects were fixed test-first: removed source paths and missing role flags. The actual host stage now passes with **302 tests run, 1 skipped, 0 failures, 0 errors**.
- All **15** target PlatformIO environments build. Eight ARQ and reverse-raw images use the 923 MHz ARQ profile and fit their static application bounds. Candidate images are not flashed.
- Physical RF sessions remain **NOT RUN**. No Gateway DATA reception, Tracker ACK transmission/acceptance, new POR result, voltage/current measurement or antenna EIRP measurement is claimed.

Tracker saved cause remained **0x01 → 0x01**, RSTFR **0 → 0**. Gateway remained **0x20 → 0x20**, RSTFR **0 → 0**. Sampled Tracker uptime increased throughout the 20 responses. No new reset indicator was captured. An unchanged saved POR bit alone cannot exclude another POR.

## Physical RF and power matrix

| Condition | Status | Reason |
|---|---|---|
| A: original H01 | Historical only | 2 prior sessions, 10 local DATA TxDone, 10 ACK timeouts, 0 accepted ACKs |
| B: HF only | NOT EXECUTED | Physical RF path and safe source arrangement unverified; baseline image/hash must be preserved |
| C: peripheral only | NOT EXECUTED | Baseline already commands GPS/SD off; a load-removal claim would be confounded |
| D: combined candidate | Built, not flashed | Empty SD socket, antenna/bridge and power wiring not physically verified |
| E: alternate source | NOT EXECUTED | No instrument/source or safe reconnection capability available to this agent |
| F: reversal | NOT EXECUTED | No new physical intervention to reverse |

New RF DATA sessions: **0**. New physical ACK/NACK trials: **0**. Firmware flashes: **0**. Fuse/EEPROM/BOOT writes: **0**. MCU and peripheral rail voltages/current: **NOT MEASURED**. A physical acceptance or reliability claim is not justified.
