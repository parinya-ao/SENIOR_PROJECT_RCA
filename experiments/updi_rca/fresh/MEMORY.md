# RCA_FRESH_01 execution ledger

Plan saved before implementation. Inherited host suite: 105 passed in 0.09s.

Scope: fresh runner/tests, fresh evidence/reports, root RCA.md entry point, Graphify refresh. Existing strict transport and historical evidence remain unchanged.

Pre-flight interfaces: discovery supplies path identity; strict probes supply raw operation events; runner adds immutable epoch envelope; coordinator validates envelopes before CSV metrics. Control and identity gates consume fresh SIB batches only.

Ruling: use a new branch in the existing dirty workspace because all experiment code and historical evidence are untracked; a clean checkout would omit the dependencies and evidence required by this task. No inherited files are staged or committed.

Ruling: no existing worker sessions are available in this fresh context (agent inventory contains only root). Create exactly two lane workers after the host gate, preserving the requested two-worker roles and lane-only write ownership.

The supplied plan mentions 13 requested tests without enumerating them; map the existing post-swap contract's 13 checks into fresh tests and add the fresh isolation and resource-safety checks.

Implementation gate: 30 fresh checks failed on the intended missing-runner assertion; seven reused causal checks already passed. Initialization/report/missing-transport checks then failed 3/3 and passed after implementation. Final review regression checks failed 5/5 (command/result/timing consistency and control batch reservation) and passed after fixes. Final requested suite: 150 passed (105 inherited, 45 fresh). Existing project default test suite: 105 passed. One default-suite command initially used the wrong relative --project path from inside the project; corrected to `uv run pytest -q`.

Fresh discovery executed and frozen before serial access: P=usb-0:1:1.0/current ttyUSB1; Q=usb-0:4:1.0/current ttyUSB0. Both target IDs UNKNOWN; adapter-unit IDs UNRESOLVED; separate current-branch PowerBoard P/Q recorded. Two lane workers assigned, each restricted to its own fresh evidence directory. No inherited target association reused.

P smoke completed 0/10 SIB, all SIB_RESPONSE_EMPTY; no port/discovery errors. Coordinator validates and refreshes shared reports after each completed batch.

Final baseline checkpoint: Q smoke also 0/10; P/Q baseline-1 each 0/30 SIB, all SIB_RESPONSE_EMPTY. Total fresh 80 attempts/560 events. Exact first/second BREAK and SIB command echoes in every attempt; no target response bytes. Busy/discovery/execution failures zero. Stage boundaries unchanged; no mandatory third baseline, no informative rate comparison requiring expansion100. Control and identity gates closed. No physical changes, reset/programming commands, flash writes, fuse writes, chip erases or BOD changes.

Selected causal experiment: single simultaneous BREAK-triggered P-lane capture of target-local VDD, ground offset, adapter TX and UPDI after qualified pinout/reference verification. Branch BLOCKED_MEASUREMENT: instruments and safe attachment unverified. No movement or restoration requested; no repair/proof/locality claim. All D1–D8 remain unresolved at zero because baseline does not distinguish them.

Final coordinator review: preserved strict backend unchanged; all historical file hashes match, 629 inherited raw hashes match, fresh 80 envelopes/240 source artifacts validate, 560 unique mapped fresh events and 12 fresh CSV schemas/epochs verify, both ports idle. Historical run IDs are 17 batch-level IDs across 629 attempt rows; do not impose fresh per-attempt uniqueness on historical ledgers. First verifier assertion exposed this schema difference; corrected the verifier and documented the distinction without changing old evidence.

Requested suite rerun: 150 passed in 0.17s initially; final rerun recorded in VERIFICATION.json. Root RCA.md entry point added. Full git diff check exposes pre-existing whitespace in .automation/compact-bundle.xml; scoped RCA.md diff check passes. Graphify refreshed AST-only, with pre-existing extraction warnings for pyproject.toml and two external C headers; no semantic/API extraction used. Self-review by coordinator only, as required by the two-worker contract. No commits or merge performed because substantial unrelated untracked/dirty work was inherited.
