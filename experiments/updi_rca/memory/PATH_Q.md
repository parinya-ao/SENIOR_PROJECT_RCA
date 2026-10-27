# Path Q lane — RCA_BOARD_SWAP_01

Updated 2026-10-27 02:02 UTC. Q remains on the original endpoint Q→Y; no board swap occurred. The coordinator instructed this lane to hold further hardware activity pending the target power-state answer.

## Inventory

- Stable adapter identity: ID_PATH=pci-0000:00:14.0-usb-0:1:1.0, VID:PID 10c4:ea60, USB serial 0001 (duplicated across adapters, not identity).
- Stable by-path locator: /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0. Udev also exposes the alias containing usbv2; both aliases resolve to one endpoint.
- Current tty locator at 2026-10-27 02:02 UTC: /dev/ttyUSB1. This is a locator only.
- Sysfs device: /sys/devices/pci0000:00/0000:00:14.0/usb3/3-1; tty interface: /sys/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0/ttyUSB1.
- At the 01:57 UTC inventory snapshot, USB sysfs reported bus 3/device 19, 12 Mbit/s, authorized=1, power/control=on, runtime_status=active, autosuspend delay=2000 ms. No power or service setting was changed.
- Original target label Y is coordinator/user-confirmed. Unique AVR target fingerprint remains UNKNOWN_TARGET. Power source and time since target power-on remain unknown.

## Ownership and host USB observations

- At 01:57:10 UTC, fuser -v and lsof on Q’s stable by-path both exited 1 with no file-owner output. lsof may emit its tracefs warning; that warning does not name a serial-device owner.
- A clean process-table capture at 01:57:47 UTC had no avrdude, upditerm, or RCA CLI process line.
- A fresh direct check at 02:02:13–02:02:15 UTC re-resolved the stable link to ID_PATH Q and /dev/ttyUSB1; fuser -v exited 1 with empty output and lsof exited 1 with only “can't stat() tracefs” warning. No process held Q at that snapshot.
- USB topology at 01:57 showed both CP210x interfaces on bus 3, ports 1 and 4. dmesg was denied with “Operation not permitted”; journalctl -k -n 100 returned “No entries” plus a permissions hint. Kernel logs were unavailable, so this is not evidence of a clean USB interval.

## PRE batch status

**Not started: 0/20 attempts.** Two single-use host wrappers failed (HOST_TOOL_ERROR): first at parse time, then during wrapper setup. See experiments/updi_rca/evidence/RCA_BOARD_SWAP_01/path_q/tooling_failures.md. The second wrapper’s immediate fuser/lsof output was not persisted; do not classify it as PORT_BUSY. Its run directory contains no raw JSON. A later direct fuser/lsof check was clear, but the coordinator then instructed this lane to hold pending the target power-state answer. No SIB, control, reset, key, write, fuse, flash, BOD change, or physical manipulation was performed by this lane.

The previous inventory logs and their hashes:

- inventory_commands.log — SHA-256 f56deabc4eb3e8c63d9b0db9243e2c6d776bec8054209c2908b39e1ef285aa50
- inventory_final.log — SHA-256 ef789ffded3b0028bd259adcedb56b1aaabbcbe7b91177473a9b1f720f2ac9c8
- pre/Q_PRE_SIB_20261027T015644Z/preflight.log — SHA-256 54d2456afed954c90301f083a06bc74b35cd1f49e1faac5cc5161a143eba7330
- pre/Q_PRE_SIB_20261027T015644Z/owner_processes.log — SHA-256 e1014eea6c8e4d8bc9852ccf36ec0e31c488b85ce0c5183d11afcd58592677ca

The unique run folder pre/Q_PRE_SIB_20261027T015802Z/attempts/ exists but is empty. No attempt or run row should be counted for Q.

Latest lane-only record hashes:

- `evidence/RCA_BOARD_SWAP_01/path_q/tooling_failures.md` — SHA-256 `d95dbfca2849450965477b73e64979cb2c9712f51bd5fbe1998555184dc9b033`
- `evidence/RCA_BOARD_SWAP_01/path_q/owner_check_20261027T0202Z.md` — SHA-256 `167cda9f34ba8498e5d8e09e54b64de77963c7e87f33dbf2ac02f841188dad64`
