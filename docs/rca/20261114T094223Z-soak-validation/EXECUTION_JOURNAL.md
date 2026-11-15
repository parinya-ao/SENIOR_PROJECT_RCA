# Execution Journal

## Experiment: Soak stage ledger and retry recovery

**HYPOTHESIS:** A stage receipt can enforce progression while retaining interrupted evidence.  
**COMMAND:** `uv run python -m unittest discover -s tests -p test_arq_soak.py -v`  
**HARDWARE:** None; host-only tests.  
**OBSERVED:** Initial stage-ledger tests exposed an unfinished entry point. Added tests demonstrated correct pass/fail, interruption persistence, stage prerequisite enforcement, duration measurement, and retention of an earlier interrupted receipt after a retry. Final focused result: 16 passed.  
**RAW EVIDENCE:** `retry-preservation-red.txt`; prior run logs `../20261114T092808Z-soak-readiness-retry2/arq-soak-ledger-red.txt`, `arq-soak-metrics-red.txt`, `arq-soak-interruption-red.txt`, and `arq-soak-failure-reason-red.txt`.  
**ELIMINATED CAUSES:** Host-side stage-order, loss-of-partial-receipt, and incorrect-pacing logic errors in the runner. No RF or hardware cause was tested.  
**REMAINING CAUSES:** Physical DATA/ACK and POR boundaries remain unknown.  
**NEXT EXPERIMENT:** Run the gated `1-session` stage only after supply, board wiring, SD guard, antenna/EIRP, and authorization conditions are directly established.

## Experiment: Full host regression

**HYPOTHESIS:** The soak runner and existing host/firmware logic pass together after the test updates.  
**COMMAND:** `PATH=<repository GCC 16.2.1> uv run python tools/rf_proof.py --stage host-tests`  
**HARDWARE:** Host only; the stage performs build/test and USB inventory but no UPDI probe, flash, reset, or RF transaction.  
**OBSERVED:** 322 tests run, one skipped, zero failures/errors; 10 role-log checks, 92 RadioLib wrapper checks, RF-disabled send protection passed.  
**RAW EVIDENCE:** `../../../artifacts/rf-proof/20261114T094920Z/host-measurements.json`; full command output `../20261114T092808Z-soak-readiness-retry2/host-tests-final3.log`.  
**ELIMINATED CAUSES:** Current host regression failures within the tested suite.  
**REMAINING CAUSES:** Physical firmware behavior and RF path were not exercised.  
**NEXT EXPERIMENT:** Gated single DATA/ACK hardware trial.

## Experiment: Clean build matrix

**HYPOTHESIS:** The 923 MHz candidate configuration builds across the active firmware targets and stays within the static application region.  
**COMMAND:** Clean then `pio run -e <environment>` for all 15 active targets.  
**HARDWARE:** None; PlatformIO build only.  
**OBSERVED:** 15/15 builds passed, including reset-vector and application-bound checks; eight candidate image pairs archived and hash-matched.  
**RAW EVIDENCE:** `../20261114T092808Z-soak-readiness-retry2/FIRMWARE_BUILD_RESULTS.json`, `candidate-builds-923.json`, and `build-logs/`.  
**ELIMINATED CAUSES:** Compile and static layout failures for those exact build inputs.  
**REMAINING CAUSES:** Both physical images remain unflashed; register readback, power, RF, ACK, and reset behavior remain unknown.  
**NEXT EXPERIMENT:** Physical preflight and verified application-only flash after blockers are closed.

## Experiment: Physical soak preflight gate

**HYPOTHESIS:** The runner refuses RF soak without physical confirmations before starting a device campaign.  
**COMMAND:** `uv run python tools/arq_trial.py --soak-stage 10-sessions`  
**HARDWARE:** No device port opened by the soak runner.  
**OBSERVED:** Exit code 2: `RF transmission requires --rf-path-confirmed after physical inspection`; no campaign started.  
**RAW EVIDENCE:** `../20261114T092808Z-soak-readiness-retry2/soak-preflight-blocked.log`; prior detailed blockers in `../20261114T044136Z-radio-only/HARDWARE_PREFLIGHT.json`.  
**ELIMINATED CAUSES:** None in hardware; this verified only the software preflight gate.  
**REMAINING CAUSES:** Safe supply/back-feed, SD socket state, RF path/EIRP, and authorization are not established.  
**NEXT EXPERIMENT:** Repeat this stage only after evidence-backed physical preflight, then run `1-session`.

## Experiment: Stale runner recovery

**HYPOTHESIS:** A restarted process must not overwrite a live run and should preserve a stale `RUNNING` receipt as interrupted when its recorded host PID is gone.  
**COMMAND:** `uv run python -m unittest discover -s tests -p test_arq_soak.py -v`  
**HARDWARE:** None; host-only tests.  
**OBSERVED:** Live-process overlap is rejected; an absent previous PID becomes an `INTERRUPTED` history receipt with termination reason recorded as unknown. Focused suite: 18 passed.  
**RAW EVIDENCE:** `live-resume-red.txt`; final full host output `../20261114T092808Z-soak-readiness-retry2/host-tests-final4.log`.  
**ELIMINATED CAUSES:** Stage receipt replacement and concurrent same-stage start within the modeled process-ownership boundary.  
**REMAINING CAUSES:** A hard host shutdown still cannot reveal its actual reason; partial fsynced session logs remain the evidence. No physical behavior was exercised.  
**NEXT EXPERIMENT:** Physically gated single-session DATA/ACK after preflight.
