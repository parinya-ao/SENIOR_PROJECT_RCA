# Gate 1 source and safety audit

## Repository selection

OBSERVED: the user supplied `gateway-lora/loraboard`, which has a `.git` root
at `/home/parinya/university/iwing-tracker` and contains only the legacy
`loraboard/src`, PCB files and PlatformIO configuration. It has no requested
`third_party/upditerm`, `tools/arq_trial.py`, ARQ docs or Gate 1 runner.
The active ARQ V1 implementation and the original incidents are in
`/home/parinya/university/SENIOR_PROJECT_RCA`. The live test therefore uses the
active source repo and its `config/current_hardware.json` mapping. No files in
the legacy repository or its pre-existing dirty worktree were modified.

## Monitor initialization

OBSERVED in `third_party/upditerm/upditerm.py`:

| Source | Effect |
| --- | --- |
| `SerialPort.__init__`, lines115–128 | Opens the requested serial port using configured parity/stopbits and a 1 s read timeout |
| `SerialPort.send_break`, lines151–155 | Temporarily sets300 baud, sends one `00` character, then restores baud |
| `UPDI.__init__`, lines172–183 | Sends two BREAKs; writes SYNCH-framed `STCS CTRLB, CCDETDIS`; may switch UPDI clock only when baud exceeds115200 |
| `UPDI.sib`, lines213–215 | Reads the32-byte System Information Block after SYNCH; no CPU reset call |
| `SerialUPDI.__init__`, lines230–236 | Sends OCD key; optional CPU reset is guarded by `if reset`; writes UART-enable flag to `GPIOR2` |
| `SerialUPDI.recv1`, lines252–263 | Polls OCD status; when STOPPED is observed it reenables UART and writes `OCD_RUN`; this resumes CPU execution, not a reset |
| `Terminal`, lines314–396 | Serializes UPDI mailbox operations with a lock and pumps device stdout/stderr |
| `main`, lines438–459 | Uses `SerialUPDI(..., arg.r)`; `arg.r` is optional, absent by default; Gate 1 does not set it |

The runner follows the same `UPDI(port,38400)` double-BREAK setup, then performs
read-only SIB/SIGROW reads before applying the Monitor's existing OCD key and
SRAM-mailbox enable. It constructs the same `SerialUPDI` interface for the
existing `Terminal` class. No `.reset()` call is made. Port opening requests
the OS exclusive lock; a visible owner or failed owner check stops acquisition.

## Why identity uses raw UPDI reads

The active hardware configuration maps `receiver` to Tracker serial
`42032240221092150158013400000000` on
`/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0`. Current udev must
match vendor10c4, productea60 and that exact USB path. The Monitor then requires
the firmware build and configuration to match the last verified Tracker
standby image and current ARQ config.

The exact unique MCU identity is read over the same traced UPDI connection.
Microchip AVR128DA28/32/48/64 DS40002183C (2021), printed pp39–43, maps SIGROW
to data space0x1100, Device ID offsets0–2 and unique SERNUM offsets0x10–0x1f.
The manufacturer lists AVR128DA28 signature bytes `1E 97 0A`, and describes
SIGROW as preprogrammed/read-only and readable via UPDI. The direct LDS byte
operation uses the documented LDS encoding with SizeA=01 (16-bit address) and
SizeB=00 (one-byte data), opcode04; addresses are transmitted least significant
byte first. Evidence: [AVR128DA datasheet](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-40002183C.pdf),
§7.2, §7.6, §35.3.3.1, Figures35-6/35-7. The test asserts the exact `04 10 11`
UPDI instruction for address0x1110 before using hardware.

The PlatformIO avrdude identity routine was **not** used: the installed tool is
AVRDUDE8.1, and its tagged `serialupdi.c` initialization enters NVM programming
and toggles CPU RESET in `serialupdi_enter_progmode`. That reset is not needed
for this Monitor acquisition. Source: [AVRDUDE v8.1 serialupdi.c](https://github.com/avrdudes/avrdude/blob/v8.1/src/serialupdi.c#L2719-L2865),
especially the `APPLY_RESET` operations; initialization caller at
[v8.1 lines3140–3298](https://github.com/avrdudes/avrdude/blob/v8.1/src/serialupdi.c#L3140-L3298).
This is why Gate 1 reads SIGROW directly rather than entering programmer mode.

## STATUS behavior and side effects

`src/arq/main.cpp:79–99` implements STATUS: BOOT/identity, counters and radio
register snapshot are logged; STATUS_END carries logger overflow. It does not
call radio TX or RX methods. `command()` at126–128 routes only the literal
STATUS command into this handler. The Monitor's command channel writes byte
mailbox GPIOR3 (`0x1f`) and flags GPIOR2 (`0x1e`), which are volatile SRAM
registers; status handler register capture uses SPI reads (`52–71`). No Flash,
EEPROM, fuse or USERROW command is part of this path. STATUS transactions are
sequential, with a complete parsed event block required before advancing.

## Historical separation and preservation

Incident A (20261113T121506Z) remains PHYSICAL_RF_FAILURE_UNISOLATED. Incident B
(20261113T123620Z) remains HOST_TRANSPORT_ERROR / RF INCONCLUSIVE. The earlier
Gate 1 artifact (20261113T142138Z) was blocked before serial open and had0
STATUS attempts. The three original manifests were checked before this run:
62,74 and67 entries; zero hash mismatches. The old1553-file preservation map
also matches before this run. See the run-directory per-incident integrity JSON.

## No reset, programming or RF actions

The identity reads only use SIB and LDS. The runner uses two documented startup
BREAKs and does not call RESET, CHIPERASE or memory programming. It never invokes
`tools/arq_trial.py`, `rf_proof.program_application`, `avrdude`, or any radio
command. Normal Monitor cleanup disables the SRAM mailbox and UPDI interface.

## External source claim record

| Claim | Primary source/version | Confidence |
| --- | --- | --- |
| SIGROW address, ID and serial offsets; readonly access | Microchip AVR128DA DS40002183C (2021), printed pp39–43 | High |
| LDS16 address and byte transfer, opcode fields | Same datasheet, printed pp537–538, Figures35-6/35-7 | High |
| AVRDUDE SerialUPDI initialization toggles RESET while entering NVM programming | AVRDUDE Git tag v8.1 `src/serialupdi.c` | High |

