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
the original and returned text, both SHA-256 hashes, captured transaction events,
fragment count, attempts, retries, and per-fragment elapsed time on the Gateway
clock. The console decodes and displays the reassembled bytes from Gateway RX
after matching the original bytes. Use `/mode` for the capability state and
`/metrics` for session counters. Host elapsed time includes bench preparation,
serial capture, and cleanup.

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

For the enrolled all-BOOT bench pair, prepare a reviewed laboratory replacement
and rollback package with `uv run --no-sync python -m tools.lora_chat.prepare_echo_deployment`.
Preparation builds and inspects both images, reads the installed boards, and
rehearses the package offline with AVRDUDE `dryrun`. The generated operation
requires explicit approval for the listed BOOT pages and both exact HEX files
per target. Both images are linked at address zero. This path keeps the
all-BOOT layout and leaves FOTA unavailable.

## Laboratory deployment and recovery

1. Quit every bench console and verify that the enrolled UPDI adapters are
   free. Keep the confirmed bench power and RF connections in place. Confirm
   that the package shows `AWAITING_EXACT_AUTHORIZATION` and record its SHA-256.
   Obtain explicit approval for the exact manifest, targets, ranges, and
   replacement and rollback images.
2. On each role, use `tools.receiver_boot.read_snapshot` with
   `current_target=True` and `include_usersig=True` in a new evidence directory.
   Compare every memory hash with `pre_write_memory_sha256` and check the
   recorded adapter path, MCU serial, signature, and fuses. Check the exact
   install and restore page HEX SHA-256 values again immediately before use.
   A mismatch requires fresh review before any erase.
3. Install Tracker first, then Gateway. Run the manifest's `install_argv`
   once per target as an argument vector with the platform's reviewed AVRDUDE
   8.1, no shell, and a bounded timeout. The command verifies serial and fuses
   first and requests single 512-byte Flash-page erases. The only write is the
   specified page image. Keep the full original backups and command output.
4. Before moving to the next board, collect another independent full memory
   snapshot. Call `tools.receiver_boot.require_preserved` with both snapshots
   and the approved half-open range. Compare the entire resulting Flash with
   `expected_flash_sha256`. Record both results, then confirm runtime build IDs
   and compatible `INTERACTIVE_CAPS` from both devices before RF acceptance.
5. On programming failure, stop before touching the second target. If the
   changed target remains reachable and every original non-Flash memory and
   every byte outside the authorized span still matches, use the separately
   approved `restore_argv` and verify the entire original Flash SHA-256.
   After an unsuccessful RF campaign, park and release both radios before any
   approved rollback. Loss of UPDI or unexpected memory changes require
   recovery inspection. A chip erase or fuse change needs a different reviewed
   operation.

A production BOOT/APPCODE migration requires a compatible startup image and
relocated application for each role. Confirm their linker bounds, reset
handoff, interrupt placement, and recovery on the intended fuse geometry
before provisioning it. The laboratory package does not perform that migration.

After authorized installation and full readback verification, run the physical
acceptance campaign with both serial ports free:

```sh
uv run --no-sync python -m tools.lora_chat.echo_trials \
  --authorize-rf-test --confirm-rf-setup
```

The runner requires two verified Echo-capable runtimes, then sends ten messages
including Thai, command-like text, and a 1024-byte UTF-8 input. It runs a
separate one-shot NACK recovery trial and suppresses one return payload after
the Tracker receives the ACK confirmation. That negative trial requires a
matching observed forward ACK and Gateway Echo timeout. The runner writes a new
directory under `artifacts/lora-chat/` and releases both monitors on exit.
