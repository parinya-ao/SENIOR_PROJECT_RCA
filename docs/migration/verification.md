# C++ migration verification

Verified 2026-11-16. Application conversion is implemented and host-verified; full project acceptance remains limited by the failing legacy/integration checks listed below and hardware NOT TESTED. No device was flashed or accessed.

## A. Migration summary

Converted every handwritten C application implementation: SSOT protocol/campaign/control logic and the ARQ codec, sender, and receiver. Migrated their two C characterization executables and all native compiler consumers to C++17. Existing application modules already written in C++ remain in place; only affected callers and readability formatting changed.

Intentionally retained C: generated `src/arq/board_ssot.c`; `lib/updi_uart/src/updi_uart.c`, which includes the upstream C UART implementation with its C ABI; upstream GPL `stable_lib/mcurses/mcurses.c`; and boot-only `boot/receiver_handoff_contract.c`. Startup assembly, vendor code, generated hardware definitions, Python tools, wire formats, persistent formats, pin maps, power sequencing, interrupts, and silicon workarounds were preserved.

## B. Files changed

The `.c` deletions are replacements by the corresponding `.cpp` files, not removed functionality. The pre-existing deletion of `src/lora/__init__.py` was not touched. Ignored generated provenance JSON files update during builds as before; protected generated configuration remains byte-for-byte identical.

- [.clang-format](../../.clang-format)
- [.clang-tidy](../../.clang-tidy)
- [README.md](../../README.md)
- [docs/migration/architecture.md](../../docs/migration/architecture.md)
- [docs/migration/baseline.md](../../docs/migration/baseline.md)
- [platformio.ini](../../platformio.ini)
- [src/arq/arq.h](../../src/arq/arq.h)
- `src/arq/codec.c` (removed; replaced by the matching C++ implementation)
- [src/arq/codec.cpp](../../src/arq/codec.cpp)
- [src/arq/main.cpp](../../src/arq/main.cpp)
- `src/arq/receiver.c` (removed; replaced by the matching C++ implementation)
- [src/arq/receiver.cpp](../../src/arq/receiver.cpp)
- `src/arq/sender.c` (removed; replaced by the matching C++ implementation)
- [src/arq/sender.cpp](../../src/arq/sender.cpp)
- [src/shared/reliable_transport.h](../../src/shared/reliable_transport.h)
- `src/ssot.c` (removed; replaced by the matching C++ implementation)
- [src/ssot.cpp](../../src/ssot.cpp)
- [src/ssot.h](../../src/ssot.h)
- [tests/arq/adapter_test.cpp](../../tests/arq/adapter_test.cpp)
- `tests/arq/core_test.c` (removed; replaced by the matching C++ implementation)
- [tests/arq/core_test.cpp](../../tests/arq/core_test.cpp)
- [tests/arq/directional_test.cpp](../../tests/arq/directional_test.cpp)
- `tests/ssot_protocol_test.c` (removed; replaced by the matching C++ implementation)
- [tests/ssot_protocol_test.cpp](../../tests/ssot_protocol_test.cpp)
- [tests/test_arq.py](../../tests/test_arq.py)
- [tests/test_arq_directional.py](../../tests/test_arq_directional.py)
- [tests/test_arq_radio_only.py](../../tests/test_arq_radio_only.py)
- [tests/test_cpp_migration.py](../../tests/test_cpp_migration.py)
- [tests/test_mvp_roundtrip.py](../../tests/test_mvp_roundtrip.py)
- [tests/test_reliable_transport.py](../../tests/test_reliable_transport.py)
- [tests/test_ssot_protocol.py](../../tests/test_ssot_protocol.py)
- [tools/config/platformio_generate.py](../../tools/config/platformio_generate.py)

This note is also a new file: [docs/migration/verification.md](verification.md).

## C. Architecture

The existing Arduino lifecycle and module boundaries remain. SSOT provides free functions for explicit byte encoding, bounded campaign state, duplicate filtering and command parsing. ARQ retains separate stateless codec and caller-owned sender/receiver state machines; the existing adapter owns hardware access and radio turnaround. No new class, HAL, wrapper, runtime polymorphism, dependency, dynamic allocation or hardware initialization mechanism was introduced.

Existing `.h` include paths and function names are retained. Application headers are now C++ interfaces with scoped enums; callers use scoped state names. Only genuine generated/vendor C boundaries retain C linkage. This is an intentional source-language migration, not a promise of binary compatibility with external C application clients.

## D. C++ improvements and comments

- Native structs replace typedef struct declarations; state/result enums prevent implicit conversion into wire integers. Their original native int size is retained.
- Typed constexpr constants preserve protocol codes and bounded capacities. Value initialization replaces whole-state memset; wire serializers still write each field explicitly.
- nullptr and explicit casts replace C null/cast idioms; unsigned promoted bit operations behave consistently on host and AVR.
- Private helper namespaces contain implementation details; all frame buffers and state remain statically or caller allocated.
- Google-style formatting and declaration comments document nullable pointers, buffer bounds, ownership, unchanged output on decode failure, replay/timeout rules and foreground/ISR boundaries. Comments explain contracts and non-obvious behavior, rather than narrating every assignment.
- No repository-wide license exists. Migrated headers record that fact; third-party licensing and author notices remain untouched.

## E. Verification

### Firmware

Original and final clean matrices both built **19/19 role-specific environments**. There are 21 named sections total; `debug` and `release` fail with the existing `PlatformIO environment has no radio role` error. They were neither deleted nor assigned guessed hardware roles. Aggregate all-environment command therefore exits 1; each real role target reports SUCCESS.

Commands: `pio run -t clean` followed by `pio run -v`, each with `-e` for every role target; the final matrix additionally attempted `debug` and `release`. Final role builds emitted zero compiler warnings. Verbose commands confirm gnu++17, and the four migrated modules have `-Wall -Wextra -Wshadow -Wconversion -Wsign-conversion`, with `-w`, `-fpermissive` and the narrowing-error exemption removed only from those modules. Framework/library flags remain unchanged.

Actual ELF/HEX inspection used `avr-size -A`, `avr-nm`, and the existing Intel HEX parser. All 19 emitted images start at application address zero and end below 130048; `.data` and `.bss` sizes are unchanged. This establishes linked image boundaries, not permission to program hardware.

### Host tests

Original full suite: **400 tests; 8 failures, 10 errors, 1 skip**. Final fresh run:

```text
.venv/bin/python -m unittest discover -s tests -v
Ran 402 tests in 36.830s
FAILED (failures=2, errors=7, skipped=1)
```

All 37 selected migration/consumer cases in `test_ssot_protocol`, `test_arq`, `test_arq_directional`, `test_arq_radio_only`, `test_reliable_transport`, `test_mvp_roundtrip` and `test_cpp_migration` pass in that run. Coverage includes exact DATA/ACK/NACK bytes, all 65536 ARQ sequences, 50000 bounded parser inputs with AddressSanitizer/UBSan, late/incorrect ACKs, bounded retry/exhaustion, duplicate delivery, malformed sizes, null outputs, one-attempt mode, timer rollover, and host firmware exchange simulations. Compile-time negative tests confirm state/result values cannot silently become wire integers. A failing pre-build test was observed before fixing protected-file regeneration; original C SSOT characterization was also run successfully before conversion.

Remaining failures/errors are explicitly outside the converted application logic:

| Check | Observed cause |
|---|---|
| `test_radio_915_ssot.Radio915ValidationTests.test_gateway_mainboard_profile_keeps_address_wire_shape` | Unchanged sibling `iwing-tracker` integration does not contain the expected `def configure(self, addr):` API. The initial stale-manifest failure masked this later assertion. |
| `test_receiver_boot.ApplicationPageWriteTests.test_guarded_app_writer_erases_only_its_page_with_installed_avrdude_dryrun` | Legacy assertion expects `erase flash 0x5800 0x200`; current replacement-board command uses different application geometry. No actual device access occurred. |
| `test_raw_mvp.RawMvpTests.test_legacy_boot_repair_refuses_replacement_geometry` | Missing historical `receiver-candidate-backup-flash.bin` under `artifacts/rf-proof/20261106T104722Z-target-backup/`. |
| `test_receiver_boot.CompiledHandoffTests.test_blank_or_any_wrong_reset_byte_parks` | Five existing subtest errors: boot tracer rejects instruction `0xf459` at `0x14`. |
| `test_receiver_boot.CompiledHandoffTests.test_compiled_handoff_uses_correct_byte_target_and_interrupt_state` | Same existing boot-tracer instruction error. |
| `test_receiver_boot.BootPackageTests` | Skipped: archived BOOTSIZE=44 repair does not apply to the replacement Receiver. |

The two existing host compiler warnings in `tests/radiolib_hal_test.cpp:86` (control reaches end of non-void function) are unchanged. No full-suite PASS is claimed.

### Analysis, formatting and review

- Scoped `pio check -e sender_arq -e receiver_arq --src-filters '+<src/ssot.cpp> +<src/arq/codec.cpp> +<src/arq/sender.cpp> +<src/arq/receiver.cpp>' --flags 'cppcheck: --enable=warning,performance,portability --std=c++17' --fail-on-defect high -v`: both PASS, no defects. Verbose output confirms all four implementations were analyzed in both roles.
- Clang-Tidy 23.1.4, all four implementations, configured bugprone/analyzer/performance/portability checks: exit 0. Configuration excludes API-ordering, intentional terminal-branch repetition, enum-size changes and generated-header pragma style; these are documented compatibility/style choices, not blanket defect suppression.
- Clang-Format 23.1.5 `--dry-run --Werror` over all 12 affected C++ implementations/interfaces/tests: exit 0, Google style.
- `git diff --check`: exit 0. Focused Python syntax/undefined-name Ruff checks: PASS.
- Independent code review: no remaining actionable correctness findings; fresh independent ARQ 11/11, SSOT 2/2 and migration 2/2 passed. Review identified a malformed comment edit; it was corrected and all final builds/tests above ran afterward.
- Full-tree Cppcheck was also run on original and converted trees. Both report the same four high findings: three internal AST errors in existing protothread-based sender code and `legacyUninitvar` at `stable_lib/lora/lora.cpp:86`. The latter follows the existing successful RadioLib `readData(buffer, frame_length)` output call. No new high finding was introduced, and no clean full-tree analysis is claimed.

### Hardware

NOT TESTED. No upload, fuse/EEPROM operation, boot/persistent write, serial connection or RF transmission occurred. Host simulations are not physical SPI/RF evidence.

## F. Resource comparison

Flash is `.text + .data`; static RAM is `.data + .bss + .noinit`, in bytes. All static-RAM deltas are zero.

| Image | Flash before | Flash after | Delta | RAM before | RAM after |
|---|---:|---:|---:|---:|---:|
| `receiver` | 34442 | 34442 | +0 | 3579 | 3579 |
| `receiver_5dbm` | 34442 | 34442 | +0 | 3579 | 3579 |
| `receiver_arq` | 36534 | 36530 | -4 | 5234 | 5234 |
| `receiver_arq_radio_only` | 39038 | 38976 | -62 | 5312 | 5312 |
| `receiver_arq_radio_only_reverse` | 37892 | 37810 | -82 | 5256 | 5256 |
| `receiver_arq_test` | 38558 | 38554 | -4 | 5268 | 5268 |
| `receiver_mvp` | 31570 | 31570 | +0 | 1390 | 1390 |
| `receiver_reverse_raw` | 30738 | 30738 | +0 | 4485 | 4485 |
| `receiver_spi` | 30928 | 30928 | +0 | 3301 | 3301 |
| `sender` | 37054 | 37054 | +0 | 6817 | 6817 |
| `sender_arq` | 37460 | 37378 | -82 | 5226 | 5226 |
| `sender_arq_radio_only` | 37498 | 37416 | -82 | 5238 | 5238 |
| `sender_arq_radio_only_reverse` | 38616 | 38584 | -32 | 5292 | 5292 |
| `sender_arq_test` | 37460 | 37378 | -82 | 5226 | 5226 |
| `sender_hello` | 34670 | 34670 | +0 | 3611 | 3611 |
| `sender_hello_5dbm` | 34670 | 34670 | +0 | 3611 | 3611 |
| `sender_hello_spi` | 30862 | 30862 | +0 | 3303 | 3303 |
| `sender_mvp` | 31016 | 31016 | +0 | 1360 | 1360 |
| `sender_reverse_raw` | 31868 | 31868 | +0 | 4666 | 4666 |

| Section | sender before/after | receiver before/after | sender_arq before/after | receiver_arq before/after |
|---|---:|---:|---:|---:|
| `.text` | 36112 / 36112 | 33392 / 33392 | 36112 / 36030 | 35182 / 35178 |
| `.data` | 942 / 942 | 1050 / 1050 | 1348 / 1348 | 1352 / 1352 |
| `.bss` | 5875 / 5875 | 2529 / 2529 | 3878 / 3878 | 3882 / 3882 |

| Metric | Before | After | Delta |
|---|---|---|---|
| Largest migrated per-function stack estimate | 54 bytes, arq_decode | 54 bytes, arq_decode | 0 |
| Runtime stack high-water / ISR nesting | Unknown | Unknown | N/A |
| Runtime heap high-water / fragmentation | Unknown | Unknown | N/A |
| Migrated object references to malloc/new/exception runtime | None | None | None introduced |

Stack estimates used AVR GCC/G++ 7.3.0 with `-Os -fno-lto -fstack-usage`, compiling the original C and final C++ modules separately. They are not production-LTO worst-case call-chain or interrupt-stack measurements. Other largest frames are unchanged: sender request 19 bytes, control input/sender control/receiver DATA 14 bytes. Existing linked framework images still contain allocator support; no claim of whole-firmware allocation freedom or measured heap stability is made. An inactive legacy `src/sender/main.cpp` also retains its existing `new Module(...)` initialization.

## G. Risks and limits

Physical boot/power/SPI/RF behavior, loop/ISR latency, actual stack/heap high-water, watchdog behavior under load and extended hardware reliability remain NOT TESTED. Native enum sizes were retained; pin maps, startup calls, timers, volatile/ISR code and persistence operations were not redesigned. Hardware validation needs a separate authorized write and the established test setup. The missing historical binary cannot be reconstructed as evidence. Boot/integration failures and full-tree analyzer limitations remain visible rather than being hidden by weakened assertions.

## H. Final assessment

| Area | Status |
|---|---|
| Handwritten C application migration | IMPLEMENTED; all four modules are C++17 |
| All 19 actual firmware role targets | PASS, clean builds |
| Roleless debug/release templates | Existing FAIL, no radio role |
| Migration/consumer tests | PASS, 37 selected cases |
| Full automated suite | FAIL: 2 failures, 7 errors, 1 skip across 402 tests |
| Migrated-module static analysis | PASS |
| Full-tree static analysis | Existing limitations/findings remain |
| Formatting and diff whitespace | PASS |
| Flash/static RAM regression | None; ARQ Flash decreases up to 82 bytes |
| Protected configuration checksum comparison | PASS, no changes |
| Physical hardware/RF verification | NOT TESTED |

Overall: application migration is complete; full project/production acceptance remains PARTIAL until the listed external/legacy checks and authorized physical validation are resolved. No commit or push was made.
