# Offline LoRa firmware refactor

This report records the first ownership pass. The current source layout, fresh matrix, and standalone BOOT comparison are in [Source ownership V2](SOURCE_OWNERSHIP_V2.md).

## Application and dependency audit

| Responsibility | Before | After |
| --- | --- | --- |
| Arduino lifecycle | `src/main.cpp` forwarded three hooks through a common dispatcher | Sender and Receiver own `src/{sender,receiver}/appcode/main.cpp`. The source filter selects one physical board entry per target. Gateway retains DxCore's default early hook, and all other configured variants retain the protected CPUINT write. |
| Gateway scheduling, GPIO, I2C mailbox and radio transaction | `stable_lib/gateway_app` and `src/app/gateway_radio.cpp` | `src/sender/appcode/gateway`, selected for `sender`. |
| Reliable startup and transaction control | One role-conditional `src/app/reliable_app.cpp` | Each role owns its GPIO, LED, and transaction actions. The reliable application shares transport event reporting, UART dispatch and payload acceptance. |
| ARQ foreground and radio startup | `stable_lib/arq/application.cpp` owned both protocol states and raw radio startup | `src/app/arq/application.cpp` owns one state per DATA direction. `src/app/arq/radio.cpp` owns the raw radio, SPI readback and startup profile. The portable codec, state machines, diagnostics and generated board file remain in `stable_lib/arq`. |
| Addressed radio header | SSOT codec and LoRa adapter each packed and unpacked it | Both use the four-byte SSOT header codec. `LoRa` still owns the addressed RadioLib adapter. |

The obsolete dispatcher and the `firmware-app`, `gateway-app` and `reliable-app` manifests were removed. The inactive `LORA_APP_LEGACY_SENDER` and `LORA_APP_LEGACY_RECEIVER` selectors were retired from lifecycle selection. Their source remains under `stable_lib`, and none of the 19 configured targets used either selector. Gate 1 provenance now hashes both migrated ARQ source files. The historical Gate 1 integrity policy still applies.

All 19 builds resolved RadioLib 7.1.2 and Time 1.6.1. PlatformIO now lists the Gateway's existing Wire, debug and AVR support dependencies directly. Its source scanner also lists `iw_core` for the other Sender targets. Their maps show only their selected application objects. Receiver targets dropped the unused `task` discovery, and the raw reverse targets dropped the unused `arq` discovery. No package was added or upgraded. The board configurations, generated role headers, radio profile, linker origins and upload settings were preserved.

## Wire and host evidence

- **SSOT** uses destination, source, then the little-endian campaign ID. With campaign `0x1234` and sequence `1`, the full DATA is `01 00 34 12 08 01 68 65 6C 6C 6F 20 77 6F 72 6C 64`. The ACK is `00 01 34 12 03 01` and the NACK is `00 01 34 12 09 01`. Decoding checks wire structure, and the application callback checks all 11 payload bytes before accepting DATA.
- **ARQ** keeps its versioned 12-byte header, 32-bit session and 16-bit sequence. The directional bench compares every DATA, ACK and NACK byte in both directions and checks STATUS fields against the pre-move adapter. Reverse direction swaps initiator and responder while retaining the Sender and Receiver board pins, power sequencing and identities.
- **MVP and reverse raw** retain their existing raw 11-byte `Hello World` frames and independent command and radio behavior. The fixtures check the whole byte string, including the case and absence of a terminator.
- Host tests exercise wrong destination, peer, session and sequence, malformed frames, corrupted payloads, dropped or delayed replies, duplicate delivery, bounded retry exhaustion, wrapping deadlines, radio faults and blocked diagnostic consumers. The source-selection contract failed against the old dispatcher and passed with one role entry point per target. Source fixtures and the static-analysis filters follow the new paths.

## Firmware matrix

Flash and static SRAM are bytes, with differences from the approved baseline in parentheses. The highest byte in each HEX is one less than the reported exclusive end. All images start at `0x0000` and fit below the configured exclusive limit `0x1FC00`.

| Target | Build | Flash (delta) | Static SRAM (delta) | Flash end |
| --- | --- | ---: | ---: | ---: |
| `sender` | PASS | 38,792 (-28) | 7,079 (+0) | `0x9788` |
| `sender_hello` | PASS | 36,832 (+0) | 4,009 (+0) | `0x8FE0` |
| `receiver` | PASS | 35,868 (-40) | 3,849 (+7) | `0x8C1C` |
| `sender_hello_spi` | PASS | 31,492 (+0) | 3,482 (+0) | `0x7B04` |
| `sender_hello_5dbm` | PASS | 36,832 (+0) | 4,009 (+0) | `0x8FE0` |
| `receiver_5dbm` | PASS | 35,868 (-40) | 3,849 (+7) | `0x8C1C` |
| `receiver_spi` | PASS | 31,548 (+0) | 3,478 (+0) | `0x7B3C` |
| `sender_mvp` | PASS | 31,018 (+0) | 1,360 (+0) | `0x792A` |
| `receiver_mvp` | PASS | 31,578 (+0) | 1,392 (+0) | `0x7B5A` |
| `sender_arq` | PASS | 37,014 (-548) | 5,200 (-26) | `0x9096` |
| `receiver_arq` | PASS | 35,804 (-852) | 5,044 (-190) | `0x8BDC` |
| `sender_arq_test` | PASS | 37,014 (-548) | 5,200 (-26) | `0x9096` |
| `receiver_arq_test` | PASS | 36,862 (-854) | 5,072 (-190) | `0x8FFE` |
| `sender_arq_radio_only` | PASS | 37,048 (-552) | 5,212 (-26) | `0x90B8` |
| `receiver_arq_radio_only` | PASS | 37,252 (-782) | 5,116 (-188) | `0x9184` |
| `sender_reverse_raw` | PASS | 31,850 (+0) | 4,646 (+0) | `0x7C6A` |
| `sender_arq_radio_only_reverse` | PASS | 36,836 (-814) | 5,096 (-190) | `0x8FE4` |
| `receiver_arq_radio_only_reverse` | PASS | 37,460 (-508) | 5,230 (-26) | `0x9254` |
| `receiver_reverse_raw` | PASS | 30,946 (+0) | 4,443 (+0) | `0x78E2` |

Linker maps show one physical role entry object in each image. Symbol inspection confirms one Arduino `main` entry and, for every ARQ image, only the selected protocol direction's state. The ELF and Intel HEX Flash addresses agree for loadable `.text` and initialized `.data`. Reset disassembly reaches Arduino startup from each vector, with the reviewed CPUINT write for the variants that use it. `debug` and `release` are retained as role-less profiles. Direct builds reached the expected role check and rejected each profile before linking. Static SRAM counts exclude run-time stack high-water usage.

## Historical BOOT and deployment status

Build the archived fixture in a new directory with `.venv/bin/python tools/receiver_boot.py /tmp/receiver-handoff-fixture`. It uses the historical freestanding AVR-GCC recipe and produces ELF, map, disassembly, HEX, binary and instruction traces. The fixture occupies 48 bytes at `[0x0000, 0x0030)`. Its four-byte guard accepts `52 C0 00 00` before jumping to `0x5800`. Blank Flash or changing any guarded byte reaches the park loop with interrupts disabled and CPUINT cleared. The historical package still requires its original backup integrity, fuse geometry, page bounds and write authorization checks.

**Active BOOT/APPCODE pairing and FOTA acceptance are BLOCKED.** The configured Receiver has `BOOTSIZE=0` and its application starts at `0x0000`. The AVR DA fuse geometry assigns all Flash to BOOT at that setting, with no distinct APPCODE partition. The fixture also starts at `0x0000` and expects an application at `0x5800` with the historical reset vector. The active Receiver reset bytes are `5E C0 00 00`. The repository has a historical handoff and provisioning-key reader. SD staging, authenticated image installation and installation recovery require an approved split layout and installer scope. [Microchip AVR DA Flash section reference](https://onlinedocs.microchip.com/oxy/GUID-CBA6F7C8-69DB-44BF-ACE3-6949CC30E98A-en-US-5/GUID-1FBA83BB-35A7-4B9D-A92E-8A9C7CB8DED6.html)

**Physical RF exchange, RF timing, device fuse readback and power-failure recovery are NOT TESTED.** All verification was offline.

## Verification

- PlatformIO built all 19 role-bearing targets with zero compiler warnings. `avr-nm`, `avr-objdump`, the linker maps and Intel HEX addresses were checked for all 19 images.
- The complete Python-driven host suite ran 432 tests. 431 passed and the archived programming-package test was skipped because the configured Receiver geometry differs from the historical one. The command-local Git excludes override isolated the temporary repository fixture from the workstation's global ignore rules.
- `.venv/bin/python tools/config/generate_lora_config.py --check` verified the checked-in generated configuration and current build provenance. Graphify was refreshed and the patch passed `git diff --check`.
- `scripts/quality/check_cpp.sh` exited zero. Its formatter, Clang-Tidy, Clang Static Analyzer, IWYU, clang-doc, Lizard, jscpd, Doxygen, five clean AVR builds, and host suite passed. The gate retains its existing unsupported LLVM cases for native AVR, TimeUtils and parts of Gateway integration.
- Local evidence is under `/tmp/lora-offline-refactor`, including the matrix and host logs, per-target symbol and startup dumps, and the standalone handoff artifacts.
