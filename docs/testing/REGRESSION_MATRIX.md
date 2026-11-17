# Regression Matrix

Current checkout: `f0ca01554c156b2034ac29c304571ec7dcb02acb`; working-tree verification 2026-11-17 Asia/Bangkok. Feature ownership, host behavior, and all role-bearing builds are verified; physical RF acceptance is pending installation of the current images.

## Firmware builds

All 19 role-bearing environments pass `pio run` after the final comment pass and SD line-reader bounds fix, with zero compiler warnings. `debug` and `release` are configuration bases without a radio role, not firmware targets.

Largest reported image: 39,012 bytes Flash (`receiver_arq_radio_only`). Largest reported static RAM: 7,049 bytes (`sender`). The current `sender_hello` image is 36,368 bytes Flash / 3,939 bytes static RAM; `receiver` is 35,612 bytes / 3,772 bytes. No physical programming has occurred; BOOT, fuses, EEPROM, USERROW, and protected Flash remain untouched.

## Host tests

| Command | Result |
|---|---|
| `.venv/bin/python -m unittest tests.test_reliable_transport tests.test_mvp_roundtrip tests.test_stable_lora_safety tests.test_lora_ssot tests.test_sender_one_shot -q` | PASS, 30 tests |
| `.venv/bin/python -m unittest tests.test_radio_915_ssot tests.test_raw_mvp -q` | PASS, 14 tests |
| `.venv/bin/python -m unittest discover -s tests -q` | PASS, 429 tests, 1 skipped |

The one skip is the boot-package case for the archived BOOTSIZE=44 repair, which does not apply to the current replacement Receiver. The legacy backup fixture was restored byte-for-byte from local Git history after its 128 KiB size and SHA-256 matched `tools/receiver_boot.py`; it remains ignored under `artifacts/` and was not programmed.

The SD `read_line` boundary regression runs with ASan/UBSan: 127-byte lines are retained, longer lines are capped at 127 bytes, and the remainder is consumed through the delimiter so the next call starts at the next line.

The reference behavior test now checks the actual tracked four-argument `configure(addr, freq, tx_power, long_range)` API. The untracked `gateway-lora_dev` tree contains only its generated profile, so only the profile equality is checked there.

`clang-format --dry-run --Werror` passes for 135 active first-party C++ files; imported mcurses/printf/protothread files retain their existing style. Ruff reports diagnostics in dirty Python files, but none fall on changed lines.

## Session and duplicate behavior

Host tests verify that DATA and ACK/NACK use the same nonzero campaign value in
the existing four-byte header, stale-session ACKs cannot complete a transaction,
wrong-session DATA is discarded before delivery or response, and re-arming the
same receiver object replays ACK without reapplying accepted DATA. Campaign IDs
are 16-bit runtime correlation values and may collide across MCU resets. The
legacy LoRa overload still sends zero; a reliable sender using a nonzero ID
requires a receiver that echoes it. These compatibility and reset cases still
need physical validation.

## Link and source ownership

The 19 successful links prove the selected role source set has no duplicate linked definitions. `avr-nm -C` finds one `LoRa::send` and one `LoRa::recv` definition in each checked default Sender/Receiver ELF. Host behavior tests compile the moved radio and transport owners directly.

## C++ comments

The comment audit covered 145 active C++ sources/headers under `src/`, `stable_lib/`, `include/`, and `tests/`; every file has a purpose comment, and public interfaces describe ownership, units, failure behavior, or concurrency constraints where applicable. Comments explain protocol and hardware rationale rather than restating assignments. Generated board/layout headers and archived source snapshots were not annotated; `application_config.h` was restored from its generator. Upstream license notices are preserved.

## Physical hardware

The two USB adapters and AVR128DA28 SIB identities are now verified. The running Gateway identifies as an older `sender_hello` image, while the Tracker has no recognized firmware identity; neither is accepted as the current pair. The exact current image hashes and application-only page ranges are recorded in `REAL_RADIO_EVIDENCE.md`. No over-the-air packets have been sent in this iteration.
