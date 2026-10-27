# Post-swap handoff

The current investigation is waiting for a physical restoration reply, not
complete. Do not resume the old PRE power question as a reason to recreate A1.
The latest user explicitly reported the boards were already swapped; the B
state has now been captured without agent hardware manipulation.

## Measured B state

Epoch RCA_POST_SWAP_01, phase CROSSED_UNTOUCHED. P at ID_PATH ending
usb-0:4:1.0 drives user-labeled Y; Q ending usb-0:1:1.0 drives X. Unique AVR
identities remain UNKNOWN_TARGET. Current inventory locators ttyUSB0/1,
bus3 devices21/22, are historical locators and must be resolved again.

P:0/30 SIB;1 corrupt BREAK1 (00→80),29 missing SIB responses after exact
BREAK1/BREAK2/SIB-command echoes. Q:0/30 SIB;24 empty BREAK1 echoes and6 empty
BREAK2 echoes after exact BREAK1. No Q SIB request was sent. All ports closed.
No control/ACC/programming/reset command. New flash/fuse/BOD/erase/repair:0.

FC1 remains descriptively associated with Q, but no A2 restoration exists.
P's later SIB-response failure also occurred in the latest PRE (20/20), whose
power state is unknown. Do not merge this with historical FC2 ACC19/60.
Do not claim target or adapter component locality as proven.

## Pending human action

One async request asks the user to safely power down and restore X to P,
Y to Q while retaining USB ports/cables, CP2102 units, resistors and both
jumpers with their external path, then power on using the same procedure.
Wait for explicit “Restored” or inability to do it safely. No completion is
implied by elapsed time. Another optional text question about swap power/
USB-unplug history is unanswered; retain unknowns if no answer arrives.

If restored: write A2 intervention record including known power sequence,
rediscover P/Q from ID_PATH and check port owners, then authorize each of
the SAME two workers for30 strict SIB attempts in new RESTORED directories.
Never overwrite B evidence. Compare stage-specific A1/B/A2 results, retaining
the non-stationary A1 caveat. Choose exactly one supported next branch.

If restoration cannot be done safely: stop at the measurement boundary.
Request simultaneous TX, shared/target UPDI, MCU-local VDD and ground-offset
capture around BREAK1/BREAK2 as specified in the STAR report. No repair or
speculative firmware change is authorized.

## Verification and artifacts

105 host tests pass.21 evidence checks pass. Old569+new60=629 runs;
old7073+new277=7350 events; all raw hashes valid, all event IDs unique/mapped.
41 frozen old reports remain unchanged.168 master IDs and41 focused IDs
preserved. All required new post_swap CSVs and STAR_POST_SWAP_RCA.md exist.
P manifest237 entries verifies; Q raw30 hashes match manifest. Q output has
combined stdout/stderr only; record this limitation without inventing streams.

Only board_swap.py interpretation code and test_post_swap.py changed. Strict
transport code unchanged. Graphify refreshed. Follow current installed
Superpowers skills; use test-first for new Python. Reuse existing CLI/probe/
runner, no new framework or custom lane wrapper. Exactly two existing workers:
/root/lane_a owns P and /root/lane_b owns Q. Coordinator owns shared reports.
