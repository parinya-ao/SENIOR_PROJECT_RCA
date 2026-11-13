# Graph Report - SENIOR_PROJECT_RCA  (2026-11-13)

## Corpus Check
- 373 files · ~175,583 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 846 file(s) not represented in the graph (top: .bin 683, .hex 95, .elf 24)
- WARNING: 846 of 1226 files seen (69%) have no supported extractor and are missing from this graph entirely. It may look complete while representing only part of the codebase.

## Summary
- 2996 nodes · 5413 edges · 205 communities (144 shown, 61 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 450 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1e2dd303`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Task
- EventId
- .TASK
- FIRMWARE MVP EXECUTION MODE
- validate_repo_isolation.py
- HardwareGateTests
- arq.h
- source/src/ssot.c
- generate_lora_config.py
- ring_buffer.h
- LoRa
- SEO optimization
- role_log_test.cpp
- Python Testing Patterns — Advanced Reference
- DeviceLayout
- PlatformResult
- SerialUPDI
- Config
- config
- codec.cpp
- TaskLoraRx
- PacketReport
- config
- device.h
- Port
- RCATests
- Task
- tools/arq_trial.py
- FlashSafetyTests
- ProvisioningResult
- Python Code Executor
- UPDI-only Hello World MVP — STAR report
- MvpRoundtripTests
- config
- Fundamental Patterns
- json
- Forensic RCA — reverse raw LoRa, 2026-11-13
- src/mvp/main.cpp
- PacketBoot
- .TASK
- DetectionIntegrationTests
- pathlib
- PacketAck
- PacketAdvertise
- config
- PacketMaintenance
- PacketMaintenanceAck
- sleep.cpp
- config
- rf_test
- LiveProofTests
- stub/SPI.h
- follow-up-software/tools/arq_trial.py
- device
- Gateway-to-Receiver SF7 Hello World
- ReceiveTests
- Accessibility (a11y)
- radio
- config
- .parser
- SX1276
- radio
- Capture
- WCAG 2.2 Quick Reference
- json
- pins
- pins
- Gate1Tests
- rca-20261113/README.md
- rf_proof.py
- config
- provenance/manifest.json
- 20261113T074154Z/manifest.json
- config
- config
- radio
- radio
- Accessibility Code Patterns
- Operable
- radio
- progress.md
- State
- source/src/arq/main.cpp
- PROTOCOL.md
- STANDARDS.md
- TEST_PLAN.md
- pins
- radio
- radio
- radio
- radio
- src/arq/main.cpp
- pins
- Connect to a virtual UART on an AVR via UPDI
- Common ARIA patterns
- Understandable
- pins
- SenderOneShotTests
- pins
- pins
- 20261113T074705Z/H01/provenance/manifest.json
- 20261113T074705Z/manifest.json
- 20261113T075357Z/H01/provenance/manifest.json
- 20261113T075357Z/manifest.json
- stub/Arduino.h
- pins
- pins
- CompiledHandoffTests
- RawEvidenceTests
- Frontend Design
- config
- guard-100/manifest.json
- guard-50/H01/provenance/manifest.json
- guard-50/manifest.json
- sender.c
- Pin Mapping Audit — AVR128DA28 / RFM95W
- SPIClass
- config
- Exact RadioLib and register audit
- Bus
- arduino
- ErrataDiagnosticsTests
- log_slot
- Radio915ValidationTests
- validate_live_proof
- source/src/reverse_raw/main.cpp
- RawMvpTests
- Gateway Hardware SSOT — Rudolph Gateway
- lora_rx.cpp
- radio
- radio
- STAR — Tracker→Rudolph receiver errata and transport follow-up
- Bash Defensive Patterns
- CaptureTests
- pins
- pins
- Proposed discriminating experiments — NOT executed or authorized here
- 20261113T084503Z/H01/provenance/manifest.json
- 20261113T084503Z/manifest.json
- stdint
- Receiver errata audit — offline follow-up, 2026-11-13
- SerialUPDI
- UPDI
- Raw LoRa ARQ V1 — STAR report
- radio_stub/RadioLib.h
- Evidence index
- RADIOLIB.md
- ReportEntry
- UPDI
- follow-up-software/third_party/upditerm/upditerm.py
- DeviceReconnectTests
- Gate 1 command and initialization audit
- SerialPort
- Tracker Hardware SSOT — LoRa Tracker RFM
- Terminal
- Power and reset evidence
- SerialPort
- Terminal
- ReceiveTests
- task.h
- .test_usb_topology_capture_records_read_only_inventory_commands
- rca_send_test.cpp
- ERRATA_FOLLOWUP_STAR.md
- reverse_raw_test.cpp
- memory_layout.h
- PacketReportWithAck
- stub/SPI.h
- SsotProtocolTests
- adapter_test.cpp
- parse_test_counts
- parse_raw_mvp_logs
- detect_devices.py
- Common issues by impact
- Testing checklist
- time
- string
- lora

## God Nodes (most connected - your core abstractions)
1. `LoRa` - 38 edges
2. `State` - 38 edges
3. `RCATests` - 33 edges
4. `analyze()` - 31 edges
5. `HardwareGateTests` - 29 edges
6. `config` - 28 edges
7. `config` - 28 edges
8. `config` - 28 edges
9. `config` - 28 edges
10. `config` - 28 edges

## Surprising Connections (you probably didn't know these)
- `Framing, adapter and lifecycle` --references--> `flush()`  [INFERRED]
  docs/arq/investigations/rca-20261113/UPDI_ANALYSIS.md → tests/test_live_rf_proof.py
- `CaptureTests` --uses--> `Capture`  [INFERRED]
  tests/test_arq_capture.py → tools/arq_trial.py
- `ArqTests` --uses--> `Capture`  [INFERRED]
  tests/test_arq.py → tools/arq_trial.py
- `run()` --calls--> `Capture`  [INFERRED]
  artifacts/arq-development/finish_standby.py → tools/arq_trial.py
- `run()` --uses--> `Capture`  [INFERRED]
  artifacts/arq-development/raw_regression.py → tools/arq_trial.py

## Import Cycles
- None detected.

## Communities (205 total, 61 thin omitted)

### Community 0 - "Task"
Cohesion: 0.15
Nodes (17): day, hour, minute, month, second, year, GetUnixTime(), GetCurrentTimeString() (+9 more)

### Community 1 - "EventId"
Cohesion: 0.05
Nodes (41): Component, kApplication, kBoot, kHil, kNvm, Event(), EventId, kAuthenticationStarted (+33 more)

### Community 2 - ".TASK"
Cohesion: 0.37
Nodes (16): updi_role_log(), updi_role_log_airtime(), updi_role_log_boot(), updi_role_log_campaign(), updi_role_log_identity(), updi_role_log_identity_crc8(), updi_role_log_packet(), updi_role_log_payload() (+8 more)

### Community 3 - "FIRMWARE MVP EXECUTION MODE"
Cohesion: 0.20
Nodes (9): Deployment, Execution Priority, FIRMWARE MVP EXECUTION MODE, Hardware Scope, Mission, Output, Physical Radio Execution, Preserve SSOT (+1 more)

### Community 4 - "validate_repo_isolation.py"
Cohesion: 0.16
Nodes (12): RepositoryIsolationTests, _check_config(), _check_symlink(), _inside(), _items(), _label(), _local_dependency(), main() (+4 more)

### Community 5 - "HardwareGateTests"
Cohesion: 0.05
Nodes (10): BuildAcceptanceTests, effective_platformio_config(), HardwareGateTests, TargetLayoutTests, hardware_blockers(), parse_radio_spi_log(), parse_role_log_count(), parse_wrapper_check_count() (+2 more)

### Community 7 - "arq.h"
Cohesion: 0.19
Nodes (16): arq_frame, arq_receiver, arq_receiver_state, arq_result, arq_sender_state, arq_decode(), arq_encode(), arq_valid() (+8 more)

### Community 8 - "source/src/ssot.c"
Cohesion: 0.10
Nodes (34): decode_payload(), duplicate_tracker_reset_session(), encode_ack_or_nack_payload(), encode_header(), ssot_ack_matches(), ssot_campaign_acknowledge(), ssot_campaign_arm(), ssot_campaign_fail() (+26 more)

### Community 9 - "generate_lora_config.py"
Cohesion: 0.10
Nodes (21): parse_arguments(), ConfigurationTests, ReceiverHardwareTests, arq_artifacts(), load_arq(), validate_arq(), artifacts(), canonical() (+13 more)

### Community 10 - "ring_buffer.h"
Cohesion: 0.09
Nodes (11): RingBuffer, buffer_, RingBuffer<Capacity>::Read(), RingBuffer<Capacity>::ReadByte(), RingBuffer<Capacity>::Write(), RingBuffer<Capacity>::WriteByte(), RingBuffer<Capacity>::WriteFrame(), first_free_ (+3 more)

### Community 11 - "LoRa"
Cohesion: 0.05
Nodes (56): Address, LoRa, _active_radio, LoRa::available(), _cs_pin, LoRa::get_last_rssi(), LoRa::init(), _initialized (+48 more)

### Community 12 - "SEO optimization"
Cohesion: 0.05
Nodes (38): Article, Breadcrumbs, FAQ, Organization, Product, Structured data reference, Validation, Agentic browsing and AI discoverability (+30 more)

### Community 13 - "role_log_test.cpp"
Cohesion: 0.11
Nodes (4): init_receiver_gpio(), setup(), main(), clear_capture()

### Community 14 - "Python Testing Patterns — Advanced Reference"
Cohesion: 0.05
Nodes (35): CI/CD Integration, Configuration Files, Pattern 10: Property-Based Testing, Pattern 6: Testing Async Code, Pattern 7: Monkeypatch for Testing, Pattern 8: Temporary Files and Directories, Pattern 9: Custom Fixtures and Conftest, Python Testing Patterns — Advanced Reference (+27 more)

### Community 15 - "DeviceLayout"
Cohesion: 0.12
Nodes (18): DeviceLayout, kAppDataStart, kApplicationEnd, kApplicationImageEnd, kApplicationStart, kBootEnd, kBootSizePages, kBootStart (+10 more)

### Community 16 - "PlatformResult"
Cohesion: 0.13
Nodes (18): InitializeAdc(), ReadBatteryAdc(), ReadSample(), ReadTemperatureAdc(), WaitForConversion(), PlatformResult, kBusy, kForbidden (+10 more)

### Community 17 - "SerialUPDI"
Cohesion: 0.14
Nodes (3): Console, main(), SerialUPDI

### Community 18 - "Config"
Cohesion: 0.11
Nodes (18): Config, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 19 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 21 - "codec.cpp"
Cohesion: 0.22
Nodes (17): DecodeConfig(), DecodePacketBoot(), DecodePacketReport(), DecodePacketReportWithAck(), DecodeReportEntry(), EncodeConfig(), EncodePacketBoot(), EncodePacketReport() (+9 more)

### Community 22 - "TaskLoraRx"
Cohesion: 0.12
Nodes (16): TaskLoraRx, _ack, _ack_bytes, _campaign_id, _dst, _flags, _id, _len (+8 more)

### Community 23 - "PacketReport"
Cohesion: 0.25
Nodes (4): PacketReport, report, seq, type

### Community 24 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 26 - "device.h"
Cohesion: 0.12
Nodes (16): IsAppCodeRange(), PORT_struct, PORT_t, Revision, major, minor, raw_revision_id, SPI_struct (+8 more)

### Community 27 - "Port"
Cohesion: 0.25
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 28 - "RCATests"
Cohesion: 0.09
Nodes (9): RCATests, analyze(), load(), read(), classify(), compare_snapshots(), delta(), main() (+1 more)

### Community 29 - "Task"
Cohesion: 0.13
Nodes (7): Task, is_paused_, pt_, wakeup_time_, TaskScheduler, task_count_, tasks_

### Community 30 - "tools/arq_trial.py"
Cohesion: 0.11
Nodes (18): run(), ArqTests, campaign(), checked_events(), main(), parse_event(), prepare(), reserve_session() (+10 more)

### Community 31 - "FlashSafetyTests"
Cohesion: 0.12
Nodes (3): FlashSafetyTests, command(), boot_fuses_match()

### Community 32 - "ProvisioningResult"
Cohesion: 0.25
Nodes (9): ProvisioningResult, kInvalidArgument, kOk, kUnprovisioned, kUnsupported, IsHmacKeyProvisioned(), ReadDeviceUid(), ReadHmacKey() (+1 more)

### Community 33 - "Python Code Executor"
Cohesion: 0.08
Nodes (24): 3D Model Processing, 3D Processing, API Calls, App Details, Data Analysis with Visualization, Data Processing, Documentation, Documents & Graphics (+16 more)

### Community 34 - "UPDI-only Hello World MVP — STAR report"
Cohesion: 0.25
Nodes (7): Action, Evidence, Result, Situation, Task, UPDI-only Hello World MVP — STAR report, Verification and limits

### Community 35 - "MvpRoundtripTests"
Cohesion: 0.26
Nodes (3): Board, frames(), MvpRoundtripTests

### Community 36 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 37 - "Fundamental Patterns"
Cohesion: 0.09
Nodes (21): 1. Strict Mode, 2. Error Trapping and Cleanup, 3. Variable Safety, 4. Array Handling, 5. Conditional Safety, Advanced Defensive Techniques, bash-defensive-patterns — detailed patterns and worked examples, Core Defensive Principles (+13 more)

### Community 38 - "json"
Cohesion: 0.13
Nodes (18): BootAnalysisTests, BuildIdentityImagesTests, analyze(), main(), normalize_ihex_region(), _parse_ihex(), ihex(), install() (+10 more)

### Community 39 - "Forensic RCA — reverse raw LoRa, 2026-11-13"
Cohesion: 0.12
Nodes (16): 10. Unresolved questions, 11. Root cause verdict, 12. Recommended corrective action, 13. Verification plan, 14. Risks and limitations, 15. STAR summary, 1. Executive summary, 2. Scope (+8 more)

### Community 40 - "src/mvp/main.cpp"
Cohesion: 0.07
Nodes (33): debug_init(), debug_write(), debug_write_float(), debug_write_hex(), debug_write_int(), field(), line(), loop() (+25 more)

### Community 41 - "PacketBoot"
Cohesion: 0.25
Nodes (7): PacketBoot, checkpoint, config, device_model, firmware, reset_flags, type

### Community 42 - ".TASK"
Cohesion: 0.15
Nodes (31): claim_campaign_build(), decode_payload(), encode_ack_or_nack_payload(), encode_header(), ssot_ack_matches(), ssot_campaign_acknowledge(), ssot_campaign_arm(), ssot_campaign_build_id() (+23 more)

### Community 43 - "DetectionIntegrationTests"
Cohesion: 0.17
Nodes (4): DetectionIntegrationTests, pio(), runner(), require()

### Community 44 - "pathlib"
Cohesion: 0.08
Nodes (6): run(), start(), I2cRadioConfigTests, RadioLibHalTests, RfTestContinuationTests, SourceFingerprintTests

### Community 45 - "PacketAck"
Cohesion: 0.33
Nodes (5): DecodePacketAck(), EncodePacketAck(), PacketAck, seq, type

### Community 46 - "PacketAdvertise"
Cohesion: 0.33
Nodes (5): DecodePacketAdvertise(), EncodePacketAdvertise(), PacketAdvertise, seq, type

### Community 47 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 48 - "PacketMaintenance"
Cohesion: 0.33
Nodes (5): DecodePacketMaintenance(), EncodePacketMaintenance(), PacketMaintenance, command, type

### Community 49 - "PacketMaintenanceAck"
Cohesion: 0.33
Nodes (5): DecodePacketMaintenanceAck(), EncodePacketMaintenanceAck(), PacketMaintenanceAck, response, type

### Community 50 - "sleep.cpp"
Cohesion: 0.17
Nodes (6): SetUnixTime(), SleepState, force_wakeup, is_sleeping, last_rtc_ticks, unix_time

### Community 51 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 52 - "rf_test"
Cohesion: 0.25
Nodes (21): capture_radio_spi_log(), capture_usb_topology(), check_port_owners(), clean_builds(), host_tests(), identify_targets(), main(), new_run() (+13 more)

### Community 54 - "LiveProofTests"
Cohesion: 0.06
Nodes (18): Actual call graph and contracts, Captured evidence, Framing, adapter and lifecycle, Manufacturer cross-check and missing telemetry, UPDI first-failure boundary, fixture(), add(), boot() (+10 more)

### Community 57 - "follow-up-software/tools/arq_trial.py"
Cohesion: 0.14
Nodes (20): error(), audit_raw_configuration(), campaign(), Capture, complete(), checked_events(), main(), park_reverse() (+12 more)

### Community 61 - "device"
Cohesion: 0.15
Nodes (9): crc8(), FirmwareIdentityTests, ihex_record(), marker(), require(), device(), probe(), require() (+1 more)

### Community 68 - "Gateway-to-Receiver SF7 Hello World"
Cohesion: 0.25
Nodes (7): Current result — Receiver installed, normal startup unresolved, Gateway-to-Receiver SF7 Hello World, No-meter read-only hardware verified; Receiver write wiring unconfirmed, Receiver boot incompatibility, Remaining physical prerequisites, Single-packet behavior and identities, Verified software result

### Community 75 - "Accessibility (a11y)"
Cohesion: 0.17
Nodes (12): Accessibility (a11y), ARIA usage (4.1.2), Color contrast (1.4.3, 1.4.6), Conformance levels, Evidence-led audit workflow, Live regions (4.1.3), Media alternatives (1.2), Perceivable (+4 more)

### Community 77 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 78 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 79 - ".parser"
Cohesion: 0.38
Nodes (4): complete_campaign_logs(), packet_event(), payload_event(), RfEvidenceTests

### Community 81 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 82 - "Capture"
Cohesion: 0.08
Nodes (9): ReverseRawTests, ReverseRawTests, audit_raw_configuration(), Capture, complete(), park_reverse(), reverse_exchange(), status() (+1 more)

### Community 83 - "WCAG 2.2 Quick Reference"
Cohesion: 0.18
Nodes (8): Level A (minimum), Level AA (standard), Level AAA (enhanced), Sources, Success criteria by level, Testing tools, WCAG 2.2 Quick Reference, What changed from 2.1 to 2.2

### Community 84 - "json"
Cohesion: 0.12
Nodes (19): audit_raw_configuration(), campaign(), Capture, complete(), checked_events(), main(), parse_event(), prepare() (+11 more)

### Community 85 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 86 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 87 - "Gate1Tests"
Cohesion: 0.15
Nodes (5): Gate1Tests, rows(), transaction(), response(), verify_hashes()

### Community 88 - "rca-20261113/README.md"
Cohesion: 0.29
Nodes (4): Confirmed and derived findings only, Firmware SEND audit, Hypothesis matrix, Offline RCA — Tracker to Rudolph

### Community 89 - "rf_proof.py"
Cohesion: 0.19
Nodes (18): application_bounds_for_environment(), application_layout_verified(), build_flag_defines(), _config_int(), effective_project_sections(), image_fits_application(), parse_ihex_range(), prepare_receiver_boot() (+10 more)

### Community 90 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 91 - "provenance/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 93 - "20261113T074154Z/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 94 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 95 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 96 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 97 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 98 - "Accessibility Code Patterns"
Cohesion: 0.22
Nodes (9): Accessibility Code Patterns, ARIA tabs, Dragging movements, Error handling, Form labels, Live regions and notifications, Modal focus trap, Screen reader commands (+1 more)

### Community 99 - "Operable"
Cohesion: 0.22
Nodes (9): Dragging movements (2.5.7) — new in 2.2, Focus not obscured (2.4.11) — new in 2.2, Focus visible (2.4.7), Keyboard accessible (2.1), Motion (2.3), Operable, Skip links (2.4.1), Target size (2.5.8) — new in 2.2 (+1 more)

### Community 100 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 102 - "State"
Cohesion: 0.05
Nodes (38): State, airtime_length, airtime_us, bandwidth_khz, begin_calls, begin_status, coding_rate, config_status (+30 more)

### Community 103 - "source/src/arq/main.cpp"
Cohesion: 0.39
Nodes (15): command(), command_byte(), discard(), event(), fatal(), frame_event(), loop(), receive() (+7 more)

### Community 107 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 108 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 109 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 110 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 111 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 112 - "src/arq/main.cpp"
Cohesion: 0.39
Nodes (15): command(), command_byte(), discard(), event(), fatal(), frame_event(), loop(), receive() (+7 more)

### Community 113 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 114 - "Connect to a virtual UART on an AVR via UPDI"
Cohesion: 0.22
Nodes (8): Connect to a virtual UART on an AVR via UPDI, Demo program, License, Prerequisites, UPDI interface, Upditerm, Usage, Virtual UART

### Community 115 - "Common ARIA patterns"
Cohesion: 0.25
Nodes (8): Buttons, Common ARIA patterns, Error states, Form fields, Links, Live regions, Modals, Navigation

### Community 116 - "Understandable"
Cohesion: 0.25
Nodes (8): Accessible authentication (3.3.8) — new in 2.2, Consistent help (3.2.6) — new in 2.2, Consistent navigation (3.2.3), Error handling (3.3.1, 3.3.3), Form labels (3.3.2), Page language (3.1.1), Redundant entry (3.3.7) — new in 2.2, Understandable

### Community 117 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 119 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 120 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 121 - "20261113T074705Z/H01/provenance/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 122 - "20261113T074705Z/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 123 - "20261113T075357Z/H01/provenance/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 124 - "20261113T075357Z/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 125 - "stub/Arduino.h"
Cohesion: 0.13
Nodes (8): setup(), setup(), arq_board, board_ssot_init(), setup(), setup(), random(), randomSeed()

### Community 126 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 127 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 130 - "Frontend Design"
Cohesion: 0.29
Nodes (6): Design principles, Frontend Design, Ground your designs in the subject matter, More on writing in design, Process: plan, review against the brief, build, critique, Restraint and self-critique

### Community 131 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 132 - "guard-100/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 133 - "guard-50/H01/provenance/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 134 - "guard-50/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 135 - "sender.c"
Cohesion: 0.39
Nodes (15): arq_sender, arq_due(), arq_sender_active(), arq_sender_arm(), arq_sender_control(), arq_sender_init(), arq_sender_poll(), arq_sender_request() (+7 more)

### Community 136 - "Pin Mapping Audit — AVR128DA28 / RFM95W"
Cohesion: 0.29
Nodes (6): Evidence basis, H1 connector, H2 connector and board signals, Pin Mapping Audit — AVR128DA28 / RFM95W, RF connector path, Verification

### Community 138 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 139 - "Exact RadioLib and register audit"
Cohesion: 0.33
Nodes (5): Confirmed errata configuration concern, causal status UNKNOWN, Exact RadioLib and register audit, Initialization and lifecycle, Register definitions and operational evidence, Version clues, not upgrades

### Community 140 - "Bus"
Cohesion: 0.07
Nodes (11): printf(), Bus, fifo, finish_delay, regs, reset_mode, ticks, main() (+3 more)

### Community 141 - "arduino"
Cohesion: 0.10
Nodes (5): init_gpio(), loop(), ReadTemperatureCelsius(), TaskHeartbeat, _ts

### Community 142 - "ErrataDiagnosticsTests"
Cohesion: 0.18
Nodes (4): ErrataDiagnosticsTests, decode_snapshot(), interpret_rx(), link_budget()

### Community 143 - "log_slot"
Cohesion: 0.38
Nodes (11): log_flush(), log_slot(), command(), command_byte(), configuration(), counter(), event(), loop() (+3 more)

### Community 144 - "Radio915ValidationTests"
Cohesion: 0.22
Nodes (4): Radio915ValidationTests, valid_profile(), validate_radio_profile(), check()

### Community 145 - "validate_live_proof"
Cohesion: 0.17
Nodes (7): parse_rf_campaign(), radio_startup_matches(), identity(), lines(), shared_identity_matches(), single_packet_evidence_passed(), validate_live_proof()

### Community 146 - "source/src/reverse_raw/main.cpp"
Cohesion: 0.47
Nodes (9): command(), command_byte(), configuration(), counter(), event(), loop(), observation(), status() (+1 more)

### Community 148 - "Gateway Hardware SSOT — Rudolph Gateway"
Cohesion: 0.18
Nodes (11): 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates, Gateway Hardware SSOT — Rudolph Gateway, H1 (10-pin; only pins 1–5 used in the source schematic) (+3 more)

### Community 149 - "lora_rx.cpp"
Cohesion: 0.06
Nodes (22): espcomm_setup(), StoreI2c16(), TaskI2CManager, _cmd, _ts, TaskI2CReset, _ts, CampaignBuildGateResult (+14 more)

### Community 150 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 151 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 152 - "STAR — Tracker→Rudolph receiver errata and transport follow-up"
Cohesion: 0.33
Nodes (6): A — Decision logic and execution, R — Result, proposed minimum correction and limits, Reproduce offline, S — Situation, STAR — Tracker→Rudolph receiver errata and transport follow-up, T — Task and hard constraints

### Community 153 - "Bash Defensive Patterns"
Cohesion: 0.40
Nodes (4): Bash Defensive Patterns, Best Practices Summary, Detailed patterns and worked examples, When to Use This Skill

### Community 155 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 156 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 157 - "Proposed discriminating experiments — NOT executed or authorized here"
Cohesion: 0.33
Nodes (5): Evidence-ranked hypothesis matrix, Gate 1 — transport and power evidence, Gate 2 — receiver-only IF A/B, Gate 3 — reference isolation and business ranking, Proposed discriminating experiments — NOT executed or authorized here

### Community 158 - "20261113T084503Z/H01/provenance/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 159 - "20261113T084503Z/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 160 - "stdint"
Cohesion: 0.09
Nodes (7): AdditionOverflows(), IsRangeWithin(), DecodeLoraConfig(), EepromSpy, reads, writes, main()

### Community 161 - "Receiver errata audit — offline follow-up, 2026-11-13"
Cohesion: 0.40
Nodes (5): Applicability to 915 MHz / BW125 / SF7, Counter and receive-event interpretation, Exact receiver-IF candidate, RadioLib implementation of record, Receiver errata audit — offline follow-up, 2026-11-13

### Community 162 - "SerialUPDI"
Cohesion: 0.14
Nodes (3): Console, main(), SerialUPDI

### Community 164 - "Raw LoRa ARQ V1 — STAR report"
Cohesion: 0.06
Nodes (26): ARQ debugging, UPDI register evidence, Reverse-raw acquisition — 2026-11-13 12:06:29 UTC, Reverse raw — 2026-11-13 12:15:06 UTC, Driver and IRQ audit, Physical result, Repository and prior evidence, Reverse raw readiness and radio audit — 20261113T123510Z (+18 more)

### Community 166 - "Evidence index"
Cohesion: 0.50
Nodes (4): 20261113T121506Z-reverse-raw, 20261113T123620Z-reverse-raw, 20261113T123837Z-standby, Evidence index

### Community 168 - "ReportEntry"
Cohesion: 0.25
Nodes (8): ReportEntry, latitude, longitude, quality, satellites, temperature, ttf, vbat

### Community 171 - "DeviceReconnectTests"
Cohesion: 0.54
Nodes (4): DeviceReconnectTests, make_device(), make_probe(), require()

### Community 172 - "Gate 1 command and initialization audit"
Cohesion: 0.29
Nodes (6): Derived mailbox exchange, not a wire capture, Gate 1 command and initialization audit, Historical first failure, kept separate from this blocked run, PESIG and primary references, Repository and implementation of record, Ten source-level safety questions

### Community 174 - "Tracker Hardware SSOT — LoRa Tracker RFM"
Cohesion: 0.18
Nodes (9): Design facts and physical unknowns, 1. Board identity and components, 2. AVR128DA28 pin and net SSOT, 3. Power and startup contract, 4. Minimal firmware implementation contract, 5. Acceptance criteria / physical evidence, Exact LoRa RFM95W signal map, Sources (+1 more)

### Community 176 - "Power and reset evidence"
Cohesion: 0.67
Nodes (3): DA-specific fuse/reset interpretation, Power and reset evidence, Smallest discriminating measurements — future authorization only

### Community 184 - "ERRATA_FOLLOWUP_STAR.md"
Cohesion: 0.22
Nodes (6): Exact register comparison and real-driver write order, FACT: option0, 25 modeled register writes, FACT: option1, 29 modeled register writes, Source call order, Claim and source log — 2026-11-13 follow-up, Reproducible verification

### Community 185 - "reverse_raw_test.cpp"
Cohesion: 0.60
Nodes (3): cmd(), logged(), main()

### Community 187 - "PacketReportWithAck"
Cohesion: 0.40
Nodes (4): PacketReportWithAck, report, seq, type

### Community 252 - "detect_devices.py"
Cohesion: 0.05
Nodes (47): build_parser(), _load_registry(), main(), _print_result(), _probe_device(), _run_self_test(), SafetyArgumentParser, _scan() (+39 more)

### Community 260 - "Common issues by impact"
Cohesion: 0.50
Nodes (4): Common issues by impact, Critical (fix immediately), Moderate (fix soon), Serious (fix before launch)

### Community 272 - "Testing checklist"
Cohesion: 0.67
Nodes (3): Automated testing, Manual testing, Testing checklist

### Community 285 - "time"
Cohesion: 0.24
Nodes (7): run(), bootstrap(), create_temp_dir(), main(), bootstrap(), create_temp_dir(), main()

### Community 298 - "string"
Cohesion: 0.09
Nodes (6): EepromBoundary, reads, stored, writes, written_bytes, wrong_address

## Knowledge Gaps
- **228 isolated node(s):** `latitude`, `longitude`, `quality`, `satellites`, `temperature` (+223 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1434 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **61 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `State` connect `State` to `radio_stub/RadioLib.h`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **What connects `latitude`, `longitude`, `quality` to the rest of the system?**
  _228 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `EventId` be split into smaller, more focused modules?**
  _Cohesion score 0.05204872646733112 - nodes in this community are weakly interconnected._
- **Why does `HardwareGateTests` connect `HardwareGateTests` to `parse_test_counts`, `pathlib`, `.test_usb_topology_capture_records_read_only_inventory_commands`, `FlashSafetyTests`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `HardwareGateTests` be split into smaller, more focused modules?**
  _Cohesion score 0.050170068027210885 - nodes in this community are weakly interconnected._
- **Should `source/src/ssot.c` be split into smaller, more focused modules?**
  _Cohesion score 0.10384068278805121 - nodes in this community are weakly interconnected._
- **Should `generate_lora_config.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10256410256410256 - nodes in this community are weakly interconnected._