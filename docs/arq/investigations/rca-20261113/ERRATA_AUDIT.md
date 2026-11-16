# Receiver errata audit — offline follow-up, 2026-11-13

FACT labels below include directly verified source/document statements; calculations
are labeled FACT (derived). HYPOTHESIS means untested causation; UNKNOWN means
missing observation. This addendum supplements the original RCA without changing it.
Primary-source versions, URLs and confidence are in [ERRATA_SOURCES.md](ERRATA_SOURCES.md).

## Applicability to 915 MHz / BW125 / SF7

FACT: the recovered **Semtech SX1276/77/78 Errata Note, Revision 1, September
2013**, identifies V1b by RegVersion=12. Both captured radios report 12.
Its filename includes `1.1`, but the document's printed revision/history says
Revision 1; no Revision 1.1 technical update is inferred. The current vendor
product page lists an errata download dated 2019-07-02. Its download returned an
HTML form here, so the recovered manufacturer PDF is from a distributor mirror;
equivalence to the vendor's currently served PDF is UNKNOWN.

| ID in recovered SX1276 note | FACT: subject | Applicable? | Reason / diagnostic consequence |
| --- | --- | --- | --- |
| 2.1 | Sensitivity tuning at BW500 | No BW500 tuning; restoration condition matters | BW125 is outside the optimization. For other settings the note specifies 36=03; verify this baseline, do not introduce 36=02 or 3A=64. |
| 2.2 | Reduced offset tolerance at BW500, SF10–12 | No | Both bandwidth and SF differ. The note identifies no workaround. |
| 2.3 | Off-channel LoRa spurious reception / receiver IF | Yes as configuration audit; causation UNKNOWN | Intended to improve rejection of interfering LoRa with compatible modulation. No such interferer was measured in these trials. |
| 2.4 | Valid-packet counter offset | Yes | RX Continuous can omit its first valid packet; RX Single does not increment it. Use an independently observed RxDone/CRC event. |
| 3.1 | Very short FSK PayloadReady with already emptied FIFO | No | These experiments use LoRa, not FSK packet/FifoLevel servicing. |
| 3.2 | IBM whitening incompatibility in FSK | No | No IBM-compatible FSK whitening is used. |

FACT: all six entries in this recovered note are mapped. Two are relevant to
the present receiver investigation. SX1272/73 uses different numbering (its
counter issue is 2.3); that numbering must not replace SX1276's 2.4.
SX126x AGC errata and sibling AVR-DB/AVR32DA mechanisms are not verified defects
of this SX1276/AVR128DA system.

## Exact receiver-IF candidate

FACT: section 2.3 Table 1 is an image; it was visually inspected on PDF page 5,
not inferred from a text extraction that omits its cells. Its BW125 column gives:

| Setting | FACT: required BW125 value | Existing physical observation | Scope |
| --- | --- | --- | --- |
| 31.bit7, AutomaticIFOn | 0 | C3 → bit7=1 in Rudolph active RX | Candidate C3→43 preserves other bits |
| 2F, IfFreq2 | 40 | UNKNOWN; absent from snapshot | Required accompanying setting |
| 30, IfFreq1 | 00 | UNKNOWN; absent from snapshot | Required accompanying setting |
| Frf offset | None | E4C000, nominal 915 MHz | No carrier trim |
| 01.bit3 | No change in this candidate | 1 in 89/8D | Separate test-register-bank control |

FACT: the same IF values apply at BW62.5/250. Smaller bandwidth columns require
different IF values and positive RX carrier offsets; BW500 retains automatic IF.
The note requires applying the sequence in Sleep/Standby and reapplying IF
settings after reset or after re-enabling automatic IF. Section 2.3 does not say
that an unpatched receiver must miss every intended on-channel packet.

FACT: Rev7 datasheet page115 gives AutomaticIFOn reset=1 and an instruction to
clear it after reset. This is a documented default, not a physical reset trace.
Installed source resets the radio, changes only DetectionOptimize bits2:0 for
SF7, and does not clear bit7 with the default errata option. Physical evidence
shows C3 in standby and active RX. The immediate post-reset byte was **not captured**.

FACT: RegOpMode bit3 is a different register and control. Rev7 pages106/108
describe access to band-specific test registers (61 onward). Installed mode
updates preserve it. Neither a high Frf value nor 89/8D proves that this bit
caused RF loss. The candidate does not change it.

## RadioLib implementation of record

FACT: installed library.json says 7.1.2. Fresh downloads of tag7.1.2 BuildOpt.h,
SX127x.cpp and SX1278.cpp are byte-identical to the inspected installed files.
BuildOpt.h:57–64 documents the below-62.5kHz warning and disabled default;
BuildOpt.h:572–576 suppresses the errata call when the switch is zero.
No project build flag enables it. See [register/write audit](ERRATA_REGISTERS.md).

FACT: SX1278.cpp:600–689 implements the workaround. Across all branches it can
write 36/3A (BW500 only), 01 (Standby), 06/07/08 (carrier), 31.bit7, 2F and 30.
At BW125 it uses no frequency offset and does not execute the 36/3A branch.
SX127x::setFrequencyRaw forces an LSB write even if the carrier is unchanged;
other SPIsetRegValue calls may omit identical-value bus writes. Therefore a
correct 30=00 readback may occur with no new 30 write when it was already zero.
The implementation does not provide the software packet counter for erratum2.4.

FACT: upstream issue388 explains the default: users reported failures below
62.5kHz; the maintainer retained optional spurious-response mitigation rather
than requiring it for basic radio operation. Issue372 describes older incorrect
frequency-offset units and RX/TX application. Installed7.1.2 already separates
RX/TX frequency choice, and BW125 adds zero offset. Those old reports do not
establish this incident's cause. Issue521's later SX126x AGC discussion is not
an SX1276 diagnosis. [Exact issue references](ERRATA_SOURCES.md).

FACT: master was pinned to f45ac88212dcfbed2e6fa7a0485e815011d9c833
(2026-11-11). Its errata body uses integer Hz/switch cases instead of floats;
the BW125 tuple remains bit7=0 / 40 / 00 / no offset. The saved function diff
does not establish a newer BW125 fix or justify upgrading during RCA.

## Counter and receive-event interpretation

FACT: B's packets=0 and headers=0 were recorded at **RX_READY before SEND**;
there is no later B timeout/counter observation. A has a complete 15000ms timeout
but its older image did not capture header/packet history. Neither record proves
zero headers or zero physical packets over both entire windows.

FACT: erratum2.4 means a zero continuous-RX packet counter is compatible with
one CRC-valid received packet. It does not explain an absent RxDone by itself.
The safe diagnostic is to snapshot IRQ12 before readData/rearm/clear, observe
RxDone40, CRC-error20, ValidHeader10 and timeout80 independently of DIO, record
CRC presence from HopChannel1C.bit6, and increment a software counter **once per
consumed event**. Repeated polls of a latched bit must not count again. A CRC-clear
flag alone, without RxDone or with CRC absent, is not a validated CRC packet.

FACT: tools/rca/errata_audit.py interprets archived single-event samples this way;
it is not a live poller and does not infer unrecorded events. Missing flags/counts
remain null. Production packet handling is unchanged.

FACT: installed startReceive() uses RX Continuous when timeout=0, programs DIO,
clears IRQs, resets FIFO pointers and enters RX; the application supplies the
15000ms deadline. Hardware RxTimeout is not the application's continuous-RX
deadline. readData clears flags; finishTransmit clears flags. getIRQFlags does
not clear them. The reverse firmware polls SPI IRQs and handles RxDone before
the deadline; a DIO wiring defect alone cannot explain failed polling.

UNKNOWN: RF energy at Rudolph, preamble/header history in A, Tracker active-TX
state in B, and any IRQ that was lost outside captured observations. A simultaneous
SPI/IRQ trace and independent RF reference are needed to isolate event loss.
