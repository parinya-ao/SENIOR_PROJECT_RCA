# Baseline Graph

Snapshot: 2026-11-16, repository `f0ca01554c156b2034ac29c304571ec7dcb02acb`, before feature ownership migration. The worktree had 117 pre-existing dirty entries; the 118th status entry was the temporary Graphify interpreter marker used for the query and later removed. This report describes the live checkout, not HEAD alone.

## Graph tools

- Graphify Local 0.9.106 queried `graphify-out/graph.json` (3,784 nodes, 6,909 links; graph metadata names the same HEAD). The graph locates `firmware_app`, `reliable::Transport`, `LoRa`, the ARQ codec/state machines, and their source files.
- A broad Graphify path query did not establish one directed `Application → Sender → ARQ → Codec → LoRa → SX127x` path. The source has separate compile-time application paths: the reliable DATA/ACK path uses `reliable::Transport<LoRa>`, while ARQ uses its own frame codec and a direct RadioLib `Module`/`SX1276` adapter. Graph edges are structural evidence; the call sites below were checked in source.
- CodeGraph CLI 1.6.2 is installed, but both CLI and MCP report no usable project index. The index was not initialized because indexing is the project owner's choice. CodeGraph status: **BLOCKED**, not passed.

## Source-confirmed paths

```text
Arduino setup/loop
  → src/main.cpp
  → firmware_app::Initialize/Poll (compile-time role dispatch)
  → gateway_app or reliable_app
  → reliable::Transport<LoRa>
  → LoRa wrapper (stable_lib/lora/lora.cpp)
  → RadioLib SX1276 / SX127x
```

```text
ARQ environments
  → firmware_app::Initialize/Poll
  → arq::app::Initialize/Poll
  → arq::EncodeFrame/DecodeFrame and sender/receiver state machines
  → direct RadioLib Module/SX1276 operations
```

The first path is the active default `sender`/`receiver` DATA/ACK vertical slice. `src/` contains only `main.cpp`; feature implementations are still under `stable_lib/`. ARQ and SSOT use separate wire formats and are not interchangeable.

## Hardware baseline

The operator reported that the boards are unavailable. Read-only `pio device list --json-output` showed only generic `/dev/ttyS0` through `/dev/ttyS31` entries with no hardware IDs; no Sender or Receiver identity was established. No serial probe, upload, or RF transmission was performed. Physical baseline: **PHYSICAL_BASELINE_BLOCKED**.
