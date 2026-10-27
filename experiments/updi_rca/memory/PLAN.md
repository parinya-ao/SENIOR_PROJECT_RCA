# AVR128DA28 Dual-Board UPDI Root-Cause Investigation Plan

> **Execution:** Coordinator implements and verifies the plan. Exactly two lane workers handle one adapter path each; no reviewer or third agent.

**Goal:** Isolate the intermittent UPDI/OCD failure to the narrowest layer supported by reproducible, identity-linked evidence.

**Architecture:** Keep all investigation code, evidence, reports, target diagnostics, and persistent notes under `experiments/updi_rca/`. The baseline uses a dedicated experiment-owned serial path that sends BREAK synchronization and read commands only; adapter/target identity, transport events, stage classification, statistics, and CSV reporting remain explicit.

**Tech stack:** Python standard library, pytest, pyserial and existing UPDI tooling; minimal AVR C/C++ diagnostic target; D2 v0.9.0 with TALA and theme 4.

**Spec:** User-provided task contract plus root `PROMPT.md` (the referenced `updi_rca_ai_agent_prompt.md` is absent).

## Global constraints

- Do not modify production firmware, fuses, BOD settings, upstream UPDI code, or unrelated application architecture.
- Begin read-only. No `avrdude -F`, chip erase, retries after a failed bounded probe, or repeated flashing.
- Assign lanes by USB `ID_PATH`/sysfs and adapter identity, then resolve target using safe SIB/signature/REVID/serial reads; tty names are locators only and duplicate adapter serials are not unique.
- Exactly two agents: Lane A and Lane B. Each opens only its assigned port for a bounded probe, closes it, and writes only its raw lane evidence and Markdown lane note. Coordinator alone owns shared CSVs and analysis.
- The repository's normal `updi-diagnose.py` backends are not zero-register-write: upstream init sends `STCS CTRLB=CCDETDIS`; oracle init sends `STCS CTRLB` and `CTRLA`. They are excluded from the strict baseline path.
- Keep local echo, UPDI response, ACC ACK/data, OCD status/message, USB, and target reset/runtime failures distinct.
- A BORF observation without an independently observed new boot is historical state, not proof of another reset.
- Stop at the software/physical boundary if remaining causes need instruments; report the exact measurement and do not name an unsupported component defect.
- Preserve all 168 seed hypotheses and statuses; scores rank discriminators and are not probabilities.

## Review focus

- Duplicate CP2102 USB serials and tty renaming must not change board identity; cover in identity tests.
- An unreachable target remains `UNKNOWN_TARGET`; cover in identity tests.
- Corrupt/truncated/empty echo differs from exact echo followed by missing ACK/data; cover in parser and classifier tests.
- BORF without a boot marker differs from a new reset; cover in classifier tests.
- CPU RUNNING and STOPPED/programming-held outcomes remain separate; cover in event and report tests.

## Tasks

### 1. Freeze, inspect, and plan

- [x] Read the task contract, root prompt, existing UPDI implementation, report, and prior evidence.
- [x] Verify Microchip data sheet/errata, upstream code, Linux usbmon documentation, and D2/TALA availability; record source revisions and claims in `memory/SOURCES.md`.
- [x] Record adapter `ID_PATH`, sysfs/USB mapping, current tty observation, and duplicate USB serials; target identity reads remain incomplete.
- [x] Review standard UPDI setup side effects; implement a strict no-`STCS`/`STS`/key/reset/NVM probe path before continuing the baseline.

### 2. Observe both lanes

- [x] Spawn exactly two lane agents, one per unique adapter path; no third worker.
- [x] Resolve adapter paths; record targets as `UNKNOWN_TARGET` when SIB/signature/REVID/serial reads do not complete.
- [x] Finish the strict bounded 38400 SIB/control baseline at 100 attempts per lane/condition; each attempt opens and closes its port.
- [x] Coordinator joins lane evidence and produces shared inventory/runs/events and pairwise comparison.

### 3. TDD host tooling

- [x] Write and observe failing identity tests first for duplicate serial, path identity, tty swap, unknown target, reconnect.
- [x] Implement the smallest sysfs/udev identity resolver and pass those tests.
- [x] Add synthetic parser/classifier/metrics/reporting tests for required stage distinctions, reset marker semantics, USB correlation, Wilson intervals, and CSV schemas.
- [x] Add synthetic short-read, timeout, reconnect, tty-rename, and raw-persistence coverage; hardware tests remain separate.
- [x] Build a sequential runner with immutable run IDs, monotonic events, per-attempt raw JSON, SHA-256, and close-on-every-attempt behavior.
- [x] Observe red then green tests for the strict read-only path; SIB/LDCS/LDS are the only target commands used by that path.

### 4. Select discriminating experiments

- [x] Compare completed 38400 baseline outcomes and prior 19/60 unheld LDS evidence without conflating historical runs with fresh identity-linked runs.
- [x] Run 100 SIB and 100 control-read attempts per lane at 38400. Keep historical ACC RUNNING/STOPPED results separate; current Lane B never reaches its target request, and no fresh STOPPED campaign was safe/read-only.
- [x] Measure available state independently: sequential read-only GPR2/`FLAG_RX` LDS samples (n=100), `OCDMV`/`OCD_STOPPED` and raw ASI status (n=100 control snapshots), host TX/echo events, and a bounded 15-byte OCD message read. `FLAG_RX` remained set, but repeated reads cannot distinguish a sticky flag from new receive activity. The SILENT target comparison remains blocked without a safe two-board flash/verify path.
- [x] Build the minimal combined SILENT/HEARTBEAT firmware and hash the exact artifact once; do not flash while identity, metadata snapshot, and readback gates are unavailable.
- [x] No physical signals were probed without instruments. The report marks component-level causes `BLOCKED` and specifies the exact simultaneous measurement.

### 5. Evidence, reports, diagram, verification

- [x] Refresh all 168 hypothesis rows after the strict baseline and bounded OCD snapshot; generate every required CSV with fixed schemas.
- [x] Generate the STAR RCA, Markdown handoff, run/event hash mapping, and D2/TALA SVG (Cool Classics theme 4), including the 100-read FLAG_RX follow-up.
- [x] Run `uv run --project experiments/updi_rca --with pytest pytest -q experiments/updi_rca/tests`; 45 tests passed. Validate CSV schemas, classifications, and evidence/run mappings.
- [x] Run `graphify update .` after the final code changes; graph rebuilt with 2,121 nodes and 3,524 edges.
- [x] Re-read this checklist and report completed work, gaps, measured limits, and the one smallest next action.
