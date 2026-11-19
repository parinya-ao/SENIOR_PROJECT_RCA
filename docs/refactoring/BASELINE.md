# C++ Refactoring Baseline

Recorded 2026-11-18, Asia/Bangkok. This records the initial checkout and the
clean parent-revision comparison separately because the initial working tree
already contained a substantial refactor.

## Repository snapshot

- Revision at entry: `380e8f70435be1140764498b52c5634ef0e5257e`
  (`chore: refactor`), branch `Fix/rewrite`.
- Initial working tree: 35 modified/staged paths, 306 deleted paths, and 6
  untracked paths; `git diff --stat` reported 341 tracked files changed,
  1,344 insertions, and 42,341 deletions. The active C++ refactor was already
  present among those changes.
- He committed that pre-existing work as
  `740206b1c64d37d5947563393b2094448782f95f` (`fix: delete unuse`) while the
  verification was running. This continuation did not commit anything.
- `config/lora_system.json` is ignored by `*.json`. The exact JSON He supplied
  was copied into the isolated parent worktree; its SHA-256 was
  `ef1c293f9e9b0dfc0436847fa551a5a1f377744a43451afba719a11eec23aa64`.

## Production and analysis scope

- `platformio.ini` defaults to `sender` and `receiver`; the existing C++ quality
  matrix also builds `sender_hello`, `sender_arq_test`, and `receiver_arq_test`.
- The main quality runner analyzes `src/`, `stable_lib/arq/src/arq/`, and
  `stable_lib/ssot/src/ssot/` (30 C++ source/header files). The shell entry point
  adds directly compiled support libraries and all C++ tests to formatting,
  duplication, and complexity checks, then runs host analysis on the portable
  AVR support sources and Gateway I2C fixture.
- Profiles use separate `gateway_app`, `reliable_app`, and `arq` paths. The
  dependency graph and source inventory are summarized in
  [stable_lib/README.md](../../stable_lib/README.md).
- The CodeGraph MCP had no usable index; Graphify queries were used for source
  navigation and `graphify update .` refreshed the graph after comment edits.

## Parent-revision measurements

The parent source was checked in an isolated worktree at `380e8f7`. The five
firmware environments built with the supplied configuration and emitted zero
compiler warnings:

| Environment | Flash bytes | SRAM bytes | Warnings |
|---|---:|---:|---:|
| `sender_hello` | 36,368 | 3,939 | 0 |
| `receiver` | 35,612 | 3,772 | 0 |
| `sender` | 38,590 | 7,049 | 0 |
| `sender_arq_test` | 37,562 | 5,226 | 0 |
| `receiver_arq_test` | 38,672 | 5,268 | 0 |

The full parent unittest run reported 405 tests, 11 failures, 11 errors, and 1
skip. The isolated worktree did not contain local/out-of-repository artifacts:
the helper `tools/debug_protocol_ack_nack.py` used Python-2 exception syntax,
tests expected `../iwing-tracker/gateway-lora/mainboard/src/radio_915_profile.py`,
and a hardware test expected `config/current_hardware.json`. Python source was
not modified.

With the final expanded Doxygen input, the parent emitted 264 documentation
errors; the XML contained 286 function member entries, 13 with descriptions.
Clang-Tidy had 22 invocations with both passing and failing exit codes; its log
contains repeated diagnostics across flag variants. Clang Static Analyzer
emitted 6 dead-store diagnostics across 65 invocations (two source locations
repeated across variants). Lizard reported 138 functions, average CCN 5.33,
maximum CCN 48, 17 functions above CCN 10, and 5 above 60 logical lines. jscpd
reported 2 clones, 16 duplicated lines, and 0.4745% duplication in the main
source scope.

## Toolchain and limits

PlatformIO Core was 6.2.0. The installed C++ analysis versions and paths are
recorded in `reports/static_analysis/tools.txt`. Native AVR translation units
cannot use the host Clang database as an AVR analysis database; those units are
reported as unsupported by LLVM and are covered by the AVR-GCC build matrix.

No firmware upload, programming, hardware mutation, or RF transmission was
performed.
