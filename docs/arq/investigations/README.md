# ACK investigation

The ACK root cause is not established. Host models do not prove RF reception.
Latest state: [20261113T123620Z](20261113T123620Z.md) INCONCLUSIVE after Tracker
UPDI exited following SEND. Active Rudolph RX Continuous was verified; no new
RF verdict. Both boards restored to verified normal unarmed standby at
`20261113T123837Z-standby`. RF testing stopped. Reliable Tracker observation and
physical RF/supply isolation remain required; no specific hardware defect is proven.
Physical connector, solder-bridge, antennas and 915 MHz module markings were
confirmed by the operator in this session; boards are about one metre apart.

| Experiment | Actual result | Verdict |
| --- | --- | --- |
| Latest software checks | 190 tests, OK with one skip; all six builds, generator/SSOT/isolation checks pass; cleanup attempts both peers after monitor exit | PASS; host checks do not establish RF success |
| [Host readiness/configuration audit](20261113T123510Z.md) | Prior RX_READY-before-SEND confirmed from host timestamps; new mode/profile gating, pre-cleanup counters, real driver IQ/modem characterization | Software evidence; no speculative PHY change |
| [20261113T123620Z reverse raw](20261113T123620Z.md) | Active RX8D verified; Tracker UPDI empty response after SEND; 74 hashes/eight events verify; no TX or RX terminal evidence | INCONCLUSIVE; preserved independently of earlier RF failure |
| `20261113T123837Z-standby` | Normal images, protected memory and fresh standby identities/status verified on both boards | PASS; no further RF attempt |
| Archive integrity | 59 + 59 + 59 + 56 + 60 + 33 recorded file hashes verified without hardware access | PASS, historical integrity only |
| Baseline preservation | 28 current build images, identities and generated files copied with SHA-256 under `.automation/ack-investigation/baseline/` | Preserved before edits/builds |
| Capture recovery | Missing startup, partial/absent response, identity mismatch, overflow, monitor exit and cleanup tests | See current verification below |
| Archived preservation comparisons | Raw baseline/final protected Flash, EEPROM, identity/fuses/lock independently compared for both boards; Sender standby snapshot compared | PASS; Receiver standby record lacks colocated snapshots |
| `20261113T120629Z-reverse-raw` | STOPPED during acquisition: reported identities differ from generated headers; STATUS recovery returned Rudolph's full identity; no RX/SEND command issued | INVALID as RF test; raw logs, images, readbacks and failure retained |
| Image/header regression | All six actual HEX images failed identity containment after an incremental build | Confirmed software build-provenance defect; identity moved into compiler definitions to invalidate stale objects |
| Rebuilt image/header regression | All six HEX images contain their declared identity after the compiler-definition fix | PASS; real RF ACK root cause remains unknown |
| Host verification | `uv run python -m unittest discover -v -s tests`: 185 tests, one obsolete Receiver BOOT-repair class skipped; configuration/isolation/diff checks pass; all six firmware targets built | PASS; no hardware inference from simulations |
| `20261113T121210Z-standby` | Fresh normal images programmed/read back for both boards; matching build/config, complete status, overflow=0, mode standby, no RF transmissions | PASS; recovery from stale embedded identities verified |
| [20261113T121506Z reverse raw](20261113T121506Z.md) | One Tracker TxDone; Rudolph no RxDone within 15000 ms, IRQ flags zero; 62 hashes and all 12 journal events verified against raw streams | FAIL; H01–H04 and timing NOT_RUN |
| `20261113T121735Z-standby` | Normal unarmed standby restored; independent image/protected-memory comparisons, matching identities, complete zero-overflow logs, no TX | PASS; both ports released |

The local host compiler was provisioned without system changes by downloading
Fedora `gcc`, `gcc-c++`, `cpp`, and `libstdc++-devel` RPMs and extracting them
under `.automation/ack-investigation/toolchain/root/`. Tests use that `usr/bin`
on PATH, its GCC 16 library directory on LIBRARY_PATH, and its three C++ include
directories on CPLUS_INCLUDE_PATH. `uv run` supplies the existing pyserial
dependency. Complete host output is retained at
`.automation/ack-investigation/host-suite.log`.

The full suite also exposed existing UPDI tests that could not pass: STS ACK
bytes were never checked and failed connections could be reused. The shared
transport now checks ACKs, invalidates failed connections, and exits its monitor
when a reader fails while stdin is blocked. Four focused transport tests pass.
Legacy Receiver aggregate initialization was changed from `{0}` to `{}` to
retain zero initialization under the stricter host C++ compiler.

Review is performed inline, respecting the operator's prohibition on subagents.

Use [TEMPLATE.md](TEMPLATE.md) for each physical experiment, including failures.
Original evidence, raw firmware and standby snapshots remain in `artifacts/`.
`20261113T084503Z` is a capture failure before ARM/SEND, not a negative RF test.

Implementation decisions: reuse the existing runner and bounded application
writer; recover STATUS once per missing role, sequentially, within one 45-second
acquisition deadline. A capture failure sends no ARM/SEND and records its phase
and reason. Preserve the baseline 75 ms response guard; no speculative OpMode
bit changes. MVP order is H01, H02, H03, H04, as requested in the current plan.
