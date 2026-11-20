# Offline regression matrix

All results below are from the final formatted worktree. They are offline
software evidence and make no claim about physical RF behavior.

## Firmware matrix

Command:

```sh
pio run -e sender -e sender_hello -e receiver -e sender_hello_spi -e sender_hello_5dbm -e receiver_5dbm -e receiver_spi -e sender_mvp -e receiver_mvp -e sender_arq -e receiver_arq -e sender_arq_test -e receiver_arq_test -e sender_arq_radio_only -e receiver_arq_radio_only -e sender_reverse_raw -e sender_arq_radio_only_reverse -e receiver_arq_radio_only_reverse -e receiver_reverse_raw
```

Result: **19/19 PASS, 0 compiler warnings**. Flash and static SRAM values are
bytes; static SRAM does not include runtime stack high-water use.

| Environment | Flash | Static SRAM |
|---|---:|---:|
| `sender` | 38,794 | 7,079 |
| `sender_hello` | 36,760 | 4,009 |
| `receiver` | 35,788 | 3,849 |
| `sender_hello_spi` | 31,480 | 3,482 |
| `sender_hello_5dbm` | 36,762 | 4,009 |
| `receiver_5dbm` | 35,790 | 3,849 |
| `receiver_spi` | 31,528 | 3,478 |
| `sender_mvp` | 31,010 | 1,360 |
| `receiver_mvp` | 31,556 | 1,392 |
| `sender_arq` | 37,028 | 5,202 |
| `receiver_arq` | 35,772 | 5,046 |
| `sender_arq_test` | 37,028 | 5,202 |
| `receiver_arq_test` | 36,832 | 5,074 |
| `sender_arq_radio_only` | 37,068 | 5,214 |
| `receiver_arq_radio_only` | 37,214 | 5,118 |
| `sender_reverse_raw` | 31,838 | 4,646 |
| `sender_arq_radio_only_reverse` | 36,798 | 5,098 |
| `receiver_arq_radio_only_reverse` | 37,480 | 5,232 |
| `receiver_reverse_raw` | 30,952 | 4,443 |

The default `sender` and `receiver` sizes match the first clean build in this
loop. The older approved-plan baseline is recorded in the
[ACK/NACK evidence](LORA_ACK_NACK.md); those differences predate the ARQ-only
change made here.

## Host, quality, and fixture checks

| Command | Result |
|---|---|
| `uv run --no-sync python -m unittest discover -s tests -q` | **434 tests: 433 passed, 0 failed, 1 skipped** in 81.285 s; skip is the historical BOOTSIZE=44 package case, inapplicable to current Receiver geometry |
| `mise run lint:python` | **PASS**; Ruff, Ruff format, MyPy; 72 files |
| `bash scripts/quality/check_cpp.sh` | **PASS**, exit 0; Clang-Tidy 22, Analyzer 65, IWYU 65, clang-doc 22, Lizard, jscpd, Doxygen, formatting, and five selected AVR builds |
| `uv run --no-sync python tools/config/generate_lora_config.py --check` | **PASS** |
| `uv run --no-sync python tools/receiver_boot.py /tmp/lora-v4-evidence/boot-final-2` | **PASS**; standalone 48-byte handoff fixture |
| `graphify update .` | **PASS**; final graph has 3,592 nodes / 6,969 edges |

Native AVR LLVM, TimeUtils LLVM, Gateway integration Clang-Tidy, and Gateway
AVR Clang checks remain `UNSUPPORTED` under the repository's established gate.
The PlatformIO AVR-GCC matrix passes. The handoff fixture accepts reset bytes
`52 C0 00 00` and parks on the blank vector and each altered-byte case.

## Linked image checks

- All 19 final linker maps are present and contain no BOOT source references.
- `sender_arq` extracts the Sender transaction archive member and app object;
  `receiver_arq` extracts the Receiver transaction member and app object.
- No opposite-role app object is loaded in either ARQ image.
- `avr-objdump` found zero SPM instructions across all 19 APPCODE ELFs.
- SSOT, ARQ, MVP, and raw diagnostic wire formats remain separate; existing
  golden-byte, malformed-frame, ACK/NACK, retry, rollover, loss, and duplicate
  tests passed. See the [protocol walkthrough](LORA_ACK_NACK.md).

## Hardware is a separate gate

No physical trial, upload, UPDI probe, or RF transmission ran. Both device roles
were missing in passive discovery. See the
[real-radio evidence ledger](REAL_RADIO_EVIDENCE.md) for the blocked 10/10
criteria and exact evidence still required.
