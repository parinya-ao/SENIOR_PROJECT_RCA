# Firmware source map

PlatformIO selects a role-specific entry point from platformio.ini. Both entry
points delegate setup and loop to one selected application module. Shared files
contain transport plumbing and diagnostics, while stable_lib owns the generated
SSOT codec and portable ARQ algorithms.

| Path | Responsibility |
|---|---|
| sender/appcode/main.cpp | Gateway entry point and application selection |
| sender/appcode/gateway | Gateway I2C, host interface, scheduler, and radio transaction |
| sender/appcode/reliable.cpp | Sender half of the SSOT reliable test application |
| sender/appcode/arq | Sender-specific ARQ radio and session orchestration |
| receiver/appcode/main.cpp | Tracker entry point and application selection |
| receiver/appcode/reliable.cpp | Receiver payload acceptance and SSOT ACK/NACK response |
| receiver/appcode/arq | Receiver-specific ARQ radio and response orchestration |
| receiver/bootloader/handoff | Standalone offline reset-vector handoff fixture |
| shared/radio | RadioLib adapter and raw ARQ radio setup |
| shared/protocol | SSOT reliable transport and ARQ frame ingress |
| shared/diagnostics | Bounded event and status records |

The role entry points can select Gateway, reliable, ARQ, MVP, or reverse-raw
application code through their existing build flags. The reverse diagnostics
intentionally keep the physical board role while selecting the opposite ARQ
transaction source. Their source filters remain explicit in platformio.ini.

## Data and protocol boundaries

The default sender target builds the Gateway application. The sender_hello and
receiver targets build the addressed SSOT DATA/ACK/NACK transaction. The ARQ
targets use a distinct versioned 12-byte frame and the portable state machine in
stable_lib/arq. The MVP and reverse-raw targets preserve separate legacy test
formats. These formats share the radio adapter and hardware, not wire encoding.

See [Sender](sender/README.md), [Receiver](receiver/README.md),
[shared modules](shared/README.md), and the
[Receiver BOOT fixture](receiver/bootloader/README.md).
The detailed [ACK/NACK analysis](../docs/testing/LORA_ACK_NACK.md) records call
paths, frame layouts, state transitions, test evidence, and hardware status.
