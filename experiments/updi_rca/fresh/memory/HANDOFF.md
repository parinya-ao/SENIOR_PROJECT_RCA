# Fresh RCA handoff — RCA_FRESH_01

Read [STAR_RCA.md](../STAR_RCA.md), [PLAN.md](../PLAN.md), [MEMORY.md](../MEMORY.md) and [TOPOLOGY.md](../TOPOLOGY.md).

Implementation and untouched baseline complete: 150 host tests pass; 80 fresh SIB attempts / 560 events. P smoke0/10 + baseline0/30; Q smoke0/10 + baseline0/30, all SIB_RESPONSE_EMPTY. Fresh P is usb-0:1:1.0 and Q usb-0:4:1.0. Both targets UNKNOWN. Two separate power boards recorded by current branch; their physical identity and supplies remain unknown. No inherited X/Y or P/Q mapping is valid here.

Current causal status: BLOCKED_MEASUREMENT, all D1–D8 unresolved at zero. No mixed outcome or changed stage boundary, so no mandatory extra untouched batches. No useful between-lane rate contrast justified 100 attempts. Both control/identity gates false. No physical action or repair is pending authorization. Do not infer a restoration request from historical campaigns.

One next discriminator: qualified safe-pinout/reference verification and simultaneous target VDD, ground offset, adapter TX and target UPDI capture triggered by BREAK on one P SIB attempt. Instrument availability and safe attachment are unverified. Do not open a port, move hardware or resume batches just because this handoff exists; use the active user's next instruction and preserve the frozen epoch.

Runnable lane command (coordinator approval required for a new batch): `PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.fresh experiments/updi_rca/fresh P NEW-BATCH sib 30`. Never reuse batch names; interrupted batches remain reserved. Refresh shared reports only through the coordinator's `refresh_reports`. Check hashes with `verify_history` and `validate_evidence` before interpretation. The runner does not expose 16-bit reads or programming operations.

Known limits: duplicate adapter descriptors cannot detect an identical unit replacement on the same path. Files are application-write-once and hash checked, not physically write protected. No source transport change, firmware/fuse read, instrument measurement or physical causal isolation was performed. Exactly two lane workers were used; coordinator reviewed implementation. Claudе-mem observer credentials are signed out; durable campaign state is in these files.
