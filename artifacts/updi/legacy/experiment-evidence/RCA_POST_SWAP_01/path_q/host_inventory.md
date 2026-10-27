# Q host inventory — RCA_POST_SWAP_01 / CROSSED_UNTOUCHED

Inventory date: 2026-10-27 UTC. Commands ran on the host surface. This lane did not open the serial port, probe UPDI, change the hardware, alter power, or touch shared source/reports. The user's physical update is Q→X; board identity by signature remains `UNKNOWN_TARGET` because no target read was performed.

The command runner returned a single combined output stream; separate stdout/stderr streams were not exposed. Outputs below are transcribed verbatim from the runner, including empty output where applicable. Each command's exit status, UTC start/end, and `/proc/uptime` monotonic start/end are retained. Independent inventory commands ran concurrently, so timestamp intervals can overlap.

## Stable identity and path

### Resolve Q by stable path

- Command: `udevadm info --query=property --name /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0`
- Exit: 0
- UTC: `2026-10-27T03:30:20.091740767+0000` → `2026-10-27T03:30:20.107189046+0000`
- Monotonic uptime: `62205.30` → `62205.32`
- Combined output:

```text
DEVPATH=/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0/ttyUSB1/tty/ttyUSB1
DEVNAME=/dev/ttyUSB1
MAJOR=188
MINOR=1
SUBSYSTEM=tty
USEC_INITIALIZED=61909231423
ID_BUS=usb
ID_MODEL=CP2102_USB_to_UART_Bridge_Controller
ID_MODEL_ENC=CP2102\x20USB\x20to\x20UART\x20Bridge\x20Controller
ID_MODEL_ID=ea60
ID_SERIAL=Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001
ID_SERIAL_SHORT=0001
ID_VENDOR=Silicon_Labs
ID_VENDOR_ENC=Silicon\x20Labs
ID_VENDOR_ID=10c4
ID_REVISION=0100
ID_TYPE=generic
ID_USB_MODEL=CP2102_USB_to_UART_Bridge_Controller
ID_USB_MODEL_ENC=CP2102\x20USB\x20to\x20UART\x20Bridge\x20Controller
ID_USB_MODEL_ID=ea60
ID_USB_SERIAL=Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001
ID_USB_SERIAL_SHORT=0001
ID_USB_VENDOR=Silicon_Labs
ID_USB_VENDOR_ENC=Silicon\x20Labs
ID_USB_VENDOR_ID=10c4
ID_USB_REVISION=0100
ID_USB_TYPE=generic
ID_USB_INTERFACES=:ff0000:
ID_USB_INTERFACE_NUM=00
ID_USB_DRIVER=cp210x
ID_VENDOR_FROM_DATABASE=Silicon Labs
ID_HARDWARE_WALLET=1
ID_MODEL_FROM_DATABASE=CP210x UART Bridge
ID_PATH_WITH_USB_REVISION=pci-0000:00:14.0-usbv2-0:1:1.0
ID_PATH=pci-0000:00:14.0-usb-0:1:1.0
ID_PATH_TAG=pci-0000_00_14_0-usb-0_1_1_0
ID_INTEGRATION=external
ID_MM_CANDIDATE=1
ID_MM_DEVICE_IGNORE=1
ID_MM_PORT_IGNORE=1
DEVLINKS=/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0 /dev/serial/by-path/pci-0000:00:14.0-usbv2-0:1:1.0-port0 /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0
TAGS=:systemd:
CURRENT_TAGS=:systemd:
```

The ID_PATH matches the assigned Q adapter. VID:PID is `10c4:ea60`; USB serial `0001` is duplicated and is not used as an identity key. Physical target label is X per the user's crossed-untouched confirmation. Current tty `/dev/ttyUSB1` is only a transient locator.

### Current by-path links

- Command: `ls -l /dev/serial/by-path`
- Exit: 0
- UTC: `2026-10-27T03:30:20.024240806+0000` → `2026-10-27T03:30:20.029513755+0000`
- Monotonic uptime: `62205.23` → `62205.24`
- Combined output:

```text
total 0
lrwxrwxrwx. 1 root root 13 Oct 27 10:25 pci-0000:00:14.0-usb-0:1:1.0-port0 -> ../../ttyUSB1
lrwxrwxrwx. 1 root root 13 Oct 27 10:25 pci-0000:00:14.0-usb-0:4:1.0-port0 -> ../../ttyUSB0
lrwxrwxrwx. 1 root root 13 Oct 27 10:25 pci-0000:00:14.0-usbv2-0:1:1.0-port0 -> ../../ttyUSB1
lrwxrwxrwx. 1 root root 13 Oct 27 10:25 pci-0000:00:14.0-usbv2-0:4:1.0-port0 -> ../../ttyUSB0
```

The standard and usbv2-spelled aliases for each USB path resolve to one tty each. The two adapters remain distinguishable by ID_PATH; tty numbering and duplicate USB serial do not identify them.

## USB topology and sysfs snapshot

### Topology

- Command: `lsusb -t`
- Exit: 0
- UTC: `2026-10-27T03:30:20.070165516+0000` → `2026-10-27T03:30:20.076984822+0000`
- Monotonic uptime: `62205.28` → `62205.29`
- Combined output:

```text
/:  Bus 001.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/1p, 480M
/:  Bus 002.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/3p, 20000M/x2
/:  Bus 003.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/12p, 480M
    |__ Port 001: Dev 022, If 0, Class=Vendor Specific Class, Driver=cp210x, 12M
    |__ Port 004: Dev 021, If 0, Class=Vendor Specific Class, Driver=cp210x, 12M
    |__ Port 006: Dev 004, If 0, Class=Video, Driver=uvcvideo, 480M
    |__ Port 006: Dev 004, If 1, Class=Video, Driver=uvcvideo, 480M
    |__ Port 006: Dev 004, If 2, Class=Human Interface Device, Driver=usbhid, 480M
    |__ Port 006: Dev 004, If 3, Class=Application Specific Interface, Driver=[none], 480M
    |__ Port 009: Dev 005, If 0, Class=Vendor Specific Class, Driver=[none], 12M
    |__ Port 010: Dev 006, If 0, Class=Wireless, Driver=btusb, 12M
    |__ Port 010: Dev 006, If 1, Class=Wireless, Driver=btusb, 12M
/:  Bus 004.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/4p, 10000M
```

Q is Bus 003 / Port 001 at this snapshot; the other CP210x is Bus 003 / Port 004. USB device numbers are dynamic locators.

### USB sysfs attributes

- Command: `for f in /sys/bus/usb/devices/3-1/{idVendor,idProduct,serial,busnum,devnum,speed,authorized,power/control,power/runtime_status,power/autosuspend_delay_ms}; do printf '%s=' "$f"; cat "$f" 2>&1; done`
- Exit: 0
- UTC: `2026-10-27T03:30:19.995069118+0000` → `2026-10-27T03:30:20.008149808+0000`
- Monotonic uptime: `62205.20` → `62205.22`
- Combined output:

```text
/sys/bus/usb/devices/3-1/idVendor=10c4
/sys/bus/usb/devices/3-1/idProduct=ea60
/sys/bus/usb/devices/3-1/serial=0001
/sys/bus/usb/devices/3-1/busnum=3
/sys/bus/usb/devices/3-1/devnum=22
/sys/bus/usb/devices/3-1/speed=12
/sys/bus/usb/devices/3-1/authorized=1
/sys/bus/usb/devices/3-1/power/control=on
/sys/bus/usb/devices/3-1/power/runtime_status=active
/sys/bus/usb/devices/3-1/power/autosuspend_delay_ms=2000
```

This records USB bridge runtime state only; it does not measure target MCU VDD or prove target power stability. No host setting was changed.

## Port ownership

The ownership commands used Q's stable by-path locator. No serial session was opened.

### fuser

- Command: `fuser -v /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0`
- Exit: 1 (no owner listed)
- UTC: `2026-10-27T03:30:20.092823326+0000` → `2026-10-27T03:30:20.230754428+0000`
- Monotonic uptime: `62205.30` → `62205.44`
- Combined output: empty.

### lsof

- Command: `lsof /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0`
- Exit: 1 (no serial owner listed)
- UTC: `2026-10-27T03:30:19.977111420+0000` → `2026-10-27T03:30:20.186420740+0000`
- Monotonic uptime: `62205.19` → `62205.39`
- Combined output:

```text
lsof: WARNING: can't stat() tracefs file system /sys/kernel/debug/tracing
      Output information may be incomplete.
```

The tracefs warning means lsof's overall view may be incomplete; the warning itself does not report a holder. The separate process filter below found no avrdude/upditerm/updi_rca process.

### Process filter

- Command: `ps -eo pid,comm,args | grep -E '[a]vrdude|[u]pditerm|[u]pdi_rca'`
- Exit: 1 (no matching process line)
- UTC: `2026-10-27T03:30:33.733143897+0000` → `2026-10-27T03:30:33.747146837+0000`
- Monotonic uptime: `62218.94` → `62218.95`
- Combined output: empty.

Ownership is clear for this snapshot; re-resolve identity and owners immediately before any future approved probe.

## Kernel log availability

### dmesg

- Command: `dmesg --time-format iso | tail -n 60` with `pipefail` enabled
- Exit: 1
- UTC: `2026-10-27T03:30:33.794899798+0000` → `2026-10-27T03:30:33.799094880+0000`
- Monotonic uptime: `62219.00` → `62219.01`
- Combined output:

```text
dmesg: read kernel buffer failed: Operation not permitted
```

### journalctl

- Command: `journalctl -k --since '10 minutes ago' --no-pager -n 100`
- Exit: 0
- UTC: `2026-10-27T03:30:33.748081558+0000` → `2026-10-27T03:30:33.753792948+0000`
- Monotonic uptime: `62218.96` → `62218.96`
- Combined output:

```text
Hint: You are currently not seeing messages from other users and the system.
      Users in the 'systemd-journal' group can see all messages. Pass -q to
      turn off this notice.
-- No entries --
```

Kernel events are unavailable to this user context. The empty journal result is not evidence that USB was clean.

## Existing software identifiers (read-only)

- Command: `sha256sum experiments/updi_rca/src/updi_rca/cli.py experiments/updi_rca/src/updi_rca/probes.py experiments/updi_rca/src/updi_rca/identity.py experiments/updi_rca/src/updi_rca/runner.py experiments/updi_rca/src/updi_rca/board_swap.py experiments/updi_rca/pyproject.toml experiments/updi_rca/uv.lock`
- Exit: 0
- UTC: `2026-10-27T03:30:42.108022630+0000` → `2026-10-27T03:30:42.115414499+0000`
- Monotonic uptime: `62227.32` → `62227.32`
- Output:

```text
fe1776dc56695d713312f42c304b4a977cfc2b0d0886b59b49697eba5ed5d1e9  experiments/updi_rca/src/updi_rca/cli.py
db783316cc16653d12b90040507a89d178622374bb61ec87fecd5a2f3fe347e8  experiments/updi_rca/src/updi_rca/probes.py
0f905d6e7cd391575753ed7239ca8b97fab7e209cc58366b55017e447788192e  experiments/updi_rca/src/updi_rca/identity.py
7f737b0fe624967829dd51525cc0256cfd6c847840710eacc078c1ff9f6f8997  experiments/updi_rca/src/updi_rca/runner.py
3c5b2b0c48d82be3203048eba0c417f8b16d722ff19f9c8070d2b9490fdde621  experiments/updi_rca/src/updi_rca/board_swap.py
5142dc8be694bfa7fdc74ebbcb595fa39527d8f237a9117cc17b7d9762e69996  experiments/updi_rca/pyproject.toml
cc6f9f5458543bf68a64ee9380bc6cf151b4a2102613a398335b35cd7a873d5c  experiments/updi_rca/uv.lock
```

- Command: `git status --short -- experiments/updi_rca/src/updi_rca/cli.py experiments/updi_rca/src/updi_rca/probes.py experiments/updi_rca/src/updi_rca/identity.py experiments/updi_rca/src/updi_rca/runner.py experiments/updi_rca/src/updi_rca/board_swap.py experiments/updi_rca/pyproject.toml experiments/updi_rca/uv.lock`
- Exit: 0; output: these seven paths were reported as untracked (`??`) in the shared working tree at inventory time. This lane did not edit them. The hashes identify exactly the source/configuration bytes seen at this snapshot.

## Probe gate and proposed command (not run)

No target probe is authorized yet. After the coordinator's host gate and explicit approval, the existing one-attempt read-only CLI syntax is:

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/sib_001.json --baud 38400 --timeout 1.0
```

This command was not invoked. Its planned raw output is under the Q lane's allowed epoch directory; do not count it as evidence until separately approved and executed. Target fingerprint remains `UNKNOWN_TARGET`.
