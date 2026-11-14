# ARQ and packet path

## Reverse-raw path

Host writes SEND over Tracker UPDI virtual UART → Tracker firmware parses newline → Tracker radio startTransmit → Tracker TxDone → radiated RF → Gateway continuous RX → Gateway header/RxDone/CRC/FIFO.

**FACT:** In reverse-raw, the role name is not the RF direction: Tracker’s LORA_ROLE_RECEIVER image executes TX; Gateway’s LORA_ROLE_SENDER image executes RX. The one-shot payload is 11 bytes (Hello World) and this mode has no ACK.

**OBSERVED:** The reader-free Host writer delivered all 28 ASCII command bytes of SEND 48656C6C6F20576F726C64 plus newline. Gateway was already in RX continuous and reported RAW_RX_TIMEOUT after 15 seconds.

**UNKNOWN:** Whether the newline was consumed and the SEND handler entered before POR. The post-window UART_FLAGS=0 cannot prove consumption because POR resets the GPIOR. No Tracker RAW_TX/RAW_TX_DONE record survived the POR.

## Historical raw incident

Incident A captured local Tracker RAW_TX_DONE and a Gateway timeout. TxDone means the radio reported local transmit completion; it does not prove the antenna radiated or the Gateway received the packet.

## Normal ARQ and ACK

The H01 normal-direction run commanded Gateway DATA TX toward Tracker RX, then failed capture on a Tracker Monitor error. No complete Tracker receive/accept or ACK event was recorded. Physical ACK/NACK behavior remains unverified. Do not proceed to retry/ACK hypotheses until reverse raw is independently received.
