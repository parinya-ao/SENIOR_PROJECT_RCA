# Post-swap RCA state

Epoch: RCA_POST_SWAP_01. Phase measured: CROSSED_UNTOUCHED.
Updated: 2026-10-27.

- Mapping: P=ID_PATH usb-0:4:1.0→physicalY; Q=usb-0:1:1.0→physicalX, per latest user. Current locators ttyUSB0/1; bus3 devices21/22. Both unique targets UNKNOWN_TARGET.
- Crossed screen: P0/30 SIB,1 BREAK1 corrupt00→80,29 missingSIBresponse after exact echoes; Q0/30 SIB,24BREAK1empty+6BREAK2empty. NoACC/control probes.
- Metrics: P median/p95 1145.145/1149.716ms;Q1061.754/1063.539ms. Each SIB success Wilson95 0–11.352%. FC1 rate P3.333%(0.591–16.671%),Q100%(88.648–100%).
- Boundary: stage-specific Q-path FC1 association SUPPORTED; component/path locality not proven. Both completeSIB fail at different predominant stages. Prior PREP0/20 exactecho/SIBmissing remains separate non-stationarity.
- Counts: inherited569runs/7073events;new60/277;total629/7350. Echo rows124;allnewrawhashes60verified;41oldreporthashes unchanged.
- Last experiment: POST-00130 perpath;portsclosed/ownercheckclear. No hardware touch by agents. No100expansion because bothfullSIB fail and nonstationary/powerconfounds remain.
- Unknowns: MCU-localVDD;currentpower andswappowerhistory;uniqueAVRidentity;componentmechanism;A2restoration. Optional power-history question pending.
- Next gate: crossed evidence is persisted and verified. The user has been asked for one safe restoration to P→X/Q→Y, with both targets powered afterward and all external bundles retained. Await explicit completion before rediscovery or another probe. Record power-cycle/reseat details as an intervention, then select30 SIB attempts per path.
- Safety: flash0,fuse0,BOD0,erase0,repair0. No reset/programmingkey/STCS/STS.
- Primary report: reports/STAR_POST_SWAP_RCA.md. Do not overwrite olderSWAP/FOCUSED reports.

## Checkpoint verification

105 host tests pass.21 ledger/schema/identity checks pass. All629 raw-log
hashes verify (569 inherited,60 new); all7350 event IDs are unique and mapped.
P's237 manifest entries and Q's30 raw hashes match their saved manifests.
Graphify AST update completed:2637 nodes,4331 edges,187 communities; existing
external header parsing warnings remain. No unrelated source was edited.

Q command output was retained as a combined tool stream. Separate stdout and
stderr cannot be recovered retrospectively. Raw serial bytes and command exit
results are preserved. No rerun was made to conceal that capture limitation.
