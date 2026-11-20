# LoRa source ownership V2

## A. Situation

At `3f9f3f0`, each physical board already had an Arduino entry point. Both entries still relied on a common reliable application and an ARQ application with conditional transaction roles. The historical Receiver handoff lived outside both board trees.

```text
src/
├── app/
│   ├── arq/ (application.cpp, arq_application.h, radio.cpp, radio.h)
│   ├── campaign_id.h
│   └── reliable_app.cpp, reliable_app.h, reliable_role.h
├── features/
│   ├── diagnostics/ (radio_diagnostics.cpp, radio_diagnostics.h)
│   ├── radio_link/ (radio_link.cpp, radio_link.h)
│   └── reliable_transfer/ (reliable_transport.h)
├── receiver/appcode/ (main.cpp, reliable.cpp)
└── sender/appcode/ (gateway/, main.cpp, reliable.cpp)
boot/
└── receiver_handoff.S, receiver_handoff_contract.c
```

The measured starting point is in [OWNERSHIP_BASELINE.md](OWNERSHIP_BASELINE.md).

This V2 report preserves its historical measurements. The current follow-up
verification, including 19 target sizes and final ARQ link-map evidence, is in
[ACK/NACK verification](../testing/LORA_ACK_NACK.md), with the present
[architecture map](../architecture/FINAL_ARCHITECTURE.md).

## B. Task

Assign startup and foreground transaction policy to their Sender or Receiver application sources. Keep common transport, packet read/decode, radio access, and diagnostic formatting reusable. Build the historical BOOT handoff independently and preserve the active Flash geometry, fuses, RF configuration, and wire contracts.

## C. Action

| Source | Starting owner and actual consumers | V2 owner and decision | Risk and verification |
| --- | --- | --- | --- |
| `app/arq/application.cpp`, `arq_application.h` | One application selected by the eight ARQ environments and host fixtures, with compile-time direction branches | Directional `appcode/arq/` units own command handling, session state, RX restart, TX completion, retries or response guard, and parking. The entry headers declare only that direction's lifecycle. | Maintain RX-before-retry order, guard time, diagnostics, and reverse direction. Checked with host fixtures, compiled objects, and ELF symbols. |
| `app/arq/radio.*` | Raw ARQ SPI and RadioLib setup used by both ARQ directions | Shared raw radio adapter. Pin mapping and the Tracker radio-only isolation safeguard still follow the physical target. | Preserve register access and startup order. Checked with host radio, fault, card-isolation, and directional tests. |
| `app/reliable_app.*`, `reliable_role.h` and role `reliable.cpp` files | Shared lifecycle with cross-TU hooks for the addressed reliable targets | Direct lifecycle and transport ownership in each role's existing `reliable.cpp`. The former hook interface is removed. Common formatting has no application control or transport state. | Preserve LED cadence and startup order, UART commands, and DATA acceptance and logging. Checked with role fixtures and log-backpressure tests. |
| `app/campaign_id.h` | Runtime seed and advancement used by Gateway and Sender reliable only | Sender-owned. Shared campaign arithmetic stays in SSOT. | Preserve the same seeding and progression. Checked with reliable tests and Gateway builds. |
| `features/radio_link/` | Addressed `LoRa` API used by Gateway, both reliable roles and host fixtures | Shared radio. Its API and implementation stay intact, including the SSOT header codec. | Checked with the HAL vectors, RF configuration tests and codec integration. |
| `features/reliable_transfer/` | One addressed transport template instantiated by Gateway and both reliable roles | Shared protocol. Its implementation already owns address checks, duplicate detection, retry and timeout behavior for its callers. | Checked with loss, duplicate, expiry, rollover and payload tests. |
| `features/diagnostics/` | Bounded transport event FIFO used by both reliable roles | Shared diagnostics. Common ARQ STATUS formatting and radio observations also live here. | Checked with buffer pressure and the directional STATUS fixtures. |
| `stable_lib/arq/` | Portable codecs, transaction algorithms, parser, diagnostic FIFO, generated board glue, plus their host consumers | Retained. PlatformIO may compile both portable transaction sources while building the archive. The final link retains only the selected algorithm and state. | Checked the dependency graph, compilation logs and linked symbols. |
| `stable_lib/mvp_app/`, `stable_lib/reverse_raw_app/` | Existing raw compatibility diagnostics selected by their four explicit targets | Retained as compatibility libraries. Their raw frame and command behavior are separate from the addressed and ARQ applications. Retired legacy selectors remain absent. | Checked existing host fixtures and all four images. |
| Top-level `boot/` | Historical offline fixture and reviewed package builder in `tools/receiver_boot.py` | Receiver Bootloader handoff. The assembler and C device-contract files moved byte-for-byte. Only the tool's source paths changed. | Compared Flash bytes, addresses, instructions, symbol names and traces. |

PlatformIO selects one physical entry and only the sources for the chosen mode. Gateway gets the addressed radio adapter, reliable gets that adapter and its event queue, and ARQ gets its directional transaction plus raw radio, ingress and bench observations. Both reverse ARQ diagnostics intentionally select the opposite **transaction** source while retaining the original board entry, pins and physical startup. Neither imports the opposite board's reliable or Gateway application. All APPCODE filters exclude the Receiver Bootloader.

The addressed adapter is still needed to manage the RadioLib IRQ and FIFO sequence and SSOT header packing. The raw ARQ adapter provides the existing board SPI readback and radio setup while leaving retry and session policy to the direction sources. The shared ARQ ingress reads a bounded FIFO packet and calls the existing decoder. It returns the disposition to the caller, which decides whether to restart RX or fail the transaction. It adds no codec or metadata policy. Common reliable log formatting stays in the active role translation unit because the UPDI byte queue is local to that translation unit. The separate lifecycles repeat some explicit setup and polling steps. The packet algorithms and formatters each retain one implementation.

Build filters are maintained in `platformio.ini`. The generated layout, board and RF profiles, code origin, upload settings and pinned RadioLib 7.1.2 were preserved. Gate 1 provenance now covers the directional ARQ translation units and extracted support. The quality gate follows the relocated startup and reduced STATUS complexity exceptions.

The isolation test in `tests/test_single_firmware_entry.py` failed on the old filters and passed after migration. Runtime behavior was characterized by the established host suite before source edits. Focused Sender and Receiver builds and host fixtures then exercised each active path, followed by the full offline matrix and the existing C++ quality gate.

## D. Result

- Firmware builds **19/19**, with **0 compiler warnings**. The existing host HAL characterization warning remains.
- Host suite **431 passed, 0 failed, 1 skipped**. The archived programming-package skip still reflects the historical versus active Receiver geometry.
- C++ quality gate **exit 0**. Its existing unsupported AVR LLVM, TimeUtils and Gateway cases are recorded in its output. Portable analysis and AVR-GCC builds ran.
- **Zero wrong-direction state symbols**, zero opposite board lifecycle objects, and zero BOOT source objects in the final APPCODE maps. Every linked image has one Arduino entry, matching ELF and Intel HEX coverage, and an exclusive end below `0x1FC00`. The disassembly audit found no `spm` instructions in these images.
- **Protocol compatibility PASS offline.** Existing fixtures compare addressed packet bytes and full ARQ DATA, ACK and NACK bytes in both directions. They exercise source and destination checks, campaign/session and sequence handling, malformed lengths, CRC rejection, duplicates, deadlines, and response loss. Raw compatibility vectors also passed.
- **BOOT fixture PASS offline.** The 48-byte binary, Intel HEX, normalized disassembly and all six traces match the baseline. The ELF embeds a different compiler-generated temporary object name. Its actual defined symbol addresses and executable bytes match. The fixture jumps to `0x5800` for reset bytes `52 C0 00 00`; blank Flash and all four one-bit byte mutations park.
- Source count including the two BOOT fixture sources rose from **28 to 34**. The active images compile **1–5 board/transaction objects** and **0–3 shared project objects**. Some source duplication follows from making both foreground loops explicit. The C++ gate's jscpd scope measured **0.83% → 7.29%** duplicated lines, including similar lifecycle, hardware sequencing, and test-mode branches.

Flash and static SRAM are bytes. Object counts come from project `src` entries in the linker map and exclude framework and library archives.

| Target | Flash before → after | SRAM before → after | Project objects before → after | Final role + shared |
| --- | ---: | ---: | ---: | ---: |
| `sender` | 38,792 → 38,794 | 7,079 → 7,079 | 9 → 6 | 5 + 1 |
| `sender_hello` | 36,832 → 36,760 | 4,009 → 4,009 | 5 → 4 | 2 + 2 |
| `receiver` | 35,868 → 35,788 | 3,849 → 3,849 | 5 → 4 | 2 + 2 |
| `sender_hello_spi` | 31,492 → 31,480 | 3,482 → 3,482 | 5 → 4 | 2 + 2 |
| `sender_hello_5dbm` | 36,832 → 36,762 | 4,009 → 4,009 | 5 → 4 | 2 + 2 |
| `receiver_5dbm` | 35,868 → 35,790 | 3,849 → 3,849 | 5 → 4 | 2 + 2 |
| `receiver_spi` | 31,548 → 31,528 | 3,478 → 3,478 | 5 → 4 | 2 + 2 |
| `sender_mvp` | 31,018 → 31,010 | 1,360 → 1,360 | 5 → 1 | 1 + 0 |
| `receiver_mvp` | 31,578 → 31,556 | 1,392 → 1,392 | 5 → 1 | 1 + 0 |
| `sender_arq` | 37,014 → 37,022 | 5,200 → 5,202 | 7 → 5 | 2 + 3 |
| `receiver_arq` | 35,804 → 35,774 | 5,044 → 5,046 | 7 → 5 | 2 + 3 |
| `sender_arq_test` | 37,014 → 37,022 | 5,200 → 5,202 | 7 → 5 | 2 + 3 |
| `receiver_arq_test` | 36,862 → 36,832 | 5,072 → 5,074 | 7 → 5 | 2 + 3 |
| `sender_arq_radio_only` | 37,048 → 37,068 | 5,212 → 5,214 | 7 → 5 | 2 + 3 |
| `receiver_arq_radio_only` | 37,252 → 37,214 | 5,116 → 5,118 | 7 → 5 | 2 + 3 |
| `sender_reverse_raw` | 31,850 → 31,838 | 4,646 → 4,646 | 5 → 1 | 1 + 0 |
| `sender_arq_radio_only_reverse` | 36,836 → 36,798 | 5,096 → 5,098 | 7 → 5 | 2 + 3 |
| `receiver_arq_radio_only_reverse` | 37,460 → 37,480 | 5,230 → 5,232 | 7 → 5 | 2 + 3 |
| `receiver_reverse_raw` | 30,946 → 30,952 | 4,443 → 4,443 | 5 → 1 | 1 + 0 |

Flash deltas range from **−80 to +20 bytes**. The instruction and section audits showed small code-layout changes in the relinked images. The ARQ receive counters now include the last observed IRQ flags in a single aggregate. The linked ARQ images use two more static SRAM bytes. Static SRAM excludes runtime stack use. Local evidence is under `/tmp/lora-ownership-v2/`, including `final-matrix.log`, `final-tests.log`, `final-quality.log`, `final-audit/`, `matrix-resources.json`, and `after-boot/`.

## E. Final directory tree

```text
src/
├── receiver/
│   ├── appcode/
│   │   ├── arq/
│   │   │   ├── application.h
│   │   │   └── receiver.cpp
│   │   ├── main.cpp
│   │   ├── reliable.cpp
│   │   └── reliable.h
│   └── bootloader/
│       └── handoff/
│           ├── receiver_handoff.S
│           └── receiver_handoff_contract.c
├── sender/
│   └── appcode/
│       ├── arq/
│       │   ├── application.h
│       │   └── sender.cpp
│       ├── campaign_id.h
│       ├── gateway/
│       │   ├── espcomm.cpp
│       │   ├── espcomm.h
│       │   ├── gateway_app.cpp
│       │   ├── gateway_app.h
│       │   ├── gateway_radio.cpp
│       │   ├── io.cpp
│       │   ├── io.h
│       │   ├── lora_config.h
│       │   └── lora_rx.h
│       ├── main.cpp
│       ├── reliable.cpp
│       └── reliable.h
└── shared/
    ├── diagnostics/
    │   ├── arq_bench.cpp
    │   ├── arq_bench.h
    │   ├── radio_diagnostics.cpp
    │   ├── radio_diagnostics.h
    │   └── reliable_log.h
    ├── protocol/
    │   ├── arq_ingress.cpp
    │   ├── arq_ingress.h
    │   └── reliable_transport.h
    └── radio/
        ├── arq_radio.cpp
        ├── arq_radio.h
        ├── radio_link.cpp
        └── radio_link.h
```

## F. Migration table

| Old path | New path | Reason | Verified |
| --- | --- | --- | --- |
| `src/app/arq/application.cpp` | `src/{sender,receiver}/appcode/arq/{sender,receiver}.cpp`, `src/shared/{diagnostics/arq_bench,protocol/arq_ingress}.cpp` | Explicit direction ownership with one formatter and packet ingress implementation | Directional tests and all ARQ ELFs |
| `src/app/arq/arq_application.h` | `src/{sender,receiver}/appcode/arq/application.h` | Local entry API | Build filters and maps |
| `src/app/arq/radio.{cpp,h}` | `src/shared/radio/arq_radio.{cpp,h}` | Common raw RadioLib and SPI access | Radio-only tests and all ARQ builds |
| `src/app/reliable_app.{cpp,h}`, `src/app/reliable_role.h` | `src/{sender,receiver}/appcode/reliable.{cpp,h}`, `src/shared/diagnostics/reliable_log.h` | Own lifecycle directly and remove the role-hook interface | Sender, Tracker, logging and addressed builds |
| `src/app/campaign_id.h` | `src/sender/appcode/campaign_id.h` | Sender seeds campaigns | Reliable and Gateway |
| `src/features/radio_link/` | `src/shared/radio/radio_link.{cpp,h}` | Shared addressed adapter | HAL and wire tests |
| `src/features/reliable_transfer/` | `src/shared/protocol/reliable_transport.h` | Shared transaction engine | Transport loss and protocol tests |
| `src/features/diagnostics/` | `src/shared/diagnostics/radio_diagnostics.{cpp,h}` | Shared bounded FIFO | Diagnostics tests |
| `boot/receiver_handoff.S`, `boot/receiver_handoff_contract.c` | `src/receiver/bootloader/handoff/` | Receiver-owned freestanding BOOT fixture | Byte comparison and all six traces |

## G. Remaining risks

Both active images still link at `0x0000`. The configured Receiver has `BOOTSIZE=0`, which assigns Flash to BOOT without a separate APPCODE region. The archived fixture also starts at `0x0000` and expects a different origin and reset vector for the application. A real pairing requires an approved memory split, compatible link addresses and vector contract, and verified fuse readback. [Microchip AN3341 Flash sections](https://onlinedocs.microchip.com/oxy/GUID-CBA6F7C8-69DB-44BF-ACE3-6949CC30E98A-en-US-5/GUID-1FBA83BB-35A7-4B9D-A92E-8A9C7CB8DED6.html)

Installation requires separate scope for staging, authentication, Flash commit and recovery. The installer review must use the actual silicon revision. Microchip documents affected AVR128DA revisions on which a multi-page erase can cross into write-protected application data. [Microchip AVR128DA errata, section 2.7.2](https://ww1.microchip.com/downloads/en/DeviceDoc/AVR128DA-28-32-48-64-SilConErrataClarif-DS80000882C.pdf)

Physical RF, RF timing, device fuse readback, and power-failure recovery were **NOT TESTED**. There were no device connections, programming operations, or RF transmissions during verification.

## H. Final status

| Boundary | Status |
| --- | --- |
| Source ownership | PASS |
| Build isolation | PASS |
| Protocol compatibility | PASS offline |
| BOOT fixture | PASS offline |
| Active BOOT/APPCODE | BLOCKED |
| FOTA installation | BLOCKED |
| Physical hardware | NOT TESTED |
