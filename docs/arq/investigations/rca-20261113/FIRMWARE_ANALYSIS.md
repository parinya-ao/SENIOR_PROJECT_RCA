# Firmware SEND audit

Implementation of record: archived Incident B
[source](../../../../artifacts/arq/20261113T123620Z-reverse-raw/source/src/reverse_raw/main.cpp).
Current equivalent line references follow; its hash is recorded in that bundle.
Active ARQ is separately `src/arq/main.cpp`, `sender.c`, `receiver.c`, `codec.c`.
Original raw MVP is `src/mvp/main.cpp`. No protocol code was changed here.

| Transition | Source/function | Preconditions / mutation / observable failure |
| --- | --- | --- |
| Host SEND | tools/arq_trial.py Capture.command:178 | Live process, complete pipe write/flush; records host timestamp; does not confirm MCU delivery |
| Host byte to mailbox | third_party/upditerm/upditerm.py SerialUPDI.send1:243 | Read GPIOR2; wait FLAG_RX clear; write GPIOR3 then set FLAG_RX; strict ACKs |
| Mailbox consumption | third_party/upditerm/updi_uart.c updi_uart_rx:60 | Poll FLAG_RX; read byte then clear flag; loop checks poll before blocking accessor |
| Byte parser | src/reverse_raw/main.cpp command_byte:73 | Ignore CR; collect at most47 bytes; newline invokes command; overflow rejects whole line then resets parser |
| Gate/payload | command:54 | STATUS/X special; ready, not active, not used; exact ASCII command with22 hex digits required |
| Pre-TX snapshot | configuration:19, command:60 | Reserve logger slot, read23 SPI registers, enqueue; no connected reader wait |
| Start radio | command:61 → SX127x::startTransmit:571 | used=true; exact static11 bytes; rc sets active; started set on return |
| Start log | command:62–64 | RAW_TX after driver return, then RAW_TX_STATE; rc error cleans up; absence does not locate execution inside preceding call |
| Completion | loop:102–106 | Poll IRQ; TxDone or3000ms bound → finishTransmit → event → standby |

No RAW_TX_PRE in B means its pre-snapshot was not delivered to the host. It
does not prove command parsing never began: enqueue is not delivery. No RAW_TX
also does not prove startTransmit was never called; logging follows its return.

Logging uses16 slots of192 bytes and emits at most one mailbox character per
loop when the reader is ready (`src/arq/diagnostics.h`). Full logger increments
overflow and returns immediately. Buffer backpressure cannot block the loop by
design; SPI/RadioLib calls still take bounded execution time and must not be
confused with waiting for host logging. No command-state ISR appears in this
path. The host reader/writer serial lock prevents concurrent UPDI transactions;
no reproducible logging/parser collision has been demonstrated.

Host-only `tests/rca_send_test.cpp` exercises actual parser/loop with existing
fake radio: partial command does not transmit; CR/LF completes exact11 bytes;
wrong length and overfull input reject; repeated command starts only once;
disconnected/full logger does not prevent TX timeout cleanup. These results
are simulated execution, not evidence that Incident B's SEND reached its MCU.
Existing reverse/ARQ tests cover CRC, pending packet at deadline, RX-arm rejection
without IRQ clearing, malformed lengths, and cleanup after transport failure.

Reset evidence limitation: installed DxCore
`cores/dxcore/main.cpp:init_reset_flags` lines144–151 reads RSTFR, clears observed
bits and stores GPIOR0; flags0 requests a software reset. Normal ARQ setup copies
GPR_GPR0 into BOOT diagnostics. Reverse setup does not log that value or reset
generation. Uptime/build/status are available, but no continuous reset record
survives this capture gap. Later programming resets cannot diagnose the earlier
SEND. A proposed reset logger must account for the core's existing early clear;
simply adding a late RSTFR read could record zero incorrectly. No such edit made.
