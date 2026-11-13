# Exact RadioLib and register audit

Implementation of record is local `.pio/libdeps/sender_arq/RadioLib`, library.json
version7.1.2. Other normal/test/raw dependency copies were historically compared;
no library was upgraded or patched. Named SX127x register constants match the
diagnostic address order. Main sources: `modules/SX127x/SX127x.cpp`, `SX1276.cpp`,
`SX1278.cpp`, `Module.cpp`, `BuildOpt.h`. Installed source remains authoritative.

## Initialization and lifecycle

Actual `SX1276::begin` order: common begin (module init/findChip/reset/version,
standby/config/modem/sync/current-limit/preamble/IQ), bandwidth, frequency,
SF, CR, output power, gain, CRC. Firmware subsequently explicitly selects2dBm
PA_BOOST, explicit header, CRC, normal IQ and standby. Explicit reset before
begin is followed by driver's findChip reset; no receive reinitialization loop.

| Call / source line | State effects |
| --- | --- |
|SX127x::setMode:1709|Writes bits2:0 only; preserves bit3 |
|setFrequencyRaw:1193|Standby unless hopping; Frf writes including forced LSB write |
|startReceive:392|Standby, DIO mapping, optional errata macro, clear IRQ, FIFO base/pointer, RX Continuous |
|getIRQFlags|Read only; polling needs no DIO interrupt |
|readData:658|Length/header/CRC checks, current FIFO pointer, reads bytes, discards excess, clears IRQ even on error |
|startTransmit:571|Standby, length bounds, mapping/IRQ clear/FIFO bytes, optional errata macro, TX |
|finishTransmit:645|833µs delay, clear IRQ, standby |
|finishReceive|Absent from installed SX127x7.1.2; no call in this firmware |

Repeated startReceive would clear events/reset FIFO pointers; repeated RX commands
in this firmware reject before calling it. In RX loop, flags/counters are captured
before readData and cleanup. Header/packet counters describe an RX observation
window; manufacturer specifies reset in Sleep. Post-cleanup zero cannot replace
an unobserved active-window value. Actual DIO0 maps RX00/TX40; polled IRQ handling
is used, not a mixed ISR/poll consumer. Pending RxDone is handled before timeout.

## Register definitions and operational evidence

[Semtech SX1276 Rev7 §§6.3–6.4, pp106–115](https://cdn.sparkfun.com/assets/7/7/3/2/2/SX1276_Datasheet.pdf)
is the register authority. Bit7 LoRa, bit6 shared-page access, bits5:4 reserved,
bit3 band-specific test-register access, bits2:0 mode explain89/8B/8D. Bit3 resets
to1; inspected initialization/frequency/mode paths preserve it. The table
describes LF/HF register access, not proof of an incorrectly tuned carrier.
No test establishes its RF effect here; changing it would require a hypothesis
and separately authorized single-variable test.

DERIVED: Frf0xE4C000=14,991,360; using32MHz/2^19 gives exactly915,000,000Hz.
The crystal's actual frequency/accuracy is unmeasured. Tcxo09 has external TCXO
bit4 clear, consistent with a passive crystal; it does not physically verify one.
ModemStat04 means RX ongoing(bit2), not signal synchronized(bit1) or detected(bit0).
IQ27/1D matches installed invertIQ(false), which deliberately swaps TX bit0
interpretation relative to datasheet wording (documented [issue778](https://github.com/jgromes/RadioLib/issues/778)).
The detailed LoRa table gives IQ2 normal1D/inverted19; an abbreviated summary
reset02 must not replace that detailed setting.

| Register/address | B Rudolph active RX | Meaning | B Tracker pre/active/post TX |
| --- | --- | --- | --- |
|Version42|12|Device revision|NOT CAPTURED|
|OpMode01|8D|LoRa continuous RX, bit3 retained|NOT CAPTURED|
|Frf06–08|E4C000|915MHz at nominal32MHz reference|NOT CAPTURED|
|PaConfig09 / PaDac4D|F0 /84|PA_BOOST2dBm configuration|NOT CAPTURED|
|Lna0C|23|Gain code1; HF boost bits1:0=3; AGC from modem3|NOT CAPTURED|
|IRQ mask11 / flags12|00 /00|No masked events / readiness snapshot|NOT CAPTURED|
|RxNbBytes13|NOT CAPTURED|Not part of this23-byte snapshot|NOT CAPTURED|
|Header14–15 / Packet16–17|0 /0|Separate RAW_RX_READY observation only|NOT CAPTURED|
|ModemStat18 / Hop1C|04 /00|RX ongoing; no received-header CRC assertion|NOT CAPTURED|
|Modem1D /1E /26|72 /74 /04|BW125,CR4/5,explicit,SF7,CRC bit set,AGC|NOT CAPTURED|
|Preamble20–21 / Sync39|0008 /12|8-symbol configured preamble / private sync|NOT CAPTURED|
|IQ33 /3B|27 /1D|Library normal-IQ settings|NOT CAPTURED|
|DIO40 /41|00 /00|DIO0 RX mapping|NOT CAPTURED|
|Detect31 / threshold37|C3 /0A|AutomaticIFOn1; SF7–12 detection|NOT CAPTURED|
|HopPeriod24 / Tcxo4B|00 /09|No hopping / external TCXO disabled|NOT CAPTURED|

Standby snapshots agree on all23 bytes for both boards; only Rudolph's
standby→RX mode differs as expected. This is not a Tracker TX operational match.
Incident A has TX/TxDone events but none of these operational snapshots.
IRQ flags RxTimeout80/RxDone40/CRC20/Header10/TxDone08 are write-one-to-clear;
read alone does not clear them. A's final flags0 describes its captured endpoint;
header history was not instrumented then. B has no terminal IRQ/counter snapshot.

## Confirmed errata configuration concern, causal status UNKNOWN

OBSERVED source: `BuildOpt.h:62–63` defaults RADIOLIB_FIX_ERRATA_SX127X to0;
lines572–575 make RADIOLIB_ERRATA_SX127X an empty macro in that case.
Project flags do not enable it. `SX1278::errataFix:600–690` exists but is not
therefore automatically applied. The active C3 snapshot confirms bit7 remains1.
Semtech's detailed DetectOptimize31 table says AutomaticIFOn should be cleared
after reset. This is a demonstrable configuration concern, unlike merely
guessing that OpMode bit3 is wrong. It does **not** establish RF causation.

New `tests/rca_errata_test.cpp` compiles the real installed driver twice against
the existing public fake HAL. With modeled C3/IfFreq2=20 at RX entry, disabled
workarounds retain C3/20; enabled workarounds produce43/40 and IfFreq1=00. Both
retain915MHz and OpMode8D. This is software characterization, not a silicon/RF
result. No production compile flag was changed.
The500kHz sensitivity branch does not apply toBW125. Spurious-response branch
atBW125 selects31.bit7=0,2F=40,30=00 without frequency offset. Registers2F/30 were
not physically captured. Semtech's old errata URL redirects to documentation
search; full standalone errata retrieval is a limitation. The detailed Rev7
register instruction and installed implementation were independently inspected.

Proposed future test: after transport/supply first-failure evidence is acquired,
compare only the existing errata compile switch against baseline under separate
authorization and external reference endpoint; preserve actual43/40/00 snapshots
and payload/CRC results. Do not bundle an OpMode-bit change or IQ change.

## Version clues, not upgrades

[7.1.2 release](https://github.com/jgromes/RadioLib/releases/tag/7.1.2) includes
[PR1369](https://github.com/jgromes/RadioLib/pull/1369/files), merged as
`680e88c7394a103e1fe9f1b1fe057e36a2c54d3d`: force Frf LSB writes even if unchanged.
The fix is already present locally. A test would program two frequencies with
the same LSB and inspect actual LSB write transactions; carrier readback alone
does not exercise the older skipped-write defect.
Later commit `937efe10eb86ff63aff5b339ba8b6e11a77a6d99` protects FSK FIFO in
finishReceive; installed7.1.2 lacks that API and uses LoRa. Later
`9c1f741febb2e2f5c3676b5e54ba3912ca388418` changes blocking FSK receive timeouts;
this nonblocking LoRa path does not exercise it. Later
`da2e5954e31988f3a17c191a248417b9c6e2333e` removes readData's damaged-header check;
7.1.2 contains it, but neither incident captured RxDone/readData rejection.
It cannot explain the observed absence of that upstream event. A targeted
future fake-HAL test would inject RxDone with header CRC bit clear, rather than
assume a library upgrade solves absent RF. Exact upstream diffs were reviewed;
no replacement/master driver was used to describe installed behavior.
