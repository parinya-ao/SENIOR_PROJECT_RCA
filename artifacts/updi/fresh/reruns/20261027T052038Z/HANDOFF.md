# Rerun handoff — RCA_FRESH_01 /20261027T052038Z

Read [STAR_RCA.md](STAR_RCA.md), [verification](VERIFICATION.json), [memory](MEMORY.md) and [power event](reports/reported_interventions.csv).

User rerun finished:220 new SIB attempts/1540 events. SmokeP0/10,Q0/10; baseline1/2/3 each30: P0,0,0 andQ30,30,29; confirmation10: P0,Q10. Baseline+confirmation excludes smoke: P0/100,Q99/100 strict length-based passes, with one full32-byte payload anomaly amongQ passes and one16-byte short failure. Both latestSIB30 control gates false; identitiesUNKNOWN.

User confirms P /ttyUSB1 power changed/cycled during this rerun; timing unknown. Do not call these verified untouched baselines, spontaneous recovery, a controlled power result, a repaired target or proven path locality. AllD1–D8 unresolved/0. No physical action/restoration is pending. Both ports idle; no further probes authorized merely by this handoff.

All raw/source hashes and prior438 fresh artifacts match. Two context-tool historical paths drifted: .automation/compact-bundle.xml and .repomixignore under experiments/updi_rca. Original1090-file freeze1088 matches; rerun1529-file freeze1527 matches. Anchors preserved; full-history status is notPASS. See explicit verification caveat.

No source changes;150 host tests pass. Zero flash/fuse/erase/BOD changes. Exactly the existing two lane workers were reused. Causal branch remains BLOCKED_MEASUREMENT /POWER_CONFOUNDED. Next discriminator: qualified safe-reference/pinout verification and one simultaneous BREAK-triggered target-local VDD, ground-offset, adapter-TX and UPDI capture with fixed supplies and recorded power state. No board swap or repair request.
