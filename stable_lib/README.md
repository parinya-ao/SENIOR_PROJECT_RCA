# `stable_lib`

`platformio.ini` sets `lib_dir = stable_lib`. Each library keeps its manifest,
public headers, and implementation files directly in its own directory. The
`library.json` manifests use `srcDir = "."` and `includeDir = "."`; keep C++
namespaces in code, not in additional filesystem levels. The only nested files
are the vendored protothread headers under `task/pt/`.

| Library | Responsibility | Notes |
|---|---|---|
| `arq` | ARQ codec, sender/receiver state machines, diagnostics | `arq.h` is the umbrella API; generated `board_ssot.c` is written here. |
| `debug` | Firmware debug logging and assertions | Keeps the existing `Debug.h` compatibility header. |
| `firmware_app` | Compile-time selected application lifecycle | Called by the Arduino entry points. |
| `gateway_app` | Gateway GPIO, I2C mailbox, radio task, and application wiring | Uses shared settings, task scheduling, and AVR helpers. |
| `gnss` | GNSS receiver data handling | Uses serial facilities supplied by the firmware target. |
| `iw_avr128da28` | AVR128DA28 ADC, routing, RTC, and provisioning operations | Public headers use the `avr128da28_` prefix to avoid collisions. |
| `iw_core` | Little-endian codecs, checked ranges, and fixed-capacity buffers | Platform-independent; no registry dependency. |
| `iw_tracker_radio_protocol` | Legacy Tracker packet layouts and codec | Kept separate from SSOT; uses `iw_core`. |
| `legacy_receiver` | Historical receiver application | Retained for its separate build environment. |
| `legacy_sender` | Historical sender application | Retained for its separate build environment. |
| `logger` | Compact firmware logging helpers | Writes through the selected platform serial output. |
| `lora` | RadioLib-backed LoRa interface | Declares `jgromes/RadioLib` 7.1.2. |
| `mcurses` | Bundled embedded terminal UI | Existing bundled source and API are retained. |
| `mvp_app` | Minimal DATA/ACK application path | Used by its dedicated firmware profile. |
| `printf` | Reduced-footprint formatted output | Existing bundled implementation is retained. |
| `raw-storage` | Raw byte storage access | Storage driver is supplied by the selected target. |
| `reliable_app` | Gateway/Tracker reliable DATA/ACK lifecycle | Runs the SSOT transport over the radio adapter. |
| `reverse_raw_app` | Reverse-direction raw radio diagnostics | Kept as a separate diagnostic profile. |
| `sd-storage` | SD-card storage interface | Used only by profiles that enable removable storage. |
| `sd-utils` | SD-card path and file helpers | Uses the storage interface selected by the profile. |
| `shared` | Application settings and nonblocking status LEDs | Consumes generated profile settings. |
| `sleep` | Bounded low-power sleep and wakeup policy | Uses the AVR RTC primitives. |
| `ssot` | DATA/ACK/NACK codec and campaign/session rules | Owns protocol state; does not own radio hardware. |
| `task` | Cooperative scheduler and project protothread wrappers | `pt/` contains the sole vendored nesting exception. |
| `time-utils` | Tracker wall-clock conversion and formatting | Declares `paulstoffregen/Time` 1.6.1. |
| `updi_uart` | C UPDI UART transport and role identity logging | Wraps the existing `third_party/upditerm` implementation. |

## Adding and checking libraries

Use a lowercase `snake_case` directory for a new library. Put its `.h`, `.c`,
and `.cpp` files beside `library.json`; give public headers distinct,
responsibility-based names when libraries would otherwise export the same
include name. Keep real dependencies in the manifest and avoid compatibility
wrappers for paths used only inside this repository.

Build the exercised firmware profiles with `pio run -e sender_hello`,
`pio run -e receiver`, `pio run -e sender`, `pio run -e sender_arq_test`, or
`pio run -e receiver_arq_test`. Run the local tests with
`rtk python3 -m unittest discover -s tests`. The combined formatter, static
analysis, documentation, host-test, and firmware-build gate is
`rtk bash scripts/quality/check_cpp.sh`.
