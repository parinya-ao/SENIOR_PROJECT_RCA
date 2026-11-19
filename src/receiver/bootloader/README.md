# Receiver BOOT boundary

The handoff directory contains a standalone offline fixture. It verifies reset
vector validation, a jump to its fixture application address, and parking for
blank or altered vectors. PlatformIO APPCODE filters explicitly exclude this
directory.

This fixture is not a FOTA installer. There is no active image staging,
validation, Flash commit, rollback, or recovery implementation here. The
project's current Receiver geometry reports BOOTSIZE=0 and image start 0 while
the approved BOOT/APPCODE pairing remains blocked. Do not use the fixture
address as an approved memory layout.

Microchip AN3341 describes the AVR DA BOOT, APPCODE, and APPDATA sections and
self-programming constraints. The AVR128DA silicon errata documents that
multi-page erase can cross a protected-section boundary. Installer work needs
its own approved memory map and silicon review.

The offline fixture is run by python tools/receiver_boot.py OUTPUT_DIR. It does
not program hardware. BOOT fuses, Flash, physical handoff, FOTA transfer, and
power-failure recovery were not tested in this session.

References: [Microchip AN3341](https://onlinedocs.microchip.com/oxy/GUID-CBA6F7C8-69DB-44BF-ACE3-6949CC30E98A-en-US-5/GUID-1FBA83BB-35A7-4B9D-A92E-8A9C7CB8DED6.html),
[AVR128DA silicon errata DS80000882F](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/Errata/AVR128DA-28-32-48-64-SilConErrataClarif-DS80000882.pdf).
