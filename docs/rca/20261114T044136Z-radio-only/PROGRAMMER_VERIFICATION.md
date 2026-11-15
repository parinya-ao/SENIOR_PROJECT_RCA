# Programmer Verification

## Source and bounds

`tools/rf_proof.py::application_bounds_for_environment()` now maps `sender_arq_radio_only` to Gateway and `receiver_arq_radio_only` to Tracker. The TDD regression first failed with missing (`None`) bounds and then passed with `(0, 130048)` for both roles. Evidence: [RED](tests/programmer-map-red.txt), [GREEN](tests/programmer-map-green.txt), and [test_arq_radio_only.py](../../../tests/test_arq_radio_only.py).

The 923 MHz candidate manifest contains eight ARQ/reverse-raw images, each bound to its Gateway/Tracker role, unique build identity, SHA-256, HEX address range, application bounds, and reset-vector check. All eight pass the static range and reset-vector checks. The aggregate firmware result records all 15 active PlatformIO target environments; all pass the same static checks.

## Identity and non-destructive controls

Previously captured read-only LDS evidence binds both configured USB paths to AVR128DA28 signatures and unique MCU serials. Both boards read BODCFG/CODESIZE/BOOTSIZE `0/0/0`, silicon revision raw `0x17`. No CPU reset, BOOT/Fuse/EEPROM write, or candidate flash was requested in those LDS reads.

The guarded programming path was not entered in this continuation. The latest preflight stopped before serial open because physical supply/back-feed conditions were not established. Thus:

- Correct image files are built and their static application ranges are safe.
- The current programming-layout tool gate has not consumed the separate LDS fuse receipt.
- No programmed-image readback or flash success is claimed.
- No BOOT, Fuse, EEPROM, USERROW, or lock-bit write occurred.

The exact next programming gate is the existing read-only target-identification/BOOT-layout check after safe power, common reference, and back-feed conditions are physically verified. The application-only writer must retain its existing preservation and readback checks.
