# RCA_BOARD_SWAP_01 — Lane P state

Captured 2026-10-27 UTC. Scope: external Path P only, stable udev `ID_PATH=pci-0000:00:14.0-usb-0:4:1.0`. No interaction with Lane Q and no shared CSV/report/source edits.

## Mapping and inventory

The coordinator's [SWAP_FREEZE.md](SWAP_FREEZE.md) records the user's confirmation that safe isolation and PCB-only endpoint swap are verified and the physical boards are labeled X/Y. Original pairing remained P→X throughout this lane's PRE run. Physical target fingerprint remains `UNKNOWN_TARGET`; X is the user-applied physical label, not a silicon identity.

- VID:PID `10c4:ea60`; USB serial `0001` is duplicated and not used as identity.
- Current tty at capture: `/dev/ttyUSB0` (ephemeral alias only).
- Stable locator: `/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0`.
- Sysfs tty path: `/sys/devices/pci0000:00/0000:00:14.0/usb3/3-4/3-4:1.0/ttyUSB0/tty/ttyUSB0`; USB bus 3, device 18, root port 4, CP210x driver, 12 Mbps.
- udev also exposes a `usbv2` alias to the same tty. The first inventory pass detected two by-path aliases and correctly skipped owner checks; it is preserved under `commands_attempt0_ambiguous_aliases/`. The rerun selected the exact non-`usbv2` locator derived from the expected ID_PATH, resolved exactly one adapter, and proceeded.
- `lsusb -t` placed the two CP210x adapters at bus 3 root ports 1 and 4. A 15-minute pre-inventory kernel query returned no visible entries; journald noted that this user cannot see all system messages. `/sys/class/power_supply` exposed no files, so power-source state is UNKNOWN in this lane inventory. The coordinator freeze separately records host mains online=1 and target power UNKNOWN.

Ownership preflight immediately before the batch: `fuser -v <stable by-path>` exit 1, no output; `pgrep -a -f '[u]pditerm'` and `pgrep -a -f '[a]vrdude'` both exit 1 with no output. The initial `lsof` check exited 1 with no file rows but warned that tracefs could not be statted. After the batch, stable by-path and udev still resolved to the same Lane P ID_PATH; `fuser` exited 1/no output and `lsof` exited 1/no file rows (same tracefs warning). The postflight JSON's `pgrep` commands matched their own enclosing heredoc text and are invalid as process evidence; rely on the clean preflight checks plus final fuser/lsof ownership results.

## Approved PRE SIB batch

Coordinator approved exactly 20 SIB-only attempts on the original P→X pairing after the 92-test TDD gate was reported GREEN. No PCB movement occurred. The command recorded in `pre/command.json` was:

```text
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python experiments/updi_rca/evidence/RCA_BOARD_SWAP_01/path_p/run_pre_campaign.py --id-path pci-0000:00:14.0-usb-0:4:1.0 --attempts 20 --baud 38400 --timeout 1.0 --target X --pairing P-to-X
```

Run ID: `swap-pre-P-20261027T015802555251Z`. Started `2026-10-27T01:58:02.361274Z`, ended `2026-10-27T01:58:26.179020Z`, wall duration 23.818 s. The command returned exit 1 because the completed campaign contained failures; `status=COMPLETE`, 20/20 attempts were made, and no retry/extra attempt occurred.

| Measure | Result |
|---|---:|
| Attempts | 20 |
| SIB response pass | 0/20 (0%) |
| Missing SIB response | 20/20 (100%), stage `UPDI_CONTROL_RESPONSE` |
| Exact BREAK1 / BREAK2 local echoes | 20/20 / 20/20 |
| Exact SIB request local echo | 20/20 (`55e6`) |
| SIB response bytes | 0/20 (all 32-byte response reads empty) |
| Failure rate Wilson 95% interval | 83.89%–100% |
| Latency median / p95 | 1146.775 ms / 1148.088 ms |

Each attempt sent two `00` synchronization bytes at 300 baud, then the SIB request at nominal 38400 baud. Both sync bytes and the SIB request echoed exactly; the 32-byte SIB response was absent until the unchanged 1.0-second timeout. This is a response-stage failure after exact local echo, distinct from `LOCAL_ECHO`. The strict harness used exclusive open and close per attempt and the existing `run_sib_probe` / `run_campaign`; `_live_adapter` resolves the stable ID_PATH before each open. There were no control reads, STCS/STS writes, programming keys, reset commands, NVM operations, firmware/fuse changes, or board movement.

The campaign's bounded kernel window was `2026-10-27 01:56:02 UTC` through `02:00:26 UTC`; the query returned `-- No entries --` for this user's visible journal and printed the limited-visibility hint. Final owner and ID_PATH observations are in `pre/postflight.json`.

The coordinator classified Path P as `NON_STATIONARY` relative to its earlier passing baseline and marked crossover `NO-GO`. No crossed pairing or additional probe was run. Wait for coordinator direction and target-power status; this lane must not perform further hardware activity until a new explicit batch is approved.

## Evidence integrity

- Per-attempt JSON: `evidence/RCA_BOARD_SWAP_01/path_p/pre/raw/swap-pre-P-20261027T015802555251Z-0001.json` through `...-0020.json`.
- `pre/campaign_summary.json` maps every attempt to its SHA-256; all 20 hashes were recomputed and matched.
- `pre/source_hashes.json` records SHA-256 of `probes.py`, `runner.py`, `identity.py`, `classify.py`, `SWAP_PLAN.md`, `SWAP_FREEZE.md`, and this lane's runner at execution.
- Inventory command records retain exact argv, stdout, stderr, exit codes, UTC and monotonic timestamps, and output hashes under `commands/` (with the initial conservative resolver pass preserved separately).
- `evidence/RCA_BOARD_SWAP_01/path_p/SHA256SUMS` covers 60 evidence files and all 60 entries pass `sha256sum -c`. Manifest SHA-256: `29e5e16acb3edf285c265519360f11aa10e1d5cf4fa02cbe8a257776778c3357`. The manifest does not include itself or this Markdown note.
