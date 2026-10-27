# Post-swap source check

2026-10-27. No analog threshold or component attribution is asserted by this screen.

- Official DS40002183 download re-fetched at 03:33:32.438456Z: 11,211,065 bytes; SHA-256 `0001076aa7fb795acef725a38e500e37efe01782b6328f02b54ac0dbb5482b3b`. Exactly matches the inherited Rev E,09/2024 PDF. Web PDF parser rejected its size; direct manufacturer download succeeded. The inherited device-specific source audit remains applicable.
- Official DS80000882 PDF opened afresh: revision F,2024. Flash endurance/BOD state errata are constraints; they do not establish a cause for BREAK echo loss. No new flash/fuse operation is performed.
- Official Silicon Labs CP2102/9 data sheet opened afresh: Rev1.8,1/2017. Page1 lists300bps–1Mbps, even parity and2stopbits; generic format capability does not diagnose a particular adapter. Silicon variant on these boards remains descriptor-reported CP2102, not chip-marking verified.
- Linux error-code URL fetch was unavailable through the web parser. Use the inherited hashed Linux documentation audit for error semantics. Current journal visibility is limited; no absence-of-USB-errors claim is made.

Primary URLs:

- https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-DS40002183.pdf
- https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/Errata/AVR128DA-28-32-48-64-SilConErrataClarif-DS80000882.pdf
- https://www.silabs.com/documents/public/data-sheets/CP2102-9.pdf
- https://docs.kernel.org/usb/error-codes.html

Actual local probe source remains authoritative for host behavior: strict two300-baud zero-byte exchanges, then SIB at38400; no STCS/STS, programming key, target reset or NVM write. Compare source hashes captured by each worker before using their measurements.
