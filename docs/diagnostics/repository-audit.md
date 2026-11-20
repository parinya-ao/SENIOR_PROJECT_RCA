# LoRa Recovery Repository Audit

## Scope and current state

The repository contains two active AVR128DA28 applications, a shared reliable
transport, UPDI-based host control, and several separate test/proof tools. The
production pair is PlatformIO `sender` + `receiver`; `sender_hello` remains a
legacy fixed-payload regression image. The interactive console uses the
production pair and does not flash on startup.

The current hardware run is
`artifacts/lora-chat/20261120T035313.464528Z/`. Device identity and fuse reads
passed. Both byte-for-byte image comparisons failed, so the console stopped at
`APPLICATION_WRITE_PREFLIGHT` before acquiring runtime monitors. BOOTSIZE=0
assigns all Flash to BOOT and leaves FOTA not ready. No Flash, fuse, EEPROM, SD,
or RF write/transmission occurred.

## Repository map

| Area | Responsibility |
|---|---|
| `src/sender/appcode/gateway/` | Production Gateway radio scheduler and UPDI/I2C commands |
| `src/receiver/appcode/reliable.cpp` | Tracker initialization, validation, ACK, and interactive Echo |
| `src/shared/protocol/reliable_transport.h` | Single stop-and-wait wire transport shared by Gateway and Tracker |
| `src/shared/protocol/interactive_command.h` | Bounded `X<length><hex>` host fragment decoder |
| `stable_lib/arq/` | Separate legacy ARQ library and compatibility tests |
| `tools/device_detection/` | Device roles, enrolled hardware registry, UPDI identity, Flash layout, and firmware event lines |
| `tools/lora_chat/` | Typer entry point, prompt-safe Rich UI, queue/session state, and capability-gated transport |
| `tools/debug_protocol_ack_nack.py` | Existing UPDI monitor owner and physical DATA/ACK/NACK exchange adapter |
| `tools/rf_proof.py` | Build/image bounds, target identity, readback comparison, upload gates, and RF evidence checks |
| `tools/production_bench.py` | Builds and verifies the production `sender`/`receiver` pair, and gates application writes |
| `tools/rf_stress/` | Test case generation, event assessment, and metrics |
| `tools/installed_rf.py` | Installed-image RF verification using the existing proof and capture adapters |

## Configuration and build

- `config/lora_system.json` is the protocol, board, and target-layout SSOT.
- `config/radio_915.toml` owns the validated radio profile.
- `config/current_hardware.json` is the enrolled identity/locator registry;
  `tools/device_detection/hardware_registry.py` validates it and supplies
  current stable by-path locators. The locator is a hint; serial and signature
  readback decide the device role.
- `tools/config/generate_lora_config.py --prepare-build` validates generated
  headers/INI and refreshes derived manifests.
- Production build environments are `sender` and `receiver`. The regression
  build `sender_hello` retains its fixed `hello world` payload.

Read-only verification compares the exact HEX-derived Flash byte range against
fresh physical readback. The report keeps byte match, fuse-layout validity,
runtime identity, and FOTA readiness as separate fields. A valid BOOT-resident
image is not called APPCODE or FOTA-ready.

## Host commands and port ownership

- `mise run lora_chat` runs `uv run --no-sync python -m tools.lora_chat`.
- `uv run --no-sync python -m tools.lora_chat --help` exposes Typer options.
- `uv run --locked python -m tools.debug_protocol_ack_nack` runs the existing
  physical monitor/ACK-NACK bench.
- `uv run --locked python -m tools.rf_stress` defaults to a non-transmitting
  plan.
- The UPDI programmer is invoked through the existing monitor/proof adapters.
  Chat bytes go through the verified monitor's supported firmware command
  channel; no code assumes `serial.write()` to a SerialUPDI programmer is an
  application UART.
- `Hardware.close()` owns monitor cleanup. The live startup run failed before
  runtime monitors were acquired; the programmer commands completed and their
  subprocesses released their ports.

## RF and protocol evidence

Gateway and Tracker use `reliable::Transport`; the host does not implement a
second ARQ. `tools/device_detection/firmware_events.py` is the canonical event
line parser. Chat and RF stress adapt its parsed result to their own typed
assessment models. The current interactive path requires Gateway and Tracker
capability records, transmits one fragment at a time, correlates campaign and
sequence, and verifies a Tracker-originated DATA Echo before success.

The prior physical artifact
`artifacts/rf-debug/sram-rf-20261119T141435.030695Z/summary.json` records 10 ACK
and 10 NACK trials for `hello world`, sequence 1, across 20 campaigns. It reports
34 total attempts, 14 retries, both radios parked, no port owners, and no run
error. This is historical one-way DATA/ACK/NACK evidence; it does not prove the
new interactive Echo path.

## Existing safety invariants

- No automatic firmware writes; exact image, identity, target, authorization,
  and page-range checks remain required.
- No BOOT/fuse/EEPROM/USERROW/SD writes as part of chat startup or this audit.
- RF stays behind the explicit authorization flag and resolved radio/antenna
  inventory.
- `BOOTSIZE=0x00` is interpreted as whole Flash BOOT. Application-only writes
  are rejected unless the live fuses and the image's APPCODE span both match.
- Host logs are under `artifacts/lora-chat/<run-id>/`; no MCU storage is used.

## Checks run for this audit

The active test suite is scoped to `tests/`, so archived tests beneath
`artifacts/` are preserved as evidence rather than collected as live tests. The
final run result is recorded in
[`final-recovery-report.md`](final-recovery-report.md). The current physical
blocker and first failing transaction boundary are recorded in
[`root-cause-analysis.md`](root-cause-analysis.md).
