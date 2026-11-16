# RadioLib 7.1.2 characterization

Run `python -m unittest discover -s tests -p test_radiolib_hal.py` with a C++11
compiler (`gcc-c++` and `libstdc++-devel` on Fedora). The test compiles the
installed `.pio/libdeps/sender_arq/RadioLib/src` driver, PhysicalLayer, Module
and Hal; no driver method is stubbed and no private-access macros are used.
Both modeled reset states (OpMode bit 3 clear/set) pass.

| Public call | Observed driver operations against the fake SPI bus |
| --- | --- |
| `begin(915,125,7,5,0x12,2,8,0)` | Resets/configures chip; preserves modeled reset bit 3 |
| `setFrequency(915)` | Writes carrier registers `E4 C0 00`; preserves bit 3 |
| `getIRQFlags()` twice | Returns the same flags; does not clear them |
| `clearIrqFlags(0x20)` | Clears only that bit in the W1C register model |
| `startTransmit()` | Writes exact FIFO bytes, clears flags, enters TX |
| `finishTransmit()` | Delays `1000000/1200` = 833 us, clears flags, enters standby |
| `startReceive()` | Standby, IRQ mapping/FIFO preparation, flag clearing, RX continuous |
| `readData()` | Reads current packet FIFO, checks CRC/header, clears IRQs even on CRC error |

`finishReceive()` is absent from the installed SX127x API. Use the existing
standby/read/startReceive sequence. Sources: installed `modules/SX127x/`
(`SX127x.cpp`, `SX1276.cpp`), `Module.cpp`, `Hal.h`; version pinned in
`platformio.ini`.

The fake bus supplies reset values and write-one-to-clear semantics. It tests
driver call behavior, not silicon behavior, RF reception, counter resets, or
the meaning of the band-register access bit. This is no justification for
changing OpMode bit 3.

Firmware now captures the polled IRQ flags before standby/FIFO reads and
snapshots registers `0x14..0x17` before RX restoration and ACK deadlines.
`RX_IRQ`, `RX_RESTART`, and `RX_TIMEOUT` encode six bytes: flags high/low,
valid-header count high/low, valid-packet count high/low. These are radio
observation windows, not lifetime totals: mode changes, reset and 16-bit
rollover can alter their interpretation. Compare snapshots from the same RX
window; counter lifetime across transitions still needs silicon evidence.

The [Semtech register table, p.111](https://cdn.sparkfun.com/assets/7/7/3/2/2/SX1276_Datasheet.pdf)
specifies header/packet counts since transition into RX and reset in Sleep.
Reverse-raw firmware therefore records counters while still in RX, before
standby/readData/startReceive or timeout cleanup. Counts are not lifetime totals.
The real driver HAL test also confirms modem 72/74/04 and normal IQ across
TX and RX. `invertIQ(false)` sets RX bit6=0, TX bit0=1 and IQ2=1D; RadioLib's
source explicitly documents the TX polarity workaround. Reserved bits explain
the fake-HAL IQ value01 versus actual27; neither is evidence of an IQ mismatch.
`RX_DONE_COUNT`, `DECODE_ERRORS`, and `CONTROL_REJECTS` are independent software
counters reset on a new ARM session, even if log delivery overflows.

`CONTROL_DISCARD rc` identifies type (1), peer (2), session (3), sequence (4),
or inactive transaction (5); expected session/sequence and received metadata
appear in the same event. `DECODE_DISCARD` follows a raw RX event whose bytes
permit independent codec analysis. Any overflow invalidates evidence.
