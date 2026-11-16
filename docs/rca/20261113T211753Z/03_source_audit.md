# Source and transport audit

## Host UPDI / STATUS path

`SerialUPDI.__init__` opens half-duplex UPDI at 38,400 baud, sends the normal two BREAKs, enters OCD, and sets the virtual-UART enable flag. The optional reset path is only taken when `reset=True`; the reader-free SEND tests used the default `False`. Each `UPDI.instr()` prefixes SYNCH.

The old `UPDI.sts8()` encoded a one-byte STS address for writes to AVR128DA GPR mailbox registers at `0x1C–0x1F`. On the actual AVR128DA28 Tracker, the link returned ACKs, but a halted-CPU GPIOR1 probe showed a short STS write to address `0x1D` left the register unchanged. The 16-bit address STS changed it and was cross-read successfully; restoring the original `0x00` also verified. The corrected host `sts8()` uses `STS | (1 << 2)` and both address bytes while retaining strict ACK checks.

The real Tracker then completed 20/20 non-RF STATUS transactions with no response mismatch, timeout, Monitor exit, or identity mismatch. This proves a non-RF STATUS baseline for that run; it does not prove transport stability during radio activity.

## Host Monitor response failure

The Terminal reader polls `ASI_OCD_STATUS` (LDCS, request `55 85`) while waiting for application output. Active SEND traces report a one-byte expected response, a 1.0 s serial read timeout, and zero actual bytes. In reader-free trials, a later post-window LDS of GPIOR2 (request `55 00 1e`) also timed out after 1.0 s. These are observed UPDI response failures; neither alone proves USB disconnection.

The host error now preserves request/response bytes, lengths, configured timeout, read duration, and last request. It does not retry or relax response checks.

## Firmware command and reset-state path

- `src/reverse_raw/main.cpp:73–81` accumulates input bytes and dispatches on newline.
- `src/reverse_raw/main.cpp:54–64` validates the exact SEND line, queues `RAW_TX_PRE`, calls `radio.startTransmit`, then queues `RAW_TX` and `RAW_TX_STATE`.
- `src/reverse_raw/main.cpp:96–106` polls the virtual UART, reads radio IRQ flags, and queues `RAW_TX_DONE` only if the radio reports TxDone.
- `third_party/upditerm/updi_uart.c:52–69` polls GPIOR2/GPIOR3 and clears the RX-full bit when firmware consumes a byte.
- DxCore 1.6.2 startup at `cores/dxcore/main.cpp:145–150` copies `RSTCTRL.RSTFR` into GPIOR0 and clears RSTFR before the application runs. The reverse-raw app does not write GPIOR0.

The post-window reset snapshot is therefore taken from the core's retained reset-source byte. The subsequent reset recovery uses two normal BREAKs and a fresh UPDI session; it requests no CPU reset.
