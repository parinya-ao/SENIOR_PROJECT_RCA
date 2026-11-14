# Cross-experiment comparison

| Condition | Tracker reader | Tracker command | Reset state | Gateway result | Interpretation |
|---|---|---|---|---|---|
| Gate1, non-RF | Monitor active | 20 STATUS | Reset source not measured in that run; one controlled startup reset was requested | N/A | 20/20 STATUS passed after the STS correction |
| Reader-attached reverse raw | Monitor reader/writer | SEND via Monitor | Empty UPDI responses; reset not established in those captures | 15 s timeout in runs that continued Gateway capture | Monitor observation loss does not establish TX outcome |
| Reader-free reverse raw, seven attempts | No Tracker reader; direct writer | 28 bytes per SEND | Two runs changed GPIOR0 0x20→0x01 | Seven Gateway RX timeouts | Continuous reader is not required for the failure; POR is reproducible |
| Reader-free idle control | No Tracker reader | No RF command | GPIOR0/RSTFR/UART_FLAGS unchanged for 15.029 s | N/A | Ordinary UPDI idle did not produce the reset |

Original Incident A remains distinct: Tracker logged TxDone, but no reset-cause capture exists. The current POR reproductions do not retroactively establish the cause of that historical TxDone/no-RX result.
