# Shared Logic and Duplication Audit

## Outcome

Common device roles, stable port lookup, Flash layout, event-line parsing, event
names, and reliable transport now have one authoritative implementation each.
The four tool families remain adapters around those services; the CLI UI is not
imported by RF stress or production verification.

## Responsibilities and migration

| Responsibility | Previous implementations | Canonical source | Consumers / result |
|---|---|---|---|
| Firmware event line grammar and duplicate field handling | Regex and field extraction in `lora_chat.protocol` and `rf_stress.protocol_adapter` | `tools/device_detection/firmware_events.py` | Chat and RF stress now adapt `FirmwareEventLine` to their own outcome models. Duplicate fields are rejected centrally. |
| Gateway/Tracker role enum | Separate chat role enum plus device registry enum | `tools/device_detection/evidence.py::DeviceRole` | `lora_chat.protocol` re-exports the canonical enum; legacy RECEIVER/SENDER labels are converted at the adapter boundary. |
| Event names | Separate subsets in chat and RF stress | `FirmwareEventName` in `tools/device_detection/firmware_events.py` | Both tools use one string-valued enum containing the union of current firmware events. |
| Packet type and sequence widths | RF stress literals plus current LoRa JSON | `config/lora_system.json`, loaded by `validate_lora_ssot.load()` | RF stress packet types and sequence mask now derive from the validated protocol SSOT. Chat already loads the same source profile. |
| Physical role-to-port mapping | A removed `rf_proof.PORTS` map and a fixed `receiver_boot.PORT` constant | `config/current_hardware.json` via `tools/device_detection/hardware_registry.py` | Production bench, readback verification, and receiver snapshot tooling use the registry. The live MCU serial/signature still confirms the role. |
| Fuse-selected Flash sections and page rounding | Call-site-specific BOOT/APPCODE assumptions | `tools/device_detection/flash_layout.py` | SSOT validation, readback checks, production bench, and app-only programming use one half-open layout model. Readback byte comparison remains distinct from permission to write a page. |
| DATA/ACK/NACK state and retries | Potential second host ARQ vs firmware state | `src/shared/protocol/reliable_transport.h` | Gateway and Tracker share the existing C++ transport. ACK confirmation extends that state machine; no separate retry engine was added. |
| Production image and device verification | Tool-specific orchestration | `tools/rf_proof.py` plus `tools/production_bench.py` | The production bench builds `sender`/`receiver`; readback, layout, and target checks reuse `rf_proof` and the shared device registry. |

## Kept separate deliberately

`stable_lib/arq/` is a legacy ARQ implementation used by existing ARQ-focused
firmware and tests. `src/shared/protocol/reliable_transport.h` is the current
Gateway/Tracker transport. Their wire contracts and callers differ, so merging
them would create a new compatibility risk rather than remove duplicate
behavior.

The chat and RF stress tools also retain different typed result objects. Chat
needs decoded UTF-8 payloads and a full round-trip result; RF stress needs
fault-specific event fields and metrics. They now share parsing and canonical
roles, then adapt into those intentionally different outputs.

`tools/receiver_boot.py` still contains constants tied to its separately
reviewed legacy page-0 recovery package. It is not a general firmware-layout
source; physical writes remain separately authorized and the current live
BOOTSIZE=0 layout is rejected for APPCODE programming.

## Regression coverage

- Shared parser: RECEIVER-to-TRACKER normalization, field retention, duplicate
  rejection, and non-event filtering (`tests/test_firmware_events.py`).
- Both parser adapters: LoRa chat protocol/session tests and RF stress
  specifications.
- Role/port safety: `tests/test_hardware_registry.py`,
  `tests/test_role_detector.py`, and `tests/test_raw_mvp.py`.
- Layout and write boundaries: `tests/test_flash_layout.py`,
  `tests/test_rf_proof.py`, and `tests/test_receiver_boot.py`.
- Cross-language reliable transport: `tests/reliable_transport_test.cpp` and
  `tests/test_ssot_protocol.py`.

No historical evidence under `artifacts/` was removed or rewritten.
