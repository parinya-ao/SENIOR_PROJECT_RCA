# AVR128DA28 Dual-Board UPDI Root-Cause Analysis

Date: 2026-10-27  
Scope: isolated investigation under `experiments/updi_rca/`; no production UPDI or FOTA/application code changed.

## Situation

The historical report recorded 19 missing unheld LDS ACC data responses in 60 attempts (31.67%; Wilson 95% failure interval 21.31%–44.23%) after exact local echo. Its SIB/ASI control transactions remained reliable. In the fresh 38400-baud read-only baseline, Lane A passed SIB 100/100 and control 100/100; Lane B passed SIB 0/100 and control 0/100. Lane B failed before a target response, at local echo. These are distinct failure stages.

## Task

Reduce all 168 supplied hypotheses to the narrowest layer supported by reproducible evidence, while preserving firmware and fuse state and separating serial/USB, host TX, local echo, UPDI response, ACC ACK/data, OCD, and runtime/reset behavior.

## Action

- Read `PROMPT.md`, preserved historical evidence, the existing UPDI implementation, and primary Microchip/Linux/upstream references recorded in `memory/SOURCES.md`.
- Used exactly two lane workers, one per stable adapter `ID_PATH`. The CP2102 devices share USB serial `0001`; tty names are recorded only as ephemeral locators. Target signature, REVID, and unique serial remain unavailable, so both targets are `UNKNOWN_TARGET`.
- Wrote and observed a failing test before implementing strict raw-event classification and canonical run selection. The baseline probe used two 300-baud BREAK sync bytes followed by SIB or LDCS reads at 38400; no STCS, STS, key, reset, NVM, fuse, or flash writes.
- Captured 100 attempts for each of SIB and selected control reads on each lane. Raw attempt files map to run IDs and stable lane identity. SHA verification: 400 per-attempt entries, 400 verified, 0 failed.
- Final ledgers contain 509 run rows and 6387 event rows; event IDs are unique and map to run IDs. All 509 run sources were hash-checked; 0 mismatches or missing hashes were found.
- The SILENT/HEARTBEAT diagnostic target was built once (SHA-256 `729162b13f65bdcd464a20f8305857dde3d1f91b90e9084ff003a251268ba055`) and not flashed because target identity, current firmware/fuse snapshots, and safe readback gates were unavailable. No fuse write, chip erase, `-F`, BOD change, or new flash write occurred.
- Scored the 168 hypotheses with the explicit additive weights in `PROMPT.md` §12. Scores rank discriminating tests; they are not probabilities. Statuses: PROVEN=0, STRONGLY_SUPPORTED=0, SUPPORTED=8, UNRESOLVED=48, DISFAVORED=0, FALSIFIED=0, BLOCKED=112.

## Result

### Fresh read-only baseline (100 attempts per lane and condition)

| Condition | Lane | Pass/fail | Rate and Wilson 95% success interval | Median / p95 latency |
|---|---|---:|---|---:|
| SIB | A | 100/0 | 100.0%; [96.30%, 100.00%] | 157.092 / 159.884 ms |
| SIB | B | 0/100 | 0.0%; [0.00%, 3.70%] | 1060.951 / 1064.443 ms |
| Control | A | 100/0 | 100.0%; [96.30%, 100.00%] | 201.537 / 204.744 ms |
| Control | B | 0/100 | 0.0%; [0.00%, 3.70%] | 1061.433 / 1064.452 ms |

Lane A generated 300/300 exact echo frames and 100/100 SIB responses (3,200/3,200 SIB bytes); control reads generated 1,500/1,500 exact echo frames and 1,300/1,300 response bytes. Its control snapshots observed `ASI_OCD_STATUS=0x10` and `ASI_SYS_STATUS=0x82` in all 100 attempts. The masked OCD state was `OCDMV=1`, `OCD_STOPPED=0`; no `ASI_OCD_MESSAGE` bytes were consumed.

### FLAG_RX read-only follow-up

The separate Lane A campaign made 100 sequential direct LDS reads of GPR2 at `0x001e`, with 100 pass, 0 fail, a 100.0% read-success rate (Wilson 95% interval [96.30%, 100.00%]), and median/p95 latency 147.597/150.083 ms. The returned value was `0x03` in 100/100 valid reads; `FLAG_RX` (bit 1) was set in 100/100 reads (100.0%, descriptive Wilson interval [96.30%, 100.00%]) and `FLAG_ENABLE` (bit 0) in 100/100. No virtual-UART payload writes or target writes were made. These sequential reads observe persistent flag state; they do not prove 100 new RX events or identify who set the flag. The interval is descriptive only because samples were sequential, correlated observations of one uncontrolled state. The inspected upstream `updi_uart.c` defines `FLAG_RX` as “RX buffer full” and clears it only after its `updi_uart_rx()` reads GPIOR3; the LDS probe does not clear it. Current target firmware is unknown, so this is an interpretation aid, not proof that either target runs that handler. `FLAG_RX` is distinct from target-to-host OCD message activity. H131 evidence score: 1 (ranking weight, not probability).

Lane B's 100/100 SIB and 100/100 control attempts failed at `LOCAL_ECHO`; no SIB, LDCS, or target response was reached. For the first BREAK echo, 86/100 SIB and 85/100 control attempts were empty; the remaining first echoes were exact, then the second BREAK echo was absent. The observed TX/echo mismatch is a serial/half-duplex/link-stage failure. It is not the historical exact-echo/target-response failure.

Historical state comparison: prior upstream evidence reported running-state response loss in 19/180 attempts (10.56%) and stopped/programming-held success in 540/540 attempts (Wilson 95% success interval 99.29%–100.00%). The fresh 400-attempt baseline did not control RUNNING versus STOPPED and used only SIB/LDCS; therefore it does not reproduce that ACC state comparison.

No matching kernel CP210x/USB protocol errors were found during the approximately 4m01s Lane B window (n=0 correlated errors). Because each adapter remained paired with its target, these data isolate a lane-bound path, not a physical board or adapter. No controlled adapter crossover, current fuse/firmware comparison, STOPPED/programming-held campaign, independent reset marker, or scope trace exists.

### OCD text and reset interpretation

The supplied terminal transcript contained nine visible `HEYYY fuckkkk` lines followed by host process SIGKILL. A later bounded read-only Lane A snapshot (`2026-10-26T17:39:23.404420+00:00`, n=1, 1/1 pass, 0 fail, Wilson 95% success interval [20.65%, 100.00%], latency 284.286 ms, H131 evidence score 1) read `ASI_OCD_STATUS` before each `ASI_OCD_MESSAGE` byte. It captured 15 bytes, `b'HEYYY fuckkkk\r\n'`, hex `4845595959206675636b6b6b6b0d0a`; `OCDMV=1` on all 15 pre-byte status reads and the final status was `0x00`. The captured `HEYYY fuckkkk\r\n` matches the visible line text. All 33/33 request frames had exact local echo (33/33); 16 status and 15 message responses were received, and `OCD_STOPPED` stayed clear. The read consumed a 15-byte volatile OCD message queue; it made no target register write, UART write, NVM write, fuse write, or flash write. The original nine-line session still has no per-line timing or independent target identity. The host's SIGKILL is not evidence of a target reset. Historical BORF without a new boot marker remains historical state, not proof of a fresh brown-out. No SILENT firmware was flashed, so target-to-host OCD traffic in the intentional no-output condition remains untested.

### Narrowest defensible conclusion

There are at least two distinct observed failure classes: (1) fresh Lane B TX-to-echo failure before target protocol response, N=200 attempts across two conditions with 200/200 failures; and (2) historical unheld LDS exact-echo transactions with 19/60 missing ACC data responses. Neither class identifies a component. The fixed lane pairing prevents board-versus-adapter attribution; the specific board-local power, ground, UPDI, reset, AVR, and assembly causes remain BLOCKED. Current test-priority scores are Reset/watchdog 20, Power/GND 19, AVR silicon 19, Firmware/runtime 15 (H098=13, H102=12), board-side UPDI 10, PCB/assembly 6, adapter/host 1, fuse/environment/methodology 0. These are evidence-weighted test priorities, not probabilities; the investigation proves no single root cause.

### Smallest next action

With boards unpowered, perform one labeled adapter crossover while keeping host, baud, firmware, fuses, and wiring conditions fixed; repeat 100 SIB and 100 control attempts per resulting pairing. This distinguishes a lane-following adapter path from a target-following effect without programming. If failure follows a board, capture simultaneously during attachment and RUN: MCU VDD relative to local GND, adapter-to-board ground offset, RESET at the MCU, UPDI on both sides of the series element, and adapter TX, with low-capacitance probes, at least 100 ms pre/post trigger, and at least 20 MS/s. A stable VDD plus adapter TX without target-side UPDI/echo narrows toward the board-side link; VDD droop aligned with an independently observed reset narrows toward power/reset. Do not infer a specific component from either result alone.

## Evidence files

- Inventory: `reports/device_inventory.csv`
- Run/event records: `reports/runs.csv`, `reports/events.csv`
- Hypotheses and ranking: `reports/hypothesis_status.csv`, `reports/root_cause_ranking.csv`
- Pairwise/fuse/flash records: `reports/pairwise_board_comparison.csv`, `reports/fuse_compare.csv`, `reports/flash_budget.csv`
- Raw evidence and checksums: `evidence/raw/`
- Causal map: `diagrams/cause_evidence_map.svg`
- Handoff: `memory/HANDOFF.md`
