# UPDI implementation ledger

Specification: the supplied “Stabilize the AVR128DA28 UPDI Console” plan.

- Scope: receiver probe, target build adapter, upstream failure/lifecycle patch,
  standard-library tests, measurement evidence and reproducible diffs.
- Ruling: use a new branch in the active workspace because every project source
  and the nested upstream checkout are untracked; a new worktree omits them.
- Baseline: upstream f2222b02ceeff7668caab0f240d2e13298116356, clean.
- Original project files copied into `.automation/updi-baseline/` before edits.
- No transport sequencing or register-address changes without measured evidence.
- Physical topology, VCC, logic levels and cable length cannot be measured remotely.
- Probe built/uploaded once: 774 bytes verified, hex SHA256
  `88c03596bab443c74015d8dfb04e1985f6d14940d227b84a4a943b3d5f47807e`.
- Baseline SIB 20/20 at each of 115200, 57600, 38400; all echo/short counters zero.
- First traced failure at default 921600: echo of `55 40 1e` succeeds,
  missing first STS ACK. Same failure seen intermittently at 115200.
- At 38400 no transport fault observed in trace, but repeated CPU stopped states,
  no OCD messages; separate `-r` trace did not change that behavior.
- Status snapshot: latched RSTFR brownout flag 0x02; this does not prove VCC or
  the cause of the resets. User explicitly confirmed physical details remain unknown.
- Ruling: do not change startup sequencing, disable BOD, introduce retries, or
  progress to HELLO firmware without valid H output. Hardware acceptance remains open.
- Target adapter now builds the upstream body; rebuilt probe hex is identical to
  the uploaded file. No second upload.
- Tests observed failing on baseline, then passing after lifecycle patch.
- Whole-change reviewer found Windows redirected-input regression and SIB logger
  diagnostic mismatch; both fixed. Baud reconfiguration context and no-default-port
  CLI traceback also fixed. Windows pipe readiness has a mocked regression test;
  native Windows behavior remains untested.
- Real patched 115200 and 921600 failures: exit 1, one contextual stderr diagnostic,
  terminal attributes restored. A separate clean real session exited 0 via Ctrl+E,e.
- Final regression suite: 11/11. Both firmware environments build. A full receiver
  rebuild emitted only DxCore's pre-existing PROGMEM_MAPPED informational pragma.
- Final SIB CSV again confirms 20/20 each at 115200/57600/38400, zero errors.
- Ruling: 38400 is a candidate only; no baud is accepted without valid output.
  Cost: console remains unaccepted until the physical/reset condition is resolved.
- Graphify AST update succeeded, with upstream header parser limitations and empty
  symbol reports for the thin include adapters. Source and tests remain authoritative.
- Final 38400 attempt also missed the first STS ACK: exit 1, one diagnostic,
  termios restored and `stty -g` equality verified. No baud passes terminal gates.
- Both delivered diffs applied to clean original project files/pinned upstream in
  a temporary checkout. Reproduced host matches byte-for-byte; 11/11 tests pass.
- All reviewer findings addressed; no deferred code findings. Native Windows and
  physical/electrical behavior remain verification limits, not proven fixes.
