# TDD and diagnostic-tool changes

The initial H01 diagnostic slices changed only Host-side tooling. A later source audit found and corrected one SX127x register configuration defect in the unflashed firmware candidate; that correction is recorded separately below. No protocol, fuse, EEPROM, or RadioLib library source changed.

| Slice | RED observation | GREEN behavior |
|---|---|---|
| H01 evidence summary | Four assertions failed because `reader_free_h01_summary` did not exist. | Summarizes DATA/RX/ACK/terminal observations and keeps absent events `None`/UNKNOWN. |
| Firmware provenance | Test failed because the reader-free build metadata helper was missing. | Binds the copied HEX SHA-256 to the embedded build ID. |
| Reader-free session | Test failed because there was no startup-only UPDI session helper. | Opens the existing Upditerm SerialUPDI session without issuing an application mailbox command. |
| Post-error reset read | Test failed because the one-session no-CPU-reset resync helper was missing. | Closes the failed transport, opens one fresh UPDI/OCD session, and reads GPIOR0/RSTFR/UART_FLAGS without a CPU reset. |
| Partial event drain | Deterministic fake transport returned only `b'A t=1 e='` after a quiet gap instead of the complete STATUS line. | The drain waits for newline or its hard timeout before returning a partial line. |
| RX-idle control | Tests failed because the POR summary and no-RF CLI route did not exist. | Adds a bounded 120-second Tracker RX-only control mode; tests verify missing reset data remains UNKNOWN and no RF authorization is required. |
| 915 MHz HF-mode selection | Added a radio-register assertion before the fix; `test_adapter` failed because RX mode was `0x8D`, with bit 3 set. | Firmware clears `RegOpMode` bit 3 after successful RadioLib initialization; test now observes `0x85` in RX Continuous for both adapter roles. |

Historical focused run: `uv run python -m unittest tests.test_arq_reader_free tests.test_arq_capture` — **29 passed, 0 failed**. Raw output is in [focused-diagnostics.txt](tests/focused-diagnostics.txt).

Source-fix focused run: `uv run python -m unittest tests.test_arq tests.test_arq_reader_free tests.test_arq_capture tests.test_gate1_rca` — **82 passed, 0 failed**. The `test_adapter` test was observed failing before the fix and passing after it. Four relevant PlatformIO environments also built; image hashes are in [candidate_builds.json](candidate_builds.json). No candidate image was flashed.

## Test-harness dispatch mistake

One initial test patched the wrong callable and invoked the authorized no-RF RX-idle hardware control instead of a mock. That run transmitted no RF, completed the 120.029947-second control, and restored normal standby. The test now patches `reader_free_h01` directly; the final focused suite passes offline. The hardware record remains separately identified in [03_RX_IDLE_CONTROL.md](03_RX_IDLE_CONTROL.md).
