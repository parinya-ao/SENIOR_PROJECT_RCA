/goal Deliver an evidence-verified, production-grade, feature-based LoRa Sender↔Receiver vertical slice in src/, with genuine over-the-air DATA/ACK communication, correct software destination filtering for SX127x LoRa mode, and no regressions in existing firmware, boot safety, protocol semantics, or build configurations. Work single-agent only, graph-first and real-radio-test-first; iterate review → minimal change → validate until the acceptance contract is proved or a hard blocker is documented.

# OPERATING CONTRACT — READ ALL BEFORE EDITING

You are the ONLY working agent. Never spawn, delegate to, call, or coordinate subagents. Do not enable `multi_agent`, Agent teams, parallel Codex processes, or Graphify agent fan-out. Ordinary deterministic command-line processes (compiler, tests, graph extraction) are allowed. Work sequentially and keep an auditable log. A Goal is not permission to run forever or to bypass approval/safety gates. Follow repository AGENTS.md unless it conflicts with the user's more restrictive safety constraints.

## 0. Target, boundaries, priorities

Primary editable repo: the repository from which this Codex session was started; verify `pwd`, git root and `platformio.ini`. Do NOT assume the current repository is `/home/parinya/university/iwing-tracker`.
Reference repo: `/home/parinya/university/iwing-tracker` — READ ONLY. Never write, format, clean, reset, checkout, generate artifacts, run a write-producing build, or modify this reference repository. If absent or inaccessible, report the blocker instead of pretending to compare it. Re-examine the relevant reference implementation and commit identity at each relevant iteration, not through a fake always-on background monitor.
Scope now: MAIN end-to-end LoRa unicast DATA/ACK, application addressing, RX/TX state, retries, receiver re-arm, real-radio testing, maintainable feature-based `src/`. Preserve existing FOTA boot/security/storage contracts but do NOT introduce an unrequested full FOTA implementation, cloud service, UI, or protocol redesign.
Priority order: (1) radio correctness on real devices; (2) no safety or behavioral regression; (3) verification reproducibility; (4) source ownership and readability; (5) deduplication; (6) style. Never sacrifice the first three for a prettier tree.

## 1. Mandatory first phase: read-only inventory and graph analysis

Before ANY behavior-changing edit:
- Inspect `git status --short`, HEAD hash, repository instructions, `platformio.ini`, `generated/lora_platformio.ini`, `config/radio_915.toml`, `config/arq_test.toml`, `config/application.toml`, build scripts, `library.json` entries, host tests and HIL tools.
- Record current environment matrix. This snapshot shows `lib_dir = stable_lib`, `src/main.cpp` as the common entrypoint, `default_envs = sender, receiver`, and separately named `sender_arq`, `receiver_arq`, `_test`, `_radio_only`, and reverse variants. VERIFY this against the live checkout; the compressed Repomix snapshot is not full source and strips comments and code bodies.
- Detect tools: `command -v codegraph`, `command -v graphify`; inspect `--help` and any repository-local wrappers before invoking them. "CodeGraph" is not a unique CLI product; never invent commands. If installed, perform a real read-only CodeGraph analysis and save version, invocation, outputs, and exit code. If absent, label the CodeGraph gate BLOCKED, not PASSED.
- Use Graphify Local in single-agent, AST-only mode. If not installed and installation is permitted, use the official `graphifyy` package. Verify the CLI help before running. Typical command: `GRAPHIFY_BACKEND=none graphify extract . --code-only`. Then query scoped paths with `graphify query`, `graphify path`, `graphify explain`; refresh after each coherent change with `graphify update .`. Ensure it indexes `src`, `stable_lib`, `boot`, `include`, `config` and useful tests; avoid mistaking generated data, documentation, or third-party code for application ownership. No multi-agent setup is required or allowed.
- Use symbol-level graph results as candidate evidence, not proof of runtime behavior. Confirm critical relations in exact source, compile/link maps, call sites, configuration and tests. Record EXTRACTED vs INFERRED/AMBIGUOUS edges separately.
- Produce `docs/architecture/BASELINE_GRAPH.md`, `docs/architecture/ENTRYPOINT_MATRIX.md`, `docs/architecture/OWNERSHIP_MAP.md`, and `docs/architecture/REFERENCE_BEHAVIOR_MATRIX.md` (or reuse existing locations if preferred by repo). Preserve relevant existing documents and not rename them needlessly.
- List all constructors and call sites of `LoRa`, `_module.begin`, `setNodeAddress`, `set_my_address`, `init`, `send`, `recv`, and all Address types; trace each to actual selected environment. Identify all application-level filters, source/destination/ACK checks, duplicate handling, and in-flight TX to RX transitions.
- Build a duplicate-candidate table: owner A, owner B, exact proof of equivalent semantics, active environments, test dependencies, migration disposition. Similar names alone never justify deletion.

## 2. Reference repo: behavior parity without copying defects

Treat `/home/parinya/university/iwing-tracker` as behavioral reference, not unquestionable implementation truth. Read specific files and verify current git commit read-only. Compare:
- message bytes, field widths, endianness, length, CRC, destination and source placement;
- local/peer/broadcast address, ACK and NACK rules, session/sequence handling;
- RadioLib version, mode, settings, pins, SPI route, CS/RST/DIO/IRQ, IRQ clear, callbacks;
- sender start/stop/timeout, radio standby/sleep, receiver re-arm, error propagation;
- UART/UPDI logs, debug timing, and safety workarounds;
- existing host tests and physical test behavior.
For each behavior classify: MUST-PRESERVE / CORRECT-BUG / UNSPECIFIED / EXPERIMENTAL. Capture a golden trace or packet-vector evidence. Preserve externally observable *valid* behavior, not undefined behavior, memory corruption, stale IRQ races, failed status checks, security vulnerabilities, accidental promiscuous acceptance, or hidden hard-coded addresses. When changing an actual defect, first write a test proving the defect and document the intentional difference. Never change the reference repository.

## 3. IMPORTANT RADIO FACT: SX127x `setNodeAddress`

RadioLib SX127x documents `setNodeAddress(uint8_t)` as an FSK-mode hardware address-filter feature, NOT a LoRa-mode hardware address filter. This project uses RFM95W/SX127x LoRa; do not call it blindly and do not claim hardware filtering exists in LoRa mode. Confirm against the exact pinned RadioLib version (`jgromes/RadioLib@7.1.2` in the supplied snapshot), its implementation, the selected modulation mode, and runtime return code.
Required behavior in LoRa mode:
- retain explicit local node address and peer address as an application/interface contract;
- use the EXISTING interoperable wire format and correctly parse destination/source before passing bytes to ARQ or application;
- accept only packets addressed to this node or the protocol-defined broadcast address, if broadcast is actually supported for that packet type;
- never send ACK for an irrelevant destination, wrong sender, wrong session, or stale sequence;
- support legitimate retransmitted DATA when its ACK was lost, with idempotent receiver behavior and correct ACK policy;
- enforce both source AND destination in ACK acceptance; filter out wrong-session ACKs;
- bound packet lengths and distinguish CRC/PHY rejection from application address rejection;
- make local address configuration explicit and verified during startup, with no silent fallback to zero or unintended promiscuous behavior;
- if FSK mode is explicitly required and supported, use `setNodeAddress` / `setBroadcastAddress` with return-code checks and MODE-SPECIFIC tests; never switch the existing LoRa PHY silently.
First create failing regression tests that differentiate application destination filtering from FSK hardware filtering. In tests, record wrong destination unicast, intended destination, broadcast, stale ACK, wrong source, unknown session, duplicate fragment, short frame and malformed length. Update fake RadioLib stubs so they do NOT make false claims about physical LoRa filtering.

## 4. Test FIRST using real radios, BEFORE migration

Before changing behavior, establish the physical baseline if the boards are available. Read-only discovery first: device/role identity, connected USB paths, radio version, existing firmware identity, configured frequency/bandwidth/SF/sync word, power, silicon revision and IRQ/pin mappings. Check RF operation is authorized for this location, frequency, power and duty-cycle policy before transmitting; the snapshot uses 915 MHz, which must not be assumed legal at every site. Avoid key leakage or logs containing secrets.
If approved devices are connected and the existing test tooling is known safe, run the current real-radio end-to-end unicast test, capture BOTH endpoints' logs with timestamps and git/build identity, and record:
- sender DATA transmission attempt and radio return code;
- receiver physical RX/IRQ and decoded source/destination;
- receiver ACK TX and sender ACK RX;
- sender success/failure state and retry count;
- observed RSSI, SNR, packet length and elapsed time;
- receiver RX re-arm after TX, timeout/IRQ behavior;
- wrong-destination injection and whether application rejects it.
Do not upload firmware as a side effect of passive inventory. Before any intentional firmware upload, identify role/port/target/flash range and backup or log current firmware identity; restrict to the intended APPCODE and preserve BOOT, fuses, NVM and device-specific calibration. Never run `pio run -t upload` blindly or against a guessed USB port. Explicit approval is required for destructive or boot/fuse-changing operations; routine app flashing may proceed only on positively identified, authorized test fixtures per local lab rules.
If no radios are available or baseline test cannot safely run, mark PHYSICAL_BASELINE_BLOCKED with evidence; run host-level tests but DO NOT report end-to-end real RF complete. Continue only with safe, independently testable tasks and stop rather than falsely passing the acceptance gate.

## 5. Target source ownership: feature-based `src/`, not empty façades

Use the smallest useful organization. This is a TARGET, not mandatory scaffolding: create files only if real active production code will inhabit them. Prefer co-located `.h`/`.cpp` and one owner for each behavior.

src/
  main.cpp                        # thin framework entrypoint / composition root
  app/
    application.h/.cpp            # role composition and lifecycle, no packet parsing
  features/
    radio_link/
      radio_link.h/.cpp           # LoRa PHY lifecycle, callbacks, TX/RX transition
      address_policy.h/.cpp       # pure local/peer/broadcast decision logic
    reliable_transfer/
      frame_codec.h/.cpp         # single canonical on-wire representation
      sender_session.h/.cpp      # retry, deadlines, ACK correlation
      receiver_session.h/.cpp    # DATA handling, duplicate/idempotence, replies
    diagnostics/
      radio_diagnostics.h/.cpp   # bounded, non-blocking, testable event records
  platform/
    avr128da28/                   # only platform glue proven necessary

Keep bootloader, platform/device core, shared wire protocol, generated configuration and independent private libraries in place unless there is proof that moving them improves ownership without breaking build. If a feature already exists and is active in `stable_lib`, MIGRATE its single implementation to `src/features`, update includes/build wiring/tests, and remove/exclude the old linked implementation; do not create wrappers that merely duplicate public APIs while implementation stays scattered. Migrate ONE vertical slice at a time. If the build/link setup makes migration unsafe, choose a smaller working step and document remaining ownership. Do not create placeholder directories or unused abstraction layers.

## 6. Build isolation and migration constraints

`platformio.ini` currently uses a common `src/main.cpp` and `lib_dir = stable_lib` in the snapshot. Keep `sender`, `receiver`, `sender_arq`, `receiver_arq`, their `_test`, `_radio_only`, and reverse variants functional as applicable. Compile only one `setup()`, one `loop()`, and one implementation of each public symbol in each environment. Use `build_src_filter`, role defines, `lib_ignore`, library manifests, and linker maps deliberately, not as cargo-cult settings. Protect generated configs and pre-build scripts; edit their source-of-truth generators, not generated headers. Preserve RadioLib 7.1.2 unless a separately demonstrated bug requires upgrading it. No bulk rename, wholesale style-only rewrite, protocol redesign, additional dependency, or new framework as a shortcut.
Ensure the code in `src/features/` is genuinely active in production builds; prove with symbol maps or object lists and real tests. Do not leave old source linked alongside replacement. Do not delete legacy branches just because they are not used by the default environment.

## 7. Google-style production comments and maintainability

Follow https://google.github.io/styleguide/cppguide and existing `.clang-format` (Google, 2-space indent, 80 columns). Existing `.cpp` filenames are acceptable; don't mass-rename to `.cc` purely for style.
- Types: `PascalCase`; functions: `PascalCase` for new C++ APIs; variables: `snake_case`; private members: trailing `_`; named constants: `kPascalCase`; macros: uppercase; namespaces: lowercase. Respect stable C APIs, wire names, generated names and existing ABI.
- Headers: own includes, unique guards or existing convention, minimal exposure, no unnecessary transitive dependencies.
- File comments: explain module purpose and what does NOT belong in it; do not invent copyright/license ownership.
- Public API comments: document ownership/lifetime, inputs/units/ranges, outputs/error codes, preconditions/postconditions, side effects, ISR/thread context, memory bounds, and failure guarantees IF non-obvious; don't duplicate the signature.
- Implementation comments: explain WHY, protocol invariants, timing and retry semantics, IRQ races, errata workarounds, intentional tradeoffs; never narrate obvious assignments.
- Safety-critical comments: cite specific silicon revision, datasheet/erratum section, register assumptions, memory section, recovery conditions, and tests proving the restriction.
- TODOs must identify tracked issue/owner and a concrete completion condition; no vague `TODO fix later`.
- Keep comments accurate after code moves, and document deliberate behavior deviations from the reference.
Example of expected comment quality:
  // A retransmitted DATA frame can arrive after its ACK was lost. Re-ACK
  // the accepted sequence without applying its payload twice; doing so
  // preserves exactly-once application delivery over an at-least-once link.
Do not claim exactly-once behavior unless tests actually establish it at the defined application boundary.

## 8. Embedded safety and deterministic resource constraints

Preserve no-exceptions/no-RTTI compile assumptions. Prefer bounded static buffers, explicit ownership, checked arithmetic, length validation, fixed-width wire fields, deterministic retries and deadlines, and clock-wrap-safe timeout checks. Avoid dynamic allocation in radio hot paths, unbounded queues, blocking logging in ISR/receive paths, unsafe `reinterpret_cast` of packed wire payloads, unaligned NVM access, data races on ISR shared state, unchecked integer truncation, accidental memory overlap, sign-extension errors and buffer overflows.
Read and apply Microchip AVR128DA silicon errata as relevant. Never alter BOOT, fuses, NVM protections or authenticated image acceptance while restructuring LoRa. Confirm that PlatformIO compile and link outputs remain within Flash/SRAM budgets. Record stack-usage estimates when available but do not present them as whole-program WCET/stack proofs.

## 9. Test-driven development order

For EACH behavior change:
A. RED: write or update focused host tests and at least one negative case that exposes old behavior or guards an invariant. Demonstrate pre-change failure when feasible.
B. GREEN: implement the smallest production change, with no unrelated refactor.
C. VALIDATE: run focused tests, entire affected suites, build all relevant PIO environments and compare firmware sizes/maps.
D. REAL RF: if safe hardware is available, test actual Sender↔Receiver RF, wrong-destination filtering, ACK path, and RX re-arming; capture two-sided logs.
E. REFACTOR: remove proven dead duplication only after tests; re-run all gates, graph updates, and a diff review.
F. RECORD: capture commit hash, changed paths, commands, exit codes, logs, metrics, decisions and remaining uncertainty.
Do not move to the next slice while a safety or regression gate is red. For flaky tests, repeat and investigate root cause, do not delete/skip or weaken assertions to make a green dashboard.

## 10. Mandatory negative and protocol matrix

At minimum verify: local-address match; nonlocal destination rejection; valid broadcast if allowed; forbidden broadcast if not allowed; wrong-source control frame; stale/mismatched session; sequence rollover; duplicate DATA with ACK lost; ACK addressed to another node; ACK from another peer; ACK before DATA completion; NACK/retry exhaustion; RX disabled/re-enabled after TX; malformed/truncated headers; zero/max/oversized payload; CRC mismatch; radio begin failure; hardware reset/reinitialize; SPI/radio error propagation; millis overflow and timeout boundaries; incomplete UART log line; and repeatability after device restart. Distinguish actual observed hardware results from host-simulator results.

## 11. Acceptance criteria — NOT negotiable

1. `src/` contains active, feature-based, testable production code for the chosen LoRa data/ACK vertical slice; `main.cpp` is a small composition root, and no feature exists only as an empty wrapper.
2. Graphify and available CodeGraph evidence are recorded with versions and command outputs; critical call edges are verified in source and linked binaries; a missing CodeGraph tool is reported, not faked.
3. The actual pinned SX127x/RFM95W LoRa mode uses correct SOFTWARE destination filtering; hardware-only `setNodeAddress` behavior is neither assumed nor falsely advertised.
4. Wire format, valid reference behavior, timeouts, addresses, retries and logs match baseline or have documented test-proven bug fixes. No unintended ABI/protocol break.
5. All applicable pre-existing host tests and both sender/receiver production and experimental builds pass or are explicitly blocked with reproducer; no hidden deleted tests or ignored errors.
6. On physically available and approved devices, at least 10/10 controlled end-to-end DATA→ACK trials succeed with logs from both radios, and at least 10/10 wrong-destination trials cause ZERO application delivery and ZERO ACK. Repeat with lost-ACK/duplicate conditions where safe and possible. Host simulation success cannot substitute for real RF evidence.
7. No mismatched source/session ACK is accepted; all malformed frame tests pass; all tests remain deterministic and have recorded seeds/configurations.
8. BOOT unchanged, no out-of-bounds APPCODE writes, no silent alteration of protection/security mechanism, no unreviewed changes to hardware fuses or calibration. Recheck if firmware size/map changes.
9. Every removed duplicate has proof: no consumers in graph and source, excluded or moved correctly for every affected environment, equivalent behavior where required, tests/builds/HIL after deletion, and a revert path.
10. Production comments follow Google-style principles, focus on contracts/WHY/invariants and trace hardware errata to actual source. Formatting and static analysis pass on touched files, with exclusions justified.
11. Deliver `docs/architecture/FINAL_ARCHITECTURE.md`, `docs/testing/REAL_RADIO_EVIDENCE.md`, `docs/testing/REGRESSION_MATRIX.md`, `docs/migration/DELETION_AUDIT.md`, and an audit trail of iterations. Reuse existing dirs when appropriate; do not create redundant doc trees.

## 12. Agentic self-repair loop — persistent, evidence-driven, bounded

Operate as a single-agent sequence:
REVIEW current evidence → choose the highest-risk/most valuable next difference → RED test → minimal REPAIR → VALIDATE unit+integration+build → REAL HARDWARE where safe → graph refresh → AUDIT → continue only if goal incomplete.
Maintain a machine-readable project-owned policy file at `automation/goal_policy.toml` and an evidence journal at `artifacts/goal_iterations/` or existing repo conventions. The policy is OUR PROJECT'S verification contract, NOT a native Codex `/goal` setting. Implement a simple verification runner only if it reduces duplicated commands and does not require a second agent, background daemon or unattended hardware operation. Produce one record per iteration with: iteration ID, git SHA, hypothesis, change summary, exact commands, exit codes, before/after metrics, references, evidence files, failures, and next constrained action.
Stop or pause when (a) all acceptance gates pass; (b) hardware or authorization is needed; (c) no new progress after 3 equivalent attempts; (d) risk of writing BOOT/fuses/unknown target; (e) graph/reference inputs are missing for a critical decision; or (f) budget/resource limit reached. Never claim success on a blocked gate. Do not loop indefinitely merely to create activity. Use a bounded timebox per experiment and preserve checkpoints so the Goal can resume from evidence.

## 13. First actions — execute in this exact order

1. Read AGENTS.md and live repository state, preserve uncommitted user work, inventory environment configs and available test/devices.
2. Build CodeGraph (if available) and Graphify AST graph; query the actual production chain; inspect current `src/main.cpp`, active `stable_lib` modules, generated SSOT and RadioLib version.
3. Inspect `/home/parinya/university/iwing-tracker` read-only; record commit identity and behavior matrix. If unavailable, explicitly mark blocked and limit parity claims.
4. Run read-only radio/port discovery and safest available real-radio BASELINE before migrating any code. Do not guess port or execute unsafe upload.
5. Run existing host regression suites and PIO build matrix; save baseline maps, sizes and test outputs.
6. Add negative tests for address filter and ACK correlation; confirm RED then GREEN.
7. Migrate the FIRST minimal active feature into `src/features/` without duplicate linked definitions; wire the production entrypoint; re-run every affected gate.
8. Continue through one bounded feature slice at a time, only removing duplication after validated proof.
9. End with transparent PASS/BLOCKED/FAIL evidence for each acceptance criterion, numbers, observed RF traces, and the next specific action for every blocker.

You must IMPLEMENT and VALIDATE, not merely produce a plan. Ask for input only at a true safety, access, or untestable-physics blocker. Never spawn subagents. Never mark the goal complete based only on architecture diagrams, comments, compilation, mocks, or claims without real-radio evidence.
