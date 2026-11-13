# Confirmed and derived findings only

1. OBSERVED: original incident manifests/hashes and raw journals pass current
   offline verification. Integrity does not establish completeness.
2. OBSERVED: A has one TX/TxDone and a fifteen-second Rudolph timeout; no exact
   received packet. Classification PHYSICAL_RF_FAILURE_UNISOLATED.
3. OBSERVED: B reports an empty UPDI response and monitor exit, with no Tracker
   pre-TX/start/done or receiver terminal observation. RF INCONCLUSIVE.
4. DERIVED: B RX_READY reached the host136,922ns before SEND; independent MCU
   clocks were not subtracted. Host pipe write does not establish MCU receipt.
5. OBSERVED source: default SX127x errata macro is disabled; actual activeRX C3
   retains AutomaticIFOn1. Detailed manufacturer table instructs clearing it.
   Modeled driver tests isolate the compile switch's register effects; RF cause
   remains UNKNOWN. No physical cause is inferred from this source discrepancy.
6. OBSERVED source: OpMode bit3 is retained from reset; frequency is E4C000.
   DERIVED nominal carrier915MHz. No causal bit3 defect has been established.
7. OBSERVED source: core captures/clears RSTFR early; reverse firmware omits
   reset-generation telemetry. Later restored standby cannot exclude earlier reset.
8. OBSERVED: archived final standby readbacks/identities/status verify; current
   RCA performed no new hardware operation or production edit.

Evidence and exact sources: [index](EVIDENCE_INDEX.md), [transport](UPDI_ANALYSIS.md),
[firmware](FIRMWARE_ANALYSIS.md), [radio](RADIO_ANALYSIS.md), [power](POWER_ANALYSIS.md).
