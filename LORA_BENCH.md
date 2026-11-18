# 915 MHz LoRa bench procedure

**Application Flash PASS. Physical DATA/ACK FAIL. Remaining RF acceptance
BLOCKED.** Both approved images were programmed and verified on 2026-11-18.
The setup owner confirmed the equipment and antenna arrangement for the
bounded 915 MHz test. The bench run measured no independent EIRP or emissions.
The Tracker's UPDI capture failed in each of three single-packet attempts.

## Verified candidates

Read-only UPDI identified both AVR128DA28 devices (signature `1e970a`).
Both fuse snapshots matched the inventory, including BOOTSIZE, CODESIZE and
BODCFG of `00`. The Flash readbacks before programming differed from each candidate.
The existing writer's static checks accepted both candidate spans inside
the configured application range `[0x00000, 0x1FC00)`. All ranges below use
inclusive starts and exclusive ends.

| Role | AVR serial | HEX image and SHA-256 | Occupied Flash | Exact 512-byte application pages |
|---|---|---|---|---|
| Tracker | `42032240221092150158013400000000` | `.pio/build/receiver/firmware.hex` · `d210cdb4abba7d53891145ccdda7027d44739a6675be62123ac394e4eda55616` | `[0x00000, 0x08C44)` | `[0x00000, 0x08E00)` |
| Gateway | `42032240221023150129012600000000` | `.pio/build/sender_hello/firmware.hex` · `d4cca086db18afaa27f8a73b90eb6742cb4ca69a79cafed6d2912164dd2edeaa` | `[0x00000, 0x08FE0)` | `[0x00000, 0x09000)` |

The Tracker's stable USB path ends in `usb-0:1:1.0-port0` and resolved to
`/dev/ttyUSB1`. The Gateway's path ends in `usb-0:4:1.0-port0` and resolved
to `/dev/ttyUSB0`.
[UPDI observations](artifacts/hello-ack-nack-quality-followup/updi-observed.log) ·
[Candidate hashes and layout](artifacts/hello-ack-nack-quality-followup/candidate-images.json) ·
[ELF sections](artifacts/hello-ack-nack-quality-followup/elf-sections.log)

## App-only programming after exact write approval

Recheck the candidate hashes and live device mapping before programming.
The existing writer checks the exact target, image, and 512-byte span.
It programs the Tracker first with AVRDUDE 8.1, disables automatic erase
with `-D`, and erases only the approved application pages. Before and after
snapshots compare Flash outside those pages and compare fuses, EEPROM,
USERROW, lock, signature, and serial. The writer verifies the complete
application page contents and produces a fresh `physical-upload.json`
receipt when both images match.

```sh
.venv/bin/python tools/rf_proof.py --stage upload \
  --physical-mapping-verified --power-verified --authorize-upload \
  --target-serial 42032240221092150158013400000000 \
  --image-sha256 d210cdb4abba7d53891145ccdda7027d44739a6675be62123ac394e4eda55616 \
  --page-start 0x00000 --page-end 0x08e00 \
  --gateway-target-serial 42032240221023150129012600000000 \
  --gateway-image-sha256 d4cca086db18afaa27f8a73b90eb6742cb4ca69a79cafed6d2912164dd2edeaa \
  --gateway-page-start 0x00000 --gateway-page-end 0x09000
```

## RF conditions and acceptance

The verified build configuration is 915.000 MHz, SF7, 125 kHz, CR4/5,
8-symbol preamble, explicit header, packet CRC, normal IQ, sync word
`0x12`, and configured power +2 dBm. The configured power is the software
output setting. Actual EIRP depends on measured output, antenna gain,
and path loss. The configuration validator and host radio tests check
the profile. Live SPI register and PHY readback are pending.

For a U.S. bench, §15.247 sets a 500 kHz minimum 6 dB bandwidth for digital
modulation and separate requirements for hopping. The configured LoRa
signal is fixed-frequency at nominal 125 kHz. §15.249 specifies a 50 mV/m
fundamental field-strength limit at 3 m for 902–928 MHz and separate
harmonic and out-of-band limits. Confirm the equipment grant and antenna
conditions or the applicable conducted or shielded test basis before
choosing site-specific limits. Canada's RSS-247 and RSS-210 also distinguish
the digital-modulation and field-strength routes. Record the actual site,
radio model and compliance identifier or lab basis, both antenna models and
gains or the cable attenuation, and the applicable limit and measurement
window before transmission.
[47 CFR §15.247](https://www.ecfr.gov/current/title-47/section-15.247) ·
[§15.249](https://www.ecfr.gov/current/title-47/section-15.249) ·
[§15.203](https://www.ecfr.gov/current/title-47/section-15.203) ·
[ISED RSS-247](https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss/rss-247-digital-transmission-systems-dtss-frequency-hopping-systems-fhss-and-licence-exempt-local) ·
[ISED RSS-210](https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss/rss-210-licence-exempt-radio-apparatus-category-i-equipment)

Estimated airtime is 51.456 ms per 17-byte DATA packet and 36.096 ms per
6-byte ACK/NACK. Four attempts yield up to 205.824 ms and 144.384 ms per
exchange at Gateway and Tracker respectively. Ten positive trials, ten
one-shot wrong-destination trials, and two retry controls sum to at most
2.985 s Gateway and 1.733 s Tracker cumulative transmit time. Compare
airtime within the actual authorized test window once that window is known.

After authorized installation and RF approval, use the fresh upload receipt
and verify live SPI/PHY agreement and Tracker `RX_READY` before any DATA.
Run the existing `--stage rf-test --stable-transport --mvp-acceptance`
with `--upload-evidence`, `--physical-mapping-verified`, `--power-verified`,
`--rf-hardware-verified`, and `--authorize-rf-test`. Run two separate
stable-transport controls using `--transport-test T02` for a NACK and
`--transport-test T01 --drop-response-once` for timeout and retry. Keep
the per-board serial journals and trial JSON under `artifacts/rf-proof/`.
Require exactly 11 bytes of `hello world`, ACK type `0x03` and sequence 1
accepted by the Gateway on all positive trials. For wrong-destination
trials require zero delivery, ACK, and NACK. Record Gateway `rtt_ms`
from DATA start to ACK acceptance, retries and timeout counts, and
any available measured radio metrics. Confirm both park events.

## Refactor verification

All five PlatformIO environments built with zero compiler warnings.
Gateway uses 36,832 B Flash and 4,009 B static SRAM. Tracker uses 35,908 B
Flash and 3,842 B static SRAM. The host suite passed 429 tests with one
skip. Clang-Tidy passed all nine host compilation variants, Lizard found
zero functions above CCN 15 across the scoped paths, and Doxygen generated
XML with strict documentation diagnostics enabled and zero documentation
findings. The existing app test intentionally includes its implementation
to inspect internal state and carries a line-level Clang-Tidy exception
for that include. The hardware results for these images follow.
[Build log](artifacts/hello-ack-nack-quality-followup/firmware-build.log) ·
[Host suite](artifacts/hello-ack-nack-quality-followup/host-after.log) ·
[Quality logs and compile database](artifacts/hello-ack-nack-quality-followup/final-quality)

## Hardware results

The guarded writer backed up both targets, flashed Tracker first, and
compared each complete written page against the approved image. Both
snapshots matched for fuses, EEPROM, USERROW, lock bytes, device serial
and signature, and all Flash outside the programmed application pages.
[Upload receipt](artifacts/rf-proof/20261118T095311Z/physical-upload.json).

Both firmwares logged radio initialization, SPI version `0x12`, and
matching 915 MHz profile fields. The Tracker reported `RX_READY` before
each `S` command. The Gateway logged a DATA request with sequence 1 and
`DATA_TX_DONE` after 55 ms on each run. The Tracker UPDI link returned a
corrupt echo on the first run and a one-byte response timeout on the other
two. The third used a 19,200 baud Tracker monitor. None of the captures
contains a validated Tracker payload, an ACK, or an ACK acceptance.

| Attempt | Result | Raw evidence |
| --- | --- | --- |
| Acceptance, stopped at first exchange | Tracker UPDI echo mismatch | [Events](artifacts/rf-proof/20261118T095622Z/data-ack-01/rf-test-events.json) · [Tracker error](artifacts/rf-proof/20261118T095622Z/data-ack-01/rf-monitor-receiver.stderr.log) |
| Acceptance retry, stopped at first exchange | Tracker UPDI response timeout | [Events](artifacts/rf-proof/20261118T095750Z/data-ack-01/rf-test-events.json) · [Tracker error](artifacts/rf-proof/20261118T095750Z/data-ack-01/rf-monitor-receiver.stderr.log) |
| Single trial, slower Tracker monitor | Tracker UPDI response timeout | [Events](artifacts/rf-proof/20261118T100014Z/rf-test-events.json) · [Tracker error](artifacts/rf-proof/20261118T100014Z/rf-monitor-receiver.stderr.log) |

The Gateway logged `PARKED E=0` at the end of the last trial. The Tracker
logged the same after its monitor was reopened. ACK latency and retry
counts remain unmeasured. The NACK, wrong-destination, duplicate, and
timeout/retry controls were held until the positive exchange can be captured
reliably. The observed boundary is the Tracker UPDI capture during the
exchange. Its electrical or firmware cause remains unresolved.
[Tracker park capture](artifacts/rf-proof/20261118T100201Z/rf-monitor-receiver.stdout.log).
