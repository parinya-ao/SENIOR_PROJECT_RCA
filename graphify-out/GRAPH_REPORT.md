# Graph Report - SENIOR_PROJECT_RCA  (2026-11-13)

## Corpus Check
- 143 files · ~69,385 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 57 file(s) not represented in the graph (top: .bin 39, (none) 7, .xml 3)
- WARNING: 57 of 201 files seen (28%) have no supported extractor and are missing from this graph entirely. It may look complete while representing only part of the codebase.

## Summary
- 1578 nodes · 2872 edges · 104 communities (61 shown, 43 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 293 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d3e6c20a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Task
- EventId
- FIRMWARE MVP EXECUTION MODE
- tempfile
- HardwareGateTests
- src/time-utils.h
- ssot.c
- tempfile
- ring_buffer.h
- LoRa
- SEO optimization
- role_log_test.cpp
- Python Testing Patterns — Advanced Reference
- DeviceLayout
- PlatformResult
- upditerm.py
- Config
- src/time-utils.h
- codec.cpp
- TaskLoraRx
- require
- device.h
- Port
- stdint
- SleepState
- effective_platformio_config
- FlashSafetyTests
- ProvisioningResult
- Python Code Executor
- lib/main.cpp
- MvpRoundtripTests
- updi-baseline/src/receiver/main.cpp
- Fundamental Patterns
- TaskI2CReset
- PacketReport
- ssot.h
- PacketBoot
- printf.cpp
- PacketAck
- PacketAdvertise
- PacketMaintenance
- PacketMaintenanceAck
- espcomm.cpp
- mvp_stub/Arduino.h
- memory_layout.h
- LiveProofTests
- lora_rx.cpp
- task.h
- device
- Gateway-to-Receiver SF7 Hello World
- Accessibility (a11y)
- .parser
- SX1276
- WCAG 2.2 Quick Reference
- Accessibility Code Patterns
- Operable
- State
- Connect to a virtual UART on an AVR via UPDI
- Common ARIA patterns
- Understandable
- SenderOneShotTests
- .TASK
- Frontend Design
- State
- Gateway Hardware SSOT — Rudolph Gateway
- .test_no_meter_identity_uses_live_unique_serial_without_checklist
- Bash Defensive Patterns
- detect_devices.py
- Common issues by impact
- Testing checklist
- rf_proof.py
- EepromBoundary
- lora

## God Nodes (most connected - your core abstractions)
1. `LoRa` - 38 edges
2. `State` - 38 edges
3. `HardwareGateTests` - 29 edges
4. `SX1276` - 25 edges
5. `rf_test()` - 24 edges
6. `main()` - 24 edges
7. `DeviceLayout` - 23 edges
8. `TaskLoraRx` - 22 edges
9. `Config` - 22 edges
10. `loop()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `lora_rx_reject_config()` --calls--> `updi_role_log()`  [INFERRED]
  src/sender/lib/lora_rx.cpp → lib/updi_uart/src/role_log.h
- `lora_rx_start_lora()` --calls--> `updi_role_log()`  [INFERRED]
  src/sender/lib/lora_rx.cpp → lib/updi_uart/src/role_log.h
- `step()` --calls--> `loop()`  [INFERRED]
  tests/mvp_board.cpp → src/receiver/main.cpp
- `loop()` --calls--> `updi_uart_enabled()`  [INFERRED]
  .automation/updi-baseline/src/receiver/main.cpp → third_party/upditerm/updi_uart.c
- `loop()` --calls--> `updi_uart_enabled()`  [INFERRED]
  src/sender/lib/main.cpp → third_party/upditerm/updi_uart.c

## Import Cycles
- None detected.

## Communities (104 total, 43 thin omitted)

### Community 0 - "Task"
Cohesion: 0.14
Nodes (7): Task, is_paused_, pt_, wakeup_time_, TaskScheduler, task_count_, tasks_

### Community 1 - "EventId"
Cohesion: 0.05
Nodes (41): Component, kApplication, kBoot, kHil, kNvm, Event(), EventId, kAuthenticationStarted (+33 more)

### Community 3 - "FIRMWARE MVP EXECUTION MODE"
Cohesion: 0.20
Nodes (9): Deployment, Execution Priority, FIRMWARE MVP EXECUTION MODE, Hardware Scope, Mission, Output, Physical Radio Execution, Preserve SSOT (+1 more)

### Community 4 - "tempfile"
Cohesion: 0.06
Nodes (25): bootstrap(), create_temp_dir(), main(), I2cRadioConfigTests, CompiledHandoffTests, RepositoryIsolationTests, ihex_record(), RfTestContinuationTests (+17 more)

### Community 7 - "src/time-utils.h"
Cohesion: 0.28
Nodes (3): SetUnixTime(), InitializeTime(), SetTime()

### Community 8 - "ssot.c"
Cohesion: 0.15
Nodes (34): setup(), lora_rx_setup(), decode_payload(), duplicate_tracker_reset_session(), encode_ack_or_nack_payload(), encode_header(), ssot_ack_matches(), ssot_campaign_acknowledge() (+26 more)

### Community 9 - "tempfile"
Cohesion: 0.09
Nodes (20): ConfigurationTests, Radio915ValidationTests, valid_profile(), ReceiverHardwareTests, artifacts(), canonical(), digest(), generate() (+12 more)

### Community 10 - "ring_buffer.h"
Cohesion: 0.09
Nodes (11): RingBuffer, buffer_, RingBuffer<Capacity>::Read(), RingBuffer<Capacity>::ReadByte(), RingBuffer<Capacity>::Write(), RingBuffer<Capacity>::WriteByte(), RingBuffer<Capacity>::WriteFrame(), first_free_ (+3 more)

### Community 11 - "LoRa"
Cohesion: 0.06
Nodes (47): Address, LoRa, _active_radio, LoRa::available(), _cs_pin, LoRa::get_last_rssi(), LoRa::init(), _initialized (+39 more)

### Community 12 - "SEO optimization"
Cohesion: 0.05
Nodes (38): Article, Breadcrumbs, FAQ, Organization, Product, Structured data reference, Validation, Agentic browsing and AI discoverability (+30 more)

### Community 13 - "role_log_test.cpp"
Cohesion: 0.10
Nodes (5): init_receiver_gpio(), DecodeLoraConfig(), main(), main(), clear_capture()

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

### Community 19 - "src/time-utils.h"
Cohesion: 0.13
Nodes (22): ReportEntry, day, hour, latitude, longitude, minute, month, quality (+14 more)

### Community 21 - "codec.cpp"
Cohesion: 0.22
Nodes (17): DecodeConfig(), DecodePacketBoot(), DecodePacketReport(), DecodePacketReportWithAck(), DecodeReportEntry(), EncodeConfig(), EncodePacketBoot(), EncodePacketReport() (+9 more)

### Community 22 - "TaskLoraRx"
Cohesion: 0.12
Nodes (16): TaskLoraRx, _ack, _ack_bytes, _campaign_id, _dst, _flags, _id, _len (+8 more)

### Community 24 - "require"
Cohesion: 0.10
Nodes (9): DetectionIntegrationTests, pio(), runner(), require(), crc8(), FirmwareIdentityTests, ihex_record(), marker() (+1 more)

### Community 26 - "device.h"
Cohesion: 0.12
Nodes (15): PORT_struct, PORT_t, Revision, major, minor, raw_revision_id, SPI_struct, SPI_t (+7 more)

### Community 27 - "Port"
Cohesion: 0.25
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 29 - "SleepState"
Cohesion: 0.40
Nodes (5): SleepState, force_wakeup, is_sleeping, last_rtc_ticks, unix_time

### Community 30 - "effective_platformio_config"
Cohesion: 0.18
Nodes (3): BuildAcceptanceTests, effective_platformio_config(), TargetLayoutTests

### Community 32 - "ProvisioningResult"
Cohesion: 0.25
Nodes (9): ProvisioningResult, kInvalidArgument, kOk, kUnprovisioned, kUnsupported, IsHmacKeyProvisioned(), ReadDeviceUid(), ReadHmacKey() (+1 more)

### Community 33 - "Python Code Executor"
Cohesion: 0.08
Nodes (24): 3D Model Processing, 3D Processing, API Calls, App Details, Data Analysis with Visualization, Data Processing, Documentation, Documents & Graphics (+16 more)

### Community 34 - "lib/main.cpp"
Cohesion: 0.08
Nodes (7): espcomm_setup(), init_gpio(), loop(), ReadTemperatureCelsius(), setup(), TaskHeartbeat, _ts

### Community 35 - "MvpRoundtripTests"
Cohesion: 0.26
Nodes (3): Board, frames(), MvpRoundtripTests

### Community 37 - "Fundamental Patterns"
Cohesion: 0.09
Nodes (21): 1. Strict Mode, 2. Error Trapping and Cleanup, 3. Variable Safety, 4. Array Handling, 5. Conditional Safety, Advanced Defensive Techniques, bash-defensive-patterns — detailed patterns and worked examples, Core Defensive Principles (+13 more)

### Community 39 - "PacketReport"
Cohesion: 0.18
Nodes (8): PacketReport, report, seq, type, PacketReportWithAck, report, seq, type

### Community 40 - "ssot.h"
Cohesion: 0.13
Nodes (4): ssot_control_input_feed(), ssot_control_input_t, ssot_state_t, feed()

### Community 41 - "PacketBoot"
Cohesion: 0.25
Nodes (7): PacketBoot, checkpoint, config, device_model, firmware, reset_flags, type

### Community 45 - "PacketAck"
Cohesion: 0.33
Nodes (5): DecodePacketAck(), EncodePacketAck(), PacketAck, seq, type

### Community 46 - "PacketAdvertise"
Cohesion: 0.33
Nodes (5): DecodePacketAdvertise(), EncodePacketAdvertise(), PacketAdvertise, seq, type

### Community 48 - "PacketMaintenance"
Cohesion: 0.33
Nodes (5): DecodePacketMaintenance(), EncodePacketMaintenance(), PacketMaintenance, command, type

### Community 49 - "PacketMaintenanceAck"
Cohesion: 0.33
Nodes (5): DecodePacketMaintenanceAck(), EncodePacketMaintenanceAck(), PacketMaintenanceAck, response, type

### Community 50 - "espcomm.cpp"
Cohesion: 0.18
Nodes (6): StoreI2c16(), TaskI2CManager, _cmd, _ts, lora_rx_reject_config(), lora_rx_stop_lora()

### Community 54 - "LiveProofTests"
Cohesion: 0.07
Nodes (11): fixture(), add(), boot(), LiveProofTests, emit(), start(), write(), ApplicationPageWriteTests (+3 more)

### Community 55 - "lora_rx.cpp"
Cohesion: 0.12
Nodes (13): CampaignBuildGateResult, AlreadyRun, ReadbackFailed, Ready, claim_campaign_build(), lora_rx_hello_boot(), lora_rx_start_lora(), ssot_campaign_build_id() (+5 more)

### Community 57 - "task.h"
Cohesion: 0.25
Nodes (3): SleepFor(), PowerSavingTaskScheduler, GetTotalSeconds()

### Community 61 - "device"
Cohesion: 0.17
Nodes (11): DeviceReconnectTests, make_device(), make_probe(), require(), device(), probe(), require(), RoleDetectorTests (+3 more)

### Community 68 - "Gateway-to-Receiver SF7 Hello World"
Cohesion: 0.25
Nodes (7): Current result — Receiver installed, normal startup unresolved, Gateway-to-Receiver SF7 Hello World, No-meter read-only hardware verified; Receiver write wiring unconfirmed, Receiver boot incompatibility, Remaining physical prerequisites, Single-packet behavior and identities, Verified software result

### Community 75 - "Accessibility (a11y)"
Cohesion: 0.17
Nodes (12): Accessibility (a11y), ARIA usage (4.1.2), Color contrast (1.4.3, 1.4.6), Conformance levels, Evidence-led audit workflow, Live regions (4.1.3), Media alternatives (1.2), Perceivable (+4 more)

### Community 79 - ".parser"
Cohesion: 0.38
Nodes (4): complete_campaign_logs(), packet_event(), payload_event(), RfEvidenceTests

### Community 83 - "WCAG 2.2 Quick Reference"
Cohesion: 0.18
Nodes (8): Level A (minimum), Level AA (standard), Level AAA (enhanced), Sources, Success criteria by level, Testing tools, WCAG 2.2 Quick Reference, What changed from 2.1 to 2.2

### Community 98 - "Accessibility Code Patterns"
Cohesion: 0.22
Nodes (9): Accessibility Code Patterns, ARIA tabs, Dragging movements, Error handling, Form labels, Live regions and notifications, Modal focus trap, Screen reader commands (+1 more)

### Community 99 - "Operable"
Cohesion: 0.22
Nodes (9): Dragging movements (2.5.7) — new in 2.2, Focus not obscured (2.4.11) — new in 2.2, Focus visible (2.4.7), Keyboard accessible (2.1), Motion (2.3), Operable, Skip links (2.4.1), Target size (2.5.8) — new in 2.2 (+1 more)

### Community 102 - "State"
Cohesion: 0.05
Nodes (38): State, airtime_length, airtime_us, bandwidth_khz, begin_calls, begin_status, coding_rate, config_status (+30 more)

### Community 114 - "Connect to a virtual UART on an AVR via UPDI"
Cohesion: 0.22
Nodes (8): Connect to a virtual UART on an AVR via UPDI, Demo program, License, Prerequisites, UPDI interface, Upditerm, Usage, Virtual UART

### Community 115 - "Common ARIA patterns"
Cohesion: 0.25
Nodes (8): Buttons, Common ARIA patterns, Error states, Form fields, Links, Live regions, Modals, Navigation

### Community 116 - "Understandable"
Cohesion: 0.25
Nodes (8): Accessible authentication (3.3.8) — new in 2.2, Consistent help (3.2.6) — new in 2.2, Consistent navigation (3.2.3), Error handling (3.3.1, 3.3.3), Form labels (3.3.2), Page language (3.1.1), Redundant entry (3.3.7) — new in 2.2, Understandable

### Community 119 - ".TASK"
Cohesion: 0.21
Nodes (21): updi_role_log(), updi_role_log_airtime(), updi_role_log_boot(), updi_role_log_campaign(), updi_role_log_identity(), updi_role_log_identity_crc8(), updi_role_log_packet(), updi_role_log_payload() (+13 more)

### Community 130 - "Frontend Design"
Cohesion: 0.29
Nodes (6): Design principles, Frontend Design, Ground your designs in the subject matter, More on writing in design, Process: plan, review against the brief, build, critique, Restraint and self-critique

### Community 132 - "State"
Cohesion: 0.07
Nodes (21): Evidence basis, H1 connector, H2 connector and board signals, Pin Mapping Audit — AVR128DA28 / RFM95W, Radio and MCU pins, RF connector path, Verification, SPIClass (+13 more)

### Community 148 - "Gateway Hardware SSOT — Rudolph Gateway"
Cohesion: 0.10
Nodes (19): 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates, Gateway Hardware SSOT — Rudolph Gateway, H1 (10-pin; only pins 1–5 used in the source schematic) (+11 more)

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

### Community 285 - "rf_proof.py"
Cohesion: 0.06
Nodes (69): BootAnalysisTests, analyze(), main(), normalize_ihex_region(), _parse_ihex(), ihex(), install(), load_package() (+61 more)

### Community 298 - "EepromBoundary"
Cohesion: 0.25
Nodes (6): EepromBoundary, reads, stored, writes, written_bytes, wrong_address

## Knowledge Gaps
- **221 isolated node(s):** `is_paused_`, `pt_`, `wakeup_time_`, `task_count_`, `tasks_` (+216 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 706 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **43 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `rf_test()` connect `rf_proof.py` to `upditerm.py`, `device`, `HardwareGateTests`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **What connects `is_paused_`, `pt_`, `wakeup_time_` to the rest of the system?**
  _221 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Task` be split into smaller, more focused modules?**
  _Cohesion score 0.14130434782608695 - nodes in this community are weakly interconnected._
- **Why does `SX1276` connect `SX1276` to `mvp_stub/Arduino.h`, `LoRa`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Should `EventId` be split into smaller, more focused modules?**
  _Cohesion score 0.05204872646733112 - nodes in this community are weakly interconnected._
- **Why does `DeviceLayout` connect `DeviceLayout` to `memory_layout.h`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Should `tempfile` be split into smaller, more focused modules?**
  _Cohesion score 0.057703081232493 - nodes in this community are weakly interconnected._