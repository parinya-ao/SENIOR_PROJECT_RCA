# AVR128DA28 Dual-Board UPDI Root-Cause Investigation Agent Prompt

## Mission

You are the lead embedded-debugging agent for a **single isolated investigation**: determine why one AVR128DA28 target board shows intermittent UPDI/OCD/virtual-UART failures while another board can work under otherwise equivalent conditions.

Treat this as an evidence-driven root-cause investigation, not as a "make the error disappear" task.

The user explicitly authorizes:
- repository inspection,
- local shell/tool execution,
- internet research,
- creation of isolated diagnostic Python/C code,
- controlled read-only probing,
- controlled application reflashing when evidence justifies it,
- exactly **two high-quality subagents**,
- long-running/repeated test matrices,
- CSV/Markdown evidence/report generation.

The user does **not** want unrelated project work touched.

The user wants KISS/YAGNI/Occam/Gall's Law/Chesterton's Fence/Rule of Least Power:
- preserve essential complexity,
- remove accidental complexity,
- one variable at a time,
- boring/proven tools,
- evidence before intervention,
- smallest sufficient test,
- no speculative refactors.

---

# 0. Activate the investigation as an evidence-based Goal

If the environment supports Codex Goals, set a Goal equivalent to:

> `/goal Isolate the AVR128DA28 intermittent UPDI/OCD failure to the narrowest defensible root-cause class, verified by reproducible dual-board experiments, raw logs, automated Python tests, controlled target firmware, and an evidence ledger, while preserving production project behavior and avoiding unnecessary flash/fuse writes. Use exactly two device-lane subagents. Continue until the evidence supports a root-cause classification or the remaining hypotheses require unavailable physical instrumentation. If blocked, report exactly what measurement would distinguish the remaining hypotheses.`

The Goal is complete only when evidence says it is complete.

Do not mark success because a board "worked once."

---

# 1. Required Superpowers workflow

Use the installed Superpowers skills when available.

Required order/purpose:

1. `using-superpowers`
2. `systematic-debugging`
3. `brainstorming`
   - Treat this prompt as an already-approved specification.
   - Do not start an approval conversation unless a destructive action outside this prompt becomes necessary.
4. `writing-plans`
   - Save the plan inside the isolated RCA directory defined below.
5. `test-driven-development`
   - Host automation/classification code must be developed test-first.
6. `dispatching-parallel-agents`
   - Spawn **exactly two** lane workers, no more.
7. `verification-before-completion`
   - Required before any final root-cause claim.

Hard debugging law:

> NO FIXES BEFORE ROOT-CAUSE INVESTIGATION.

Do not change BOD, timeout, baud, fuses, retries, or UPDI implementation merely to make the symptom disappear.

---

# 2. Current system context

Known platform:

- MCU: AVR128DA28
- Two physical AVR128DA28 boards are available.
- Two CP2102/SerialUPDI paths may be connected simultaneously.
- Linux host.
- PlatformIO `atmelmegaavr`
- DxCore 1.6.2
- avr-gcc 7.3.0
- avrdude 8.1.0
- Python via `uv`
- virtual UPDI UART implementation based on `streef/upditerm`
- investigation baud of particular interest: 38400
- historical `/dev/ttyUSB0` and `/dev/ttyUSB1` names are **not identities** and may swap.

Important observed failure classes include:

1. Full flash upload/readback can succeed:
   - 826 bytes written
   - 826 bytes read
   - flash verified

2. UPDI initialization can fail:
   - `UPDI link initialization failed`

3. UPDI command local echo can corrupt or truncate:
   - sent `55 85`
   - expected echo `55 85`
   - observed examples include `95 e1`, `80`, or empty

4. Echo may be correct but target response/ACK can be absent:
   - STS ACK missing
   - LDS/LDCS response missing

5. The problematic target can emit one or many `H` bytes and then fail.

6. A working target has demonstrated continuous virtual-UART output such as:
   - `HEYYY fuckkkk`
   - repeated normally for multiple messages.

7. Earlier investigation found an important state-dependent pattern:
   - control/SIB access can remain available,
   - data/system-domain access becomes less reliable while CPU is running,
   - stopped/programming-held access can be substantially more reliable.

8. Historical reset investigation observed BORF, but BORF alone must **not** be treated as proof of a new brown-out event. A persistent reset flag without an independently observed new boot/reset is not enough.

9. The user currently suspects that swapping the **target board** can change behavior while the rest of the external chain is unchanged. This must be validated rigorously rather than accepted as a conclusion.

---

# 3. Critical reference behavior to verify from primary sources

Before coding, research and record current authoritative sources in:

`experiments/updi_rca/memory/SOURCES.md`

Source priority:

1. Current Microchip AVR128DA28/32/48/64(S) data sheet, DS40002183.
2. Current AVR128DA silicon errata, DS80000882.
3. Upstream `streef/upditerm`, especially the pinned/current version actually vendored by the project.
4. Linux kernel USB documentation, especially usbmon and USB error codes.
5. pyserial/CP210x documentation only where needed.
6. Blogs/forums only as secondary evidence after primary sources.

Verify, do not blindly assume from this prompt:

- exact AVR128DA28 UPDI architecture and register meanings,
- exact RSTFR bits for this device,
- exact BOD fuse meanings for this device,
- exact REVID mapping,
- exact signature-row/device-serial access method,
- exact UPDI control/status bits,
- exact current data-sheet hardware recommendations.

Known upstream `upditerm` behavior that should be checked against the vendored code:
- pyserial uses even parity and two stop bits for UPDI;
- half-duplex send expects the same transmitted bytes to echo back;
- connection initialization sends BREAKs and configures UPDI;
- virtual UART uses GPR/GPIOR addresses around `0x1e/0x1f`;
- target-to-host virtual UART uses OCD message state;
- host polling distinguishes `OCD_STOPPED` and an OCD-message-valid state.

Do not import register names or meanings from a different AVR family without proving they match AVR128DA28.

---

# 4. Hard safety and scope constraints

## 4.1 Repository scope

Create a dedicated investigation project only:

`experiments/updi_rca/`

Do **not** refactor production FOTA code.
Do **not** rename existing production libraries.
Do **not** modify protocol code unrelated to this RCA.
Do **not** modify upstream/vendored `third_party/upditerm` unless:
1. a reproducible upstream defect is proven,
2. a failing test exists first,
3. the change is isolated and documented.

Prefer wrapping/invoking existing code over reimplementing UPDI.

## 4.2 Flash/fuse safety

Default mode is read-only.

Do not:
- lower BOD,
- disable BOD,
- use avrdude `-F`,
- change fuses casually,
- chip erase casually,
- alter lock bits,
- erase USERROW/EEPROM,
- rewrite flash repeatedly as a diagnostic loop.

The AVR128DA A7 errata reports reduced Flash endurance. Maintain an explicit flash-write budget.

If firmware identity between boards cannot be proven, a controlled diagnostic reflash is allowed:

1. Read/snapshot current metadata first.
2. Build exactly one diagnostic image artifact.
3. SHA-256 the exact image.
4. Flash the **same artifact bytes** to each target.
5. Verify readback.
6. Log one flash event per target.
7. Do not rebuild separately between boards.
8. Preserve fuses/USERROW/EEPROM unless a later, explicit hypothesis requires otherwise.

Default RCA flash budget:
- application reflashes per board: maximum 3 unless a written evidence-based justification is added to `memory/DECISIONS.md`.
- fuse writes: 0 by default.
- chip erases: 0 by default.

## 4.3 Physical-action policy

Do everything possible in software first.

If a physical swap is eventually necessary, request **one** precise physical action at a time, for example:

> "Move Board A from Adapter Path X to Adapter Path Y; change nothing else."

Never ask the user to change board + cable + jumper + adapter simultaneously.

---

# 5. Two-subagent architecture: exactly two workers

Spawn **exactly two** subagents.

No third debugging subagent.
No swarm.
No reviewer subagent.
The parent/coordinator performs integration, coding, scoring, and final review.

## Lane Worker A

Owns one physical connection lane.

Responsibilities:
- monitor only its assigned current device,
- capture raw evidence,
- execute coordinator-approved probe batches,
- detect disconnect/re-enumeration,
- re-resolve identity after any tty rename,
- never edit shared source or shared CSV files.

Writes only:
- `evidence/raw/<run_id>/lane_a/*`
- `memory/LANE_A.md`

## Lane Worker B

Same contract, but:
- `evidence/raw/<run_id>/lane_b/*`
- `memory/LANE_B.md`

## Coordinator

The parent agent:
- owns hypothesis logic,
- owns source code,
- owns test plan,
- owns shared reports,
- compares A vs B,
- decides the next smallest experiment,
- is the only writer to shared CSV reports.

## Port contention rule

A worker must not keep a serial port open merely to "watch" it.

Each probe:
1. resolve device,
2. acquire its lane lock,
3. open,
4. perform bounded probe,
5. close,
6. release lock,
7. write result.

Do not leave a background terminal holding a port while avrdude or another probe needs it.

---

# 6. Device identity: never trust ttyUSB number

`/dev/ttyUSB0` and `/dev/ttyUSB1` are ephemeral labels.

Build a device identity resolver first.

Collect for every observed serial port:

- current tty path,
- `/dev/serial/by-id` entry if unique,
- `/dev/serial/by-path`,
- `udevadm` `ID_PATH`,
- sysfs device path,
- USB bus/device address,
- VID/PID,
- CP2102 serial if present,
- USB manufacturer/product strings,
- UPDI SIB,
- AVR device signature,
- REVID,
- target unique serial/signature-row identity if the exact device documentation supports safe readout,
- firmware hash if readable,
- fuse snapshot hash.

Never identify a board using CP2102 serial alone because clones/adapters can share serial strings.

Create a target fingerprint using multiple independent fields.

Suggested model:

`BoardIdentity = {target_signature, target_serial_if_available, revid, sib}`

`AdapterIdentity = {vid, pid, usb_serial, id_path, sysfs_path}`

`ConnectionIdentity = {BoardIdentity, AdapterIdentity, current_tty}`

If target is unreachable, mark target identity as `UNKNOWN_TARGET`; do not silently infer it from tty number.

If ports swap:
- preserve the board ID,
- update only current connection mapping.

---

# 7. Isolated project structure

Create only what is necessary:

```text
experiments/updi_rca/
├── README.md
├── pyproject.toml
├── src/
│   └── updi_rca/
│       ├── __init__.py
│       ├── cli.py
│       ├── identity.py
│       ├── probes.py
│       ├── events.py
│       ├── classify.py
│       ├── metrics.py
│       ├── runner.py
│       └── reporting.py
├── target/
│   ├── README.md
│   ├── main.cpp
│   ├── rca_probe.c
│   └── rca_probe.h
├── tests/
│   ├── fixtures/
│   │   ├── good/
│   │   ├── bad/
│   │   └── synthetic/
│   ├── test_identity.py
│   ├── test_event_parser.py
│   ├── test_classifier.py
│   ├── test_metrics.py
│   └── test_reporting.py
├── config/
│   ├── hypotheses_seed.csv
│   └── test_matrix.csv
├── memory/
│   ├── CURRENT_STATE.md
│   ├── DECISIONS.md
│   ├── EVIDENCE_LOG.md
│   ├── SOURCES.md
│   ├── PLAN.md
│   ├── LANE_A.md
│   ├── LANE_B.md
│   └── HANDOFF.md
├── evidence/
│   └── raw/
└── reports/
    ├── device_inventory.csv
    ├── runs.csv
    ├── events.csv
    ├── hypothesis_status.csv
    ├── pairwise_comparison.csv
    ├── fuse_compare.csv
    ├── flash_budget.csv
    ├── root_cause_ranking.csv
    └── RCA_SUMMARY.md
```

KISS rule:
- do not add a database,
- do not add a web UI,
- do not add asyncio unless proven necessary,
- do not add pandas unless the standard library is insufficient,
- use `csv`, `dataclasses`, `enum`, `statistics`, `subprocess`, `pathlib`, `time`, and pyserial where appropriate.

---

# 8. Persistent memory policy

Investigation memory must be Markdown only.

No JSON memory database.
No hidden state that is required to resume work.

## `memory/CURRENT_STATE.md`

Keep short and overwrite/update after each test batch:

```markdown
# Current State
Updated: <UTC/local timestamp>

## Known facts
- ...

## Current leading hypotheses
1. Hxxx — evidence score N
2. ...

## Falsified / strongly disfavored
- ...

## Last completed experiment
- ...

## Next smallest discriminating experiment
- ...

## Safety state
- flash writes Board A: N
- flash writes Board B: N
- fuse writes: 0
```

## `memory/EVIDENCE_LOG.md`

Append-only chronological evidence.

Every entry:
- timestamp,
- run_id,
- board identity,
- adapter identity,
- command,
- exact result,
- interpretation,
- what it supports,
- what it weakens,
- uncertainty.

## `memory/DECISIONS.md`

Record only decisions, not private chain-of-thought.

For every decision:
- decision,
- evidence,
- rejected alternatives,
- trade-off,
- next verification.

Do **not** attempt to expose hidden/private reasoning.
Provide auditable engineering rationale instead.

---

# 9. CSV report schemas

## `device_inventory.csv`

Columns:

```text
timestamp,run_id,lane,board_id,current_tty,by_id,by_path,id_path,sysfs_path,usb_bus,usb_device,vid,pid,adapter_serial,sib,device_signature,revid,target_serial,firmware_sha256,fuse_sha256,status,notes
```

## `runs.csv`

```text
timestamp,run_id,test_id,lane,board_id,adapter_id,current_tty,baud,cpu_state,firmware_sha256,attempt,result,latency_ms,failure_stage,error_type,expected_hex,observed_hex,rstfr_raw,ocd_status_raw,sys_status_raw,kernel_usb_error,source_log
```

## `events.csv`

```text
timestamp_monotonic,run_id,event_id,lane,board_id,stage,direction,operation,address,tx_hex,echo_hex,response_hex,expected_len,actual_len,status_raw,errno,classification,raw_log_path
```

## `hypothesis_status.csv`

```text
hypothesis_id,domain,cause,status,evidence_score,confidence_label,predictions,discriminator,evidence_for,evidence_against,next_test,requires_flash,requires_physical_measurement,last_updated
```

Important:
- `evidence_score` is a deterministic prioritization score, **not a probability**.
- `confidence_label` must be one of:
  - PROVEN
  - STRONGLY_SUPPORTED
  - SUPPORTED
  - UNRESOLVED
  - DISFAVORED
  - FALSIFIED
  - BLOCKED

## `pairwise_comparison.csv`

```text
test_id,metric,board_a_value,board_b_value,absolute_delta,relative_delta,interpretation,n_a,n_b
```

## `flash_budget.csv`

```text
timestamp,board_id,write_number,reason,image_sha256,verify_result,fuses_changed,userrow_changed,eeprom_changed,approved_by_rule,notes
```

## `root_cause_ranking.csv`

```text
rank,hypothesis_id,domain,cause,status,evidence_score,decisive_evidence,contrary_evidence,remaining_uncertainty,next_required_measurement
```

---

# 10. Failure-stage taxonomy

Every failure must be classified at the lowest proven layer.

Use stages such as:

1. `PORT_DISCOVERY`
2. `SERIAL_OPEN`
3. `USB_HOST`
4. `HOST_TX`
5. `LOCAL_ECHO`
6. `UPDI_PHY_CONTROL`
7. `UPDI_CONTROL_RESPONSE`
8. `ACC_ACK`
9. `ACC_DATA_RESPONSE`
10. `OCD_STATUS`
11. `OCD_MESSAGE`
12. `TARGET_RUNTIME`
13. `TARGET_RESET`
14. `FLASH_PROGRAM`
15. `FLASH_VERIFY`

Examples:

- `sent 55 85; echo 80`:
  - failure stage = `LOCAL_ECHO`
  - do not blame ACC/system bus yet.

- echo exactly matches, but STS ACK is absent:
  - failure stage = `ACC_ACK` or target-response path.

- SIB/LDCS stable while running LDS/STS fails:
  - control path and data/system path differ; preserve that distinction.

- avrdude cannot initialize UPDI:
  - do not collapse it into "firmware failure."

---

# 11. TDD requirements for host automation

Write tests first.

Minimum unit tests:

## Identity tests

1. maps two tty devices into stable connection identities.
2. handles ttyUSB0/ttyUSB1 swap without swapping board identity.
3. handles duplicate CP2102 serial values.
4. marks target identity unknown when UPDI is unreachable.
5. updates connection mapping after reconnect.

## Parser/event tests

Fixtures must include real failure shapes:

1. successful flash verify.
2. `UPDI link initialization failed`.
3. missing LDCS response.
4. missing STS ACK.
5. local echo corruption:
   - expected `55 85`
   - observed `95 e1`
6. local echo truncation:
   - expected `55 85`
   - observed `80`
7. local echo empty.
8. successful repeated `HEYYY...`.
9. missing tty device.
10. kernel USB `-EPROTO`, `-EILSEQ`, disconnect, and clean cases.

## Classifier tests

The classifier must not overclaim.

Required tests:

1. one isolated timeout can never produce `PROVEN`.
2. repeated board-only A/B/A difference strongly supports board-local classes.
3. BORF without a new boot marker is **not** proof of a fresh brown-out.
4. exact echo + missing ACK differs from corrupt echo.
5. stopped-state success + running-state failure increases power/reset/system-domain hypotheses.
6. identical fuse snapshots reduce fuse/config hypotheses.
7. identical firmware SHA + behavior difference reduces generic firmware hypotheses.
8. correlated kernel USB `EPROTO/EILSEQ` raises host/adapter/cable hypotheses.
9. clean USB trace during a target-response failure reduces generic USB hypotheses.
10. no-output target firmware plus repeated OCD-message-valid events raises OCD/target-state hypotheses and triggers a dedicated investigation, not an immediate fix.

## Metrics tests

Calculate at minimum:
- attempts,
- successes,
- failures,
- pass rate,
- failure rate,
- median latency,
- p95 latency,
- 95% Wilson interval for success proportion.

Use standard library math; no scipy required.

## Integration tests without hardware

Use pseudo-terminals or synthetic subprocess fixtures to prove:
- echo parser,
- short-read detection,
- reconnect handling,
- tty renaming,
- timeout handling,
- raw evidence persistence.

Hardware tests must be marked separately, e.g. `pytest -m hardware`.

Destructive/flash tests must require an explicit marker/env flag.

---

# 12. Root-cause scoring rules

Implement simple explicit weights.
Do not implement machine learning.

Example evidence weights; tune only with a documented reason:

```text
Evidence: same external chain, only target board changes, failure follows board
  +8 board-local A/B/C/D/E/H
  -6 generic host/software G

Evidence: TX != local echo
  +6 physical/electrical/adapter/line B/G/H
  -4 pure ACC arbitration F98
  -3 pure application bug F102

Evidence: echo exact, ACK/response missing
  +4 target response / UPDI endpoint / reset / power
  +2 ACC/system path
  0  USB until kernel evidence exists

Evidence: SIB/control 100% stable, data-space fails only while RUNNING
  +7 power/reset/system-domain A/C/D/F
  -5 generic serial/baud/host issue

Evidence: stopped-state 100% stable, running-state degraded
  +8 power/reset/system-domain
  +4 CPU-load-sensitive board fault

Evidence: new boot marker + BORF
  +8 BOD/power hypothesis

Evidence: BORF persists but boot marker did not change
  +1 historical reset state only
  MUST NOT classify a fresh brown-out

Evidence: fuses differ
  +7 fuse/config E

Evidence: fuses identical
  -6 fuse/config E

Evidence: exact same firmware image hash + exact verify on both
  -6 generic firmware mismatch F105/F106

Evidence: usbmon shows correlated EPROTO/EILSEQ
  +7 USB/adapter/cable G

Evidence: usbmon clean and kernel delivered exact host echo during target timeout
  -5 generic USB data corruption
  +3 target-side response/power/UPDI

Evidence: silent firmware, but OCDMV repeatedly reasserts
  +6 OCD state / target debug-message generation / silicon-state hypothesis
```

A score ranks tests.
A score does not prove causality.

---

# 13. Statistical test policy

Default read-only matrix:
- 100 attempts per board per primary condition.
- no flash wear from read-only probes.

Do not hide intermittency by reporting only final state.

For every condition report:
- N,
- success count,
- failure count,
- success percentage,
- Wilson 95% interval,
- failure-stage distribution.

If a condition is extremely slow, start at 30 attempts, then expand if the result is ambiguous.

Use monotonic timestamps for duration/ordering.

No arbitrary sleeps as a "fix."
A delay may be introduced only as a controlled independent variable in an experiment.

---

# 14. Phase-by-phase investigation

## Phase 0 — Freeze and inventory

Before any change:

1. Record git status/commit.
2. Record tool versions.
3. Discover both serial adapters.
4. Resolve identities.
5. Save udev/sysfs mapping.
6. Read SIB if possible.
7. Read signature/REVID safely.
8. Snapshot fuse values read-only.
9. Read firmware identity/hash if practical without destructive operation.
10. Record current kernel USB power-management settings read-only.
11. Record existing PlatformIO build artifact SHA-256.
12. Write `memory/CURRENT_STATE.md`.

No fixes.

## Phase 1 — Baseline dual-board matrix at 38400

For each lane independently:

1. 100 SIB attempts.
2. 100 selected control-space reads.
3. record exact echoes.
4. record exact response bytes.
5. classify failure stage.
6. record latency.
7. close port after each bounded attempt.

Compare boards.

Do not expand baud matrix until 38400 baseline is understood.

## Phase 2 — Control vs data-space boundary

Use the smallest safe register set verified from the AVR128DA documentation.

Compare:

- SIB/control commands,
- ASI status reads,
- safe data-space reads such as selected read-only reset/clock/status registers,
- GPR scratch access only when reversible.

Run in:
1. CPU running state,
2. CPU stopped/OCD-held state,
3. programming-held state where available.

The purpose is to answer:

> Does reliability depend on system-domain execution state?

Preserve raw status values, even for undocumented/reserved bits.
Do not assign cross-family names to undocumented bits.

## Phase 3 — Minimal reversible data-space write

Only if Phase 2 needs it.

Use one safe scratch byte such as a GPR after confirming address/semantics.

Protocol:

1. read original,
2. write known marker such as `0x5A`,
3. read back,
4. restore original,
5. read back restored value.

Never use a production state register as a scratch register.

## Phase 4 — Firmware equivalence

First try to prove both boards run the same bytes without writing.

If not provable:
- build one diagnostic image,
- hash it once,
- flash exact same artifact to each board,
- verify,
- update flash budget.

Do not change fuses.

## Phase 5 — Diagnostic target firmware

Keep target code deliberately tiny.

Use the existing proven virtual-UART implementation rather than inventing a new one.

Create two test modes in one isolated diagnostic implementation if possible:

### Mode SILENT

- CPU runs.
- virtual UART enabled logic may be present.
- target intentionally sends **zero OCD message bytes**.

Purpose:
- determine whether host sees OCD message activity when target should be silent.

### Mode HEARTBEAT

Emit a small machine-readable frame at a slow rate, e.g. every 2 seconds.

Prefer a fixed binary frame rather than stdio:

```text
MAGIC | boot_id | sequence | reset_flags
```

Example 4-byte concept:
- `0xA5`
- boot identifier
- sequence counter
- reset-cause snapshot

If a checksum is needed for resynchronization, use a trivial XOR; do not add a protocol stack.

Requirements:
- no malloc,
- no dynamic allocation,
- no printf unless size/cost is justified,
- no unrelated peripherals,
- no radio,
- no FOTA,
- no sensor stack.

### Optional LOAD phase

Only after SILENT and HEARTBEAT are understood.

Add deterministic CPU activity without unrelated peripherals to test whether CPU switching/load correlates with failure.

Do not add this in the first implementation if HEARTBEAT already discriminates the issue.

## Phase 6 — Reset evidence

Capture reset cause as early as safely possible.

Need to distinguish:
- stale/persistent RSTFR flag,
- genuine new boot/reset.

Implement a boot marker/counter in a minimal safe way.
If using `.noinit`, document exactly what it proves and what it cannot prove across power loss.

A fresh BORF plus an independently observed new boot event is stronger evidence than BORF alone.

## Phase 7 — "RX always active" / OCD message investigation

This is a priority special investigation.

Do **not** use the phrase "RX stuck" until the exact bit/state is defined.

Separate these concepts:

1. Host-to-target virtual UART RX buffer:
   - GPR/UART_FLAGS `FLAG_RX`

2. Target-to-host debug message availability:
   - UPDI OCD-message-valid status (`OCDMV` in upstream upditerm terminology)

3. CPU stopped state:
   - `OCD_STOPPED`

4. Target-side OCD message status:
   - `SYSCFG_OCDMS` used by upstream target code
   - note that upstream comments describe this area as undocumented; treat accordingly.

Create a dedicated probe that logs raw values over time:

```text
timestamp
UART_FLAGS raw
FLAG_ENABLE
FLAG_RX
ASI_OCD_STATUS raw
OCD_STOPPED
OCDMV
ASI_SYS_STATUS raw
message byte if and only if valid
```

Experiment A:
- SILENT firmware.
- Observe for a bounded interval.
- Expected: no target-generated message stream.

Experiment B:
- HEARTBEAT firmware.
- Expected: OCD message events correspond to heartbeat frames.

If the problematic board shows continuously asserted/reappearing OCDMV under SILENT firmware while the good board does not:
- capture exact raw states,
- confirm read/clear semantics from source/docs,
- test stopped vs running state,
- do not immediately call it a silicon defect.

If `FLAG_RX` is stuck set without host sending data:
- prove this by logging host writes and GPR state,
- test whether the flag survives reset or reinitialization,
- compare exact firmware/fuse state.

## Phase 8 — Host/USB escalation only when evidence warrants it

Capture:
- `journalctl`/kernel USB events,
- usbmon,
- optional bounded `strace`.

Use these specifically when:
- local echo corrupts,
- serial read unexpectedly returns empty,
- device disconnects,
- kernel reports USB errors.

Correlate by monotonic timestamp.

Interpret Linux USB errors using kernel documentation, not guesswork.

Do not equate an old `-EPROTO` event with the current failure unless timestamps correlate.

## Phase 9 — Board-local hypothesis narrowing

If failure reliably follows a target board:

Prioritize:
1. board power/GND/decoupling,
2. board-side UPDI header/trace/solder/pad,
3. reset path,
4. AVR unit damage/marginality,
5. fuse/config difference,
6. PCB assembly/BOM differences.

Without a multimeter/scope/logic analyzer, software may only prove:
- board-local fault domain,
- state-dependent behavior,
- reset evidence,
- UPDI endpoint symptoms.

Do not claim "bad capacitor" without measurement or controlled component intervention.

## Phase 10 — Cross-over experiment if still ambiguous

If physically feasible and needed, use a 2x2 matrix:

```text
Adapter/Path A + Board A
Adapter/Path A + Board B
Adapter/Path B + Board A
Adapter/Path B + Board B
```

Change only one physical variable per transition.

If the failure follows Board B across both external paths, board-local causality becomes very strong.

If it follows Adapter/Path A instead, revisit external path hypotheses.

---

# 15. Python API expectations

Keep interfaces small and testable.

Example signatures:

```python
@dataclass(frozen=True)
class AdapterIdentity:
    vid: str
    pid: str
    usb_serial: str | None
    id_path: str
    sysfs_path: str

@dataclass(frozen=True)
class BoardIdentity:
    sib: str | None
    device_signature: str | None
    revid: str | None
    target_serial: str | None

@dataclass(frozen=True)
class ProbeResult:
    success: bool
    stage: str
    tx: bytes
    echo: bytes
    response: bytes
    latency_ms: float
    error_type: str | None
```

Suggested functions:

```python
discover_serial_ports() -> list[...]
resolve_connection(port: str) -> ...
run_sib_probe(connection, baud: int) -> ProbeResult
run_control_read(...) -> ProbeResult
run_data_read(...) -> ProbeResult
parse_upditerm_log(line: str) -> ...
classify_event(event) -> ...
wilson_interval(successes: int, total: int) -> tuple[float, float]
append_run_csv(...)
render_summary(...)
```

Do not build a framework.
Functions should have one job.

---

# 16. C target implementation expectations

Use the current project toolchain and the least-invasive build path.

Because the project currently uses DxCore/Arduino, it is acceptable to use:
- a tiny `main.cpp` framework adapter,
- a C diagnostic core in `rca_probe.c`.

The diagnostic logic itself should remain C/simple.

Do not rewrite clock startup unless the experiment specifically tests clock configuration.

Reuse the known `updi_uart` implementation.

Required target properties:

1. deterministic,
2. fixed-size state,
3. no heap,
4. no unrelated interrupts,
5. no radio/peripherals,
6. compile warnings enabled,
7. firmware SHA recorded,
8. size recorded,
9. same image used on both boards.

Before flashing hardware:
- compile,
- run any host-native unit tests possible,
- inspect generated size/map as needed.

---

# 17. Hypothesis inventory and evidence model

Seed all hypotheses below into `config/hypotheses_seed.csv`.

Every hypothesis must have:
- ID,
- domain,
- text,
- observable prediction,
- cheapest discriminator,
- requires instrument? yes/no,
- requires flash? yes/no,
- risk,
- evidence score,
- current status.

Never delete a hypothesis merely because it seems unlikely.
Mark it DISFAVORED/FALSIFIED with evidence.

## A. Power / GND ฝั่ง board

1. VDD solder joint (cold / crack / ไม่ติด)
2. GND solder joint (cold / crack / ไม่ติด)
3. VDD/GND pin ของ AVR ตัวใดตัวหนึ่งไม่ contact
4. Decoupling cap 100 nF หาย
5. Decoupling cap ค่าผิด / package ผิด
6. MLCC แตก (flex crack)
7. Cap solder joint เย็น
8. Cap อยู่ไกล pin เกินไป (trace ยาว, inductance สูง)
9. MLCC DC-bias derating (ค่าจริงต่ำกว่าที่ระบุ)
10. Bulk cap หาย / เสื่อม / ESR สูง
11. Regulator dropout / output droop ตอน load สูง
12. Regulator oscillation (cap ผิด ESR ผิด)
13. Regulator thermal shutdown / over-current limit
14. Regulator output ผิดค่า (feedback resistor ผิด)
15. Regulator ตัวเสีย / marginal
16. Input supply ไม่พอ (จ่ายจาก adapter 3V3 ที่ current จำกัด)
17. VDD/GND ผ่าน jumper wire → contact resistance สูง
18. GND ระหว่าง adapter กับ board ต่อไม่ดี
19. Ground loop / GND หลายเส้นทาง
20. Ground bounce ใน PCB
21. Ground plane ขาด / slit ขวาง return path
22. Via ขาด / barrel crack
23. Trace VDD/GND บางเกิน / resistance สูง
24. Ripple / noise บน VDD
25. Rail rise time ช้าเกิน (POR/BOD ไม่สะอาด)
26. Inrush current ตอน power-up
27. Power sequencing ผิด
28. Polyfuse / ferrite bead / diode / switch ในเส้น power มี resistance สูง
29. Reverse-protection diode drop มากเกิน
30. Battery (ถ้ามี) แรงดันต่ำ / internal resistance สูง
31. มี peripheral บน board ดึง current สูงหรือ short บางส่วน (radio, sensor, LED, level shifter)
32. Peripheral ตัวใดตัวหนึ่งเสีย ดึง rail ลง
33. Leakage path ระหว่าง VDD-GND (flux, ความชื้น, สิ่งสกปรก)
34. VDD ต่ำกว่า spec ของ clock ที่ใช้ (เช่น 24 MHz)
35. Voltage mismatch ระหว่าง adapter กับ board (3.3V vs 5V)

## B. UPDI path บน board

36. Header pin solder joint เย็น / แตก
37. Header pin ไม่ contact กับ jumper (oxidize, งอ, หลวม)
38. Jumper ต่อไม่แน่น (ต่อใหม่ทุกครั้ง contact ไม่เท่ากัน)
39. Trace UPDI ขาด / hairline crack
40. UPDI pad ของ AVR solder เย็น
41. UPDI pad bridge กับ pin ข้างเคียง
42. UPDI trace short กับ trace อื่น
43. Leakage บน UPDI line
44. Parasitic capacitance สูงบน UPDI line
45. มี pull-up / pull-down / series resistor บน board ที่ไม่ควรมี
46. มี ESD / TVS diode บน UPDI line ที่ leakage
47. มี component อื่นต่อกับ UPDI line (LED, sensor, connector)
48. Trace UPDI ยาว / ขนานกับ trace noisy (crosstalk)
49. UPDI pin เสียจาก ESD / overvoltage
50. Level บน UPDI line ไม่ตรง VDD ของ target
51. GND reference ของ UPDI ไม่นิ่ง
52. Resistor ใน chain หลวม / ค่าเปลี่ยน
53. UPDI line ได้รับ EMI / crosstalk จาก radio หรือ switching

## C. Reset / Watchdog / Reset cause

54. PF6/RESET pin floating
55. Pull-up reset หาย / ค่าผิด
56. Cap บน reset line ผิด
57. Reset button / สวิตช์ leakage
58. Reset line coupling noise
59. RSTPINCFG fuse ต่างกัน
60. WDT fuse ถูกเปิด
61. WDT timeout จาก firmware
62. Software reset (SWRF) จาก firmware
63. BOD reset (BORF)
64. POR reset (PORF)
65. UPDI reset (UPDIRF)
66. Firmware crash → reset loop
67. Brown-out → reset loop

## D. ตัว AVR chip

68. AVR unit นี้ defect ตั้งแต่โรงงาน
69. ESD damage
70. Overvoltage / reverse polarity เคยโดน
71. UPDI PHY เสียบางส่วน
72. Internal oscillator tolerance ต่างกัน
73. Oscillator ไม่ stable ตอน VDD ต่ำ / อุณหภูมิเปลี่ยน
74. Chip ปลอม / remark / lot ต่างกัน
75. Silicon revision ต่างกัน
76. Errata ที่ trigger ด้วย environment
77. Flash เสื่อม (endurance) / bit error
78. Flash เขียนไม่สมบูรณ์แต่ verify ผ่านผ่าน UPDI
79. Data retention ผิดปกติ
80. Pin อื่นของ chip เสียหรือ solder ไม่ดี (ไม่ใช่เฉพาะ UPDI/VDD/GND)
81. ถูก overheat ตอน solder / rework
82. Internal bond wire / pad damage
83. Chip ร้อนเกินระหว่างรัน

## E. Fuse / Config ที่อาจต่างกัน

84. BODCFG (level, mode ใน active/sleep, sample freq)
85. SYSCFG0 / SYSCFG1
86. WDTCFG
87. OSCCFG
88. TCD0CFG
89. BOOTEND / APPEND / CODESIZE
90. Lock bits
91. CRC-at-reset ตรวจ fail
92. USERROW / EEPROM content ต่างกัน
93. UPDI clock select (UPDICLKSEL) ต่างกัน
94. UPDI control bits (GTVAL, IBDLY, CCDETDIS, PARD ฯลฯ) ถูกตั้งค่าไม่เท่ากัน

## F. Firmware / Runtime behavior

95. Firmware เปลี่ยน clock / prescaler ระหว่างรัน
96. Firmware เข้า sleep mode
97. Firmware สั่ง peripheral ที่ทำให้ bus load สูง (DMA, event system, interrupt storm)
98. ACC access ชนกับ CPU/bus (bus arbitration timeout)
99. NVMCTRL busy ตอน ACC เข้าถึง
100. CCP-protected register เขียนไม่ผ่าน
101. Firmware อ่าน pin ที่ floating / peripheral ที่ไม่ได้ต่อ แล้ว behavior ต่างกัน
102. Stack overflow / undefined behavior / uninitialized memory
103. Interrupt vector / bootloader config ผิด
104. Firmwareพิมพ์ผ่าน virtual UART/OCD message ถี่เกินจน host อ่านไม่ทัน
105. Firmware version บน good board กับ bad board ไม่เหมือนกันจริง
106. Compile/link ต่างกันโดยไม่รู้ตัว
107. Firmware ไม่ได้ clear reset flag แล้วตีความผิด

## G. Adapter / Host / Software

108. CP2102 ตัวนี้ intermittent (unit-level)
109. CP2102 clone / ปลอม
110. Adapter TX drive strength ไม่พอเมื่อ load ของ bad board สูงกว่า
111. Adapter 3V3 sag เมื่อต่อ bad board
112. Resistor tolerance / contact
113. Baud rounding error ที่ 38400
114. UART format ผิด (parity even, 2 stop bits)
115. Echo handling ผิด (half-duplex RX/TX collision)
116. Timing race ระหว่างอ่าน echo กับ response
117. FIFO overrun / buffer flush ผิด
118. Timeout ของ upditerm สั้นเกินสำหรับ bad board
119. Retry / error recovery logic ใน upditerm
120. Double-break / reinit handling
121. Python scheduling jitter / GC / CPU load
122. USB latency timer
123. USB autosuspend / power management
124. Linux driver (cp210x) issue
125. Process อื่นจับ port (ModemManager, brltty ฯลฯ)
126. USB hub / port ต่างกัน
127. Laptop USB noise
128. Laptop charger เสียบ/ไม่เสียบ (common-mode noise)
129. Cable USB หลวม / เสื่อม / ถูกขยับ
130. ลำดับการ plug/unplug ต่างกัน
131. Session ก่อนหน้าทิ้ง state ค้างบน target (OCD / halt / reset state)
132. Target ไม่ได้ power-cycle ระหว่าง test

## H. PCB / Assembly / BOM

133. PCB revision ต่างกันระหว่าง good กับ bad
134. BOM ต่างกัน (component ต่างค่า ต่างยี่ห้อ)
135. Component ผิดค่า / ผิด package
136. Component ใส่กลับด้าน (diode, LED, polarized cap)
137. Component หาย (DNP ผิด) / 0Ω link หาย
138. Tombstoning
139. Solder paste ไม่พอ / void / head-in-pillow
140. Hand-solder เย็น
141. Solder bridge ที่มองไม่เห็น (ใต้ package)
142. Flux residue ทำ leakage / corrosion
143. Solder mask residue บน pad
144. PCB trace scratch / over-etch / hairline
145. Plated through-hole เสีย
146. Inner layer ขาด (ถ้า multilayer)
147. Bodge wire / modification หลวม
148. Crystal / external clock components บน board โหลด pin
149. Mechanical stress / board flex
150. Thermal cycling ทำ joint ร้าว
151. Board เคยเสียหายจาก experiment ก่อนหน้า (short, ต่อผิดขั้ว, 5V เข้า 3.3V line)
152. Board เคย contaminate (เหงื่อ, น้ำ, ฝุ่น)

## I. Environment

153. อุณหภูมิ (ร้อน / เย็น / warm-up drift)
154. ความชื้น / condensation
155. ESD จากมือ / เสื้อผ้า / โต๊ะ
156. EMI จาก phone, WiFi, motor, switching charger, radio บน board เอง
157. มือ/นิ้วใกล้ board (capacitive coupling)
158. Board วางบนพื้นผิวนำไฟฟ้า (โต๊ะเหล็ก, ถาด)
159. Vibration / การขยับสาย
160. Power line noise จากแหล่ง AC

## J. Methodology / การตีความผล

161. สลับ label good/bad
162. Good board ทดสอบจำนวนครั้งน้อยเกินไป (อาจ intermittent ด้วยแต่ rate ต่ำ)
163. เงื่อนไขทดสอบไม่เท่ากัน (เวลาหลัง power-up, อุณหภูมิ, ลำดับ test)
164. Log จากคนละ session / คนละ firmware build
165. Fuse / firmware / USERROW บน good board กับ bad board ไม่ได้เทียบกันจริง
166. Probe หรือสายวัดเพิ่ม load เข้าไปเอง
167. อาการหลายอย่างเกิดจากหลายสาเหตุพร้อมกัน (ไม่ใช่ root cause เดียว)
168. อาการบางอย่างที่เห็นเป็น artifact ของ tool (log format, retry ซ่อนความจริง)

---

# 18. Tests that specifically attack methodology errors 161–168

These are mandatory because they can invalidate the entire RCA.

1. Generate immutable `run_id`.
2. Record both board and adapter identity every test.
3. Record image SHA every test.
4. Record fuse SHA every test batch.
5. Record monotonic timestamp.
6. Preserve raw logs.
7. SHA-256 raw logs after each run.
8. Never combine results from different firmware hashes without labeling them.
9. Never compare a warmed board to a cold board without recording warm-up state.
10. Report test order.
11. Randomize or alternate board test order when practical to reduce time/environment bias.
12. Repeat the final winning discriminator A/B/A at least 3 cycles if non-destructive.

---

# 19. Evidence standards for root-cause claims

## PROVEN

Use only if either:

A. a single-variable intervention makes the failure follow that variable in repeated A/B/A tests, with at least 3 cycles and no contradictory evidence,

or

B. direct measurement proves a specification violation that causally matches the failure.

Example:
- Board B fails on both external chains;
- Board A passes on both;
- swapping back restores original outcomes;
- repeated 3 times.

## STRONGLY_SUPPORTED

- strong repeatable difference,
- one causal boundary isolated,
- but component-level measurement unavailable.

Example:
- fault follows target board,
- same firmware/fuses,
- same adapter path,
- stopped-state stable,
- running-state fails,
- reset evidence aligns,
- but VDD waveform cannot be measured.

## SUPPORTED

Prediction fits evidence but alternatives remain.

## DISFAVORED

Repeated predictions fail.

## FALSIFIED

A required prediction is contradicted by controlled evidence.

## BLOCKED

Needs unavailable physical instrumentation or a user physical action.

Never convert "most likely" into "proven."

---

# 20. Required experiments before blaming the board hardware

Before saying "bad board":

1. prove board identity is not mislabeled,
2. prove firmware hash equivalence,
3. compare fuse snapshots,
4. compare SIB/signature/revision,
5. show repeated outcome difference,
6. rule out tty renaming confusion,
7. correlate host USB errors,
8. distinguish echo corruption from missing target response.

Before saying "power/decoupling":

1. show state/load dependency or reset evidence,
2. show board-locality,
3. show host/UPDI transport alternatives weakened,
4. label component-level cause unresolved without analog measurement.

Before saying "UPDI pin/path":

1. show failures at LOCAL_ECHO/UPDI PHY even when CPU/system-domain state cannot explain them,
2. show failure follows target board,
3. compare stopped/running states,
4. compare external path if possible.

---

# 21. Current data-sheet/errata checks to include

Explicitly verify current AVR128DA28 documentation for:

1. recommended VDD decoupling network,
2. VDD slew-rate limits,
3. RESET connection recommendations,
4. UPDI connector recommendations,
5. operating voltage limits at target clock,
6. BOD threshold/mode fuse definitions,
7. reset-cause register semantics,
8. flash endurance erratum,
9. errata tied to silicon revision/date code,
10. BOD-related errata when UPDI is enabled.

Record exact document revision/date and source in `memory/SOURCES.md`.

---

# 22. Commands and execution style

Prefer reproducible commands through project scripts.

Examples of intended final user surface:

```bash
uv run pytest -q experiments/updi_rca/tests
uv run python -m updi_rca.cli inventory
uv run python -m updi_rca.cli baseline --attempts 100 --baud 38400
uv run python -m updi_rca.cli compare
uv run python -m updi_rca.cli report
```

Do not require the user to remember raw ad-hoc commands if the operation is repeated.

Every CLI command must:
- return nonzero on failure,
- create/append evidence,
- print the run_id,
- print resolved board identity,
- never silently continue after a port remap ambiguity.

---

# 23. Test selection algorithm

After every batch:

1. update facts,
2. update hypothesis scores,
3. identify top unresolved hypotheses,
4. find the **smallest test that maximally separates them**,
5. prefer read-only,
6. prefer no physical change,
7. prefer no flash,
8. execute one variable,
9. update evidence,
10. repeat.

Do not execute the entire 168-hypothesis matrix blindly.

The inventory is broad.
The actual test plan must shrink aggressively as evidence accumulates.

---

# 24. Required final outputs

Do not finish with only a chat summary.

Required files:

1. `reports/device_inventory.csv`
2. `reports/runs.csv`
3. `reports/events.csv`
4. `reports/hypothesis_status.csv`
5. `reports/pairwise_comparison.csv`
6. `reports/fuse_compare.csv`
7. `reports/flash_budget.csv`
8. `reports/root_cause_ranking.csv`
9. `reports/RCA_SUMMARY.md`
10. `memory/HANDOFF.md`

`RCA_SUMMARY.md` must include:

# Executive Result
- narrowest proven fault domain,
- what is not proven.

# STAR

## Situation
Use numbers:
- 2 boards,
- 2 lanes,
- N attempts,
- observed failure types.

## Task
- isolate 168 initial hypotheses into a defensible short list.

## Action
### Decision logic
- why each discriminator was chosen.

### Execution
- exact tests.

### Trade-offs
- why flash/fuse writes were minimized.

## Result
Hard metrics:
- pass/fail rate per board,
- echo error rate,
- ACK missing rate,
- stopped vs running rate,
- USB error count,
- reset count,
- number of hypotheses falsified/disfavored,
- final evidence score.

# Root-cause ranking
Top 5 only.

# Proven
Facts only.

# Strongly supported
Facts + inference clearly separated.

# Falsified/disfavored
List decisive evidence.

# Blocked
Exact unavailable measurement.

# Recommended next action
One smallest action.

Final user-facing summary should be in Thai and concise, but the files contain full detail.

---

# 25. Completion checklist

Do not mark complete until all applicable items are true:

- [ ] Exactly 2 subagents used; no unnecessary third agent.
- [ ] ttyUSB labels are not treated as identities.
- [ ] Board/adapter mapping is captured.
- [ ] Raw logs are preserved.
- [ ] Host parser/classifier tests pass.
- [ ] Real hardware matrix has numeric results.
- [ ] Good/bad board comparison uses equivalent conditions.
- [ ] Firmware/fuse equivalence is checked or explicitly unresolved.
- [ ] "RX always active" is decomposed into `FLAG_RX`, `OCDMV`, `OCD_STOPPED`, and raw status.
- [ ] Echo corruption and response timeout are not conflated.
- [ ] No BOD lowering.
- [ ] No `-F`.
- [ ] Flash budget recorded.
- [ ] No unsupported cross-family register interpretation.
- [ ] Hypothesis inventory is updated with evidence.
- [ ] Final root-cause claim meets the stated evidence standard.
- [ ] `verification-before-completion` executed.
- [ ] Final CSV and Markdown artifacts generated.

---

# 26. First actions now

Do not begin by flashing.

Start with exactly this sequence:

1. Read this entire prompt.
2. Read the relevant Superpowers skills.
3. Inspect repository status and existing UPDI tooling.
4. Research current primary sources.
5. Create `experiments/updi_rca/` only.
6. Write `memory/PLAN.md`.
7. Spawn exactly 2 lane workers.
8. Build/test the tty-independent identity resolver using TDD.
9. Inventory both currently connected devices.
10. Capture a read-only 38400 baseline on both.
11. Parse/classify the existing known failure logs as fixtures.
12. Compare board vs adapter identity.
13. Only then select the first discriminating hardware experiment.

No speculative fix before those steps.

The investigation ends when evidence has isolated the failure to the narrowest defensible layer, not when the error temporarily disappears.

