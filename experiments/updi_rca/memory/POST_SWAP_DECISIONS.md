# Post-swap decisions

- Latest user report supersedes PRE_NO_GO waiting state: boards already swapped. Capture current B state first; do not ask for another swap or recreate PRE.
- Treat P→Y/Q→X as user-confirmed physical continuity, not silicon identity. Freeze both adapters by stableID_PATH; duplicate0001 and tty aliases cannot identify them uniquely.
- Reuse exactly two existing workers. Coordinator alone edits shared source and reports. Workers do not touch hardware or sharedCSV.
- Add only confound-aware assessment and required tests;105hosttests green. No transport modifications.7intendedRED failures observed;6existing behaviors reused.
- POST-001 uses30SIB-only probes perpath. All60failed fullSIB but Q30FC1 and P1FC1/29SIBresponsemissing are different observations. An unreached secondBREAK is not an empty secondBREAKecho.
- CurrentFC1 rate difference supports an external-path association, not a CP2102 diagnosis. P's later response failure predates this crossed screen. No complete stationary2×2 design exists; interaction/multiplefaults remainunknown.
- Stop at30each:100morezeros would not resolve power/reseat/nonstationarity. Persist/verify current B state,thenonecontrolledrestore supplies higherinformation.
- No kernel absence-of-error claim: journal/dmesg visibility insufficient. No usbmon escalation before restoredcomparison.
- Preserve41historicalreporthashes andall168hypothesisIDs. New epochCSVsonly;physicalcomponentstatusesnotpromotedwithouta discriminator. No flash/fuse/BOD/erase/repair.
