# Gate 1 command and initialization audit

**OBSERVED — GATE1_BLOCKED_UNSAFE_COMMAND_PATH.** No serial port was opened.
The requested authorization explicitly prohibits automatic BREAK, target reset
and recovery. Existing monitor startup unconditionally performs two BREAKs.
This is an authorization incompatibility, not a diagnosed transport defect.

## Repository and implementation of record

OBSERVED: active ARQ V1 sources and incident archives are in
`/home/parinya/university/SENIOR_PROJECT_RCA`. The requested
`/home/parinya/university/iwing-tracker/gateway-lora/loraboard` is a separate
directory under Git root `/home/parinya/university/iwing-tracker`; its
PlatformIO configuration references `device-lora_dev` components. It is not
the `src/arq/main.cpp` implementation archived with these incidents. No existing
source in either location was changed. Current target firmware remains UNKNOWN.

## Ten source-level safety questions

| Question | OBSERVED source behavior | Reference |
| --- | --- | --- |
| Host command bytes | `STATUS\n` = `53 54 41 54 55 53 0A`; derived intended bytes, not captured live traffic | `tools/arq_trial.py:178–183` |
| UPDI operations | 8E2 half duplex; strict echo reads; LDS mailbox flags, STS data and flags, LDCS OCD status/message | `third_party/upditerm/upditerm.py:129–149,172–180,243–263` |
| Mailbox addresses | GPIOR2 flags `0x1E`, GPIOR3 RX character `0x1F`; volatile MCU I/O, not EEPROM/Flash | `upditerm.py:43–48,243–249` |
| Does STATUS trigger LoRa? | Its handler logs counters/identity, reads radio registers and ends; it does not call TX/RX mode methods. An already active application is a separate risk; current unarmed state was not verified | `src/arq/main.cpp:79–99,126–128,244–263` |
| Persistent writes | No Flash, EEPROM, fuse or NVM writer in the inspected STATUS path | same handler plus mailbox path above |
| MCU reset | STATUS handler does not reset. `-r` controls a separate explicit startup reset, but omitting `-r` does **not** suppress BREAK/OCD effects | `upditerm.py:216–218,230–236,454` |
| Initialization/recovery | Two unconditional BREAKs, contention-detection disable, OCD key, UART-enable write. Poller can reenable UART and run a stopped CPU. Destructors write disable operations | `upditerm.py:151–155,172–189,230–242,253–258` |
| Response length / termination | Each UPDI instruction requires its specified byte count; STS requires ACK `40`. Text STATUS is variable length and ends with LF-terminated `e=STATUS_END ... v=0`, not a fixed byte length | `upditerm.py:141–147,199–212`; `src/arq/main.cpp:79–99` |
| Complete STATUS | One BOOT, IDENTITY, STATUS, RESULT, four RTT records, RX_DONE_COUNT, DECODE_ERRORS, CONTROL_REJECTS, REG when ready, STATUS_END. Matching identity/session, ready=1 and zero overflow required | `src/arq/main.cpp:79–99`; `tools/arq_trial.py:76–81,196–210` |
| Safe identity/readiness acquisition? | Existing `-i` constructs UPDI and therefore sends BREAKs too. No audited already-active monitor/control channel was available. Current MCU identity is UNKNOWN | `upditerm.py:172–180,438–454`; `port-discovery.json` |

OBSERVED: `tools/rf_proof.py:1211–1222` launches
`uv run python -u third_party/upditerm/upditerm.py <port> 38400`.
That command **was not executed**. The campaign and restore commands also
program devices; neither is suitable for this authorization.

## Derived mailbox exchange, not a wire capture

For each command character, `lds8(0x1E)` emits `55 00 1E`, requesting one flag
byte. When RX-full is clear, `sts8(0x1F, character)` emits `55 40 1F`, expects
ACK `40`, writes the character and expects ACK again. Updating flags similarly
uses `55 40 1E`, then the observed flags OR `02`. The flags value is UNKNOWN
until read; it must not be replaced by zero. The reader polls `55 85` and
reads messages with `55 8D` when indicated. Each host write must echo exactly.
The constructor temporarily sets 300 baud for each BREAK before restoring the
requested baud. The existing SERIAL_TIMEOUT is 1.0 seconds; no timeout was
changed or measured here. Reader/writer locks serialize exchanges, but the
normal monitor polls even between application commands.

OBSERVED: attaching the virtual UART also causes firmware startup status via
`src/arq/main.cpp:245`; unsolicited startup and solicited STATUS must be drained
and distinguished in any future authorized acquisition. The fixed logger must
not be flooded. No startup response was captured in this run.

## Historical first failure, kept separate from this blocked run

OBSERVED: archived Incident B stderr is exactly
`UPDI response mismatch: expected None, received b''` plus LF.
The captured bytes representation means a zero-byte response. `expected None`
skips value comparison, not the strict byte-count requirement. The historical
message lacks the requested length and last request. Current source includes
`last_tx`, added after the incident; it cannot reconstruct historical bytes.

| Boundary in Incident B | Evidence classification |
| --- | --- |
| Host SEND queued to monitor stdin | CONFIRMED by archived command journal |
| Complete UPDI delivery to mailbox | UNKNOWN |
| Firmware parses SEND | UNKNOWN |
| Response read / length validation | FAILED: source plus empty-response exception |
| Exact failed UPDI instruction / request length / thread | UNKNOWN |
| Monitor propagates transport failure | CONFIRMED by stderr and capture errors; numeric exit code UNKNOWN |
| MCU reset, USB removal or rail sag | UNKNOWN; not established by monitor exit |
| RF start / TxDone | UNKNOWN in Incident B |

No new first-failure transaction occurred. `first_failure` is null, not the
historical Incident B error copied into a new transaction.

## PESIG and primary references

OBSERVED from Microchip AVR128DA28/32/48/64 **DS40002183C (2021), printed p553,
§35.5.2 / Table35-8**: STATUSB offset01 PESIG is read-to-clear. Codes are
0 none,1 parity,2 frame,3 access timeout,4 clock recovery,5 reserved,6 bus,
7 contention. Confidence HIGH, device-specific manufacturer source:
[AVR128DA datasheet](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-40002183C.pdf).
The supplied online STATUSB URL describes tinyAVR devices, so it was checked
against the AVR128DA PDF rather than substituted for it. The supplied online
communication-error URL returned HTTP503 during this review.

**PESIG_NOT_CAPTURED:** no target connection, no justified post-failure access,
and a read would clear error state. No BREAK/recovery/PESIG command was sent.
