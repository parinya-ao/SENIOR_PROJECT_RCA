# LoRa ARQ V1 root-cause investigation — 20261113T211753Z

**Status: PARTIALLY_ISOLATED.**

This run separates two failures:

1. Tracker STATUS silence was caused by the Host UPDI writer using the wrong STS address width for AVR128DA28 GPR/mailbox registers. The Host-side correction is in place; the real Tracker completed 20/20 non-RF STATUS transactions.
2. In two reader-free Tracker SEND trials, the AVR reset-cause snapshot changed from `GPIOR0=0x20` (UPDIRF at baseline) to `GPIOR0=0x01` (PORF after the receive window). A matched 15-second no-RF idle control kept `GPIOR0=0x20`, `RSTFR=0`, and `UART_FLAGS=1`. This confirms a POR occurred during the SEND experiment interval. It strongly implicates the Tracker power path during radio operation, but no voltage waveform was captured and the exact instant relative to TX_START is unknown.

The earliest proven RF failure boundary is the Tracker MCU reset during the controlled SEND interval. Tracker TX_START/TX_DONE and radiated RF were not captured in the two POR trials. Rudolph entered continuous RX and timed out without a captured header or packet. The historical 12:15 trial, where Tracker logged TxDone, remains a separate unisolated RF failure.

## Review map

- [Final RCA](FINAL_RCA.md)
- [Baseline and preservation](00_scope_and_baseline.md)
- [Hardware topology](01_hardware_topology.md)
- [Incident timeline](02_incident_timeline.md)
- [Source audit](03_source_audit.md)
- [Hypotheses](04_hypothesis_register.md)
- [Experiment plan](05_experiment_plan.md)
- [Execution journal](06_execution_journal.md)
- [Hardware measurement gaps](07_hardware_measurements.md)
- [Radio registers](08_rf_register_analysis.md)
- [ARQ path](09_arq_protocol_analysis.md)
- [Cross-experiment comparison](10_cross_experiment_comparison.md)
- [Root-cause analysis](11_root_cause_analysis.md)
- [Corrective actions](12_corrective_actions.md)
- [Regression results](13_regression_results.md)
- [External source log](references/SOURCE_LOG.md)
- [Experiment matrix](experiments/EXPERIMENT_MATRIX.csv)
- [Evidence manifest](manifest.json)
- [Original 1,553-file hash baseline](original_hashes.json)
- [Final hash comparison](final_hashes.json)

Raw evidence remains in its original `artifacts/` directories. This run does not copy over or rewrite Incident A, Incident B, or the earlier RCA documentation.
