# Investigation Sources

Research checked 2026-10-26. Device-specific PDF revision is preferred over generic AVR-family guidance.

| Source | Revision / location | Use |
|---|---|---|
| [AVR128DA28/32/48/64(S) Complete Data Sheet](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-DS40002183.pdf) | DS40002183E, 09/2024; especially §§4, 7, 8, 11, 13, 18, 35–37 | Device identity (signature/SIGROW serial), memory/register map, UPDI/OCD/ACC, reset semantics, fuses, electrical limits and design recommendations. Confirm the exact paragraph before using any limit in a causal claim. |
| [AVR128DA Silicon Errata and Data Sheet Clarification](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/Errata/AVR128DA-28-32-48-64-SilConErrataClarif-DS80000882.pdf) | DS80000882F, 2024; §2.9.1; §3.1 / §3.6 | UPDI-enabled BOD `VLMCTRL`/`INTCTRL`/`INTFLAGS` reset erratum; clarified Flash endurance of 1,000 cycles. Applies to revision A7, but does not by itself explain missing LDS data. |
| [Microchip online documentation: SIGROW](https://onlinedocs.microchip.com/oxy/GUID-3EE676DF-490E-41BC-98F0-5774B35DC989-en-US-25/GUID-FC75867C-DACB-4865-AA4F-E976C31DFAB3.html) | AVR128DA family, §7.7 | Confirms device signature bytes and that signature row includes the unique 16-byte serial number. Use the device PDF for final identity interpretation. |
| `external/upditerm/upditerm.py` and `external/upditerm/updi_uart.c` | Current checked-out source; hash/commit captured during freeze | Actual project protocol behavior: serial framing, BREAK setup, virtual UART `FLAG_RX`, `OCDMV`, `OCD_STOPPED`, `ASI_OCD_MESSAGE`, and target message generation. Local source is the primary implementation reference. |
| [Linux kernel usbmon documentation](https://www.kernel.org/doc/html/latest/usb/usbmon.html) | Current docs checked 2026-10-26 | USB traces describe HCD requests and are not themselves a direct analog signal measurement. Collect only when correlated host/USB symptoms justify escalation. |
| [D2 0.9.0 release notes](https://d2lang.com/releases/0.9.0/) and [TALA announcement](https://d2lang.com/blog/tala-is-open-source/) | v0.9.0; announcement 2026-09-07 | TALA is bundled/open source; use `--layout=tala`. Diagram palette is D2 theme 4 (Cool Classics), already specified in project work state. |

## Evidence boundary

Prior software measurements report correct local echo with 19/60 unheld LDS responses missing while SIB/ASI control remains reliable. A BORF value remained asserted while a GPR1 marker survived repeated reads, so those samples are not independent reset counts. No physical instruments are available. Software can classify the serial/UPDI/ACC/OCD/reset boundary, but cannot establish VDD droop, ground offset, RESET edges, UPDI line levels, or which component causes them.
