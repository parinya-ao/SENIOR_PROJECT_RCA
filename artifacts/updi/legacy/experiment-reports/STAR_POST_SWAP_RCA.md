# AVR128DA28 untouched crossed-state RCA

Epoch: `RCA_POST_SWAP_01`. Phase measured: `CROSSED_UNTOUCHED`.
Disposition: crossed screen captured; restoration pending. This is a verified checkpoint, not a completed component RCA.

## Situation

2 external paths,2 physically labeled targets. Inherited evidence:509 original
runs/6387 events,40 continuation runs/546 events,20 latest PRE runs/140 events.
Total before this epoch:569 runs/7073 events. This epoch adds60 SIB attempts,
277 protocol events and124 echo frames. Combined:629 runs/7350 events.

Historical strict original pairing P+X passed100/100 SIB and100/100 control;
Q+Y passed0/100 in each. All200 historical Q failures stopped at LOCAL_ECHO
during300-baud BREAK synchronization. Q's SIB split was86 first-BREAK empty
and14 second-BREAK empty after exact first echo. Its control split was85/15.
Earlier short confirmation P+X passed10/10 SIB and10/10 control, Q+Y0/10 each.

The latest PRE is different: P+X0/20 SIB, with20/20 exact BREAK1, BREAK2 and
SIB-command echoes, then20 missing target responses. Median/p95 latency
1146.775/1148.088ms, Wilson95 success interval0–16.113%. Q had0 PRE attempts.
Target power during that PRE is UNKNOWN. This non-stationarity prevents a
clean stationary four-cell causal analysis.

FC1 means BREAK/local echo failure. Historical FC2 means exact echo followed
by missing ACC data:19/60 unheld LDS attempts. Current missing SIB responses
are a third observed boundary, `UPDI_CONTROL_RESPONSE`, not FC2. No ACC was
attempted in this epoch.

## Task

Determine where FC1 went after the user-reported completed PCB-only swap,
before any further physical manipulation. Distinguish observed protocol
stage, causal path and component. Preserve all168 master hypotheses while
working only on33 physical candidates plus8 methodology guards.

## Action

The inherited freeze defines P by `pci-0000:00:14.0-usb-0:4:1.0` and Q by
`pci-0000:00:14.0-usb-0:1:1.0`. Latest user report establishes crossed physical
labels P→Y and Q→X. Both unique target fingerprints remain UNKNOWN_TARGET;
no SIB was received and no SIGROW/REVID read was possible. Physical labels
come from the user, not tty aliases or duplicate USB serial0001.

Current host discovery uniquely resolves P to bus3/port4/device21, Q to
bus3/port1/device22. Current ttyUSB0/ttyUSB1 are locators. Stable by-path and
sysfs identities are in post_swap_inventory.csv and the worker evidence.
fuser/lsof listed no owner before and after batches. Exactly the two existing
workers were reused, each accessing only its path. Each CLI probe exclusively
opened, captured and closed its port. No terminal or hidden monitor was left.

Inherited92 host tests passed. New tests first produced7 missing-gate failures
and6 passing existing behaviors; after minimal interpretation-only code,
105 tests passed. Probe/transport code,8E2 framing,38400 nominal baud,
300-baud BREAKs and1.0s timeout were unchanged. No retries hide failures.

POST-001 hypothesis: an unchanged crossed screen can distinguish an FC1 path
association from target association, or reveal shared/non-stationary state.
The already-completed target assignment was the intervention; no new physical
variable was changed by the agents.30 strict SIB attempts ran per path.
Exact commands, exits, raw bytes and timing/hashes were preserved. P captured
separate stdout/stderr. Q retained the tool's combined output stream; stdout
and stderr cannot be separated retrospectively. This capture limitation is
recorded rather than silently repaired by rerunning the changed state.
Full experiment design and stopping rule are in POST_SWAP_PLAN.md.

Kernel journal visibility is limited and dmesg access denied. Therefore USB
error correlation is NOT_CAPTURED, not evidence of clean USB. USBMON was not
started: stage-aware restoration has higher value before decomposing the
external path. No target power/reference or signal waveform was measured.

The swap may also have reseated contacts or power-cycled devices. USB unplug
history, exact swap time, power-off duration, power-on sequence and current
MCU-local voltage remain UNKNOWN. The optional user history question is
pending. No agent power cycle, reconnect, rewiring or restoration occurred.

## Result

| Crossed pairing | N | SIB pass/fail | Success rate / Wilson95 | Failure stages | Median/p95 latency,ms |
|---|---:|---:|---|---|---|
| P+Y |30|0/30|0%;0–11.352%|LOCAL_ECHO1;UPDI_CONTROL_RESPONSE29|1145.145/1149.716|
| Q+X |30|0/30|0%;0–11.352%|LOCAL_ECHO30|1061.754/1063.539|
| Restored P+X |0|NOT_MEASURED|NOT_APPLICABLE|NOT_MEASURED|NOT_APPLICABLE|
| Restored Q+Y |0|NOT_MEASURED|NOT_APPLICABLE|NOT_MEASURED|NOT_APPLICABLE|

P attempt1 transmitted00 but observed80 on BREAK1: XOR80, Hamming distance1.
BREAK2 and SIB were NOT_REACHED in that attempt, not empty response events.
The other29 attempts each had exact BREAK1, BREAK2 and55e6 SIB-command echoes,
then an empty32-byte requested target response. P echo frames:87 EXACT,
1 CORRUPT. BREAK1 corruption rate1/30=3.333%, Wilson95 0.591–16.671%.

Q had24 BREAK1 empty echoes and6 BREAK2 empty echoes after exact BREAK1.
No Q SIB command was sent. Q echo frames:6 EXACT,30 EMPTY. FC1 rate30/30=100%,
Wilson95 88.648–100%. The stage-specific FC1 rate delta Q minus P is96.667
percentage points; this is a descriptive path association, not a measured
electrical mechanism. Both complete-SIB failure rates are100% (Wilson95
88.648–100%), but they do not represent the same boundary.

Wilson intervals use z=1.96 and describe observed proportions. Consecutive
samples may share state; these are not probabilities of hypotheses. Echo
latencies and write/read timestamps are preserved per frame; aggregate
latencies above cover complete attempts, including response timeout.

**Narrowest current conclusion:** LEVEL1 protocol boundaries are established.
FC1 remains associated with Q across the user-labeled crossed assignment
(SUPPORTED path association; evidence score1 for stage observation,N=30 per
path,0 restoration cycles). P has a separate predominant SIB target-response
failure, consistent with its latest PRE state. Full SIB result is SHARED_FAILURE
with DIFFERENT_STAGES; a shared physical cause is not established. Pure
target-Y-following FC1 is disfavored by this screen. External-path locality,
adapter×target interaction, number of physical faults and component mechanism
remain UNRESOLVED. Candidate-specific component scores remain0.

The41-row focused table retains33 BLOCKED physical candidates and8 UNRESOLVED
guards. No individual physical hypothesis is promoted merely because a broad
path prediction fits. Master168 statuses remain112 BLOCKED,48 UNRESOLVED,
8 SUPPORTED;0 PROVEN,0 STRONGLY_SUPPORTED,0 DISFAVORED,0 FALSIFIED. Versioned
post-swap status/evidence preserves all168 IDs; inherited files are unchanged.
The separate proof table contains2 SUPPORTED observations/path patterns,
1 DISFAVORED pure target-following pattern and1 UNRESOLVED intervention theory.
These four proof rows are not additions to the168-hypothesis inventory.

No100-attempt expansion was selected: both paths failed all30 full SIB
attempts, the latest PRE was already non-stationary, and repeating zeros
cannot control target power/reseat state. Control, ACC, identity/fuse/firmware
reads are gated on lower-layer reliability. No control test is implied by a
failed SIB attach. Flash/fuse/BOD/erase/repair actions in this epoch:0 each.

### Required answers

| Question | Answer |
|---|---|
| Did FC1 follow the target? | NO in this screen's simple target-following prediction; A/B/A ownership UNKNOWN. |
| Did FC1 follow the external path? | PARTIAL: Q30/30 versusP1/30; restoration and confound control required. |
| Did reconnect/reseat alone alter failure? | UNKNOWN; latest PRE was already non-stationary and power history is unknown. |
| Adapter×target interaction? | UNKNOWN; no stationary complete2×2 matrix. |
| Which BREAK failed? | BOTH across Q attempts:24 BREAK1,6 BREAK2. P1 BREAK1 corrupt. |
| Kernel USB errors correlated? | NOT_CAPTURED; limited journal/dmesg access. |
| Board-level locality proven? | NO. |
| Adapter-path locality proven? | NO. |
| Component-level root cause proven? | NO. |
| Physical measurement still required? | YES for electrical component distinctions; restoration is the next experimental gate. |
| One next smallest discriminator? | Controlled original-pairing restoration, followed by30 SIB attempts per path with the same strict probe. |

Crossed evidence has been persisted and independently checked:60/60 new raw
hashes valid,277 unique mapped event IDs,60 unique attempt IDs,124 echo rows,
41/41 inherited report hashes unchanged. Full verification:105 host tests,
21 ledger/schema/identity checks,629/629 raw hashes and7350 unique mapped
event IDs pass. P's237 manifest entries and Q's30 raw hashes match their
saved manifests. Details are in post_swap_verification.csv.

After this checkpoint was verified, the user was asked for safe power-down
and restoration to P→X/Q→Y while retaining external bundles, followed by
power-on using the same procedure. No restoration completion has yet been
reported. Record
that power/reseat intervention explicitly; do not treat it as target-only
causality if those controls remain unknown.

If restoration or instrumentation is unavailable, the remaining precise
electrical discriminator is a simultaneous BREAK1/BREAK2 capture of CP2102
TX, shared UPDI at the adapter and target sides, MCU-local VDD/local GND and
adapter-to-MCU ground offset. Use low-capacitance probes, short ground paths,
≥20MS/s investigation floor and ≥100ms pre/post windows where practical.
Verify topology and scope grounding first. These are investigation settings,
not MCU limits. This would distinguish TX drive/return/contact/loading from
VDD/reference behavior; it cannot be replaced by kernel logs.

Sources and exact revisions are in POST_SWAP_SOURCES.md; inherited official
datasheet audit remains unchanged after the manufacturer PDF re-fetch matched
its SHA-256. No erratum or component defect is claimed causal.
