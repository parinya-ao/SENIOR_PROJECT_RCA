# Embedded C++ readability refactor verification

## 1. Summary

Completed the host-verifiable readability/configuration refactor on top of the
previous C++ migration. Firmware uses the existing C++17 Arduino/PlatformIO
runtime. No dependencies, schedulers, virtual interfaces or heap allocations
were added. Board/PHY/generated/boot files and both wire protocols are preserved.
The only intentional behavior correction is the gateway I2C task retaining its
received length after consuming the mailbox; valid configuration previously
always reached the decoder with length zero.

## 2. Architecture before and after

Previously `arq/main.cpp` combined startup, commands, event formatting, queue
storage, radio integration and protocol orchestration. It is now a 15-line
Arduino entry point. `application.cpp` coordinates hardware effects; `commands`
owns parsing/line lifetime; `diagnostics` owns one queue and event formatting.
Separate codec/sender/receiver headers expose the portable contracts. Include-only
`arq.h` remains convenient for callers using both directions.

SSOT wire logic remains in `ssot.cpp`; campaign/duplicate state and command input
moved to `ssot/session.cpp` and `ssot/control_input.cpp`. The two protocols remain
distinct. The existing template transport stays in its header because native and
hardware radio types instantiate it without runtime dispatch. See the complete
[module/entry-point/flow map](../architecture.md).

## 3. C++ refactoring

Application protocol types/functions use `arq` and `ssot` namespaces, PascalCase
APIs/types, `kPascalCase` constants/enumerators and explicit conversions. Native
state enum representation and field-by-field wire encoding are unchanged.
`reliable::Transport<Radio>` retains borrowed radio/callback lifetimes. Sender
Wire mailbox/task state is private; required Arduino hooks and task callbacks
keep their signatures. `CommandInput` is the only new stateful class, justified
by its owned bounded buffer and overflow/recovery invariant.

## 4. Readability and configuration

Naming/comments/formatting follow the applicable
[Google C++ guide](https://google.github.io/styleguide/cppguide.html), with the
requested `.cpp` extension and supported C++17 toolchain. Contracts describe
nullable buffers, unchanged outputs on decode failure, state transitions,
rollover assumptions, foreground ownership and hardware sequencing. Retained
hardware macros and external callback names remain exceptions. Comments explain
constraints rather than every assignment.

`config/application.toml` is the application policy source. Its renderer writes
only `include/application_config.h`; builds reject stale policy. Existing SSOT
owns pins/PHY/protocol values. Diagnostic IDs derive from generated IDs rather
than repeated literals. Raw/ARQ host commands and capture validation consume the
same configured payloads. Capacities are bounded, result buffers must be powers
of two, and radio-only tests remain restricted to one attempt.

Independent review found three configuration gaps: a missing power-of-two check,
a raw command buffer too small for the permitted payload, and host-side payload
literals. Regression tests reproduced all three before their fixes. Tests now
compile the real raw firmware with a configured 32-byte payload and verify that
its exact bytes reach the simulated transmitter. A stale fixed-timeout comment
was corrected. No review findings were waived.

## 5. Files changed

Added application/config/tool modules:

- [config/application.toml](../../config/application.toml)
- [include/application_config.h](../../include/application_config.h)
- [src/arq/application.cpp](../../src/arq/application.cpp)
- [src/arq/application.h](../../src/arq/application.h)
- [src/arq/codec.h](../../src/arq/codec.h)
- [src/arq/commands.cpp](../../src/arq/commands.cpp)
- [src/arq/commands.h](../../src/arq/commands.h)
- [src/arq/config.h](../../src/arq/config.h)
- [src/arq/diagnostics.cpp](../../src/arq/diagnostics.cpp)
- [src/arq/frame.h](../../src/arq/frame.h)
- [src/arq/receiver.h](../../src/arq/receiver.h)
- [src/arq/sender.h](../../src/arq/sender.h)
- [src/ssot/codec.h](../../src/ssot/codec.h)
- [src/ssot/control_input.cpp](../../src/ssot/control_input.cpp)
- [src/ssot/control_input.h](../../src/ssot/control_input.h)
- [src/ssot/session.cpp](../../src/ssot/session.cpp)
- [src/ssot/session.h](../../src/ssot/session.h)
- [tools/config/application_config.py](../../tools/config/application_config.py)

Modified application/config/tool files relative to the preceding migration:

- [src/arq/arq.h](../../src/arq/arq.h)
- [src/arq/codec.cpp](../../src/arq/codec.cpp)
- [src/arq/diagnostics.h](../../src/arq/diagnostics.h)
- [src/arq/main.cpp](../../src/arq/main.cpp)
- [src/arq/radio_only.h](../../src/arq/radio_only.h)
- [src/arq/receiver.cpp](../../src/arq/receiver.cpp)
- [src/arq/sender.cpp](../../src/arq/sender.cpp)
- [src/mvp/main.cpp](../../src/mvp/main.cpp)
- [src/receiver/main.cpp](../../src/receiver/main.cpp)
- [src/reliable/main.cpp](../../src/reliable/main.cpp)
- [src/reverse_raw/main.cpp](../../src/reverse_raw/main.cpp)
- [src/sender/lib/espcomm.cpp](../../src/sender/lib/espcomm.cpp)
- [src/sender/lib/espcomm.h](../../src/sender/lib/espcomm.h)
- [src/sender/lib/io.cpp](../../src/sender/lib/io.cpp)
- [src/sender/lib/io.h](../../src/sender/lib/io.h)
- [src/sender/lib/lora_config.h](../../src/sender/lib/lora_config.h)
- [src/sender/lib/lora_rx.cpp](../../src/sender/lib/lora_rx.cpp)
- [src/sender/lib/lora_rx.h](../../src/sender/lib/lora_rx.h)
- [src/sender/lib/main.cpp](../../src/sender/lib/main.cpp)
- [src/sender/lib/main.h](../../src/sender/lib/main.h)
- [src/sender/lib/stable_lora.cpp](../../src/sender/lib/stable_lora.cpp)
- [src/sender/main.cpp](../../src/sender/main.cpp)
- [src/shared/hello_config.h](../../src/shared/hello_config.h)
- [src/shared/reliable_transport.h](../../src/shared/reliable_transport.h)
- [src/ssot.cpp](../../src/ssot.cpp)
- [src/ssot.h](../../src/ssot.h)
- [tools/arq_trial.py](../../tools/arq_trial.py)
- [tools/config/platformio_generate.py](../../tools/config/platformio_generate.py)
- [tools/rf_proof.py](../../tools/rf_proof.py)

Added tests:

- [tests/arq/commands_test.cpp](../../tests/arq/commands_test.cpp)
- [tests/arq/diagnostics_test.cpp](../../tests/arq/diagnostics_test.cpp)
- [tests/arq/diagnostics_test_access.h](../../tests/arq/diagnostics_test_access.h)
- [tests/gateway_i2c_test.cpp](../../tests/gateway_i2c_test.cpp)
- [tests/gateway_stub/Wire.h](../../tests/gateway_stub/Wire.h)
- [tests/test_application_config.py](../../tests/test_application_config.py)
- [tests/test_cpp_interfaces.py](../../tests/test_cpp_interfaces.py)
- [tests/test_gateway_i2c.py](../../tests/test_gateway_i2c.py)

Updated test consumers:

- [tests/arq/adapter_test.cpp](../../tests/arq/adapter_test.cpp)
- [tests/arq/directional_test.cpp](../../tests/arq/directional_test.cpp)
- [tests/mvp_board.cpp](../../tests/mvp_board.cpp)
- [tests/raw_mvp_test.cpp](../../tests/raw_mvp_test.cpp)
- [tests/rca_send_test.cpp](../../tests/rca_send_test.cpp)
- [tests/receiver_gpio_test.cpp](../../tests/receiver_gpio_test.cpp)
- [tests/reliable_app_test.cpp](../../tests/reliable_app_test.cpp)
- [tests/reliable_transport_test.cpp](../../tests/reliable_transport_test.cpp)
- [tests/reverse_raw_test.cpp](../../tests/reverse_raw_test.cpp)
- [tests/test_arq.py](../../tests/test_arq.py)
- [tests/test_arq_directional.py](../../tests/test_arq_directional.py)
- [tests/test_arq_radio_only.py](../../tests/test_arq_radio_only.py)
- [tests/test_mvp_roundtrip.py](../../tests/test_mvp_roundtrip.py)
- [tests/test_raw_mvp.py](../../tests/test_raw_mvp.py)
- [tests/test_rca.py](../../tests/test_rca.py)
- [tests/test_receiver_hardware.py](../../tests/test_receiver_hardware.py)
- [tests/test_reliable_transport.py](../../tests/test_reliable_transport.py)
- [tests/test_reverse_raw.py](../../tests/test_reverse_raw.py)
- [tests/test_rf_proof.py](../../tests/test_rf_proof.py)
- [tests/test_sender_one_shot.py](../../tests/test_sender_one_shot.py)
- [tests/test_ssot_protocol.py](../../tests/test_ssot_protocol.py)

Also updated `.clang-format`, `.clang-tidy`, `platformio.ini`, README and this
architecture/verification documentation. No additional source-file deletion was
needed in this phase. Earlier `.c` → `.cpp` replacements remain in the working
tree. The pre-existing deletion of `src/lora/__init__.py` was preserved.

## 6. Verification

All commands below were executed; hardware was not accessed.

| Check | Observed result |
|---|---|
| Baseline host suite | 402 tests; two failures, seven errors, one skip |
| Clean all 19 role environments | PASS, each explicitly selected with `-e` |
| Rebuild all 19 with `pio run ... -v` | PASS; zero compiler warnings; 52.040 s |
| Effective compiler commands | 63 strict compilations across eight modules; `gnu++17`, all five warning flags, no `-w`/`-fpermissive` |
| Actual HEX bounds | All 19 start at zero and end within 130048 bytes |
| Final `.venv/bin/python -m unittest discover -s tests -v` | 413 tests in 42.037 s; two failures, seven errors, one skip; no new failure signatures |
| Scoped PlatformIO Cppcheck on both ARQ roles | PASS; no defects, including new ARQ/SSOT modules |
| Full-tree Cppcheck across sender/receiver/ARQ roles | FAIL; same four unique baseline findings repeated across roles |
| Clang-Tidy 23.1.4, eight portable/diagnostic implementations | PASS; configured checks, warnings treated as errors; hardware headers stubbed for host parsing |
| Clang-Format 23.1.5 dry run | PASS; 58 source/header/test files |
| Focused Ruff syntax/undefined-name checks | PASS on modified Python files |
| `git diff --check` | PASS |
| Protected file SHA-256 comparison | Unchanged |
| Provenance manifests | Both equal current source-derived artifacts |
| Direct host CLI `--help` | Both arq_trial and rf_proof execute successfully |
| Independent read-only review | Three P2 findings fixed with regression tests |
| Physical firmware, SPI, RF, timing/soak | NOT TESTED; no flashing authorized |

Strict diagnostics apply only to project modules. DxCore's existing conversion
warnings are excluded locally around its Arduino include in diagnostics.cpp,
then restored for application code. Framework/compiler settings are unchanged.
The AVR compiler rejected marking Arduino headers as system headers because it
changed linkage; those flags were removed and the final build verifies their
absence.

Reproducible focused commands:

```sh
.venv/bin/python -m unittest tests.test_application_config tests.test_cpp_interfaces tests.test_gateway_i2c -v
pio check -e sender_arq -e receiver_arq --src-filters '+<src/arq/> +<src/ssot.cpp> +<src/ssot/>' --flags 'cppcheck: --enable=warning,performance,portability --std=c++17' --fail-on-defect high
uvx --from clang-tidy clang-tidy src/ssot.cpp src/ssot/session.cpp src/ssot/control_input.cpp src/arq/codec.cpp src/arq/sender.cpp src/arq/receiver.cpp src/arq/commands.cpp src/arq/diagnostics.cpp -- -std=c++17 -Isrc -Iinclude -Itests/arq/stub -Itests/raw_mvp_stub -DLORA_ROLE_SENDER=1
```

The remaining host failures are the same as the fresh baseline:

- `Radio915ValidationTests.test_gateway_mainboard_profile_keeps_address_wire_shape`:
  the external ESP32 sibling lacks the expected address-only configure method.
- `ApplicationPageWriteTests.test_guarded_app_writer_erases_only_its_page_with_installed_avrdude_dryrun`:
  historical boot/page geometry differs from the replacement target.
- `RawMvpTests.test_legacy_boot_repair_refuses_replacement_geometry`: historical
  receiver backup fixture is missing.
- `CompiledHandoffTests.test_blank_or_any_wrong_reset_byte_parks` (five subcases)
  and `test_compiled_handoff_uses_correct_byte_target_and_interrupt_state`: the
  existing host boot tracer rejects instruction `0xf459` at address `0x14`.

The skipped boot-package case is inapplicable to replacement receiver geometry.
Two existing host RadioLib-HAL test warnings about a non-void function remain.
Full-tree Cppcheck reports three protothread macro AST errors in sender tasks
and the existing `legacyUninitvar` finding in `stable_lib/lora/lora.cpp:86`;
the buffer is filled by the successful driver read before use. No broad static
analysis PASS is claimed. Roleless `debug` and `release` still fail with
`PlatformIO environment has no radio role`; all 19 actual role targets build.

## 7. Memory and performance

Flash is `.text + .data`; static RAM is `.data + .bss`, in bytes. Before means the
verified preceding C++ migration snapshot, not an inferred original C size.

| Environment | Flash before | Flash after | Delta | RAM before | RAM after | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `receiver` | 34442 | 34438 | -4 | 3579 | 3579 | +0 |
| `receiver_5dbm` | 34442 | 34438 | -4 | 3579 | 3579 | +0 |
| `receiver_arq` | 36530 | 36550 | +20 | 5234 | 5234 | +0 |
| `receiver_arq_radio_only` | 38976 | 39006 | +30 | 5312 | 5312 | +0 |
| `receiver_arq_radio_only_reverse` | 37810 | 37974 | +164 | 5256 | 5256 | +0 |
| `receiver_arq_test` | 38554 | 38566 | +12 | 5268 | 5268 | +0 |
| `receiver_mvp` | 31570 | 31572 | +2 | 1390 | 1392 | +2 |
| `receiver_reverse_raw` | 30738 | 30872 | +134 | 4485 | 4443 | -42 |
| `receiver_spi` | 30928 | 30924 | -4 | 3301 | 3301 | +0 |
| `sender` | 37054 | 37078 | +24 | 6817 | 6814 | -3 |
| `sender_arq` | 37378 | 37546 | +168 | 5226 | 5226 | +0 |
| `sender_arq_radio_only` | 37416 | 37584 | +168 | 5238 | 5238 | +0 |
| `sender_arq_radio_only_reverse` | 38584 | 38582 | -2 | 5292 | 5292 | +0 |
| `sender_arq_test` | 37378 | 37546 | +168 | 5226 | 5226 | +0 |
| `sender_hello` | 34670 | 34666 | -4 | 3611 | 3611 | +0 |
| `sender_hello_5dbm` | 34670 | 34666 | -4 | 3611 | 3611 | +0 |
| `sender_hello_spi` | 30862 | 30858 | -4 | 3303 | 3303 | +0 |
| `sender_mvp` | 31016 | 31016 | +0 | 1360 | 1360 | +0 |
| `sender_reverse_raw` | 31868 | 31856 | -12 | 4666 | 4646 | -20 |

| Metric | Before | After | Interpretation |
|---|---:|---:|---|
| ARQ foreground loop compiler stack frame | 182 B | 181 B | Separate `-Os -fno-lto -fstack-usage` compile; excludes callees/runtime high-water |
| ARQ decoder compiler stack frame | 54 B | 54 B | Same limited measurement |
| ARQ request compiler stack frame | 19 B | 19 B | Same limited measurement |
| New command parser compiler stack frame | N/A | 12 B | Call-path total is not established by this number |
| Heap stability / runtime stack / interrupt latency | Unknown | Unknown | No hardware measurement |

A first diagnostics extraction increased ARQ Flash by roughly 2–3 KiB. AVR symbol
sizes traced most growth to per-call aggregate context packing in the main loop.
Borrowing live context fields removed that growth without adding static RAM.
The final largest ARQ increase is 168 B (under 0.5% of its baseline image), for
separated command handling and bounded diagnostic formatting. RadioLib code and
its runtime behavior were not replaced. The gateway length fix and removal of an
unused task timestamp reduce static RAM by three bytes. Payload-sized raw command
storage saves RAM. The raw receiver's 134 B Flash increase implements configured
hex matching; the MVP receiver's two RAM bytes reflect configured string storage.
No runtime speedup or heap-safety claim is inferred from image sizes.

## 8. Remaining risks

- Physical startup, GNSS/SD isolation, SPI/RF turnaround, reset and long-running
  reliability require authorized hardware validation. No fuses, EEPROM or Flash
  were written.
- Wire callers must still respect readiness. The existing callback/task mailbox
  synchronization design was preserved; its byte-wide volatile latches do not
  guarantee atomic multi-byte buffer access.
- The excluded SX1262 experiment has no configured target and is unverified.
  Generated board C, vendor C and boot boundaries intentionally remain unchanged.
- Existing external/archived boot test failures prevent a fully green repository
  suite. They were not hidden, bypassed or repaired by unrelated changes.

## 9. Final assessment

Implementation and all feasible build/protocol/readability/configuration checks
are complete. Overall acceptance is **partially completed**: hardware validation
is NOT TESTED and the repository-wide host/static baselines remain failing as
listed above. No new full-suite failure signature remains. No commit, rebase,
push, upload or physical transmission was performed.
