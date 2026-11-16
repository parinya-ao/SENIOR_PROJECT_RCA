# UPDI first-failure boundary

## Captured evidence

OBSERVED: Incident B's [raw stderr](../../../../artifacts/arq/20261113T123620Z-reverse-raw/rf-monitor-receiver.stderr.log)
contains `UPDI response mismatch: expected None, received b''`.
`b''` is Python's representation of zero bytes, not ASCII b/0x62. The shortened
form `received b` in prose is not the original exception. The analyzer preserves
the whole original string and safely decodes complete bytes literals only.

Verified source: [SerialPort.recv](../../../../third_party/upditerm/upditerm.py#L141)
calls `dev.read(length)`, requires exactly length bytes and optionally compares
with a fixed expected value. `expected=None` skips value comparison, **not length
validation**. Empty data necessarily fails a nonzero-length request.
No evidence of an unexpected echo: that has a separate error message.

## Actual call graph and contracts

```text
Terminal.writer → SerialUPDI.send1 → UPDI.lds8(UART_FLAGS) → recv(1, None)
                                → sts8(UART_RX/FLAGS) → recv(1, ACK=40) twice
Terminal.reader → SerialUPDI.recv1 → ldcs(OCD_STATUS) → recv(1, None)
                                  → ldcs(OCD_MESSAGE) → recv(1, None)
UPDI.recv → SerialPort.recv → pyserial.read → TransportError
Terminal reader/writer catches → failure → Terminal.wait raises
main catches → stderr → sys.exit(1)
Capture.wait sees process.poll != None → 'monitor exited'
```

Sources: transport lines194–261 and Terminal lines318 onward; host runner
[Capture](../../../../tools/arq_trial.py#L172),
[monitor creation/termination](../../../../tools/rf_proof.py#L1211).
The transport failed at a response read with no fixed byte contract. Candidate
operations during SEND are command-mailbox LDS, status LDCS and message LDCS;
the exact request/address, thread, start/end time, request byte count, and parser
state are UNKNOWN. Earlier SIB/init calls also use unrestricted values, but had
completed before the logged startup. No stack trace/request log binds this
failure to one candidate. The last-request patch was added **after** the trial;
the copy under `follow-up-software/` cannot retroactively supply its bytes.

## Framing, adapter and lifecycle

Source configures 38400 baud, even parity, two stop bits, half-duplex echo,
one-second pyserial timeout. A shared lock serializes reader/writer transactions.
Each send verifies echo before receiving target data; no explicit `flush()`
waits for transmit completion, but blocking echo reads provide an observable
echo requirement. No blind retry follows a bad echo/read/ACK. The serial timeout
is configured, not a measured duration of the failing transaction.

The monitor first sends two low-speed BREAK bytes (300 baud), disables UPDI
contention detection, requests OCD access and enables the mailbox. It can resume
an OCD-stopped CPU during receive polling. Consequently starting a new monitor
is **not passive inspection**; this RCA does not start one. Process stderr and
the runner's `monitor exited` establish an application-process exit. Exact
exit code/PID/exit timestamp, USB disconnect, target low-level reply waveform,
adapter voltage and in-trial competing owner are UNKNOWN in the preserved bundle.
Source main intends exit1; that is not a captured wait-status measurement.
Owner checks before programming returned no conflicts; this is not continuous
port ownership telemetry. Existing stable paths map port1 to Tracker and port4
to Rudolph; ttyUSB numbering is not an identity guarantee. MCU serials are in
the evidence index. CP2102/switcher is operator-reported; no evidence establishes
an FTDI bridge or justifies changing a latency timer.

The trial's cleanup loop aborted at the first dead peer and failed to send X to
the live peer. The preserved source and empty X command journal demonstrate
this cleanup defect; it does not explain the original empty response. Current
`park_reverse` attempts both peers independently, a post-trial regression fix.
Unconditional later restoration succeeded. No production change was made here.

## Manufacturer cross-check and missing telemetry

[AVR DA DS40002183C §§35.2–35.5](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-40002183C.pdf)
defines dedicated half-duplex UPDI, SYNCH55, frame checking and turnaround guard
time. STATUSB offset01 exposes PESIG: 0 none,1 parity,2 frame,3 access timeout,
4 clock recovery,6 bus,7 contention. Reading clears PESIG. No STATUSB value was
captured. The supplied online error-handling link describes AVR DU; DA-specific
claims here use the DA datasheet instead. BREAK/reconnect can destroy first-failure
state; neither recovery nor high-voltage activation is performed.

Smallest future discriminating capture: retain request bytes/address/thread and
pyserial timestamps; analog UPDI at MCU and adapter RX plus MCU VDD and radio
rail, common trigger. At38400, bit period=26.0417µs and 8E2 frame=312.5µs
(DERIVED, not measurements). A clean MCU reply absent at adapter RX separates
loading/framing from target silence. Rail/reset correlation separates supply
failure from transport failure. Exact electrical levels require the actual
adapter datasheet and measured target voltage, not a universal 900mV criterion.
