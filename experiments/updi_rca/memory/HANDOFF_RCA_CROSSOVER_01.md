# Handoff — `RCA_CROSSOVER_01`

## Current finding

The short read-only confirmation reproduced the original connection-lane difference. Adapter P plus provisional Target X passed SIB/control 10/10 each; Adapter Q plus provisional Target Y passed 0/10 each, with all 20 attempts failing at `LOCAL_ECHO`. Per-condition Wilson 95% success intervals are 72.25%–100.00% for P+X and 0.00%–27.75% for Q+Y. Q+Y median latencies were 1061.647 ms for SIB and 1061.556 ms for control. This does not identify whether the adapter, target, or interconnect is causal.

The inherited ACC evidence remains separate: 19/60 running/unheld LDS attempts missed ACC data after exact echo. No ACC probe was made in this continuation. Persistent `FLAG_RX=1` observations, the captured 15-byte OCD message, the nine historical terminal lines, and host SIGKILL retain the interpretation limits documented in the prior STAR report.

## Work completed

- Re-read the prior report, handoff, run/event and hypothesis CSVs, device inventory, pairwise/fuse/flash reports, source record, and `PROMPT.md`.
- Re-ran the inherited suite (45 passed), added eight test-first cases across pairing snapshots, crossover classification, interaction handling, and run/event conversion; final verification results are recorded in `reports/STAR_RCA_CONTINUATION.md`.
- Reused exactly the two existing lane workers; each had one stable `ID_PATH`, no port contention, 10 SIB plus 10 control attempts, raw evidence and hashes.
- Preserved the prior 509 run and 6,387 event rows. New epoch raw evidence contains 40 attempts and 546 protocol events.
- No wiring change, firmware write, fuse write, BOD change, reset, or chip erase.

## Physical boundary

The user reported they cannot safely perform the requested power-off/harness crossover. Do not ask them to manipulate the current wiring again. The crossed cells are absent, and target signatures/serials remain unknown. This is a safe-stop at the lane boundary, not a completed adapter-vs-target isolation.

## Next step

A qualified bench operator should first verify the normal target power-isolation method and the UPDI/GND/VDD harness pin orientation. Then run the controlled no-programming crossover and 100 SIB/100 control attempts per crossed pairing at 38400 baud. If failure follows a target, capture MCU VDD/local GND, adapter-to-target ground offset, RESET, UPDI on both sides of the series element, and adapter TX simultaneously during attach/RUN; low-capacitance probes, ≥20 MS/s, ≥100 ms pre/post trigger.

## Inherited state and safety

- Prior rows: 509 runs / 6,387 events; continuation adds 40 / 546; combined 549 / 6,933.
- Hypotheses: 168 total — 8 SUPPORTED, 48 UNRESOLVED, 112 BLOCKED; 0 PROVEN or STRONGLY_SUPPORTED.
- New flash writes: 0; fuse writes: 0; chip erases: 0; diagnostic firmware was not flashed.
