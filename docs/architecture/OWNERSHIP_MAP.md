# Ownership Map

Snapshot: `f0ca01554c156b2034ac29c304571ec7dcb02acb`, before the first `src/features` migration.

| Module | Current owner and responsibility | Active consumers / evidence |
|---|---|---|
| `src/main.cpp` | Arduino `setup`, `loop`, and early hook; calls the firmware dispatcher | All role environments; only production source currently selected from `src/` |
| `stable_lib/firmware_app/` | Compile-time selection and lifecycle dispatch | `gateway_app`, `reliable_app`, ARQ, MVP, reverse-raw, and legacy app families |
| `stable_lib/gateway_app/lora_rx.cpp` | Gateway LoRa task and transaction startup | Default `sender`; instantiates `reliable::Transport<LoRa>` |
| `stable_lib/reliable_app/reliable_app.cpp` | Host commands, receiver/sender role setup, callbacks and event reporting | `receiver` and reliable sender variants; instantiates the same transport |
| `stable_lib/shared/reliable_transport.h` | Header-only reliable transaction state machine: bounded attempts/deadlines, exact peer/local filtering, ACK/NACK acceptance, duplicate replay, and response TX | Gateway and reliable app; host transport tests |
| `stable_lib/lora/lora.h/.cpp` | `LoRa` public API and RadioLib lifecycle, 4-byte address header, IRQ callbacks, TX completion, RX re-arm, and driver error propagation | Reliable/gateway and legacy applications; wrapper and safety tests |
| `stable_lib/ssot/src/ssot/codec.*`, `session.*` | SSOT byte codec and campaign/session helpers | SSOT-specific callers/tests. The active `reliable::Transport` uses SSOT type/timeout constants but builds its two-byte payload directly; it does not call `EncodeDataFrame`, `DecodeFrame`, or `AckMatches` |
| `stable_lib/arq/src/arq/` | Separate 12-byte ARQ codec, sender/receiver state, command parser, and direct RadioLib adapter | Eight ARQ environments and ARQ host tests; do not merge with SSOT |
| `include/generated/`, `config/`, `generated/` | Hardware, role, PHY, target-layout and protocol source/generated values | Protected SSOT; do not edit/regenerate during ordinary migration |
| `boot/` and protected Flash region | Handoff contract and boot boundary | Outside this LoRa application migration |

## Address and radio API call sites

- `LoRa::init`, `send`, and `recv` are implemented only in `stable_lib/lora/lora.cpp`; active reliable/gateway callers reach them through `stable_lib/shared/reliable_transport.h`. Legacy applications also call the same API.
- `_module.begin(...)` is called by `LoRa::init` only. `LoRa::set_my_address()` has no production caller in the current source; it appears in host wrapper tests.
- The current application does not call `SX127x::setNodeAddress()`. The exact pinned local RadioLib 7.1.2 implementation rejects that API unless the active modem is FSK/OOK.
- ARQ has its own `Module` and `SX1276` object in `stable_lib/arq/src/arq/application.cpp`; it does not use the `LoRa` wrapper or reliable transport.

The receive driver extracts source and destination and returns them to the caller. `reliable::Transport::HandleReceive()` applies software source/destination filtering before invoking the application callback or generating ACK/NACK. Broadcast address `255` is rejected during transport arming.
