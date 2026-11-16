# Regression results

## Python

- Focused Host/capture/Gate1 suite: **67 passed, 0 failed** via uv run python -m unittest -v tests.test_arq_capture tests.test_upditerm_transport tests.test_gate1_rca.
- Full test discovery: **272 tests run, 2 skipped, 7 errors**. Every error is a compiler-dependent test that cannot start because host g++ is absent (FileNotFoundError: g++). clang++ is also absent. No assertion failure was reported.
- Full output: firmware/full-suite-output.txt. Focused output: firmware/focused-test-output.txt.
- Six-environment build output: [pio-six-final.log](../../../.automation/pio-six-final.log).

## Configuration and firmware builds

- uv run python tools/config/generate_lora_config.py --check: passed.
- uv run python tools/config/validate_lora_ssot.py config/lora_system.json: passed; the tool limits this to static configuration consistency.
- PlatformIO builds: sender_arq, receiver_arq, sender_arq_test, receiver_arq_test, sender_reverse_raw, receiver_reverse_raw: **6/6 succeeded**.
- PlatformIO reported RadioLib 7.1.2.

## Hardware counts

- Gate1 non-RF STATUS: **20 attempted, 20 passed, 0 failed**; latency min 7,345.001 ms, median 7,557.178 ms, max 7,738.887 ms.
- Reader-free reverse-raw: **7 one-packet SEND attempts**, all Gateway RX windows timed out; 28 command bytes were accepted per attempt.
- POR source observed after SEND: **2/2** reader-free repeats; matched 15-second no-RF idle control: **0/1** reset observations.
- Tracker TX_START/TX_DONE captured in POR runs: **0**.
- Valid Gateway RX payloads captured in POR runs: **0**.
- External voltage/current/RF captures: **0**.

## Evidence integrity and restoration

- Original Incident A, Incident B, and standby manifests: **221 files checked, 0 hash mismatches**.
- Reader-free POR bundles 20261113T210613Z and 20261113T211753Z: **61/61 listed files each verified**, 0 missing, 0 mismatched.
- Normal restoration 20261113T212027Z: standby true; RF transmissions during cleanup 0.
