# C++ migration baseline

Measured on 2026-11-16 before application conversion. Original firmware builds ran in a scratch copy so the original pre-build generator could not rewrite protected SSOT files in this checkout. No physical devices were accessed.

## Hardware and build

- AVR128DA28, 8-bit AVR DA, 131072 bytes Flash, 16384 bytes SRAM, 512 bytes EEPROM; PlatformIO board `AVR128DA28`.
- Installed PlatformIO Core 6.2.0, atmelmegaavr, Arduino DxCore 1.6.2, AVR GCC/G++ 7.3.0; effective CPU flag `F_CPU=24000000L`.
- Effective C++ flag already `-std=gnu++17`; C uses `-std=gnu11`. AVR toolchain does **not** provide `<cstdint>` (fresh compile probe failed). Retain `<stdint.h>`/`<stddef.h>` without adding an STL dependency.
- Existing flags disable exceptions, RTTI, thread-safe statics and cxa atexit; optimization `-Os`, LTO, function/data sections. Baseline builds silence diagnostics with `-w`; successful builds alone do not establish warning cleanliness.
- Existing dependencies remain RadioLib 7.1.2 and Time 1.6.1. Pin maps, PHY, app range 0..130048, protected Flash and startup sequencing remain unchanged.

## Original results

`pio run -v`: sender and receiver PASS. `pio run` with every named environment: all 19 role-specific targets PASS; `debug` and `release` FAIL with `PlatformIO environment has no radio role`. They are existing roleless configuration templates, not usable standalone firmware targets.

| Default image | Flash | Static RAM |
|---|---:|---:|
| sender | 37054 | 6817 |
| receiver | 34442 | 3579 |

Full original host suite (`.venv/bin/python -m unittest discover -s tests -v`): 400 tests, 8 failures, 10 errors, 1 skipped. This is a failing baseline; the original firmware does build. Failure names and causes are retained in the final verification note. Existing golden-byte SSOT and ARQ tests characterize serialization, malformed frames, bounded retries, all 65536 ARQ sequences, 50000 parser inputs, duplicate delivery, late ACKs and timer wraparound.

## Source inventory

Generated snapshots in `docs/rca`, `.pio` packages, third-party libraries, Python host tooling, startup/boot contracts and generated configuration are not application rewrite targets. No `.ino` application files exist.

| Implementation | Ownership / responsibility |
|---|---|
| `src/arq/board_ssot.c` | Preserve: generated GPIO/power configuration |
| `src/arq/codec.c` | Migrate: portable ARQ protocol/state machine |
| `src/arq/main.cpp` | C++ application/integration |
| `src/arq/receiver.c` | Migrate: portable ARQ protocol/state machine |
| `src/arq/sender.c` | Migrate: portable ARQ protocol/state machine |
| `src/mvp/main.cpp` | C++ application/integration |
| `src/receiver/main.cpp` | C++ application/integration |
| `src/reliable/main.cpp` | C++ application/integration |
| `src/reverse_raw/main.cpp` | C++ application/integration |
| `src/sender/lib/espcomm.cpp` | C++ application/integration |
| `src/sender/lib/io.cpp` | C++ application/integration |
| `src/sender/lib/lora_rx.cpp` | C++ application/integration |
| `src/sender/lib/main.cpp` | C++ application/integration |
| `src/sender/lib/stable_lora.cpp` | C++ application/integration |
| `src/sender/main.cpp` | C++ application/integration |
| `src/ssot.c` | Migrate: protocol, campaign state, duplicate filter and command parser |
| `lib/iw_avr128da28/src/adc.cpp` | C++ application/integration |
| `lib/iw_avr128da28/src/provisioning.cpp` | C++ application/integration |
| `lib/iw_avr128da28/src/routing.cpp` | C++ application/integration |
| `lib/iw_core/src/byte_codec.cpp` | C++ application/integration |
| `lib/iw_tracker_radio_protocol/src/codec.cpp` | C++ application/integration |
| `lib/printf/src/printf.cpp` | C++ application/integration |
| `lib/sleep/src/sleep.cpp` | C++ application/integration |
| `lib/task/src/task.cpp` | C++ application/integration |
| `lib/time-utils/src/time-utils.cpp` | C++ application/integration |
| `lib/updi_uart/src/updi_uart.c` | Preserve: C ABI wrapper including third-party C implementation |
| `stable_lib/gnss/gnss.cpp` | C++ application/integration |
| `stable_lib/logger/logger.cpp` | C++ application/integration |
| `stable_lib/lora/lora.cpp` | C++ application/integration |
| `stable_lib/mcurses/mcurses-printf.cpp` | C++ application/integration |
| `stable_lib/mcurses/mcurses.c` | Preserve: upstream GPL terminal library |
| `stable_lib/printf/printf.cpp` | C++ application/integration |
| `stable_lib/raw-storage/raw-storage.cpp` | C++ application/integration |
| `stable_lib/sd-utils/sd-utils.cpp` | C++ application/integration |
| `stable_lib/sleep/sleep.cpp` | C++ application/integration |
| `stable_lib/task/task.cpp` | C++ application/integration |
| `stable_lib/time-utils/time-utils.cpp` | C++ application/integration |
| `boot/receiver_handoff.S` | Preserve: boot assembly/compile-time hardware contract |
| `boot/receiver_handoff_contract.c` | Preserve: boot assembly/compile-time hardware contract |

## Dependencies and risks

SSOT free functions are consumed by the sender HAL, receiver, and shared reliable transport; host protocol/transport/application tests also compile them. ARQ codec, sender and receiver state are consumed by `src/arq/main.cpp`; the hardware adapter owns radio I/O and TX/RX transitions. ARQ and SSOT use different existing wire formats; their numeric packet types must never be merged. Neither protocol serializes native structs.

Protocol/state modules own no peripherals and allocate no heap memory. Callers own all input/output buffers and state. Generated `board_ssot.c` retains a necessary C linkage boundary into Arduino firmware; upstream UPDI UART retains its `_Bool`/C interface. Interrupt handlers, register sequencing, volatile flags and persistent storage stay in their existing C++/vendor implementations.

No repository-wide license is declared. Preserve existing third-party notices and record this fact in migrated source headers; do not invent a license grant. Hardware timing, RF interoperability, ISR latency, full stack high-water and long-running reliability require separately authorized hardware validation.
