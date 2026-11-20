# LoRa Chat Firmware and Installed-Image Requirements

The console uses the existing readback-verified UPDI monitor and the same
`reliable::Transport` used by the Gateway and Tracker. UPDI programmer stdin is
not treated as an application data channel. No firmware is flashed by the chat
command.

## Source-level interactive protocol

The production `sender` and `receiver` sources now implement bounded interactive
DATA and Tracker Echo without a second ARQ engine or a full-message MCU buffer.
The host keeps one transaction in flight and derives its per-packet limit from
fresh capability records from both devices.

The existing firmware monitor command channel is:

| Command | Meaning | Required response |
|---|---|---|
| `B` | Enter the existing bench control state and select a fresh campaign | `BENCH_READY` |
| `V` | Query interactive support | `INTERACTIVE_CAPS MAX_DATA=<bytes> ECHO=1` |
| `I` | Enable interactive mode after radios are ready | `INTERACTIVE_READY MAX_DATA=<bytes> ECHO=1` |
| `X<length:2 hex digits><payload:hex>` | Submit one bounded DATA fragment | Real DATA/ACK/Echo/ACK events |

`MAX_DATA` is the minimum of the existing transport buffer and bounded UPDI
payload-log capacity. The host uses the lower value advertised by Gateway and
Tracker, converts messages to UTF-8, and fragments only at that negotiated
limit. Fragments are sent sequentially; each retains the existing campaign and
sequence identity. Sequence rollover starts the protocol's next campaign.

For each fragment, Gateway sends DATA and waits for the existing ACK. Gateway
then sends a matching ACK confirmation with the DATA type as a third byte.
Ordinary ACK and NACK frames remain two bytes. Tracker sends Echo DATA only
after it receives the tagged confirmation. Gateway retries the confirmation
within the configured attempt budget while waiting for Echo DATA. It validates
the Echo bytes against the original fragment and re-ACKs exact Echo duplicates
if Tracker retransmits. The host reports a round trip only after it observes
both addressed DATA legs, both ACK
legs, the ACK confirmation, and exact reassembly. An ACK by itself is ACK-only,
never Echo success.

## Connecting to the installed boards

Start `uv run --no-sync python -m tools.lora_chat` on this bench. The
`confirmed_bench_receipt` setting in `config/lora_chat.json` saves the confirmed
915 MHz arrangement and reviewed upload receipt for the enrolled boards. When
the receipt is present, the console enables bounded RF sends after verification.
It transmits DATA only after you enter a message. Use `--no-authorize-rf-test`
for read-only firmware diagnostics or `--dry-run` without device access.

With the reviewed legacy pair, Chat compares fresh full Flash, serial,
signature, and fuses on both boards with the archived receipt and binary
readbacks. It then checks both runtime build IDs and the live 915 MHz profile.
Unrecognized firmware stays visible in diagnostics with DATA disabled. Each
board's panel shows USB presence, enrolled MCU serial, current-build byte
comparison, live build ID, radio status, and FOTA status.

After both current builds are installed and byte-verified, the console selects
Echo automatically from the two fresh `V` responses. Type UTF-8 text directly,
or use `/send <text>` for text beginning with `/`. The message journal records
the original and returned text, fragment count, attempts, retries, and
per-fragment elapsed time on the Gateway clock. Host elapsed time includes
bench preparation, serial capture, and cleanup.

Without the saved bench receipt, use `--authorize-rf-test` and
`--confirm-rf-setup` after confirming the connected radio and antenna setup.
Use `--historical-receipt PATH` to select a reviewed legacy pair. The run
directory records the effective settings, board status, and timestamped events.

The reviewed legacy firmware accepts exactly `hello world`. Chat releases the
Tracker UPDI monitor during the exchange and reopens it to collect buffered
Tracker events. A correlated DATA/ACK is logged separately from application
Echo. Arbitrary UTF-8 requires fresh Echo capabilities from both runtimes.

## Installed Flash layout

The reviewed pair has `BOOTSIZE=0x00` and `CODESIZE=0x00`. Its full Flash is
BOOT, and FOTA is unavailable. Chat only reads Flash and fuses. Production
programming retains its exact image and APPCODE checks.
