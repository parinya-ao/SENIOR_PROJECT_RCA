# Incident timeline

All run IDs are UTC. Device `t=` counters are local MCU milliseconds and are not subtracted across boards.

| UTC/run | Observation | Classification |
|---|---|---|
| `20261113T121506Z` | Tracker reported one local `RAW_TX_DONE` (`flags=8`); Rudolph was in RX for 15,000 ms and reported `RAW_RX_TIMEOUT`, `flags=0`. No valid payload was captured. | Historical `PHYSICAL_RF_FAILURE_UNISOLATED`; RF radiation and endpoint fault were not isolated. |
| `20261113T123620Z` | Tracker Monitor reported `UPDI response mismatch: expected None, received b''` after Host `SEND`. No Tracker `TX_START`/`TX_DONE` was captured. | Historical `HOST_TRANSPORT_ERROR / RF INCONCLUSIVE`. |
| `20261113T142138Z` | Earlier Gate 1 preflight refused to start because standard Monitor initialization sends two BREAKs, then prohibited by that run’s authorization. Zero STATUS requests. | `GATE1_BLOCKED`; not hardware evidence. |
| `20261113T183400Z`–`184115Z` | Tracker GPR mailbox width probe. The short STS form was acknowledged but failed GPR readback; 16-bit STS changed the same GPR and readbacks agreed. | Confirmed Host UPDI data-space write defect. Raw trace: [`transport-trace.jsonl`](../../../artifacts/arq/gate1-updi/20261113T184115Z-tracker-wide-gpr-sts/transport-trace.jsonl). |
| `20261113T191315Z` | Tracker identity verified; normal Monitor double BREAK and OCD initialization; 20/20 non-RF STATUS transactions passed. | `GATE1_PASS` for that non-RF window only. |
| `20261113T193134Z`, `194423Z`, `200454Z`, `201155Z` | Tracker Monitor failed during reverse/active-radio capture with an empty UPDI response. In later captures Rudolph remained in RX and timed out. | Monitor/UPDI observation failure; no Tracker TX state proved. |
| `20261113T202649Z`, `203405Z` | Reader-free Tracker UPDI writer sent all 28 bytes of `SEND 48656C6C6F20576F726C64\n`; Gateway timed out. Late Monitor read did not recover Tracker TX events. | Tracker RF event still unknown. |
| `20261113T204403Z`–`205844Z` | After the 15 s window, Tracker UPDI `LDS` of GPIOR2 timed out after 1.0 s with zero bytes (`last_tx=55 00 1e`). A fresh no-reset UPDI session was used to read state. | Direct UPDI response loss after the SEND window. |
| `20261113T210613Z`, `211753Z` | Two reader-free Tracker SEND trials. Each had Gateway `RAW_RX_TIMEOUT` after 15 s. Baseline `GPIOR0=0x20`; post-window fresh-UPDI read returned `GPIOR0=0x01`, `RSTFR=0`. | POR occurred during each test interval. No Tracker TX event or valid RX packet was captured. |
| `20261113T211610Z` | Matched 15.029 s no-RF idle control on Tracker: `GPIOR0=0x20`, `RSTFR=0`, `UART_FLAGS=1` before and after. | No reset observed during this idle control. |
| `20261113T212027Z` | Normal Sender/Receiver images restored, verified unarmed standby, zero RF during cleanup. | Restoration verified. |

The POR sample was taken after the Gateway receive window and fresh UPDI synchronization, so its exact instant relative to Tracker TX_START is **UNKNOWN**. The reset-source change is direct evidence, not an inference from a Monitor disconnect.
