# Lane B

## Adapter observation

- Observed: 2026-10-26
- Stable lane selector: `ID_PATH=pci-0000:00:14.0-usb-0:1:1.0`
- Sysfs path: `/sys/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0/ttyUSB1/tty/ttyUSB1`
- USB VID:PID: `10c4:ea60`
- Manufacturer/product: `Silicon_Labs` / `CP2102_USB_to_UART_Bridge_Controller`
- USB serial: `0001` (duplicated by the other adapter; not a unique identity)
- `/dev/serial/by-path`: `pci-0000:00:14.0-usb-0:1:1.0-port0`
- Current tty locator at observation: `/dev/ttyUSB1` (ephemeral; never use as board identity)

## Target and probe state

- Target identity: `UNKNOWN_TARGET`; SIB initialization failed before any AVR identity response, so signature, REVID, and serial reads were not attempted.
- Identity run: `laneB-20261026T163048Z` at 38400 baud.
- Probe: one existing-harness upstream SIB attempt using the dynamically re-resolved by-path link.
- Preflight: exactly one adapter matched the assigned ID_PATH; the current by-path target matched the sysfs mapping; `fuser` reported no owner.
- Outcome: failed during initialization at `LOCAL_ECHO`; the first transmitted BREAK byte was `00` at 300 baud, expected one echo byte, received zero bytes. The bounded harness exited 1; no SIB or target response was observed.
- Raw evidence: `evidence/raw/laneB-20261026T163048Z/lane_b/identity-sib.json`
- SHA-256: `62dfb23d319a30f691c95603a69d01c1b32b8c422af9b68fcc2c73bfbf612e31`
- Serial port opened: yes, for the single bounded identity probe only; it was closed by the harness after failure.
- Firmware/fuse writes: none.
- Stopped after this first failure per probe boundary; no retry and no signature/REVID/serial probes.

## Fresh independent SIB sample

- Timestamp: `2026-10-26T16:47:53.094727+00:00`
- Run: `laneB-20261026T164740Z`; preflight again resolved exactly one adapter with the assigned ID_PATH, confirmed the by-path target matched the current sysfs mapping, and `fuser` found no owner.
- Probe: one new upstream SIB attempt at 38400 using the stable by-path link.
- Outcome: failed at `LOCAL_ECHO` during initialization, same stage as the earlier sample: TX `00` at 300 baud, expected one local echo byte, received none. Exit 1; SIB/signature/REVID/serial were not reached.
- Raw evidence: `evidence/raw/laneB-20261026T164740Z/lane_b/identity-sib.json`
- SHA-256: `d576a51ccd350b4637518405d431101d84b2570e51650a41ccc5bae5d5d2c8a3`
- Teardown: the harness closed the OS handle in `finally` with no extra recovery/protocol traffic.
- Firmware/fuse writes: none. No further retry or identity read performed.

## Phase 1 baseline disposition

- 100-attempt Phase 1 SIB/control baseline: **not started** (0/100 attempts for each condition).
- Reason: source review found the available upstream/oracle initialization path writes UPDI `CTRLB`/`CTRLA`, and normal close may write `UPDIDIS`. The required baseline forbids target/register writes, so this harness is not safe for that baseline.
- Prior SIB attempts both stopped before any STCS operation: captured raw events contain only the initial BREAK `00` TX and an empty echo. No recovery, register write, reset, key, fuse, or flash operation occurred.
- Current disposition: baseline blocked at `LOCAL_ECHO`; resume only with a proven no-write probe path or a coordinator-approved non-writing implementation. No additional hardware probes were run after the write-path concern was raised.

## Strict read-only Phase 1 baseline

- Run: `baseline-20261026T171633Z-88c741a8`; adapter `ID_PATH=pci-0000:00:14.0-usb-0:1:1.0`, USB serial `0001`; target remains `UNKNOWN_TARGET`.
- Preflight resolved exactly one adapter by ID_PATH, confirmed `/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0` matched its current sysfs mapping, and `fuser` reported no owner.
- Policy/backend: coordinator-provided strict read-only harness; two BREAK synchronization bytes, then only SIB or LDCS reads if synchronization succeeds; `exclusive=True`; close is OS-handle close only. No STCS, STS, key, reset, flash, fuse, or NVM write.
- SIB condition: N=100, 0 pass, 100 fail (100% `LOCAL_ECHO`); median latency 1060.951 ms, p95 1064.443 ms; Wilson 95% CI for success proportion 0.000%–3.699%.
- Control condition: N=100, 0 pass, 100 fail (100% `LOCAL_ECHO`); median latency 1061.433 ms, p95 1064.452 ms; Wilson 95% CI for success proportion 0.000%–3.699%.
- Stage detail: every attempt failed during BREAK synchronization before the SIB or any control-space request. In SIB mode the first BREAK echo was empty in 86/100 and exact (`00`) in 14/100; in control mode it was empty in 85/100 and exact in 15/100. Each of the 29 attempts with an exact first echo then sent the second BREAK and received an empty echo. No SIB request (`55 e6`), LDCS request, or target response was transmitted/observed.
- Per-attempt raw evidence and path→SHA-256 mapping are in the two condition summary JSONs; all 100 raw hashes per condition were recomputed and matched. SIB summary SHA-256: `4140151eaefcb349ca412dec8613d360cb8cba387a98bada83a5fd5632b9ee50`. Control summary SHA-256: `f764befb130009392fcdaf937c0ed2c81ea8af3e437ac1a0918120cb898b9ab6`.
- Evidence directory: `evidence/raw/baseline-20261026T1655Z/lane_b/`.
- The kernel log query for 2026-10-26 17:16:33–17:20:34 UTC returned no matching USB/CP210x/disconnect/EPROTO/EILSEQ/error lines. No usbmon trace was captured; the kernel query is not an analog signal measurement.
- Interpretation: this lane cannot provide a board-target SIB/control baseline because the strict read-only probe never passed local echo synchronization. This confirms a repeatable pre-target boundary on this adapter path, not a target-response failure or a physical component cause.

## RCA_CROSSOVER_01 pre-crossover confirmation

- Run: `baseline-20261026T211832Z-88c741a8`; UTC wall interval `2026-10-26T21:18:32.106295+00:00` to `2026-10-26T21:18:54.027076+00:00`; monotonic duration 21.920764 s; CLI exit 1 because all probes failed.
- Preflight: VID:PID `10c4:ea60`; USB serial `0001` (duplicate count 2); ID_PATH `pci-0000:00:14.0-usb-0:1:1.0`; sysfs `/sys/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0/ttyUSB1/tty/ttyUSB1`; by-path `/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0`; current tty locator `/dev/ttyUSB1`. Exactly one adapter matched, by-path matched the sysfs mapping, and fuser found no owner.
- SIB: N=10, 0 pass/10 fail, all `LOCAL_ECHO`; median 1061.647 ms, p95 1064.128 ms; Wilson 95% success interval 0.000%–27.754%.
- Control snapshot: N=10, 0 pass/10 fail, all `LOCAL_ECHO`; median 1061.556 ms, p95 1063.475 ms; Wilson 95% success interval 0.000%–27.754%.
- SIB first BREAK echo: empty 8/10, exact `00` 2/10; both then failed on the second BREAK with empty echo. Control first BREAK echo: empty 9/10, exact `00` 1/10; that second BREAK echo was empty. No SIB (`55 e6`) or LDCS request/target response occurred. Target remains `UNKNOWN_TARGET`.
- Exact command, stdout, empty stderr, exit, wall/monotonic timing, and preflight are captured under `evidence/raw/RCA_CROSSOVER_01/pre/lane_b/`. Attempt raw files and per-attempt hashes are recorded in the condition summaries; all 20 hashes were recomputed and matched.
- Summary SHA-256: SIB `d5701554adda8b9227632eece9f5513cf85d9c15f2b4fa33a7b23d67de690997`; control `0ae0e694396525806064ed02a6de72e4b472f28b719a28acd379895ffa8c037b`.
- Command SHA-256: `700dca875d1a45a73834adb3d55ee9f5dc53764e11203b1d988067955f54a693`; stdout SHA-256: `aa9f27a65727670155d425fe7882e04aeba968a6a330fac5906ee0756a2be7fe`; empty stderr SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- This remains an adapter-path local echo failure before target communication; it does not establish a target-side or physical board cause.
