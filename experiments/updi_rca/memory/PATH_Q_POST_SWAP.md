# Path Q — RCA_POST_SWAP_01 crossed-untouched

Updated 2026-10-27 03:38 UTC. User reported the PCB-only swap complete with P→Y and Q→X; no cable, power, or other hardware changes. Q external adapter path is `ID_PATH=pci-0000:00:14.0-usb-0:1:1.0` (VID:PID `10c4:ea60`, duplicated serial `0001`, not identity). At pre/post snapshots, current tty locator was `/dev/ttyUSB1`, USB Bus 3 Port 1 Device 22. The other CP210x remained Bus 3 Port 4 Device 21. User's physical target label is X; AVR signature/SIB identity remains `UNKNOWN_TARGET`.

## Batch result

Coordinator authorized 30 SIB-only CLI attempts after the host gate. Batch `POST-00130` is complete: 30/30 attempts exited at `LOCAL_ECHO` (100%, Wilson95 88.65%–100%). Median probe latency 1061.754 ms; nearest-rank p95 1063.539 ms. There were 36 BREAK TX events: 24 attempts failed echo on the first BREAK; 6 had an exact first echo `00` and then failed echo on the second BREAK. Across 36 BREAK echo reads, 6 were exact and 30 empty. First-BREAK echo success was 6/30 (20.0%, Wilson95 9.51%–37.31%); second-BREAK echo success after first passed was 0/6 (Wilson95 0%–39.03%). The SIB command was never sent; response bytes and target identity were never obtained. This result is at the local half-duplex echo/sync stage, not a target-response failure. No controls, ACC, resets, keys, target writes, fuses, flash, or BOD changes occurred.

## Evidence

- [Host inventory](../evidence/RCA_POST_SWAP_01/path_q/host_inventory.md) — SHA-256 `af987be92228f9fe9a01efc9dfaf03320c64fcf10f9db4eee5e00e15bf24c444`. It records ID_PATH/udev/sysfs, USB topology, current tty locator, owner checks, kernel log access limits, and software hashes.
- [POST-00130 manifest](../evidence/RCA_POST_SWAP_01/path_q/POST-00130/manifest.md) — SHA-256 `22bc74122a96c0b2f0fdbf89c1af5e19a188a753ac5d2daa4555b8a6c70dd35a`. It records all exact CLI invocations and returned outputs, exit statuses, timings, stages, BREAK event counts and per-attempt SHA-256.
- 30 raw JSON files are unchanged under `../evidence/RCA_POST_SWAP_01/path_q/POST-00130/`; recomputed on-disk hashes matched CLI output 30/30.
- Post-batch ID_PATH remained Q; tty locator/by-path, Bus 3 Port 1 Device 22 remained stable. No USB re-enumeration observed. Post-batch `fuser` listed no owner; `lsof` showed only the tracefs warning.
- Kernel buffer access remained unavailable (`dmesg` permission denied; unprivileged journal query empty), so this is not evidence that USB was clean during the batch.
- Relevant code hashes at batch time: `cli.py` fe1776dc56695d713312f42c304b4a977cfc2b0d0886b59b49697eba5ed5d1e9; `probes.py` db783316cc16653d12b90040507a89d178622374bb61ec87fecd5a2f3fe347e8; `identity.py` 0f905d6e7cd391575753ed7239ca8b97fab7e209cc58366b55017e447788192e; `runner.py` 7f737b0fe624967829dd51525cc0256cfd6c847840710eacc078c1ff9f6f8997. Lane Q changed no source.

All 30 approved attempts are complete, port is closed, and the post-batch ownership snapshot is clear. No further probes or confirmation batch were run; await coordinator instruction. Historical RCA_BOARD_SWAP_01 Q PRE remains 0/20 and is not part of POST-00130.

