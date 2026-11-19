# Graph Report - SENIOR_PROJECT_RCA  (2026-11-20)

## Corpus Check
- 326 files · ~195,723 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 26 file(s) not represented in the graph (top: (none) 10, .toml 7, .css 4)

## Summary
- 4294 nodes · 8535 edges · 282 communities (165 shown, 117 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 538 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b3b3d936`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- pathlib
- rf_proof.py
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
- check_cpp.py
- appcode/arq/receiver.cpp
- RadioBringupTests
- arq_trial.py
- updi_role_log
- validate_live_proof
- mvp_stub/Arduino.h
- cli.py
- Transport
- Gate1Tests
- effective_platformio_config
- load
- gateway_radio.cpp
- ReaderFreeH01SummaryTests
- ._run_capture
- Campaign
- ring_buffer.h
- tracker_radio_codec.cpp
- ScanResult
- sd-storage.h
- EventId
- SX1276
- ControlInput
- reverse_raw_app.cpp
- discover_usb_devices
- image_evidence
- DeviceLayout
- Bus
- require
- TracePort
- diagnostics.cpp
- string
- AGENTS.md — AVR128DA28 / LoRa Embedded Engineering
- HardwareGateTests
- upditerm.py
- TrackerConfig
- Task
- FakeRadio
- ReceiveTests
- Sender
- Logger
- PlatformResult
- receiver_boot.py
- MvpRoundtripTests
- test_application_config.py
- dynamic_attr
- require
- OPERATING CONTRACT — READ ALL BEFORE EDITING
- Config
- .EmitEvent
- Tracker Hardware SSOT — LoRa Tracker RFM
- Sd2Card
- EventQueue
- commands.cpp
- Port
- radio_link.cpp
- LoRa
- make_error
- 915 MHz LoRa bench procedure
- boot_analysis.py
- Receiver
- main
- Json
- installed_rf.py
- ExcludedSx1262Experiment
- stdint
- Controller
- System
- stub/RadioLib.h
- Any
- complete_campaign_logs
- debug_protocol_ack_nack.py
- ErrataDiagnosticsTests
- Receiver APPCODE
- raw_mvp_stub/Arduino.h
- SessionConfigError
- load_config
- Pins
- mvp_app.cpp
- Pair
- PacketAdvertise
- ssot_codec.cpp
- ReportEntry
- SD.h
- Frame
- Result
- tracker_config.h
- State
- gate1_live.py
- avr128da28_device.h
- State
- test_lora_chat_session.py
- receiver/appcode/reliable.cpp
- parse_raw_mvp_logs
- metrics.py
- reliable_transport_test.cpp
- ReliableTransportTests
- production_bench.py
- BuildEnvironment
- Frame
- PacketBoot
- LoRa source ownership V2
- ErrorCode
- ProvisioningResult
- EventStats
- StableLoraSafetyTests
- Fixed settings and checks
- SdFile
- detect_devices.py
- spec_timeout.py
- Module
- SessionConfigTypeError
- Connect to a virtual UART on an AVR via UPDI
- check_cpp.sh
- gate1.py
- C++ Refactoring Results
- Gateway-to-Receiver SF7 Hello World
- AdcTemp
- adc.cpp
- ProfileTypeError
- LoRa ACK/NACK analysis and verification
- Offline LoRa firmware refactor
- _remember_bounded
- AVR128DA28 LoRa Board Pin Audit
- updi_probe.py
- RfTestContinuationTests
- LossMetrics
- runner.py
- PacketMaintenanceAck
- SenderStableTransportTests
- Gate1Audit
- role_detector.py
- protocol_adapter.py
- BuildIdentityImagesTests
- .test_rf_enabled_upload_does_not_require_rf_authorization
- RawStorage
- spec_protocol.py
- AVR128DA28 LoRa firmware
- .test_T36_wide_gpr_counterfactual_uses_16_bit_sts_only_for_gprs
- GatewayI2cTests
- Tasks
- LORA_ACK_NACK.md
- ResponseFault
- Comm
- firmware_identity.py
- spec_payload.py
- spec_runner.py
- application_bounds_for_environment
- CppInterfaceTests
- core_test.cpp
- SsotProtocolTests
- install_cpp_quality_tools.sh
- main
- ConsoleStateError
- test_arq.py
- ihex
- replay_bundle
- load_package
- PacketAck
- MonitorConsole
- PacketReport
- SingleFirmwareEntryTests
- Final LoRa firmware architecture
- RESULTS.md
- Offline regression matrix
- PacketMaintenance
- LoRa Chat Firmware Requirements
- ReceiverBootTests
- InstalledRadioEvidenceTests
- Source and documentation deletion audit
- _build_handoff
- ExcludedSx1262Experiment
- Revision
- ProfileError
- Sender APPCODE
- LORA_RF_STRESS_SPECIAL.md
- Real-radio verification evidence
- Firmware source map
- sleep.cpp
- lora
- lora/library.json
- time-utils/library.json
- ใช้งาน Codex Goal — LoRa E2E Feature-Based
- Suggested append-only AGENTS.md contract (merge; do not overwrite existing instructions)
- Hardware

## God Nodes (most connected - your core abstractions)
1. `Transport` - 72 edges
2. `Hardware` - 55 edges
3. `SystemConstants` - 46 edges
4. `State` - 45 edges
5. `Gate1Tests` - 45 edges
6. `LoRa` - 40 edges
7. `error()` - 40 edges
8. `make_error()` - 37 edges
9. `ProofRun` - 36 edges
10. `DebugConsoleTests` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Radio SPI and interrupt contract` --references--> `ExcludedSx1262Experiment`  [INFERRED]
  GATEWAY_SSOT.md → include/gateway_ssot.hpp
- `Application and dependency audit` --references--> `LoRa`  [INFERRED]
  docs/refactoring/OFFLINE_LORA.md → src/shared/radio/radio_link.h
- `C. Action` --references--> `LoRa`  [INFERRED]
  docs/refactoring/SOURCE_OWNERSHIP_V2.md → src/shared/radio/radio_link.h
- `SSOT addressed DATA, ACK, and NACK` --references--> `LoRa`  [INFERRED]
  docs/testing/LORA_ACK_NACK.md → src/shared/radio/radio_link.h
- `Scope` --references--> `TrackerConfig`  [INFERRED]
  TRACKER_CONFIG_SSOT.md → include/tracker_config.h

## Import Cycles
- None detected.

## Communities (282 total, 117 thin omitted)

### Community 0 - "pathlib"
Cohesion: 0.06
Nodes (13): bootstrap(), create_temp_dir(), main(), test_capture_journal_marks_buffered_lines_until_a_fresh_readiness_barrier(), TaskRestartTests, I2cRadioConfigTests, RadioDiagnosticsTests, RadioLibHalTests (+5 more)

### Community 1 - "rf_proof.py"
Cohesion: 0.09
Nodes (51): normalize_ihex_region(), application_layout_verified(), authorized_application_pages(), boot_fuses_match(), capture_radio_spi_log(), capture_usb_topology(), check_port_owners(), clean_builds() (+43 more)

### Community 2 - "Storage"
Cohesion: 0.11
Nodes (9): Storage, _first, _raw, _start_block, Storage<T>::clear(), Storage<T>::peek(), Storage<T>::pop(), Storage<T>::push() (+1 more)

### Community 3 - "mvp_board.cpp"
Cohesion: 0.05
Nodes (12): DecodeLoraConfig(), delay(), main(), pump(), state_name(), step(), EepromSpy, reads (+4 more)

### Community 4 - "analyze"
Cohesion: 0.05
Nodes (9): RCATests, analyze(), load(), read(), classify(), compare_snapshots(), delta(), main() (+1 more)

### Community 5 - "mcurses.c"
Cohesion: 0.09
Nodes (38): addch(), addstr(), addstr_P(), attrset(), clear(), clrtobot(), clrtoeol(), curs_set() (+30 more)

### Community 6 - "appcode/arq/sender.cpp"
Cohesion: 0.10
Nodes (42): ArmSession(), CurrentSession(), ExecuteCommand(), FailAdapter(), FeedCommandByte(), FlushStatus(), GetEventContext(), HandleReceive() (+34 more)

### Community 7 - "CaptureTests"
Cohesion: 0.06
Nodes (3): CaptureTests, command(), monotonic()

### Community 8 - "error"
Cohesion: 0.11
Nodes (26): error(), campaign(), progress(), run_one(), Capture, complete(), checked_events(), park_reverse() (+18 more)

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
Nodes (17): ArqSoakPlanTests, fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), confirmed_rf_preflight(), dynamic_attr() (+9 more)

### Community 13 - "generate_lora_config.py"
Cohesion: 0.12
Nodes (13): SourceFingerprintTests, artifacts(), canonical(), digest(), generate(), load_radio_profile(), main(), prepare_build_inputs() (+5 more)

### Community 14 - "check_cpp.py"
Cohesion: 0.06
Nodes (22): capture_host_commands(), check(), complexity_check(), firmware_checks(), main(), record(), resolve_tools(), run() (+14 more)

### Community 15 - "appcode/arq/receiver.cpp"
Cohesion: 0.25
Nodes (19): Source ownership and dependency map, ArmSession(), CurrentSession(), ExecuteCommand(), FailAdapter(), FeedCommandByte(), FlushStatus(), GetEventContext() (+11 more)

### Community 16 - "RadioBringupTests"
Cohesion: 0.10
Nodes (6): RadioBringupTests, acquire(), command(), audit_radio_configuration(), read_radio(), validate_hello_exchange()

### Community 17 - "arq_trial.py"
Cohesion: 0.19
Nodes (13): capture_tracker_diagnostics(), close_updi_without_recovery(), drain_updi_messages(), hello_airtime_budget(), lora_time_on_air_us(), read_reset_state(), tracker_command(), resync_reset_state_once() (+5 more)

### Community 18 - "updi_role_log"
Cohesion: 0.10
Nodes (43): Poll(), ReportBoot(), AcceptData(), ArmRadio(), HandleRadioCommand(), Initialize(), InitializeGpio(), InitializeRoleGpio() (+35 more)

### Community 19 - "validate_live_proof"
Cohesion: 0.15
Nodes (8): matches(), parse_rf_campaign(), radio_startup_matches(), shared_identity_matches(), single_packet_evidence_passed(), validate_live_proof(), validate_symmetric_exchange(), validate_wrong_destination_trials()

### Community 22 - "mvp_stub/Arduino.h"
Cohesion: 0.22
Nodes (4): CPUINT(), digitalReadFast(), digitalWrite(), digitalWriteFast()

### Community 23 - "cli.py"
Cohesion: 0.03
Nodes (37): test_ack_alone_never_counts_as_a_tracker_echo(), test_ack_matching_requires_campaign_sequence_and_type(), test_encodes_supported_utf8_bytes_exactly(), test_parses_firmware_campaign_sequence_and_payload_bytes(), test_rejects_configured_payload_beyond_transport_limit(), test_rejects_invalid_unicode_before_encoding(), test_rejects_malformed_firmware_payload_hex(), test_rejects_out_of_range_sequence_from_firmware_log() (+29 more)

### Community 24 - "Transport"
Cohesion: 0.05
Nodes (34): Transport, armed_, context_, error_, event_context_, frequency_, have_accepted_, kMaxData (+26 more)

### Community 26 - "Gate1Tests"
Cohesion: 0.11
Nodes (3): Gate1Tests, rows(), transaction()

### Community 28 - "load"
Cohesion: 0.06
Nodes (10): ConfigurationTests, Radio915ValidationTests, valid_profile(), write_toml(), RawMvpTests, ReceiverHardwareTests, load(), main() (+2 more)

### Community 29 - "gateway_radio.cpp"
Cohesion: 0.08
Nodes (28): I2cCommandTask, command_, command_length_, InitializeEspCommunication(), StoreI2c16(), Initialize(), Poll(), ReadTemperatureCelsius() (+20 more)

### Community 30 - "ReaderFreeH01SummaryTests"
Cohesion: 0.09
Nodes (6): DirectionalHostTests, ReaderFreeH01SummaryTests, hardware_gate_errors(), main(), open_reader_free_h01_session(), reader_free_rx_idle_summary()

### Community 31 - "._run_capture"
Cohesion: 0.08
Nodes (10): fixture(), add(), LiveProofTests, emit(), start(), write(), symmetric_fixture(), add() (+2 more)

### Community 32 - "Campaign"
Cohesion: 0.08
Nodes (32): Campaign, attempts, campaign_id, destination, sequence, single_packet, source, state (+24 more)

### Community 34 - "ring_buffer.h"
Cohesion: 0.09
Nodes (11): RingBuffer, buffer_, RingBuffer<Capacity>::Read(), RingBuffer<Capacity>::ReadByte(), RingBuffer<Capacity>::Write(), RingBuffer<Capacity>::WriteByte(), RingBuffer<Capacity>::WriteFrame(), first_free_ (+3 more)

### Community 36 - "tracker_radio_codec.cpp"
Cohesion: 0.24
Nodes (16): DecodeConfig(), DecodePacketBoot(), EncodeConfig(), EncodePacketAck(), EncodePacketAdvertise(), EncodePacketBoot(), EncodePacketMaintenance(), EncodePacketMaintenanceAck() (+8 more)

### Community 37 - "ScanResult"
Cohesion: 0.18
Nodes (3): ScanResult, format_text(), result_to_json()

### Community 38 - "sd-storage.h"
Cohesion: 0.21
Nodes (3): Storage<T>::_load_state(), Storage<T>::_save_state(), Storage<T>::setup()

### Community 39 - "EventId"
Cohesion: 0.05
Nodes (41): Component, kApplication, kBoot, kHil, kNvm, Event(), EventId, kAuthenticationStarted (+33 more)

### Community 41 - "ControlInput"
Cohesion: 0.22
Nodes (9): ControlInput, command, digits, last_ms, reading, triggered, value, ssot::ControlInputFeed() (+1 more)

### Community 42 - "reverse_raw_app.cpp"
Cohesion: 0.25
Nodes (13): arq_board, board_ssot_init(), ExecuteCommand(), FeedCommandByte(), Initialize(), IsPayloadCommand(), ParkRadio(), Poll() (+5 more)

### Community 43 - "discover_usb_devices"
Cohesion: 0.13
Nodes (8): _print_result(), discover_usb_devices(), InventoryResult, _normalize_hex(), parse_udev_properties(), _run_command(), start_udev_monitor(), _usb_instance()

### Community 44 - "image_evidence"
Cohesion: 0.12
Nodes (10): wire(), event(), image_evidence(), journal(), StableTransportProofTests, _line(), write(), wrong_destination_journal() (+2 more)

### Community 45 - "DeviceLayout"
Cohesion: 0.12
Nodes (18): DeviceLayout, kAppDataStart, kApplicationEnd, kApplicationImageEnd, kApplicationStart, kBootEnd, kBootSizePages, kBootStart (+10 more)

### Community 47 - "Bus"
Cohesion: 0.08
Nodes (9): Bus, fifo, finish_delay, regs, reset_mode, ticks, TraceBus, sensitivity_writes (+1 more)

### Community 48 - "require"
Cohesion: 0.11
Nodes (4): DetectionIntegrationTests, pio(), runner(), require()

### Community 49 - "TracePort"
Cohesion: 0.09
Nodes (3): instrument(), open_exclusive(), TracePort

### Community 50 - "diagnostics.cpp"
Cohesion: 0.09
Nodes (21): FrameRead, kDiscard, kRadioError, kValid, ReceiveCounters, crc_errors, decode_errors, last_rx_flags (+13 more)

### Community 51 - "string"
Cohesion: 0.05
Nodes (17): arq::DecodeFrame(), arq::EncodeFrame(), arq::IsValidFrame(), AcquireLine(), FlushByte(), OverflowCount(), PendingLineCount(), RecordDiscard() (+9 more)

### Community 52 - "AGENTS.md — AVR128DA28 / LoRa Embedded Engineering"
Cohesion: 0.09
Nodes (21): 10. Logging, measurement, and evidence, 11. Decision and intervention policy, 12. Response contract, 13. Technical references (read when relevant; do not substitute for active SSOT), 1. Mission and current MVP, 2. Operating philosophy, 3. Project truth and protected files, 4. Target architecture (+13 more)

### Community 54 - "upditerm.py"
Cohesion: 0.07
Nodes (8): Console, main(), parse_arguments(), SerialPort, SerialUPDI, Terminal, TransportError, UPDI

### Community 55 - "TrackerConfig"
Cohesion: 0.10
Nodes (18): TrackerConfig, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 57 - "Task"
Cohesion: 0.06
Nodes (18): I2cResetTask, timestamp_ms_, HeartbeatTask, timestamp_ms_, RadioTransactionTask, Task::Task(), TaskScheduler::GetTaskCount(), Task (+10 more)

### Community 58 - "FakeRadio"
Cohesion: 0.09
Nodes (17): FakeRadio, bytes, campaign_id, completion_error, destination, done, incoming, incoming_campaign_id (+9 more)

### Community 59 - "ReceiveTests"
Cohesion: 0.13
Nodes (3): ReceiveTests, wait(), wait()

### Community 60 - "Sender"
Cohesion: 0.05
Nodes (44): Result, kOk, kPending, kProtocolError, kRadioError, kRejected, kTimeoutExhausted, Sender (+36 more)

### Community 61 - "Logger"
Cohesion: 0.31
Nodes (5): Logger, _capacity, _cursor, _raw, _start_block

### Community 62 - "PlatformResult"
Cohesion: 0.16
Nodes (13): PlatformResult, kBusy, kForbidden, kHardwareError, kInvalidArgument, kOk, kOutOfRange, kTimeout (+5 more)

### Community 63 - "receiver_boot.py"
Cohesion: 0.18
Nodes (8): _parse_ihex(), prepare(), read_snapshot(), read_snapshot_command(), require_preserved(), reset_target(), trace_stub(), verify_live_receipt()

### Community 64 - "MvpRoundtripTests"
Cohesion: 0.21
Nodes (3): Board, frames(), MvpRoundtripTests

### Community 65 - "test_application_config.py"
Cohesion: 0.08
Nodes (12): ApplicationConfigTests, ReverseRawTests, audit_raw_configuration(), diagnostic_case(), reverse_exchange(), status(), validate_reverse(), load() (+4 more)

### Community 66 - "dynamic_attr"
Cohesion: 0.13
Nodes (3): dynamic_attr(), FlashSafetyTests, command()

### Community 67 - "require"
Cohesion: 0.09
Nodes (15): DeviceReconnectTests, make_device(), make_probe(), require(), crc8(), FirmwareIdentityTests, ihex_record(), marker() (+7 more)

### Community 68 - "OPERATING CONTRACT — READ ALL BEFORE EDITING"
Cohesion: 0.12
Nodes (15): 0. Target, boundaries, priorities, 10. Mandatory negative and protocol matrix, 11. Acceptance criteria — NOT negotiable, 12. Agentic self-repair loop — persistent, evidence-driven, bounded, 13. First actions — execute in this exact order, 1. Mandatory first phase: read-only inventory and graph analysis, 2. Reference repo: behavior parity without copying defects, 3. IMPORTANT RADIO FACT: SX127x `setNodeAddress` (+7 more)

### Community 69 - "Config"
Cohesion: 0.11
Nodes (18): Config, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 71 - "Tracker Hardware SSOT — LoRa Tracker RFM"
Cohesion: 0.22
Nodes (9): 1. Board identity and components, 2. AVR128DA28 pin and net SSOT, 3. Power and startup contract, 4. Minimal firmware implementation contract, 5. Acceptance criteria / physical evidence, 6. Firmware configuration, Exact LoRa RFM95W signal map, Sources (+1 more)

### Community 72 - "Sd2Card"
Cohesion: 0.20
Nodes (4): get_data_and_log_partitions(), read_line(), Sd2Card, main()

### Community 73 - "EventQueue"
Cohesion: 0.11
Nodes (15): Event, campaign_id, error, name, sequence, time_ms, type, EventQueue (+7 more)

### Community 74 - "commands.cpp"
Cohesion: 0.08
Nodes (26): Command, budget, kind, payload, payload_length, session, stride, CommandInput (+18 more)

### Community 75 - "Port"
Cohesion: 0.21
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 77 - "LoRa"
Cohesion: 0.12
Nodes (12): ReportRegisters(), LoRa, _active, _hardware, _initialized, _last_rssi, _module, _my_addr (+4 more)

### Community 78 - "make_error"
Cohesion: 0.04
Nodes (9): test_dry_run_creates_empty_event_log_and_disables_transmission(), test_rf_authorization_still_blocks_when_inventory_is_unresolved(), _help_panel(), InteractiveConsole, make_error(), ChatSession, _utc_now(), BenchTransport (+1 more)

### Community 80 - "915 MHz LoRa bench procedure"
Cohesion: 0.29
Nodes (6): 915 MHz LoRa bench procedure, App-only programming after exact write approval, Hardware results, Refactor verification, RF conditions and acceptance, Verified candidates

### Community 81 - "boot_analysis.py"
Cohesion: 0.29
Nodes (3): BootAnalysisTests, analyze(), main()

### Community 82 - "Receiver"
Cohesion: 0.11
Nodes (18): Receiver, accepted, armed, deliveries, duplicates, expected, last_sequence, session (+10 more)

### Community 83 - "main"
Cohesion: 0.07
Nodes (10): test_current_profile_exposes_fixed_payload_and_unresolved_rf_inventory(), test_profile_rejects_wrong_numeric_types(), test_run_directory_is_created_once_by_the_transport(), ConsoleRuntime, _create_run_directory(), main(), BenchProfile, load_bench_profile() (+2 more)

### Community 84 - "Json"
Cohesion: 0.14
Nodes (13): _fault_bundle(), _run_replay(), test_cancel_fault_is_not_passed_by_a_normal_ack_exchange(), test_cancel_is_passed_only_after_both_radios_park_and_ports_release(), test_cancel_requires_park_after_the_cancel_request(), test_controlled_nack_retries_the_same_session_and_sequence(), test_crc_rejection_uses_timeout_recovery_without_application_nack(), test_duplicate_is_not_passed_without_single_delivery_evidence() (+5 more)

### Community 85 - "installed_rf.py"
Cohesion: 0.05
Nodes (14): test_capture_metrics_preserve_radio_errors_irq_and_missing_rf_metrics(), test_capture_phase_distinguishes_reopened_buffer_from_post_ready_events(), test_planned_transaction_failure_is_not_counted_as_background(), test_unplanned_transaction_failure_is_retained_in_run_summary(), Capture, capture_diagnostics(), capture_event_phase(), gateway_finished() (+6 more)

### Community 86 - "ExcludedSx1262Experiment"
Cohesion: 0.20
Nodes (10): ExcludedSx1262Experiment, BUSY_PIN, DIO1_PIN, ERROR_RETRY_DELAY_MS, NSS_PIN, PACKET_BYTES, PACKET_COUNT, PACKET_GAP_MS (+2 more)

### Community 87 - "stdint"
Cohesion: 0.04
Nodes (11): Memory, I2C_MAILBOX_BYTES, SHARED_RINGBUF_BYTES, InitializeRadio(), ReadRadioRegister(), PrepareTrackerForRadioOnly(), AdditionOverflows(), IsRangeWithin() (+3 more)

### Community 90 - "Controller"
Cohesion: 0.13
Nodes (12): Controller, last_led1_toggle_, last_tx_toggle_, led1_interval_ms_, led1_on_, led1_pin_, led2_pin_, led_off_level_ (+4 more)

### Community 91 - "System"
Cohesion: 0.40
Nodes (5): System, ENABLE_ESPCOMM, ENABLE_LORA_RX, ENABLE_WATCHDOG, WDT_TIMEOUT_PERIOD

### Community 94 - "stub/RadioLib.h"
Cohesion: 0.04
Nodes (4): beginTransaction(), SPIClass, SPISettings, beginTransaction()

### Community 95 - "Any"
Cohesion: 0.28
Nodes (3): _prepare_run(), radio_configuration(), real_rf_blockers()

### Community 96 - "complete_campaign_logs"
Cohesion: 0.38
Nodes (4): complete_campaign_logs(), packet_event(), payload_event(), RfEvidenceTests

### Community 97 - "debug_protocol_ack_nack.py"
Cohesion: 0.05
Nodes (8): assess_control_fault(), assess_exhaustion(), Console, discover_ports(), firmware_role(), hardware_output(), main(), Session

### Community 98 - "ErrataDiagnosticsTests"
Cohesion: 0.13
Nodes (5): ErrataDiagnosticsTests, decode_snapshot(), interpret_rx(), link_budget(), main()

### Community 99 - "Receiver APPCODE"
Cohesion: 0.67
Nodes (3): Hardware and power, Receiver APPCODE, Source path

### Community 101 - "raw_mvp_stub/Arduino.h"
Cohesion: 0.11
Nodes (7): random(), randomSeed(), begin(), digitalWrite(), end(), ltoa(), push_back()

### Community 103 - "load_config"
Cohesion: 0.25
Nodes (4): load_config(), _validate_installed_pair(), _validate_profiles(), _validate_runner_settings()

### Community 105 - "Pins"
Cohesion: 0.14
Nodes (14): Pins, ANALOG_IN_0, ANALOG_IN_1, DEBUG_RX, DEBUG_TX, HOST_INT, LED1, LED2 (+6 more)

### Community 106 - "mvp_app.cpp"
Cohesion: 0.37
Nodes (12): debug_init(), debug_write(), debug_write_float(), debug_write_hex(), debug_write_int(), Initialize(), Poll(), RecordStartupStage() (+4 more)

### Community 107 - "Pair"
Cohesion: 0.15
Nodes (12): Application, applied, reject, Pair, a, aa, b, bb (+4 more)

### Community 109 - "PacketAdvertise"
Cohesion: 0.40
Nodes (4): DecodePacketAdvertise(), PacketAdvertise, seq, type

### Community 110 - "ssot_codec.cpp"
Cohesion: 0.18
Nodes (15): DecodePayloadFields(), EncodeControlPayload(), ssot::AckMatches(), ssot::DecodeFrame(), ssot::DecodePayload(), ssot::EncodeAckFrame(), ssot::EncodeAckPayload(), ssot::EncodeDataFrame() (+7 more)

### Community 111 - "ReportEntry"
Cohesion: 0.13
Nodes (22): ReportEntry, day, hour, latitude, longitude, minute, month, quality (+14 more)

### Community 112 - "SD.h"
Cohesion: 0.25
Nodes (8): mbr_t, mbrSig0, mbrSig1, part, SdPartition, firstSector, totalSectors, type

### Community 113 - "Frame"
Cohesion: 0.22
Nodes (9): Frame, dst, length, payload, reason, sequence, session, src (+1 more)

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
Cohesion: 0.17
Nodes (22): controlled_cpu_reset(), firmware_identity_from_events(), gpr_roundtrip_succeeded(), halted_gpr_roundtrip(), mailbox_snapshot(), main(), _parse_block(), part_from_signature() (+14 more)

### Community 120 - "avr128da28_device.h"
Cohesion: 0.15
Nodes (12): IsAppCodeRange(), PORT_struct, PORT_t, SPI_struct, SPI_t, TWI_struct, TWI_t, TwiHold (+4 more)

### Community 121 - "State"
Cohesion: 0.22
Nodes (8): State, kComplete, kFailed, kRetryPending, kRxWait, kTxData, kTxResponse, kWaitResponse

### Community 122 - "test_lora_chat_session.py"
Cohesion: 0.11
Nodes (15): _event(), _session(), test_ack_matching_deduplicates_replayed_event_counts(), test_ack_without_real_echo_is_not_round_trip_success(), test_chat_settings_allow_zero_manual_retries(), test_chat_settings_enforce_memory_and_refresh_caps(), test_chat_settings_reject_unknown_keys_and_invalid_limits(), test_message_queue_keeps_one_active_transaction_and_is_bounded() (+7 more)

### Community 123 - "receiver/appcode/reliable.cpp"
Cohesion: 0.14
Nodes (14): AcceptData(), ArmRadio(), HandleRadioCommand(), Initialize(), InitializeGpio(), InitializeRoleGpio(), RecordTransportEvent(), updi_role_log_dropped() (+6 more)

### Community 125 - "metrics.py"
Cohesion: 0.24
Nodes (3): main(), calculate_metrics(), _percentile()

### Community 126 - "reliable_transport_test.cpp"
Cohesion: 0.36
Nodes (9): count_transition(), deliver(), dropped(), finish_reply(), loss_scenario(), main(), start_data(), stress_round_trips() (+1 more)

### Community 128 - "production_bench.py"
Cohesion: 0.10
Nodes (11): approve_writes(), BenchBlockedError, BenchFailedError, build(), inspect_image(), phy_matches(), power_matches(), publish_receipt() (+3 more)

### Community 130 - "Frame"
Cohesion: 0.33
Nodes (6): Frame, campaign_id, destination, sequence, source, type

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

### Community 135 - "EventStats"
Cohesion: 0.18
Nodes (11): EventStats, ack_accepted, ack_tx, data_tx, destination_discards, duplicates, failures, nack_received (+3 more)

### Community 137 - "Fixed settings and checks"
Cohesion: 0.40
Nodes (4): Fixed settings and checks, Runtime settings, Scope, Tracker Configuration SSOT

### Community 138 - "SdFile"
Cohesion: 0.20
Nodes (6): open_file_in_root(), SdFile, data_, length_, position_, SdVolume

### Community 140 - "detect_devices.py"
Cohesion: 0.20
Nodes (11): build_parser(), _load_registry(), main(), _probe_device(), _run_self_test(), SafetyArgumentParser, _scan(), _watch() (+3 more)

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
Cohesion: 0.17
Nodes (4): assess(), response(), _status(), verify_hashes()

### Community 151 - "C++ Refactoring Results"
Cohesion: 0.29
Nodes (7): A — Action, C++ Refactoring Results, Current follow-up verification — 2026-11-19, R — Result, S — Situation, T — Task, Trade-offs and limits

### Community 152 - "Gateway-to-Receiver SF7 Hello World"
Cohesion: 0.25
Nodes (7): Current result — Receiver installed, normal startup unresolved, Gateway-to-Receiver SF7 Hello World, No-meter read-only hardware verified; Receiver write wiring unconfirmed, Receiver boot incompatibility, Remaining physical prerequisites, Single-packet behavior and identities, Verified software result

### Community 154 - "AdcTemp"
Cohesion: 0.17
Nodes (12): AdcTemp, ADC_MAX_COUNTS, CTRLA_ENABLE_12BIT, FIXED_POINT_SHIFT, INIT_DELAY_SETTING, KELVIN_TO_CELSIUS, MUX_TEMP_CHANNEL, PRESCALER_SETTING (+4 more)

### Community 155 - "adc.cpp"
Cohesion: 0.43
Nodes (5): InitializeAdc(), ReadBatteryAdc(), ReadSample(), ReadTemperatureAdc(), WaitForConversion()

### Community 157 - "LoRa ACK/NACK analysis and verification"
Cohesion: 0.20
Nodes (10): Bench ARQ protocol, Documentation audit, Historical baseline evidence, Historical hardware trial requirements and result, Installed SRAM-only pair, LoRa ACK/NACK analysis and verification, Production bench repair report, Runbook (+2 more)

### Community 158 - "Offline LoRa firmware refactor"
Cohesion: 0.33
Nodes (6): Application and dependency audit, Firmware matrix, Historical BOOT and deployment status, Offline LoRa firmware refactor, Verification, Wire and host evidence

### Community 162 - "AVR128DA28 LoRa Board Pin Audit"
Cohesion: 0.29
Nodes (7): AVR128DA28 LoRa Board Pin Audit, AVR128DA28 package pins, Evidence basis, Gateway LoRa daughterboard, Radio profile and serial identity, Read the table, Tracker

### Community 164 - "updi_probe.py"
Cohesion: 0.20
Nodes (9): firmware_fingerprint_evidence(), identify_mcu(), _is_access_error(), _port_busy(), probe_firmware_identity(), probe_target_sib(), read_firmware_flash(), _require_safe() (+1 more)

### Community 166 - "LossMetrics"
Cohesion: 0.29
Nodes (7): LossMetrics, ack_tx, attempts, duplicates, nack_tx, retries, timeouts

### Community 169 - "runner.py"
Cohesion: 0.16
Nodes (7): generate_payload(), split_payload(), _add_direction_cases(), _append_case(), build_case_plan(), add(), CaseSpec

### Community 170 - "PacketMaintenanceAck"
Cohesion: 0.40
Nodes (4): DecodePacketMaintenanceAck(), PacketMaintenanceAck, response, type

### Community 173 - "role_detector.py"
Cohesion: 0.11
Nodes (8): DetectedDevice, USBDevice, classify_devices(), diff_device_presence(), _identity_role(), _probe_for(), _registry_hint(), _registry_record()

### Community 174 - "protocol_adapter.py"
Cohesion: 0.21
Nodes (6): _assess_cancellation(), assess_case(), _assess_sequence_rollover(), FirmwareEvent, parse_event_row(), _result()

### Community 178 - "RawStorage"
Cohesion: 0.42
Nodes (4): ui64toa(), RawStorage, _cached_block, _cached_pos

### Community 179 - "spec_protocol.py"
Cohesion: 0.23
Nodes (6): _replay(), test_nonzero_radio_status_code_is_reported_as_failure(), test_replay_pass_requires_matching_two_sided_payload_and_ack(), test_replay_rejects_payload_mismatch(), test_replay_without_receiver_payload_bytes_is_unverified(), _write_replay_bundle()

### Community 180 - "AVR128DA28 LoRa firmware"
Cohesion: 0.33
Nodes (6): Application configuration, AVR128DA28 LoRa firmware, Build, Host tests, Preserved boundaries, Static analysis and formatting

### Community 186 - "Tasks"
Cohesion: 0.22
Nodes (9): Tasks, ENABLE_HEARTBEAT_TASK, HEARTBEAT_NAME, HEARTBEAT_OFF_MS, HEARTBEAT_ON_MS, HEARTBEAT_PERIOD_MS, I2C_RESET_SETTLE_MS, LED1_TOGGLE_INTERVAL_MS (+1 more)

### Community 190 - "ResponseFault"
Cohesion: 0.25
Nodes (6): ResponseFault, kCampaign, kDrop, kDuplicate, kNone, kSequence

### Community 194 - "Comm"
Cohesion: 0.25
Nodes (8): Comm, AIR_CONFIG_NODE_ADDR, DEBUG_BAUD_RATE, ENABLE_I2C_WIRE, GATEWAY_ANYCAST_ADDR, GATEWAY_DEFAULT_ADDR, I2C_ADDRESS_BASE, I2C_ADDRESS_STRAP_SHIFT

### Community 196 - "firmware_identity.py"
Cohesion: 0.20
Nodes (8): FirmwareIdentity, crc8(), FingerprintResult, IdentityParseResult, match_flash_fingerprint(), parse_identity_stream(), _valid_build(), _valid_timestamp()

### Community 199 - "spec_payload.py"
Cohesion: 0.23
Nodes (6): _run_smoke_plan(), test_full_fifty_two_letter_alphabet_is_split_without_byte_loss(), test_random_ascii_changes_with_seed_and_boundary_patterns_stay_frame_bounded(), test_seed_reproduces_bounded_payloads_and_both_direction_character_coverage(), test_smoke_fault_cases_are_ten_total_and_cover_each_direction(), test_stress_plan_contains_sequence_255_to_zero_rollover_case()

### Community 200 - "spec_runner.py"
Cohesion: 0.18
Nodes (6): test_default_cli_writes_a_zero_transmission_dry_run(), test_real_rf_requires_explicit_profile_and_saved_readback(), test_stress_config_rejects_unknown_settings(), test_torture_config_must_keep_one_thousand_transaction_minimum(), test_torture_plan_has_at_least_one_thousand_cases_and_a_bounded_runtime(), test_torture_profile_requires_long_duration_opt_in()

### Community 201 - "application_bounds_for_environment"
Cohesion: 0.15
Nodes (12): DirectionalTests, RadioOnlyTests, TargetLayoutTests, application_bounds_for_environment(), build_flag_defines(), _config_int(), effective_project_sections(), radio_profile_compile_flags() (+4 more)

### Community 204 - "core_test.cpp"
Cohesion: 0.38
Nodes (12): absolute_deadline(), ack_matrix(), codec(), control(), data(), fault_harness(), fresh(), main() (+4 more)

### Community 206 - "install_cpp_quality_tools.sh"
Cohesion: 0.50
Nodes (3): find_tool(), PATH, install_cpp_quality_tools.sh script

### Community 207 - "main"
Cohesion: 0.13
Nodes (7): build_parser(), _display_run(), main(), RunOptions, RunPlan, _validated_options(), _write_run_bundle()

### Community 212 - "test_arq.py"
Cohesion: 0.16
Nodes (4): ArqTests, arq_artifacts(), load_arq(), validate_arq()

### Community 214 - "ihex"
Cohesion: 0.16
Nodes (3): ApplicationPageWriteTests, command(), ihex()

### Community 215 - "replay_bundle"
Cohesion: 0.17
Nodes (5): load_event_journal(), _output_directory(), _read_case_journal(), replay_bundle(), _write_replay_bundle()

### Community 218 - "load_package"
Cohesion: 0.24
Nodes (6): boot(), BootPackageTests, recording_command(), install(), load_package(), sha()

### Community 221 - "PacketAck"
Cohesion: 0.40
Nodes (4): DecodePacketAck(), PacketAck, seq, type

### Community 223 - "PacketReport"
Cohesion: 0.13
Nodes (13): DecodePacketReport(), DecodePacketReportWithAck(), DecodeReportEntry(), LoadSigned16(), LoadSigned32(), PacketReport, report, seq (+5 more)

### Community 225 - "Final LoRa firmware architecture"
Cohesion: 0.40
Nodes (5): Board roles and source ownership, Build and safety boundary, Final LoRa firmware architecture, Protocol boundaries, Status

### Community 226 - "RESULTS.md"
Cohesion: 0.15
Nodes (9): C++ Refactoring Baseline, Parent-revision measurements, Production and analysis scope, Repository snapshot, Toolchain and limits, Source ownership baseline, Shared firmware modules, Adding and checking libraries (+1 more)

### Community 227 - "Offline regression matrix"
Cohesion: 0.40
Nodes (5): Firmware matrix, Hardware is a separate gate, Host, quality, and fixture checks, Linked image checks, Offline regression matrix

### Community 228 - "PacketMaintenance"
Cohesion: 0.40
Nodes (4): DecodePacketMaintenance(), PacketMaintenance, command, type

### Community 229 - "LoRa Chat Firmware Requirements"
Cohesion: 0.50
Nodes (3): Firmware work required for arbitrary round trips, Installed behavior, LoRa Chat Firmware Requirements

### Community 230 - "ReceiverBootTests"
Cohesion: 0.17
Nodes (3): ReceiverBootTests, page_write_command(), patch_page0()

### Community 233 - "Source and documentation deletion audit"
Cohesion: 0.50
Nodes (4): Current continuation, Earlier source-ownership migration, Markdown inventory and references, Source and documentation deletion audit

### Community 236 - "_build_handoff"
Cohesion: 0.16
Nodes (3): CompiledHandoffTests, build_fixture(), _build_handoff()

### Community 237 - "ExcludedSx1262Experiment"
Cohesion: 0.18
Nodes (11): 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates, Gateway Hardware SSOT — Rudolph Gateway, H1 (10-pin; only pins 1–5 used in the source schematic) (+3 more)

### Community 238 - "Revision"
Cohesion: 0.50
Nodes (4): Revision, major, minor, raw_revision_id

### Community 244 - "Sender APPCODE"
Cohesion: 0.67
Nodes (3): Builds and hardware, Sender APPCODE, Source path

### Community 299 - "sleep.cpp"
Cohesion: 0.12
Nodes (11): SetUnixTime(), SleepFor(), SleepState, force_wakeup, is_sleeping, last_rtc_ticks, unix_time, PowerSavingTaskScheduler (+3 more)

### Community 313 - "lora/library.json"
Cohesion: 0.25
Nodes (8): jgromes/RadioLib, build, includeDir, srcDir, dependencies, jgromes/RadioLib@7.1.2, name, version

### Community 315 - "time-utils/library.json"
Cohesion: 0.25
Nodes (8): paulstoffregen/Time, build, includeDir, srcDir, dependencies, paulstoffregen/Time@^1.6.1, name, version

### Community 341 - "ใช้งาน Codex Goal — LoRa E2E Feature-Based"
Cohesion: 0.33
Nodes (6): ค่าคลื่นวิทยุที่ตั้งไว้, ความต่างระหว่าง Goal กับ config, จุดที่ต้องพิสูจน์, เริ่มต้นใช้งานเฟิร์มแวร์ LoRa AVR128DA28, แหล่งอ้างอิง, ใช้งาน Codex Goal — LoRa E2E Feature-Based

### Community 357 - "Hardware"
Cohesion: 0.04
Nodes (4): DebugConsoleTests, assess_probe(), Hardware, parked()

## Knowledge Gaps
- **610 isolated node(s):** `day`, `fixquality`, `_gga_received`, `hour`, `latitude` (+605 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1984 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **117 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Transport` connect `Transport` to `.EmitEvent`, `EventQueue`, `Pair`, `Result`, `stdint`, `State`, `reliable_transport_test.cpp`, `ResponseFault`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **What connects `day`, `fixquality`, `_gga_received` to the rest of the system?**
  _610 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.05520941502249913 - nodes in this community are weakly interconnected._
- **Why does `error()` connect `error` to `pathlib`, `debug_protocol_ack_nack.py`, `rf_proof.py`, `analyze`, `Hardware`, `ArqSoakPlanTests`, `make_error`, `main`, `arq_trial.py`, `main`, `upditerm.py`, `ReceiveTests`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Should `rf_proof.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08612612612612612 - nodes in this community are weakly interconnected._
- **Why does `AdcTemp` connect `AdcTemp` to `stdint`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Should `Storage` be split into smaller, more focused modules?**
  _Cohesion score 0.1067193675889328 - nodes in this community are weakly interconnected._