# Board Swap Decisions

## RCA_BOARD_SWAP_01

- User newly confirmed safe power isolation, PCB-only swap boundary and physical X/Y labels. This supersedes the earlier safety blockage for the defined crossover; it does not itself mean the swap occurred. Original P→X/Q→Y endpoints remain until a requested action is explicitly completed.
- Reused exactly the existing two workers as P/Q lane owners. Coordinator alone owns shared source/reports and physical experiment choice. Workers may only open their own stable path in approved bounded attempts.
- Baseline suite 75 passed. Required crossover tests were written before new code; RED had 7 missing behaviors and 10 already-implemented behaviors passing. Minimal board-swap interpretation helpers then produced full GREEN: 92 tests passed before hardware approval.
- Reuse existing identity, raw probe, runner, earliest-failure analyzer, statistics and crossover classifiers. Added only SIB-specific outcome vocabulary and an explicit missing-restoration gate. No timing, timeout, baud or transport implementation changes.
- No control attempts in PRE if SIB already separates FC1. No SIB/LDCS target-response claim on failed synchronization. Port ownership errors remain host/preflight failures.
- Read-only host inventory at freeze resolved the two expected stable paths; tty aliases are recorded as locators. Both target unique identities, actual resistor values, connector type and power-source descriptions remain UNKNOWN where not provided.
- Crossed confirmation and restoration are dependent on a reproduced original baseline and human completion of the powered-off target-only endpoint swap. A request, elapsed time or tty renumbering is not completion evidence.
- PRE P now failed20/20 at UPDI_CONTROL_RESPONSE after exact synchronization and command echoes. This contradicts the original passing-P prerequisite, so classify NON_STATIONARY/NO-GO. Stop additional probes and hold Q before its first valid hardware attempt. Do not swap into an unreproduced baseline.
- Ask current target power state while preserving all wiring. The user-confirmed safe isolation method does not itself tell us whether the targets were on during PRE. Unknown power is not asserted as the cause.
- Q had two HOST_TOOL_ERROR wrapper failures before any probe; preserve those failures separately and do not count them as PORT_BUSY or UPDI results. Future batches should use the existing minimal probe/runner interfaces without additional custom wrappers.
