# Fresh UPDI RCA — RCA_FRESH_01

## Executive result

**REPRODUCED_CURRENTLY; CAUSAL_BRANCH_BLOCKED_MEASUREMENT. No root cause or repair is proven.** Both fresh paths fail at the same observable boundary: exact local BREAK1, BREAK2 and SIB-command echoes followed by zero target-response bytes. This identifies a response boundary, not the failing component or whether the target received a valid waveform.

Fresh evidence: **80 read-only SIB attempts, 560 operation events**, with smoke and baseline kept separate. Historical evidence remains in place: **629 runs and 7,350 events**, excluded from fresh statistics, target identities and scores. No old P/Q or X/Y target association was reused.

## Situation

Two USB paths and two user-reported separate power boards are present. Fresh P is `pci-0000:00:14.0-usb-0:1:1.0` (discovery locator ttyUSB1); fresh Q is `pci-0000:00:14.0-usb-0:4:1.0` (ttyUSB0). Both adapters expose duplicate serial 0001, so unit identity remains unresolved. Both target fingerprints remain UNKNOWN. See [topology](TOPOLOGY.md), [frozen mapping](mapping.json) and [inventory](reports/device_inventory.csv).

Supply values, physical pinout, target power-on state, wiring, common upstream supply/ground, firmware/fuses and instrument availability are unverified in this epoch. Having two power boards does not establish two independent supplies or rule out a common electrical condition.

## Task

Start independent current measurements, preserve historical evidence and distinguish failure stages without programming targets. Narrow D1–D8 only through discriminating evidence; require restoration before locality and three consistent controlled A/B/A cycles or direct discriminating measurement before PROVEN.

## Action

### Implementation and evidence controls

The new runner wraps the existing strict probe CLI without changing transport behavior. Each attempt acquires a stable-path lock, checks ownership, re-resolves its frozen path, opens exclusively through the strict backend, closes and releases. UUID run IDs are epoch-prefixed. Unique attempt directories and exclusive-create envelopes prevent runner overwrites. This is write-once application behavior with hash verification, not filesystem-enforced write protection.

Every canonical envelope records epoch, run/mapping, actual command, separate stdout/stderr hashes, process exit status, wall and monotonic timestamps, original transport classification, derived stage and source raw JSON hash. Events retain operation bytes/timing and BREAK ordinals. Hashes, identity continuity, commands, result consistency, event uniqueness/mapping and epoch isolation are validated before reports.

Exactly two lane workers wrote only their own fresh evidence and lane Markdown. The coordinator implemented tests/code and owns all shared CSVs and interpretation. No reviewer or third worker was used. Parent review found and fixed command/result/timing integrity and control-batch reservation gaps with failing regression tests.

### Execution and batch results

Existing settings only: **38400, 8E2, one-second timeout, two 300-baud BREAK exchanges, no hidden retries**. Stop at the first failing layer. Each attempt transmitted only `00`, `00`, `55e6`; no control/data/ACC command was reached or requested.

| Lane | Batch | Pass / N | Success / failure rate | Wilson95 success | Median / p95 ms | Exact failure distribution |
|---|---|---:|---|---|---:|---|
| P | Smoke | 0 / 10 | 0% / 100% | 0–27.754% | 1368.049 / 1396.408 | SIB_RESPONSE_EMPTY: 10 |
| Q | Smoke | 0 / 10 | 0% / 100% | 0–27.754% | 1385.532 / 1414.215 | SIB_RESPONSE_EMPTY: 10 |
| P | Baseline-1 | 0 / 30 | 0% / 100% | 0–11.352% | 1384.324 / 1397.089 | SIB_RESPONSE_EMPTY: 30 |
| Q | Baseline-1 | 0 / 30 | 0% / 100% | 0–11.352% | 1373.747 / 1421.678 | SIB_RESPONSE_EMPTY: 30 |

CSV latency is end-to-end attempt latency, including child-process startup, inventory and ownership checks. Source transport-only median latency was P smoke/baseline 1146.660/1144.279 ms and Q smoke/baseline 1145.779/1144.963 ms. Raw JSON retains individual transport latency and operation timing.

All 80 attempts have three exact echoes and an empty 32-byte response request. BREAK empty/short/corrupt counts are zero; SIB command echo errors are zero; response-empty counts are 40 per lane across the two separately reported batches. PORT_BUSY, DISCOVERY_ERROR and EXECUTION_ERROR counts are zero. No new ACC failures were measured; historical ACC evidence remains separate. ACK, reset, OCD/runtime and kernel-error rates were not measured and cannot be reported as zero.

### Decisions and stopping rules

Smoke and baseline show no mixed success/failure and no change in stage boundary. The mandatory three untouched SIB30 repeat rule is therefore not triggered. This does not prove future stationarity. No 100-attempt expansion was selected: both lanes have identical all-failure stages, with no candidate rate contrast to discriminate; merely tightening overlapping zero-success bounds would not distinguish a cause. Smoke is never pooled into baseline.

Both latest SIB30 batches failed completely. The control30 gate is false for both lanes, so no control or identity reads were attempted. The strict backend's 8-bit data-address limit is unchanged; 16-bit signature/REVID/complete 16-byte serial support is deferred until reliable access makes it necessary. A failed SIB supplies no target fingerprint.

All D1–D8 remain **UNRESOLVED, score 0**, with no fresh causal evidence credited. The domains include separate power board/supply (D4), distinct from adapter/harness, target power, target UPDI assembly and runtime. No causal evidence item is duplicated. Scores are priorities, not probabilities; no ranking among tied domains is defensible.

## Selected causal experiment: BREAK-triggered simultaneous electrical capture

**Status: BLOCKED — instrumentation, pinout and safe measurement setup unavailable/unverified. Not performed.** A target crossover has no clear discriminating prediction while both branches share the same all-failure boundary, and verified physical target identities and safe isolation are absent.

Hypothesis: target-local power/ground or the delivered UPDI waveform is invalid despite exact local adapter echoes. Competing hypothesis: delivered electrical conditions are valid and the absent response reflects target state/configuration, endpoint behavior or host timing/receive behavior. These are candidates, not findings.

Prediction: a simultaneous trace can discriminate rail/ground excursion, failure to deliver/decode the request, target response present electrically but absent in host evidence, or a valid delivered request with no target transmission. Each result selects a different next domain; none alone identifies a particular capacitor, regulator, adapter unit or AVR defect.

Independent comparison: measurement location/channel (target-local VDD versus ground offset, adapter TX and target UPDI), aligned within the same failed attempt. No active circuit variable is changed. Controls: freeze USB paths, adapters, harness/resistors, power boards, firmware/fuses, transport settings and target state. Use one existing P SIB attempt after qualified verification of pinout and safe reference/isolation. The capture is passive, so it is not counted as controlled A/B/A or a repair trial.

Measurement: simultaneously capture target-local VDD, adapter-to-target ground offset, adapter TX and target UPDI, triggered on the first BREAK; retain pre-trigger context and both BREAK exchanges through the SIB response window. Use appropriate high-impedance/low-capacitance and differential/isolated probing where required by the verified ground arrangement. Associate the trace hash and monotonic/wall timestamp with that attempt's run ID.

Alternative interpretation: probe loading, incorrect reference/pin identification or trigger alignment can alter or hide the fault; local echo alone cannot validate target voltage or decoding. Stop before attachment if safe isolation/pinout is uncertain. Stop analysis if any channel saturates or the trace cannot be tied to a run. Do not modify power components or lower BOD. If valid waveforms show no target response, retain target state/configuration and silicon/assembly alternatives pending a further discriminator.

## Result and causal level

Supported observable fact: both current paths reproduce the same SIB response failure after exact local echoes. **No target-local, adapter-local, power-board-local or shared-cause claim is established.** The shared symptom is not evidence that the two boards have independent identical faults or a single common cause. Controlled cycles: zero. Repairs: zero.

The software campaign is complete to its measurement boundary; the causal branch remains BLOCKED. No safe target crossover, restoration, component swap, waveform capture, repair screen30 or confirmation100 was performed. No condition is called repaired or PROVEN. NON_REPRODUCED_CURRENTLY does not apply because the symptom was reproduced.

## Verification and preserved history

Requested host command: `uv run --project experiments/updi_rca pytest -q experiments/updi_rca/tests experiments/updi_rca/fresh/tests` — **150 passed** (105 inherited, 45 fresh). The project's default host suite also passed 105 tests. Test-first evidence and review rulings are recorded in [memory](MEMORY.md).

Historical file freeze covers 1,090 files. The 629 inherited attempt rows comprise 509 original + 40 continuation + 20 PRE + 60 post-swap; their 7,350 events comprise 6,387 + 546 + 140 + 277. Historical run_id denotes a batch (17 distinct IDs), whereas all 80 fresh run IDs identify individual attempts. These are provenance counts only. Fresh reports contain exactly 80 runs/560 events; no historical IDs, scores or target associations enter their metrics.

Canonical envelope and source artifact hashes, CSV schemas/epochs, unique IDs, event mapping, frozen identity continuity and strict transmitted frames are checked independently. Final verification results are in [VERIFICATION.json](VERIFICATION.json). The global tracked diff check also finds pre-existing whitespace problems in `.automation/compact-bundle.xml`; this unrelated generated bundle was left unchanged by this task.

Flash writes **0**, fuse writes **0**, chip erases **0**, BOD changes **0**. Firmware/fuse equivalence remains unmeasured. See [flash budget](reports/flash_budget.csv) and [fuse comparison](reports/fuse_compare.csv).

## Smallest next discriminator

Have a qualified operator verify the physical reference/pinout and obtain the single simultaneous BREAK-triggered P-lane capture described above. Keep the current topology fixed. This is a measurement prerequisite, not a request to swap or restore boards.
