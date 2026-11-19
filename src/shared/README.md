# Shared firmware modules

Shared code provides concrete protocol and hardware boundaries used by both
roles. Application decisions remain in Sender or Receiver source.

| Path | Role |
|---|---|
| radio/radio_link.cpp | Addressed SX127x RadioLib adapter for the SSOT transport |
| radio/arq_radio.cpp | SPI and RadioLib setup for the separate raw ARQ diagnostics |
| protocol/reliable_transport.h | Bounded SSOT DATA/ACK/NACK transaction state |
| protocol/arq_ingress.cpp | CRC, FIFO length, and ARQ frame decoding before dispatch |
| diagnostics | Bounded event and status storage |

The authoritative SSOT codec remains in stable_lib/ssot. The portable ARQ
encoder and sender/receiver algorithms remain in stable_lib/arq. Keeping these
implementations there avoids a second codec or state machine under src/shared.
Radio wrappers contain I/O only. They do not own retry, session, or acceptance
policy.

Both protocols use RadioLib and the same physical SX127x class of radio, but
their packet layouts and state machines are intentionally distinct. See the
[ACK/NACK analysis](../../docs/testing/LORA_ACK_NACK.md) and the
[stable_lib inventory](../../stable_lib/README.md).
