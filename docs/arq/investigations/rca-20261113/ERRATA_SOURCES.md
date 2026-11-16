# Claim and source log — 2026-11-13 follow-up

FACT: external technical claims below were checked against manufacturer-authored
documents or upstream source/maintainer records. High means directly verified
in the cited document/source; Medium means an author report, mirrored-document
provenance limitation or conditional inference. Neither label establishes physical
causation. UNKNOWN/UNVERIFIED entries are not recommendations to change hardware.

| ID | FACT / UNKNOWN claim checked | Source URL and version | Confidence / limit |
| --- | --- | --- | --- |
| S1 | FACT: vendor lists datasheet2020-05-26 and errata2019-07-02 | [Semtech SX1276 documentation](https://www.semtech.com/products/wireless-rf/lora-connect/sx1276) | High for listing; UNKNOWN whether the currently linked PDF differs from recovered Rev1 |
| S2 | FACT: six errata, V1b version12; BW125 IF tuple; packet-counter limitation | [Semtech-authored Errata Note mirror](https://www.ariat-tech.com/datasheet/cc/HMC615LP4E.pdf), printed Revision1, Sept2013, pp3–6 | High for inspected content; Medium for mirror equivalence to current vendor download; filename is misleading, document title/content were verified |
| S3 | FACT: official errata download did not deliver PDF here | [Vendor download](https://semtech.my.salesforce.com/sfc/p/E0000000JelG/a/2R000000HSPv/sqi9xX0gs6hgzl2LoPwCK0TS9GDPlMwsXmcNzJCMHjw), accessed2026-11-13 | High: returned1359-byte HTML form; not silently treated as PDF |
| S4 | FACT: AutomaticIFOn reset1; band-register access; CRC/IRQ semantics; HF/LF RSSI offsets; SF7/BW125 typical sensitivity−123dBm; offset limit±25%BW | [Semtech SX1276/77/78/79 datasheet](https://cdn.sparkfun.com/assets/7/7/3/2/2/SX1276_Datasheet.pdf), Rev7 May2020, pp20–21,37,40,106–115 | High for specified conditions; actual receiver sensitivity/carrier/power UNKNOWN |
| S5 | FACT: errata disabled by default, warning below62.5kHz | [RadioLib BuildOpt.h](https://github.com/jgromes/RadioLib/blob/7.1.2/src/BuildOpt.h#L57), tag7.1.2 | High; installed bytes matched tag |
| S6 | FACT: exact IF workaround branches and register calls | [RadioLib SX1278.cpp](https://github.com/jgromes/RadioLib/blob/7.1.2/src/modules/SX127x/SX1278.cpp#L600), tag7.1.2 | High; installed bytes matched tag |
| S7 | FACT: RX/TX lifecycle, W1C, FIFO and packet RSSI calculation | [RadioLib SX127x.cpp](https://github.com/jgromes/RadioLib/blob/7.1.2/src/modules/SX127x/SX127x.cpp#L392), tag7.1.2 | High; installed bytes matched tag |
| S8 | FACT: SX1276 begin order and carrier setter | [RadioLib SX1276.cpp](https://github.com/jgromes/RadioLib/blob/7.1.2/src/modules/SX127x/SX1276.cpp#L8), tag7.1.2 | High; actual installed source inspected |
| S9 | FACT: default-disable rationale from maintainer | [Issue388 maintainer comment](https://github.com/jgromes/RadioLib/issues/388#issuecomment-946094657), Oct2021 | High for rationale, Medium for reported hardware symptoms; BW<62.5 differs from current125 |
| S10 | FACT: historical offset-unit/RX-TX mistake | [Issue372 maintainer analysis](https://github.com/jgromes/RadioLib/issues/372#issuecomment-925301456), Sept2021 | High for historical report; installed path inspected separately, not an applicable diagnosis |
| S11 | FACT: historical initialization-order issue | [Issue251](https://github.com/jgromes/RadioLib/issues/251#issuecomment-778607264), Feb2021 | High for report; installed begin sets bandwidth before frequency |
| S12 | FACT: later errata path uses same BW125 tuple | [Pinned master SX1278.cpp](https://github.com/jgromes/RadioLib/blob/f45ac88212dcfbed2e6fa7a0485e815011d9c833/src/modules/SX127x/SX1278.cpp), commit2026-11-11 | High; saved diff/hash, not used as implementation of record |
| S13 | FACT: CRC/header/IQ historical discussions require path applicability | [IQ issue778](https://github.com/jgromes/RadioLib/issues/778), [sensitivity issue521](https://github.com/jgromes/RadioLib/issues/521) | Medium investigation clues; neither proves this hardware mechanism |
| S14 | FACT: DA reset flags W1C; BOD fuse modes; dedicated UPDI; PESIG read-clears | [Microchip AVR128DA DS40002183C](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-40002183C.pdf), 2021, pp47–53,119,529–554 | High; no AVR-DU/DB sibling substitution |
| S15 | FACT: RFM95W module reference architecture/supply specifications | [HopeRF RFM95W](https://www.hoperf.com/uploads/RFM95W-V2.0_1695351437.pdf), V2.0 | High for document design, UNKNOWN for actual assembly continuity/module authenticity |
| S16 | FACT: regulator product rating does not establish board feed path | [TI TPS7A02](https://www.ti.com/product/TPS7A02), manufacturer product page | High for rating; actual H1 feed/rail waveform UNKNOWN; no current at2dBm inferred from high-power specs |

FACT: local source references are authoritative for executed firmware paths:
`.pio/libdeps/sender_arq/RadioLib/src/BuildOpt.h:57,572`,
`modules/SX127x/SX1278.cpp:473,600`, `SX1276.cpp:8,88`,
`SX127x.cpp:392,571,645,656,1822`; line numbers refer to installed7.1.2.
Project `src/reverse_raw/main.cpp:18,51,84,96` defines the snapshot and control flow;
`src/arq/board_ssot.c:15` enables PA7 once in setup.
Transport `third_party/upditerm/upditerm.py:141,194,243,252` defines read and mailbox
contracts; its `last_tx` diagnostic is newer than Incident B.

FACT: retrieved PDF SHA256:

- Semtech errata mirror: `d31cd91430b1ba04cc237e38895fd210a3a33aaa15a30077eb10d7cf79e0c010`.
- Rev7 datasheet: `330745f933df00015d2de3efd582608339350ba3a21001d11b9d449839ce016b`.

FACT: download metadata, pinned-master comparison, issue JSON and full driver
function diff are retained in [errata-followup verification](errata-followup/).
Full manufacturer PDFs remain in the local research cache
`.automation/ack-investigation/errata-followup/`; no original incident capture was
altered or replaced. This report paraphrases findings rather than copying documents.

UNKNOWN: actual oscillator tolerance/temperature drift, RF output power, supply
transients, adapter thresholds, measured sensitivity and a current Semtech errata
revision newer than recovered Rev1. Obtain measurements/vendor confirmation as
appropriate; do not invent values from similar modules.
