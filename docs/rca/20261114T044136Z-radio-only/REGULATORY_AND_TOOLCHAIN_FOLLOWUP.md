# RF Configuration and Toolchain Follow-up

## Thai RF test profile

The current ARQ diagnostic profile is configured at **923 MHz, +2 dBm**, with BW125/SF7 and the existing frame settings. The ARQ and reverse-raw firmware use the same generated ARQ profile. The separate general profile `config/radio_915.toml` remains unchanged.

NBTC's current online SDoC summary lists LoRa Non-RFID operation at 920–925 MHz and a 50 mW power category. The 2025 NBTC listing identifies the associated technical standard. This establishes a candidate band, not conformity or authorization for this assembled Tracker/Gateway. [NBTC SDoC listing](https://standard.nbtc.go.th/%E0%B8%9A%E0%B8%A3%E0%B8%B4%E0%B8%81%E0%B8%B2%E0%B8%A3%E0%B8%AD%E0%B8%AD%E0%B8%99%E0%B9%84%E0%B8%A5%E0%B8%99%E0%B9%8C/SDoC-Online.aspx), [NBTC 2025 technical-standard notice](https://www.nbtc.go.th/law/announce/688543/688545/701196/688752/), [NBTC general-use rules](https://nbtc.go.th/th/law/announce/688543/688545/701196/688866/).

At nominal +2 dBm conducted output, 50 mW EIRP (16.99 dBm) leaves at most about 14.99 dB for net antenna/feed gain before output tolerance. This is a calculation only; the installed antenna model/gain, actual output tolerance, EIRP, equipment conformity and applicable lab conditions were not verified. Accordingly, the profile is **software-configured but not authorized/cleared for physical transmission**. The configured 125 kHz bandwidth is centered well inside 920–925 MHz, but spurious emissions and system conformity were not measured.

## Host compiler and test stage

The repository-provided GCC 16.2.1 was used through the existing toolchain path; no system package or persistent wrapper was installed. The RF-proof host-test stage had stale references to removed Hello protocol sources and omitted the role compile flag from its diagnostic RadioLib build. Both defects were reproduced with failing tests and corrected. The current stage passes role-log, wrapper, diagnostic-protection and unit tests; see [host-tests-final.log](tests/host-tests-final.log).

Result: **302 tests run, 1 skipped, 0 failures, 0 errors**. All **15 active target environments** build, and all image ranges/reset vectors pass the static application-bound checks. See [build results](FIRMWARE_BUILD_RESULTS.json). Eight ARQ/reverse-raw candidates use the 923 MHz profile; none was flashed.

## Remaining physical dependencies

Two USB CP2102 devices are present, but their USB descriptors do not identify their board-level 3.3 V regulator path or target current. The operator reported adapter 3.3 V power; battery/regulator isolation, common ground and back-feed conditions remain unverified. No supply/rail waveform or current measurement exists. The RF authorization/equipment/EIRP evidence and the SD socket state are also unknown.

Consequently, there was no candidate flash, RF transmission, DATA RX, ACK/NACK exchange, reset A/B/A experiment, or physical reliability trial in this continuation.
