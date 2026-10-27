# AVR128DA28 UPDI RCA — Continuation `RCA_CROSSOVER_01`

**Disposition:** Outcome E at the safe software boundary. The initial lane difference reproduced, but the adapter/target crossover was not performed because the user could not safely power off and identify the harness. No adapter, board, or component cause is claimed.

## Situation

The immutable inherited ledgers contain **509 run rows** and **6,387 event rows**. The continuation added **40 bounded raw attempts** and **546 protocol events**. Combined totals are **549 runs** and **6,933 events**. All inherited and new raw evidence hashes are checked in the final verification section below.

The inherited 38400-baud baseline was Lane A SIB **100/100** and control **100/100** pass, while Lane B was **0/100** in each condition, with all 200 failures at `LOCAL_ECHO`. The historical running/unheld data-read class remains separate: **19/60** LDS attempts lacked ACC data after exact echo (31.67%; Wilson 95% failure interval 21.31%–44.23%).

At the continuation precheck, the initial physical pairings were provisionally labeled P+X and Q+Y. P is the adapter on `ID_PATH=pci-0000:00:14.0-usb-0:4:1.0`; Q is `pci-0000:00:14.0-usb-0:1:1.0`. Both are CP2102 VID:PID `10c4:ea60` with duplicate USB serial `0001`. At this snapshot they resolved to tty aliases `/dev/ttyUSB0` and `/dev/ttyUSB1`; those aliases are not identity keys. Neither target has a verified unique signature-row serial. X and Y are provisional physical labels only; no stickers were applied.

| Initial pairing / condition | Attempts | Pass | Fail and stage | Success rate, Wilson 95% CI | Median / p95 latency |
|---|---:|---:|---|---|---:|
| P+X / SIB | 10 | 10 | 0 | 100.0%, 72.25%–100.00% | 156.332 / 158.131 ms |
| P+X / control | 10 | 10 | 0 | 100.0%, 72.25%–100.00% | 201.944 / 203.732 ms |
| Q+Y / SIB | 10 | 0 | 10 `LOCAL_ECHO` | 0.0%, 0.00%–27.75% | 1061.647 / 1064.128 ms |
| Q+Y / control | 10 | 0 | 10 `LOCAL_ECHO` | 0.0%, 0.00%–27.75% | 1061.556 / 1063.475 ms |

Every P+X probe passed its echo and target-response stages. Every Q+Y attempt stopped before a SIB/control request could be evaluated. The raw Q+Y attempts contain 20 failed echo frames, all `ECHO_EMPTY` (`TX=00`, expected length 1, observed length 0); three earlier synchronization frames echoed exactly before a later synchronization echo failed. No target response was reached on Q+Y. This is a repeat of a **lane-bound** result, not board-versus-adapter attribution.

## Task

Remove the adapter/target pairing confound to determine whether the repeated `LOCAL_ECHO` failure follows Adapter Q/path, physical Target Y, reconnection, or a two-factor interaction. Only after this lower-stage distinction would the historical exact-echo/ACC failure be revisited.

## Action

- Re-read the inherited STAR report, handoff, all required ledgers, and `PROMPT.md`; `updi_rca_ai_agent_prompt.md` is absent. Existing evidence remains preserved.
- Re-ran the inherited host tests: **45 passed**. Added TDD coverage for immutable pairing snapshots, conservative crossover classification, 2×2 interaction handling, and epoch-tagged run/event conversion. The new tests were observed failing on missing APIs before implementation; the final suite result is recorded below.
- Reused exactly the two existing lane workers. Each resolved one adapter by stable `ID_PATH`, checked its port was unowned, ran only its own 10-SIB/10-control read-only precheck, saved command/stdout/stderr/timing and raw attempts, and closed the serial link. No process held either port at the final ownership check.
- Recomputed every new per-attempt raw hash. Lane A’s 28-entry `SHA256SUMS` manifest passed; Lane B’s command/stdout/empty-stderr hashes match its execution record. The versioned run/event CSVs link every row to its raw file and hash.
- Requested the single no-programming target-only crossover. The user reported that power-off and harness identification could not be performed safely. No wiring was moved, no crossover probe was run, and no physical measurement was taken.
- No target flash, fuse, USERROW, EEPROM, BOD, reset, or NVM operation was performed. New flash writes: **0**; new fuse writes: **0**; chip erases: **0**. The existing diagnostic firmware remains unflashed.
- Compared the new matrix as rates and failure stages. The classifier and tests avoid labeling the two original pairings as an adapter or target effect when the crossed cells are absent.

## Result

The continuation **reproduced** the initial lane behavior with N=10 per condition: P+X succeeded 20/20 across SIB/control, while Q+Y failed 20/20 at `LOCAL_ECHO`. Per-condition Wilson intervals remain wide at N=10: 72.25%–100.00% for P+X and 0.00%–27.75% for Q+Y. P+X SIB/control median latencies were 156.332/201.944 ms; Q+Y were 1061.647/1061.556 ms. The old 100-attempt baseline remains stronger evidence of lane repeatability. No new ACC, reset, RUNNING-versus-STOPPED, firmware-equivalence, fuse-equivalence, or USB-protocol correlation test was performed in this epoch.

The existing test-priority scores are unchanged: reset/watchdog hypotheses score **20**; board-local power/GND and AVR-silicon groups score **19**; firmware/runtime priorities top out at **15** (individual H098=13 and H102=12); board-side UPDI scores **10**; PCB/assembly **6**; adapter/host **1**; fuse/environment/methodology **0**. These are deterministic test-priority scores, **not probabilities**. The 168-row status total remains **0 PROVEN, 0 STRONGLY_SUPPORTED, 8 SUPPORTED, 48 UNRESOLVED, 112 BLOCKED**. The repeated lane result adds no evidence capable of updating one physical entity’s cause.

### Required decision tree

| Question | Result | Evidence boundary |
|---|---|---|
| Did failure follow target? | BLOCKED | No crossed pairing; target identities remain unknown. |
| Did failure follow adapter? | BLOCKED | No crossed pairing; adapter and target remain confounded. |
| Did reconnect alone change outcome? | NOT_APPLICABLE | No reconnect/crossover occurred. |
| Was adapter×target interaction measured? | BLOCKED | The two crossed cells were not run. |
| Was a USB protocol error correlated? | UNKNOWN | No usbmon/kernel error correlation was captured for these 40 attempts. |
| Did exact local echo succeed? | YES for P+X; NO for complete Q+Y probes | P+X passed 20/20 attempts; Q+Y failed 20/20 at `LOCAL_ECHO`, after 3 isolated synchronization frames had echoed exactly. |
| Did control space succeed? | YES for P+X; NOT_REACHED for Q+Y | P+X 10/10; Q+Y control requests did not pass the echo gate. |
| Did ACC fail after exact echo in this epoch? | NOT_APPLICABLE | No ACC/data read was run. Historical separate result: 19/60 missing LDS responses after exact echo. |
| Was the failure RUNNING-state dependent? | UNKNOWN | CPU state was uncontrolled; no STOPPED comparison was run. |
| Did a new boot occur, and which reset flag accompanied it? | UNKNOWN | No heartbeat/independent boot marker was observed in this epoch. Historical BORF alone remains non-proof of a new reset. |
| Were firmware hashes identical? | UNKNOWN | No current flash hash was read. |
| Were fuse values identical? | UNKNOWN | No fuse reads were made. |
| Was target VDD measured? | NO | No physical instrumentation was available. |
| Was ground offset measured? | NO | No physical instrumentation was available. |
| Was RESET measured? | NO | No physical instrumentation was available. |
| Was the UPDI waveform measured? | NO | No physical instrumentation was available. |
| Is a component-level RCA proven? | NO | Component-level RCA is BLOCKED; no component is named. |

### Narrowest defensible conclusion

For P+X, the read-only SIB/control path passed **20/20** attempts (0 failures; 100%; per-condition Wilson 95% CI 72.25%–100.00%). For Q+Y, **20/20** attempts failed at `LOCAL_ECHO` (100%; per-condition Wilson 95% failure interval 72.25%–100.00%; median latency about 1.062 s). This confirms a difference between two *paired connection lanes*. It does not distinguish Adapter Q, Target Y, wiring/contact, or their interaction. Historical **19/60** ACC-data failures remain a separate later-stage class. No specific board assembly, AVR unit, capacitor, solder joint, regulator, or silicon defect is supported.

### Smallest next action

The user has stated that the crossover cannot be performed safely. Do not move the wiring under the present information. A qualified bench operator must first identify the normal target power-isolation control and verify the harness pin orientation; then the single discriminating operation is a no-programming target-only crossover with the USB adapters kept in their original host ports, followed by 100 SIB and 100 control attempts at 38400 baud for each crossed pairing. Until that safe setup exists, retain the conclusion above as lane-bound.

If the controlled crossover shows the failure follows one target, the next physical capture is simultaneous: MCU VDD relative to MCU-local GND; MCU-local GND versus adapter GND; RESET at the MCU; UPDI at both sides of the series element; and adapter TX. Capture during attach and RUN/known failure with low-capacitance probes, at least 20 MS/s, and at least 100 ms before and after trigger. This is a measurement-plan minimum, not an AVR device specification. Without that evidence, component attribution remains BLOCKED.

## Continuation artifacts

Versioned CSVs are under `reports/continuation/RCA_CROSSOVER_01/`; they preserve the inherited reports unchanged:

- `runs_RCA_CROSSOVER_01.csv` — 40 attempt rows.
- `events_RCA_CROSSOVER_01.csv` — 546 protocol-event rows.
- `device_inventory_RCA_CROSSOVER_01.csv` — two current adapter paths; both target identities unknown.
- `hypothesis_status_RCA_CROSSOVER_01.csv` and `root_cause_ranking_RCA_CROSSOVER_01.csv` — all 168 hypotheses retained; statuses/scores unchanged.
- `pairwise_board_comparison_RCA_CROSSOVER_01.csv` — path comparison only; no verified board identities.
- `crossover_matrix_RCA_CROSSOVER_01.csv` — two original cells measured; crossed cells explicitly marked `WAITING_PHYSICAL_UNSAFE`.
- `echo_error_distribution_RCA_CROSSOVER_01.csv` — 20 failed echo frames with byte lengths and raw-log hashes.
- `fuse_compare_RCA_CROSSOVER_01.csv` and `flash_budget_RCA_CROSSOVER_01.csv` — prior records carried forward; no new reads/writes.

## Verification

- Host suite: **53 passed**.
- Inherited raw sources: **509/509** SHA-256 checks match; inherited event IDs are unique and map to run IDs.
- Continuation raw sources: **40/40** SHA-256 checks match; continuation event IDs are unique, do not collide with inherited IDs, and every event maps to a continuation run ID. New run/attempt keys are unique.
- Combined ledgers: **549 runs / 6,933 events**. Old rows were preserved and continuation rows remain in a separate versioned directory.
- Hypothesis IDs: **168/168** match the inherited seed, continuation status, and continuation ranking; status counts are **112 BLOCKED / 48 UNRESOLVED / 8 SUPPORTED**. No score was treated as a probability.
- Versioned CSV row counts: inventory 2; runs 40; events 546; hypothesis status 168; root-cause ranking 168; pairwise comparison 8; crossover matrix 8; echo-error distribution 20; fuse comparison 2; flash budget 3.
- Crossover matrix state: 4 measured original-pairing cells and 4 crossed cells marked `WAITING_PHYSICAL_UNSAFE`; no unmeasured result was filled in.
- All new run rows identify adapters by stable `ID_PATH`; tty strings appear only as current locators. Target fingerprints remain `UNKNOWN_TARGET`.
- Continuation flash writes 0; fuse writes 0; chip erases 0. The carried-forward flash budget retains its historical event without representing it as a continuation write.

