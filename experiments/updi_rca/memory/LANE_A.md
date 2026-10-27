# Lane A

## Adapter mapping (read-only; target port not opened)

- Assigned identity: `ID_PATH=pci-0000:00:14.0-usb-0:4:1.0`
- Current tty locator at inventory time: `/dev/ttyUSB0` (ephemeral; not a board identity)
- Sysfs path: `/sys/devices/pci0000:00/0000:00:14.0/usb3/3-4/3-4:1.0/ttyUSB0/tty/ttyUSB0`
- USB VID:PID: `10c4:ea60`
- Manufacturer/product: `Silicon_Labs / CP2102_USB_to_UART_Bridge_Controller`
- USB serial: `0001` (duplicated by the other adapter; not unique)
- Stable by-path link: `/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0`
- Alternate kernel by-path link: `/dev/serial/by-path/pci-0000:00:14.0-usbv2-0:4:1.0-port0`
- by-id link: `/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0` (not unique)
- Target identity: `UNKNOWN_TARGET` pending coordinator authorization for safe identity reads.

No serial open or UPDI transaction was performed. Awaiting the coordinator's identity-resolver tests and bounded probe authorization.

## Authorized identity probe attempt

- Run ID: `identity-20261026T163044Z`
- Preflight re-resolved exactly one adapter by the assigned `ID_PATH` and its current by-path link.
- `fuser` found the port already owned; no SIB or other UPDI command was issued.
- Owner observed read-only with `ps`: PID `166282`, command `external/upditerm/upditerm.py /dev/ttyUSB0 38400` (parent PID `166263`).
- Result: `PORT_BUSY`; target remains `UNKNOWN_TARGET`. No probe evidence file exists.
- Do not terminate or displace the existing process; await coordinator resolution and re-run identity/ownership checks before any probe.

## Authorized identity-only probes

Run ID: `identity-20261026T164124Z`. Before each probe the resolver found exactly one adapter at the assigned `ID_PATH`, selected its current by-path link, and found no owner. The diagnostic harness closed the OS handle after each bounded command.

### SIB — pass

- Timestamp: `2026-10-26T16:41:36.810823Z`; baud: 38400; attempts: 1; result: 1/1 pass; latency: 122.696 ms (first TX to final recorded event).
- Local echo: 9/9 exact; control responses: 5/5 one-byte reads; SIB: 32/32 bytes.
- Literal SIB: `    AVR P:2D:1-3M2 (A7.KV001.0)\0`. This is retained as a raw label; it is not treated as a unique board identity or a decoded serial number.
- Control snapshot from this SIB run: `CS02=00`, `CS03=08`, `CS05=10`, `CS07=02`, `CS0B=82`.
- Raw files: `evidence/raw/identity-20261026T164124Z/lane_a/sib.json` (SHA-256 `610f3aff4d1ed536311faf3ce99233e778b017837d66cdfb6b2b3b2d53c9d86e`), `.stdout` (`78b6503cdaad00abd36d2018326a16f71bf03147946fe223f92dc2acbdef4dbb`), `.stderr` (empty; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).

### Signature byte 0 (`0x1100`) — failed during link initialization

- Timestamp: `2026-10-26T16:42:08.905314Z`; baud: 38400; attempts: 1; result: 0/1 completed; latency: 1006.782 ms.
- The four host transmissions had exact local echoes. The first anomaly was `oracle init_datalink: RuntimeError: missing response: expected 1 bytes received`; the final response was empty (0/1 byte). The requested signature address was not read.
- Classification: missing UPDI control response during oracle link initialization after exact echo. This is not a local-echo error and is not evidence of an ACC data failure.
- Stop rule applied: no retries, no signature bytes 1–2, no REVID or serial-row reads. Target identity remains `UNKNOWN_TARGET`.
- Raw files: `evidence/raw/identity-20261026T164124Z/lane_a/signature_1100.json` (SHA-256 `ee243af3ff4e573e3e1f879464503e042134b865d5d4d8d8179c8ba07ce83aa8`), `.stdout` (`6adbe8f6d8ea95107f2a478884b1965607349114ff9a0f2de9ccf7aa0c55b816`), `.stderr` (empty; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
- No flash, fuse, target-data, or reset request was issued. UPDI setup did issue control-space configuration writes as recorded in the raw event log.

## Unverified terminal text

The user supplied repeated `HEYYY fuckkkk` text preceding a forced `SIGKILL`. Its timestamp, tty, board identity, and byte-level source are unverified. It is not counted as an OCD message, a boot marker, a reset, or evidence of cause.

## Post-SIGKILL one-sample status snapshot

Run ID: `snapshot-20261026T164555Z`. The target state may have changed between the kill and this snapshot. This sample cannot establish what was pending at kill time.

### Control-space snapshot — pass

- Timestamp: `2026-10-26T16:46:09.565026Z`; baud: 38400; one bounded open/close; exit 0.
- Preflight: exactly one adapter resolved at the assigned `ID_PATH`; current by-path link was used; `fuser` found no owner.
- All 16 transmitted sequences had exact local echoes; all 13 requested LDCS responses returned; latency 144.306 ms.
- `ASI_OCD_STATUS` (`LDCS 0x05`) raw: `0x10` (`OCDMV` set, `OCD_STOPPED` clear under the vendored upditerm masks).
- `ASI_SYS_STATUS` (`LDCS 0x0B`) raw: `0x82` on both reads. Preserved without assigning meaning to undocumented bits.
- No KEY/reset/RUN or host virtual-UART writes. `ASI_OCD_MESSAGE` was not read or consumed; actual message bytes are unknown.
- Raw files: `evidence/raw/snapshot-20261026T164555Z/lane_a/control.json` (SHA-256 `3baaac1abe20aecf6a3781c3ae1b0c0d5cbf505327a9661d7d3e0dcf6727a55f`), `.stdout` (`bafedb8fac877e13abad85ceacd791c51a4569ed25af78eb64c7ccdf23efa845`), `.stderr` (empty; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).

### GPIOR2 / `FLAG_RX` — pass

- Timestamp: `2026-10-26T16:46:21.397479Z`; baud: 38400; one bounded open/close; exit 0.
- Preflight was repeated and again resolved the assigned `ID_PATH` uniquely with no port owner.
- Read address `0x001E` returned raw `0x03`; the vendored `upditerm.py` defines `FLAG_ENABLE=0x01` and `FLAG_RX=0x02`, so both bits were set in this one sample.
- All 9 transmitted sequences had exact echoes and all 6 requested responses returned; latency 113.253 ms. No host data write occurred.
- Raw files: `evidence/raw/snapshot-20261026T164555Z/lane_a/data_001e.json` (SHA-256 `555c7421fa3333ab163e77f5e332a5fef9d131484d1fed51b9686d4911fb4e2a`), `.stdout` (`80233ac944bf6c6b6540b18f7d6cc7bddf22cd0cf776df5afd1c0e24aa2d1156`), `.stderr` (empty; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).

These post-kill reads show `FLAG_RX` and `OCDMV` were both set when sampled, but they do not establish whether an OCD message was present at the earlier forced termination, whether it was genuine target output, or what caused the prior terminal text. No message byte was consumed.

## Final A in non-destructive SIB A/B/A discriminator

- Run ID: `aba-20261026T164816Z`; timestamp `2026-10-26T16:48:28.001896Z`; baud 38400.
- Immediate preflight resolved exactly one adapter at Lane A's assigned `ID_PATH`, used its current by-path link, and found no port owner.
- One bounded SIB probe passed (1/1); 9/9 exact echoes, 5/5 one-byte control responses, and 32/32 SIB bytes; latency 122.840 ms. OS handle closed after the run.
- SIB bytes exactly match Lane A's earlier sample: `2020202041565220503a32443a312d334d32202841372e4b563030312e302900` (`    AVR P:2D:1-3M2 (A7.KV001.0)\0`).
- Raw files: `evidence/raw/aba-20261026T164816Z/lane_a/sib.json` (SHA-256 `eb6d82c9ce86a8b7dd11e6d07147d26fe7b77b4368b8370f719da68d83f9956c`), `.stdout` (`78b6503cdaad00abd36d2018326a16f71bf03147946fe223f92dc2acbdef4dbb`), `.stderr` (empty; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
- This is one identity-linked A/B/A observation only; it does not make the SIB a unique board identity or establish a causal failure mechanism.

## Phase 1 baseline safety stop

- Requested Lane A baseline: 100 SIB attempts and 100 selected control snapshots at 38400, each as a bounded open/probe/close.
- No baseline attempts were started: SIB `0/100`; control snapshots `0/100`. No port was opened for this batch and no campaign raw files were created.
- The existing `experiments/updi_rca/src/updi_rca/probes.py` wrapper calls `tools/updi-diagnose.py`. Its `upstream` backend constructs `UPDI`; `UPDI.__init__` sends `STCS CTRLB=CCDETDIS`, and a clean `UPDI.close()` sends `STCS CTRLB=UPDIDIS`. The oracle backend also sends `STCS` to `CTRLB` and `CTRLA` during initialization. These are control-space writes, which conflict with the explicit no-write baseline constraint.
- Stopped before serial open pending a validated no-write probe path. No reset, programming key, target data write, fuse write, or flash operation was issued for this baseline batch.

## Phase 1 strict read-only baseline

- Run ID: `baseline-20261026T171644Z-1a031f37`; adapter `ID_PATH=pci-0000:00:14.0-usb-0:4:1.0`; current tty at start `/dev/ttyUSB0` (ephemeral locator only); target identity remains `UNKNOWN_TARGET`.
- Preflight resolved exactly one adapter from `ID_PATH` and its `/dev/serial/by-path` link; `fuser` reported the port unowned. The CLI then re-resolved that `ID_PATH` before each probe. Each of the 200 attempts opened, performed one bounded probe, and closed.
- Write policy: two 300-baud BREAK sync bytes, then SIB or LDCS read commands only. No STCS, STS, programming/debug key, reset, target-memory write, fuse write, or flash operation was issued. The SIB request uses the protocol's read-only SIB opcode, not a programming key.

### SIB condition

- N=100; pass=100; fail=0; pass rate=100%; Wilson 95% interval for success: 96.30%–100.00%; failure-stage counts: none.
- Exact local echo: 300/300 frames (two BREAK syncs and one SIB request per attempt); target response: 100/100 responses, 3,200/3,200 bytes. No echo or response failure.
- Latency median=157.092 ms; p95=159.884 ms.
- SIB response was identical in all attempts: `2020202041565220503a32443a312d334d32202841372e4b563030312e302900` (`    AVR P:2D:1-3M2 (A7.KV001.0)\0`). This is not a unique board identity.

### Control-space condition

- N=100 snapshots; pass=100; fail=0; pass rate=100%; Wilson 95% interval for success: 96.30%–100.00%; failure-stage counts: none.
- Exact local echo: 1,500/1,500 frames (two BREAK syncs and thirteen LDCS commands per attempt); target response: 1,300/1,300 one-byte responses. No echo or response failure.
- Latency median=201.537 ms; p95=204.744 ms.
- Raw response counts across attempts: `CS00=30` 100; `CS01=00` 100; `CS02=00` 100; `CS03=08` 100; `CS07=02` 100; `CS08=00` 100; `CS09=03` 100; `CS0A=01` 100; `CS0B=82` 200 (two reads per snapshot); `CS0C=00` 100; `CS04=00` 100; `CS05=10` 100. `CS05` is `ASI_OCD_STATUS` and `CS0B` is `ASI_SYS_STATUS` in the existing implementation. Its `OCDMV=0x10` mask is set and `OCD_STOPPED=0x01` is clear in all 100 observations. The raw `CS0B=0x82` is retained without assigning meanings to undocumented bits. No `ASI_OCD_MESSAGE` read occurred, so actual message bytes are unknown.

### Evidence and hashes

- Raw per-attempt records: 100 files in `evidence/raw/baseline-20261026T1655Z/lane_a/sib/` and 100 in `.../control/`. Each condition's summary JSON contains the attempt-to-file SHA-256 mapping; recomputation matched all 200/200 entries.
- SIB summary SHA-256: `eb83068d8b1003e0e3bd79cb4778250d66548b2310b0253e24fe5e4d8878d5fd`.
- Control summary SHA-256: `931fd524f8378d4431cca0ce64a50f7fdf8b3ba83e5d2ee9bf6e18e98dd9ce32`.
- `cli.sha256` maps the two summaries plus `baseline.stdout`, `baseline.stderr`, and `baseline.exit`; all entries were recomputed and verified. The stdout contains the run/condition metrics and evidence paths.
- No usbmon capture was made because all probes passed; this baseline therefore does not quantify kernel USB errors.

## Coordinator's one-shot OCD message snapshot

- Run: `ocd-message-20261026T173917Z-lane_a`; Lane A `ID_PATH=pci-0000:00:14.0-usb-0:4:1.0`; target identity remains `UNKNOWN_TARGET`.
- N=1; pass=1; failures=0; latency 284.286 ms; 33/33 exact echoes; 16 status responses and 15 message bytes.
- `ASI_OCD_STATUS` was `0x10` for 15 reads, then `0x00` on the final read; `OCD_STOPPED=0` throughout. The consumed message bytes were `HEYYY fuckkkk\r\n` (`4845595959206675636b6b6b6b0d0a`).
- Raw SHA-256: `25bb225b5fc8cc680196c7178703e9b66ece65e28faa58fe1b3f9866788547ce`.
- The volatile message queue was consumed by the read. The probe made no writes. This post-baseline observation does not prove the SILENT-firmware condition or identify the source of the message.

## Follow-up GPR2 / FLAG_RX reads

- Evidence path: `evidence/raw/flag-rx-20261026T174820Z/lane_a/`; 100 sequential read-only LDS reads at address `0x1E` on the stable Lane A ID_PATH. All 100/100 passed and returned `0x03`; `FLAG_RX` (`0x02`) and `FLAG_ENABLE` (`0x01`) were set in 100/100 reads. Median latency was 147.597 ms; p95 was 150.083 ms.
- No virtual-UART payload or target writes were issued. Repeated reads observe persistent register state; they do not prove 100 new RX events or identify the flag's source.
- The inspected upstream `external/upditerm/updi_uart.c` defines `FLAG_RX` as “RX buffer full” and clears it only after `updi_uart_rx()` reads GPIOR3; the direct LDS reads do not clear it, and current target firmware remains unknown. This is separate from target-to-host OCD bytes.

## RCA_CROSSOVER_01 pre-crossover confirmation

- Preflight resolved `ID_PATH=pci-0000:00:14.0-usb-0:4:1.0`, VID:PID `10c4:ea60`, duplicated USB serial `0001`, and sysfs path `/devices/pci0000:00/0000:00:14.0/usb3/3-4/3-4:1.0/ttyUSB0/tty/ttyUSB0`. Two by-path aliases resolved to that same device; the selected locator was `/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0`. `fuser` showed no owner. The target identity remains `UNKNOWN_TARGET`.
- Command: `PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli baseline pci-0000:00:14.0-usb-0:4:1.0 experiments/updi_rca/evidence/raw/RCA_CROSSOVER_01/pre/lane_a --attempts 10 --baud 38400 --timeout 1.0`. Wall interval: `2026-10-26T21:18:21.620722Z`–`2026-10-26T21:18:25.824075Z`; monotonic duration 4.203343358 s; exit 0. Command, stdout, stderr, exit, timing, preflight, raw attempts, and summary hashes are preserved in `evidence/raw/RCA_CROSSOVER_01/pre/lane_a/`.
- SIB run `baseline-20261026T211821Z-1a031f37-sib`: N=10, pass=10, fail=0, no failure stages; 30/30 exact echo frames and 10/10 SIB responses (320 bytes); median 156.332 ms, p95 158.131 ms; Wilson 95% success interval 72.25%–100%.
- Control run `baseline-20261026T211821Z-1a031f37-control`: N=10, pass=10, fail=0, no failure stages; 150/150 exact echo frames and 130/130 one-byte control responses; median 201.944 ms, p95 203.732 ms; Wilson 95% success interval 72.25%–100%.
- All 20 raw attempt hashes in the condition summaries were recomputed and matched. SIB summary SHA-256: `ba02fb4d18ef6457be7d3c2acd485b88cd9d11d273dec73059b153122bd147f2`; control summary SHA-256: `1305adf2d6a79cfdd4aba946ddad1920d20485a553360a8002a95a375e30995f`; `SHA256SUMS` manifest SHA-256: `8dbb36446439915e96f873c57ab18d42415b0804b374bd513047fe199df5f7a7`. Both conditions used the strict read-only path (BREAK sync plus SIB/LDCS reads); no target writes, reset, key, or programming operation was issued.
