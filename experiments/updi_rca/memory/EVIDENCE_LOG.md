# Evidence log

All current raw probe records are linked from `reports/runs.csv` and `reports/events.csv`. SHA-256 values below identify the JSON payloads; agent-owned lane records remain in their respective lane directories.

| UTC | Run | Lane / identity | Result and exact boundary | Raw evidence SHA-256 |
|---|---|---|---|---|
| 2026-10-26 16:31:15.676515 | `LB-SIB-01` | B / target unknown; ID_PATH `pci-0000:00:14.0-usb-0:1:1.0` | SIB failed at initial 300-baud BREAK echo: TX `00`, expected 1 byte, observed 0; latency 1001.253 ms. No control/SIB response. | `62dfb23d319a30f691c95603a69d01c1b32b8c422af9b68fcc2c73bfbf612e31` |
| 2026-10-26 16:41:36.810823 | `LA-SIB-01` | A / target unknown; ID_PATH `pci-0000:00:14.0-usb-0:4:1.0` | SIB passed: 9/9 exact echoes, 5/5 LDCS control responses, 32/32 SIB bytes; 122.696 ms. SIB `    AVR P:2D:1-3M2 (A7.KV001.0)\0`. | `610f3aff4d1ed536311faf3ce99233e778b017837d66cdfb6b2b3b2d53c9d86e` |
| 2026-10-26 16:42:08.905314 | `LA-SIGNATURE-1100-01` | A / target unknown | Signature read init failed at UPDI control response: 4/4 exact echoes; expected 1 response byte, observed 0; 1006.782 ms. Stopped before signature, REVID, or serial result. | `ee243af3ff4e573e3e1f879464503e042134b865d5d4d8d8179c8ba07ce83aa8` |
| 2026-10-26 16:46:09.565026 | `LA-CONTROL-01` | A / target unknown; post-SIGKILL snapshot | Control read passed: 16/16 exact echoes, 13/13 LDCS responses; raw `ASI_OCD_STATUS=0x10`, `ASI_SYS_STATUS=0x82` twice; 144.306 ms. | `3baaac1abe20aecf6a3781c3ae1b0c0d5cbf505327a9661d7d3e0dcf6727a55f` |
| 2026-10-26 16:46:21.397479 | `LA-GPR2-01` | A / target unknown; post-SIGKILL snapshot | Read `GPR2` at `0x001E` passed: 9/9 exact echoes, 6/6 responses; raw `0x03` (`FLAG_ENABLE=1`, `FLAG_RX=1`); 113.253 ms. | `555c7421fa3333ab163e77f5e332a5fef9d131484d1fed51b9686d4911fb4e2a` |
| 2026-10-26 16:47:53.094727 | `LB-SIB-02` | B / target unknown; same stable ID_PATH | Independent SIB attempt again failed at initial BREAK echo: TX `00`, expected 1 byte, observed 0; latency 1001.233 ms. No retry or target read. | `d576a51ccd350b4637518405d431101d84b2570e51650a41ccc5bae5d5d2c8a3` |
| 2026-10-26 16:48:28.001896 | `LA-SIB-02` | A / target unknown; A/B/A final A | SIB passed: 9/9 exact echoes, 5/5 LDCS responses, 32/32 SIB bytes; 122.840 ms. SIB bytes match A1 exactly. | `eb6d82c9ce86a8b7dd11e6d07147d26fe7b77b4368b8370f719da68d83f9956c` |
| timestamp unknown | `USER-OBS-001` | Lane A path was held by the terminal process; target unknown | Nine identical visible strings before host `SIGKILL`; plausible OCD message path, with no raw byte/status/timing trace. See `evidence/raw/terminal-observation-20261026.md`. | user-supplied text, no instrumented log hash |

The two current Lane B failures are `LOCAL_ECHO` failures. Lane A's signature attempt is a different class: exact local echo followed by a missing UPDI control response. Neither is an ACC data-response failure.

## Historical input (not fresh lane-linked evidence)

- Prior report: unheld LDS had 19 missing target data responses in 60 trials (31.67%); the pool of 180 running-upstream trials across bauds had 19 missing data responses. Echo was correct in the 19/60 discriminator.
- Prior stopped-upstream campaign: 540/540 passed. Valid stopped official-oracle matrix: 720/720 passed after excluding 20 observer-invalid records. Default-CTRLA discriminator: 120/120 passed.
- Prior reset study: BORF remained asserted after clear in later samples while a GPR marker survived; those samples are not 20 independent resets. Do not count BORF alone as a new boot.
- Historical verified H image SHA-256: `88c03596bab443c74015d8dfb04e1985f6d14940d227b84a4a943b3d5f47807e`; target identity was not linked to either current lane.

## Strict no-register-write 38400 baseline

The standard repository probe backends were stopped before the 100-attempt batch because their initialization sends volatile UPDI control-space `STCS` writes. The experiment-owned strict path was then TDD-tested and used; it sends two 300-baud BREAK synchronization bytes, then only SIB/LDCS reads, and closes the OS port without protocol teardown writes.

| Lane / run | Condition | N | Pass / fail | Failure stages | Success Wilson 95% | Median / p95 latency (ms) |
|---|---|---:|---:|---|---|---|
| A / `baseline-20261026T171644Z-1a031f37` | SIB | 100 | 100 / 0 | none | 96.30–100.00% | 157.092 / 159.884 |
| A / same run | control snapshot | 100 | 100 / 0 | none | 96.30–100.00% | 201.537 / 204.744 |
| B / `baseline-20261026T171633Z-88c741a8` | SIB | 100 | 0 / 100 | `LOCAL_ECHO` 100 | 0.00–3.70% | 1060.951 / 1064.443 |
| B / same run | control snapshot | 100 | 0 / 100 | `LOCAL_ECHO` 100 | 0.00–3.70% | 1061.433 / 1064.452 |

Lane A SIB: 300/300 exact echoes; 100/100 SIB responses and 3,200/3,200 response bytes. The 32-byte SIB was identical across all attempts and matches A1/A2. Lane A control: 1,500/1,500 exact echoes and 1,300/1,300 one-byte LDCS responses. Across 100 control snapshots, `ASI_OCD_STATUS=0x10` every time (`OCDMV` set and `OCD_STOPPED` clear under the existing masks); `ASI_SYS_STATUS=0x82` on both reads each time. No `ASI_OCD_MESSAGE` byte was read.

Lane B: 0/100 SIB and 0/100 control commands reached their UPDI request phase. In SIB, the first BREAK echo was empty 86/100 times; in control, it was empty 85/100 times. The other 14 and 15 attempts respectively echoed the first BREAK exactly, then received no echo for the second BREAK. All 200 bounded attempts ended at `LOCAL_ECHO`; no SIB/LDCS response was observed. The port remained distinct from Lane A by `ID_PATH`, not by tty or duplicated USB serial.

Raw attempt logs are under `evidence/raw/baseline-20261026T1655Z/lane_a/` and `.../lane_b/`. All 400 per-attempt SHA-256 entries were recomputed and verified against files. Summary hashes: Lane A SIB `eb83068d8b1003e0e3bd79cb4778250d66548b2310b0253e24fe5e4d8878d5fd`, control `931fd524f8378d4431cca0ce64a50f7fdf8b3ba83e5d2ee9bf6e18e98dd9ce32`; Lane B SIB `4140151eaefcb349ca412dec8613d360cb8cba387a98bada83a5fd5632b9ee50`, control `f764befb130009392fcdaf937c0ed2c81ea8af3e437ac1a0918120cb898b9ab6`. Lane B's kernel-log check found 0 matching USB/CP210x/disconnect/EPROTO/EILSEQ lines in the 17:16:33–17:20:34 UTC window; no `usbmon` trace was captured.

## Scope correction for legacy probe records

The first Lane A batch used `tools/updi-diagnose.py` before the strict side-effect audit. Its raw logs contain six `STCS` initialization frames: four `CTRLB=0x08` operations and two oracle setup writes (`CTRLB=0x08`, `CTRLA=0x80`). They did not write target data memory, fuses, USERROW, EEPROM, or flash, and did not request reset. These five legacy records remain evidence but are labeled separately from the 400 strict attempts. `tools/updi-diagnose.py` closes upstream sessions with `abort=True`, so no additional cleanup protocol frame was sent.

## Bounded OCD message snapshot

At 2026-10-26 17:39:23 UTC, after the user terminal process had exited and `fuser` showed no process holding the stable Lane A by-path link, one bounded `ocd-message` probe ran against ID_PATH `pci-0000:00:14.0-usb-0:4:1.0`. Run ID: `ocd-message-20261026T173917Z-lane_a`; target identity remains unknown. It passed 1/1 in 284.286 ms (0 failures; Wilson 95% success interval 20.65%–100.00%). The raw trace records 33/33 exact echoes, 16 `OCD_STATUS` responses and 15 `OCD_MESSAGE` responses. Status was `0x10` before each of 15 bytes, then `0x00`; `OCD_STOPPED` remained clear. The exact message was 15 bytes: ASCII `HEYYY fuckkkk\r\n`, hex `4845595959206675636b6b6b6b0d0a`. The JSON hash is `25bb225b5fc8cc680196c7178703e9b66ece65e28faa58fe1b3f9866788547ce`. This confirms one line in the terminal text was target OCD output; it does not establish the count or timing of the original nine lines. Reading consumed the volatile 15-byte message queue. No STCS, STS, UART data, reset, NVM, fuse, or flash write occurred.

This single valid message is not the required SILENT-firmware test. The exact diagnostic image remains unflashed because Lane B cannot pass local echo, so identical-byte programming and verification on both targets are not possible without a new discriminator. The 168-row status inventory retains all hypotheses; the fresh lane difference remains confounded between adapter and target.

## Final structured outputs

The current ledgers contain 509 run rows (400 commissioned baseline attempts, 100 GPR2 reads, 7 earlier bounded probes, 1 OCD message snapshot, and 1 terminal observation) and 6,387 protocol/event rows. All 509 run sources have a SHA-256 mapping that verifies; all 400 commissioned baseline sidecar hashes also verify. Event IDs are unique and every event maps to a run ID. All 168 seed/status/ranking rows remain present with 112 `BLOCKED`, 48 `UNRESOLVED`, and 8 `SUPPORTED`; no cause is `PROVEN` or `STRONGLY_SUPPORTED`.

## Read-only GPR2 / FLAG_RX follow-up

After verifying the stable Lane A by-path port was free, one sequential 100-attempt campaign read GPR2 (`LDS 0x001e`) at 38400 using ID_PATH `pci-0000:00:14.0-usb-0:4:1.0`. All 100 reads passed; all 100 returned `0x03`, so `FLAG_RX` bit 1 and `FLAG_ENABLE` bit 0 were set throughout. Median/p95 read latency was 147.597/150.083 ms; the read-success Wilson 95% interval was 96.30%–100.00%, and the descriptive interval for the observed `FLAG_RX` state was also 96.30%–100.00%. Samples are sequential, correlated observations of one uncontrolled register state; they do not demonstrate 100 fresh RX events or identify the source of the flag. No virtual-UART payload, register, NVM, fuse, reset, or flash write was issued. Raw JSON attempts are under `evidence/raw/flag-rx-20261026T174820Z/lane_a/` and map to the run ID and per-file SHA-256 entries in `reports/runs.csv`.

The RCA now reports this as persistent FLAG_RX state, rather than a single sample. The terminal transcript remains nine un-timestamped lines; the later OCD snapshot captured one matching 15-byte line (N=1). The host `SIGKILL` remains distinct from a target reset.

Interpretation from the inspected upstream `external/upditerm/updi_uart.c`: `FLAG_RX` is documented as “RX buffer full,” and `updi_uart_rx()` clears it only after reading GPIOR3. A direct LDS read of GPR2 does not clear it. Because the current firmware identity is unknown, this is not proof that either target uses this handler. The flag represents virtual-UART host-to-target receive state and is distinct from target-to-host OCD message bytes.
