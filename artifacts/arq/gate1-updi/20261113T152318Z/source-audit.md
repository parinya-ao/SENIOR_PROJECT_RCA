# Gate 1 source audit

The active ARQ V1 source and evidence repository is `SENIOR_PROJECT_RCA`. The
user-supplied `gateway-lora/loraboard` directory is a separate legacy component
under the `iwing-tracker` Git root; it does not contain the specified ARQ
runner, UPDI Monitor or investigation files. No files in that legacy worktree
were changed.

## Normal UPDI Monitor path

In `third_party/upditerm/upditerm.py`, `UPDI.__init__` at172–183 sends exactly
two `00` BREAK characters at300 baud, restores38400 baud, and sends a SYNCH
framed STCS to disable contention detection. It does not call `reset()`. The
normal Monitor initializes SerialUPDI at230–236: OCD key followed by volatile
UART enable. The optional reset parameter defaults false and the reset call is
conditional. `Terminal` at314–396 serializes its reader/writer traffic.
`SerialUPDI.recv1` at252–263 resumes a STOPPED CPU through OCD_RUN; this is a
resume action, not a reset. Gate 1 records any occurrence. Normal cleanup
disables the mailbox and UPDI interface. No BREAK/recovery loop is used.

For identity, the same UPDI link reads the32-byte SIB and then reads the
read-only signature row. Microchip DS40002183C (2021), printed pp39–43, maps
SIGROW at data address0x1100, signature bytes at offsets00–02 and unique
serial bytes at offsets10–1f. AVR128DA28 signature is `1E 97 0A`.
The LDS instruction uses SizeA=01 for a16-bit address, SizeB=00 for one-byte
data, opcode `04`; address bytes are low then high. Gate 1 reads addresses
0x1100–0x1102 and0x1110–0x111f over the captured UPDI transport. These are
read-only accesses; no NVM programming key or data write is involved.

The normal monitor then uses the same OCD and SRAM-mailbox operations as the
existing SerialUPDI class. Status requests access GPIOR2 at0x1e and GPIOR3 at
0x1f. Firmware `status()` in `src/arq/main.cpp:79–99` reports readiness,
overflow, session, counters and register snapshot. `command()` at126–128 routes
STATUS to that handler; it does not initiate TX or RX. The status loop may
continue unrelated existing firmware work, so successful complete status and
idle session are checked each time.

## Reset-capable identity alternative excluded

The installed AVRDUDE is8.1. Its normal SerialUPDI initialization enters NVM
programming. The tagged source `serialupdi.c` calls `serialupdi_enter_progmode`
and toggles APPLY_RESET/RELEASE_RESET. That optional identity method was not
used because Monitor acquisition does not require reset. Primary source:
[AVRDUDE v8.1 SerialUPDI source](https://github.com/avrdudes/avrdude/blob/v8.1/src/serialupdi.c#L2719-L2865)
and [initialization](https://github.com/avrdudes/avrdude/blob/v8.1/src/serialupdi.c#L3140-L3298).

## Target and application identity

`config/current_hardware.json` maps Tracker's receiver role to
`/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0`, the configured Tracker
MCU serial and expected fuse baseline. Before opening the port, Gate 1 checks
that stable path resolves, udev reports CP2102 VID10c4/PIDea60 at USB path
`pci-0000:00:14.0-usb-0:1:1.0`, `fuser` reports no owner, and serial opening
obtains the exclusive OS lock. Live SIB, signature and unique serial are then
compared to AVR128DA28 and current hardware configuration. Startup firmware
build/config and receiver role are compared to the last verified Tracker
standby image and generated ARQ manifest. A mismatch stops before STATUS.

## Historical incident boundary

Incident A `20261113T121506Z` remains PHYSICAL_RF_FAILURE_UNISOLATED. Incident B
`20261113T123620Z` remains HOST_TRANSPORT_ERROR / RF INCONCLUSIVE. A later
monitor disconnect is not treated as proof of reset or USB removal. The blocked
`20261113T142138Z` Gate 1 attempt had0 STATUS requests. Its two-break conflict
was resolved by this task's explicit authorization; it is not hardware evidence.

