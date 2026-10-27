# Continuation State

Epoch: `RCA_CROSSOVER_01`
Updated: 2026-10-27 04:30 Asia/Bangkok

## Verified inherited evidence

- Existing host tests: 45 passed at continuation start; final full suite: 53 passed.
- Immutable prior ledger: 509 run rows and 6,387 event rows.
- All 509 inherited source-log hashes validated in the prior verification.
- All 168 hypothesis IDs remain present; prior statuses: 8 SUPPORTED, 48 UNRESOLVED, 112 BLOCKED.
- Lane A at 38400 baud: SIB 100/100 and control 100/100 pass.
- Lane B at 38400 baud: SIB 0/100 and control 0/100 pass; all 200 failures stop at LOCAL_ECHO.
- Historical running/unheld LDS: 19/60 missing ACC data responses after exact echo. This remains separate from LOCAL_ECHO failures.
- Lane A GPR2: 100/100 reads succeeded and returned `0x03`; persistent FLAG_RX is not 100 new receive events.
- One bounded OCD read captured 15 bytes matching `HEYYY fuckkkk\r\n`; the nine-line terminal session has no per-line timing or stable target identity. SIGKILL describes host-process termination, not a target reset.
- Diagnostic firmware SHA-256 is `729162b13f65bdcd464a20f8305857dde3d1f91b90e9084ff003a251268ba055`; it was not flashed. No new flash or fuse writes.

## New evidence in this epoch

- Host TDD: six focused pairing-snapshot and crossover-classifier tests plus two run/event-stage tests were observed failing before implementation, then passed. The final full suite is 53/53 green.
- The two existing lane agents ran bounded 10-attempt SIB and control pre-crossover checks in parallel, each on its own stable `ID_PATH`; no physical wiring changes occurred.
- Pre-crossover confirmation is complete with 40 raw attempt records and 546 raw protocol events. Per-attempt hashes match on both lanes; Lane A's 28-entry SHA256SUMS manifest passes, and Lane B's command/stdout/empty-stderr hashes match its execution record.
- Lane A, initial P+X: SIB 10/10 and control 10/10 pass; Wilson 95% success interval 72.25%–100% for each condition. Median/p95 latency was 156.332/158.131 ms for SIB and 201.944/203.732 ms for control.
- Lane B, initial Q+Y: SIB 0/10 and control 0/10 pass; every attempt failed at LOCAL_ECHO, before any SIB/LDCS request or target response. Wilson 95% success interval 0%–27.75% for each condition. Median/p95 latency was 1061.647/1064.128 ms for SIB and 1061.556/1063.475 ms for control.
- The reproduced lane difference is still adapter-plus-target confounded. No target serial is available, and there has been no physical reconnection or crossover. The user reported the crossover could not be performed safely; do not request further board manipulation from the user.
- Current stable adapter paths from udev are `pci-0000:00:14.0-usb-0:4:1.0` and `pci-0000:00:14.0-usb-0:1:1.0`; both report VID:PID `10c4:ea60` and duplicate USB serial `0001`.
- At this inventory snapshot, the first path resolves to `/dev/ttyUSB0` and the second to `/dev/ttyUSB1`. These tty names are current aliases only.
- No process held either serial device at the inventory snapshot. The previous `upditerm.py` process is absent; user terminal reported it terminated by SIGKILL.

## Current causal boundary

- Historical evidence isolates a lane difference, but adapter, wiring, target board, and target AVR remain confounded.
- Neither target has a verified unique signature-row serial. Keep both targets `UNKNOWN_TARGET` until a current safe target read or physical label mapping proves otherwise.
- The next experiment is the 2x2 adapter/target crossover. Do not infer a board or adapter cause before the cross-pairing result.

## Current physical labels (pending confirmation)

- Adapter P = stable ID_PATH ending `usb-0:4:1.0` (inherited Lane A path).
- Adapter Q = stable ID_PATH ending `usb-0:1:1.0` (inherited Lane B path).
- Target X = the physical target currently connected to P; unique target identity unknown.
- Target Y = the physical target currently connected to Q; unique target identity unknown.
- Initial pairing is P+X / Q+Y. A later physical crossover must keep USB plugs fixed and swap only target connections while powered off.

## Next smallest discriminator

1. Ten SIB and ten control attempts per stable adapter path are complete; every echo and target-response stage is preserved separately.
2. The user could not safely power off and identify the harness for the requested target-only swap. Crossed probes were not run; all four crossed matrix cells are explicitly `WAITING_PHYSICAL_UNSAFE`.
3. A qualified bench operator must first verify power isolation and connector pin orientation, then perform the no-programming crossover. Re-resolve adapter paths from scratch and run 100 SIB and 100 control attempts per crossed pairing at 38400 baud.
4. If a target or adapter effect is not repeatable, classify the matrix by rates and intervals rather than forcing a binary result.

## Safety

- New flash writes: 0.
- Fuse writes: 0.
- Chip erases: 0.
- BOD changes: 0.
- New raw attempts/events in this epoch: 40 / 546. Versioned structured continuation CSVs are present; the inherited 509/6,387 ledgers remain unchanged.
- Final verification: 53 tests passed; 509/509 inherited and 40/40 continuation raw hashes match; event IDs are unique and mapped; all 168 hypothesis IDs/statuses are present.
- Preserve inherited report files; continuation outputs are versioned/append-only.
