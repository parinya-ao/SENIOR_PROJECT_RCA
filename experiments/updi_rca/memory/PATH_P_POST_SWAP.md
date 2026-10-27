# RCA_POST_SWAP_01 — Lane P inventory

Direct-host inventory was captured at 2026-10-27 03:30 UTC. The user reports the PCB-only swap is complete and current endpoints are P→Y, Q→X. This lane did not move or touch hardware. The approved POST-001 SIB-only run later opened and closed P's serial connection once per attempt. The physical label is user-reported; target silicon identity remains `UNKNOWN_TARGET`.

## Current P mapping

The exact expected udev identity resolves uniquely:

- `ID_PATH=pci-0000:00:14.0-usb-0:4:1.0`
- Stable locator: `/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0`
- Current tty alias: `/dev/ttyUSB0` (recorded only as a current locator, never used as hardware identity)
- Sysfs DEVPATH: `/devices/pci0000:00/0000:00:14.0/usb3/3-4/3-4:1.0/ttyUSB0/tty/ttyUSB0`
- USB attributes: VID:PID `10c4:ea60`, serial `0001` (duplicate across adapters), product `CP2102 USB to UART Bridge Controller`, bus 3, device 21, root port 4, `cp210x`, 12 Mbps.
- Physical target: Y per user report; unique AVR target fingerprint UNKNOWN.

The existing `updi_rca.cli inventory` output resolves exactly one P adapter at the stable ID_PATH and reports `target_identity=UNKNOWN_TARGET`. Q remains at ID_PATH `pci-0000:00:14.0-usb-0:1:1.0`; the CLI reports its current tty `/dev/ttyUSB1` and USB device 22. `lsusb -t` shows the two CP210x interfaces at bus 3 root ports 1 and 4. Device numbers changed since the prior freeze, so current bus/device values are re-inventoried rather than inherited.

## Ownership and host observations

- `fuser -v` on P's stable by-path exited 1 with empty output: no owner reported.
- `lsof -nP` exited 1 with no device rows; stderr warns it cannot stat tracefs, so retain that limitation.
- `pgrep -a -f '[u]pditerm'` and `pgrep -a -f '[a]vrdude'` each exited 1 with no output.
- `journalctl -k --since '15 minutes ago'` returned `-- No entries --`; stderr says this user cannot see all system journal messages. This is a limited negative observation.
- `/sys/class/power_supply` exposed no files. Current host/target power state and target power source are UNKNOWN; no power controls or services were changed.
- Read-only command records include exact command argv, stdout, stderr, exit code, UTC start/end, `/proc/uptime` start/end, and SHA-256 for each stream in `evidence/RCA_POST_SWAP_01/path_p/commands/`.

One inventory invocation without `PYTHONPATH=experiments/updi_rca/src` exited 1 because Python could not import `updi_rca`; it did not open a port. The corrected existing CLI inventory invocation with the project `PYTHONPATH` exited 0 and is retained alongside the failed invocation.

## Tool versions and source hashes

- `uv 0.13.5`
- `Python 3.14.8`
- `pySerial 3.5`; installed module SHA-256 `5dec897fdef45a0eaf63eacda1e01d62e1e75490302584ae0238f75376592344`
- SHA-256 for the current `probes.py`, `runner.py`, `identity.py`, `cli.py`, and `pyproject.toml` is recorded by the `source_hashes` command output.

## POST-001 SIB-only result

The parent approved POST-001 after the fresh direct-host preflight returned `PREFLIGHT=GREEN` at 2026-10-27 03:32 UTC. Exactly 30 invocations of the existing one-attempt CLI ran sequentially on the unchanged user-reported P→Y pairing. Run ID: `POST-001-P-20261027T033205Z`. The existing CLI re-resolved the stable ID_PATH for each invocation, opened exclusively, performed only two BREAK synchronization bytes plus SIB, and closed the port. There were no retries, physical changes, resets, programming keys, control reads, ACC reads, or writes.

| Measure | Result |
|---|---:|
| Attempts | 30/30 completed |
| Full SIB successes | 0/30 (0%) |
| Overall failure rate | 30/30 (100%); Wilson 95% CI 88.65%–100% |
| Failure stage `LOCAL_ECHO` | 1/30: TX `00`, echo `80`; BREAK2/SIB were **not reached** |
| Failure stage `UPDI_CONTROL_RESPONSE` | 29/30 after exact BREAK1, BREAK2, and exact `55e6` SIB-request echo |
| SIB requests / responses | 29 transmitted; 0 response bytes in all 29 response reads |
| Conditional missing SIB response | 29/29; Wilson 95% CI 88.30%–100% |
| Latency median / p95 | 1145.145 ms / 1149.716 ms |
| Latency min / max | 108.194 ms / 1149.867 ms |

Echo distribution: BREAK1 was `00` in 29/30 and corrupted as `80` in 1/30; BREAK2 was exact `00` in 29/29 attempts where reached and not reached once; SIB request `55e6` was exact-echoed in 29/29 where reached and not reached once. The first failure's missing BREAK2 and SIB events are not empty echoes. No SIB response bytes were returned; raw `values.SIB` is absent in all attempts. This separates the one local-echo anomaly from the 29 post-echo response failures.

The first three outcomes were: attempt 001 `LOCAL_ECHO` (108.194 ms; echoed `80` for `00`); attempt 002 `UPDI_CONTROL_RESPONSE` (1142.546 ms; exact sync/request echoes, empty SIB response); attempt 003 same stage (1145.199 ms). Attempts 028, 029, and 030 all ended at `UPDI_CONTROL_RESPONSE` with exact sync/request echoes and no SIB response (1143.514, 1143.612, and 1145.207 ms).

Run wall interval: `2026-10-27T03:34:16.164184095Z` through `2026-10-27T03:34:54.288473544Z`; `/proc/uptime` changed from `62441.37` to `62479.50`. The shell loop completed all 30; outer exit was 0. Each existing CLI command exited 1 because its read-only probe failed. Per-command stdout/stderr, exit code, UTC/uptime timestamps, hashes and unchanged raw JSON are retained under `evidence/RCA_POST_SWAP_01/path_p/post001_20261027T033205Z/`.

Postflight at 03:35:19 UTC reconfirmed the same ID_PATH and symlink. `fuser` exit 1/no output and `lsof` exit 1/no device rows indicate the port is closed; lsof again warned about tracefs. The postflight pgrep checks matched the enclosing inline shell command text and are not treated as process evidence; the clean preflight pgrep results are retained. No additional probe has been run since POST-001; await parent direction.

## Probe boundary

The existing one-attempt SIB CLI form used for each invocation was:

```text
env PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:4:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_p/post001_20261027T033205Z/raw/POST-001-P-20261027T033205Z-001.json --baud 38400 --timeout 1.0
```

The output filename incremented from `001` through `030`.

POST-001 has now been authorized and completed. Do not run the command again without a new parent batch approval. No firmware, ACC, control-space, reset, or programming action was performed.

## Evidence integrity

- Direct-host capture script: `evidence/RCA_POST_SWAP_01/path_p/capture_inventory.sh` (inventory-only; it does not open serial).
- All outputs are under `evidence/RCA_POST_SWAP_01/path_p/commands/`; the first failed CLI inventory and corrected successful inventory are both retained.
- `evidence/RCA_POST_SWAP_01/path_p/SHA256SUMS` is the preserved inventory-only manifest for 59 files; SHA-256 `37a39e67761fa1f00c846e6eb8e5924b7c1c4e726356b7def76f4c99ae6579b8`.
- `evidence/RCA_POST_SWAP_01/path_p/SHA256SUMS_POST001` covers all 237 inventory and POST-001 evidence files, including 30 raw probe records and per-attempt command captures; all entries verify with `sha256sum -c`. Manifest SHA-256: `55b9bfe2adeefaf8f159ce798bfc9e1b52312b9497b51ae6188f8efaf0bb1f61`. It excludes itself and this note.
