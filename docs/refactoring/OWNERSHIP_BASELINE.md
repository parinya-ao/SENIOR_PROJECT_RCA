# Source ownership baseline

The starting checkout was clean at `3f9f3f0` before the Graphify query updated its query stamp. This was an offline baseline.

| Check | Observed result |
| --- | --- |
| Fresh PlatformIO matrix | 19/19 role-bearing targets, zero compiler warnings |
| Host suite | 432 total, 431 passed, zero failed, one historical package skip |
| C++ quality gate | Exit 0, with existing unsupported LLVM cases for native AVR, TimeUtils, and parts of Gateway |
| ELF and HEX | Each image had one physical entry point, the intended ARQ state where applicable, and matching Flash coverage inside `[0x0000, 0x1FC00)` |
| Standalone BOOT fixture | 48 bytes at `[0x0000, 0x0030)`, matching vector enters `0x5800` and blank plus all four single-byte mutations park |
| Physical and installer checks | Out of scope for this run |

The historical package skip reflects the mismatch between archived and active Receiver geometry. The host HAL characterization emitted an existing missing-return warning in `tests/radiolib_hal_test.cpp`. The firmware matrix emitted zero warnings. CodeGraph reported no usable local index. Graphify resolved the principal ownership paths, which were verified against sources, resolved build filters, and linker output.

Before the migration, physical entry points were already separate. ARQ direction and foreground radio policy still occupied one conditional source, and reliable lifecycle and diagnostic command handling were split between common application code and board hooks. The archived handoff lived in top-level `boot/`.

| Target | Flash bytes | Static SRAM bytes |
| --- | ---: | ---: |
| `sender` | 38,792 | 7,079 |
| `sender_hello` | 36,832 | 4,009 |
| `receiver` | 35,868 | 3,849 |
| `sender_arq` | 37,014 | 5,200 |
| `receiver_arq` | 35,804 | 5,044 |

The complete per-target baseline, ELF symbols, section tables, reset disassembly, fixture map, and logs are in `/tmp/lora-ownership-v2/`. The pre-move BOOT symbol `_start` is `0x0000`. Its binary SHA-256 is `b0a680ac4a15c18f627ff2940da88754e6321c2a89d49cac1687c9e7dcd9d4c5`. The trace reports CPUINT cleared and interrupts disabled on all six paths. Blank Flash parks at `0x2C`, and single-byte changes park at `0x2C` or `0x2E`.

The baseline used resolved `pio project config --json-output`, a fresh `pio run` build directory, `.venv/bin/python -m unittest discover -s tests`, `scripts/quality/check_cpp.sh`, and `.venv/bin/python tools/receiver_boot.py /tmp/lora-ownership-v2/before-boot`. The host suite and quality gate used a command-local Git excludes override for the workstation’s global ignore. No source changes preceded these runs.
