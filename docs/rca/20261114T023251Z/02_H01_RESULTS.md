# H01 reader-free hardware result

## Experiment

**Purpose:** Separate failure of the Tracker output reader from failure of the DATA/ACK exchange, while preserving the Tracker’s direct UPDI command path and reset-cause evidence.

**Command:** `uv run python tools/arq_trial.py --reader-free-h01 --rf-path-confirmed` (two sequential sessions, IDs 8 and 9).

**Firmware:** `sender_arq_test` on Gateway and `receiver_arq_test` on Tracker. Tracker SHA-256 `a0ab664615411a069e3a928598fc6d7228dda70e4e4425758bb9bd63801a93bc`, build ID `5022e27fcd7077f35450baa8e1595e3f51e2e3ba4c224698a55d66ec619ba9ac`. Gateway SHA-256 `72774ddc8222e892f2c432033822673bbc6e09aab0c02812f28ba516251ba18c`, build ID `f79febdfcc9d9e56bd33f0b298c82af55374b49191750193db1ae3dc07eb801c`.

Session 8 records source commit `19ef9ccb32a79dd4d9e200f40aaa7c8d05745197`; session 9 and the RX-idle control record `f8092bc70eae4d99d197427708b74ef19c11be13`. All three bundles report the same Tracker HEX hash and build ID above.

**RF parameters:** Existing shared profile, nominal 915 MHz (`Frf=E4C000`), BW 125 kHz, SF7, CR 4/5, sync word `0x12`, explicit header, CRC enabled, normal IQ, configured +2 dBm. No settings changed.

## Observations

| Boundary | Observed evidence | What it proves |
|---|---|---|
| Tracker preflight | `STATUS ready=1`, overflow 0, `ARM rc=0`, `RX_READY rc=0`, register snapshot `RegOpMode=0x8D` | Tracker firmware reported ready and the radio was configured in LoRa RX Continuous before Gateway DATA. |
| Gateway TX | Each session had five DATA `TX` records and five `TX_DONE rc=0 flags=8`; each was followed by `RX_READY` with `RegOpMode=0x8D` | Gateway radio completed ten internal DATA transmissions total and entered its ACK receive window after each. This does not prove radiated output. |
| Gateway ARQ result | Sessions 8 and 9 each had five `RX_TIMEOUT` events and ended `TIMEOUT_EXHAUSTED` with attempts 5 | No valid ACK was accepted by the Gateway application in either H01 session. |
| Tracker events after DATA | No Tracker RX/ACCEPT/ACK event was captured. Its post-transaction output buffer was empty. | Tracker RX and ACK stages remain unknown; absence of buffered events after reset is not proof the events never occurred. |
| Tracker reset state before exchange | `GPIOR0=0x20`, `RSTFR=0`, `UART_FLAGS=1` | The startup-captured flags contained UPDIRF, not PORF, at preflight. |
| Session 8 post-window UPDI read | Zero-byte response while reading GPIOR0 (`expected None, received b''`) | Direct UPDI read failed; reset state remained UNKNOWN in this session. |
| Session 9 post-window UPDI read | Echo mismatch on request `55 00 1C` (read GPIOR0); received `FF FF 55` instead of expected echo | Direct UPDI transport failed after the H01 window. This error does not itself prove reset. |
| Session 9 fresh UPDI/OCD session, no CPU reset | Standard double BREAK/OCD initialization, then `GPIOR0=0x01`, `RSTFR=0`, `UART_FLAGS=0` | A POR flag had been captured by startup during the interval after preflight and before resync. The second session did not request CPU reset. |

In session 9, the exact reset time relative to its five Gateway transmissions, Tracker preamble detection, application DATA acceptance, or a possible Tracker ACK transmission is **UNKNOWN**. No Tracker `RX_DONE`, `ACCEPT`, ACK `TX`, or ACK `TX_DONE` was captured in either session, so these runs cannot prove whether a reset preceded or followed those stages.

## Evidence

- [Session 8 bundle](../../../artifacts/arq/20261114T022413Z-h01-reader-free/bundle.json) — 73/73 listed files match. [Session 9 bundle](../../../artifacts/arq/20261114T023251Z-h01-reader-free/bundle.json) — 75/75 listed files match.
- `tracker-output-preflight-status.bin`, `tracker-output-arm.bin`, and `tracker-output-armed-status.bin` preserve the successful preflight/RX-state logs.
- `tracker-reset-read-error` and `tracker-reset-resync` in the bundle preserve the first UPDI failure and the later reset-state read.
- [Normal standby restore](../../../artifacts/arq/20261114T023713Z-standby/standby-verified.json) — `standby=true`, zero cleanup RF transmissions.

## Interpretation

The H01 receive/ACK exchange failed, and a Tracker POR occurred in the same bounded trial window. This is a confirmed reset event associated with packet-exchange activity, but the available software evidence does not identify the triggering instruction or physical rail. Gateway `TX_DONE` is not evidence of RF emission, and Gateway timeout is not proof that Tracker’s radio saw no energy.
