# RCA continuation — 2026-11-14

This run continues [the 2026-11-13 RCA](../20261113T211753Z/FINAL_RCA.md). It keeps the two failures separate:

- **Gate 1 STATUS:** the earlier AVR-DA UPDI mailbox STS-width defect is fixed. The verified non-RF run completed 20/20 STATUS transactions.
- **Radio exchange:** two reader-free H01 sessions each ended with Gateway `TIMEOUT_EXHAUSTED` after five DATA TX completions. In session 9, a fresh UPDI/OCD resync confirmed Tracker POR; session 8 had an incomplete post-window reset read. A matched 120-second Tracker RX-Continuous idle control using the same Tracker image did not POR.

The latest evidence narrows the radio failure to packet-exchange activity, beyond continuous RX alone. It does **not** show whether Tracker received DATA, accepted it, or began ACK TX. No voltage or RF waveform was measured, so the physical trigger remains unknown.

## Key evidence

- [Reader-free H01 session 8 bundle](../../../artifacts/arq/20261114T022413Z-h01-reader-free/bundle.json) and [session 9 bundle](../../../artifacts/arq/20261114T023251Z-h01-reader-free/bundle.json)
- [120-second RX-idle control bundle](../../../artifacts/arq/20261114T025241Z-rx-idle-control/bundle.json)
- [Restored normal standby](../../../artifacts/arq/20261114T025609Z-standby/standby-verified.json)
- [H01 result analysis](02_H01_RESULTS.md)
- [Power-path analysis](04_POWER_AND_RESET.md)
- [Program source finding and TDD correction](09_PROGRAM_SOURCE_FINDINGS.md)
- [Final STAR report](FINAL_RCA.md)

**Verdict: PARTIALLY_ISOLATED.** Tracker POR during a packet-exchange trial is observed; the rail, exact triggering event, and cause of the missed DATA/ACK exchange require physical measurements.
