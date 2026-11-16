# Offline RCA — Tracker to Rudolph

**Verdict: HARDWARE_MEASUREMENT_REQUIRED.** Two different failures are preserved;
neither identifies a defective radio or proves a new brownout.

Start with [RCA_REPORT.md](RCA_REPORT.md). Supporting analyses:
[evidence](EVIDENCE_INDEX.md), [UPDI](UPDI_ANALYSIS.md),
[firmware](FIRMWARE_ANALYSIS.md), [power](POWER_ANALYSIS.md),
[radio](RADIO_ANALYSIS.md), [hardware](HARDWARE_ANALYSIS.md),
[hypotheses](HYPOTHESIS_MATRIX.md), [findings](FINDINGS.md).

Reproduce from the repository root, with no connected devices required:

```sh
uv run python tools/rca/analyze.py artifacts/arq/20261113T121506Z-reverse-raw
uv run python tools/rca/analyze.py artifacts/arq/20261113T123620Z-reverse-raw
uv run python tools/rca/analyze.py artifacts/arq/20261113T123837Z-standby
uv run python -m unittest discover -s tests -p test_rca.py
```

The analyzer accepts only a directory and emits JSON to stdout. Exit 2 means
invalid/corrupt evidence; exit 0 means analysis completed, **not RF success**.
Missing values are JSON null (UNKNOWN). Inputs are read only, bounded to 16 MiB
per read and 64 MiB cumulative reads, at most 2048 manifest entries. Paths must
resolve inside the bundle. Existing event/HEX parsers are reused without invoking
their hardware runners. It intentionally never asserts ROOT_CAUSE_CONFIRMED.
The single module avoids seven overlapping parser/report modules.

OBSERVED means directly captured or verified source; DERIVED means a documented
calculation; HYPOTHESIS means untested mechanism; UNKNOWN means absent evidence.
JSON reports are derived artifacts, not replacements for the original bundles.
No live port, fuse, register, firmware, RF, or hardware operation is part of this RCA.

Source revision: `1e2dd303e2ca63b93826df030e8fd116683d7284`, dirty working tree
inherited from prior implementation. Actual repository is
`/home/parinya/university/SENIOR_PROJECT_RCA`. The requested `loraboard` path is
inside `/home/parinya/university/iwing-tracker`, a separate repository with a
legacy project LoRa wrapper, not the active ARQ implementation.

Observed tools: host `python` 3.12.16; `uv run python` 3.14.10; pyserial3.5;
PlatformIO6.2.0; AVR-GCC7.3.0; AVRDUDE8.1; installed RadioLib7.1.2.
No dependency installation or upgrade was performed. Six firmware builds are
historical evidence from the prior task, not new builds in this RCA-only task.
