# Graph Report - SENIOR_PROJECT_RCA  (2026-11-20)

## Corpus Check
- 338 files · ~209,742 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 26 file(s) not represented in the graph (top: (none) 10, .toml 7, .css 4)

## Summary
- 4582 nodes · 9285 edges · 305 communities (176 shown, 129 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 637 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2b5a31cb`
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
- Hardware
- mvp_stub/Arduino.h
- ._arm_radio
- Transport
- Gate1Tests
- HardwareGateTests
- load
- gateway_radio.cpp
- ReaderFreeH01SummaryTests
- validate_live_proof
- Campaign
- ring_buffer.h
- raw_mvp_stub/Arduino.h
- tracker_radio_codec.cpp
- os
- rf_proof.py
- EventId
- SX1276
- .exchange
- reverse_raw_app.cpp
- runner.py
- image_evidence
- DeviceLayout
- Bus
- require
- TracePort
- production_bench.py
- AGENTS.md — AVR128DA28 / LoRa Embedded Engineering
- arduino
- upditerm.py
- TrackerConfig
- Task
- reliable_transport_test.cpp
- ReceiveTests
- Sender
- receiver_boot.py
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
- EventQueue
- Command
- Port
- role_log_test.cpp
- LoRa
- make_error
- 915 MHz LoRa bench procedure
- role_detector.py
- Receiver
- BenchTransport
- Json
- installed_rf.py
- ExcludedSx1262Experiment
- stdint
- Controller
- cli.py
- gateway_app.cpp
- firmware_identity.py
- complete_campaign_logs
- ring_buffer.h
- ErrataDiagnosticsTests
- Receiver APPCODE
- core_test.cpp
- RCATests
- test_lora_chat_protocol.py
- Pins
- mvp_app.cpp
- HexDataCommandDecoder
- ssot_codec.cpp
- ReportEntry
- ReverseRawTests
- BenchStatus
- Result
- tracker_config.h
- State
- gate1_live.py
- AdcTemp
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
- test_firmware_identity.py
- spec_timeout.py
- DebugConsoleTests
- task.h
- Connect to a virtual UART on an AVR via UPDI
- check_cpp.sh
- gate1.py
- C++ Refactoring Results
- Gateway-to-Receiver SF7 Hello World
- ControlInput
- gateway_ssot.hpp
- ExchangeResult
- LoRa ACK/NACK analysis and verification
- TaskScheduler
- SPIClass
- AVR128DA28 LoRa Board Pin Audit
- detect_devices.py
- usb_inventory.py
- .exchange_interactive_message
- symmetric_fixture
- install
- PacketMaintenanceAck
- SenderStableTransportTests
- Gate1Audit
- ScanResult
- protocol_adapter.py
- normalize_ihex_region
- TraceBus
- Logger
- spec_protocol.py
- AVR128DA28 LoRa firmware
- compare_snapshots
- Console
- RESULTS.md
- LORA_ACK_NACK.md
- avr128da28_memory_layout.h
- ResponseFault
- ReceiverBootTests
- spec_payload.py
- raw_mvp_stub/SPI.h
- trace_stub
- CppInterfaceTests
- Frame
- _build_handoff
- SsotProtocolTests
- install_cpp_quality_tools.sh
- .test_runner_uses_receiver_ready_then_one_gateway_start
- DeviceRole
- Library Skills
- Revision
- Library Skills
- RestartTask
- effective_platformio_config
- Tasks
- MonitorConsole
- PacketReport
- SingleFirmwareEntryTests
- Final LoRa firmware architecture
- Comm
- Offline regression matrix
- PacketMaintenance
- LoRa Chat Firmware and Installed-Image Requirements
- match_flash_fingerprint
- InstalledRadioEvidenceTests
- parse_raw_mvp_logs
- rf_test
- EventField
- ExcludedSx1262Experiment
- RadioTransactionTask
- identify_mcu
- stdio
- Source and documentation deletion audit
- HeartbeatTask
- main
- LORA_RF_STRESS_SPECIAL.md
- PacketAck
- PacketAdvertise
- _remember_bounded
- _event_style
- _event_summary
- check_cpp.py
- Sender APPCODE
- GatewayI2cTests
- echo_trials.py
- Real-radio verification evidence
- Firmware source map
- .connect
- _legacy_keyboard_mode
- sleep.cpp
- lora
- lora/library.json
- time-utils/library.json
- ใช้งาน Codex Goal — LoRa E2E Feature-Based
- Suggested append-only AGENTS.md contract (merge; do not overwrite existing instructions)

## God Nodes (most connected - your core abstractions)
1. `Transport` - 72 edges
2. `Hardware` - 66 edges
3. `BenchTransport` - 49 edges
4. `error()` - 47 edges
5. `SystemConstants` - 46 edges
6. `State` - 45 edges
7. `Gate1Tests` - 45 edges
8. `make_error()` - 43 edges
9. `LoRa` - 40 edges
10. `ProofRun` - 40 edges

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

## Communities (305 total, 129 thin omitted)

### Community 0 - "pathlib"
Cohesion: 0.06
Nodes (5): TaskRestartTests, I2cRadioConfigTests, RadioDiagnosticsTests, RadioLibHalTests, ihex_record()

### Community 1 - "ProofRun"
Cohesion: 0.12
Nodes (29): main(), package_target(), build(), inspect_image(), read_layouts(), authorized_application_pages(), capture_usb_topology(), check_port_owners() (+21 more)

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
Cohesion: 0.16
Nodes (18): error(), campaign(), progress(), run_one(), Capture, complete(), prepare(), radio_only_bringup() (+10 more)

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
Cohesion: 0.10
Nodes (15): ArqSoakPlanTests, fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), confirmed_rf_preflight(), dynamic_attr() (+7 more)

### Community 13 - "generate_lora_config.py"
Cohesion: 0.09
Nodes (16): SourceFingerprintTests, arq_artifacts(), load_arq(), validate_arq(), artifacts(), canonical(), digest(), load_radio_profile() (+8 more)

### Community 15 - "appcode/arq/receiver.cpp"
Cohesion: 0.32
Nodes (17): ArmSession(), CurrentSession(), ExecuteCommand(), FailAdapter(), FeedCommandByte(), FlushStatus(), GetEventContext(), HandleReceive() (+9 more)

### Community 16 - "RadioBringupTests"
Cohesion: 0.08
Nodes (7): DirectionalHostTests, RadioBringupTests, acquire(), command(), audit_radio_configuration(), read_radio(), validate_hello_exchange()

### Community 17 - "arq_trial.py"
Cohesion: 0.11
Nodes (28): build_soak_plan(), capture_tracker_diagnostics(), checked_events(), close_updi_without_recovery(), drain_updi_messages(), hardware_gate_errors(), hello_airtime_budget(), lora_time_on_air_us() (+20 more)

### Community 18 - "updi_role_log"
Cohesion: 0.17
Nodes (28): ReportBoot(), ReportBoot(), FlushEvent(), InteractivePayloadLimit(), ReportConfig(), ReportIdentity(), ReportInteractiveCapability(), ReportPhy() (+20 more)

### Community 19 - "Hardware"
Cohesion: 0.07
Nodes (3): Hardware, hardware_output(), BenchBlockedError

### Community 22 - "mvp_stub/Arduino.h"
Cohesion: 0.22
Nodes (4): CPUINT(), digitalReadFast(), digitalWrite(), digitalWriteFast()

### Community 23 - "._arm_radio"
Cohesion: 0.13
Nodes (6): approve_writes(), BenchFailedError, phy_matches(), power_matches(), publish_receipt(), write_span_is_application()

### Community 24 - "Transport"
Cohesion: 0.05
Nodes (35): Transport, armed_, confirming_ack_, context_, error_, event_context_, frequency_, have_accepted_ (+27 more)

### Community 26 - "Gate1Tests"
Cohesion: 0.10
Nodes (4): Gate1Tests, rows(), transaction(), verify_hashes()

### Community 27 - "HardwareGateTests"
Cohesion: 0.05
Nodes (6): dynamic_attr(), FlashSafetyTests, HardwareGateTests, command(), hardware_blockers(), upload_config_preserves_flash()

### Community 28 - "load"
Cohesion: 0.08
Nodes (9): ConfigurationTests, RawMvpTests, ReceiverHardwareTests, checked_cpp(), load(), main(), unique_object(), validate() (+1 more)

### Community 29 - "gateway_radio.cpp"
Cohesion: 0.13
Nodes (25): I2cCommandTask, command_, command_length_, StoreI2c16(), ArmRadio(), InitializeRadio(), IsRadioBenchActive(), IsRadioTransmitting() (+17 more)

### Community 30 - "ReaderFreeH01SummaryTests"
Cohesion: 0.08
Nodes (4): ArqTests, ReaderFreeH01SummaryTests, main(), reader_free_rx_idle_summary()

### Community 31 - "validate_live_proof"
Cohesion: 0.07
Nodes (16): fixture(), add(), LiveProofTests, emit(), start(), write(), expected_signature_hex(), parse_rf_campaign() (+8 more)

### Community 32 - "Campaign"
Cohesion: 0.08
Nodes (32): Campaign, attempts, campaign_id, destination, sequence, single_packet, source, state (+24 more)

### Community 34 - "ring_buffer.h"
Cohesion: 0.13
Nodes (6): RingBuffer, buffer_, RingBuffer<Capacity>::Read(), RingBuffer<Capacity>::ReadByte(), RingBuffer<Capacity>::WriteByte(), first_free_

### Community 35 - "raw_mvp_stub/Arduino.h"
Cohesion: 0.27
Nodes (5): begin(), digitalWrite(), end(), ltoa(), push_back()

### Community 36 - "tracker_radio_codec.cpp"
Cohesion: 0.24
Nodes (16): DecodeConfig(), DecodePacketBoot(), EncodeConfig(), EncodePacketAck(), EncodePacketAdvertise(), EncodePacketBoot(), EncodePacketMaintenance(), EncodePacketMaintenanceAck() (+8 more)

### Community 37 - "os"
Cohesion: 0.29
Nodes (11): _check_config(), _check_symlink(), _inside(), _items(), _label(), _local_dependency(), main(), _resolved() (+3 more)

### Community 38 - "rf_proof.py"
Cohesion: 0.07
Nodes (24): DirectionalTests, RadioOnlyTests, TargetLayoutTests, application_bounds_for_environment(), application_layout_verified(), boot_fuses_match(), build_flag_defines(), _config_int() (+16 more)

### Community 39 - "EventId"
Cohesion: 0.05
Nodes (41): Component, kApplication, kBoot, kHil, kNvm, Event(), EventId, kAuthenticationStarted (+33 more)

### Community 41 - ".exchange"
Cohesion: 0.06
Nodes (3): assess_exhaustion(), firmware_role(), parked()

### Community 42 - "reverse_raw_app.cpp"
Cohesion: 0.23
Nodes (13): arq_board, board_ssot_init(), ExecuteCommand(), FeedCommandByte(), Initialize(), IsPayloadCommand(), ParkRadio(), Poll() (+5 more)

### Community 43 - "runner.py"
Cohesion: 0.04
Nodes (32): load_event_journal(), calculate_metrics(), _percentile(), generate_payload(), split_payload(), _add_direction_cases(), _append_case(), build_case_plan() (+24 more)

### Community 44 - "image_evidence"
Cohesion: 0.16
Nodes (8): wire(), event(), image_evidence(), journal(), StableTransportProofTests, wrong_destination_journal(), assess(), validate_stable_transport()

### Community 45 - "DeviceLayout"
Cohesion: 0.12
Nodes (18): DeviceLayout, kAppDataStart, kApplicationEnd, kApplicationImageEnd, kApplicationStart, kBootEnd, kBootSizePages, kBootStart (+10 more)

### Community 47 - "Bus"
Cohesion: 0.11
Nodes (6): Bus, fifo, finish_delay, regs, reset_mode, ticks

### Community 48 - "require"
Cohesion: 0.11
Nodes (4): DetectionIntegrationTests, pio(), runner(), require()

### Community 49 - "TracePort"
Cohesion: 0.09
Nodes (3): instrument(), open_exclusive(), TracePort

### Community 50 - "production_bench.py"
Cohesion: 0.23
Nodes (6): bootstrap(), create_temp_dir(), main(), bootstrap(), create_temp_dir(), main()

### Community 52 - "AGENTS.md — AVR128DA28 / LoRa Embedded Engineering"
Cohesion: 0.09
Nodes (21): 10. Logging, measurement, and evidence, 11. Decision and intervention policy, 12. Response contract, 13. Technical references (read when relevant; do not substitute for active SSOT), 1. Mission and current MVP, 2. Operating philosophy, 3. Project truth and protected files, 4. Target architecture (+13 more)

### Community 53 - "arduino"
Cohesion: 0.09
Nodes (6): PrepareTrackerForRadioOnly(), Initialize(), InitializeRadio(), InitializeReceiverGpio(), main(), reset_radio()

### Community 54 - "upditerm.py"
Cohesion: 0.07
Nodes (8): Console, main(), parse_arguments(), SerialPort, SerialUPDI, Terminal, TransportError, UPDI

### Community 55 - "TrackerConfig"
Cohesion: 0.10
Nodes (18): TrackerConfig, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 57 - "Task"
Cohesion: 0.21
Nodes (6): Task::Task(), Task, is_paused_, pt_, wakeup_time_, main()

### Community 58 - "reliable_transport_test.cpp"
Cohesion: 0.08
Nodes (23): AcceptedPayload, allow_new, bytes, size, EventLog, count, names, FakeRadio (+15 more)

### Community 59 - "ReceiveTests"
Cohesion: 0.13
Nodes (3): ReceiveTests, wait(), wait()

### Community 60 - "Sender"
Cohesion: 0.07
Nodes (37): Result, kOk, kPending, kProtocolError, kRadioError, kRejected, kTimeoutExhausted, Sender (+29 more)

### Community 61 - "receiver_boot.py"
Cohesion: 0.19
Nodes (6): Laboratory deployment and recovery, enrolled_port(), read_snapshot(), read_snapshot_command(), require_preserved(), verify_live_receipt()

### Community 62 - "PlatformResult"
Cohesion: 0.13
Nodes (18): InitializeAdc(), ReadBatteryAdc(), ReadSample(), ReadTemperatureAdc(), WaitForConversion(), PlatformResult, kBusy, kForbidden (+10 more)

### Community 63 - "sender/appcode/reliable.cpp"
Cohesion: 0.18
Nodes (18): Poll(), AcceptData(), ArmRadio(), HandleRadioCommand(), Initialize(), InitializeGpio(), InitializeRoleGpio(), Poll() (+10 more)

### Community 64 - "MvpRoundtripTests"
Cohesion: 0.21
Nodes (3): Board, frames(), MvpRoundtripTests

### Community 65 - "test_application_config.py"
Cohesion: 0.11
Nodes (7): ApplicationConfigTests, diagnostic_case(), load(), raw_payload(), raw_send_command(), render(), validate()

### Community 66 - "LoRa Recovery Repository Audit"
Cohesion: 0.09
Nodes (21): A — การดำเนินการ, Hardware readback และ RF, R — ผลการตรวจสอบ, S — สถานการณ์, Software และ firmware build, T — งานที่ต้องทำ, การตัดสินใจ, ขั้นตอนถัดไป (+13 more)

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

### Community 73 - "EventQueue"
Cohesion: 0.11
Nodes (15): Event, campaign_id, error, name, sequence, time_ms, type, EventQueue (+7 more)

### Community 74 - "Command"
Cohesion: 0.07
Nodes (26): Command, budget, kind, payload, payload_length, session, stride, CommandInput (+18 more)

### Community 75 - "Port"
Cohesion: 0.21
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 76 - "role_log_test.cpp"
Cohesion: 0.10
Nodes (6): DecodeLoraConfig(), EepromSpy, reads, writes, main(), clear_capture()

### Community 77 - "LoRa"
Cohesion: 0.08
Nodes (20): Application and dependency audit, Firmware matrix, Historical BOOT and deployment status, Offline LoRa firmware refactor, Verification, Wire and host evidence, ReportRegisters(), Address (+12 more)

### Community 78 - "make_error"
Cohesion: 0.04
Nodes (11): test_csi_u_keyboard_sequence_is_rejected_as_a_message(), test_prompt_admits_utf8_when_both_endpoints_support_echo(), ConsoleRuntime, _help_panel(), InteractiveConsole, _parse_event(), make_error(), ChatSession (+3 more)

### Community 80 - "915 MHz LoRa bench procedure"
Cohesion: 0.29
Nodes (6): 915 MHz LoRa bench procedure, App-only programming after exact write approval, Hardware results, Refactor verification, RF conditions and acceptance, Verified candidates

### Community 81 - "role_detector.py"
Cohesion: 0.15
Nodes (10): DetectedDevice, FirmwareIdentity, ProbeEvidence, USBDevice, classify_devices(), diff_device_presence(), _identity_role(), _probe_for() (+2 more)

### Community 82 - "Receiver"
Cohesion: 0.06
Nodes (30): Source ownership and dependency map, IsDeadlineDue(), Receiver, accepted, armed, deliveries, duplicates, expected (+22 more)

### Community 83 - "BenchTransport"
Cohesion: 0.05
Nodes (9): test_plain_chat_uses_only_the_configured_bench_defaults(), test_archived_gateway_names_and_full_fresh_readback(), test_connect_read_only_with_a_current_build_mismatch(), test_dry_run_creates_empty_event_log_and_disables_transmission(), test_post_rf_tracker_monitor_reopens_without_reissuing_data(), test_rf_authorization_requires_separate_setup_confirmation(), test_verified_current_pair_takes_precedence_over_saved_legacy_receipt(), main() (+1 more)

### Community 84 - "Json"
Cohesion: 0.14
Nodes (13): _fault_bundle(), _run_replay(), test_cancel_fault_is_not_passed_by_a_normal_ack_exchange(), test_cancel_is_passed_only_after_both_radios_park_and_ports_release(), test_cancel_requires_park_after_the_cancel_request(), test_controlled_nack_retries_the_same_session_and_sequence(), test_crc_rejection_uses_timeout_recovery_without_application_nack(), test_duplicate_is_not_passed_without_single_delivery_evidence() (+5 more)

### Community 85 - "installed_rf.py"
Cohesion: 0.06
Nodes (17): test_capture_journal_marks_buffered_lines_until_a_fresh_readiness_barrier(), test_capture_metrics_preserve_radio_errors_irq_and_missing_rf_metrics(), test_planned_transaction_failure_is_not_counted_as_background(), test_unplanned_transaction_failure_is_retained_in_run_summary(), test_lost_or_reset_legacy_monitor_cannot_trigger_data(), main(), assess_control_fault(), assess_probe() (+9 more)

### Community 86 - "ExcludedSx1262Experiment"
Cohesion: 0.20
Nodes (10): ExcludedSx1262Experiment, BUSY_PIN, DIO1_PIN, ERROR_RETRY_DELAY_MS, NSS_PIN, PACKET_BYTES, PACKET_COUNT, PACKET_GAP_MS (+2 more)

### Community 90 - "Controller"
Cohesion: 0.13
Nodes (12): Controller, last_led1_toggle_, last_tx_toggle_, led1_interval_ms_, led1_on_, led1_pin_, led2_pin_, led_off_level_ (+4 more)

### Community 91 - "cli.py"
Cohesion: 0.03
Nodes (22): test_terminal_output_preserves_rich_ansi_in_prompt_toolkit(), test_typer_app_exposes_help_for_supported_options(), test_current_profile_exposes_fixed_payload_and_unresolved_rf_inventory(), test_profile_rejects_wrong_numeric_types(), test_run_directory_is_created_once_by_the_transport(), ConsoleCommand, ConsoleStateError, _create_run_directory() (+14 more)

### Community 94 - "gateway_app.cpp"
Cohesion: 0.07
Nodes (7): I2cResetTask, timestamp_ms_, InitializeEspCommunication(), Initialize(), Poll(), ReadTemperatureCelsius(), RegisterRadioTask()

### Community 95 - "firmware_identity.py"
Cohesion: 0.22
Nodes (6): crc8(), IdentityParseResult, parse_identity_stream(), _valid_build(), _valid_timestamp(), _is_access_error()

### Community 96 - "complete_campaign_logs"
Cohesion: 0.38
Nodes (4): complete_campaign_logs(), packet_event(), payload_event(), RfEvidenceTests

### Community 97 - "ring_buffer.h"
Cohesion: 0.16
Nodes (5): RingBuffer<Capacity>::Write(), RingBuffer<Capacity>::WriteFrame(), RingBufferPart, data, length

### Community 98 - "ErrataDiagnosticsTests"
Cohesion: 0.13
Nodes (5): ErrataDiagnosticsTests, decode_snapshot(), interpret_rx(), link_budget(), main()

### Community 99 - "Receiver APPCODE"
Cohesion: 0.67
Nodes (3): Hardware and power, Receiver APPCODE, Source path

### Community 101 - "core_test.cpp"
Cohesion: 0.38
Nodes (12): absolute_deadline(), ack_matrix(), codec(), control(), data(), fault_harness(), fresh(), main() (+4 more)

### Community 103 - "test_lora_chat_protocol.py"
Cohesion: 0.04
Nodes (42): _chunk_events(), test_ack_alone_never_counts_as_a_tracker_echo(), test_ack_matching_requires_campaign_sequence_and_type(), test_echo_latency_uses_the_gateway_clock_and_first_attempt(), test_encodes_supported_utf8_bytes_exactly(), test_interactive_boundaries_reject_empty_oversize_and_invalid_utf8(), test_interactive_capability_requires_echo_support_from_both_endpoints(), test_interactive_host_command_encodes_payload_length_and_bytes() (+34 more)

### Community 105 - "Pins"
Cohesion: 0.14
Nodes (14): Pins, ANALOG_IN_0, ANALOG_IN_1, DEBUG_RX, DEBUG_TX, HOST_INT, LED1, LED2 (+6 more)

### Community 106 - "mvp_app.cpp"
Cohesion: 0.37
Nodes (12): debug_init(), debug_write(), debug_write_float(), debug_write_hex(), debug_write_int(), Initialize(), Poll(), RecordStartupStage() (+4 more)

### Community 107 - "HexDataCommandDecoder"
Cohesion: 0.08
Nodes (20): HexDataCommandDecoder, high_nibble_, length_, received_, state_, Result, kComplete, kInvalidBuffer (+12 more)

### Community 110 - "ssot_codec.cpp"
Cohesion: 0.18
Nodes (15): DecodePayloadFields(), EncodeControlPayload(), ssot::AckMatches(), ssot::DecodeFrame(), ssot::DecodePayload(), ssot::EncodeAckFrame(), ssot::EncodeAckPayload(), ssot::EncodeDataFrame() (+7 more)

### Community 111 - "ReportEntry"
Cohesion: 0.13
Nodes (22): ReportEntry, day, hour, latitude, longitude, minute, month, quality (+14 more)

### Community 112 - "ReverseRawTests"
Cohesion: 0.16
Nodes (4): ReverseRawTests, audit_raw_configuration(), reverse_exchange(), status()

### Community 113 - "BenchStatus"
Cohesion: 0.07
Nodes (35): BenchStatus, attempted, completed, control_rejects, crc_errors, decode_errors, deliveries, duplicates (+27 more)

### Community 114 - "Result"
Cohesion: 0.22
Nodes (8): Result, kAccepted, kAckTimeout, kInvalidArgument, kPending, kRadioError, kRejected, kTxTimeout

### Community 115 - "tracker_config.h"
Cohesion: 0.29
Nodes (6): Checkpoint, INVALID_GNSS_DATE, SPI_CTRL_BEFORE_LORA, SPI_CTRL_BEFORE_PWR_ON, TRACKER_AFTER_GNSS_ON, TRACKER_BEFORE_GNSS_ON

### Community 117 - "State"
Cohesion: 0.17
Nodes (12): State, begin_count, cs_high_seen, cs_low_seen, cs_pin, initialized, route, swap_count (+4 more)

### Community 119 - "gate1_live.py"
Cohesion: 0.18
Nodes (22): controlled_cpu_reset(), firmware_identity_from_events(), gpr_roundtrip_succeeded(), halted_gpr_roundtrip(), mailbox_snapshot(), main(), _parse_block(), part_from_signature() (+14 more)

### Community 120 - "AdcTemp"
Cohesion: 0.17
Nodes (12): AdcTemp, ADC_MAX_COUNTS, CTRLA_ENABLE_12BIT, FIXED_POINT_SHIFT, INIT_DELAY_SETTING, KELVIN_TO_CELSIUS, MUX_TEMP_CHANNEL, PRESCALER_SETTING (+4 more)

### Community 121 - "State"
Cohesion: 0.22
Nodes (8): State, kComplete, kFailed, kRetryPending, kRxWait, kTxData, kTxResponse, kWaitResponse

### Community 122 - "test_lora_chat_session.py"
Cohesion: 0.08
Nodes (19): _event(), _session(), test_ack_matching_deduplicates_replayed_event_counts(), test_ack_without_real_echo_is_not_round_trip_success(), test_captured_echo_timeout_counts_once(), test_chat_settings_allow_zero_manual_retries(), test_chat_settings_enforce_memory_and_refresh_caps(), test_chat_settings_reject_unknown_keys_and_invalid_limits() (+11 more)

### Community 123 - "receiver/appcode/reliable.cpp"
Cohesion: 0.11
Nodes (14): AcceptData(), ArmRadio(), HandleRadioCommand(), Initialize(), InitializeGpio(), InitializeRoleGpio(), RecordTransportEvent(), updi_role_log_dropped() (+6 more)

### Community 124 - "diagnostics.cpp"
Cohesion: 0.10
Nodes (22): AcquireLine(), FlushByte(), OverflowCount(), PendingLineCount(), RecordDiscard(), RecordEvent(), RecordFrame(), drain_status() (+14 more)

### Community 125 - "avr128da28_device.h"
Cohesion: 0.15
Nodes (12): IsAppCodeRange(), PORT_struct, PORT_t, SPI_struct, SPI_t, TWI_struct, TWI_t, TwiHold (+4 more)

### Community 126 - "spec_runner.py"
Cohesion: 0.18
Nodes (6): test_default_cli_writes_a_zero_transmission_dry_run(), test_real_rf_requires_explicit_profile_and_saved_readback(), test_stress_config_rejects_unknown_settings(), test_torture_config_must_keep_one_thousand_transaction_minimum(), test_torture_plan_has_at_least_one_thousand_cases_and_a_bounded_runtime(), test_torture_profile_requires_long_duration_opt_in()

### Community 128 - "updi_probe.py"
Cohesion: 0.31
Nodes (6): _port_busy(), probe_firmware_identity(), probe_target_sib(), read_firmware_flash(), _require_safe(), _run_bounded()

### Community 131 - "PacketBoot"
Cohesion: 0.25
Nodes (7): PacketBoot, checkpoint, config, device_model, firmware, reset_flags, type

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
Cohesion: 0.09
Nodes (3): discover_ports(), main(), Session

### Community 137 - "Fixed settings and checks"
Cohesion: 0.40
Nodes (4): Fixed settings and checks, Runtime settings, Scope, Tracker Configuration SSOT

### Community 138 - "SdFile"
Cohesion: 0.10
Nodes (16): open_file_in_root(), read_line(), mbr_t, mbrSig0, mbrSig1, part, SdFile, data_ (+8 more)

### Community 139 - "Logger"
Cohesion: 0.27
Nodes (5): Logger, _capacity, _cursor, _raw, _start_block

### Community 140 - "Radio915ValidationTests"
Cohesion: 0.17
Nodes (3): Radio915ValidationTests, valid_profile(), write_toml()

### Community 141 - "test_firmware_identity.py"
Cohesion: 0.16
Nodes (8): _hex_image(), _record(), test_flash_comparison_rejects_hex_data_outside_the_authorized_region(), test_flash_comparison_reports_exact_sparse_image_match(), test_flash_comparison_reports_first_actual_mismatch_address(), compare_flash_region(), FlashComparison, parse_ihex_image()

### Community 143 - "spec_timeout.py"
Cohesion: 0.19
Nodes (9): _replay(), test_gateway_accepting_wrong_sequence_is_a_false_ack_failure(), test_latency_wraps_the_same_device_millisecond_counter(), test_retry_limit_excess_is_a_failure(), test_timeout_recovery_keeps_the_same_session_and_sequence(), test_wrong_campaign_is_explicitly_rejected(), test_wrong_destination_must_be_ignored_until_timeout(), test_wrong_sequence_is_explicitly_rejected_before_correct_ack() (+1 more)

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
Cohesion: 0.29
Nodes (7): A — Action, C++ Refactoring Results, Current follow-up verification — 2026-11-19, R — Result, S — Situation, T — Task, Trade-offs and limits

### Community 152 - "Gateway-to-Receiver SF7 Hello World"
Cohesion: 0.25
Nodes (7): Current result — Receiver installed, normal startup unresolved, Gateway-to-Receiver SF7 Hello World, No-meter read-only hardware verified; Receiver write wiring unconfirmed, Receiver boot incompatibility, Remaining physical prerequisites, Single-packet behavior and identities, Verified software result

### Community 154 - "ControlInput"
Cohesion: 0.20
Nodes (9): ControlInput, command, digits, last_ms, reading, triggered, value, ssot::ControlInputFeed() (+1 more)

### Community 155 - "gateway_ssot.hpp"
Cohesion: 0.20
Nodes (8): Memory, I2C_MAILBOX_BYTES, SHARED_RINGBUF_BYTES, System, ENABLE_ESPCOMM, ENABLE_LORA_RX, ENABLE_WATCHDOG, WDT_TIMEOUT_PERIOD

### Community 156 - "ExchangeResult"
Cohesion: 0.11
Nodes (6): test_fragmentation_preserves_exact_bytes_at_the_negotiated_packet_limit(), test_interactive_encoder_accepts_bounded_utf8_messages(), encode_interactive_message(), fragment_message(), ExchangeResult, _result_count()

### Community 157 - "LoRa ACK/NACK analysis and verification"
Cohesion: 0.20
Nodes (10): Bench ARQ protocol, Documentation audit, Historical baseline evidence, Historical hardware trial requirements and result, Installed SRAM-only pair, LoRa ACK/NACK analysis and verification, Production bench repair report, Runbook (+2 more)

### Community 158 - "TaskScheduler"
Cohesion: 0.22
Nodes (4): TaskScheduler::GetTaskCount(), TaskScheduler, task_count_, tasks_

### Community 159 - "SPIClass"
Cohesion: 0.18
Nodes (3): beginTransaction(), SPIClass, SPISettings

### Community 162 - "AVR128DA28 LoRa Board Pin Audit"
Cohesion: 0.29
Nodes (7): AVR128DA28 LoRa Board Pin Audit, AVR128DA28 package pins, Evidence basis, Gateway LoRa daughterboard, Radio profile and serial identity, Read the table, Tracker

### Community 164 - "detect_devices.py"
Cohesion: 0.19
Nodes (10): build_parser(), _load_registry(), main(), _probe_device(), _run_self_test(), SafetyArgumentParser, _scan(), _watch() (+2 more)

### Community 165 - "usb_inventory.py"
Cohesion: 0.16
Nodes (7): _print_result(), discover_usb_devices(), InventoryResult, _normalize_hex(), parse_udev_properties(), _run_command(), _usb_instance()

### Community 167 - "symmetric_fixture"
Cohesion: 0.21
Nodes (4): symmetric_fixture(), add(), event(), SymmetricProofTests

### Community 169 - "install"
Cohesion: 0.24
Nodes (6): boot(), BootPackageTests, recording_command(), install(), load_package(), sha()

### Community 170 - "PacketMaintenanceAck"
Cohesion: 0.40
Nodes (4): DecodePacketMaintenanceAck(), PacketMaintenanceAck, response, type

### Community 172 - "Gate1Audit"
Cohesion: 0.23
Nodes (4): Gate1Audit, _read_block(), _readline(), utc()

### Community 173 - "ScanResult"
Cohesion: 0.16
Nodes (4): ScanResult, exit_code_for(), format_text(), result_to_json()

### Community 174 - "protocol_adapter.py"
Cohesion: 0.13
Nodes (9): _assess_cancellation(), assess_case(), _assess_sequence_rollover(), CaptureStream, FaultName, FirmwareEvent, parse_event_row(), _result() (+1 more)

### Community 175 - "normalize_ihex_region"
Cohesion: 0.18
Nodes (4): BuildIdentityImagesTests, normalize_ihex_region(), _parse_ihex(), prepare()

### Community 176 - "TraceBus"
Cohesion: 0.22
Nodes (4): main(), TraceBus, sensitivity_writes, stage

### Community 178 - "Logger"
Cohesion: 0.21
Nodes (7): ui64toa(), RawStorage, _cached_block, _cached_pos, Storage<T>::_save_state(), get_data_and_log_partitions(), Sd2Card

### Community 179 - "spec_protocol.py"
Cohesion: 0.23
Nodes (6): _replay(), test_nonzero_radio_status_code_is_reported_as_failure(), test_replay_pass_requires_matching_two_sided_payload_and_ack(), test_replay_rejects_payload_mismatch(), test_replay_without_receiver_payload_bytes_is_unverified(), _write_replay_bundle()

### Community 180 - "AVR128DA28 LoRa firmware"
Cohesion: 0.33
Nodes (6): Application configuration, AVR128DA28 LoRa firmware, Build, Host tests, Preserved boundaries, Static analysis and formatting

### Community 181 - "compare_snapshots"
Cohesion: 0.15
Nodes (3): classify(), compare_snapshots(), delta()

### Community 186 - "RESULTS.md"
Cohesion: 0.15
Nodes (9): C++ Refactoring Baseline, Parent-revision measurements, Production and analysis scope, Repository snapshot, Toolchain and limits, Source ownership baseline, Shared firmware modules, Adding and checking libraries (+1 more)

### Community 190 - "ResponseFault"
Cohesion: 0.25
Nodes (6): ResponseFault, kCampaign, kDrop, kDuplicate, kNone, kSequence

### Community 199 - "spec_payload.py"
Cohesion: 0.23
Nodes (6): _run_smoke_plan(), test_full_fifty_two_letter_alphabet_is_split_without_byte_loss(), test_random_ascii_changes_with_seed_and_boundary_patterns_stay_frame_bounded(), test_seed_reproduces_bounded_payloads_and_both_direction_character_coverage(), test_smoke_fault_cases_are_ten_total_and_cover_each_direction(), test_stress_plan_contains_sequence_255_to_zero_rollover_case()

### Community 201 - "trace_stub"
Cohesion: 0.22
Nodes (3): CompiledHandoffTests, reset_target(), trace_stub()

### Community 203 - "Frame"
Cohesion: 0.22
Nodes (9): Frame, dst, length, payload, reason, sequence, session, src (+1 more)

### Community 204 - "_build_handoff"
Cohesion: 0.24
Nodes (3): build_fixture(), _build_handoff(), page_write_command()

### Community 206 - "install_cpp_quality_tools.sh"
Cohesion: 0.50
Nodes (3): find_tool(), PATH, install_cpp_quality_tools.sh script

### Community 212 - "DeviceRole"
Cohesion: 0.14
Nodes (7): Kept separate deliberately, Outcome, Regression coverage, Responsibilities and migration, Shared Logic and Duplication Audit, DeviceRole, _latest_event()

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

### Community 218 - "effective_platformio_config"
Cohesion: 0.11
Nodes (7): BuildAcceptanceTests, ApplicationPageWriteTests, command(), appcode_platformio_config(), _base_platformio_sections(), effective_platformio_config(), ihex()

### Community 221 - "Tasks"
Cohesion: 0.22
Nodes (9): Tasks, ENABLE_HEARTBEAT_TASK, HEARTBEAT_NAME, HEARTBEAT_OFF_MS, HEARTBEAT_ON_MS, HEARTBEAT_PERIOD_MS, I2C_RESET_SETTLE_MS, LED1_TOGGLE_INTERVAL_MS (+1 more)

### Community 223 - "PacketReport"
Cohesion: 0.13
Nodes (13): DecodePacketReport(), DecodePacketReportWithAck(), DecodeReportEntry(), LoadSigned16(), LoadSigned32(), PacketReport, report, seq (+5 more)

### Community 225 - "Final LoRa firmware architecture"
Cohesion: 0.40
Nodes (5): Board roles and source ownership, Build and safety boundary, Final LoRa firmware architecture, Protocol boundaries, Status

### Community 226 - "Comm"
Cohesion: 0.25
Nodes (8): Comm, AIR_CONFIG_NODE_ADDR, DEBUG_BAUD_RATE, ENABLE_I2C_WIRE, GATEWAY_ANYCAST_ADDR, GATEWAY_DEFAULT_ADDR, I2C_ADDRESS_BASE, I2C_ADDRESS_STRAP_SHIFT

### Community 227 - "Offline regression matrix"
Cohesion: 0.40
Nodes (5): Firmware matrix, Hardware is a separate gate, Host, quality, and fixture checks, Linked image checks, Offline regression matrix

### Community 228 - "PacketMaintenance"
Cohesion: 0.40
Nodes (4): DecodePacketMaintenance(), PacketMaintenance, command, type

### Community 229 - "LoRa Chat Firmware and Installed-Image Requirements"
Cohesion: 0.40
Nodes (4): Connecting to the installed boards, Installed Flash layout, LoRa Chat Firmware and Installed-Image Requirements, Source-level interactive protocol

### Community 231 - "match_flash_fingerprint"
Cohesion: 0.33
Nodes (3): FingerprintResult, match_flash_fingerprint(), firmware_fingerprint_evidence()

### Community 234 - "rf_test"
Cohesion: 0.09
Nodes (18): RfTestContinuationTests, assess_installed_exchange(), capture_radio_spi_log(), parse_radio_spi_log(), rf_test(), command(), record(), run_mvp_acceptance() (+10 more)

### Community 237 - "ExcludedSx1262Experiment"
Cohesion: 0.18
Nodes (11): 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates, Gateway Hardware SSOT — Rudolph Gateway, H1 (10-pin; only pins 1–5 used in the source schematic) (+3 more)

### Community 240 - "identify_mcu"
Cohesion: 0.50
Nodes (3): First failing boundary in the current real startup, LoRa Recovery Root Cause Analysis, identify_mcu()

### Community 241 - "stdio"
Cohesion: 0.09
Nodes (9): Frame, campaign_id, destination, sequence, source, type, main(), main() (+1 more)

### Community 242 - "Source and documentation deletion audit"
Cohesion: 0.50
Nodes (4): Current continuation, Earlier source-ownership migration, Markdown inventory and references, Source and documentation deletion audit

### Community 246 - "PacketAck"
Cohesion: 0.40
Nodes (4): DecodePacketAck(), PacketAck, seq, type

### Community 247 - "PacketAdvertise"
Cohesion: 0.40
Nodes (4): DecodePacketAdvertise(), PacketAdvertise, seq, type

### Community 252 - "check_cpp.py"
Cohesion: 0.34
Nodes (9): capture_host_commands(), check(), complexity_check(), firmware_checks(), main(), record(), resolve_tools(), run() (+1 more)

### Community 254 - "Sender APPCODE"
Cohesion: 0.67
Nodes (3): Builds and hardware, Sender APPCODE, Source path

### Community 277 - "echo_trials.py"
Cohesion: 0.13
Nodes (8): test_legacy_pair_blocks_acceptance_without_sending(), test_missing_echo_trial_requires_matching_ack_and_timeout(), test_trial_list_has_utf8_boundary_and_command_like_payloads(), main(), messages(), run_trials(), suppressed_echo_observed(), _write_json()

### Community 299 - "sleep.cpp"
Cohesion: 0.13
Nodes (10): SetUnixTime(), SleepFor(), SleepState, force_wakeup, is_sleeping, last_rtc_ticks, unix_time, GetTotalSeconds() (+2 more)

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2135 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **129 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Transport` connect `Transport` to `.EmitEvent`, `EventQueue`, `Result`, `State`, `receiver/appcode/reliable.cpp`, `ResponseFault`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `Hardware` (e.g. with `DeviceEvent` and `RoundTripContext`) actually correct?**
  _`Hardware` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `day`, `fixquality`, `_gga_received` to the rest of the system?**
  _600 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.06378865979381443 - nodes in this community are weakly interconnected._
- **Why does `error()` connect `error` to `pathlib`, `analyze`, `Session`, `test_lora_chat_protocol.py`, `.exchange`, `rf_test`, `runner.py`, `ArqSoakPlanTests`, `make_error`, `arq_trial.py`, `Hardware`, `BenchTransport`, `echo_trials.py`, `upditerm.py`, `Console`, `ReceiveTests`, `ExchangeResult`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Should `ProofRun` be split into smaller, more focused modules?**
  _Cohesion score 0.11510204081632654 - nodes in this community are weakly interconnected._
- **Why does `Board` connect `MvpRoundtripTests` to `pathlib`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._