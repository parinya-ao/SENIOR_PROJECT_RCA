# Board-swap physical freeze

Epoch: `RCA_BOARD_SWAP_01`

Updated UTC: 2026-10-27T01:55:39.910446+00:00

User confirmed safe power isolation and PCB-only crossover are verified; X/Y physically labeled. Endpoints remain original until a completed coordinator-requested swap. The user did not supply connector/power-source descriptions; those fields remain UNKNOWN.

## External Path P

- Physical USB port/topology: `pci-0000:00:14.0-usb-0:4:1.0`
- Current tty locator: `/dev/ttyUSB0`
- Sysfs: `/sys/devices/pci0000:00/0000:00:14.0/usb3/3-4/3-4:1.0/ttyUSB0/tty/ttyUSB0`
- VID/PID: `10c4:ea60`; USB serial: `0001` (duplicate, not identity).
- By-path link: `pci-0000:00:14.0-usb-0:4:1.0-port0`
- USB cable description / CP2102 marking: UNKNOWN; keep the same physical items with P.
- Resistor/bridge actual value: UNKNOWN; remains with P.
- UPDI jumper and GND jumper: same existing bundle; remains with P by user-confirmed boundary.
- Target: **X**; target unique fingerprint UNKNOWN.

## External Path Q

- Physical USB port/topology: `pci-0000:00:14.0-usb-0:1:1.0`
- Current tty locator: `/dev/ttyUSB1`
- Sysfs: `/sys/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0/ttyUSB1/tty/ttyUSB1`
- VID/PID: `10c4:ea60`; USB serial: `0001` (duplicate, not identity).
- By-path link: `pci-0000:00:14.0-usb-0:1:1.0-port0`
- USB cable description / CP2102 marking: UNKNOWN; keep the same physical items with Q.
- Resistor/bridge actual value: UNKNOWN; remains with Q.
- UPDI jumper and GND jumper: same existing bundle; remains with Q by user-confirmed boundary.
- Target: **Y**; target unique fingerprint UNKNOWN.

## Targets and shared controls

- Target X: user-applied physical label; currently P; board description/connector type UNKNOWN.
- Target Y: user-applied physical label; currently Q; board description/connector type UNKNOWN.
- Target power source and time since power-on: UNKNOWN. User confirms a safe power-off method and PCB-only endpoint disconnect.
- Host mains online: 1; other power states are in coordinator/preflight.log. Historical charger state is not inferred.
- Host sleep/autosuspend: not changed; no observed sleep transition yet.
- Current firmware hashes: UNKNOWN; no writes permitted.
- Current fuse snapshots: UNKNOWN; no writes permitted.
- Photographs: not supplied.
- Physical movement during PRE: none instructed; preserve current configuration.

## Frozen ledger boundary

- `experiments/updi_rca/reports/runs.csv`: 509 rows; SHA-256 `cc2d794a45677685065f0c7752916c32478b21351da0b49afecdf541cb086a93`.
- `experiments/updi_rca/reports/events.csv`: 6387 rows; SHA-256 `31f75235ed9fcbd4eb0344ab7db5ff253a27198302eec1c3f9ed503095e27c88`.
- `experiments/updi_rca/reports/continuation/RCA_CROSSOVER_01/runs_RCA_CROSSOVER_01.csv`: 40 rows; SHA-256 `4e425226f4b572b33280e6d8368767723da493150ca10f866bf636c8aa132a21`.
- `experiments/updi_rca/reports/continuation/RCA_CROSSOVER_01/events_RCA_CROSSOVER_01.csv`: 546 rows; SHA-256 `8296cfdf92161d0086db62eb5364cc3d46bf5b838aa767bafca07d322d8f3c57`.

Old baseline =509 runs /6387 events. Earlier continuation =40 runs /546 events. Start-of-swap total =549 runs /6933 events. No previous hardware row is reclassified as a new swap attempt.
