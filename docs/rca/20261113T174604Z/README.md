# LoRa ARQ V1 root cause war room — 20261113T174604Z

Status: active. No production firmware, SSOT, or generated configuration was modified for this review. All live tests use the physically verified Tracker USB path and have separate artifact bundles under `artifacts/arq/`.

The completed Gate 1 failure is the current earliest software boundary: MCU identity and low-level UPDI exchanges passed; one STATUS command was delivered through the mailbox, but no Monitor output arrived by the response deadline. The firmware role/build and command-consumption result remain unknown.

SSOT review found the static Tracker/Gateway pin maps consistent and confirmed reverse-raw functional role inversion is intentional. Physical power/RF measurements remain unavailable.

See `EXECUTION_JOURNAL.md`, `HYPOTHESES.md`, and the existing raw Gate 1 bundle `artifacts/arq/gate1-updi/20261113T153146Z/`.
