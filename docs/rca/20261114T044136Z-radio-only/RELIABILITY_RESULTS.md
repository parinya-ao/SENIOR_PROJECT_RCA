# Reliability Results

## Software-only results

- Full host suite: **302 tests run, 1 skipped, 0 failures, 0 errors**.
- PlatformIO: **15/15 active target environments built**; all static HEX application ranges and reset vectors pass.
- Host simulation emitted: `DATA_ACK=PASS DATA=1 PAYLOAD_MATCH=11/11 ACK=1 RETRIES=0 EEPROM_WRITES=0`. This is a simulation and not a physical radio transaction.
- RadioLib 7.1.2 HAL simulation: 12 modeled TX/RX cycles at 923 MHz across two reset-mode models.

## Physical results

| Metric | Physical result |
|---|---:|
| Candidate firmware flashed | 0 devices |
| RF sessions | 0 |
| DATA accepted by Tracker | UNKNOWN |
| ACK accepted by Gateway | UNKNOWN; historical H01 was 0/10 |
| NACK hardware trials | 0 |
| Retry hardware trials | 0 |
| Candidate-window reset count | NOT MEASURED |
| MCU VDD / 3V3-LORA minimum | NOT MEASURED / NOT MEASURED |

There is no physical sample from which to calculate packet success rate, retry rate, latency, P50/P95/P99, or reliability bounds. The system is not cleared for FOTA or deployment.
