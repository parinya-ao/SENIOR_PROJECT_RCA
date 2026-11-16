# Soak Runner Implementation and Regression

## Changes

- `tools/arq_trial.py`: added a bounded session/duration stage plan, SX127x LoRa time-on-air calculation, start-to-start pacing, prerequisite receipts, fail-closed hardware gates, persistent stage status, interruption/partial-result recording, and a per-session metric extractor tied to validated raw DATA/ACK bundles.
- `config/arq_test.toml`: set DATA start spacing to 10,000 ms. At the current SF7/BW125 profile, a 44-byte DATA frame occupies the channel for 92.416 ms, so the configured gap is 0.9242% per maximum frame.
- `tests/test_arq_soak.py`: covers airtime, stage order, pass/fail receipts, interruption recovery, duration timestamps, confidence intervals, pacing, and hardware-gate dispatch.
- Existing tests were aligned with the current physical preflight contract and the configurable ARQ spacing, including the portable sender timing boundary.

No new dependency was added. The runner does not claim physical success from simulated tests or firmware logs alone.

## TDD and verification

Focused RED evidence is saved beside the prior radio-only investigation tests, including `arq-soak-ledger-red.txt`, `arq-soak-metrics-red.txt`, `arq-soak-interruption-red.txt`, and `arq-soak-failure-reason-red.txt`. Retry-history and stale-process RED cases are [here](retry-preservation-red.txt) and [here](live-resume-red.txt). The final focused soak suite passed **18 tests**.

The final full host stage passed **324 tests, 1 skipped, 0 failures, 0 errors**, plus 10 role-log checks, 92 RadioLib-wrapper checks, and the RF-disabled send-protection check. Evidence: [host test command output](../20261114T092808Z-soak-readiness-retry2/host-tests-final4.log) and [machine measurements](../../../artifacts/rf-proof/20261114T095758Z/host-measurements.json).

All **15/15 active PlatformIO targets** clean-built. Eight 923 MHz candidate HEX/ELF pairs were archived; every archived HEX hash matched its build result. The firmware remains **not flashed**. See [build results](../20261114T092808Z-soak-readiness-retry2/FIRMWARE_BUILD_RESULTS.json) and [candidate image manifest](../20261114T092808Z-soak-readiness-retry2/candidate-builds-923.json).

The runner records its host PID in each active receipt. A restart refuses to overlap a still-live stage process and preserves a stale run as `INTERRUPTED` when the recorded PID no longer exists; the original termination reason remains unknown. The first full-suite run after integrating the new stage flow exposed stale test assumptions: missing physical-gate arguments, an outdated mocked CLI target, and a portable ARQ test using the former 3-second retry spacing. Those tests were corrected to exercise the current guard and use `ARQ_SPACING_MS`; the final full-suite run above is green. An earlier firmware result-reporting wrapper also stopped on an import/manifest mismatch; it did not indicate a compiler failure. A clean rerun with a role-independent image reader produced the 15/15 build report.

## Explicitly not verified

No hardware was programmed or queried for this soak. Real RegOpMode readback, DATA reception, ACK/NACK, retries, resets, supply voltage, current, and RF airtime remain unknown. Build output and HOST_SIMULATION evidence are not hardware evidence.
