# Raw LoRa ARQ V1

ทั้งสองบอร์ดเริ่มแบบ unarmed ใน standby; host ต้อง ARM session ใหม่หลัง reset เสมอ.
Raw MVP และ legacy `src/ssot.c` ยังคงเดิม.

Wire bytes: version=1, type (DATA=1/ACK=2/NACK=3), source, destination,
session uint32 LE, sequence uint16 LE, payload length, reason, payload.
Header=12 bytes, payload<=32, frame<=44. DATA/ACK reason=0; ACK/NACK
payload empty. NACK reason: 1 unexpected sequence, 2 application rejected,
3 temporarily busy. Malformed/CRC/address/session failures are silent.

Commands are newline terminated, bounded ASCII: `ARM 1234ABCD`,
`SEND 48656C6C6F20576F726C64`, `STATUS`, `X`, and test receiver only
`FAULT 10 10`. ARM same session is idempotent; session replacement while
active is rejected. RF cannot arm devices. X stops new requests, lets an
outstanding request finish, then parks the radio in standby. A new-session
ARM clears stop and enables RX. Host reserves sessions
monotonically on disk and waits for both ARM acknowledgements.

Sender: IDLE -> TRANSMITTING -> WAITING_ACK -> BACKOFF -> TRANSMITTING.
DELIVERED/FAILED retain result until explicit SEND. One immutable outstanding
frame, initial RTO sampled once in [2000,3000] ms, doubles each retry, four
retries. TxDone/cleanup/RX success precede RTO start. Controls are processed
before deadlines. Matching ACK in WAITING_ACK/BACKOFF succeeds; matching
application rejection -> REJECTED, unexpected sequence -> PROTOCOL_ERROR.
BUSY uses the existing deadline (repetition cannot postpone retry).
No second full wait in BACKOFF after timeout; DATA starts >=3000 ms apart.
TX timeout=3000 ms, fatal adapter failure -> RADIO_ERROR, exhausted budget
-> TIMEOUT_EXHAUSTED. Fixed transaction deadline bounds all attempts,
including local TX and spacing. All intervals stay below half uint32 range.
Sequence increments only on ACK, modulo 65536; sequence reuse requires a
new session, including after a failed transaction. Reset aborts the trial.

Receiver: LISTENING -> VALIDATING -> SENDING_RESPONSE -> RETURNING_TO_RX
-> LISTENING. Exact configured payload accepted at expected sequence;
record acceptance before response. Duplicate last accepted DATA replays ACK,
without another delivery, only after exact payload validation. ACK failure
does not erase deduplication. Initial response guard=75 ms; subsequent guard
experiments come only from TOML with recorded evidence. Restore RX after response
or recoverable error; controls never produce controls. Fault injection drops
only selected first acceptance responses; duplicate replay remains enabled.

Diagnostics use 16 fixed event slots, nonblocking byte flushing, retained
startup/status, overflow count. RTT is local TxDone to matching ACK, only
without retransmission. Report samples/count/min/max/average/P95. No clock
subtraction between boards. Reset, overflow, missing terminal invalidates
completeness. STATUS_END follows all diagnostics and carries the final overflow
count; the host waits for that marker in the active session before closing.
Text parser validation alone cannot prove physical origin.

Deferred: adaptive RTO, FOTA, persistence, authentication. Deduplication is
RAM only. Power integrity remains unmeasured.
