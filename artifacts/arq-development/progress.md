# ARQ V1 implementation ledger

Source: user-supplied approved plan (2026-11-13).
Archive: /home/parinya/arq-backups/20261113T072630Z (339 files + hashes + dirty diff).
Preflight: existing dirty MVP is required; work remains in this workspace,
no commit/push, no worktree that would omit untracked MVP files.
Interfaces: config -> generated C/settings/manifest -> portable modules ->
RadioLib adapter -> bounded UPDI commands/events -> trial runner/evidence.
Ruling: portable modules expose actions instead of RadioLib callbacks; time,
random RTO, radio completions and receive frames are explicit test seams.
Ruling: do not reuse a failed sequence with changed content in a session;
host uses a fresh session after any failed transaction.

RED: tests/test_arq.py initially missing core/config/runner; retained red.log.
Core GREEN: golden codec, sender outcomes/backoff/wrap, receiver dedup/session,
fault harness; Clang ASan/UBSan passes (GCC sanitizer runtime missing).
Adapter GREEN: both roles, command bounds, RX restoration, fault first-ACK,
logger overflow and nonblocking behavior. Config and page bounds GREEN.
Toolchain ruling: use Clang driver for host tests; system g++ and C++ standard
headers absent. Existing raw tests may need their original toolchain.
Stack ruling: DxCore appends -flto after build flags; build_unflags removes
LTO for ARQ targets only to get actual compiler .su reports.

Review: fresh agent reviewed portable logic/adapter/config/runner. Fixed session
counter carryover, raw-log/journal comparison and manifest-based payload/IDs.
Regression RED/GREEN logs retained. Fixed AVR printf_min padding parsing after
first physical capture failed before ARM. Fixed receiver same-session ARM
idempotence during response guard (RED/GREEN).
Hardware run 20261113T074154Z: test firmware programmed and independently read
back on both boards, then capture rejected s=0 formatting before ARM; normal
firmware restored with independent preservation comparisons.
Hardware run 20261113T074705Z: fresh run underway (session reservations persist).
Full regression: 165 tests, 160 passed, 1 skipped, 4 pre-existing UPDI errors
(two test methods / three bad-ACK subcases). Temporary external Clang/GCC-header
compatibility wrapper used because system C++ driver/headers absent. See
regression-final.log; no project dependency or compiler setup changed.
Stack: full DxCore must retain LTO; separately compiled ARQ objects yield .su
per-function reports. Receiver loop 154 bytes, status 91; not whole-program
worst-case stack usage. Firmware static SRAM is about 5 KiB of 16 KiB.

USER STEERING: RF path not visually verified; no further RF until explicit
physical confirmation. User then requested finishing all software now without
waiting. No more inspection questions needed. Physical objective remains paused.
Turnaround batch was safely stopped after active avrdude read completed; killed
paused orchestrators, no remaining serial owners. 50ms guard failed (session4),
100ms prepared only before ARM/SEND, 200ms not started. Config restored75ms.
Completed standby behavior: boot unarmed/standby, ARM enables RX, X parks after
outstanding work. RX_READY rc and TX_STATE/RX_STATE register dumps include DIO0,
IRQ mask and modem status. Observed Sender TxDone→RX_READY 2–3ms, OpMode8D,
IRQ00, DIO0 mapping00, IRQmask00. No ACK RX; local ACK TxDone is not RF proof.
CLI: --prepare never ARM/SEND; --mvp --rf-path-confirmed runs H01(1), H04(10),
H02(1), H03(1) and restores normal. Full campaign preserved behind RF flag.
Tests: 11 focused pass, sanitized portable C and heap checks on unsanitized
objects; full suite169 =164pass,4existingUPDIerrors,1skip. All six targets build.
Current normal Flash/SRAM Sender35678/5035, Receiver35096/5033; test Receiver
37078/5069. Per-function stack Sender loop111, Receiver154, status91, not a
whole-program worst-case. Review found no important issue in latest changes.
RAW regression physical3TXdone/3matchingRX preserved in
artifacts/arq/20261113T080205Z-raw-regression/raw-rf-monitor-* and raw-result.json.
Receiver restore independent read failed74%, separate read-only full retry
verified preservation. Later Sender prepare UPDI init failed before any write;
separate read-only full preflight passed, then normal install completed.
FINAL DEVICE STATE VERIFIED: both normal images, unarmed session0, OpMode89
standby, ready1, IRQ00, mapping00, mask00, overflow0, Sender IDLE, zero TX.
Proof: artifacts/arq/sender-standby-completion/{standby-verified.json,status.json,
preservation.json}; Receiver full snapshots also in 20261113T082243Z-standby.
Offline compare from first ARQ backups verifies fuses/EEPROM/identity/lock and
Flash beyond union of written pages unchanged (Receiver>=37376, Sender>=35840).
Legacy ssot/raw source and legacy config hashes equal initial archive.
Resume RF only after user's physical confirmation, using exact --mvp command.
