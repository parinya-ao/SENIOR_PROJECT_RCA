# Official-source review: AVR128DA target and power path

Retrieved 2026-10-27. This is a source review for RCA_PHY_01, not a claim about either assembled board.

## Primary sources and revisions

| Source | Revision/date | Official URL | Local raw copy |
|---|---|---|---|
| AVR128DA28/32/48/64(S) complete data sheet, DS40002183E | Rev. E, 09/2024; ©2024 | https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-DS40002183.pdf | AVR128DA28-32-48-64-DS40002183.pdf and pdftotext extraction |
| AVR128DA28/32/48/64(S) Silicon Errata and Data Sheet Clarification, DS80000882F | Rev. F, 09/2024; ©2024 | https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/Errata/AVR128DA-28-32-48-64-SilConErrataClarif-DS80000882.pdf | AVR128DA-DS80000882.pdf and pdftotext extraction |
| Microchip online AVR UPDI Interface | Section 3.3.5.3; page does not expose a revision date, accessed 2026-10-27 | https://onlinedocs.microchip.com/oxy/GUID-E7CBBF9B-B23F-4E8A-8B9D-C66C24729842-en-US-1/GUID-B29416BA-442A-461F-A90F-542C149DC9CC.html | microchip_avr_updi_interface.html |

The data sheet and errata revision dates above were read from their revision-history pages, not inferred from search-result dates. The data sheet itself directs readers to the device PDF because the online versions are provided as a courtesy.

## Device-specific electrical and layout guidance

### Supply decoupling and placement

Data sheet §4.2, Figure 4-1 (printed page 21, DS40002183E-21) labels typical recommended supply capacitors as:

- C1: 100 nF, called the primary decoupling capacitor in the figure.
- C2: 1–10 nF, called the high-frequency decoupling capacitor.
- C3: 1 µF, optional; the figure footnote associates it with frequent VDD cycling or fast VDD transients beyond the supply slew-rate limits.

The same section says to provide a decoupling capacitor for each supply pin pair, place it close to the VDD/GND pair, prefer the MCU side of the PCB, keep any via path short if the opposite side is unavoidable, route supply and return to the capacitor before the device pins, and minimize the capacitor-to-pin trace length. For noise above tens of MHz it recommends a second ceramic capacitor next to the primary capacitor. It says example values are typical and a real design can require other values. The DA-family pinout note says VDD and AVDD are internally connected, with no separate power domains.

**Document ambiguity requiring an explicit caveat:** the same Rev. E document's revision history (§41.4, printed page 696, DS40002183E-696) says Rev. B changed the “primary decoupling capacitor” from 100 nF to 1 µF. This conflicts with the Rev. E current Figure 4-1 and Figure 4-3 labels, which still call C1=100 nF the primary value and show C3=1 µF as optional. Figure 4-3 (§4.4.1, printed page 22) repeats C1=100 nF and C2=1–10 nF and requires the VDD/GND decoupler to be as close to the pin pair as possible, even without a UPDI connector. I do not resolve this contradiction or silently substitute one value for the other; obtain Microchip clarification before treating either value as the only authoritative primary capacitor.

### RESET and UPDI physical connection

- §4.3 and Figure 4-2 (printed page 21) describe RESET as active-low with an internal pull-up; an external pull-up is usually unnecessary. The example external switch circuit lists a 100 nF filtering capacitor and 330 Ω switch-series resistor. This is an example, not evidence that either candidate board has those parts.
- §2.1 pinout (printed page 14) for 28-pin SPDIP/SSOP/SOIC shows UPDI on pin 19 and PF6/RESET on pin 18. Other package pinouts have different physical pin numbers; the assembled package has not been verified here.
- §4.4.1 / Figure 4-3 (printed page 22) shows the UPDI v1, 100-mil 2×3 / six-pin connector: pin 1 UPDI, pin 2 VDD, pin 6 GND; remaining contacts NC.
- §4.4.2 / Figure 4-4 (printed page 23) shows the UPDI v2, 100-mil 1×4 / four-pin connector: pin 1 RESET, pin 2 VDD, pin 3 GND, pin 4 UPDI. The data sheet recommends this connector so RESET is available. It warns that high-voltage activation on RESET can damage other connected components and that PDID-equipped parts cannot be re-enabled via RESET after PDID activation.
- Data sheet §35.1–§35.3 and Microchip online §3.3.5.3 describe UPDI as a single-wire, bidirectional half-duplex asynchronous interface. The DA pinout separates UPDI from PF6/RESET. The online overview calls AVR DA/DB a dedicated-UPDI configuration; the device data sheet also documents RESET high-voltage override for some disabled-UPDI states. Because target suffix/fuse state and actual wiring are unknown, no RESET/HV activation experiment is proposed or inferred.

### Voltage, slew, clock, and signal limits

- Data sheet §37.3 Table 37-3 (printed page 582) gives operating VDD as 1.8–5.5 V over the specified industrial/extended temperature ranges. The feature list gives CPU operation up to 24 MHz. Current Rev. E §37.3 does not state a VDD-dependent frequency derating table; §10.3.3 points to maximum frequency versus VDD, so a guaranteed voltage/frequency envelope is not derived here from that reference or from non-guaranteed graphs.
- §37.4 Table 37-4 (printed page 583) gives a maximum supply slew rate of 0.25 V/µs for 1.8 V ≤ VDD ≤ 5.5 V. The same table gives SVDD minimum 0.05 V/ms to ensure internal POR when BOD is disabled. These are different limits and must not be conflated.
- §37.21 Table 37-28 (printed page 598) characterizes UPDI baud rates up to 1.8 Mbps for 0–50°C and 0.9 Mbps outside that range; the table explicitly says those parameters are characterized, not production tested. It also lists the handshake/BREAK and UPDI-low duration ranges. The present 38,400-baud host campaign is below those baud maxima, but this fact does not establish target-side waveform levels or timing margins.
- §37.2 Table 37-1 gives absolute maximum voltage on pins other than VDD/RESET as −0.3 V to VDD+0.3 V with respect to GND; the RESET absolute maximum is the same upper/lower relation. These are stress limits, not recommended operating levels.
- §37.7 Table 37-7 gives general I/O Schmitt-buffer thresholds of VIL ≤ 0.2×VDD and VIH ≥ 0.8×VDD, and the same fractions for RESET. The table does not provide a separately named UPDI VIH/VIL specification. Do not claim that these general I/O thresholds are the guaranteed UPDI threshold without Microchip confirmation.
- Thus “3.3 V versus 5 V” is only a seeded hypothesis. Actual target VDD, adapter TX level, bus high/low levels, ground offset, and waveform validity must be measured on the actual connection; none is known from the documents or current software records.

## Errata relevance and interpretation limit

Errata DS80000882F §2.9.1 (printed page 6) says that with UPDI enabled, BOD.VLMCTRL, BOD.INTCTRL, and BOD.INTFLAGS are not reset by reset sources other than POR; it applies to listed revisions A6, A7, A8, and AB. This supports treating BOD monitor/control state cautiously across non-POR resets. It does not state that BORF proves or disproves a fresh reset; use an independently observed boot/reset marker for that conclusion.

Errata §2.2.2 (printed page 3) reports Flash endurance of 1K rather than 10K cycles for A6/A7/A8/AB. Target silicon revisions are not known for either current board. This is a write-budget constraint, not evidence for an electrical UPDI cause.

## Local board artifact audit

Graphify query: “AVR128DA28 board schematic BOM UPDI net regulator RESET connector decoupling” returned investigation plans, reports, and software but no board schematic/netlist/BOM node. CodeGraph query for local AVR128DA28 schematic/BOM/PCB/netlist/UPDI/regulator/RESET found software-source relationships only. A scoped file inventory for KiCad schematic/PCB, legacy schematic/board, netlist, BOM and hardware PDFs found no board design artifact; it found the Microchip reference PDFs and RCA evidence/report CSVs only.

Therefore actual board package, connector pinout, rail source and value, ground path, UPDI trace, pull/series resistor, ESD device, other attached load, decoupler population/value/location, and assembly condition are all **UNKNOWN / UNVERIFIED**. The Microchip figures are reference circuits, not a substitute for the missing board topology.

## Raw-source hashes

SHA-256 values for fetched PDFs and their local plain-text extracts:

- DS40002183E PDF: 0001076aa7fb795acef725a38e500e37efe01782b6328f02b54ac0dbb5482b3b
- DS40002183E pdftotext extract: fc64a7fd158361733c7d74e6cbac11d8395a1b14d5840a4ad8c3a9817f0f8bb8
- DS80000882F PDF: cae3820ed15d73ca0d5dec20e9de45a8d7b25e04c4bb9685df43072f1f782ee2
- DS80000882F pdftotext extract: a3014ca62b07f4705f38168091eda89e12aca851c6c60d4f8f809ca5a42cf67c
- Official UPDI-interface HTML: cb5635595bd975bc2fa0416cd6cad98ef041bedc6e3bd89dc707feded3c8d611

The PDF byte hashes are for the downloaded files in this directory. The accompanying text files were made with pdftotext -layout for reproducible targeted extraction.
