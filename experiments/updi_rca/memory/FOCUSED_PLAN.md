# Focused physical-layer RCA plan

> Execute the user-approved focused specification in this session. Coordinator owns code, CSVs, experiment choice and causal decisions; exactly the two existing workers perform separate read-only analyses.

**Epoch:** `RCA_PHY_01`

**Goal:** distinguish external SerialUPDI path, target UPDI network, power/reference, and interaction for the current BREAK/LOCAL_ECHO failure. Historical exact-echo/ACC misses remain a separate failure class.

## Inherited boundary and physical gate

Preserve the 509 inherited runs / 6,387 events and 40 continuation runs / 546 events. No crossed pairing has been measured. P and Q identify physical USB paths, not adapter silicon independently of port. X/Y are provisional connected-target labels with unknown fingerprints. The user previously reported crossover unsafe; a new request to investigate does not establish safe power isolation or connector orientation. No physical action or new probe may assume those facts.

## Execution

1. Read checkpoint, raw evidence, actual UPDI implementation and `PROMPT.md`; verify host baseline with `uv run --project experiments/updi_rca pytest -q experiments/updi_rca/tests`.
2. Reuse lane_a as External Path Investigator (H108–H112, H115–H116, H126–H130) and lane_b as Target Electrical Investigator (H017–H018, H035, H036–H053). They write only their named Markdown state and epoch-specific evidence subdirectories, do not open serial ports, and do not change shared source/reports.
3. Test first: extend identity coverage and add a small `physical.py` analysis module only where existing helpers are insufficient. Required behaviors: physical target labels persist across crossed pairing; snapshots are immutable; BREAK1/BREAK2 failures differ; echo failure gates higher layers; path/target effects remain distinct; interactions remain explicit; single recovery does not clear intermittency; proof requires repeated controlled failure movement and restoration. Observe expected RED before implementation, then GREEN and the full suite.
4. Audit primary sources and exact local topology. Record document revisions, guaranteed thresholds and recommended decoupling values only when verified. Distinguish reference wiring from the unverified actual harness/BOM.
5. Preflight without opening ports: capture stable udev/sysfs identity and ownership. Current power, harness topology, physical pairing continuity, charger/movement state and instrument availability must be known before a new hardware batch. If unsafe/unconfirmed, preserve the earlier short reproduction rather than spend another batch or imply a crossover.
6. Generate focused reports from hashed inherited/continuation sources: 33 primary candidates plus 8 methodology guards; per-attempt BREAK classification, echo taxonomy, metrics, unmeasured crossover cells, USB-observation limits, proof ledger and STAR report. Do not overwrite historical ledgers. Include per-hypothesis falsifiers as a separate column. No fresh physical evidence means no promoted component/domain conclusion.
7. Produce D2 source + SVG showing the shared-node physical model and causal gate, using existing Cool Classics theme 4. Show actual topology as unverified; target loading can affect local echo.
8. Verify tests, source hashes, preserved row counts/IDs, focused schemas/counts/statuses, diagram rendering, and write budget; refresh Graphify after code changes. Update concise Markdown state/decisions and handoff.

## Authorized experiment design (pending safe physical access)

- **Hypothesis:** failure follows either complete external path or target PCB assembly.
- **Prediction:** target-only crossover and restoration move the failure consistently with one entity, or reveal interaction/handling sensitivity.
- **Independent variable:** target PCB attached to each frozen external path.
- **Controlled variables:** USB port/cable/CP2102, bridge/resistor and adapter-side harness remain with P/Q; same software, baud, timeout and target firmware/fuses. No adapter-side jumper is swapped with the target.
- **Measurement:** preflight, N=20 original SIB synchronization attempts per lane, N=30 crossed screen per pairing, N=100 only when needed; exact BREAK1/BREAK2 TX/echo, later request reachability, monotonic timing, hashes, Wilson intervals, restoration/A-B-A.
- **Pass criterion:** repeated controlled movement/restoration isolates a path or target domain; component proof requires its own one-variable intervention or direct discriminating measurement.
- **Fail criterion:** ambiguous topology, unsafe isolation, unequal conditions, changed multiple variables or unresolved identity invalidates physical attribution.
- **Interpretation:** no crossed observations means only LEVEL 1 BREAK/LOCAL_ECHO is established. If physical access stays unavailable, select BLOCKED and specify a qualified bench capture at the first/second 300-baud BREAK.

## Safety and deliverables

New flash writes=0, fuse writes=0, chip erases=0, BOD changes=0. No repair before proof. All handwritten files stay under `experiments/updi_rca/`; raw logs may remain logs, structured evidence is CSV, persistent state is Markdown. Required reports: focused hypotheses, crossover matrix, echo distribution, USB correlation, proof, metrics, focused STAR; required Markdown worker/state/decision files.
