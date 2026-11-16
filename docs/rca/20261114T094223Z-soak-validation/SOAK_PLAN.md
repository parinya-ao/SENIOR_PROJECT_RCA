# Long-Duration Soak Plan and Readiness

## Implemented

The host runner reuses `tools/arq_trial.py` and the existing live ARQ protocol. It runs one validated transaction per session, uses a fresh session ID, validates matching DATA/ACK frames from raw capture, parks both radios, checks final STATUS, and restores normal firmware after each stage. The soak runner:

- Requires physical board mapping, safe power/ground/UPDI, RF hardware/path, and applicable RF authorization confirmations before it opens device interfaces.
- Requires each preceding stage to have a durable `PASS` receipt before beginning a later stage.
- Paces session start times at least 60 seconds apart and calculates a conservative 1% airtime budget from the selected PHY and maximum frame lengths.
- Streams and fsyncs progress records, records interruptions and partial results, and only passes a duration stage when monotonic session-start timestamps cover its full target duration and cleanup/firmware restoration is recorded.
- Reports Wilson 95% confidence intervals, attempts, retries, observed timeouts, reset observations, and host-observed latency. P90/P95 are withheld below 20 observations; P99 is withheld below 100.

The raw `campaign.json`, per-session `bundle.json` files, `soak-progress.jsonl`, programmed image snapshots, and `manifest.json` remain under `artifacts/arq/<run-id>/` when the runner is used. A persistent `artifacts/arq/soak-ledger.json` records stage receipts. It is intentionally not created by this blocked run.

## Workload and airtime envelope

The active ARQ profile is 923 MHz, +2 dBm configured conducted power, BW 125 kHz, SF7, CR 4/5, sync word `0x12`, explicit header, CRC enabled, and normal IQ. These are source/build settings, not physical readbacks or measured EIRP.

The maximum DATA frame is 44 bytes (12-byte protocol header plus 32-byte payload); the ACK/NACK control frame is 12 bytes. The Semtech SX1276 packet-airtime calculation gives 92.416 ms DATA and 41.216 ms control airtime. With five allowed attempts, the worst-case airtime per session is 462.080 ms on Gateway and 206.080 ms on Tracker. At a 60-second session-start interval, modeled channel occupancy is 0.7702% and 0.3435% respectively. Firmware DATA start spacing is 10 seconds, or 0.9242% for a maximum-size frame.

These are modeled upper bounds, not RF measurements. NBTC MT 1033-2560 specifies 1% cumulative airtime per hour for EIRP below 50 mW and occupied bandwidth up to 500 kHz, and 10% for EIRP above 50 mW through 4 W. Using 1% is a conservative planning target; the actual prototype EIRP, equipment conformity, and legal test conditions are still unknown. See [SOURCE_RESEARCH.md](SOURCE_RESEARCH.md).

## Progressive stages

| Stage | Planned sessions | Minimum interval | Required pass condition |
|---|---:|---:|---|
| `1-session` | 1 | 60 s | One valid DATA accepted, matching ACK accepted, successful cleanup |
| `10-sessions` | 10 | 60 s | 10/10 complete, verified bundles and cleanup |
| `100-sessions` | 100 | 60 s | 100/100 complete, valid event and retry accounting |
| `1000-sessions` | 1,000 | 60 s | 1,000/1,000 complete, no detected reset/session break |
| `1-hour` | 61 | 60 s | First-to-last monotonic session-start span at least 3,600 s |
| `8-hours` | 481 | 60 s | First-to-last monotonic session-start span at least 28,800 s |
| `24-hours` | 1,441 | 60 s | First-to-last monotonic session-start span at least 86,400 s |

Duration stages add one session so the first and last starts are separated by the full requested span. The stage order is enforced; a skipped, failed, or interrupted stage cannot authorize the next one. A finite passing sample is evidence only for the recorded conditions and does not establish lifetime reliability.

## Current execution status

All seven stages are `NOT_RUN`. The CLI was exercised without physical confirmations and exited before opening UPDI/serial ports. No candidate firmware was flashed, no DATA command was sent, and no RF transmission was started. The previously recorded hardware preflight remains blocked by power/back-feed, SD socket, and RF equipment/authorization unknowns; see [SOAK_RESULTS.json](SOAK_RESULTS.json) and the [prior preflight](../20261114T044136Z-radio-only/HARDWARE_PREFLIGHT.json).
