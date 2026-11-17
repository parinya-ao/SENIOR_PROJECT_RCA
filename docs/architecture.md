# Firmware architecture

The AVR128DA28 targets use C++17 and the existing Arduino/DxCore runtime. The
firmware has one entry source, `src/main.cpp`. Role dispatch and the active
Gateway/Receiver application coordinators live under `src/app/`; shared
reliable-transfer, diagnostics and radio-link implementations live under
`src/features/`.
Gateway I2C support and independent protocols remain under `stable_lib/`.

## Build and application selection

`platformio.ini` sets `lib_dir = stable_lib` and selects `src/main.cpp`, the
`src/app` lifecycle/radio coordinators, and the radio-link/diagnostics feature
sources. Each environment selects one application at compile time.
`firmware_app` dispatches initialization, polling, and the required early
interrupt hook to that application.

| Application | Environments | Implementation |
|---|---|---|
| Gateway | `sender` | `src/app/application.cpp`, `src/app/gateway_radio.cpp`, and `stable_lib/gateway_app/` I2C support |
| Reliable DATA/ACK | `receiver`, `sender_hello`, SPI and power variants | `src/app/application.cpp` and `src/app/reliable_app.cpp` |
| MVP radio bring-up | `sender_mvp`, `receiver_mvp` | `stable_lib/mvp_app/` |
| ARQ | Eight `*_arq*` variants | `stable_lib/arq/src/arq/` |
| Reverse raw radio diagnostic | `sender_reverse_raw`, `receiver_reverse_raw` | `stable_lib/reverse_raw_app/` |

The roleless `debug` and `release` sections are configuration bases; the
pre-build script rejects building them without a role. Legacy sender and
receiver experiments remain isolated under `stable_lib/legacy_*` and are not
selected by a supported target. PlatformIO ignores non-selected application
libraries for each role.

The common entry calls `firmware_app::Initialize()` and `firmware_app::Poll()`.
For applications that historically routed interrupts before Arduino startup,
`onPreMain()` calls the same dispatcher at the original early startup point.
Board power sequencing and radio setup remain in the owning application.

## Protocol and ownership

ARQ and SSOT are distinct protocols; their encoders must stay separate. ARQ owns
an explicit 12-byte header and up to 32 payload bytes. SSOT uses the existing
four-byte RadioHead-compatible address/campaign header and its own type codes.
Neither protocol serializes native C++ object memory.

ARQ sender/receiver state is caller-owned, foreground-only and fixed-capacity.
Sender transitions are idle → transmitting → waiting for ACK → delivered, or
backoff → transmitting, with terminal failure on exhausted time/radio errors.
Matching controls are processed before retry evaluation. Only a matching ACK
advances sequence; failed or wrapped sessions cannot reuse sequence/payload
pairs. Receiver validates payload before duplicate ACK replay, delivers once,
and retains duplicate history even when ACK transmission fails.

`src/features/radio_link/` owns the LoRa hardware wrapper and TX/RX turnaround;
`src/features/reliable_transfer/` owns the shared bounded DATA/ACK state machine.
Logs are evidence, not protocol state. Wire callbacks and cooperative task
continuation state in the sender are separate ownership boundaries; volatile
byte mailboxes do not imply that multi-byte data is atomic.

## Implementation contracts

ARQ codec, sender and receiver interfaces stay portable, caller-owned, and
fixed-capacity. Diagnostics have one bounded queue owner; command parsing stays
separate from radio effects. SSOT wire encoding remains separate from campaign,
duplicate, and command state. The template transport adapts real and host radios
without runtime allocation and remains header-only in its feature owner.

No class is needed around a stateless codec. State aggregates remain explicit
rather than gaining forwarding methods. A command accumulator owns a real
buffer lifecycle. Template transport stays in its header because callers
instantiate it with different radio types.

## Configuration and maintenance

Pins, image bounds, PHY and existing protocol defaults belong to the protected
`config/lora_system.json`, `config/radio_915.toml`, `config/arq_test.toml` and
their existing generated outputs. Application-only policy belongs in
`config/application.toml`; its generated header is separately validated.
Builds must reject stale configuration, never silently override it.

Change encoding in the codec, retry decisions in the sender, delivery/duplicate
rules in the receiver, command syntax in the command parser, and radio startup
in the selected application's hardware coordinator. Generated board code,
vendor libraries, boot code and inactive target entry points remain distinct.

No firmware was flashed and no physical RF test ran during this migration pass.
Host simulations establish byte/state behavior only; interrupt latency, RF
turnaround and runtime stack/heap measurements still require physical validation.

## Resulting module map

| Module | Responsibility | Dependencies / ownership |
|---|---|---|
| `stable_lib/arq/src/arq/frame.h`, `codec.*` | Logical ARQ fields and byte-exact encoding | Fixed wire limits; no Arduino |
| `stable_lib/arq/src/arq/sender.*` | Retry spacing, deadlines and ACK acceptance | Caller-owned `arq::Sender`; generated ARQ policy |
| `stable_lib/arq/src/arq/receiver.*` | Session/payload validation and duplicate ACK replay | Caller-owned `arq::Receiver`; no radio I/O |
| `stable_lib/arq/src/arq/commands.*` | Role-specific grammar and bounded line input | `CommandInput` owns its buffer; parsed payload copied |
| `stable_lib/arq/src/arq/diagnostics.*` | Event formatting and one bounded output queue | Foreground-only UPDI mailbox; no reader wait |
| `stable_lib/arq/src/arq/application.*` | Radio initialization, command effects, IRQ/deadline ordering | Owns static radio/state; failures park or disable progress |
| `stable_lib/ssot/src/ssot/codec.*` | SSOT field encoding and frame validation | Generated wire constants; caller buffers |
| `stable_lib/ssot/src/ssot/session.*` | Campaign progress, build marker, duty interval and duplicates | Caller-owned state; fixed bitmap |
| `stable_lib/ssot/src/ssot/control_input.*` | Legacy session command accumulation | Configured inter-byte timeout; no hardware |
| `src/app/application.cpp/.h` | Compile-time role dispatch and lifecycle | Calls one selected role; no packet parsing |
| `src/app/gateway_radio.cpp` | One scheduled Gateway DATA/ACK transaction | `reliable::Transport<LoRa>` and static radio |
| `src/app/reliable_app.cpp` | Reliable sender/receiver startup, host commands, callbacks and events | Borrows `LoRa` through the shared transport |
| `src/features/reliable_transfer/reliable_transport.h` | Bounded DATA/ACK transactions, address filtering and duplicate handling | `reliable::Transport<Radio>` borrows radio/callbacks |
| `src/features/diagnostics/radio_diagnostics.*` | Fixed-capacity event FIFO and saturating overflow counter | Foreground-only; event names must outlive queued entries; no allocation |
| `src/features/radio_link/radio_link.h/.cpp` | SX127x LoRa lifecycle, RadioHead-compatible header and checked TX/RX re-arm | One RadioLib module per MCU; old include path retained |
| `stable_lib/gateway_app/espcomm.cpp` | Wire callbacks and deferred host commands | Private byte mailboxes; cooperative scheduler |
| `stable_lib/iw_tracker_radio_protocol/` | Legacy Tracker packet layout and byte codec | Separate legacy wire contract; fixed-size buffers |
| `config/application.toml` → `include/application_config.h` | Validated application-only policy | Separate renderer; no protected output writes |

`arq/arq.h` and `ssot/ssot.h` are include-only entry headers for callers using
multiple portable responsibilities. New single-responsibility code can include
its direct header. `stable_lib/lora/lora.h` is a compatibility include only; the
`LoRa` class and implementation have one owner in `src/features/radio_link/`.

An ARQ line flows from `CommandInput::Feed()` to `ParseCommand()`, then application
state effects. Sender requests hand an immutable frame to the radio coordinator.
TX completion is followed by checked RX restoration before ACK timing starts.
ARQ bytes pass CRC, codec and peer/session/sequence checks before acceptance.
The reliable transport checks peer, destination, campaign, type, sequence,
transaction state and deadline. It carries a nonzero sender campaign ID in the
existing RadioHead ID/flags bytes; an unbound receiver adopts the first DATA
campaign and drops other campaigns without responding. Re-arming the same
receiver object preserves duplicate history for that campaign and replays its
ACK without redelivery. A receiver power reset still loses RAM history. The
16-bit ID is mixed from the build marker and MCU timer, so collisions across
resets remain possible; it is correlation data, not authentication. The legacy
LoRa overloads still emit zero, but a reliable sender using a campaign ID needs
the updated receiver to echo it in ACK/NACK frames.
Receiver decisions precede the response guard; failed ACK transmission never
undoes delivery history. Diagnostics borrow live scalar context fields and never mutate protocol state.
The referenced state has application lifetime; no duplicate state is synchronized. STATUS remains incremental to avoid overflowing bounded buffers.

The I2C task snapshots command length before clearing its receive mailbox. This
fixes valid configuration being rejected as zero-length. The host must still
respect readiness before sending another work command; no broader synchronization
redesign was performed. The disabled legacy I2C recovery task remains disabled.

Protocol byte widths and MCU register addresses are constants, not tunable policy.
Known board pins use generated mappings; GNSS UART/TIMEPULSE isolation retains its
existing direct register/pin sequence. The excluded SX1262 experiment is documented
and formatted, but has no configured build target and remains unverified.

PlatformIO library storage and source filtering follow the documented
[`lib_dir`](https://docs.platformio.org/en/stable/projectconf/sections/platformio/options/directory/lib_dir.html),
[`build_src_filter`](https://docs.platformio.org/en/stable/projectconf/sections/env/options/build/build_src_filter.html),
and [Library Dependency Finder](https://docs.platformio.org/en/latest/librarymanager/ldf.html)
behavior. `.clang-format` uses Google's C++ base style as described by the
[Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html).
