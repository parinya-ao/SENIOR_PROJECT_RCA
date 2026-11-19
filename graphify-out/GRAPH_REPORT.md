# Graph Report - SENIOR_PROJECT_RCA  (2026-11-19)

## Corpus Check
- 286 files · ~159,927 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 25 file(s) not represented in the graph (top: (none) 10, .toml 6, .css 4)

## Summary
- 3505 nodes · 6831 edges · 246 communities (142 shown, 104 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 454 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3f9f3f05`
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
- test_arq.py
- validate_repo_isolation.py
- appcode/arq/receiver.cpp
- RadioBringupTests
- arq_trial.py
- updi_role_log
- rf_proof.py
- stdint
- Transport
- Gate1Tests
- RepositoryIsolationTests
- load
- gateway_app.cpp
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
- ControlInput
- image_evidence
- DeviceLayout
- Bus
- require
- TracePort
- directional_test.cpp
- EventContext
- AGENTS.md — AVR128DA28 / LoRa Embedded Engineering
- symmetric_fixture
- upditerm.py
- TrackerConfig
- task.cpp
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
- install
- LoRa
- mcurses_puts_P
- 915 MHz LoRa bench procedure
- subprocess
- Receiver
- upditerm.py
- role_detector.py
- CompiledHandoffTests
- updi_probe.py
- SPIClass
- Controller
- string
- radio_link.cpp
- role_log_test.cpp
- Session
- ErrataDiagnosticsTests
- firmware_identity.py
- .test_T41_resume_helper_only_runs_a_confirmed_stopped_cpu
- Json
- Command
- arq_bench.h
- Pins
- mvp_app.cpp
- Pair
- mcurses-printf.cpp
- RawStorage
- ssot_codec.cpp
- ReportEntry
- run_gate1
- stub/Arduino.h
- Result
- tracker_config.h
- State
- gate1_live.py
- avr128da28_device.h
- State
- Radio915ValidationTests
- AdcTemp
- Json
- ReceiverBootTests
- reliable_transport_test.cpp
- ReliableTransportTests
- Sd2Card
- BuildEnvironment
- TraceBus
- PacketBoot
- HeartbeatTask
- ErrorCode
- ProvisioningResult
- EventStats
- StableLoraSafetyTests
- SD.h
- SdFile
- tempfile
- Frame
- TaskScheduler
- validate_live_proof
- Module
- raw_mvp_stub/Arduino.h
- .test_T32_halted_gpr_probe_resumes_cpu_after_roundtrip
- Connect to a virtual UART on an AVR via UPDI
- check_cpp.sh
- test_arq.py
- link_budget
- Gateway-to-Receiver SF7 Hello World
- SPIClass
- I2cResetTask
- .test_runner_uses_receiver_ready_then_one_gateway_start
- C++ Refactoring Baseline
- stub/SPI.h
- OWNERSHIP_BASELINE.md
- Wire.h
- RfTestContinuationTests
- PacketAck
- PacketAdvertise
- LossMetrics
- discover_ports
- _build_handoff
- PacketMaintenanceAck
- SenderStableTransportTests
- Tasks
- PacketReportWithAck
- BuildIdentityImagesTests
- .test_rf_enabled_upload_does_not_require_rf_authorization
- AVR128DA28 LoRa firmware
- RawMvpTests
- Comm
- Offline LoRa firmware refactor
- RestartTask
- MonitorConsole
- CppInterfaceTests
- core_test.cpp
- SsotProtocolTests
- install_cpp_quality_tools.sh
- PacketMaintenance
- parse_raw_mvp_logs
- Task
- mvp_stub/Arduino.h
- .test_T28_reenable_uart_preserves_pending_rx_flag_and_reads_back
- receiver_boot.py
- SingleFirmwareEntryTests
- application_bounds_for_environment
- ExcludedSx1262Experiment
- sleep.cpp
- lora
- lora/library.json
- time-utils/library.json
- usb_inventory.py
- arduino
- ใช้งาน Codex Goal — LoRa E2E Feature-Based
- Suggested append-only AGENTS.md contract (merge; do not overwrite existing instructions)
- Hardware

## God Nodes (most connected - your core abstractions)
1. `Transport` - 64 edges
2. `Gate1Tests` - 47 edges
3. `SystemConstants` - 46 edges
4. `State` - 45 edges
5. `HardwareGateTests` - 36 edges
6. `Hardware` - 36 edges
7. `analyze()` - 35 edges
8. `LoRa` - 34 edges
9. `Sender` - 33 edges
10. `RCATests` - 33 edges

## Surprising Connections (you probably didn't know these)
- `Application and dependency audit` --references--> `LoRa`  [INFERRED]
  docs/refactoring/OFFLINE_LORA.md → src/shared/radio/radio_link.h
- `Scope` --references--> `TrackerConfig`  [INFERRED]
  TRACKER_CONFIG_SSOT.md → include/tracker_config.h
- `Fixed settings and checks` --references--> `SystemConstants`  [INFERRED]
  TRACKER_CONFIG_SSOT.md → include/tracker_config.h
- `Radio SPI and interrupt contract` --references--> `ExcludedSx1262Experiment`  [INFERRED]
  GATEWAY_SSOT.md → include/gateway_ssot.hpp
- `Fixed settings and checks` --references--> `TrackerConfig`  [INFERRED]
  TRACKER_CONFIG_SSOT.md → include/tracker_config.h

## Import Cycles
- None detected.

## Communities (246 total, 104 thin omitted)

### Community 1 - "rf_proof.py"
Cohesion: 0.14
Nodes (37): application_layout_verified(), authorized_application_pages(), boot_fuses_match(), capture_usb_topology(), check_port_owners(), clean_builds(), firmware_measurement(), host_tests() (+29 more)

### Community 2 - "Storage"
Cohesion: 0.09
Nodes (11): Storage, _first, _raw, _start_block, Storage<T>::clear(), Storage<T>::_load_state(), Storage<T>::peek(), Storage<T>::pop() (+3 more)

### Community 3 - "mvp_board.cpp"
Cohesion: 0.06
Nodes (12): updi_role_log_dropped(), delay(), main(), pump(), state_name(), step(), command(), complete_tx() (+4 more)

### Community 4 - "analyze"
Cohesion: 0.07
Nodes (9): RCATests, analyze(), load(), read(), classify(), compare_snapshots(), delta(), main() (+1 more)

### Community 5 - "mcurses.c"
Cohesion: 0.14
Nodes (22): addch(), addstr(), addstr_P(), clear(), clrtobot(), delch(), getch(), getnstr() (+14 more)

### Community 6 - "appcode/arq/sender.cpp"
Cohesion: 0.31
Nodes (18): ArmSession(), CurrentSession(), ExecuteCommand(), FailAdapter(), FeedCommandByte(), FlushStatus(), GetEventContext(), HandleReceive() (+10 more)

### Community 7 - "CaptureTests"
Cohesion: 0.06
Nodes (3): CaptureTests, command(), monotonic()

### Community 8 - "error"
Cohesion: 0.14
Nodes (13): error(), campaign(), progress(), run_one(), Capture, prepare(), radio_only_bringup(), reader_free_h01_firmware() (+5 more)

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

### Community 13 - "test_arq.py"
Cohesion: 0.12
Nodes (12): SourceFingerprintTests, artifacts(), canonical(), digest(), generate(), load_radio_profile(), main(), _profile_python() (+4 more)

### Community 14 - "validate_repo_isolation.py"
Cohesion: 0.25
Nodes (11): _check_config(), _check_symlink(), _inside(), _items(), _label(), _local_dependency(), main(), _resolved() (+3 more)

### Community 15 - "appcode/arq/receiver.cpp"
Cohesion: 0.32
Nodes (17): ArmSession(), CurrentSession(), ExecuteCommand(), FailAdapter(), FeedCommandByte(), FlushStatus(), GetEventContext(), HandleReceive() (+9 more)

### Community 16 - "RadioBringupTests"
Cohesion: 0.08
Nodes (7): DirectionalHostTests, RadioBringupTests, acquire(), command(), audit_radio_configuration(), read_radio(), validate_hello_exchange()

### Community 17 - "arq_trial.py"
Cohesion: 0.13
Nodes (24): build_soak_plan(), capture_tracker_diagnostics(), close_updi_without_recovery(), diagnostic_case(), drain_updi_messages(), hardware_gate_errors(), hello_airtime_budget(), lora_time_on_air_us() (+16 more)

### Community 18 - "updi_role_log"
Cohesion: 0.08
Nodes (50): AcceptData(), ArmRadio(), HandleRadioCommand(), Initialize(), InitializeGpio(), InitializeRoleGpio(), Poll(), RecordTransportEvent() (+42 more)

### Community 19 - "rf_proof.py"
Cohesion: 0.08
Nodes (18): capture_radio_spi_log(), parse_radio_spi_log(), parse_rf_campaign(), radio_startup_matches(), run_stable_ack_rf_test(), command(), record(), run_wrong_destination_rf_test() (+10 more)

### Community 22 - "stdint"
Cohesion: 0.07
Nodes (8): Poll(), ReadTemperatureCelsius(), Frame, campaign_id, destination, sequence, source, type

### Community 24 - "Transport"
Cohesion: 0.05
Nodes (30): Transport, armed_, context_, error_, event_context_, frequency_, have_accepted_, kMaxData (+22 more)

### Community 26 - "Gate1Tests"
Cohesion: 0.11
Nodes (5): Gate1Tests, rows(), transaction(), response(), verify_hashes()

### Community 28 - "load"
Cohesion: 0.11
Nodes (7): ConfigurationTests, ReceiverHardwareTests, checked_cpp(), load(), main(), unique_object(), validate()

### Community 29 - "gateway_app.cpp"
Cohesion: 0.06
Nodes (14): I2cCommandTask, command_, command_length_, InitializeEspCommunication(), StoreI2c16(), Initialize(), IsRadioTransmitting(), RegisterRadioTask() (+6 more)

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
Cohesion: 0.15
Nodes (22): DecodePacketReport(), DecodePacketReportWithAck(), DecodeReportEntry(), EncodeConfig(), EncodePacketAck(), EncodePacketAdvertise(), EncodePacketBoot(), EncodePacketMaintenance() (+14 more)

### Community 37 - "detect_devices.py"
Cohesion: 0.16
Nodes (11): build_parser(), _load_registry(), main(), _probe_device(), _run_self_test(), SafetyArgumentParser, _scan(), _watch() (+3 more)

### Community 38 - "BenchStatus"
Cohesion: 0.12
Nodes (17): BenchStatus, attempted, completed, control_rejects, crc_errors, decode_errors, deliveries, duplicates (+9 more)

### Community 39 - "EventId"
Cohesion: 0.05
Nodes (41): Component, kApplication, kBoot, kHil, kNvm, Event(), EventId, kAuthenticationStarted (+33 more)

### Community 41 - "ScanResult"
Cohesion: 0.12
Nodes (4): DetectedDevice, ScanResult, format_text(), result_to_json()

### Community 42 - "reverse_raw_app.cpp"
Cohesion: 0.19
Nodes (15): arq_board, board_ssot_init(), ExecuteCommand(), FeedCommandByte(), Initialize(), IsPayloadCommand(), ParkRadio(), Poll() (+7 more)

### Community 43 - "ControlInput"
Cohesion: 0.22
Nodes (9): ControlInput, command, digits, last_ms, reading, triggered, value, ssot::ControlInputFeed() (+1 more)

### Community 44 - "image_evidence"
Cohesion: 0.19
Nodes (7): event(), image_evidence(), journal(), StableTransportProofTests, wrong_destination_journal(), assess(), validate_stable_transport()

### Community 45 - "DeviceLayout"
Cohesion: 0.11
Nodes (19): IsAppCodeRange(), DeviceLayout, kAppDataStart, kApplicationEnd, kApplicationImageEnd, kApplicationStart, kBootEnd, kBootSizePages (+11 more)

### Community 47 - "Bus"
Cohesion: 0.11
Nodes (6): Bus, fifo, finish_delay, regs, reset_mode, ticks

### Community 48 - "require"
Cohesion: 0.11
Nodes (4): DetectionIntegrationTests, pio(), runner(), require()

### Community 49 - "TracePort"
Cohesion: 0.07
Nodes (5): controlled_cpu_reset(), instrument(), open_exclusive(), read_updi_pesig(), TracePort

### Community 50 - "directional_test.cpp"
Cohesion: 0.12
Nodes (19): AcquireLine(), FlushByte(), OverflowCount(), PendingLineCount(), RecordEvent(), RecordFrame(), drain_status(), main() (+11 more)

### Community 51 - "EventContext"
Cohesion: 0.30
Nodes (9): FlushBenchStatus(), RecordRadioRegisters(), RecordReceiveDiagnostics(), RecordStatusCounters(), RecordStatusTiming(), ReadReceivedFrame(), ReadRadioRegister(), EventContext (+1 more)

### Community 52 - "AGENTS.md — AVR128DA28 / LoRa Embedded Engineering"
Cohesion: 0.10
Nodes (20): 10. Logging, measurement, and evidence, 11. Decision and intervention policy, 12. Response contract, 13. Technical references (read when relevant; do not substitute for active SSOT), 1. Mission and current MVP, 2. Operating philosophy, 3. Project truth and protected files, 4. Target architecture (+12 more)

### Community 53 - "symmetric_fixture"
Cohesion: 0.21
Nodes (4): symmetric_fixture(), add(), event(), SymmetricProofTests

### Community 54 - "upditerm.py"
Cohesion: 0.08
Nodes (7): Console, main(), SerialPort, SerialUPDI, Terminal, TransportError, UPDI

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
Cohesion: 0.05
Nodes (44): Result, kOk, kPending, kProtocolError, kRadioError, kRejected, kTimeoutExhausted, Sender (+36 more)

### Community 62 - "PlatformResult"
Cohesion: 0.14
Nodes (18): InitializeAdc(), ReadBatteryAdc(), ReadSample(), ReadTemperatureAdc(), WaitForConversion(), PlatformResult, kBusy, kForbidden (+10 more)

### Community 63 - "ihex"
Cohesion: 0.16
Nodes (3): ApplicationPageWriteTests, command(), ihex()

### Community 64 - "MvpRoundtripTests"
Cohesion: 0.21
Nodes (3): Board, frames(), MvpRoundtripTests

### Community 65 - "arq_trial.py"
Cohesion: 0.09
Nodes (11): ApplicationConfigTests, ReverseRawTests, audit_raw_configuration(), reverse_exchange(), status(), validate_reverse(), load(), raw_payload() (+3 more)

### Community 66 - "HardwareGateTests"
Cohesion: 0.06
Nodes (8): BuildAcceptanceTests, dynamic_attr(), effective_platformio_config(), FlashSafetyTests, HardwareGateTests, command(), hardware_blockers(), upload_config_preserves_flash()

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
Cohesion: 0.18
Nodes (9): 1. Board identity and components, 2. AVR128DA28 pin and net SSOT, 3. Power and startup contract, 4. Minimal firmware implementation contract, 5. Acceptance criteria / physical evidence, 6. Firmware configuration, Exact LoRa RFM95W signal map, Sources (+1 more)

### Community 72 - "C++ Refactoring Results"
Cohesion: 0.22
Nodes (8): A — Action, C++ Refactoring Results, R — Result, S — Situation, T — Task, Trade-offs and limits, SleepFor(), PowerSavingTaskScheduler

### Community 73 - "EventQueue"
Cohesion: 0.12
Nodes (15): Event, campaign_id, error, name, sequence, time_ms, type, EventQueue (+7 more)

### Community 74 - "commands.cpp"
Cohesion: 0.09
Nodes (16): CommandInput, buffer_, length_, overflow_, InputResult, kComplete, kOverflow, kPending (+8 more)

### Community 75 - "Port"
Cohesion: 0.21
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 76 - "install"
Cohesion: 0.25
Nodes (5): boot(), BootPackageTests, recording_command(), install(), sha()

### Community 77 - "LoRa"
Cohesion: 0.12
Nodes (11): LoRa, _active, _hardware, _initialized, _last_rssi, _module, _my_addr, _radio_version (+3 more)

### Community 78 - "mcurses_puts_P"
Cohesion: 0.31
Nodes (13): attrset(), clrtoeol(), curs_set(), deleteln(), endwin(), insertln(), mcurses_phyio_done(), mcurses_putc() (+5 more)

### Community 80 - "915 MHz LoRa bench procedure"
Cohesion: 0.29
Nodes (6): 915 MHz LoRa bench procedure, App-only programming after exact write approval, Hardware results, Refactor verification, RF conditions and acceptance, Verified candidates

### Community 81 - "subprocess"
Cohesion: 0.31
Nodes (9): capture_host_commands(), check(), complexity_check(), firmware_checks(), main(), record(), resolve_tools(), run() (+1 more)

### Community 82 - "Receiver"
Cohesion: 0.11
Nodes (18): Receiver, accepted, armed, deliveries, duplicates, expected, last_sequence, session (+10 more)

### Community 83 - "upditerm.py"
Cohesion: 0.11
Nodes (5): BootAnalysisTests, parse_arguments(), analyze(), main(), main()

### Community 84 - "role_detector.py"
Cohesion: 0.17
Nodes (8): ProbeEvidence, USBDevice, classify_devices(), diff_device_presence(), _identity_role(), _probe_for(), _registry_hint(), _registry_record()

### Community 86 - "updi_probe.py"
Cohesion: 0.19
Nodes (9): firmware_fingerprint_evidence(), identify_mcu(), _is_access_error(), _port_busy(), probe_firmware_identity(), probe_target_sib(), read_firmware_flash(), _require_safe() (+1 more)

### Community 90 - "Controller"
Cohesion: 0.13
Nodes (12): Controller, last_led1_toggle_, last_tx_toggle_, led1_interval_ms_, led1_on_, led1_pin_, led2_pin_, led_off_level_ (+4 more)

### Community 91 - "string"
Cohesion: 0.07
Nodes (3): main(), reset_radio(), main()

### Community 96 - "role_log_test.cpp"
Cohesion: 0.14
Nodes (5): EepromSpy, reads, writes, clear_capture(), main()

### Community 97 - "Session"
Cohesion: 0.11
Nodes (3): Console, main(), Session

### Community 98 - "ErrataDiagnosticsTests"
Cohesion: 0.21
Nodes (3): ErrataDiagnosticsTests, decode_snapshot(), interpret_rx()

### Community 99 - "firmware_identity.py"
Cohesion: 0.17
Nodes (8): FirmwareIdentity, crc8(), FingerprintResult, IdentityParseResult, match_flash_fingerprint(), parse_identity_stream(), _valid_build(), _valid_timestamp()

### Community 102 - "Command"
Cohesion: 0.15
Nodes (13): Command, budget, kind, payload, payload_length, session, stride, CommandKind (+5 more)

### Community 103 - "arq_bench.h"
Cohesion: 0.17
Nodes (9): FrameRead, kDiscard, kRadioError, kValid, ReceiveCounters, crc_errors, decode_errors, last_rx_flags (+1 more)

### Community 105 - "Pins"
Cohesion: 0.14
Nodes (14): Pins, ANALOG_IN_0, ANALOG_IN_1, DEBUG_RX, DEBUG_TX, HOST_INT, LED1, LED2 (+6 more)

### Community 106 - "mvp_app.cpp"
Cohesion: 0.37
Nodes (12): debug_init(), debug_write(), debug_write_float(), debug_write_hex(), debug_write_int(), Initialize(), Poll(), RecordStartupStage() (+4 more)

### Community 107 - "Pair"
Cohesion: 0.15
Nodes (12): Application, applied, reject, Pair, a, aa, b, bb (+4 more)

### Community 108 - "mcurses-printf.cpp"
Cohesion: 0.20
Nodes (3): mc_printf(), mc_vprintf(), printf()

### Community 109 - "RawStorage"
Cohesion: 0.36
Nodes (5): ui64toa(), RawStorage, _cached_block, _cached_pos, Storage<T>::_save_state()

### Community 110 - "ssot_codec.cpp"
Cohesion: 0.18
Nodes (15): DecodePayloadFields(), EncodeControlPayload(), ssot::AckMatches(), ssot::DecodeFrame(), ssot::DecodePayload(), ssot::EncodeAckFrame(), ssot::EncodeAckPayload(), ssot::EncodeDataFrame() (+7 more)

### Community 111 - "ReportEntry"
Cohesion: 0.14
Nodes (22): ReportEntry, day, hour, latitude, longitude, minute, month, quality (+14 more)

### Community 112 - "run_gate1"
Cohesion: 0.15
Nodes (9): firmware_identity_from_events(), Gate1Audit, gpr_roundtrip_succeeded(), main(), preservation_diff(), run_gate1(), startup_profile(), target_profile() (+1 more)

### Community 114 - "Result"
Cohesion: 0.22
Nodes (8): Result, kAccepted, kAckTimeout, kInvalidArgument, kPending, kRadioError, kRejected, kTxTimeout

### Community 115 - "tracker_config.h"
Cohesion: 0.20
Nodes (10): Checkpoint, INVALID_GNSS_DATE, SPI_CTRL_BEFORE_LORA, SPI_CTRL_BEFORE_PWR_ON, TRACKER_AFTER_GNSS_ON, TRACKER_BEFORE_GNSS_ON, Fixed settings and checks, Runtime settings (+2 more)

### Community 117 - "State"
Cohesion: 0.17
Nodes (12): State, begin_count, cs_high_seen, cs_low_seen, cs_pin, initialized, route, swap_count (+4 more)

### Community 119 - "gate1_live.py"
Cohesion: 0.13
Nodes (12): mailbox_snapshot(), _parse_block(), part_from_signature(), _read_block(), read_data_space_byte(), _readline(), roundtrip_gpr(), roundtrip_gpr_16() (+4 more)

### Community 120 - "avr128da28_device.h"
Cohesion: 0.09
Nodes (18): InitializeGpio(), PORT_struct, PORT_t, Revision, major, minor, raw_revision_id, SPI_struct (+10 more)

### Community 121 - "State"
Cohesion: 0.22
Nodes (8): State, kComplete, kFailed, kRetryPending, kRxWait, kTxData, kTxResponse, kWaitResponse

### Community 122 - "Radio915ValidationTests"
Cohesion: 0.17
Nodes (3): Radio915ValidationTests, valid_profile(), write_toml()

### Community 123 - "AdcTemp"
Cohesion: 0.17
Nodes (12): AdcTemp, ADC_MAX_COUNTS, CTRLA_ENABLE_12BIT, FIXED_POINT_SHIFT, INIT_DELAY_SETTING, KELVIN_TO_CELSIUS, MUX_TEMP_CHANNEL, PRESCALER_SETTING (+4 more)

### Community 125 - "ReceiverBootTests"
Cohesion: 0.20
Nodes (3): ReceiverBootTests, patch_page0(), require_preserved()

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
Cohesion: 0.18
Nodes (10): DecodeConfig(), DecodePacketBoot(), LoadFloat(), PacketBoot, checkpoint, config, device_model, firmware (+2 more)

### Community 133 - "ErrorCode"
Cohesion: 0.20
Nodes (10): ErrorCode, CONFIG_FILE_READ_FAILED, CONFIG_PART_NOT_FOUND, CONFIG_VOL_INIT_FAILED, DATA_PARTITION_NOT_FOUND, LOG_PARTITION_NOT_FOUND, LOGGER_SETUP_FAILED, LORA_INIT_FAILED (+2 more)

### Community 134 - "ProvisioningResult"
Cohesion: 0.27
Nodes (9): ProvisioningResult, kInvalidArgument, kOk, kUnprovisioned, kUnsupported, IsHmacKeyProvisioned(), ReadDeviceUid(), ReadHmacKey() (+1 more)

### Community 135 - "EventStats"
Cohesion: 0.18
Nodes (11): EventStats, ack_accepted, ack_tx, data_tx, destination_discards, duplicates, failures, nack_received (+3 more)

### Community 137 - "SD.h"
Cohesion: 0.25
Nodes (8): mbr_t, mbrSig0, mbrSig1, part, SdPartition, firstSector, totalSectors, type

### Community 138 - "SdFile"
Cohesion: 0.20
Nodes (6): open_file_in_root(), SdFile, data_, length_, position_, SdVolume

### Community 139 - "tempfile"
Cohesion: 0.13
Nodes (8): bootstrap(), create_temp_dir(), main(), TaskRestartTests, RadioDiagnosticsTests, bootstrap(), create_temp_dir(), main()

### Community 140 - "Frame"
Cohesion: 0.22
Nodes (9): Frame, dst, length, payload, reason, sequence, session, src (+1 more)

### Community 141 - "TaskScheduler"
Cohesion: 0.22
Nodes (4): TaskScheduler::GetTaskCount(), TaskScheduler, task_count_, tasks_

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

### Community 150 - "test_arq.py"
Cohesion: 0.09
Nodes (14): ArqTests, complete(), checked_events(), parse_event(), gateway_status(), reserve_session(), status_complete(), validate_bundle() (+6 more)

### Community 152 - "Gateway-to-Receiver SF7 Hello World"
Cohesion: 0.25
Nodes (7): Current result — Receiver installed, normal startup unresolved, Gateway-to-Receiver SF7 Hello World, No-meter read-only hardware verified; Receiver write wiring unconfirmed, Receiver boot incompatibility, Remaining physical prerequisites, Single-packet behavior and identities, Verified software result

### Community 157 - "C++ Refactoring Baseline"
Cohesion: 0.22
Nodes (7): C++ Refactoring Baseline, Parent-revision measurements, Production and analysis scope, Repository snapshot, Toolchain and limits, Adding and checking libraries, `stable_lib`

### Community 162 - "Wire.h"
Cohesion: 0.22
Nodes (8): Evidence basis, H1 connector, H2 connector and board signals, Pin Mapping Audit — AVR128DA28 / RFM95W, Radio and MCU pins, RF connector path, Verification, begin()

### Community 164 - "PacketAck"
Cohesion: 0.40
Nodes (4): DecodePacketAck(), PacketAck, seq, type

### Community 165 - "PacketAdvertise"
Cohesion: 0.40
Nodes (4): DecodePacketAdvertise(), PacketAdvertise, seq, type

### Community 166 - "LossMetrics"
Cohesion: 0.29
Nodes (7): LossMetrics, ack_tx, attempts, duplicates, nack_tx, retries, timeouts

### Community 169 - "_build_handoff"
Cohesion: 0.22
Nodes (3): build_fixture(), _build_handoff(), page_write_command()

### Community 170 - "PacketMaintenanceAck"
Cohesion: 0.40
Nodes (4): DecodePacketMaintenanceAck(), PacketMaintenanceAck, response, type

### Community 172 - "Tasks"
Cohesion: 0.22
Nodes (9): Tasks, ENABLE_HEARTBEAT_TASK, HEARTBEAT_NAME, HEARTBEAT_OFF_MS, HEARTBEAT_ON_MS, HEARTBEAT_PERIOD_MS, I2C_RESET_SETTLE_MS, LED1_TOGGLE_INTERVAL_MS (+1 more)

### Community 173 - "PacketReportWithAck"
Cohesion: 0.40
Nodes (4): PacketReportWithAck, report, seq, type

### Community 180 - "AVR128DA28 LoRa firmware"
Cohesion: 0.29
Nodes (6): Application configuration, AVR128DA28 LoRa firmware, Build, Host tests, Preserved boundaries, Static analysis and formatting

### Community 186 - "Comm"
Cohesion: 0.25
Nodes (8): Comm, AIR_CONFIG_NODE_ADDR, DEBUG_BAUD_RATE, ENABLE_I2C_WIRE, GATEWAY_ANYCAST_ADDR, GATEWAY_DEFAULT_ADDR, I2C_ADDRESS_BASE, I2C_ADDRESS_STRAP_SHIFT

### Community 188 - "Offline LoRa firmware refactor"
Cohesion: 0.29
Nodes (6): Application and dependency audit, Firmware matrix, Historical BOOT and deployment status, Offline LoRa firmware refactor, Verification, Wire and host evidence

### Community 196 - "RestartTask"
Cohesion: 0.33
Nodes (3): RestartTask, completions, entries

### Community 204 - "core_test.cpp"
Cohesion: 0.38
Nodes (12): absolute_deadline(), ack_matrix(), codec(), control(), data(), fault_harness(), fresh(), main() (+4 more)

### Community 206 - "install_cpp_quality_tools.sh"
Cohesion: 0.50
Nodes (3): find_tool(), PATH, install_cpp_quality_tools.sh script

### Community 207 - "PacketMaintenance"
Cohesion: 0.40
Nodes (4): DecodePacketMaintenance(), PacketMaintenance, command, type

### Community 213 - "Task"
Cohesion: 0.22
Nodes (5): RadioTransactionTask, Task, is_paused_, pt_, wakeup_time_

### Community 214 - "mvp_stub/Arduino.h"
Cohesion: 0.25
Nodes (3): CPUINT(), digitalWrite(), digitalWriteFast()

### Community 220 - "receiver_boot.py"
Cohesion: 0.18
Nodes (9): normalize_ihex_region(), _parse_ihex(), load_package(), prepare(), read_snapshot(), read_snapshot_command(), reset_target(), trace_stub() (+1 more)

### Community 233 - "application_bounds_for_environment"
Cohesion: 0.16
Nodes (12): DirectionalTests, RadioOnlyTests, TargetLayoutTests, application_bounds_for_environment(), build_flag_defines(), _config_int(), effective_project_sections(), radio_profile_compile_flags() (+4 more)

### Community 237 - "ExcludedSx1262Experiment"
Cohesion: 0.10
Nodes (21): 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates, Gateway Hardware SSOT — Rudolph Gateway, H1 (10-pin; only pins 1–5 used in the source schematic) (+13 more)

### Community 299 - "sleep.cpp"
Cohesion: 0.14
Nodes (9): SetUnixTime(), SleepState, force_wakeup, is_sleeping, last_rtc_ticks, unix_time, GetTotalSeconds(), InitializeTime() (+1 more)

### Community 313 - "lora/library.json"
Cohesion: 0.25
Nodes (8): jgromes/RadioLib, build, includeDir, srcDir, dependencies, jgromes/RadioLib@7.1.2, name, version

### Community 315 - "time-utils/library.json"
Cohesion: 0.25
Nodes (8): paulstoffregen/Time, build, includeDir, srcDir, dependencies, paulstoffregen/Time@^1.6.1, name, version

### Community 319 - "usb_inventory.py"
Cohesion: 0.16
Nodes (7): _print_result(), discover_usb_devices(), InventoryResult, _normalize_hex(), parse_udev_properties(), _run_command(), _usb_instance()

### Community 335 - "arduino"
Cohesion: 0.09
Nodes (13): Memory, I2C_MAILBOX_BYTES, SHARED_RINGBUF_BYTES, System, ENABLE_ESPCOMM, ENABLE_LORA_RX, ENABLE_WATCHDOG, WDT_TIMEOUT_PERIOD (+5 more)

### Community 341 - "ใช้งาน Codex Goal — LoRa E2E Feature-Based"
Cohesion: 0.40
Nodes (4): ความต่างระหว่าง Goal กับ config, จุดที่ต้องพิสูจน์, แหล่งอ้างอิง, ใช้งาน Codex Goal — LoRa E2E Feature-Based

### Community 357 - "Hardware"
Cohesion: 0.09
Nodes (3): firmware_role(), Hardware, parked()

## Knowledge Gaps
- **597 isolated node(s):** `startup`, `reset_flags`, `ready`, `deliveries`, `duplicates` (+592 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1575 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **104 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Transport` connect `Transport` to `.EmitEvent`, `EventQueue`, `Pair`, `Result`, `stdint`, `State`, `reliable_transport_test.cpp`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Gate1Tests` (e.g. with `Gate1Audit` and `TracePort`) actually correct?**
  _`Gate1Tests` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `startup`, `reset_flags`, `ready` to the rest of the system?**
  _597 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.0975609756097561 - nodes in this community are weakly interconnected._
- **Why does `SX1276` connect `SX1276` to `Module`, `LoRa`, `stdint`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Should `rf_proof.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14370748299319727 - nodes in this community are weakly interconnected._
- **Why does `SystemConstants` connect `SystemConstants` to `tracker_config.h`, `arduino`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._