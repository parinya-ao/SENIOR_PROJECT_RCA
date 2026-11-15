# Regression and preservation results

## Python tests

- Focused RCA/capture tests: **29 passed, 0 failed** via `uv run python -m unittest tests.test_arq_reader_free tests.test_arq_capture`.
- Full discovery: **285 tests run, 2 skipped, 7 errors**. All seven errors are compiler-backed tests that could not start because host `g++` is missing (`FileNotFoundError`). No assertion failure appears in the full-run output.
- Full output: [full-suite-output.txt](tests/full-suite-output.txt).

The focused suite covers the reader-free H01 summary, missing-event UNKNOWN semantics, POR flag transition, the explicit RF-path CLI gate, UPDI resync without CPU reset, partial event-line drain, and existing capture/Gate 1 behavior.

## Firmware and configuration

- PlatformIO environments built successfully: `sender_arq`, `receiver_arq`, `sender_arq_test`, `receiver_arq_test`, `sender_reverse_raw`, `receiver_reverse_raw` (**6/6**). Installed RadioLib reported `7.1.2`.
- `uv run python tools/config/generate_lora_config.py --check`: passed.
- `uv run python tools/config/validate_lora_ssot.py config/lora_system.json`: passed; it checks static consistency, not electrical suitability.
- `git diff --check`: passed.
- No source changes in `src/` or `lib/`; no RadioLib, frequency, power, PHY, fuse, BOOTSIZE, lock, or EEPROM changes.

## Hardware counts

| Test | Attempts | Outcome |
|---|---:|---|
| Gate 1 non-RF STATUS after STS fix (prior run) | 20 | 20/20 passed; 0 response mismatch |
| H01 reader-attached current trial | 1 session | Incomplete capture after Tracker UPDI failure; not an RF verdict |
| H01 reader-free current trial | 2 sessions (8, 9) | Each had five Gateway DATA TX_DONEs, five RX timeouts, and `TIMEOUT_EXHAUSTED`; session 9 confirmed Tracker POR on resync, session 8 reset read incomplete |
| Tracker RX-only matched control | 1 × 120.029947 s | 0 RF transmissions; no POR observed |
| Historical reverse-raw reader-free runs | 7 single-packet attempts | All 7 Gateway windows timed out; POR sampled in 2/2 |
| Historical forward raw capture | At least 17 matched packets | Explicit CRC-clean rows 15–17 in the preserved log |

## Preservation

- Historical Incident A, Incident B, and standby manifests: **221 files, 0 missing, 0 SHA-256 mismatches**.
- H01 reader-free bundles: session 8 **73 listed files**, session 9 **75 listed files**; 0 missing or mismatched in either bundle.
- RX-idle bundle: **44 listed files, 0 missing, 0 mismatches**.
- Application programming snapshots show signature, serial, EEPROM, fuses, and lock unchanged before/after each temporary test image write. Both boards were restored to verified normal standby after each live run.
- The 1,553-file baseline compares as **7 changed, 0 missing**. The exact paths are in [preservation.json](preservation.json); `tools/arq_trial.py` was already dirty at task start and was extended for these diagnostics. No historical incident bundle was overwritten.

The TDD CLI-dispatch test initially targeted the wrong mocked function and invoked the authorized no-RF RX-idle control. That control completed, recorded its bundle, and restored normal standby. The test now mocks `reader_free_h01` directly and passes offline; its accidental invocation produced no RF transmission.

## Source-fix follow-up

- Test-first register assertion: RED against the old adapter (`RegOpMode=0x8D` in the model), GREEN after the 915 MHz HF-bank bit was cleared in `setup()`; see [TDD_RESULTS.md](TDD_RESULTS.md).
- Focused suite after the source correction: **82 passed**.
- PlatformIO environments: `sender_arq`, `receiver_arq`, `sender_arq_test`, `receiver_arq_test`, `sender_reverse_raw`, and `receiver_reverse_raw`: **6/6 built** with RadioLib 7.1.2.
- Candidate firmware SHA-256 values: [candidate_builds.json](candidate_builds.json). Images remain unflashed; no RF A/B was performed.
- Full unit discovery after the source correction: **285 run, 2 skipped, 7 errors** because `g++` is unavailable. Captured output: [full-suite-source-followup.txt](tests/full-suite-source-followup.txt).
