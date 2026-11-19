# Graph Report - SENIOR_PROJECT_RCA  (2026-11-19)

## Corpus Check
- 298 files · ~170,355 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 25 file(s) not represented in the graph (top: (none) 10, .toml 6, .css 4)

## Summary
- 3612 nodes · 7011 edges · 270 communities (152 shown, 118 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 452 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5e8701b8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
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
- test_arq.py
- validate_repo_isolation.py
- appcode/arq/receiver.cpp
- RadioBringupTests
- arq_trial.py
- updi_role_log
- rf_proof.py
- Json
- Transport
- Gate1Tests
- RepositoryIsolationTests
- load
- gateway_radio.cpp
- ReaderFreeH01SummaryTests
- ._run_capture
- Campaign
- ring_buffer.h
- Logger
- tracker_radio_codec.cpp
- detect_devices.py
- BenchStatus
- EventId
- SX1276
- ScanResult
- reverse_raw_app.cpp
- application_config.h
- image_evidence
- DeviceLayout
- Bus
- require
- TracePort
- directional_test.cpp
- diagnostics.cpp
- AGENTS.md — AVR128DA28 / LoRa Embedded Engineering
- symmetric_fixture
- upditerm.py
- TrackerConfig
- Task
- FakeRadio
- ReceiveTests
- Sender
- DebugConsoleTests
- PlatformResult
- ihex
- MvpRoundtripTests
- arq_trial.py
- HardwareGateTests
- require
- OPERATING CONTRACT — READ ALL BEFORE EDITING
- Config
- .EmitEvent
- Tracker Hardware SSOT — LoRa Tracker RFM
- C++ Refactoring Results
- EventQueue
- commands.cpp
- Port
- receiver_boot.py
- LoRa
- role_detector.py
- 915 MHz LoRa bench procedure
- subprocess
- Receiver
- generate_lora_config.py
- SenderState
- firmware_identity.py
- application_bounds_for_environment
- gateway_ssot.hpp
- Controller
- string
- ReverseRawTests
- gateway_i2c_test.cpp
- Session
- ErrataDiagnosticsTests
- PIN_MAPPING_AUDIT.md
- Json
- updi_probe.py
- EventContext
- Pins
- mvp_app.cpp
- Pair
- RawStorage
- ssot_codec.cpp
- ReportEntry
- stddef
- Result
- tracker_config.h
- State
- gate1_live.py
- avr128da28_device.h
- State
- AdcTemp
- sender/appcode/reliable.cpp
- SPIClass
- reliable_transport_test.cpp
- ReliableTransportTests
- Sd2Card
- BuildEnvironment
- TraceBus
- PacketBoot
- LoRa source ownership V2
- ErrorCode
- ProvisioningResult
- EventStats
- StableLoraSafetyTests
- Fixed settings and checks
- SdFile
- TaskRestartTests
- load_package
- ReceiverBootTests
- validate_live_proof
- Module
- raw_mvp_stub/Arduino.h
- Connect to a virtual UART on an AVR via UPDI
- check_cpp.sh
- assess
- link_budget
- Gateway-to-Receiver SF7 Hello World
- TaskScheduler
- RawMvpTests
- .test_runner_uses_receiver_ready_then_one_gateway_start
- LoRa ACK/NACK analysis and verification
- Offline LoRa firmware refactor
- AVR128DA28 LoRa Board Pin Audit
- PacketAck
- soak_campaign
- LossMetrics
- discover_ports
- RestartTask
- PacketMaintenanceAck
- SenderStableTransportTests
- I2cResetTask
- tracker_radio_packets.h
- HeartbeatTask
- normalize_ihex_region
- .test_rf_enabled_upload_does_not_require_rf_authorization
- AVR128DA28 LoRa firmware
- verify_hashes
- GatewayI2cTests
- avr128da28_memory_layout.h
- LORA_ACK_NACK.md
- FlashSafetyTests
- main
- RadioDiagnosticsTests
- RadioLibHalTests
- PacketReport
- MonitorConsole
- CppInterfaceTests
- ExcludedSx1262Experiment
- core_test.cpp
- SsotProtocolTests
- install_cpp_quality_tools.sh
- parse_raw_mvp_logs
- Revision
- trace_stub
- mvp_stub/Arduino.h
- Task
- _build_handoff
- I2cRadioConfigTests
- Tasks
- effective_project_sections
- PacketReportWithAck
- SingleFirmwareEntryTests
- Final LoRa firmware architecture
- C++ Refactoring Baseline
- Offline regression matrix
- ReceiveCounters
- shared/README.md
- stub/SPI.h
- RfTestContinuationTests
- ExcludedSx1262Experiment
- sleep.cpp
- lora
- lora/library.json
- time-utils/library.json
- receiver/appcode/reliable.cpp
- ใช้งาน Codex Goal — LoRa E2E Feature-Based
- Suggested append-only AGENTS.md contract (merge; do not overwrite existing instructions)
- Hardware

## God Nodes (most connected - your core abstractions)
1. `Transport` - 64 edges
2. `SystemConstants` - 46 edges
3. `State` - 45 edges
4. `Gate1Tests` - 45 edges
5. `LoRa` - 36 edges
6. `Hardware` - 36 edges
7. `HardwareGateTests` - 36 edges
8. `analyze()` - 35 edges
9. `RCATests` - 34 edges
10. `Sender` - 33 edges

## Surprising Connections (you probably didn't know these)
- `C. Action` --references--> `LoRa`  [INFERRED]
  docs/refactoring/SOURCE_OWNERSHIP_V2.md → src/shared/radio/radio_link.h
- `SSOT addressed DATA, ACK, and NACK` --references--> `LoRa`  [INFERRED]
  docs/testing/LORA_ACK_NACK.md → src/shared/radio/radio_link.h
- `Radio SPI and interrupt contract` --references--> `ExcludedSx1262Experiment`  [INFERRED]
  GATEWAY_SSOT.md → include/gateway_ssot.hpp
- `Application and dependency audit` --references--> `LoRa`  [INFERRED]
  docs/refactoring/OFFLINE_LORA.md → src/shared/radio/radio_link.h
- `Scope` --references--> `TrackerConfig`  [INFERRED]
  TRACKER_CONFIG_SSOT.md → include/tracker_config.h

## Import Cycles
- None detected.

## Communities (270 total, 118 thin omitted)

### Community 1 - "rf_proof.py"
Cohesion: 0.16
Nodes (35): application_layout_verified(), authorized_application_pages(), boot_fuses_match(), capture_usb_topology(), check_port_owners(), clean_builds(), firmware_measurement(), host_tests() (+27 more)

### Community 2 - "Storage"
Cohesion: 0.09
Nodes (11): Storage, _first, _raw, _start_block, Storage<T>::clear(), Storage<T>::_load_state(), Storage<T>::peek(), Storage<T>::pop() (+3 more)

### Community 3 - "mvp_board.cpp"
Cohesion: 0.09
Nodes (5): delay(), main(), pump(), state_name(), step()

### Community 4 - "analyze"
Cohesion: 0.05
Nodes (9): RCATests, analyze(), load(), read(), classify(), compare_snapshots(), delta(), main() (+1 more)

### Community 5 - "mcurses.c"
Cohesion: 0.09
Nodes (38): addch(), addstr(), addstr_P(), attrset(), clear(), clrtobot(), clrtoeol(), curs_set() (+30 more)

### Community 6 - "appcode/arq/sender.cpp"
Cohesion: 0.31
Nodes (18): ArmSession(), CurrentSession(), ExecuteCommand(), FailAdapter(), FeedCommandByte(), FlushStatus(), GetEventContext(), HandleReceive() (+10 more)

### Community 7 - "CaptureTests"
Cohesion: 0.07
Nodes (3): CaptureTests, command(), monotonic()

### Community 8 - "error"
Cohesion: 0.16
Nodes (17): error(), audit_radio_configuration(), Capture, complete(), park_reverse(), prepare(), radio_only_bringup(), read_radio() (+9 more)

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
Cohesion: 0.11
Nodes (9): ArqSoakPlanTests, fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), confirmed_rf_preflight(), dynamic_attr() (+1 more)

### Community 13 - "test_arq.py"
Cohesion: 0.07
Nodes (17): valid_profile(), write_toml(), SourceFingerprintTests, arq_artifacts(), load_arq(), validate_arq(), artifacts(), canonical() (+9 more)

### Community 14 - "validate_repo_isolation.py"
Cohesion: 0.25
Nodes (11): _check_config(), _check_symlink(), _inside(), _items(), _label(), _local_dependency(), main(), _resolved() (+3 more)

### Community 15 - "appcode/arq/receiver.cpp"
Cohesion: 0.32
Nodes (17): ArmSession(), CurrentSession(), ExecuteCommand(), FailAdapter(), FeedCommandByte(), FlushStatus(), GetEventContext(), HandleReceive() (+9 more)

### Community 16 - "RadioBringupTests"
Cohesion: 0.09
Nodes (5): DirectionalHostTests, RadioBringupTests, acquire(), command(), validate_hello_exchange()

### Community 17 - "arq_trial.py"
Cohesion: 0.18
Nodes (14): build_soak_plan(), capture_tracker_diagnostics(), close_updi_without_recovery(), drain_updi_messages(), hello_airtime_budget(), lora_time_on_air_us(), read_reset_state(), tracker_command() (+6 more)

### Community 18 - "updi_role_log"
Cohesion: 0.18
Nodes (22): InitializeRadio(), FlushEvent(), ReportConfig(), ReportIdentity(), ReportPhy(), ReportRadioProfile(), ReportRadioStatus(), Poll() (+14 more)

### Community 19 - "rf_proof.py"
Cohesion: 0.08
Nodes (19): capture_radio_spi_log(), parse_radio_spi_log(), parse_rf_campaign(), radio_startup_matches(), run_mvp_acceptance(), run_stable_ack_rf_test(), command(), record() (+11 more)

### Community 23 - "Json"
Cohesion: 0.13
Nodes (12): ArqTests, campaign(), progress(), run_one(), checked_events(), parse_event(), reader_free_h01_summary(), frame_seen() (+4 more)

### Community 24 - "Transport"
Cohesion: 0.05
Nodes (30): Transport, armed_, context_, error_, event_context_, frequency_, have_accepted_, kMaxData (+22 more)

### Community 26 - "Gate1Tests"
Cohesion: 0.13
Nodes (3): Gate1Tests, rows(), transaction()

### Community 28 - "load"
Cohesion: 0.08
Nodes (8): ConfigurationTests, Radio915ValidationTests, ReceiverHardwareTests, checked_cpp(), load(), main(), unique_object(), validate()

### Community 29 - "gateway_radio.cpp"
Cohesion: 0.07
Nodes (16): I2cCommandTask, command_, command_length_, InitializeEspCommunication(), StoreI2c16(), Initialize(), Poll(), ReadTemperatureCelsius() (+8 more)

### Community 30 - "ReaderFreeH01SummaryTests"
Cohesion: 0.12
Nodes (4): ReaderFreeH01SummaryTests, main(), open_reader_free_h01_session(), reader_free_rx_idle_summary()

### Community 31 - "._run_capture"
Cohesion: 0.12
Nodes (7): fixture(), add(), LiveProofTests, emit(), start(), write(), upload_evidence_matches()

### Community 32 - "Campaign"
Cohesion: 0.08
Nodes (32): Campaign, attempts, campaign_id, destination, sequence, single_packet, source, state (+24 more)

### Community 34 - "ring_buffer.h"
Cohesion: 0.09
Nodes (11): RingBuffer, buffer_, RingBuffer<Capacity>::Read(), RingBuffer<Capacity>::ReadByte(), RingBuffer<Capacity>::Write(), RingBuffer<Capacity>::WriteByte(), RingBuffer<Capacity>::WriteFrame(), first_free_ (+3 more)

### Community 35 - "Logger"
Cohesion: 0.31
Nodes (5): Logger, _capacity, _cursor, _raw, _start_block

### Community 36 - "tracker_radio_codec.cpp"
Cohesion: 0.19
Nodes (20): DecodeConfig(), DecodePacketBoot(), DecodePacketReport(), DecodeReportEntry(), EncodeConfig(), EncodePacketAck(), EncodePacketAdvertise(), EncodePacketBoot() (+12 more)

### Community 37 - "detect_devices.py"
Cohesion: 0.12
Nodes (14): build_parser(), _load_registry(), main(), _print_result(), _probe_device(), _run_self_test(), SafetyArgumentParser, _scan() (+6 more)

### Community 38 - "BenchStatus"
Cohesion: 0.12
Nodes (17): BenchStatus, attempted, completed, control_rejects, crc_errors, decode_errors, deliveries, duplicates (+9 more)

### Community 39 - "EventId"
Cohesion: 0.05
Nodes (41): Component, kApplication, kBoot, kHil, kNvm, Event(), EventId, kAuthenticationStarted (+33 more)

### Community 41 - "ScanResult"
Cohesion: 0.13
Nodes (3): DetectedDevice, ScanResult, result_to_json()

### Community 42 - "reverse_raw_app.cpp"
Cohesion: 0.28
Nodes (12): ExecuteCommand(), FeedCommandByte(), IsPayloadCommand(), ParkRadio(), Poll(), ReadStableCounter(), RecordConfiguration(), RecordEvent() (+4 more)

### Community 43 - "application_config.h"
Cohesion: 0.09
Nodes (15): Frame, campaign_id, destination, sequence, source, type, ControlInput, command (+7 more)

### Community 44 - "image_evidence"
Cohesion: 0.19
Nodes (7): event(), image_evidence(), journal(), StableTransportProofTests, wrong_destination_journal(), assess(), validate_stable_transport()

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
Cohesion: 0.17
Nodes (13): FrameRead, kDiscard, kRadioError, kValid, drain_status(), main(), send_command(), QueuedLogLine() (+5 more)

### Community 51 - "diagnostics.cpp"
Cohesion: 0.16
Nodes (11): AcquireLine(), FlushByte(), OverflowCount(), PendingLineCount(), RecordDiscard(), RecordEvent(), RecordFrame(), main() (+3 more)

### Community 52 - "AGENTS.md — AVR128DA28 / LoRa Embedded Engineering"
Cohesion: 0.09
Nodes (21): 10. Logging, measurement, and evidence, 11. Decision and intervention policy, 12. Response contract, 13. Technical references (read when relevant; do not substitute for active SSOT), 1. Mission and current MVP, 2. Operating philosophy, 3. Project truth and protected files, 4. Target architecture (+13 more)

### Community 53 - "symmetric_fixture"
Cohesion: 0.21
Nodes (4): symmetric_fixture(), add(), event(), SymmetricProofTests

### Community 54 - "upditerm.py"
Cohesion: 0.07
Nodes (8): Console, main(), parse_arguments(), SerialPort, SerialUPDI, Terminal, TransportError, UPDI

### Community 55 - "TrackerConfig"
Cohesion: 0.10
Nodes (18): TrackerConfig, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 58 - "FakeRadio"
Cohesion: 0.09
Nodes (17): FakeRadio, bytes, campaign_id, completion_error, destination, done, incoming, incoming_campaign_id (+9 more)

### Community 59 - "ReceiveTests"
Cohesion: 0.13
Nodes (3): ReceiveTests, wait(), wait()

### Community 60 - "Sender"
Cohesion: 0.07
Nodes (37): Result, kOk, kPending, kProtocolError, kRadioError, kRejected, kTimeoutExhausted, Sender (+29 more)

### Community 62 - "PlatformResult"
Cohesion: 0.13
Nodes (18): InitializeAdc(), ReadBatteryAdc(), ReadSample(), ReadTemperatureAdc(), WaitForConversion(), PlatformResult, kBusy, kForbidden (+10 more)

### Community 63 - "ihex"
Cohesion: 0.19
Nodes (3): ApplicationPageWriteTests, command(), ihex()

### Community 64 - "MvpRoundtripTests"
Cohesion: 0.21
Nodes (3): Board, frames(), MvpRoundtripTests

### Community 65 - "arq_trial.py"
Cohesion: 0.11
Nodes (9): ApplicationConfigTests, diagnostic_case(), reverse_exchange(), validate_reverse(), load(), raw_payload(), raw_send_command(), render() (+1 more)

### Community 66 - "HardwareGateTests"
Cohesion: 0.06
Nodes (7): BuildAcceptanceTests, dynamic_attr(), effective_platformio_config(), HardwareGateTests, command(), hardware_blockers(), parse_test_counts()

### Community 67 - "require"
Cohesion: 0.06
Nodes (20): DeviceReconnectTests, make_device(), make_probe(), require(), crc8(), FirmwareIdentityTests, ihex_record(), marker() (+12 more)

### Community 68 - "OPERATING CONTRACT — READ ALL BEFORE EDITING"
Cohesion: 0.12
Nodes (15): 0. Target, boundaries, priorities, 10. Mandatory negative and protocol matrix, 11. Acceptance criteria — NOT negotiable, 12. Agentic self-repair loop — persistent, evidence-driven, bounded, 13. First actions — execute in this exact order, 1. Mandatory first phase: read-only inventory and graph analysis, 2. Reference repo: behavior parity without copying defects, 3. IMPORTANT RADIO FACT: SX127x `setNodeAddress` (+7 more)

### Community 69 - "Config"
Cohesion: 0.11
Nodes (18): Config, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 71 - "Tracker Hardware SSOT — LoRa Tracker RFM"
Cohesion: 0.22
Nodes (9): 1. Board identity and components, 2. AVR128DA28 pin and net SSOT, 3. Power and startup contract, 4. Minimal firmware implementation contract, 5. Acceptance criteria / physical evidence, 6. Firmware configuration, Exact LoRa RFM95W signal map, Sources (+1 more)

### Community 72 - "C++ Refactoring Results"
Cohesion: 0.18
Nodes (10): A — Action, C++ Refactoring Results, Current follow-up verification — 2026-11-19, R — Result, S — Situation, T — Task, Trade-offs and limits, SleepFor() (+2 more)

### Community 73 - "EventQueue"
Cohesion: 0.11
Nodes (15): Event, campaign_id, error, name, sequence, time_ms, type, EventQueue (+7 more)

### Community 74 - "commands.cpp"
Cohesion: 0.08
Nodes (26): Command, budget, kind, payload, payload_length, session, stride, CommandInput (+18 more)

### Community 75 - "Port"
Cohesion: 0.21
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 76 - "receiver_boot.py"
Cohesion: 0.23
Nodes (6): install(), read_snapshot(), read_snapshot_command(), require_preserved(), sha(), verify_live_receipt()

### Community 77 - "LoRa"
Cohesion: 0.11
Nodes (12): Address, LoRa, _active, _hardware, _initialized, _last_rssi, _module, _my_addr (+4 more)

### Community 78 - "role_detector.py"
Cohesion: 0.17
Nodes (9): FirmwareIdentity, ProbeEvidence, USBDevice, classify_devices(), diff_device_presence(), _identity_role(), _probe_for(), _registry_hint() (+1 more)

### Community 80 - "915 MHz LoRa bench procedure"
Cohesion: 0.29
Nodes (6): 915 MHz LoRa bench procedure, App-only programming after exact write approval, Hardware results, Refactor verification, RF conditions and acceptance, Verified candidates

### Community 81 - "subprocess"
Cohesion: 0.18
Nodes (15): bootstrap(), create_temp_dir(), main(), capture_host_commands(), check(), complexity_check(), firmware_checks(), main() (+7 more)

### Community 82 - "Receiver"
Cohesion: 0.09
Nodes (21): Receiver, accepted, armed, deliveries, duplicates, expected, last_sequence, session (+13 more)

### Community 83 - "generate_lora_config.py"
Cohesion: 0.12
Nodes (3): BootAnalysisTests, analyze(), main()

### Community 84 - "SenderState"
Cohesion: 0.29
Nodes (7): SenderState, kBackoff, kDelivered, kFailed, kIdle, kTransmitting, kWaitingAck

### Community 85 - "firmware_identity.py"
Cohesion: 0.18
Nodes (7): crc8(), FingerprintResult, IdentityParseResult, match_flash_fingerprint(), parse_identity_stream(), _valid_build(), _valid_timestamp()

### Community 86 - "application_bounds_for_environment"
Cohesion: 0.19
Nodes (6): DirectionalTests, RadioOnlyTests, TargetLayoutTests, application_bounds_for_environment(), _config_int(), target_fuses()

### Community 87 - "gateway_ssot.hpp"
Cohesion: 0.09
Nodes (16): Comm, AIR_CONFIG_NODE_ADDR, DEBUG_BAUD_RATE, ENABLE_I2C_WIRE, GATEWAY_ANYCAST_ADDR, GATEWAY_DEFAULT_ADDR, I2C_ADDRESS_BASE, I2C_ADDRESS_STRAP_SHIFT (+8 more)

### Community 90 - "Controller"
Cohesion: 0.13
Nodes (12): Controller, last_led1_toggle_, last_tx_toggle_, led1_interval_ms_, led1_on_, led1_pin_, led2_pin_, led_off_level_ (+4 more)

### Community 91 - "string"
Cohesion: 0.07
Nodes (9): updi_role_log_dropped(), main(), reset_radio(), command(), complete_tx(), deliver(), main(), updi_uart_try_tx() (+1 more)

### Community 95 - "ReverseRawTests"
Cohesion: 0.20
Nodes (3): ReverseRawTests, audit_raw_configuration(), status()

### Community 96 - "gateway_i2c_test.cpp"
Cohesion: 0.10
Nodes (7): DecodeLoraConfig(), EepromSpy, reads, writes, main(), clear_capture(), main()

### Community 97 - "Session"
Cohesion: 0.11
Nodes (3): Console, main(), Session

### Community 98 - "ErrataDiagnosticsTests"
Cohesion: 0.21
Nodes (3): ErrataDiagnosticsTests, decode_snapshot(), interpret_rx()

### Community 99 - "PIN_MAPPING_AUDIT.md"
Cohesion: 0.20
Nodes (8): Data and protocol boundaries, Firmware source map, Hardware and power, Receiver APPCODE, Source path, Builds and hardware, Sender APPCODE, Source path

### Community 102 - "updi_probe.py"
Cohesion: 0.20
Nodes (9): firmware_fingerprint_evidence(), identify_mcu(), _is_access_error(), _port_busy(), probe_firmware_identity(), probe_target_sib(), read_firmware_flash(), _require_safe() (+1 more)

### Community 103 - "EventContext"
Cohesion: 0.21
Nodes (12): arq_board, FlushBenchStatus(), RecordRadioRegisters(), RecordReceiveDiagnostics(), RecordStatusCounters(), RecordStatusTiming(), ReadReceivedFrame(), InitializeRadio() (+4 more)

### Community 105 - "Pins"
Cohesion: 0.14
Nodes (14): Pins, ANALOG_IN_0, ANALOG_IN_1, DEBUG_RX, DEBUG_TX, HOST_INT, LED1, LED2 (+6 more)

### Community 106 - "mvp_app.cpp"
Cohesion: 0.37
Nodes (12): debug_init(), debug_write(), debug_write_float(), debug_write_hex(), debug_write_int(), Initialize(), Poll(), RecordStartupStage() (+4 more)

### Community 107 - "Pair"
Cohesion: 0.15
Nodes (12): Application, applied, reject, Pair, a, aa, b, bb (+4 more)

### Community 109 - "RawStorage"
Cohesion: 0.31
Nodes (5): ui64toa(), RawStorage, _cached_block, _cached_pos, Storage<T>::_save_state()

### Community 110 - "ssot_codec.cpp"
Cohesion: 0.18
Nodes (15): DecodePayloadFields(), EncodeControlPayload(), ssot::AckMatches(), ssot::DecodeFrame(), ssot::DecodePayload(), ssot::EncodeAckFrame(), ssot::EncodeAckPayload(), ssot::EncodeDataFrame() (+7 more)

### Community 111 - "ReportEntry"
Cohesion: 0.13
Nodes (22): ReportEntry, day, hour, latitude, longitude, minute, month, quality (+14 more)

### Community 113 - "stddef"
Cohesion: 0.10
Nodes (11): Frame, dst, length, payload, reason, sequence, session, src (+3 more)

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
Cohesion: 0.09
Nodes (28): controlled_cpu_reset(), firmware_identity_from_events(), Gate1Audit, gpr_roundtrip_succeeded(), halted_gpr_roundtrip(), instrument(), open_exclusive(), mailbox_snapshot() (+20 more)

### Community 120 - "avr128da28_device.h"
Cohesion: 0.15
Nodes (12): IsAppCodeRange(), PORT_struct, PORT_t, SPI_struct, SPI_t, TWI_struct, TWI_t, TwiHold (+4 more)

### Community 121 - "State"
Cohesion: 0.22
Nodes (8): State, kComplete, kFailed, kRetryPending, kRxWait, kTxData, kTxResponse, kWaitResponse

### Community 122 - "AdcTemp"
Cohesion: 0.17
Nodes (12): AdcTemp, ADC_MAX_COUNTS, CTRLA_ENABLE_12BIT, FIXED_POINT_SHIFT, INIT_DELAY_SETTING, KELVIN_TO_CELSIUS, MUX_TEMP_CHANNEL, PRESCALER_SETTING (+4 more)

### Community 123 - "sender/appcode/reliable.cpp"
Cohesion: 0.17
Nodes (19): AcceptData(), ArmRadio(), HandleRadioCommand(), Initialize(), InitializeGpio(), InitializeRoleGpio(), Poll(), PollRoleRadio() (+11 more)

### Community 125 - "SPIClass"
Cohesion: 0.18
Nodes (3): SPIClass, SPISettings, beginTransaction()

### Community 126 - "reliable_transport_test.cpp"
Cohesion: 0.36
Nodes (9): count_transition(), deliver(), dropped(), finish_reply(), loss_scenario(), main(), start_data(), stress_round_trips() (+1 more)

### Community 128 - "Sd2Card"
Cohesion: 0.22
Nodes (4): get_data_and_log_partitions(), read_line(), Sd2Card, main()

### Community 130 - "TraceBus"
Cohesion: 0.28
Nodes (3): TraceBus, sensitivity_writes, stage

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
Cohesion: 0.12
Nodes (14): open_file_in_root(), mbr_t, mbrSig0, mbrSig1, part, SdFile, data_, length_ (+6 more)

### Community 140 - "load_package"
Cohesion: 0.33
Nodes (4): boot(), BootPackageTests, recording_command(), load_package()

### Community 143 - "validate_live_proof"
Cohesion: 0.38
Nodes (4): complete_campaign_logs(), packet_event(), payload_event(), RfEvidenceTests

### Community 145 - "raw_mvp_stub/Arduino.h"
Cohesion: 0.21
Nodes (5): begin(), digitalWrite(), end(), ltoa(), push_back()

### Community 148 - "Connect to a virtual UART on an AVR via UPDI"
Cohesion: 0.22
Nodes (8): Connect to a virtual UART on an AVR via UPDI, Demo program, License, Prerequisites, UPDI interface, Upditerm, Usage, Virtual UART

### Community 149 - "check_cpp.sh"
Cohesion: 0.70
Nodes (4): PATH, record_support(), run_support(), check_cpp.sh script

### Community 150 - "assess"
Cohesion: 0.28
Nodes (3): assess(), response(), _status()

### Community 152 - "Gateway-to-Receiver SF7 Hello World"
Cohesion: 0.25
Nodes (7): Current result — Receiver installed, normal startup unresolved, Gateway-to-Receiver SF7 Hello World, No-meter read-only hardware verified; Receiver write wiring unconfirmed, Receiver boot incompatibility, Remaining physical prerequisites, Single-packet behavior and identities, Verified software result

### Community 154 - "TaskScheduler"
Cohesion: 0.22
Nodes (4): TaskScheduler::GetTaskCount(), TaskScheduler, task_count_, tasks_

### Community 157 - "LoRa ACK/NACK analysis and verification"
Cohesion: 0.14
Nodes (13): Current continuation, Earlier source-ownership migration, Markdown inventory and references, Source and documentation deletion audit, Bench ARQ protocol, Current evidence, Documentation audit, Hardware trial requirements and result (+5 more)

### Community 158 - "Offline LoRa firmware refactor"
Cohesion: 0.33
Nodes (6): Application and dependency audit, Firmware matrix, Historical BOOT and deployment status, Offline LoRa firmware refactor, Verification, Wire and host evidence

### Community 162 - "AVR128DA28 LoRa Board Pin Audit"
Cohesion: 0.29
Nodes (7): AVR128DA28 LoRa Board Pin Audit, AVR128DA28 package pins, Evidence basis, Gateway LoRa daughterboard, Radio profile and serial identity, Read the table, Tracker

### Community 164 - "PacketAck"
Cohesion: 0.40
Nodes (4): DecodePacketAck(), PacketAck, seq, type

### Community 165 - "soak_campaign"
Cohesion: 0.22
Nodes (8): hardware_gate_errors(), missing_soak_prerequisites(), soak_campaign(), read_run_evidence(), update_partial_record(), summarize_soak_results(), latency(), wilson_interval95()

### Community 166 - "LossMetrics"
Cohesion: 0.29
Nodes (7): LossMetrics, ack_tx, attempts, duplicates, nack_tx, retries, timeouts

### Community 169 - "RestartTask"
Cohesion: 0.29
Nodes (3): RestartTask, completions, entries

### Community 170 - "PacketMaintenanceAck"
Cohesion: 0.40
Nodes (4): DecodePacketMaintenanceAck(), PacketMaintenanceAck, response, type

### Community 173 - "tracker_radio_packets.h"
Cohesion: 0.17
Nodes (8): DecodePacketAdvertise(), DecodePacketMaintenance(), PacketAdvertise, seq, type, PacketMaintenance, command, type

### Community 175 - "normalize_ihex_region"
Cohesion: 0.18
Nodes (4): BuildIdentityImagesTests, normalize_ihex_region(), _parse_ihex(), prepare()

### Community 180 - "AVR128DA28 LoRa firmware"
Cohesion: 0.33
Nodes (6): Application configuration, AVR128DA28 LoRa firmware, Build, Host tests, Preserved boundaries, Static analysis and formatting

### Community 188 - "LORA_ACK_NACK.md"
Cohesion: 0.27
Nodes (4): Source ownership baseline, Real-radio verification evidence, Status: BLOCKED, no physical trials run, Receiver BOOT boundary

### Community 200 - "PacketReport"
Cohesion: 0.40
Nodes (4): PacketReport, report, seq, type

### Community 203 - "ExcludedSx1262Experiment"
Cohesion: 0.20
Nodes (10): ExcludedSx1262Experiment, BUSY_PIN, DIO1_PIN, ERROR_RETRY_DELAY_MS, NSS_PIN, PACKET_BYTES, PACKET_COUNT, PACKET_GAP_MS (+2 more)

### Community 204 - "core_test.cpp"
Cohesion: 0.38
Nodes (12): absolute_deadline(), ack_matrix(), codec(), control(), data(), fault_harness(), fresh(), main() (+4 more)

### Community 206 - "install_cpp_quality_tools.sh"
Cohesion: 0.50
Nodes (3): find_tool(), PATH, install_cpp_quality_tools.sh script

### Community 212 - "Revision"
Cohesion: 0.50
Nodes (4): Revision, major, minor, raw_revision_id

### Community 213 - "trace_stub"
Cohesion: 0.22
Nodes (3): CompiledHandoffTests, reset_target(), trace_stub()

### Community 214 - "mvp_stub/Arduino.h"
Cohesion: 0.25
Nodes (3): CPUINT(), digitalWrite(), digitalWriteFast()

### Community 215 - "Task"
Cohesion: 0.22
Nodes (4): Task, is_paused_, pt_, wakeup_time_

### Community 217 - "_build_handoff"
Cohesion: 0.24
Nodes (3): build_fixture(), _build_handoff(), page_write_command()

### Community 221 - "Tasks"
Cohesion: 0.22
Nodes (9): Tasks, ENABLE_HEARTBEAT_TASK, HEARTBEAT_NAME, HEARTBEAT_OFF_MS, HEARTBEAT_ON_MS, HEARTBEAT_PERIOD_MS, I2C_RESET_SETTLE_MS, LED1_TOGGLE_INTERVAL_MS (+1 more)

### Community 222 - "effective_project_sections"
Cohesion: 0.36
Nodes (7): build_flag_defines(), effective_project_sections(), radio_profile_compile_flags(), rf_spi_diagnostic_config(), shared_rf_profile(), upload_config_preserves_flash(), valid_rf_profile_config()

### Community 223 - "PacketReportWithAck"
Cohesion: 0.33
Nodes (5): DecodePacketReportWithAck(), PacketReportWithAck, report, seq, type

### Community 225 - "Final LoRa firmware architecture"
Cohesion: 0.40
Nodes (5): Board roles and source ownership, Build and safety boundary, Final LoRa firmware architecture, Protocol boundaries, Status

### Community 226 - "C++ Refactoring Baseline"
Cohesion: 0.40
Nodes (5): C++ Refactoring Baseline, Parent-revision measurements, Production and analysis scope, Repository snapshot, Toolchain and limits

### Community 227 - "Offline regression matrix"
Cohesion: 0.40
Nodes (5): Firmware matrix, Hardware is a separate gate, Host, quality, and fixture checks, Linked image checks, Offline regression matrix

### Community 228 - "ReceiveCounters"
Cohesion: 0.40
Nodes (5): ReceiveCounters, crc_errors, decode_errors, last_rx_flags, rx_done

### Community 229 - "shared/README.md"
Cohesion: 0.40
Nodes (3): Shared firmware modules, Adding and checking libraries, `stable_lib`

### Community 237 - "ExcludedSx1262Experiment"
Cohesion: 0.18
Nodes (11): 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates, Gateway Hardware SSOT — Rudolph Gateway, H1 (10-pin; only pins 1–5 used in the source schematic) (+3 more)

### Community 299 - "sleep.cpp"
Cohesion: 0.15
Nodes (8): SetUnixTime(), SleepState, force_wakeup, is_sleeping, last_rtc_ticks, unix_time, InitializeTime(), SetTime()

### Community 313 - "lora/library.json"
Cohesion: 0.25
Nodes (8): jgromes/RadioLib, build, includeDir, srcDir, dependencies, jgromes/RadioLib@7.1.2, name, version

### Community 315 - "time-utils/library.json"
Cohesion: 0.25
Nodes (8): paulstoffregen/Time, build, includeDir, srcDir, dependencies, paulstoffregen/Time@^1.6.1, name, version

### Community 335 - "receiver/appcode/reliable.cpp"
Cohesion: 0.11
Nodes (14): AcceptData(), ArmRadio(), HandleRadioCommand(), Initialize(), InitializeGpio(), InitializeRoleGpio(), Poll(), RecordTransportEvent() (+6 more)

### Community 341 - "ใช้งาน Codex Goal — LoRa E2E Feature-Based"
Cohesion: 0.33
Nodes (6): ค่าคลื่นวิทยุที่ตั้งไว้, ความต่างระหว่าง Goal กับ config, จุดที่ต้องพิสูจน์, เริ่มต้นใช้งานเฟิร์มแวร์ LoRa AVR128DA28, แหล่งอ้างอิง, ใช้งาน Codex Goal — LoRa E2E Feature-Based

### Community 357 - "Hardware"
Cohesion: 0.09
Nodes (3): firmware_role(), Hardware, parked()

## Knowledge Gaps
- **597 isolated node(s):** `day`, `fixquality`, `_gga_received`, `hour`, `latitude` (+592 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1629 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **118 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Transport` connect `Transport` to `.EmitEvent`, `EventQueue`, `Pair`, `.IsActive`, `Result`, `State`, `string`, `reliable_transport_test.cpp`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **What connects `day`, `fixquality`, `_gga_received` to the rest of the system?**
  _597 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.09263157894736843 - nodes in this community are weakly interconnected._
- **Why does `analyze()` connect `analyze` to `pathlib`, `error`, `normalize_ihex_region`, `generate_lora_config.py`, `Json`, `main`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Should `Storage` be split into smaller, more focused modules?**
  _Cohesion score 0.09401709401709402 - nodes in this community are weakly interconnected._
- **Why does `LoRa` connect `LoRa` to `LoRa source ownership V2`, `SX1276`, `Module`, `updi_role_log`, `LoRa ACK/NACK analysis and verification`, `gateway_radio.cpp`, `Offline LoRa firmware refactor`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Should `mvp_board.cpp` be split into smaller, more focused modules?**
  _Cohesion score 0.08620689655172414 - nodes in this community are weakly interconnected._