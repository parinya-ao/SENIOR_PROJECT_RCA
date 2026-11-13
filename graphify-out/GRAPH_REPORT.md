# Graph Report - SENIOR_PROJECT_RCA  (2026-11-13)

## Corpus Check
- 245 files · ~103,286 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 547 file(s) not represented in the graph (top: .bin 443, .hex 57, .elf 14)
- WARNING: 547 of 793 files seen (69%) have no supported extractor and are missing from this graph entirely. It may look complete while representing only part of the codebase.

## Summary
- 2347 nodes · 4079 edges · 153 communities (105 shown, 48 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 397 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c4eab41a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Task
- EventId
- .TASK
- FIRMWARE MVP EXECUTION MODE
- validate_repo_isolation.py
- HardwareGateTests
- arq/main.cpp
- ssot.c
- generate_lora_config.py
- ring_buffer.h
- lora.cpp
- SEO optimization
- role_log_test.cpp
- Python Testing Patterns — Advanced Reference
- DeviceLayout
- PlatformResult
- upditerm.py
- Config
- config
- codec.cpp
- TaskLoraRx
- PacketReportWithAck
- config
- device.h
- Port
- stdint
- sleep.cpp
- effective_platformio_config
- FlashSafetyTests
- ProvisioningResult
- Python Code Executor
- UPDI-only Hello World MVP — STAR report
- MvpRoundtripTests
- config
- Fundamental Patterns
- json
- PacketReport
- mvp/main.cpp
- PacketBoot
- printf.cpp
- pathlib
- PacketAck
- PacketAdvertise
- config
- PacketMaintenance
- PacketMaintenanceAck
- espcomm.cpp
- config
- rf_test
- LiveProofTests
- mvp_board.cpp
- .test_no_meter_identity_uses_live_unique_serial_without_checklist
- device
- Gateway-to-Receiver SF7 Hello World
- Accessibility (a11y)
- radio
- config
- .parser
- SX1276
- radio
- json
- WCAG 2.2 Quick Reference
- pins
- pins
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
- string
- PROTOCOL.md
- STANDARDS.md
- TEST_PLAN.md
- pins
- radio
- radio
- radio
- radio
- State
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
- Raw LoRa ARQ V1 — STAR report
- pins
- pins
- CompiledHandoffTests
- RawEvidenceTests
- Frontend Design
- guard-100/manifest.json
- guard-50/H01/provenance/manifest.json
- guard-50/manifest.json
- raw_mvp_stub/SPI.h
- Pin Mapping Audit — AVR128DA28 / RFM95W
- SPIClass
- validate_live_proof
- memory_layout.h
- stub/SPI.h
- Gateway Hardware SSOT — Rudolph Gateway
- Bash Defensive Patterns
- detect_devices.py
- Common issues by impact
- Testing checklist
- capture-driver.py
- EepromBoundary
- lora

## God Nodes (most connected - your core abstractions)
1. `LoRa` - 38 edges
2. `State` - 38 edges
3. `HardwareGateTests` - 29 edges
4. `config` - 28 edges
5. `config` - 28 edges
6. `config` - 28 edges
7. `config` - 28 edges
8. `config` - 28 edges
9. `config` - 28 edges
10. `config` - 28 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `Capture`  [INFERRED]
  artifacts/arq-development/finish_standby.py → tools/arq_trial.py
- `run()` --uses--> `Capture`  [INFERRED]
  artifacts/arq-development/raw_regression.py → tools/arq_trial.py
- `main()` --calls--> `ssot_control_input_feed()`  [INFERRED]
  tests/ssot_protocol_test.c → src/ssot.c
- `main()` --calls--> `init_receiver_gpio()`  [INFERRED]
  tests/receiver_gpio_test.cpp → src/receiver/main.cpp
- `run()` --indirect_call--> `error()`  [INFERRED]
  artifacts/arq-development/turnaround_trials.py → third_party/upditerm/upditerm.py

## Import Cycles
- None detected.

## Communities (153 total, 48 thin omitted)

### Community 0 - "Task"
Cohesion: 0.06
Nodes (34): ReportEntry, day, hour, latitude, longitude, minute, month, quality (+26 more)

### Community 1 - "EventId"
Cohesion: 0.05
Nodes (41): Component, kApplication, kBoot, kHil, kNvm, Event(), EventId, kAuthenticationStarted (+33 more)

### Community 2 - ".TASK"
Cohesion: 0.26
Nodes (18): updi_role_log(), updi_role_log_airtime(), updi_role_log_boot(), updi_role_log_campaign(), updi_role_log_identity(), updi_role_log_identity_crc8(), updi_role_log_packet(), updi_role_log_payload() (+10 more)

### Community 3 - "FIRMWARE MVP EXECUTION MODE"
Cohesion: 0.20
Nodes (9): Deployment, Execution Priority, FIRMWARE MVP EXECUTION MODE, Hardware Scope, Mission, Output, Physical Radio Execution, Preserve SSOT (+1 more)

### Community 4 - "validate_repo_isolation.py"
Cohesion: 0.16
Nodes (12): RepositoryIsolationTests, _check_config(), _check_symlink(), _inside(), _items(), _label(), _local_dependency(), main() (+4 more)

### Community 7 - "arq/main.cpp"
Cohesion: 0.07
Nodes (54): arq_board, arq_frame, arq_receiver, arq_receiver_state, arq_result, arq_sender, arq_sender_state, board_ssot_init() (+46 more)

### Community 8 - "ssot.c"
Cohesion: 0.16
Nodes (34): claim_campaign_build(), decode_payload(), duplicate_tracker_reset_session(), encode_ack_or_nack_payload(), encode_header(), ssot_ack_matches(), ssot_campaign_acknowledge(), ssot_campaign_arm() (+26 more)

### Community 9 - "generate_lora_config.py"
Cohesion: 0.07
Nodes (25): ConfigurationTests, Radio915ValidationTests, valid_profile(), RawMvpTests, ReceiverHardwareTests, arq_artifacts(), load_arq(), validate_arq() (+17 more)

### Community 10 - "ring_buffer.h"
Cohesion: 0.09
Nodes (11): RingBuffer, buffer_, RingBuffer<Capacity>::Read(), RingBuffer<Capacity>::ReadByte(), RingBuffer<Capacity>::Write(), RingBuffer<Capacity>::WriteByte(), RingBuffer<Capacity>::WriteFrame(), first_free_ (+3 more)

### Community 11 - "lora.cpp"
Cohesion: 0.07
Nodes (44): Address, LoRa, _active_radio, LoRa::available(), _cs_pin, LoRa::get_last_rssi(), LoRa::init(), _initialized (+36 more)

### Community 12 - "SEO optimization"
Cohesion: 0.05
Nodes (38): Article, Breadcrumbs, FAQ, Organization, Product, Structured data reference, Validation, Agentic browsing and AI discoverability (+30 more)

### Community 13 - "role_log_test.cpp"
Cohesion: 0.10
Nodes (5): EepromSpy, reads, writes, main(), clear_capture()

### Community 14 - "Python Testing Patterns — Advanced Reference"
Cohesion: 0.05
Nodes (35): CI/CD Integration, Configuration Files, Pattern 10: Property-Based Testing, Pattern 6: Testing Async Code, Pattern 7: Monkeypatch for Testing, Pattern 8: Temporary Files and Directories, Pattern 9: Custom Fixtures and Conftest, Python Testing Patterns — Advanced Reference (+27 more)

### Community 15 - "DeviceLayout"
Cohesion: 0.11
Nodes (19): IsAppCodeRange(), DeviceLayout, kAppDataStart, kApplicationEnd, kApplicationImageEnd, kApplicationStart, kBootEnd, kBootSizePages (+11 more)

### Community 16 - "PlatformResult"
Cohesion: 0.13
Nodes (18): InitializeAdc(), ReadBatteryAdc(), ReadSample(), ReadTemperatureAdc(), WaitForConversion(), PlatformResult, kBusy, kForbidden (+10 more)

### Community 17 - "upditerm.py"
Cohesion: 0.07
Nodes (8): Console, error(), main(), parse_arguments(), SerialPort, SerialUPDI, Terminal, UPDI

### Community 18 - "Config"
Cohesion: 0.11
Nodes (18): Config, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 19 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 21 - "codec.cpp"
Cohesion: 0.27
Nodes (14): DecodePacketReport(), DecodePacketReportWithAck(), DecodeReportEntry(), EncodeConfig(), EncodePacketBoot(), EncodePacketReport(), EncodePacketReportWithAck(), EncodeReportEntry() (+6 more)

### Community 22 - "TaskLoraRx"
Cohesion: 0.12
Nodes (16): TaskLoraRx, _ack, _ack_bytes, _campaign_id, _dst, _flags, _id, _len (+8 more)

### Community 23 - "PacketReportWithAck"
Cohesion: 0.40
Nodes (4): PacketReportWithAck, report, seq, type

### Community 24 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 26 - "device.h"
Cohesion: 0.12
Nodes (15): PORT_struct, PORT_t, Revision, major, minor, raw_revision_id, SPI_struct, SPI_t (+7 more)

### Community 27 - "Port"
Cohesion: 0.25
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 28 - "stdint"
Cohesion: 0.08
Nodes (6): AdditionOverflows(), IsRangeWithin(), init_receiver_gpio(), setup(), CPUINT(), millis()

### Community 29 - "sleep.cpp"
Cohesion: 0.17
Nodes (6): SetUnixTime(), SleepState, force_wakeup, is_sleeping, last_rtc_ticks, unix_time

### Community 30 - "effective_platformio_config"
Cohesion: 0.18
Nodes (3): BuildAcceptanceTests, effective_platformio_config(), TargetLayoutTests

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
Cohesion: 0.12
Nodes (23): run(), BootAnalysisTests, analyze(), main(), normalize_ihex_region(), _parse_ihex(), ihex(), install() (+15 more)

### Community 39 - "PacketReport"
Cohesion: 0.40
Nodes (4): PacketReport, report, seq, type

### Community 40 - "mvp/main.cpp"
Cohesion: 0.06
Nodes (24): loop(), UpdiWrite(), debug_init(), debug_write(), debug_write_float(), debug_write_hex(), debug_write_int(), field() (+16 more)

### Community 41 - "PacketBoot"
Cohesion: 0.18
Nodes (10): DecodeConfig(), DecodePacketBoot(), LoadFloat(), PacketBoot, checkpoint, config, device_model, firmware (+2 more)

### Community 44 - "pathlib"
Cohesion: 0.14
Nodes (5): run(), I2cRadioConfigTests, ihex_record(), RfTestContinuationTests, SourceFingerprintTests

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

### Community 50 - "espcomm.cpp"
Cohesion: 0.10
Nodes (11): espcomm_setup(), StoreI2c16(), TaskI2CManager, _cmd, _ts, TaskI2CReset, _ts, DecodeLoraConfig() (+3 more)

### Community 51 - "config"
Cohesion: 0.07
Nodes (28): config, ack_max_ms, ack_min_ms, bandwidth_khz, coding_rate, crc_enabled, explicit_header, fault_ack_stride (+20 more)

### Community 52 - "rf_test"
Cohesion: 0.11
Nodes (43): application_bounds_for_environment(), application_layout_verified(), boot_fuses_match(), build_flag_defines(), capture_radio_spi_log(), capture_usb_topology(), check_port_owners(), clean_builds() (+35 more)

### Community 54 - "LiveProofTests"
Cohesion: 0.07
Nodes (11): fixture(), add(), boot(), LiveProofTests, emit(), start(), write(), ApplicationPageWriteTests (+3 more)

### Community 55 - "mvp_board.cpp"
Cohesion: 0.13
Nodes (13): CampaignBuildGateResult, AlreadyRun, ReadbackFailed, Ready, lora_rx_hello_boot(), lora_rx_setup(), lora_rx_start_lora(), setup() (+5 more)

### Community 61 - "device"
Cohesion: 0.06
Nodes (19): DetectionIntegrationTests, pio(), runner(), require(), DeviceReconnectTests, make_device(), make_probe(), require() (+11 more)

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
Cohesion: 0.28
Nodes (5): complete_campaign_logs(), packet_event(), payload_event(), RfEvidenceTests, parse_rf_campaign()

### Community 81 - "radio"
Cohesion: 0.17
Nodes (12): radio, bandwidth_khz, coding_rate, crc_enabled, explicit_header, frequency_hz, iq_inverted, preamble_symbols (+4 more)

### Community 82 - "json"
Cohesion: 0.14
Nodes (13): ArqTests, campaign(), Capture, checked_events(), main(), parse_event(), prepare(), reserve_session() (+5 more)

### Community 83 - "WCAG 2.2 Quick Reference"
Cohesion: 0.18
Nodes (8): Level A (minimum), Level AA (standard), Level AAA (enhanced), Sources, Success criteria by level, Testing tools, WCAG 2.2 Quick Reference, What changed from 2.1 to 2.2

### Community 85 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 86 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

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

### Community 103 - "string"
Cohesion: 0.24
Nodes (4): ssot_control_input_feed(), ssot_control_input_t, ssot_state_t, feed()

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

### Community 112 - "State"
Cohesion: 0.17
Nodes (12): State, begin_count, cs_high_seen, cs_low_seen, cs_pin, initialized, route, swap_count (+4 more)

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

### Community 125 - "Raw LoRa ARQ V1 — STAR report"
Cohesion: 0.22
Nodes (8): Action, Limits and next physical check, Operator stop for physical inspection (2026-11-13), Raw LoRa ARQ V1 — STAR report, Result, Safe software completion and final device state, Situation, Task

### Community 126 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 127 - "pins"
Cohesion: 0.33
Nodes (10): cs, dio1, enable, irq, miso, mosi, rst, sck (+2 more)

### Community 128 - "CompiledHandoffTests"
Cohesion: 0.20
Nodes (3): CompiledHandoffTests, SsotProtocolTests, ReceiveTests

### Community 130 - "Frontend Design"
Cohesion: 0.29
Nodes (6): Design principles, Frontend Design, Ground your designs in the subject matter, More on writing in design, Process: plan, review against the brief, build, critique, Restraint and self-critique

### Community 132 - "guard-100/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 133 - "guard-50/H01/provenance/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 134 - "guard-50/manifest.json"
Cohesion: 0.22
Nodes (8): boards, receiver, sender, config_hash, radio_power_active_level, spi_route, spi_route, source_hash

### Community 136 - "Pin Mapping Audit — AVR128DA28 / RFM95W"
Cohesion: 0.29
Nodes (6): Evidence basis, H1 connector, H2 connector and board signals, Pin Mapping Audit — AVR128DA28 / RFM95W, RF connector path, Verification

### Community 139 - "validate_live_proof"
Cohesion: 0.29
Nodes (4): radio_startup_matches(), shared_identity_matches(), single_packet_evidence_passed(), validate_live_proof()

### Community 148 - "Gateway Hardware SSOT — Rudolph Gateway"
Cohesion: 0.08
Nodes (21): ARQ debugging, UPDI register evidence, 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates (+13 more)

### Community 153 - "Bash Defensive Patterns"
Cohesion: 0.40
Nodes (4): Bash Defensive Patterns, Best Practices Summary, Detailed patterns and worked examples, When to Use This Skill

### Community 252 - "detect_devices.py"
Cohesion: 0.05
Nodes (47): build_parser(), _load_registry(), main(), _print_result(), _probe_device(), _run_self_test(), SafetyArgumentParser, _scan() (+39 more)

### Community 260 - "Common issues by impact"
Cohesion: 0.50
Nodes (4): Common issues by impact, Critical (fix immediately), Moderate (fix soon), Serious (fix before launch)

### Community 272 - "Testing checklist"
Cohesion: 0.67
Nodes (3): Automated testing, Manual testing, Testing checklist

### Community 285 - "capture-driver.py"
Cohesion: 0.16
Nodes (10): run(), pump(), start(), bootstrap(), create_temp_dir(), main(), bootstrap(), create_temp_dir() (+2 more)

### Community 298 - "EepromBoundary"
Cohesion: 0.25
Nodes (6): EepromBoundary, reads, stored, writes, written_bytes, wrong_address

## Knowledge Gaps
- **221 isolated node(s):** `latitude`, `longitude`, `quality`, `satellites`, `temperature` (+216 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1188 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **48 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `State` connect `State` to `stdint`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **What connects `latitude`, `longitude`, `quality` to the rest of the system?**
  _221 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Task` be split into smaller, more focused modules?**
  _Cohesion score 0.05747126436781609 - nodes in this community are weakly interconnected._
- **Why does `SX1276` connect `SX1276` to `lora.cpp`, `stdint`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Should `EventId` be split into smaller, more focused modules?**
  _Cohesion score 0.05204872646733112 - nodes in this community are weakly interconnected._
- **Why does `Config` connect `Config` to `PacketBoot`, `stdint`, `codec.cpp`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Should `HardwareGateTests` be split into smaller, more focused modules?**
  _Cohesion score 0.1038961038961039 - nodes in this community are weakly interconnected._