# Suggested append-only AGENTS.md contract (merge; do not overwrite existing instructions)

## Goal-driven LoRa development

- Work only as the primary single agent. Never spawn subagents or enable multi-agent orchestration.
- Before modifying code, inspect the actual current repository, Graphify/CodeGraph output, target build environment and test evidence.
- Keep `/home/parinya/university/iwing-tracker` strictly read-only and check the reference implementation/commit before changing observable behavior.
- The active project uses PlatformIO with `src/main.cpp` and a `stable_lib` library directory unless verified otherwise. Never link duplicate owners for an active symbol.
- In SX127x LoRa mode, `setNodeAddress` is not a hardware LoRa address-filter feature. Implement and test the existing software destination/source/session policy.
- Physical DATA↔ACK tests precede migration when hardware and RF permissions allow. Do not report physical success from host mocks.
- Preserve BOOT, fuses, generated single-source-of-truth values, wire compatibility and security controls.
- Use Google C++ comment principles for public API contracts and non-obvious implementation decisions, not obvious line-by-line narration.
- Do not delete duplicate-looking modules until caller analysis, build ownership and regression evidence prove deletion safe.
- Every iteration: review evidence, write a failing test, make minimal change, validate, update graph, record results; stop on genuine safety/access blockers.
