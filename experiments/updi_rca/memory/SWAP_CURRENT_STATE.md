# Board Swap RCA State

Epoch: `RCA_BOARD_SWAP_01`
Updated: 2026-10-27, after PRE NO-GO.

## Physical mapping

P:
- ID_PATH: `pci-0000:00:14.0-usb-0:4:1.0`
- tty locator at freeze: `/dev/ttyUSB0`
- target: physically labeled X by user; unique silicon fingerprint UNKNOWN.

Q:
- ID_PATH: `pci-0000:00:14.0-usb-0:1:1.0`
- tty locator at freeze: `/dev/ttyUSB1`
- target: physically labeled Y by user; unique silicon fingerprint UNKNOWN.

## Current phase

PRE, waiting for target-power-state clarification. User confirms safe isolation and PCB-only swap, with original endpoints retained. Both workers have finished/held and both ports are closed.

## Current result

P→X: 0/20 SIB responses, with exact BREAK1, BREAK2 and SIB-command echo in20/20 each. Failure stage UPDI_CONTROL_RESPONSE, outcome SIB_TX_ECHO_OK_RESPONSE_MISSING. Q→Y:0 attempts, held when original P baseline changed; two failed host wrappers executed0 hardware attempts. No physical crossover or restoration has been requested or reported.

## Causal classification

NON_STATIONARY / UNRESOLVED. PRE GO prerequisite failed: previously passing P now has a later SIB-control response failure. This is not FC1 echo failure or FC2 ACC timeout. Current target power during PRE is awaiting user clarification.

## Hard metrics

Inherited509 runs/6387 events; previous continuation40/546; swap start549/6933. New20 runs/140 events; total569/7073. 20/20 current raw hashes match. P pass rate0%, Wilson95 success CI0–16.113%; median/p95 latency1146.775/1148.088ms. All60 host echo frames exact. Current host suite92 passed.

## Last experiment

PRE P SIB20, run swap-pre-P-20261027T015802555251Z, UTC01:58:02–01:58:26. Q held at0attempts. Host-only wrapper failures are recorded as tooling evidence, not port/UPDI failures.

## Next smallest discriminator

User must report whether both targets were powered on during PRE. Do not request crossover until original baseline is understood/reproduced. No power cycle is inferred or silently executed. If power was off, any power-on repeat is a recorded independent-variable experiment.

## Safety

Flash writes: 0
Fuse writes: 0
BOD changes: 0
Chip erases: 0
No firmware, NVM/FOTA, FLAG_RX or ACC investigation during FC1.
