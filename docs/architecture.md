# Firmware architecture and readability refactor

The AVR128DA28 firmware has independent PlatformIO applications. C++17 is
supported, but the AVR toolchain does not ship the C++ standard-library headers;
portable code uses `<stdint.h>` and `<stddef.h>`. No new runtime is needed.

## Audit and execution flow

| Entry point | Environments | Responsibility and dependencies |
|---|---|---|
| `src/sender/lib/main.cpp` | `sender` | GPIO, ADC, Wire callbacks and cooperative tasks; stable LoRa transport |
| `src/reliable/main.cpp` | `receiver`, `sender_hello` and their SPI/power variants | Bounded DATA/ACK test; stable LoRa and SSOT transport |
| `src/arq/main.cpp` → `application.cpp` | Eight `*_arq*` variants | Explicit Arduino lifecycle and radio orchestration |
| `src/mvp/main.cpp` | `sender_mvp`, `receiver_mvp` | Register-oriented radio bring-up |
| `src/reverse_raw/main.cpp` | `*_reverse_raw` | Independent reverse-direction raw radio diagnostic |
| `src/sender/main.cpp`, `src/receiver/main.cpp` | Excluded by current filters | Retained alternative applications; no duplicate active entry points |

`debug` and `release` are roleless configuration bases, not working applications.
The pre-build script rejects using either without a role. All 19 role targets
built during the preceding migration; this refactor starts with those artifacts
and a fresh host baseline: 402 tests, two failures, seven errors and one skip.

Arduino initializes the platform before `setup()`. Required `onPreMain()` hooks
retain vector routing. Setup initializes board power/GPIO, SPI and the radio.
The foreground loop collects commands, inspects IRQ flags, processes receive
bytes, handles TX completion, restores RX and advances protocol deadlines.
Commands and diagnostics must not block radio progress.

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

The radio adapter owns hardware and TX/RX turnaround. Its logs are evidence,
not protocol state. Wire callbacks and cooperative task continuation state in
the sender are separate ownership boundaries; volatile byte mailboxes do not
imply that multi-byte data is atomic.

## Implementation sequence and contracts

1. Add validated application policy configuration without changing the protected
   board/radio SSOT. Test bounds, unknown keys and deterministic generation.
   Preserve existing values. Protocol widths/register addresses remain constants.
2. Give ARQ codec, sender and receiver self-contained interfaces, Google names
   and a small namespace. Preserve caller-owned aggregates and byte fixtures.
3. Give diagnostics one queue owner; separate bounded command parsing from
   hardware effects. Test queue saturation/backpressure and command overflow.
4. Separate SSOT wire encoding from campaign/duplicate/command state. Preserve
   the existing template transport, which adapts real and host radios statically.
5. Improve names, comments and formatting in all application variants and sender
   integration; retain callback signatures, task scheduling and hardware order.
6. Run affected tests after each boundary, then all role builds, full host suite,
   static analysis, formatting, resource comparison and independent review.

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

No flashing or physical RF test is authorized by this refactor. Host simulations
establish byte/state behavior only; interrupt latency, RF turnaround and runtime
stack/heap measurements require later physical validation.

## Resulting module map

| Module | Responsibility | Dependencies / ownership |
|---|---|---|
| `arq/frame.h`, `codec.h/.cpp` | Logical fields and byte-exact encoding | Fixed wire limits; no Arduino |
| `arq/sender.h/.cpp` | Requests, retry spacing, deadlines and ACK acceptance | Caller-owned `arq::Sender`; generated ARQ policy |
| `arq/receiver.h/.cpp` | Session/payload validation and duplicate ACK replay | Caller-owned `arq::Receiver`; no radio I/O |
| `arq/commands.h/.cpp` | Role-specific command grammar and bounded line input | `CommandInput` owns its buffer; parsed payload copied |
| `arq/diagnostics.h/.cpp` | Event formatting and one bounded output queue | Foreground-only UPDI mailbox; no reader wait |
| `arq/application.h/.cpp` | Radio initialization, command effects, IRQ/deadline ordering | Owns static radio/state; failures park or disable progress |
| `ssot/codec.h`, `ssot.cpp` | Existing SSOT field encoding and frame validation | Generated wire constants; caller buffers |
| `ssot/session.h/.cpp` | Campaign progress, build marker, duty interval and duplicates | Caller-owned state; fixed bitmap |
| `ssot/control_input.h/.cpp` | Legacy session command accumulation | Configured inter-byte timeout; no hardware |
| `shared/reliable_transport.h` | Statically adapts stable radio and native fault injection | `reliable::Transport<Radio>` borrows radio/callbacks |
| `sender/lib/espcomm.cpp` | Wire callbacks and deferred host commands | Private byte mailboxes; existing cooperative scheduler |
| `sender/lib/lora_rx.cpp` | One scheduled reliable transaction | Existing transport and static LoRa object |
| `config/application.toml` → `include/application_config.h` | Validated application-only policy | Separate renderer; no protected output writes |

`arq.h` and `ssot.h` are include-only entry headers for callers using multiple
portable responsibilities. New single-responsibility code can include its direct
header. There are no forwarding API implementations or new radio interfaces.

An ARQ line flows from `CommandInput::Feed()` to `ParseCommand()`, then application
state effects. Sender requests hand an immutable frame to the radio coordinator.
TX completion is followed by checked RX restoration before ACK timing starts.
Received bytes pass CRC, codec and peer/session/sequence checks before acceptance.
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
