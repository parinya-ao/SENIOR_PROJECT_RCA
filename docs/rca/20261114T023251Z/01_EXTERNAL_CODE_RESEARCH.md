# External code and primary-source review

## Reuse decisions

| Component | Exact local version | Upstream / license | Use and conclusion |
|---|---|---|---|
| UPDI virtual terminal | `third_party/upditerm`, source declares version `1.1` | [streef/upditerm](https://github.com/streef/upditerm), GPL-2.0 | Reused for UPDI/OCD virtual UART. The local vendored copy has no pinned upstream commit metadata; local source is the implementation of record. No new package was copied. |
| RadioLib | PlatformIO package `7.1.2` | [RadioLib tag 7.1.2](https://github.com/jgromes/RadioLib/tree/7.1.2), tag commit `d26b1ff` | Existing installed driver was used unchanged. `BuildOpt.h` has `RADIOLIB_FIX_ERRATA_SX127X=0`. No dependency upgrade or errata setting change was made. |
| pySerial | `3.5`, existing environment dependency | [pyserial miniterm source](https://github.com/pyserial/pyserial/blob/master/serial/tools/miniterm.py), BSD-3-Clause | Not substituted for Upditerm: miniterm is a plain serial terminal and does not implement this project’s UPDI/OCD virtual-mailbox protocol. |
| pymcuprog | Not installed/used for this run | [Microchip pymcuprog](https://github.com/microchip-pic-avr-tools/pymcuprog) | Not used as a live monitor. Programming transport and monitor initialization have different side effects; existing verified project tooling was retained. |

The active `third_party/` directory contains Upditerm, not RadioLib. RadioLib is already installed under `.pio/libdeps/<environment>/RadioLib`; duplicating it into `third_party/` would add no capability.

## RadioLib behavior relevant to this run

- Installed `library.properties` and PlatformIO package resolution both report version 7.1.2.
- The current H01 receiver path uses `radio.getIRQFlags()`, `radio.standby()`, `radio.readData()`, and `radio.startReceive()`; the ACK path calls `radio.standby()` then `radio.startTransmit()`, then observes `TX_DONE`. The active path does not call `finishReceive()`.
- RadioLib 7.3.0 release notes list an SX127x `finishReceive()` IRQ-flag-clearing fix (#1592). That is a later-version clue, not a candidate explanation for this captured failure because the active receive path does not call `finishReceive()`.
- SX127x errata workaround remains disabled in the existing build. This is a configuration observation, not a proven cause of the reset or H01 timeout. No errata, IQ, frequency, bandwidth, output power, or `RegOpMode` bit was modified.

## Manufacturer facts used

- Silicon Labs CP2102/9 Rev. 1.8 specifies a 3.3 V regulator output with a maximum output current of 100 mA. This makes the operator-reported adapter-powered Tracker topology a **testable supply hypothesis**; it does not prove the actual adapter wiring, board current, or voltage droop.
- Microchip AVR128DA DS40002183C documents `RSTFR.PORF` and the POR/re-arm circuit. With BOD disabled, typical release and re-arm values are 1.6 V and 1.25 V. These are silicon typicals, not measurements from the Tracker.
- The same AVR128DA datasheet defines `BOOTSIZE=0` as no separate application partition. The active project SSOT also configures image start 0; this run used the current project’s bounded application writer and did not write fuses.

External sources and revisions are recorded in [SOURCE_LOG.md](references/SOURCE_LOG.md).
