# Minimal C++ migration architecture

> Historical architecture for the first language migration. The current module map is [here](../architecture.md).

The existing boundaries already match the hardware. Keep SSOT serialization/campaign logic together, and retain separate ARQ codec, sender and receiver modules. Convert these four handwritten C implementations to C++17 free functions and aggregates. Keep existing `.h` include paths and function names so callers need no forwarding headers or wrappers. Use typed constants, scoped state enums with the original integer representation, value initialization, explicit conversions and private helper namespaces. Retain byte arrays because the AVR toolchain lacks C++ standard-library headers.

There are no new classes, dependencies, runtime dispatch, allocation or hardware wrappers. Wire constants remain byte values; frames continue to be encoded field by field. State and buffers remain caller-owned. Document nullable arguments, unchanged output on decode failure, terminal states, rollover assumptions and replay protection at declarations and non-obvious operations.

Execution order: preserve the original build/test evidence; make builds validate protected configuration and update only provenance; migrate SSOT and its host consumers; migrate ARQ codec, sender and receiver with their existing characterization tests; run all role builds, full host suite, supported static analysis and formatting; compare image sections and inspect the complete diff. Keep boot, vendor and generated C intact. No flash, EEPROM, fuse, or RF operation is authorized.
