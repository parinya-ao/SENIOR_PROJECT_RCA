# Execution journal

| ID | Command / action | Hardware | Observation | Evidence |
|---|---|---|---|---|
| E-STS-AB | Host-only GPIOR1 short-address / 16-bit STS probe | Tracker, CPU halted for register A/B | Short STS ACKed but readback remained 0x00; wide STS wrote 0xFF, cross-read agreed, restore verified | artifacts/arq/gate1-updi/20261113T184115Z-tracker-wide-gpr-sts/transport-trace.jsonl |
| E-GATE1 | Live, non-RF Gate 1; 20 STATUS requests | Tracker port1 | Identity/build matched; 20/20 passed; zero mismatch/timeout/Monitor exit | artifacts/arq/gate1-updi/20261113T191315Z-tracker-gate1-20-fixed/verdict.json |
| E-RF-ATTACHED | uv run python tools/arq_trial.py --reverse-raw --rf-path-confirmed | Tracker TX, Gateway RX | Tracker Monitor exited on UPDI response errors; Gateway timed out in runs that continued capture | artifacts/arq/20261113T193134Z-reverse-raw/, 194423Z-reverse-raw/, 200454Z-reverse-raw/, 201155Z-reverse-raw/ |
| E-RF-NOREADER | uv run python tools/arq_trial.py --reverse-raw-no-tracker-reader --rf-path-confirmed | Gateway Monitor only; direct Tracker UPDI writer | Seven bounded attempts; 28 command bytes accepted each; Gateway RX timeout in all seven. Two repeats recorded PORF after baseline | artifacts/arq/20261113T202649Z-reverse-raw/ through 211753Z-reverse-raw/ |
| E-IDLE-CONTROL | uv run python tools/rca/updi_idle_control.py | Tracker in verified normal standby | 15.029 s no-RF; GPIOR0/RSTFR/UART_FLAGS unchanged | artifacts/arq/20261113T211610Z-updi-idle-control/idle-control.json |
| E-RESTORE | Existing prepare() cleanup after each raw run | Both boards | Normal firmware restored; latest standby true, no RF during cleanup | artifacts/arq/20261113T212027Z-standby/standby-verified.json |

No scope, logic analyzer, SDR, spectrum analyzer, antenna swap, receiver IF A/B, or ACK/NACK test was executed.
