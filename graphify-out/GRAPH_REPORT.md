# Graph Report - SENIOR_PROJECT_RCA  (2026-11-20)

## Corpus Check
- 335 files · ~207,106 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 26 file(s) not represented in the graph (top: (none) 10, .toml 7, .css 4)

## Summary
- 4542 nodes · 9117 edges · 310 communities (168 shown, 142 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 607 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `413b3d4b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- pathlib
- ProofRun
- Storage
- mvp_board.cpp
- analyze
- mcurses.c
- appcode/arq/sender.cpp
- CaptureTests
- error
- State
- GNSS
- SystemConstants
- ArqSoakPlanTests
- generate_lora_config.py
- RepositoryIsolationTests
- appcode/arq/receiver.cpp
- RadioBringupTests
- arq_trial.py
- updi_role_log
- rf_test
- mvp_stub/Arduino.h
- session.py
- Transport
- Gate1Tests
- HardwareGateTests
- load
- gateway_radio.cpp
- ReaderFreeH01SummaryTests
- ._run_capture
- Campaign
- ring_buffer.h
- build_case_plan
- tracker_radio_codec.cpp
- os
- firmware_image_bounds_for_environment
- EventId
- SX1276
- Hardware
- reverse_raw_app.cpp
- main
- image_evidence
- DeviceLayout
- Bus
- require
- TracePort
- directional_test.cpp
- AGENTS.md — AVR128DA28 / LoRa Embedded Engineering
- arduino
- upditerm.py
- TrackerConfig
- Task
- reliable_transport_test.cpp
- ReceiveTests
- Sender
- FlashSafetyTests
- PlatformResult
- sender/appcode/reliable.cpp
- MvpRoundtripTests
- test_application_config.py
- LoRa Recovery Repository Audit
- require
- OPERATING CONTRACT — READ ALL BEFORE EDITING
- Config
- .EmitEvent
- Tracker Hardware SSOT — LoRa Tracker RFM
- application_authorization_fixture
- Event
- Command
- Port
- role_log_test.cpp
- LoRa
- InteractiveConsole
- 915 MHz LoRa bench procedure
- role_detector.py
- Receiver
- BenchTransport
- Json
- .connect
- ExcludedSx1262Experiment
- stdint
- Controller
- cli.py
- string
- firmware_identity.py
- complete_campaign_logs
- RCATests
- ErrataDiagnosticsTests
- PIN_MAPPING_AUDIT.md
- core_test.cpp
- runner.py
- test_lora_chat_protocol.py
- Pins
- mvp_app.cpp
- HexDataCommandDecoder
- application_config.h
- ReportEntry
- SD.h
- BenchStatus
- Result
- tracker_config.h
- State
- gate1_live.py
- result_to_json
- State
- test_lora_chat_session.py
- receiver/appcode/reliable.cpp
- diagnostics.cpp
- avr128da28_device.h
- spec_runner.py
- ReliableTransportTests
- updi_probe.py
- BuildEnvironment
- re
- PacketBoot
- LoRa source ownership V2
- ErrorCode
- ProvisioningResult
- Session
- StableLoraSafetyTests
- Fixed settings and checks
- SdFile
- Logger
- Radio915ValidationTests
- replay_bundle
- spec_timeout.py
- payload_generator.py
- Connect to a virtual UART on an AVR via UPDI
- check_cpp.sh
- gate1.py
- C++ Refactoring Results
- Gateway-to-Receiver SF7 Hello World
- compare_snapshots
- test_arq.py
- load_bench_profile
- LoRa ACK/NACK analysis and verification
- TaskScheduler
- SPIClass
- AVR128DA28 LoRa Board Pin Audit
- detect_devices.py
- usb_inventory.py
- stub/Arduino.h
- commands.cpp
- receiver_boot.py
- PacketMaintenanceAck
- SenderStableTransportTests
- Gate1Audit
- ScanResult
- protocol_adapter.py
- BuildIdentityImagesTests
- TraceBus
- Logger
- spec_protocol.py
- AVR128DA28 LoRa firmware
- .test_no_meter_identity_uses_live_unique_serial_without_checklist
- shared/README.md
- LORA_ACK_NACK.md
- avr128da28_memory_layout.h
- ResponseFault
- stub/SPI.h
- EventContext
- spec_payload.py
- raw_mvp_stub/SPI.h
- parse_raw_mvp_logs
- CppInterfaceTests
- Frame
- arq_sender.h
- SsotProtocolTests
- install_cpp_quality_tools.sh
- _legacy_keyboard_mode
- start_udev_monitor
- Shared Logic and Duplication Audit
- Library Skills
- Revision
- Library Skills
- RestartTask
- .test_unsafe_image_makes_build_stage_fail
- MonitorConsole
- PacketReportWithAck
- SingleFirmwareEntryTests
- Final LoRa firmware architecture
- C++ Refactoring Baseline
- Offline regression matrix
- PacketMaintenance
- LoRa Chat Firmware and Installed-Image Requirements
- FaultName
- InstalledRadioEvidenceTests
- main
- EventField
- ExcludedSx1262Experiment
- RadioTransactionTask
- Json
- ProfileValue
- HeartbeatTask
- LORA_RF_STRESS_SPECIAL.md
- PacketAck
- PacketAdvertise
- _base_platformio_sections
- checked_cpp
- check_cpp.py
- Capture
- GatewayI2cTests
- TaskRestartTests
- I2cRadioConfigTests
- RadioDiagnosticsTests
- RadioLibHalTests
- sleep.cpp
- lora
- lora/library.json
- time-utils/library.json
- ใช้งาน Codex Goal — LoRa E2E Feature-Based
- Suggested append-only AGENTS.md contract (merge; do not overwrite existing instructions)

## God Nodes (most connected - your core abstractions)
1. `Transport` - 72 edges
2. `Hardware` - 64 edges
3. `SystemConstants` - 46 edges
4. `error()` - 46 edges
5. `State` - 45 edges
6. `Gate1Tests` - 45 edges
7. `make_error()` - 42 edges
8. `BenchTransport` - 40 edges
9. `LoRa` - 40 edges
10. `ProofRun` - 38 edges

## Surprising Connections (you probably didn't know these)
- `Radio SPI and interrupt contract` --references--> `ExcludedSx1262Experiment`  [INFERRED]
  GATEWAY_SSOT.md → include/gateway_ssot.hpp
- `C. Action` --references--> `LoRa`  [INFERRED]
  docs/refactoring/SOURCE_OWNERSHIP_V2.md → src/shared/radio/radio_link.h
- `SSOT addressed DATA, ACK, and NACK` --references--> `LoRa`  [INFERRED]
  docs/testing/LORA_ACK_NACK.md → src/shared/radio/radio_link.h
- `Scope` --references--> `TrackerConfig`  [INFERRED]
  TRACKER_CONFIG_SSOT.md → include/tracker_config.h
- `Fixed settings and checks` --references--> `SystemConstants`  [INFERRED]
  TRACKER_CONFIG_SSOT.md → include/tracker_config.h

## Import Cycles
- None detected.

## Communities (310 total, 142 thin omitted)

### Community 0 - "pathlib"
Cohesion: 0.06
Nodes (4): bootstrap(), create_temp_dir(), main(), assess_control_fault()

### Community 1 - "ProofRun"
Cohesion: 0.09
Nodes (39): RfTestContinuationTests, build(), inspect_image(), read_layouts(), authorized_application_pages(), capture_usb_topology(), check_port_owners(), clean_builds() (+31 more)

### Community 2 - "Storage"
Cohesion: 0.09
Nodes (11): Storage, _first, _raw, _start_block, Storage<T>::clear(), Storage<T>::_load_state(), Storage<T>::peek(), Storage<T>::pop() (+3 more)

### Community 3 - "mvp_board.cpp"
Cohesion: 0.09
Nodes (5): delay(), main(), pump(), state_name(), step()

### Community 4 - "analyze"
Cohesion: 0.08
Nodes (3): analyze(), load(), read()

### Community 5 - "mcurses.c"
Cohesion: 0.09
Nodes (38): addch(), addstr(), addstr_P(), attrset(), clear(), clrtobot(), clrtoeol(), curs_set() (+30 more)

### Community 6 - "appcode/arq/sender.cpp"
Cohesion: 0.31
Nodes (18): ArmSession(), CurrentSession(), ExecuteCommand(), FailAdapter(), FeedCommandByte(), FlushStatus(), GetEventContext(), HandleReceive() (+10 more)

### Community 7 - "CaptureTests"
Cohesion: 0.06
Nodes (3): CaptureTests, command(), monotonic()

### Community 8 - "error"
Cohesion: 0.15
Nodes (21): error(), campaign(), progress(), run_one(), Capture, complete(), park_reverse(), prepare() (+13 more)

### Community 9 - "State"
Cohesion: 0.04
Nodes (45): State, airtime_length, airtime_us, bandwidth_khz, begin_calls, begin_status, chip_version, coding_rate (+37 more)

### Community 10 - "GNSS"
Cohesion: 0.09
Nodes (20): calculate_checksum(), extract_field(), GNSS, day, fixquality, _gga_received, GNSS::GNSS(), hour (+12 more)

### Community 11 - "SystemConstants"
Cohesion: 0.04
Nodes (45): SystemConstants, ADC_RESOLUTION_STEPS, ADC_VREF_MV, BOOT_DELAY_MS, BOOT_SENTINEL_COORD, BOOT_SENTINEL_VBAT_MV, DEBUG_SERIAL_BAUD, DEVICE_MODEL (+37 more)

### Community 12 - "ArqSoakPlanTests"
Cohesion: 0.09
Nodes (16): ArqSoakPlanTests, fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), confirmed_rf_preflight(), dynamic_attr() (+8 more)

### Community 13 - "generate_lora_config.py"
Cohesion: 0.07
Nodes (15): SourceFingerprintTests, artifacts(), canonical(), digest(), load_radio_profile(), main(), prepare_build_inputs(), _profile_python() (+7 more)

### Community 15 - "appcode/arq/receiver.cpp"
Cohesion: 0.32
Nodes (17): ArmSession(), CurrentSession(), ExecuteCommand(), FailAdapter(), FeedCommandByte(), FlushStatus(), GetEventContext(), HandleReceive() (+9 more)

### Community 16 - "RadioBringupTests"
Cohesion: 0.09
Nodes (7): DirectionalHostTests, RadioBringupTests, acquire(), command(), audit_radio_configuration(), read_radio(), validate_hello_exchange()

### Community 17 - "arq_trial.py"
Cohesion: 0.10
Nodes (22): ArqTests, capture_tracker_diagnostics(), checked_events(), close_updi_without_recovery(), drain_updi_messages(), hello_airtime_budget(), lora_time_on_air_us(), missing_soak_prerequisites() (+14 more)

### Community 18 - "updi_role_log"
Cohesion: 0.12
Nodes (31): EventQueue, count_, events_, head_, kCapacity, FlushEvent(), InteractivePayloadLimit(), ReportConfig() (+23 more)

### Community 19 - "rf_test"
Cohesion: 0.08
Nodes (24): assess_installed_exchange(), boot_fuses_match(), capture_radio_spi_log(), expected_signature_hex(), host_tests(), parse_radio_spi_log(), parse_rf_campaign(), parse_role_log_count() (+16 more)

### Community 22 - "mvp_stub/Arduino.h"
Cohesion: 0.22
Nodes (4): CPUINT(), digitalReadFast(), digitalWrite(), digitalWriteFast()

### Community 23 - "session.py"
Cohesion: 0.05
Nodes (12): test_interactive_encoder_accepts_bounded_utf8_messages(), encode_interactive_message(), ChatStats, CompletedMessage, ExchangeStatus, QueueFullError, _remember_bounded(), SessionConfigError (+4 more)

### Community 24 - "Transport"
Cohesion: 0.05
Nodes (35): Transport, armed_, confirming_ack_, context_, error_, event_context_, frequency_, have_accepted_ (+27 more)

### Community 26 - "Gate1Tests"
Cohesion: 0.09
Nodes (4): Gate1Tests, rows(), transaction(), verify_hashes()

### Community 27 - "HardwareGateTests"
Cohesion: 0.11
Nodes (3): dynamic_attr(), effective_platformio_config(), HardwareGateTests

### Community 28 - "load"
Cohesion: 0.09
Nodes (8): ConfigurationTests, RawMvpTests, ReceiverHardwareTests, load(), main(), unique_object(), validate(), shape()

### Community 29 - "gateway_radio.cpp"
Cohesion: 0.06
Nodes (31): I2cCommandTask, command_, command_length_, I2cResetTask, timestamp_ms_, InitializeEspCommunication(), StoreI2c16(), Initialize() (+23 more)

### Community 30 - "ReaderFreeH01SummaryTests"
Cohesion: 0.10
Nodes (5): ReaderFreeH01SummaryTests, hardware_gate_errors(), main(), open_reader_free_h01_session(), reader_free_rx_idle_summary()

### Community 31 - "._run_capture"
Cohesion: 0.09
Nodes (10): fixture(), add(), LiveProofTests, emit(), start(), write(), symmetric_fixture(), add() (+2 more)

### Community 32 - "Campaign"
Cohesion: 0.08
Nodes (32): Campaign, attempts, campaign_id, destination, sequence, single_packet, source, state (+24 more)

### Community 34 - "ring_buffer.h"
Cohesion: 0.09
Nodes (11): RingBuffer, buffer_, RingBuffer<Capacity>::Read(), RingBuffer<Capacity>::ReadByte(), RingBuffer<Capacity>::Write(), RingBuffer<Capacity>::WriteByte(), RingBuffer<Capacity>::WriteFrame(), first_free_ (+3 more)

### Community 35 - "build_case_plan"
Cohesion: 0.19
Nodes (5): _add_direction_cases(), build_case_plan(), _prepare_run(), radio_configuration(), _validate_profiles()

### Community 36 - "tracker_radio_codec.cpp"
Cohesion: 0.15
Nodes (22): DecodePacketReport(), DecodePacketReportWithAck(), DecodeReportEntry(), EncodeConfig(), EncodePacketAck(), EncodePacketAdvertise(), EncodePacketBoot(), EncodePacketMaintenance() (+14 more)

### Community 37 - "os"
Cohesion: 0.18
Nodes (14): bootstrap(), create_temp_dir(), main(), _check_config(), _check_symlink(), _inside(), _items(), _label() (+6 more)

### Community 38 - "firmware_image_bounds_for_environment"
Cohesion: 0.09
Nodes (16): DirectionalTests, RadioOnlyTests, application_bounds_for_environment(), application_layout_verified(), build_flag_defines(), _config_int(), device_profile_for_role(), effective_project_sections() (+8 more)

### Community 39 - "EventId"
Cohesion: 0.05
Nodes (41): Component, kApplication, kBoot, kHil, kNvm, Event(), EventId, kAuthenticationStarted (+33 more)

### Community 41 - "Hardware"
Cohesion: 0.03
Nodes (7): DebugConsoleTests, discover_ports(), Hardware, chunk_complete(), parked(), BenchBlockedError, BenchFailedError

### Community 42 - "reverse_raw_app.cpp"
Cohesion: 0.37
Nodes (10): ExecuteCommand(), FeedCommandByte(), IsPayloadCommand(), ParkRadio(), Poll(), ReadStableCounter(), RecordConfiguration(), RecordEvent() (+2 more)

### Community 43 - "main"
Cohesion: 0.13
Nodes (7): build_parser(), _display_run(), main(), RunOptions, RunPlan, _validated_options(), _write_run_bundle()

### Community 44 - "image_evidence"
Cohesion: 0.10
Nodes (11): wire(), event(), image_evidence(), journal(), StableTransportProofTests, _line(), write(), wrong_destination_journal() (+3 more)

### Community 45 - "DeviceLayout"
Cohesion: 0.12
Nodes (18): DeviceLayout, kAppDataStart, kApplicationEnd, kApplicationImageEnd, kApplicationStart, kBootEnd, kBootSizePages, kBootStart (+10 more)

### Community 47 - "Bus"
Cohesion: 0.11
Nodes (6): Bus, fifo, finish_delay, regs, reset_mode, ticks

### Community 48 - "require"
Cohesion: 0.11
Nodes (4): DetectionIntegrationTests, pio(), runner(), require()

### Community 50 - "directional_test.cpp"
Cohesion: 0.21
Nodes (12): drain_status(), main(), send_command(), QueuedLogLine(), ResetLog(), clear_log(), cmd(), logged() (+4 more)

### Community 52 - "AGENTS.md — AVR128DA28 / LoRa Embedded Engineering"
Cohesion: 0.09
Nodes (21): 10. Logging, measurement, and evidence, 11. Decision and intervention policy, 12. Response contract, 13. Technical references (read when relevant; do not substitute for active SSOT), 1. Mission and current MVP, 2. Operating philosophy, 3. Project truth and protected files, 4. Target architecture (+13 more)

### Community 53 - "arduino"
Cohesion: 0.07
Nodes (17): Memory, I2C_MAILBOX_BYTES, SHARED_RINGBUF_BYTES, System, ENABLE_ESPCOMM, ENABLE_LORA_RX, ENABLE_WATCHDOG, WDT_TIMEOUT_PERIOD (+9 more)

### Community 54 - "upditerm.py"
Cohesion: 0.07
Nodes (8): Console, main(), parse_arguments(), SerialPort, SerialUPDI, Terminal, TransportError, UPDI

### Community 55 - "TrackerConfig"
Cohesion: 0.10
Nodes (18): TrackerConfig, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 57 - "Task"
Cohesion: 0.20
Nodes (6): Task::Task(), Task, is_paused_, pt_, wakeup_time_, main()

### Community 58 - "reliable_transport_test.cpp"
Cohesion: 0.08
Nodes (23): AcceptedPayload, allow_new, bytes, size, EventLog, count, names, FakeRadio (+15 more)

### Community 59 - "ReceiveTests"
Cohesion: 0.13
Nodes (3): ReceiveTests, wait(), wait()

### Community 60 - "Sender"
Cohesion: 0.05
Nodes (44): Result, kOk, kPending, kProtocolError, kRadioError, kRejected, kTimeoutExhausted, Sender (+36 more)

### Community 61 - "FlashSafetyTests"
Cohesion: 0.12
Nodes (3): FlashSafetyTests, ihex_record(), hardware_blockers()

### Community 62 - "PlatformResult"
Cohesion: 0.13
Nodes (18): InitializeAdc(), ReadBatteryAdc(), ReadSample(), ReadTemperatureAdc(), WaitForConversion(), PlatformResult, kBusy, kForbidden (+10 more)

### Community 63 - "sender/appcode/reliable.cpp"
Cohesion: 0.28
Nodes (14): AcceptData(), ArmRadio(), HandleRadioCommand(), Initialize(), InitializeGpio(), InitializeRoleGpio(), Poll(), PollRoleRadio() (+6 more)

### Community 64 - "MvpRoundtripTests"
Cohesion: 0.21
Nodes (3): Board, frames(), MvpRoundtripTests

### Community 65 - "test_application_config.py"
Cohesion: 0.08
Nodes (12): ApplicationConfigTests, ReverseRawTests, audit_raw_configuration(), diagnostic_case(), reverse_exchange(), status(), validate_reverse(), load() (+4 more)

### Community 66 - "LoRa Recovery Repository Audit"
Cohesion: 0.08
Nodes (23): A — การดำเนินการ, Hardware readback และ RF, R — ผลการตรวจสอบ, S — สถานการณ์, Software และ firmware build, T — งานที่ต้องทำ, การตัดสินใจ, ขั้นตอนถัดไป (+15 more)

### Community 67 - "require"
Cohesion: 0.14
Nodes (10): DeviceReconnectTests, make_device(), make_probe(), require(), device(), probe(), require(), RoleDetectorTests (+2 more)

### Community 68 - "OPERATING CONTRACT — READ ALL BEFORE EDITING"
Cohesion: 0.12
Nodes (15): 0. Target, boundaries, priorities, 10. Mandatory negative and protocol matrix, 11. Acceptance criteria — NOT negotiable, 12. Agentic self-repair loop — persistent, evidence-driven, bounded, 13. First actions — execute in this exact order, 1. Mandatory first phase: read-only inventory and graph analysis, 2. Reference repo: behavior parity without copying defects, 3. IMPORTANT RADIO FACT: SX127x `setNodeAddress` (+7 more)

### Community 69 - "Config"
Cohesion: 0.11
Nodes (18): Config, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 71 - "Tracker Hardware SSOT — LoRa Tracker RFM"
Cohesion: 0.22
Nodes (9): 1. Board identity and components, 2. AVR128DA28 pin and net SSOT, 3. Power and startup contract, 4. Minimal firmware implementation contract, 5. Acceptance criteria / physical evidence, 6. Firmware configuration, Exact LoRa RFM95W signal map, Sources (+1 more)

### Community 73 - "Event"
Cohesion: 0.20
Nodes (9): Event, campaign_id, error, name, sequence, time_ms, type, radio_diagnostics::EventQueue::Pop() (+1 more)

### Community 74 - "Command"
Cohesion: 0.15
Nodes (13): Command, budget, kind, payload, payload_length, session, stride, CommandKind (+5 more)

### Community 75 - "Port"
Cohesion: 0.21
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 76 - "role_log_test.cpp"
Cohesion: 0.09
Nodes (6): DecodeLoraConfig(), EepromSpy, reads, writes, main(), clear_capture()

### Community 77 - "LoRa"
Cohesion: 0.08
Nodes (19): Application and dependency audit, Firmware matrix, Historical BOOT and deployment status, Offline LoRa firmware refactor, Verification, Wire and host evidence, ReportRegisters(), Address (+11 more)

### Community 78 - "InteractiveConsole"
Cohesion: 0.05
Nodes (10): test_csi_u_keyboard_sequence_is_rejected_as_a_message(), test_prompt_admits_utf8_when_both_endpoints_support_echo(), ConsoleRuntime, InteractiveConsole, _parse_event(), make_error(), ChatSession, InputDisposition (+2 more)

### Community 80 - "915 MHz LoRa bench procedure"
Cohesion: 0.29
Nodes (6): 915 MHz LoRa bench procedure, App-only programming after exact write approval, Hardware results, Refactor verification, RF conditions and acceptance, Verified candidates

### Community 81 - "role_detector.py"
Cohesion: 0.22
Nodes (8): ProbeEvidence, USBDevice, classify_devices(), diff_device_presence(), _identity_role(), _probe_for(), _registry_hint(), _registry_record()

### Community 82 - "Receiver"
Cohesion: 0.11
Nodes (18): Receiver, accepted, armed, deliveries, duplicates, expected, last_sequence, session (+10 more)

### Community 83 - "BenchTransport"
Cohesion: 0.05
Nodes (10): test_archived_gateway_names_and_full_fresh_readback(), test_connect_read_only_with_a_current_build_mismatch(), test_dry_run_creates_empty_event_log_and_disables_transmission(), test_post_rf_tracker_monitor_reopens_without_reissuing_data(), test_rf_authorization_requires_separate_setup_confirmation(), test_run_directory_is_created_once_by_the_transport(), test_verified_current_pair_takes_precedence_over_saved_legacy_receipt(), ExchangeResult (+2 more)

### Community 84 - "Json"
Cohesion: 0.14
Nodes (13): _fault_bundle(), _run_replay(), test_cancel_fault_is_not_passed_by_a_normal_ack_exchange(), test_cancel_is_passed_only_after_both_radios_park_and_ports_release(), test_cancel_requires_park_after_the_cancel_request(), test_controlled_nack_retries_the_same_session_and_sequence(), test_crc_rejection_uses_timeout_recovery_without_application_nack(), test_duplicate_is_not_passed_without_single_delivery_evidence() (+5 more)

### Community 86 - "ExcludedSx1262Experiment"
Cohesion: 0.20
Nodes (10): ExcludedSx1262Experiment, BUSY_PIN, DIO1_PIN, ERROR_RETRY_DELAY_MS, NSS_PIN, PACKET_BYTES, PACKET_COUNT, PACKET_GAP_MS (+2 more)

### Community 87 - "stdint"
Cohesion: 0.07
Nodes (8): begin(), digitalWrite(), end(), ltoa(), push_back(), main(), main(), test_interactive_command()

### Community 90 - "Controller"
Cohesion: 0.13
Nodes (12): Controller, last_led1_toggle_, last_tx_toggle_, led1_interval_ms_, led1_on_, led1_pin_, led2_pin_, led_off_level_ (+4 more)

### Community 91 - "cli.py"
Cohesion: 0.04
Nodes (12): test_plain_chat_uses_only_the_configured_bench_defaults(), test_terminal_output_preserves_rich_ansi_in_prompt_toolkit(), test_typer_app_exposes_help_for_supported_options(), ConsoleCommand, ConsoleStateError, _create_run_directory(), _event_style(), _event_summary() (+4 more)

### Community 94 - "string"
Cohesion: 0.09
Nodes (3): InitializeRadio(), main(), reset_radio()

### Community 95 - "firmware_identity.py"
Cohesion: 0.08
Nodes (16): _hex_image(), _record(), test_flash_comparison_rejects_hex_data_outside_the_authorized_region(), test_flash_comparison_reports_exact_sparse_image_match(), test_flash_comparison_reports_first_actual_mismatch_address(), FirmwareIdentity, compare_flash_region(), crc8() (+8 more)

### Community 96 - "complete_campaign_logs"
Cohesion: 0.38
Nodes (4): complete_campaign_logs(), packet_event(), payload_event(), RfEvidenceTests

### Community 98 - "ErrataDiagnosticsTests"
Cohesion: 0.13
Nodes (5): ErrataDiagnosticsTests, decode_snapshot(), interpret_rx(), link_budget(), main()

### Community 99 - "PIN_MAPPING_AUDIT.md"
Cohesion: 0.20
Nodes (8): Data and protocol boundaries, Firmware source map, Hardware and power, Receiver APPCODE, Source path, Builds and hardware, Sender APPCODE, Source path

### Community 101 - "core_test.cpp"
Cohesion: 0.38
Nodes (12): absolute_deadline(), ack_matrix(), codec(), control(), data(), fault_harness(), fresh(), main() (+4 more)

### Community 102 - "runner.py"
Cohesion: 0.09
Nodes (8): load_event_journal(), calculate_metrics(), _percentile(), RadioProfile, real_rf_blockers(), RunMode, RunProfile, ResultStatus

### Community 103 - "test_lora_chat_protocol.py"
Cohesion: 0.04
Nodes (43): _chunk_events(), test_ack_alone_never_counts_as_a_tracker_echo(), test_ack_matching_requires_campaign_sequence_and_type(), test_echo_latency_uses_the_gateway_clock_and_first_attempt(), test_encodes_supported_utf8_bytes_exactly(), test_fragmentation_preserves_exact_bytes_at_the_negotiated_packet_limit(), test_interactive_boundaries_reject_empty_oversize_and_invalid_utf8(), test_interactive_capability_requires_echo_support_from_both_endpoints() (+35 more)

### Community 105 - "Pins"
Cohesion: 0.04
Nodes (43): AdcTemp, ADC_MAX_COUNTS, CTRLA_ENABLE_12BIT, FIXED_POINT_SHIFT, INIT_DELAY_SETTING, KELVIN_TO_CELSIUS, MUX_TEMP_CHANNEL, PRESCALER_SETTING (+35 more)

### Community 106 - "mvp_app.cpp"
Cohesion: 0.21
Nodes (18): debug_init(), debug_write(), debug_write_float(), debug_write_hex(), debug_write_int(), Initialize(), Poll(), RecordStartupStage() (+10 more)

### Community 107 - "HexDataCommandDecoder"
Cohesion: 0.08
Nodes (20): HexDataCommandDecoder, high_nibble_, length_, received_, state_, Result, kComplete, kInvalidBuffer (+12 more)

### Community 110 - "application_config.h"
Cohesion: 0.07
Nodes (30): DecodePayloadFields(), EncodeControlPayload(), Frame, campaign_id, destination, sequence, source, type (+22 more)

### Community 111 - "ReportEntry"
Cohesion: 0.14
Nodes (22): ReportEntry, day, hour, latitude, longitude, minute, month, quality (+14 more)

### Community 112 - "SD.h"
Cohesion: 0.25
Nodes (8): mbr_t, mbrSig0, mbrSig1, part, SdPartition, firstSector, totalSectors, type

### Community 113 - "BenchStatus"
Cohesion: 0.12
Nodes (17): BenchStatus, attempted, completed, control_rejects, crc_errors, decode_errors, deliveries, duplicates (+9 more)

### Community 114 - "Result"
Cohesion: 0.22
Nodes (8): Result, kAccepted, kAckTimeout, kInvalidArgument, kPending, kRadioError, kRejected, kTxTimeout

### Community 115 - "tracker_config.h"
Cohesion: 0.33
Nodes (6): Checkpoint, INVALID_GNSS_DATE, SPI_CTRL_BEFORE_LORA, SPI_CTRL_BEFORE_PWR_ON, TRACKER_AFTER_GNSS_ON, TRACKER_BEFORE_GNSS_ON

### Community 117 - "State"
Cohesion: 0.17
Nodes (12): State, begin_count, cs_high_seen, cs_low_seen, cs_pin, initialized, route, swap_count (+4 more)

### Community 119 - "gate1_live.py"
Cohesion: 0.15
Nodes (25): controlled_cpu_reset(), firmware_identity_from_events(), gpr_roundtrip_succeeded(), halted_gpr_roundtrip(), mailbox_snapshot(), main(), _parse_block(), part_from_signature() (+17 more)

### Community 121 - "State"
Cohesion: 0.22
Nodes (8): State, kComplete, kFailed, kRetryPending, kRxWait, kTxData, kTxResponse, kWaitResponse

### Community 122 - "test_lora_chat_session.py"
Cohesion: 0.09
Nodes (18): _event(), _session(), test_ack_matching_deduplicates_replayed_event_counts(), test_ack_without_real_echo_is_not_round_trip_success(), test_captured_echo_timeout_counts_once(), test_chat_settings_allow_zero_manual_retries(), test_chat_settings_enforce_memory_and_refresh_caps(), test_chat_settings_reject_unknown_keys_and_invalid_limits() (+10 more)

### Community 123 - "receiver/appcode/reliable.cpp"
Cohesion: 0.14
Nodes (16): AcceptData(), ArmRadio(), HandleRadioCommand(), Initialize(), InitializeGpio(), InitializeRoleGpio(), Poll(), RecordTransportEvent() (+8 more)

### Community 124 - "diagnostics.cpp"
Cohesion: 0.11
Nodes (15): CommandInput, buffer_, length_, overflow_, AcquireLine(), FlushByte(), OverflowCount(), PendingLineCount() (+7 more)

### Community 125 - "avr128da28_device.h"
Cohesion: 0.15
Nodes (12): IsAppCodeRange(), PORT_struct, PORT_t, SPI_struct, SPI_t, TWI_struct, TWI_t, TwiHold (+4 more)

### Community 126 - "spec_runner.py"
Cohesion: 0.13
Nodes (9): test_default_cli_writes_a_zero_transmission_dry_run(), test_real_rf_requires_explicit_profile_and_saved_readback(), test_stress_config_rejects_unknown_settings(), test_torture_config_must_keep_one_thousand_transaction_minimum(), test_torture_plan_has_at_least_one_thousand_cases_and_a_bounded_runtime(), test_torture_profile_requires_long_duration_opt_in(), load_config(), _validate_installed_pair() (+1 more)

### Community 128 - "updi_probe.py"
Cohesion: 0.20
Nodes (9): firmware_fingerprint_evidence(), identify_mcu(), _is_access_error(), _port_busy(), probe_firmware_identity(), probe_target_sib(), read_firmware_flash(), _require_safe() (+1 more)

### Community 130 - "re"
Cohesion: 0.15
Nodes (5): BootAnalysisTests, analyze(), main(), assess_exhaustion(), assess_probe()

### Community 131 - "PacketBoot"
Cohesion: 0.18
Nodes (10): DecodeConfig(), DecodePacketBoot(), LoadFloat(), PacketBoot, checkpoint, config, device_model, firmware (+2 more)

### Community 132 - "LoRa source ownership V2"
Cohesion: 0.22
Nodes (9): A. Situation, B. Task, C. Action, D. Result, E. Final directory tree, F. Migration table, G. Remaining risks, H. Final status (+1 more)

### Community 133 - "ErrorCode"
Cohesion: 0.20
Nodes (10): ErrorCode, CONFIG_FILE_READ_FAILED, CONFIG_PART_NOT_FOUND, CONFIG_VOL_INIT_FAILED, DATA_PARTITION_NOT_FOUND, LOG_PARTITION_NOT_FOUND, LOGGER_SETUP_FAILED, LORA_INIT_FAILED (+2 more)

### Community 134 - "ProvisioningResult"
Cohesion: 0.25
Nodes (9): ProvisioningResult, kInvalidArgument, kOk, kUnprovisioned, kUnsupported, IsHmacKeyProvisioned(), ReadDeviceUid(), ReadHmacKey() (+1 more)

### Community 135 - "Session"
Cohesion: 0.08
Nodes (4): Console, hardware_output(), main(), Session

### Community 137 - "Fixed settings and checks"
Cohesion: 0.40
Nodes (4): Fixed settings and checks, Runtime settings, Scope, Tracker Configuration SSOT

### Community 138 - "SdFile"
Cohesion: 0.14
Nodes (9): get_data_and_log_partitions(), open_file_in_root(), read_line(), SdFile, data_, length_, position_, SdVolume (+1 more)

### Community 139 - "Logger"
Cohesion: 0.31
Nodes (5): Logger, _capacity, _cursor, _raw, _start_block

### Community 140 - "Radio915ValidationTests"
Cohesion: 0.17
Nodes (3): Radio915ValidationTests, valid_profile(), write_toml()

### Community 141 - "replay_bundle"
Cohesion: 0.31
Nodes (4): _output_directory(), _read_case_journal(), replay_bundle(), _write_replay_bundle()

### Community 143 - "spec_timeout.py"
Cohesion: 0.19
Nodes (9): _replay(), test_gateway_accepting_wrong_sequence_is_a_false_ack_failure(), test_latency_wraps_the_same_device_millisecond_counter(), test_retry_limit_excess_is_a_failure(), test_timeout_recovery_keeps_the_same_session_and_sequence(), test_wrong_campaign_is_explicitly_rejected(), test_wrong_destination_must_be_ignored_until_timeout(), test_wrong_sequence_is_explicitly_rejected_before_correct_ack() (+1 more)

### Community 144 - "payload_generator.py"
Cohesion: 0.20
Nodes (5): generate_payload(), split_payload(), _append_case(), add(), CaseSpec

### Community 148 - "Connect to a virtual UART on an AVR via UPDI"
Cohesion: 0.22
Nodes (8): Connect to a virtual UART on an AVR via UPDI, Demo program, License, Prerequisites, UPDI interface, Upditerm, Usage, Virtual UART

### Community 149 - "check_cpp.sh"
Cohesion: 0.70
Nodes (4): PATH, record_support(), run_support(), check_cpp.sh script

### Community 150 - "gate1.py"
Cohesion: 0.28
Nodes (3): assess(), response(), _status()

### Community 151 - "C++ Refactoring Results"
Cohesion: 0.20
Nodes (9): A — Action, C++ Refactoring Results, Current follow-up verification — 2026-11-19, R — Result, S — Situation, T — Task, Trade-offs and limits, SleepFor() (+1 more)

### Community 152 - "Gateway-to-Receiver SF7 Hello World"
Cohesion: 0.25
Nodes (7): Current result — Receiver installed, normal startup unresolved, Gateway-to-Receiver SF7 Hello World, No-meter read-only hardware verified; Receiver write wiring unconfirmed, Receiver boot incompatibility, Remaining physical prerequisites, Single-packet behavior and identities, Verified software result

### Community 154 - "compare_snapshots"
Cohesion: 0.15
Nodes (3): classify(), compare_snapshots(), delta()

### Community 155 - "test_arq.py"
Cohesion: 0.30
Nodes (3): arq_artifacts(), load_arq(), validate_arq()

### Community 156 - "load_bench_profile"
Cohesion: 0.17
Nodes (6): test_current_profile_exposes_fixed_payload_and_unresolved_rf_inventory(), test_profile_rejects_wrong_numeric_types(), BenchProfile, load_bench_profile(), _optional_inventory(), _required_int()

### Community 157 - "LoRa ACK/NACK analysis and verification"
Cohesion: 0.12
Nodes (16): Current continuation, Earlier source-ownership migration, Markdown inventory and references, Source and documentation deletion audit, Bench ARQ protocol, Documentation audit, Historical baseline evidence, Historical hardware trial requirements and result (+8 more)

### Community 158 - "TaskScheduler"
Cohesion: 0.25
Nodes (4): TaskScheduler::GetTaskCount(), TaskScheduler, task_count_, tasks_

### Community 162 - "AVR128DA28 LoRa Board Pin Audit"
Cohesion: 0.29
Nodes (7): AVR128DA28 LoRa Board Pin Audit, AVR128DA28 package pins, Evidence basis, Gateway LoRa daughterboard, Radio profile and serial identity, Read the table, Tracker

### Community 164 - "detect_devices.py"
Cohesion: 0.20
Nodes (10): build_parser(), _load_registry(), main(), _probe_device(), _run_self_test(), SafetyArgumentParser, _scan(), _watch() (+2 more)

### Community 165 - "usb_inventory.py"
Cohesion: 0.16
Nodes (7): _print_result(), discover_usb_devices(), InventoryResult, _normalize_hex(), parse_udev_properties(), _run_command(), _usb_instance()

### Community 167 - "commands.cpp"
Cohesion: 0.24
Nodes (8): InputResult, kComplete, kOverflow, kPending, CommandInput::Feed(), DecodeHexDigit(), ParseCommand(), ReadFaultValue()

### Community 169 - "receiver_boot.py"
Cohesion: 0.05
Nodes (25): boot(), ApplicationPageWriteTests, BootPackageTests, CompiledHandoffTests, ReceiverBootTests, recording_command(), command(), normalize_ihex_region() (+17 more)

### Community 170 - "PacketMaintenanceAck"
Cohesion: 0.40
Nodes (4): DecodePacketMaintenanceAck(), PacketMaintenanceAck, response, type

### Community 172 - "Gate1Audit"
Cohesion: 0.18
Nodes (3): Gate1Audit, instrument(), open_exclusive()

### Community 173 - "ScanResult"
Cohesion: 0.23
Nodes (3): DetectedDevice, ScanResult, format_text()

### Community 174 - "protocol_adapter.py"
Cohesion: 0.20
Nodes (6): _assess_cancellation(), assess_case(), _assess_sequence_rollover(), FirmwareEvent, parse_event_row(), _result()

### Community 176 - "TraceBus"
Cohesion: 0.24
Nodes (4): main(), TraceBus, sensitivity_writes, stage

### Community 178 - "Logger"
Cohesion: 0.21
Nodes (6): ui64toa(), RawStorage, _cached_block, _cached_pos, Storage<T>::_save_state(), Sd2Card

### Community 179 - "spec_protocol.py"
Cohesion: 0.23
Nodes (6): _replay(), test_nonzero_radio_status_code_is_reported_as_failure(), test_replay_pass_requires_matching_two_sided_payload_and_ack(), test_replay_rejects_payload_mismatch(), test_replay_without_receiver_payload_bytes_is_unverified(), _write_replay_bundle()

### Community 180 - "AVR128DA28 LoRa firmware"
Cohesion: 0.33
Nodes (6): Application configuration, AVR128DA28 LoRa firmware, Build, Host tests, Preserved boundaries, Static analysis and formatting

### Community 186 - "shared/README.md"
Cohesion: 0.40
Nodes (3): Shared firmware modules, Adding and checking libraries, `stable_lib`

### Community 188 - "LORA_ACK_NACK.md"
Cohesion: 0.27
Nodes (4): Source ownership baseline, Real-radio verification evidence, Status: BLOCKED, no physical trials run, Receiver BOOT boundary

### Community 190 - "ResponseFault"
Cohesion: 0.25
Nodes (6): ResponseFault, kCampaign, kDrop, kDuplicate, kNone, kSequence

### Community 196 - "EventContext"
Cohesion: 0.15
Nodes (16): FlushBenchStatus(), RecordRadioRegisters(), RecordReceiveDiagnostics(), RecordStatusCounters(), RecordStatusTiming(), FrameRead, kDiscard, kRadioError (+8 more)

### Community 199 - "spec_payload.py"
Cohesion: 0.23
Nodes (6): _run_smoke_plan(), test_full_fifty_two_letter_alphabet_is_split_without_byte_loss(), test_random_ascii_changes_with_seed_and_boundary_patterns_stay_frame_bounded(), test_seed_reproduces_bounded_payloads_and_both_direction_character_coverage(), test_smoke_fault_cases_are_ten_total_and_cover_each_direction(), test_stress_plan_contains_sequence_255_to_zero_rollover_case()

### Community 203 - "Frame"
Cohesion: 0.22
Nodes (9): Frame, dst, length, payload, reason, sequence, session, src (+1 more)

### Community 204 - "arq_sender.h"
Cohesion: 0.24
Nodes (3): arq::DecodeFrame(), arq::EncodeFrame(), arq::IsValidFrame()

### Community 206 - "install_cpp_quality_tools.sh"
Cohesion: 0.50
Nodes (3): find_tool(), PATH, install_cpp_quality_tools.sh script

### Community 212 - "Shared Logic and Duplication Audit"
Cohesion: 0.33
Nodes (5): Kept separate deliberately, Outcome, Regression coverage, Responsibilities and migration, Shared Logic and Duplication Audit

### Community 213 - "Library Skills"
Cohesion: 0.40
Nodes (4): Commands, First-Time Setup, Library Skills, Safety

### Community 214 - "Revision"
Cohesion: 0.50
Nodes (4): Revision, major, minor, raw_revision_id

### Community 215 - "Library Skills"
Cohesion: 0.40
Nodes (4): Commands, First-Time Setup, Library Skills, Safety

### Community 217 - "RestartTask"
Cohesion: 0.29
Nodes (3): RestartTask, completions, entries

### Community 223 - "PacketReportWithAck"
Cohesion: 0.40
Nodes (4): PacketReportWithAck, report, seq, type

### Community 225 - "Final LoRa firmware architecture"
Cohesion: 0.40
Nodes (5): Board roles and source ownership, Build and safety boundary, Final LoRa firmware architecture, Protocol boundaries, Status

### Community 226 - "C++ Refactoring Baseline"
Cohesion: 0.40
Nodes (5): C++ Refactoring Baseline, Parent-revision measurements, Production and analysis scope, Repository snapshot, Toolchain and limits

### Community 227 - "Offline regression matrix"
Cohesion: 0.40
Nodes (5): Firmware matrix, Hardware is a separate gate, Host, quality, and fixture checks, Linked image checks, Offline regression matrix

### Community 228 - "PacketMaintenance"
Cohesion: 0.40
Nodes (4): DecodePacketMaintenance(), PacketMaintenance, command, type

### Community 229 - "LoRa Chat Firmware and Installed-Image Requirements"
Cohesion: 0.40
Nodes (4): Connecting to the installed boards, Installed Flash layout, LoRa Chat Firmware and Installed-Image Requirements, Source-level interactive protocol

### Community 231 - "FaultName"
Cohesion: 0.29
Nodes (3): CaptureStream, FaultName, ScenarioDirection

### Community 237 - "ExcludedSx1262Experiment"
Cohesion: 0.18
Nodes (11): 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates, Gateway Hardware SSOT — Rudolph Gateway, H1 (10-pin; only pins 1–5 used in the source schematic) (+3 more)

### Community 240 - "Json"
Cohesion: 0.18
Nodes (5): approve_writes(), phy_matches(), power_matches(), publish_receipt(), write_span_is_application()

### Community 246 - "PacketAck"
Cohesion: 0.40
Nodes (4): DecodePacketAck(), PacketAck, seq, type

### Community 247 - "PacketAdvertise"
Cohesion: 0.40
Nodes (4): DecodePacketAdvertise(), PacketAdvertise, seq, type

### Community 252 - "check_cpp.py"
Cohesion: 0.34
Nodes (9): capture_host_commands(), check(), complexity_check(), firmware_checks(), main(), record(), resolve_tools(), run() (+1 more)

### Community 257 - "Capture"
Cohesion: 0.09
Nodes (12): test_capture_journal_marks_buffered_lines_until_a_fresh_readiness_barrier(), test_capture_metrics_preserve_radio_errors_irq_and_missing_rf_metrics(), test_planned_transaction_failure_is_not_counted_as_background(), test_unplanned_transaction_failure_is_retained_in_run_summary(), test_lost_or_reset_legacy_monitor_cannot_trigger_data(), Capture, capture_diagnostics(), exchange_once() (+4 more)

### Community 299 - "sleep.cpp"
Cohesion: 0.14
Nodes (9): SetUnixTime(), SleepState, force_wakeup, is_sleeping, last_rtc_ticks, unix_time, GetTotalSeconds(), InitializeTime() (+1 more)

### Community 313 - "lora/library.json"
Cohesion: 0.25
Nodes (8): jgromes/RadioLib, build, includeDir, srcDir, dependencies, jgromes/RadioLib@7.1.2, name, version

### Community 315 - "time-utils/library.json"
Cohesion: 0.25
Nodes (8): paulstoffregen/Time, build, includeDir, srcDir, dependencies, paulstoffregen/Time@^1.6.1, name, version

### Community 341 - "ใช้งาน Codex Goal — LoRa E2E Feature-Based"
Cohesion: 0.33
Nodes (6): ค่าคลื่นวิทยุที่ตั้งไว้, ความต่างระหว่าง Goal กับ config, จุดที่ต้องพิสูจน์, เริ่มต้นใช้งานเฟิร์มแวร์ LoRa AVR128DA28, แหล่งอ้างอิง, ใช้งาน Codex Goal — LoRa E2E Feature-Based

## Knowledge Gaps
- **600 isolated node(s):** `day`, `fixquality`, `_gga_received`, `hour`, `latitude` (+595 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2110 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **142 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Transport` connect `Transport` to `State`, `.IsActive`, `.EmitEvent`, `Event`, `Result`, `string`, `ResponseFault`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Hardware` (e.g. with `DeviceEvent` and `RoundTripContext`) actually correct?**
  _`Hardware` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `day`, `fixquality`, `_gga_received` to the rest of the system?**
  _600 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.06460044809559373 - nodes in this community are weakly interconnected._
- **Why does `SystemConstants` connect `SystemConstants` to `Fixed settings and checks`, `arduino`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Should `ProofRun` be split into smaller, more focused modules?**
  _Cohesion score 0.09201480698043363 - nodes in this community are weakly interconnected._
- **Should `Storage` be split into smaller, more focused modules?**
  _Cohesion score 0.09401709401709402 - nodes in this community are weakly interconnected._