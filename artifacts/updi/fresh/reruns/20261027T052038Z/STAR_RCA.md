# RCA_FRESH_01 — rerun 20261027T052038Z

## Result

**P: 0/100; Q: 99/100 strict SIB response-length passes, excluding smoke. Causality remains unresolved and power-confounded.** The user confirmed a power change/cycle on fresh P / ttyUSB1 during this rerun. The event time relative to attempts is unknown. The results cannot be labeled an untouched physical baseline or used to establish spontaneous recovery, power causality, repair or path/target locality.

No agent-issued physical or programming change occurred. Zero flash writes, fuse writes, chip erases and BOD changes. Both ports are closed. Latest SIB30 gates are false for both lanes, so no control or identity reads were performed.

## Situation and task

The user requested a rerun of the fresh campaign plan. The existing runner and strict transport were reused unchanged. Fresh discovery again assigned P to `pci-0000:00:14.0-usb-0:1:1.0` / ttyUSB1, and Q to `pci-0000:00:14.0-usb-0:4:1.0` / ttyUSB0. Separate PowerBoard P/Q are branch records; target fingerprints remain UNKNOWN and descriptor-identical adapter units remain UNRESOLVED. See [topology](TOPOLOGY.md) and [frozen mapping](mapping.json).

Supplies, shared upstream connections, grounds, physical pinout, instrument availability, firmware/fuses and target continuity remain unverified. Two power boards do not establish two independent supplies or rule out shared-ground/load interactions. No historical target X/Y assignment is imported.

The task was to repeat smoke and baseline measurements, follow the non-stationarity and confirmation gates, preserve all prior evidence, and select only a defensible next discriminator.

## Action

Exactly the existing two lane workers were reused. They wrote only this dated rerun's lane-local evidence and Markdown. The coordinator owns shared reports, verification and interpretation. The previous campaign remains intact.

Configuration: nominal38400, 8E2, timeout1s, two300-baud BREAK exchanges, no hidden retries. Every attempt acquired the stable-path lock, checked owners, rediscovered its frozen path, opened exclusively, stopped at the first failure, closed and released. Canonical envelopes retain epoch-prefixed UUID attempt IDs, command, separate stdout/stderr, exit status, wall/monotonic timestamps, mapping, original transport classification, operation bytes/BREAK ordinals and hashes.

Smoke was0/10 on both lanes. Q baseline1 then passed30/30; this boundary change triggered three30-attempt baseline batches per lane. After baseline3, one response-short failure on Q justified a separate10-attempt confirmation batch per lane, reaching100 baseline/confirmation attempts per lane. Smoke stayed separate. The later user report means these are baseline-labeled observations with unknown power-intervention timing, not verified untouched batches.

## Per-batch measurements

| Lane | Batch | Strict pass/N | Success/failure | Wilson95 success | Median/p95 ms | Exact failures |
|---|---|---:|---|---|---:|---|
| P | Smoke | 0/10 | 0%/100% | 0–27.754% | 1370.317/1404.108 | SIB_RESPONSE_EMPTY:10 |
| Q | Smoke | 0/10 | 0%/100% | 0–27.754% | 1374.645/1405.022 | SIB_RESPONSE_EMPTY:10 |
| P | Baseline1 | 0/30 | 0%/100% | 0–11.352% | 1382.193/1401.799 | SIB_RESPONSE_EMPTY:30 |
| Q | Baseline1 | 30/30 | 100%/0% | 88.648–100% | 382.008/404.675 | None |
| P | Baseline2 | 0/30 | 0%/100% | 0–11.352% | 1381.954/1415.842 | SIB_RESPONSE_EMPTY:30 |
| Q | Baseline2 | 30/30 | 100%/0% | 88.648–100% | 384.640/403.012 | None |
| P | Baseline3 | 0/30 | 0%/100% | 0–11.352% | 1386.708/1401.164 | SIB_RESPONSE_EMPTY:30 |
| Q | Baseline3 | 29/30 | 96.667%/3.333% | 83.329–99.409% | 385.139/424.295 | SIB_RESPONSE_SHORT:1 |
| P | Confirmation10 | 0/10 | 0%/100% | 0–27.754% | 1385.289/1395.157 | SIB_RESPONSE_EMPTY:10 |
| Q | Confirmation10 | 10/10 | 100%/0% | 72.246–100% | 377.039/401.882 | None |

Descriptive baseline+confirmation summaries, excluding smoke:

| Lane | Strict pass/N | Wilson95 success | Median/p95 ms | Failures |
|---|---:|---|---:|---|
| P | 0/100 | 0–3.699% | 1383.221/1401.799 | SIB_RESPONSE_EMPTY:100 |
| Q | 99/100 | 94.551–99.823% | 382.996/409.799 | SIB_RESPONSE_SHORT:1 |

Latency is end-to-end attempt time, including child process, discovery and owner checks. Raw transport JSON retains individual operation timings. Intervals are conventional descriptive Wilson intervals; the power-confounded non-stationary observations do not demonstrate a stable underlying reliability rate. No smoke data is pooled into the100-attempt summaries.

All220 attempts had exact BREAK1/BREAK2 and SIB-command echoes. No empty/short/corrupt local echoes or host/busy/discovery/execution errors occurred. Across the rerun there are120 empty responses, one16-byte short response and99 full32-byte responses. Historical ACC failures remain separate; no ACC command, ACK, reset/OCD status or NVM measurement was performed. Unmeasured fields stay blank.

## Response anomaly and acceptance limit

The unchanged strict backend accepts a SIB response by32-byte length; it does not independently validate every SIB field. Of Q's99 length-based passes,98 share:

`2020202041565220503a32443a312d334d32202841372e4b563030312e302900`

One accepted full response differs at zero-based byte3 (`20`→`e0`):

`202020e041565220503a32443a312d334d32202841372e4b563030312e302900`

The failing short response is16/32 bytes:

`2020202041565220503a32443a312df3`

Both outlier run IDs and bytes are in [verification](VERIFICATION.json) and [response variants](reports/response_variants.csv). The original PASS/SHORT classifications are preserved. The full-length outlier is flagged as a bytewise anomaly; it is not proof of a specific electrical mechanism or a verified target fingerprint.99/100 therefore does not mean99 semantically validated identities.

## Gates and causal interpretation

P's latest baseline30 failed0/30; Q's latest baseline30 passed29/30. Q's subsequent10/10 confirmation does not replace the required latest all-pass30. Both control gates remain false. No control30, signature, REVID or factory-serial reads were attempted; no16-bit address extension was needed. The [official AVR128DA signature-row summary](https://onlinedocs.microchip.com/oxy/GUID-3EE676DF-490E-41BC-98F0-5774B35DC989-en-US-25/GUID-6FF396A2-060F-4D38-98B7-29984CC474AA.html) was consulted for the conditional identity step; target identity remains UNKNOWN.

User report: power changed/cycled on P / ttyUSB1. No exact time, duration, supply state or affected attempt was supplied. See [reported intervention](reports/reported_interventions.csv). This is not a controlled power experiment. Q improved during the rerun, but its transition cannot be attributed to P power without temporal correlation and controls. Shared-condition/load/ground interaction, target state, independent intermittency and delivered-signal/host receive behavior remain alternatives.

All D1–D8 remain UNRESOLVED at score0. No prediction discriminates a cause here; no controlled A/B/A evidence exists, so no+3 score or locality/proof is justified. The separate power-board domain remains a candidate. No fault is called repaired.

## Selected next experiment and stopping rule

**Causal branch: BLOCKED_MEASUREMENT / POWER_CONFOUNDED.** No target crossover or restoration is requested while the baseline is non-stationary and power-intervention timing is unknown.

Smallest discriminator: after a qualified operator verifies safe pinout/reference attachment, log target power state and obtain one simultaneous BREAK-triggered P-lane capture of target-local VDD, adapter-to-target ground offset, adapter TX and target UPDI, with all supplies/topology held fixed.

Hypothesis: the delivered waveform or target-local electrical condition is invalid despite correct local echoes. Prediction: correlated rail/ground excursions or an invalid delivered request distinguish an electrical branch; a target response visible on UPDI but absent at host selects receive/transport behavior; valid delivery with no target transmission retains target-state/configuration/assembly alternatives. Independent comparison is measurement location/channel during the same attempt; no circuit variable is actively changed. Controls are frozen paths, adapters, harness/resistors, separate power boards, target power state, firmware/fuses and serial settings.

Retain raw traces, trigger alignment, timestamps and their linked run ID/hashes. Probe loading or a wrong reference is an alternative interpretation. Stop before attachment if safe isolation/pinout is uncertain, or stop the experiment if power/topology changes without a recorded event. A passive capture is not A/B/A and does not itself prove a component defective. No repair before discriminating evidence; any later repair needs identical screen30 and confirmation100.

## Verification, provenance and limitations

Host suite: **150 passed in0.16s**, unchanged105 inherited tests plus45 fresh tests. No source/transport change was made during this rerun, so no new implementation or Graphify code refresh was required.

Counts remain separate:629 historical attempt rows/7,350 events; previous fresh campaign80 attempts/560 events; this rerun220 attempts/1,540 events. All300 current/previous fresh attempt IDs are unique, with no event/run collisions. Old historical run IDs remain batch-level identifiers; historical statistics and target associations do not enter rerun scores or rates.

All629 historical raw hashes,438 prior fresh artifact hashes,80 prior fresh canonical envelopes,220 rerun canonical envelope hashes and660 rerun source-artifact hashes validate. Original and rerun source hashes match. CSV epochs/schemas, identity mapping, event uniqueness/mapping, strict read-only transmitted frames and zero-write budgets verify. Both ports are idle.

**Full historical manifests do not pass:** two context-tool files drifted, `experiments/updi_rca/.automation/compact-bundle.xml` and `experiments/updi_rca/.repomixignore`. The first was already different at preflight and changed again during the rerun; the second changed during the rerun, with origin undetermined.1527/1529 new-freeze entries and1088/1090 original-freeze entries match. Raw evidence/source files and the previous campaign's438 artifact hashes remain intact. Neither old hash anchor was rewritten or restored to hide drift. [VERIFICATION.json](VERIFICATION.json) explicitly reports RAW_EVIDENCE_PASS_WITH_CONTEXT_FILE_DRIFT.

Root cause and target identity remain unproven. Instrument availability and physical pinout remain unverified. No safe controlled physical isolation, restoration, component intervention or repair acceptance test was performed.
