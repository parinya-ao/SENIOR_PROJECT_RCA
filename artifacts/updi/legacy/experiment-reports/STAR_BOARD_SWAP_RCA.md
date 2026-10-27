# AVR128DA28 board-swap RCA — PRE NO-GO checkpoint

Epoch: **RCA_BOARD_SWAP_01**. Current task remains active, waiting for target-power-state clarification. No crossover result or completion of the board-swap investigation is claimed.

## Situation

| Metric | Count / value |
|---|---:|
| External paths | 2 |
| Physically labeled targets | 2 |
| Independently read target fingerprints | 0 |
| Inherited original runs / events | 509 / 6387 |
| Previous continuation runs / events | 40 / 546 |
| Start-of-swap runs / events | 549 / 6933 |
| New hardware runs / events | 20 / 140 |
| Combined runs / events | 569 / 7073 |
| P→X PRE SIB passes / failures | 0 / 20 |
| P→X exact BREAK1 / BREAK2 / SIB-command echoes | 20 / 20 / 20 |
| P→X SIB-response bytes observed | 0 |
| Q→Y PRE hardware attempts | 0 |
| Crossed / restored attempts | 0 / 0 |
| Causal A/B/A cycles | 0 |

## Task

Remove the adapter-target pairing confound and identify ownership of FC1, the **preceding 300-baud BREAK/local-echo synchronization failure** in a nominal38400 session. The historical FC2 result, **19/60** missing ACC data responses after exact echo, remains separate.

## Action

### Identity and physical freeze

The user newly confirmed **safe isolation and PCB-only swap verified; X/Y labeled**. Original endpoints were retained. P remains `pci-0000:00:14.0-usb-0:4:1.0`, Q remains `pci-0000:00:14.0-usb-0:1:1.0`. Current tty locators at freeze were `/dev/ttyUSB0` and `/dev/ttyUSB1`; neither is a physical identity. Both adapters still report duplicate serial0001. Target fingerprints remain UNKNOWN_TARGET.

The fixed external path includes USB port, cable, CP2102, bridge/resistor, UPDI jumper and GND jumper. Only the PCB endpoint may move in a later experiment. Actual connector descriptions, resistor values, target supply source and time since power-on were not supplied and remain UNKNOWN. The user confirmed a safe isolation method; whether the targets were powered on during PRE is now the pending question. Host mains was online at the coordinator freeze.

The freeze is in [SWAP_FREEZE.md](../memory/SWAP_FREEZE.md), with exact current udev/sysfs mapping and the hashes/row counts of the four inherited ledgers. No inherited hardware row was overwritten or counted as a swap attempt.

### Software gate and workers

Current Superpowers skills and Agent Memory instructions were read. Agent Memory was queried; unrelated-project lessons were excluded, and repository artifacts supplied the verified checkpoint. Existing host suite:75 passed. Required crossover tests were added first: RED7 missing behaviors /10 existing checks passing; minimal SIB outcome/restoration helpers then yielded **92 passing tests** before hardware authorization.

Exactly the existing two workers were reused, one per stable external path. P/Q workers wrote only their epoch-specific evidence and PATH_P/PATH_Q Markdown. The coordinator owns shared code, CSVs, classification and physical action selection.

Both paths were resolved without trusting tty names. Preflight ownership/process/topology observations were captured. Existing serial probe, framing, synchronization, timeout and runner were reused; no transport timing was changed. P opened exclusively and closed each bounded attempt. Q's two custom-wrapper invocations failed before hardware access; they are preserved as **HOST_TOOL_ERROR,0 serial opens**, not PORT_BUSY or UPDI failures. Q was then held, and direct final ownership checks listed no holder. P's final checks also listed no holder.

### PRE experiment and decision

- Hypothesis: the original P→X passing / Q→Y failing asymmetry still exists.
- Prediction: P passes the strict SIB path, while Q fails FC1 during BREAK echo.
- Independent variable: none changed intentionally during the PRE reproduction.
- Controls: original endpoints, external bundles, existing software, nominal38400, existing300-baud synchronization and1s timeout; no flash/fuse/BOD changes.
- Measurement:20 SIB attempts on P; Q was held before its first valid attempt after the P outcome changed.
- GO criterion: current original asymmetry reproduced and identities/ownership unambiguous.
- Observed fail criterion: previously passing P had **0/20 SIB responses**, despite exact synchronization and command echoes.
- Interpretation: **NON_STATIONARY / NO-GO**. Do not perform a crossover against an unreproduced original baseline.

P run `swap-pre-P-20261027T015802555251Z` completed20 attempts from UTC2026-10-27T01:58:02.361274Z to01:58:26.165395Z. Exit1 records completed failed measurements, not a runner abort. Exact raw records and the command/stdout/stderr/source hashes are under [path_p evidence](../evidence/RCA_BOARD_SWAP_01/path_p/). All20 attempt hashes were independently checked by the coordinator.

No board-swap instruction was issued. No crossed re-identification, N=30 screen, N=100 confirmation, restoration, causal-branch decomposition or repair was performed. These remain dependent future actions.

## Result

### Current matrix

| Phase / pairing | N | Pass / fail | Success rate | Wilson95 success interval | Failure stage | Median / p95,ms |
|---|---:|---:|---:|---|---|---|
| PRE P+X | 20 | 0 /20 | 0% | 0–16.113% | UPDI_CONTROL_RESPONSE:20 | 1146.775 /1148.088 |
| PRE Q+Y | 0 | NOT_MEASURED | NOT_MEASURED | NOT_APPLICABLE | NOT_MEASURED | NOT_APPLICABLE |
| CROSSED P+Y | 0 | NOT_MEASURED | NOT_MEASURED | NOT_APPLICABLE | NOT_MEASURED | NOT_APPLICABLE |
| CROSSED Q+X | 0 | NOT_MEASURED | NOT_MEASURED | NOT_APPLICABLE | NOT_MEASURED | NOT_APPLICABLE |
| RESTORED P+X | 0 | NOT_MEASURED | NOT_MEASURED | NOT_APPLICABLE | NOT_MEASURED | NOT_APPLICABLE |
| RESTORED Q+Y | 0 | NOT_MEASURED | NOT_MEASURED | NOT_APPLICABLE | NOT_MEASURED | NOT_APPLICABLE |

Wilson calculation uses z=1.96 and is descriptive; consecutive attempts may share state. No sample count is treated as a hypothesis probability.

All **60 current host echo frames** were EXACT:40 BREAK echo frames and20 SIB-command echo frames. Empty/corrupt/short/extra/shifted echo frames:0. There were20 empty SIB-response reads, classified **SIB_TX_ECHO_OK_RESPONSE_MISSING / UPDI_CONTROL_RESPONSE**. They are neither FC1 LOCAL_ECHO failures nor FC2 ACC-data misses. Host API echo evidence does not establish electrical levels or prove target receipt.

The current P result differs from its preserved historical100/100 SIB passes. It establishes a changed observed protocol state; it does not establish that target power is the cause. The target power state during PRE is awaiting a user answer. Stage-observation evidence score=1, sampleN=20, failure rate100%; candidate-specific causal evidence score=0, crossedN=0, causal-effect latency/CI not applicable.

### Required answers

| Question | Answer | Evidence |
|---|---|---|
| 1. Did FC1 follow the target? | UNKNOWN | 0 crossed attempts |
| 2. Did FC1 follow the external path? | UNKNOWN | 0 crossed attempts |
| 3. Did reconnect/reseat alone alter failure? | UNKNOWN | 0 controlled reseat experiments |
| 4. Is there adapter×target interaction? | UNKNOWN | No complete2×2 matrix |
| 5. Which BREAK failed? | VARIABLE historically; neither failed in current P | Historical Q BREAK1/2 split171/29; current P BREAK1 and2 exact20/20 each; current Q untested |
| 6. Did kernel USB errors correlate? | NOT_CAPTURED | No attempt-correlated USB evidence; limited/empty host log access does not establish electrical health |
| 7. Is board-level locality proven? | NO | 0 crossover/restoration cycles |
| 8. Is adapter-path locality proven? | NO | 0 crossover/restoration cycles |
| 9. Is component-level cause proven? | NO | 0 component interventions or electrical measurements |
| 10. Is physical measurement still required? | YES for electrical/component proof if crossover cannot resolve it | 0 voltage/waveform captures; immediate next step is current power-state clarification |
| 11. One next smallest discriminator? | Report whether both targets were powered on during PRE | Keep all wiring fixed; do not infer a power cycle or act on an elapsed timeout |

**Root-cause locality:** UNRESOLVED. **Component root cause:** UNRESOLVED. **Confidence:** current-stage observation established; causal ownership unproven. No hypothesis is promoted to PROVEN/STRONGLY_SUPPORTED from this changed P result. The inherited168-row hypothesis/ranking tables remain untouched.

If the user reports a target was off, a power-on-only repeat can be designed and recorded with the wiring unchanged; its before/after result must remain separate from the current run. If both were already on, inspect the documented current state and the smallest read-only boundary discriminator before any physical crossover. Neither branch is assumed in advance.

The board-swap completion conditions have **not** been reached. This is a resumable PRE checkpoint, not a claim that crossover/software experiments are exhausted.

### Artifacts and safety

- [Board-swap matrix](board_swap_matrix.csv), [run rows](swap_runs.csv), [event rows](swap_events.csv), [echo distribution](swap_echo_distribution.csv), [causal proof ledger](swap_causal_proof.csv).
- [Current state](../memory/SWAP_CURRENT_STATE.md), [decisions](../memory/SWAP_DECISIONS.md), [evidence log](../memory/SWAP_EVIDENCE_LOG.md), [plan](../memory/SWAP_PLAN.md), [P worker](../memory/PATH_P.md), [Q worker](../memory/PATH_Q.md).
- New flash writes0; fuse writes0; BOD changes0; chip erases0. No repair, high-voltage activation, timing workaround, firmware/NVM/FOTA/FLAG_RX/ACC experiment, or coordinator-directed power cycle occurred.

### Checkpoint verification

Full isolated host suite:92 passed. [Validation CSV](swap_verification.csv):17 checks passed, including569/569 raw-source hashes,21/21 preserved report-file hashes,7073 unique combined event IDs and168 preserved hypothesis IDs. Current20 attempt IDs are unique; all140 events map to the current run and all60 echo frames are exact. The P evidence manifest verifies60/60 entries. Q hardware raw-file count is0. Unmeasured matrix cells retain blank outcomes/rates instead of artificial zero-percent results.

Graphify was refreshed after code changes:2575 nodes/4241 edges. It reported optional PDF-extraction availability and existing external-header/unsupported-file limitations; no extra dependency was installed. These checks validate the saved checkpoint and do not establish crossover causality.
