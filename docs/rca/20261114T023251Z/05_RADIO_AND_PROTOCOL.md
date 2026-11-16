# Radio and protocol boundaries

## Runtime configuration observed

The active H01 snapshots show both radios configured for the shared nominal profile: 915 MHz (`Frf=E4C000` at the assumed 32 MHz reference), BW 125 kHz, SF7, CR 4/5, sync word `0x12`, explicit header, CRC enabled, normal IQ. Gateway and Tracker both entered RX Continuous (`RegOpMode=0x8D`) before the H01 DATA exchange. The Tracker is the ACK transmitter only if it receives and accepts DATA; that stage was not captured.

The raw forward proof at `artifacts/rf-proof/20261113T062148Z/receiver-final.upditerm.log` records 17 valid 11-byte `Hello World` CRC-clean receives: the first status counted 14 already matched packets, followed by explicit PASS rows for counts 15, 16, and 17. This proves PHY-level Gateway-to-Tracker reception in that historical run, not ARQ ACK success and not current link reliability.

## What the H01 logs establish

- Gateway readback showed RX state `0x8D` after arming for ACK reception.
- Gateway emitted five DATA frames and observed `TX_DONE` (`flags=8`) five times.
- Gateway later timed out five times and ended `TIMEOUT_EXHAUSTED`.
- Tracker preflight showed RX Continuous and ready before DATA. After the exchange, the Tracker POR invalidated the buffered UART evidence and the first UPDI read failed.
- No captured Tracker `RX`, `RX_IRQ`, `ACCEPT`, ACK `TX`, or ACK `TX_DONE` exists. These stages are **UNKNOWN**, not numeric zero and not proof of no RF reception.

## RadioLib and errata

RadioLib 7.1.2 remains the implementation of record. `RADIOLIB_FIX_ERRATA_SX127X=0` and `AutomaticIFOn=1` remain configuration observations. The receiver-IF workaround, `RegOpMode` bit 3, IQ, power, frequency, and PHY were not changed. `RegDetectOptimize` bit 7 and `RegOpMode` bit 3 are distinct registers/fields. No errata A/B was run.

The active ARQ receive source does not call `finishReceive()`, so the later RadioLib 7.3.0 `finishReceive()` IRQ-clearing fix is not a direct explanation for this capture. The H01 evidence does not expose an IRQ/FIFO event before POR, so radio IRQ handling remains unresolved.
