# RCA_BOARD_SWAP_01 execution plan

## Contract and physical gate

Continue the approved board-swap specification. The user now confirms: **safe isolation and PCB-only swap verified; X/Y physically labeled**. Original endpoints remain P→X and Q→Y until the coordinator requests a swap. Connector type, board description and power-source details were not supplied; record UNKNOWN rather than invent them. The confirmed boundary keeps USB port/cable/CP2102/bridge/resistor/UPDI and GND jumpers with P/Q. No firmware/fuse/baud/timeout changes.

## Hypothesis and experiment

- Hypothesis: FC1 belongs to a target assembly, external path, handling-dependent state, or interaction.
- Prediction: original/crossed/restored observations move the first/second 300-baud BREAK echo failure with the controlled entity, or demonstrate non-stationarity/interaction.
- Independent variable: target PCB endpoint attached to each intact external path.
- Controls: fixed USB topology, adapters, cables, resistor/bridge, UPDI/GND harness, 38400 nominal session, existing 300-baud synchronization, existing 1 s timeout, same probe implementation, firmware and fuses.
- Measurement: 20 original SIB attempts per path; if asymmetry reproduces, stop serial activity and request powered-off target-only swap; re-resolve ID_PATH, 30 crossed SIB screen per path; informative result leads to 100-SIB confirmation and 100 control attempts where synchronization passes. Restore original endpoints and repeat screening/confirmation appropriate to the observed effect.
- GO: clearly reproduced original P+X passing / Q+Y failing pattern; no ownership or identity ambiguity.
- NO-GO: changed original pattern, ambiguity, busy port or simultaneous changed physical variables. Stop crossover classification and investigate the condition.
- Interpretation: FC1 remains separate from historical FC2 (19/60 exact-echo ACC misses). One crossover alone cannot establish causal locality. Restoration is mandatory; retain rate/interaction/handling outcomes.

## Software and ownership

1. Re-read current skills and checkpoint; 75-test baseline verified.
2. Coordinator adds required crossover tests before implementation; reuse current immutable pairing/identity/classifiers and offline BREAK forensics. Add only the missing SIB-stage vocabulary and restoration gate. Observe RED, implement minimum, run focused and full suite before hardware.
3. Reuse exactly two existing agents: lane_a owns P (`pci-0000:00:14.0-usb-0:4:1.0`), lane_b owns Q (`pci-0000:00:14.0-usb-0:1:1.0`). No additional agents. Workers write only epoch `path_p`/`path_q` evidence and their `PATH_P.md`/`PATH_Q.md`; never shared CSV/report/source. Only coordinator approves batches and physical changes.
4. Each attempt resolves current adapter, acquires exclusive lock/open, probes, closes and persists raw bytes/hash. Before batches check owners and bounded kernel/topology observations. Never kill unrelated processes.
5. Coordinator produces versioned runs/events and `board_swap_matrix.csv`, `swap_echo_distribution.csv`, `swap_causal_proof.csv`, `STAR_BOARD_SWAP_RCA.md`; maintain SWAP_FREEZE/CURRENT_STATE/DECISIONS/EVIDENCE_LOG Markdown.
6. Preserve inherited 509/6387 and earlier continuation 40/546 separately; current start is 549 runs/6933 events. New rows identify epoch, stable path, physically confirmed X/Y label, tty locator, timestamps, condition, attempt, stage, raw path/hash.
7. Verify all current tests, preserved/raw hashes, event/attempt keys, schemas, full required question set and write budget. Refresh Graphify after code changes.

## Safety and stop boundary

Flash=0, fuse=0, BOD changes=0, chip erases=0. No repair until causal isolation supports it. Physical changes require targets powered off and an explicit completion report. Elapsed time is not swap confirmation. If the physical action is pending, persist WAITING_PHYSICAL without inventing crossed/restored measurements.
