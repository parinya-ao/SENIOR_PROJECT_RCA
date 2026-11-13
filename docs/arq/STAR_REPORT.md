# Raw LoRa ARQ V1 — STAR report

## Situation

งานเดิมมี raw Hello World MVP ที่ยังไม่อยู่ใน Git HEAD. ก่อนแก้ไขสำรอง
339 files, firmware images, SHA-256 และ dirty diff ไว้ที่
`/home/parinya/arq-backups/20261113T072630Z/`.
ไม่ commit/push และไม่เปลี่ยน legacy `src/ssot.c` หรือค่าของ raw targets.

## Task

เพิ่ม command-driven ARQ: portable C codec/Sender/Receiver, generated board C,
TOML timing/profile, bounded RadioLib adapter, test-only ACK suppression และ
host evidence runner. ต้องพิสูจน์แต่ละ gate ด้วยฮาร์ดแวร์จริงและเก็บ failures
ตามจริง โดยไม่แก้ fuses, BOOTSIZE, EEPROM หรือ Flash นอก image pages.

## Action

- Added `sender_arq`, `receiver_arq` and `_test` variants. Boards boot unarmed.
- Codec and two state machines use explicit time, randomized transaction RTO,
  radio completions and receive-frame seams. Tests run with Clang ASan/UBSan;
  unsanitized portable objects have no malloc/calloc/realloc/free references.
- Assertion tests cover golden bytes/bounds, matching controls, retry identity,
  exponential backoff, bounded BUSY, clock/sequence wrap, dedup/session isolation,
  dropped DATA/ACK/NACK, delayed/incorrect controls and radio/CRC failures.
- Adapter tests exercise init return codes, malformed lengths, bounded commands,
  duplicate replay, session counter reset, idempotent ARM, full logger and busy
  mailbox. Sixteen event slots never wait for an UPDI reader.
- Review fixes bind parsed events to raw capture streams and exact manifest
  payload/IDs. Final `STATUS_END` includes overflow after diagnostics enqueue;
  validation requires complete current-session status and matching RTT count.
- ACK timer starts after cleanup/RX arming; RTT retains the observed local
  TxDone time. Session changes retain minimum DATA start pacing.
- Reused existing bounded page writer and full signature/serial/Flash/EEPROM/
  fuses/lock snapshots. No programming protocol or fuse repair changes.

## Result

**Physical acceptance is blocked at H01. ไม่ได้รายงานว่า ARQ ผ่านฮาร์ดแวร์.**

| Acquisition | Actual observation |
| --- | --- |
| `20261113T074154Z`, session 1 | Capture stopped before ARM because AVR printf_min emitted `s=0` instead of padded hex; parser fixed with regression test. No ARQ transaction. |
| `20261113T074705Z`, session 2 | Five byte-identical 23-byte DATA transmissions; Receiver accepted once, detected four duplicates, transmitted five 12-byte matching ACKs with TxDone. Sender received zero controls and ended TIMEOUT_EXHAUSTED. |
| `20261113T075357Z`, session 3 | Reproduced the same 5 DATA / 1 application delivery / 4 duplicates / 5 ACK TxDone / 0 Sender RX outcome. Final Receiver counters: gen=5, sup=0, att=5, done=5, crc=0, overflow=0, ready=1. |

Session 3 initial readbacks matched: frequency registers E4C000 (915 MHz),
PA_CONFIG F0, PA_DAC 84, modem configs 72/74/04, sync 12, IQ 27/1D.
Sender final OpMode 8D has continuous-RX mode bits; IRQ=0 and RxNbBytes=0.
Receiver observed DATA RSSI approximately −107 to −108 dBm, SNR 7.75–8.5 dB.
This isolates the missing observation to the reverse RF/receive path; it does
not identify a failed physical component or prove that TxDone radiated RF.
No timer, power or PHY values were changed to mask this failure.

H02–H06 were **not run** because H01 failed. Hundred-message delivery and
first-attempt rates are unavailable. RTT sample count is zero; average/P95
are unavailable. No injected-loss trial occurred and no natural RF loss rate
was inferred. Failed bundles retain their exact images, hashes and streams;
the earlier acquisition revisions lack the final-status marker and are not
accepted as complete bundles by the stricter final validator.

Fresh host verification: **169 tests run: 164 passed, 4 errors, 1 skipped**.
The four errors are pre-existing UPDI tests: `test_ack_and_unrestricted_payload_are_accepted`
(`recv` signature mismatch) and three bad-ACK subcases of
`test_ack_is_compared_and_failed_connection_is_not_reused` (missing `TransportError`).
UPDI repairs were intentionally deferred. All eleven focused ARQ tests passed.
Full suite used a temporary external Clang 23/libstdc++ header setup because
the system C++ driver/headers were absent; repository dependencies were not changed.
All six ARQ/raw firmware targets built. Generator `--check`, graph update and
`git diff --check` passed. Fresh review found no remaining important issue in
the reviewed fixes. RED/GREEN, compiler and regression outputs are retained
in `artifacts/arq-development/`.

| Final target | Flash bytes (text + data) | Static SRAM bytes (data + bss) |
| --- | ---: | ---: |
| sender_arq | 35,678 | 5,035 |
| receiver_arq | 35,096 | 5,033 |
| sender_arq_test | 35,678 | 5,035 |
| receiver_arq_test | 37,078 | 5,069 |

Target limits: 131,072 physical Flash bytes (approved image end 130,048) and
16,384 SRAM bytes. Separate non-LTO compilation of project files reports
111-byte Sender loop, 154-byte Receiver loop and 91-byte status frames.
These are per-function compiler figures, not a measured whole-program peak
or complete nested-call bound. Full firmware keeps DxCore's required LTO.

Raw regression and final idle readback are recorded below after acquisition.
Acquisition firmware hashes remain in each bundle; later host/diagnostic
hardening is not retroactive physical evidence. Baseline hashes confirmed
`src/ssot.c`, `src/mvp/main.cpp`, `config/lora_system.json` and
`config/radio_915.toml` unchanged by this implementation.

## Limits and next physical check

### Safe software completion and final device state

All eleven focused ARQ tests pass; the full suite is 169 tests with 164 passes,
four pre-existing UPDI transport errors and one skip. Normal/test Sender and
Receiver plus both raw targets build. Latest source/config checks and a fresh
review passed. No commits or pushes were made.

Both normal ARQ images are installed with baseline 75 ms guard and independently
verified. Receiver proof: `artifacts/arq/20261113T082243Z-standby/`; Sender and
combined status proof: `artifacts/arq/sender-standby-completion/`.
One Sender UPDI initialization failure occurred before writing; a separate
read-only full preflight succeeded before the authorized installation resumed.

Final actual register readback on **both** boards:

`89E4C000F08472740412271D00000000000010C3`

OpMode=89 (standby), IRQ=00, DIO0 mapping=00, IRQ mask=00. Both ready=1,
STATUS_END overflow=0; Sender RESULT state=0 (IDLE), unarmed session=0.
Only X/STATUS were sent during this final capture; there are zero TX events.
Image hashes, raw UPDI streams and full-memory preservation checks are retained
in `standby-verified.json`, `status.json` and `preservation.json` in the combined
proof directory. EEPROM, fuses, lock and device identity remained unchanged;
Flash beyond all authorized image pages was compared to the first ARQ backup.

After physical antenna/module confirmation, the exact command is:

```sh
python tools/arq_trial.py --mvp --rf-path-confirmed
```

It runs one confirmed DATA→ACK, ten exchanges, NACK and ACK-loss recovery in
that order, stopping at any failed gate. It has **not** been executed since the
RF inspection hold. The 100/200 ms RF trials remain unrun; the 50 ms trial and
earlier 75 ms trials did not receive an ACK. No RF success is claimed.

### Operator stop for physical inspection (2026-11-13)

The operator requires no further transmission until the actual Sender RF path
is inspected. Connector selection, SB1/SB2 solder continuity, antenna
attachment and populated radio model/frequency are **PHYSICAL INSPECTION
REQUIRED**; earlier statements about connected antennas are not verification.
BOMs specify RFM95W on Rudolph LoRa Board 2025-04-26 and Tracker RFM 2025-02-16.
No multimeter, oscilloscope or logic analyzer is available.

Before this stop, the 50 ms guard test (session 4) failed after five DATA
attempts. Sender trace proves TX_DONE -> RX_READY rc=0 in 2–3 local milliseconds;
RX_STATE = `8DE4C000F08472740412271D00000021000004C3` on the first attempt:
OpMode 8D (continuous RX), IrqFlags 00, DioMapping1 00, IRQ mask 00.
Receiver ACK TX_STATE has OpMode 8B (TX), matching frequency/PHY/PA registers
and local TxDone. This does not prove actual ACK reception or RF radiation.
Both final status markers reported overflow=0. No RTT samples were collected.
Evidence: `artifacts/arq/20261113T081019Z-turnaround/guard-50/H01/`.

The 100 ms run was stopped during programming/preflight before any ARM/SEND.
The 200 ms run was not started. The partially prepared 50/100 ms image pair was
not a completed configuration, and its batch was terminated after the active
UPDI read finished. Baseline TOML guard is restored to 75 ms. Software work
continues without RF: both roles now boot unarmed in standby; ARM enables RX,
and X parks after the outstanding exchange finishes. Fresh standby installation
and readback are recorded below. Resume with fresh identity, image/config
checks and a new session after physical confirmation.

Raw-MVP physical regression before these experiments passed with three logged
TxDone events and three matching receptions (RSSI −109/−108/−109 dBm,
SNR 8.0/8.25/8.25 dB). One Receiver independent readback failed at 74%; a
subsequent read-only full snapshot verified its normal image and preserved
signature/serial/EEPROM/fuses/lock and Flash outside the image. No repeat write
was used for that read failure. Logs: `receiver-restore-readonly-check/` and
`20261113T080205Z-raw-regression/` under `artifacts/arq/`.

ตรวจ antenna connections, RF path and board power before a new fresh-session
H01. The agent cannot inspect connections or measure power remotely. Power
integrity remains unmeasured. Deduplication is RAM only and cannot survive
reset. Authentication, persistence, adaptive RTO and FOTA remain deferred.
