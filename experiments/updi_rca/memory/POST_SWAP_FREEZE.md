# Post-swap physical freeze

Epoch: RCA_POST_SWAP_01. Initial phase: CROSSED_UNTOUCHED.
Coordinator report freeze: 2026-10-27T03:31:24.591149Z.

The user explicitly reports the target-PCB swap has already happened. Do not
repeat it or restore it before crossed measurements are persisted. No physical
change, power cycle or reset command is authorized during POST-001.

## Mapping provenance

Inherited SWAP_FREEZE.md defines P by ID_PATH
`pci-0000:00:14.0-usb-0:4:1.0`, previously attached to physical X, and Q by
`pci-0000:00:14.0-usb-0:1:1.0`, previously attached to physical Y. The user
confirmed X/Y labels and PCB-only isolation before this latest report.

Latest user-reported crossed mapping: P→Y, Q→X. These are physical labels,
not newly read silicon identities. Both target serial/signature/REVID remain
UNKNOWN_TARGET until current documented reads prove them. SIB alone is a
family response, not a unique target serial.

External bundles remain the declared experimental boundary: physical USB
port, USB cable, CP2102, bridge/resistor, UPDI jumper and GND jumper. Actual
connector description and resistor values are UNKNOWN. Current tty aliases
must be resolved by workers from current udev/sysfs, not copied from PRE.

## Confounds

Target power state during earlier PRE20 remains UNKNOWN. The latest PRE P→X
had 0/20 target SIB responses despite 20/20 exact echoes at all three exchange
stages. That is preserved non-stationarity, separate from historical FC1 and
FC2. Q PRE was held at zero attempts.

Whether USB adapters were unplugged, target power-off duration, power-on
sequence and exact swap time are UNKNOWN; a text-only question is pending.
No analog VDD/reference measurement is available. Notebook power connection
does not establish MCU-local VDD. Physical mapping is user-reported rather
than photographically/serial-number verified.

## Evidence boundary

41 inherited CSV/Markdown report files are frozen by SHA-256 in
evidence/RCA_POST_SWAP_01/inherited_report_hashes.csv. Hardware row boundary:
509 original +40 continuation +20 PRE =569 runs;
6387 original +546 continuation +140 PRE =7073 events.
No old row is counted as a new crossed observation.

## Software gate and safety

Inherited92 tests passed. New tests initially showed7 missing-gate failures
and6 covered behaviors passing; minimal confound-aware assessment added.
Full105 tests passed before the crossed serial screen. Probe/transport/
framing/timeout implementation unchanged. Nominal38400, BREAK300, 8E2,
timeout1.0s. New flash/fuse/BOD/erase/repair actions:0.
