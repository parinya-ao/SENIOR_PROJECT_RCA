# Matched Tracker RX-idle control

## Experiment

The purpose was to distinguish continuous RX / elapsed time from a packet-exchange trigger. The same Tracker `receiver_arq_test` image used in H01 was installed. Tracker was armed into RX Continuous, then held there for 120 seconds with no Gateway DATA command and no RF transmitter. The Gateway board was not programmed for this control.

**Command:** `uv run python tools/arq_trial.py --tracker-rx-idle-control`

## Result

- Target duration: 120 seconds; measured Host monotonic duration: **120.029947 seconds**.
- Tracker mode at start: `RegOpMode=0x8D` (LoRa RX Continuous), ready 1.
- RF transmissions: **0**.
- Reset state before and after: `GPIOR0=0x20`, `RSTFR=0`, `UART_FLAGS=1`.
- POR transition: **not observed**.
- Tracker test firmware SHA-256: `a0ab664615411a069e3a928598fc6d7228dda70e4e4425758bb9bd63801a93bc`, identical to the H01 Tracker image.

This control supports the conclusion that steady RX Continuous and a 120-second elapsed interval alone were insufficient to produce the observed POR in this run. It does not exclude reset during packet reception, packet processing, ACK scheduling/TX, Gateway RF activity, or an intermittent power fault.

## Evidence

- [Raw RX-idle bundle](../../../artifacts/arq/20261114T025241Z-rx-idle-control/bundle.json) — 44 listed files; all exist and match their SHA-256 entries.
- [Normal standby restore](../../../artifacts/arq/20261114T025609Z-standby/standby-verified.json) — `standby=true`, zero cleanup RF transmissions.
