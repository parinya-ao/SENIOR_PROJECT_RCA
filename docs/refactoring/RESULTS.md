# C++ Refactoring Results

The follow-on source ownership verification is in [Source ownership V2](SOURCE_OWNERSHIP_V2.md) with its [fresh baseline](OWNERSHIP_BASELINE.md).

Current ACK/NACK behavior and validation status are maintained in
[docs/testing/LORA_ACK_NACK.md](../testing/LORA_ACK_NACK.md), with hardware
nets in the repository [pin audit](../../PIN_MAPPING_AUDIT.md). The current
[regression matrix](../testing/REGRESSION_MATRIX.md) and
[real-radio evidence ledger](../testing/REAL_RADIO_EVIDENCE.md) carry the
per-target sizes and physical-test blockers.

## Current follow-up verification — 2026-11-19

This is the fresh evidence for the current worktree; the remaining sections
retain the earlier C++ quality pass as historical context.

- The final PlatformIO matrix passed **19/19** with **0 compiler warnings**.
  The default Sender image is **38,794 B Flash / 7,079 B static SRAM** and the
  Receiver image is **35,788 B / 3,849 B**; both match the first clean
  pre-fix build in this loop. The approved-plan historical baseline was
  **38,820 / 7,079 B** for Sender and **35,908 / 3,842 B** for Receiver. Those
  differences were already present before this loop's ARQ change.
  The ARQ Sender changed from **37,022 B** to **37,028 B**, and ARQ Receiver
  from **35,774 B** to **35,772 B**; their static SRAM remains **5,202 B** and
  **5,046 B**. These are the measured sizes after moving the shared deadline
  helper; no protocol field or retry rule changed.
- The full host suite ran **434 tests: 433 passed, 0 failed, 1 skipped**. The
  skip is the archived BOOTSIZE=44 package case, which does not match the active
  Receiver geometry.
- `mise run lint:python` passed Ruff, formatting, and MyPy across 72 files.
  `bash scripts/quality/check_cpp.sh` exited **0**; all reported supported
  analyses, Doxygen, formatting, and its five selected AVR builds passed.
  Native AVR LLVM, TimeUtils LLVM, and selected Gateway LLVM checks remain
  marked UNSUPPORTED by the established gate.
- The generated-config `--check` passed. The 19 final link maps contain no BOOT
  source; the Sender ARQ ELF extracts only `sender.cpp.o`, and the Receiver ARQ
  ELF only `receiver.cpp.o`. An `avr-objdump` scan found **0 SPM instructions
  across 19 APPCODE ELFs**. No memory layout, fuse, wire format, or physical
  hardware was changed.
- Graphify was queried before source reads and refreshed with `graphify update .`
  to **3,612 nodes / 7,011 edges**. CodeGraph MCP has no usable index in this
  checkout; no CodeGraph result is claimed.
- The offline handoff fixture remains **48 bytes**. Its valid reset bytes
  `52 C0 00 00` jump to `0x5800`; the blank vector and all four altered-byte
  cases park with interrupts disabled.
  It does not validate an active BOOT/APPCODE pairing or installer.
- The native Codex Goal remains **active**. Physical 10/10 DATA/ACK and 10/10
  wrong-destination trials are **BLOCKED** because passive discovery found no
  devices and `/dev/serial/by-path` is absent. No firmware was uploaded and no
  RF was transmitted.
- The active documentation audit checked **91 relative links across 28 files**
  with no broken targets. No Markdown was deleted or consolidated. The wider
  ignored historical RF report's 18 stale absolute links were converted to
  literal captured paths; its original is backed up under `/tmp`. The full
  66-file scan now has no broken links.

Historical record of the C++ quality pass before the follow-on flat-tree work.
The current library layout is documented in
[stable_lib/README.md](../../stable_lib/README.md).

## S — Situation

The starting worktree already contained the large C++ refactor and its tests.
The parent revision had undocumented APIs, Clang-Tidy failures, analyzer
dead-store reports, and complexity hotspots. Baseline measurements and the
isolated-worktree test limitations are recorded in
[BASELINE.md](BASELINE.md).

## T — Task

Finish local verification, document active library responsibilities, install
the requested C++ tools, preserve the existing PlatformIO layout, and report
only checks that actually ran.

## A — Action

- Added the Fedora-aware, user-local tool installation path to
  `install_cpp_quality_tools.sh`. It uses the caller's environment when invoked
  through `sudo`, installs LLVM 22.1.8 tools without a system package write, and
  verifies each requested executable.
- Extended `scripts/quality/check_cpp.sh` without changing its Python runner.
  It composes the user-local tool paths, checks linked support-library and test
  formatting, runs Lizard and jscpd over the expanded source set, and adds
  host Clang-Tidy, Analyzer, and IWYU checks for portable support modules.
- Added Doxygen contracts for directly used support APIs, fixed two
  parameter-name documentation errors in `RingBuffer`, documented the AVR host
  stubs and task/LED contracts, and expanded `scripts/quality/Doxyfile` to cover
  those libraries. Generated layout and vendored protothread headers remain
  excluded. The legacy packed-packet API is now documented too; Doxygen excludes
  only the false symbol it derives from the GCC `__attribute__((packed))` syntax.
- Added one line-scoped `NOLINT(bugprone-derived-method-shadowing-base-method)`
  for the unused concrete `PowerSavingTaskScheduler::Loop` policy. The base
  method is intentionally non-virtual and no in-tree caller uses this class
  through `TaskScheduler*`.
- Added the `stable_lib` inventory and per-library readmes. Four source-layout
  libraries now have manifests that point to their existing `src/` trees; no
  source/header moves or runtime configuration edits were made.
- Parenthesized the task-timer macro arguments at their existing call boundary;
  the current call sites still expand to the same operations. Added one narrow
  `NOLINT` for the unused concrete power-saving scheduler's non-virtual `Loop`
  name collision; there are no in-tree callers through `TaskScheduler*`.
- The source refactor already present at task start was committed by He as
  `740206b`; this continuation did not alter its transport state machine. A
  parent-revision comparison does show prior edge-behavior changes in that
  commit: an absolute transaction deadline, campaign rollover after sequence
  exhaustion, rejection of zero campaign/sequence identifiers, prevention of
  sequence reuse within a campaign, radio reinitialization at the sequence
  boundary, and stricter test-command parsing. They were present before this
  continuation and remain visible here; the current tests cover that current
  behavior. This continuation preserves the task-start behavior, but the branch
  is not equivalent to parent `380e8f7` on those edge cases.

## R — Result

The final command `rtk bash scripts/quality/check_cpp.sh` exited 0. It ran 430
host tests with 1 skipped, built all five selected AVR environments with zero
emitted compiler warnings, and passed the main Clang-Tidy, Clang Static
Analyzer, IWYU, clang-doc, Lizard, jscpd, formatter, and Doxygen checks.

Executed commands included `rtk bash install_cpp_quality_tools.sh`,
`rtk bash scripts/quality/check_cpp.sh`,
`rtk python3 -m unittest discover -s tests -p 'test_*.py'`, and
`rtk graphify update .`. The Python dependency `pyserial` was already declared
in `pyproject.toml`; it was installed into the active local interpreter with
`uv pip install --system --python /home/parinya/.local/share/mise/installs/python/3.15.2/bin/python3 'pyserial>=3.5'` without changing project dependencies.

Verified tool versions: PlatformIO Core 6.2.0; Clang, clang++, clang-format,
clang-tidy and clang-doc 22.1.8; IWYU 0.26; Doxygen 1.18.0; Lizard 1.26.1;
jscpd 5.4.3; AVR-GCC 7.3.0. The installer leaves these tools user-local.
Doxygen emits a `libtinfo` version-metadata warning from the mise binary, but
exits 0 and reports zero documentation warnings.

| Metric | Parent `380e8f7` | Current `740206b` |
|---|---:|---:|
| Doxygen diagnostics in expanded scope | 264 | 0 |
| Doxygen function member entries with descriptions | 13 / 286 | 148 / 298 |
| Clang-Tidy invocations with nonzero exit | At least 1 of 22 | 0 of 22 |
| Static Analyzer diagnostics | 6 dead-store emissions | 0 of 65 invocations |
| Lizard functions in main scope | 138 | 153 |
| Average cyclomatic complexity | 5.33 | 5.02 |
| Maximum complexity | 48 (`arq::app::Poll`) | 49 (`arq::app::Poll`) |
| Functions above CCN 10 | 17 | 17 |
| Functions above 60 logical lines | 5 | 3 |
| Main-scope duplicated lines | 16 / 0.4745% | 16 / 0.4323% |
| Full selected host tests | 405: 11 failures, 11 errors, 1 skip | 430: 0 failures, 0 errors, 1 skip |
| Selected AVR builds | 5 / 5, 0 warnings | 5 / 5, 0 warnings |

The support-only Lizard pass covered 138 additional functions; average CCN was
2.51, maximum CCN was 20, with 3 functions above 10 and none above 60 lines.
The expanded 62-source jscpd pass found 7 clones (49 lines, 0.7330%). No code
was consolidated; the clone reports were left for owner-by-owner review rather
than merging code across separate modules.

| Environment | Parent Flash/SRAM | Current Flash/SRAM | Change |
|---|---:|---:|---:|
| `sender_hello` | 36,368 / 3,939 | 36,832 / 4,009 | +464 / +70 |
| `receiver` | 35,612 / 3,772 | 35,908 / 3,842 | +296 / +70 |
| `sender` | 38,590 / 7,049 | 38,820 / 7,079 | +230 / +30 |
| `sender_arq_test` | 37,562 / 5,226 | 37,562 / 5,226 | 0 / 0 |
| `receiver_arq_test` | 38,672 / 5,268 | 37,716 / 5,262 | -956 / -6 |

The current support host-analysis supplement passed on `iw_core`, AVR ADC,
provisioning/routing helpers, the Tracker codec, and the Gateway I2C fixture.
Native AVR LLVM analysis remains unsupported; the PlatformIO AVR-GCC targets
passed. Clang analysis of `time-utils.cpp` is unsupported because its
`GetUnixTime`/`SetUnixTime` calls are not declared by the host TimeLib header.
The Gateway Clang-Tidy host fixture is also marked unsupported because it
includes `espcomm.cpp` directly and triggers test/vendored-macro diagnostics;
its host Analyzer and IWYU checks passed.

### Trade-offs and limits

- No radio settings, pin assignments, runtime configuration, public C++
  signatures, or wire encodings were changed in this continuation.
- At this report's point, `stable_lib` had a directory inventory and one-line
  per-library READMEs. The follow-on flat-tree pass consolidated that material
  into the root README and moved six libraries to direct file layouts.
- The existing `arq::app::Poll` remains essential state-machine complexity at
  CCN 49; it is explicitly bounded in the quality gate because it coordinates
  both radio roles and their receive restoration.
- Flash/SRAM changes are from the previously committed source refactor and
  library discovery metadata, not from the documentation comments added here.
- Compared with parent `380e8f7`, commit `740206b` already contains observable
  edge-behavior changes: an absolute transaction deadline; campaign rollover
  after sequence exhaustion; rejection of zero campaign/sequence identifiers;
  prevention of duplicate/out-of-order TX sequences within a campaign; duplicate
  history reset when the peer changes; radio reinitialization at sequence wrap;
  and stricter FAULT-command parsing. These changes were in the starting
  worktree and were not introduced or reverted in this pass. The current suite
  verifies the behavior in `740206b`; it does not prove equivalence to
  `380e8f7` for those edge cases.
- No physical hardware or RF verification was run, and no firmware was
  programmed.
