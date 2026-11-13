# Standards mapping

เป็นการประยุกต์แนวคิด reliability สำหรับ raw LoRa ไม่ใช่ CoAP/TCP/UDP
หรือ LoRaWAN implementation. Sources checked 2026-11-13.

| Source | Adaptation | Evidence |
| --- | --- | --- |
| [RFC 7252 §§4.2–4.8](https://www.rfc-editor.org/rfc/rfc7252.html#section-4.2) | One outstanding confirmable exchange, randomized initial interval, exponential retransmission, duplicate ACK replay, bounded retries and exchange lifetime | `sender.c`, `receiver.c`, core assertion harness |
| [RFC 6298 §3](https://www.rfc-editor.org/rfc/rfc6298.html#section-3) | Karn-style exclusion of RTT after retransmission; no adaptive estimator yet | Sender `attempts==1` sample guard; RTT sample counts |
| [RFC 8085 §3](https://www.rfc-editor.org/rfc/rfc8085.html#section-3) | Conservative pacing (3 seconds), retransmission backoff; control traffic never recursively acknowledged | Sender start spacing and receiver DATA-only gate |
| [RFC 1982 §3](https://www.rfc-editor.org/rfc/rfc1982.html#section-3) | Modular sequence increment; exact equality rather than ordering distant sequence values; all timer intervals below half-range | Wrap tests; config timer-bound validation |
| [LoRaWAN L2 1.0.4 §§4.3.1.2–4.3.1.3](https://lora-alliance.org/wp-content/uploads/2021/11/LoRaWAN-Link-Layer-Specification-v1.0.4.pdf) | Compare confirmed-frame ACK and bounded retransmission concept only | Separate ACK/NACK frames in custom 12-byte header |

ไม่มี LoRaWAN receive windows, network server, join, MIC, encryption, ADR,
frame counter inference หรือ regional MAC behavior. Session IDs isolate old
traffic but do not authenticate peers. The 75 ms guard and 2–3 s RTO are
experiment settings, not RFC-mandated LoRa timings.
