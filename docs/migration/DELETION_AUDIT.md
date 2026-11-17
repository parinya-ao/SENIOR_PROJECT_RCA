# Source Ownership Migration Audit

Iteration: 2026-11-17, revision `f0ca01554c156b2034ac29c304571ec7dcb02acb`.

These iterations relocated active implementations into their target owners and extracted the bounded reliable-event FIFO. No protocol code was deleted; the old implementation paths were moved, and public lifecycle/include names remain available through the composition API or header-only compatibility includes.

| Former owner | Current owner | Consumers updated | Evidence |
|---|---|---|---|
| `stable_lib/lora/lora.cpp` | `src/features/radio_link/radio_link.cpp` | Gateway/reliable apps, host wrappers, MVP simulator, RF proof host compiler | 82 focused host tests and 19 PIO environment links pass |
| `stable_lib/shared/reliable_transport.h` | `src/features/reliable_transfer/reliable_transport.h` | Gateway and reliable app includes; transport tests and sender assertions | Campaign ID is carried through DATA/ACK; stale ACK and wrong-session DATA tests pass; same-object re-arm retains duplicate history |
| `stable_lib/firmware_app/firmware_app.cpp` | `src/app/application.cpp` | `src/main.cpp` and raw-MVP entrypoint host test | Both sender/receiver raw-MVP compile/run test passes; all PIO role links pass |
| `stable_lib/gateway_app/lora_rx.cpp` | `src/app/gateway_radio.cpp` | Gateway app declarations, MVP host simulation, sender/RF-proof host checks | Gateway simulation, focused host set, and sender PIO build pass |
| `stable_lib/reliable_app/reliable_app.cpp` | `src/app/reliable_app.cpp` | Reliable app host test and compile-time role dispatcher | Sender/receiver reliable app tests and PIO builds pass |
| Reliable app's private `RecordedEvent` ring | `src/features/diagnostics/radio_diagnostics.h/.cpp` | Reliable app event callback and status flush; host queue test | FIFO wrap, overflow saturation, queue bounds and transport backpressure tests pass |

`stable_lib/lora/lora.h` and `stable_lib/firmware_app/firmware_app.h` remain include-only compatibility shims. They contain no implementation and do not create duplicate definitions. `stable_lib/gateway_app` retains I2C host integration; ARQ, MVP, reverse-raw, legacy applications, generated board mappings, and boot contracts remain in their existing owners.

Rollback is a path-level move: restore each implementation to its former file, restore the corresponding include/source-filter paths and test compile inputs, then rebuild the role matrix. No commit was made. Physical behavior remains unverified because no boards were present.
