# UPDI artifacts

- This tree holds generated UPDI traces, logs, reports, and experiment results. Experiment source and reproducibility inputs stay under `experiments/updi_rca/`.
- Historical evidence is immutable; moved files retain their names and bytes.
- Previously tracked evidence stays tracked. Previously untracked and machine-specific captures stay untracked; add new evidence intentionally when it should be shared.
- Put each new capture under `runs/<UTC-run-id>/` with its manifest and separate stdout/stderr files.
- `legacy/` preserves earlier directory provenance; `fresh/` contains the RCA_FRESH_01 results.
