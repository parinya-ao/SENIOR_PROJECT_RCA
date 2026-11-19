# Graph Report - SENIOR_PROJECT_RCA  (2026-11-19)

## Corpus Check
- 279 files · ~157,174 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 25 file(s) not represented in the graph (top: (none) 10, .toml 6, .css 4)

## Summary
- 3450 nodes · 6671 edges · 262 communities (152 shown, 110 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 435 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4d9f0195`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- pathlib
- rf_proof.py
- Storage
- reliable_app_test.cpp
- analyze
- mcurses.c
- ReverseRawTests
- CaptureTests
- error
- State
- GNSS
- SystemConstants
- ArqSoakPlanTests
- test_arq.py
- validate_repo_isolation.py
- LoRa
- RadioBringupTests
- Json
- role_log.h
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
- effective_project_sections
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
- diagnostics.cpp
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
- application.cpp
- Tracker Hardware SSOT — LoRa Tracker RFM
- C++ Refactoring Results
- EventQueue
- commands.cpp
- Port
- install
- 915 MHz LoRa bench procedure
- subprocess
- Receiver
- upditerm.py
- role_detector.py
- trace_stub
- updi_probe.py
- SPIClass
- Controller
- stdio
- role_log_test.cpp
- Session
- ErrataDiagnosticsTests
- firmware_identity.py
- assess_exhaustion
- reliable_app.cpp
- sender.cpp
- Pins
- mvp_app.cpp
- Pair
- radio_link.cpp
- ssot_codec.cpp
- ReportEntry
- Gate1Audit
- stub/Arduino.h
- sender/appcode/reliable.cpp
- tracker_config.h
- State
- gate1_live.py
- avr128da28_device.h
- mvp_board.cpp
- Radio915ValidationTests
- AdcTemp
- Json
- ReceiverBootTests
- reliable_transport_test.cpp
- ReliableTransportTests
- ssot_codec.h
- BuildEnvironment
- compare_snapshots
- PacketBoot
- HeartbeatTask
- ErrorCode
- ProvisioningResult
- EventStats
- StableLoraSafetyTests
- radio.cpp
- SdFile
- shutil
- Frame
- TaskScheduler
- validate_live_proof
- Module
- raw_mvp_stub/Arduino.h
- Connect to a virtual UART on an AVR via UPDI
- check_cpp.sh
- gate1.py
- Result
- Gateway-to-Receiver SF7 Hello World
- SenderState
- .test_runner_uses_receiver_ready_then_one_gateway_start
- C++ Refactoring Baseline
- codec.cpp
- Wire.h
- avr128da28_memory_layout.h
- PacketAck
- PacketAdvertise
- LossMetrics
- discover_ports
- _build_handoff
- tracker_radio_packets.h
- SenderStableTransportTests
- Tasks
- PacketReportWithAck
- Revision
- normalize_ihex_region
- .test_rf_enabled_upload_does_not_require_rf_authorization
- string
- DuplicateTracker
- AVR128DA28 LoRa firmware
- RawMvpTests
- Comm
- Offline LoRa firmware refactor
- Fixed settings and checks
- Frame
- CampaignState
- RestartTask
- parse_updi
- ReceiverState
- MonitorConsole
- CppInterfaceTests
- core_test.cpp
- SsotProtocolTests
- install_cpp_quality_tools.sh
- PacketMaintenance
- parse_raw_mvp_logs
- main
- load
- mvp_stub/Arduino.h
- Json
- SingleFirmwareEntryTests
- application_bounds_for_environment
- ExcludedSx1262Experiment
- Result
- sleep.cpp
- lora
- State
- .EmitEvent
- lora/library.json
- time-utils/library.json
- usb_inventory.py
- arduino
- ใช้งาน Codex Goal — LoRa E2E Feature-Based
- Suggested append-only AGENTS.md contract (merge; do not overwrite existing instructions)
- Hardware

## God Nodes (most connected - your core abstractions)
1. `Transport` - 64 edges
2. `SystemConstants` - 46 edges
3. `Gate1Tests` - 45 edges
4. `State` - 45 edges
5. `Hardware` - 36 edges
6. `HardwareGateTests` - 36 edges
7. `analyze()` - 35 edges
8. `Sender` - 33 edges
9. `RCATests` - 33 edges
10. `error()` - 32 edges

## Surprising Connections (you probably didn't know these)
- `Application and dependency audit` --references--> `LoRa`  [INFERRED]
  docs/refactoring/OFFLINE_LORA.md → src/features/radio_link/radio_link.h
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

## Communities (262 total, 110 thin omitted)

### Community 0 - "pathlib"
Cohesion: 0.08
Nodes (4): GatewayI2cTests, TaskRestartTests, RadioDiagnosticsTests, RadioLibHalTests

### Community 1 - "rf_proof.py"
Cohesion: 0.16
Nodes (26): application_layout_verified(), authorized_application_pages(), capture_usb_topology(), check_port_owners(), clean_builds(), firmware_measurement(), host_tests(), identify_targets() (+18 more)

### Community 2 - "Storage"
Cohesion: 0.08
Nodes (12): Storage, _first, _raw, _start_block, Storage<T>::clear(), Storage<T>::_load_state(), Storage<T>::peek(), Storage<T>::pop() (+4 more)

### Community 3 - "reliable_app_test.cpp"
Cohesion: 0.23
Nodes (7): updi_role_log_dropped(), command(), complete_tx(), deliver(), main(), updi_uart_try_tx(), updi_uart_tx()

### Community 5 - "mcurses.c"
Cohesion: 0.13
Nodes (35): addch(), addstr(), addstr_P(), attrset(), clear(), clrtobot(), clrtoeol(), curs_set() (+27 more)

### Community 6 - "ReverseRawTests"
Cohesion: 0.20
Nodes (4): ReverseRawTests, audit_raw_configuration(), reverse_exchange(), status()

### Community 7 - "CaptureTests"
Cohesion: 0.06
Nodes (3): CaptureTests, command(), monotonic()

### Community 8 - "error"
Cohesion: 0.18
Nodes (15): error(), Capture, complete(), park_reverse(), prepare(), radio_only_bringup(), reader_free_h01(), drain_tracker() (+7 more)

### Community 9 - "State"
Cohesion: 0.04
Nodes (45): State, airtime_length, airtime_us, bandwidth_khz, begin_calls, begin_status, chip_version, coding_rate (+37 more)

### Community 10 - "GNSS"
Cohesion: 0.07
Nodes (23): calculate_checksum(), extract_field(), GNSS, day, fixquality, _gga_received, GNSS::GNSS(), hour (+15 more)

### Community 11 - "SystemConstants"
Cohesion: 0.04
Nodes (45): SystemConstants, ADC_RESOLUTION_STEPS, ADC_VREF_MV, BOOT_DELAY_MS, BOOT_SENTINEL_COORD, BOOT_SENTINEL_VBAT_MV, DEBUG_SERIAL_BAUD, DEVICE_MODEL (+37 more)

### Community 12 - "ArqSoakPlanTests"
Cohesion: 0.11
Nodes (9): ArqSoakPlanTests, fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), confirmed_rf_preflight(), dynamic_attr() (+1 more)

### Community 13 - "test_arq.py"
Cohesion: 0.09
Nodes (15): SourceFingerprintTests, arq_artifacts(), load_arq(), validate_arq(), artifacts(), canonical(), digest(), generate() (+7 more)

### Community 14 - "validate_repo_isolation.py"
Cohesion: 0.25
Nodes (11): _check_config(), _check_symlink(), _inside(), _items(), _label(), _local_dependency(), main(), _resolved() (+3 more)

### Community 15 - "LoRa"
Cohesion: 0.12
Nodes (12): 1. Mandatory first phase: read-only inventory and graph analysis, LoRa, _active, _hardware, _initialized, _last_rssi, _module, _my_addr (+4 more)

### Community 16 - "RadioBringupTests"
Cohesion: 0.08
Nodes (7): DirectionalHostTests, RadioBringupTests, acquire(), command(), audit_radio_configuration(), read_radio(), validate_hello_exchange()

### Community 17 - "Json"
Cohesion: 0.09
Nodes (22): build_soak_plan(), campaign(), progress(), run_one(), checked_events(), hardware_gate_errors(), hello_airtime_budget(), lora_time_on_air_us() (+14 more)

### Community 18 - "role_log.h"
Cohesion: 0.14
Nodes (28): FlushTransportEvent(), HandleRadioCommand(), Poll(), ReportBoot(), ReportStatus(), InitializeRadio(), SendWrongDestination(), Poll() (+20 more)

### Community 19 - "rf_proof.py"
Cohesion: 0.07
Nodes (30): RfTestContinuationTests, boot_fuses_match(), capture_radio_spi_log(), parse_radio_spi_log(), parse_rf_campaign(), parse_role_log_count(), parse_wrapper_check_count(), radio_startup_matches() (+22 more)

### Community 22 - "stdint"
Cohesion: 0.08
Nodes (16): Memory, I2C_MAILBOX_BYTES, SHARED_RINGBUF_BYTES, System, ENABLE_ESPCOMM, ENABLE_LORA_RX, ENABLE_WATCHDOG, WDT_TIMEOUT_PERIOD (+8 more)

### Community 24 - "Transport"
Cohesion: 0.05
Nodes (30): Transport, armed_, context_, error_, event_context_, frequency_, have_accepted_, kMaxData (+22 more)

### Community 26 - "Gate1Tests"
Cohesion: 0.12
Nodes (3): Gate1Tests, rows(), transaction()

### Community 28 - "load"
Cohesion: 0.11
Nodes (7): ConfigurationTests, ReceiverHardwareTests, checked_cpp(), load(), main(), unique_object(), validate()

### Community 29 - "gateway_app.cpp"
Cohesion: 0.06
Nodes (18): I2cCommandTask, command_, command_length_, I2cResetTask, timestamp_ms_, InitializeEspCommunication(), StoreI2c16(), Initialize() (+10 more)

### Community 30 - "ReaderFreeH01SummaryTests"
Cohesion: 0.10
Nodes (5): ArqTests, ReaderFreeH01SummaryTests, main(), open_reader_free_h01_session(), reader_free_rx_idle_summary()

### Community 31 - "._run_capture"
Cohesion: 0.18
Nodes (4): LiveProofTests, emit(), start(), write()

### Community 32 - "Campaign"
Cohesion: 0.14
Nodes (17): Campaign, attempts, campaign_id, destination, sequence, single_packet, source, state (+9 more)

### Community 34 - "ring_buffer.h"
Cohesion: 0.09
Nodes (11): RingBuffer, buffer_, RingBuffer<Capacity>::Read(), RingBuffer<Capacity>::ReadByte(), RingBuffer<Capacity>::Write(), RingBuffer<Capacity>::WriteByte(), RingBuffer<Capacity>::WriteFrame(), first_free_ (+3 more)

### Community 35 - "Logger"
Cohesion: 0.15
Nodes (10): Logger, _capacity, _cursor, _raw, _start_block, ui64toa(), RawStorage, _cached_block (+2 more)

### Community 36 - "tracker_radio_codec.cpp"
Cohesion: 0.19
Nodes (20): DecodeConfig(), DecodePacketBoot(), DecodePacketReport(), DecodeReportEntry(), EncodeConfig(), EncodePacketAck(), EncodePacketAdvertise(), EncodePacketBoot() (+12 more)

### Community 37 - "detect_devices.py"
Cohesion: 0.17
Nodes (12): build_parser(), _load_registry(), main(), _probe_device(), _run_self_test(), SafetyArgumentParser, _scan(), _watch() (+4 more)

### Community 38 - "effective_project_sections"
Cohesion: 0.27
Nodes (7): build_flag_defines(), effective_project_sections(), radio_profile_compile_flags(), rf_spi_diagnostic_config(), shared_rf_profile(), upload_config_preserves_flash(), valid_rf_profile_config()

### Community 39 - "EventId"
Cohesion: 0.05
Nodes (41): Component, kApplication, kBoot, kHil, kNvm, Event(), EventId, kAuthenticationStarted (+33 more)

### Community 41 - "ScanResult"
Cohesion: 0.12
Nodes (4): DetectedDevice, ScanResult, format_text(), result_to_json()

### Community 42 - "reverse_raw_app.cpp"
Cohesion: 0.42
Nodes (10): ExecuteCommand(), FeedCommandByte(), IsPayloadCommand(), ParkRadio(), Poll(), ReadStableCounter(), RecordConfiguration(), RecordEvent() (+2 more)

### Community 43 - "ControlInput"
Cohesion: 0.22
Nodes (9): ControlInput, command, digits, last_ms, reading, triggered, value, ssot::ControlInputFeed() (+1 more)

### Community 44 - "image_evidence"
Cohesion: 0.16
Nodes (8): wire(), event(), image_evidence(), journal(), StableTransportProofTests, wrong_destination_journal(), assess(), validate_stable_transport()

### Community 45 - "DeviceLayout"
Cohesion: 0.12
Nodes (18): DeviceLayout, kAppDataStart, kApplicationEnd, kApplicationImageEnd, kApplicationStart, kBootEnd, kBootSizePages, kBootStart (+10 more)

### Community 47 - "Bus"
Cohesion: 0.08
Nodes (10): Bus, fifo, finish_delay, regs, reset_mode, ticks, main(), TraceBus (+2 more)

### Community 48 - "require"
Cohesion: 0.11
Nodes (4): DetectionIntegrationTests, pio(), runner(), require()

### Community 49 - "TracePort"
Cohesion: 0.09
Nodes (3): instrument(), open_exclusive(), TracePort

### Community 50 - "directional_test.cpp"
Cohesion: 0.18
Nodes (13): FeedCommandByte(), drain_status(), main(), send_command(), QueuedLogLine(), ResetLog(), clear_log(), cmd() (+5 more)

### Community 51 - "diagnostics.cpp"
Cohesion: 0.17
Nodes (11): EventContext, AcquireLine(), FlushByte(), OverflowCount(), PendingLineCount(), RecordDiscard(), RecordEvent(), RecordFrame() (+3 more)

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

### Community 57 - "task.cpp"
Cohesion: 0.20
Nodes (6): Task::Task(), Task, is_paused_, pt_, wakeup_time_, main()

### Community 58 - "FakeRadio"
Cohesion: 0.09
Nodes (17): FakeRadio, bytes, campaign_id, completion_error, destination, done, incoming, incoming_campaign_id (+9 more)

### Community 59 - "ReceiveTests"
Cohesion: 0.13
Nodes (3): ReceiveTests, wait(), wait()

### Community 60 - "Sender"
Cohesion: 0.10
Nodes (20): Sender, armed, attempts, frame, has_start, interval, last_start, result (+12 more)

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
Cohesion: 0.10
Nodes (19): ApplicationConfigTests, capture_tracker_diagnostics(), close_updi_without_recovery(), diagnostic_case(), drain_updi_messages(), read_reset_state(), tracker_command(), resync_reset_state_once() (+11 more)

### Community 66 - "HardwareGateTests"
Cohesion: 0.05
Nodes (8): BuildAcceptanceTests, dynamic_attr(), effective_platformio_config(), FlashSafetyTests, HardwareGateTests, command(), hardware_blockers(), parse_test_counts()

### Community 67 - "require"
Cohesion: 0.09
Nodes (15): DeviceReconnectTests, make_device(), make_probe(), require(), crc8(), FirmwareIdentityTests, ihex_record(), marker() (+7 more)

### Community 68 - "OPERATING CONTRACT — READ ALL BEFORE EDITING"
Cohesion: 0.13
Nodes (14): 0. Target, boundaries, priorities, 10. Mandatory negative and protocol matrix, 11. Acceptance criteria — NOT negotiable, 12. Agentic self-repair loop — persistent, evidence-driven, bounded, 13. First actions — execute in this exact order, 2. Reference repo: behavior parity without copying defects, 3. IMPORTANT RADIO FACT: SX127x `setNodeAddress`, 4. Test FIRST using real radios, BEFORE migration (+6 more)

### Community 69 - "Config"
Cohesion: 0.11
Nodes (18): Config, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 70 - "application.cpp"
Cohesion: 0.25
Nodes (19): ArmSession(), CurrentSession(), ExecuteCommand(), FailAdapter(), FlushStatus(), GetEventContext(), HandleReceive(), Initialize() (+11 more)

### Community 71 - "Tracker Hardware SSOT — LoRa Tracker RFM"
Cohesion: 0.22
Nodes (9): 1. Board identity and components, 2. AVR128DA28 pin and net SSOT, 3. Power and startup contract, 4. Minimal firmware implementation contract, 5. Acceptance criteria / physical evidence, 6. Firmware configuration, Exact LoRa RFM95W signal map, Sources (+1 more)

### Community 72 - "C++ Refactoring Results"
Cohesion: 0.22
Nodes (8): A — Action, C++ Refactoring Results, R — Result, S — Situation, T — Task, Trade-offs and limits, SleepFor(), PowerSavingTaskScheduler

### Community 73 - "EventQueue"
Cohesion: 0.11
Nodes (15): Event, campaign_id, error, name, sequence, time_ms, type, EventQueue (+7 more)

### Community 74 - "commands.cpp"
Cohesion: 0.08
Nodes (26): Command, budget, kind, payload, payload_length, session, stride, CommandInput (+18 more)

### Community 75 - "Port"
Cohesion: 0.21
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 76 - "install"
Cohesion: 0.22
Nodes (7): add(), boot(), BootPackageTests, recording_command(), install(), load_package(), sha()

### Community 80 - "915 MHz LoRa bench procedure"
Cohesion: 0.29
Nodes (6): 915 MHz LoRa bench procedure, App-only programming after exact write approval, Hardware results, Refactor verification, RF conditions and acceptance, Verified candidates

### Community 81 - "subprocess"
Cohesion: 0.25
Nodes (9): capture_host_commands(), check(), complexity_check(), firmware_checks(), main(), record(), resolve_tools(), run() (+1 more)

### Community 82 - "Receiver"
Cohesion: 0.15
Nodes (13): Receiver, accepted, armed, deliveries, duplicates, expected, last_sequence, session (+5 more)

### Community 83 - "upditerm.py"
Cohesion: 0.14
Nodes (4): BootAnalysisTests, parse_arguments(), analyze(), main()

### Community 84 - "role_detector.py"
Cohesion: 0.18
Nodes (7): USBDevice, classify_devices(), diff_device_presence(), _identity_role(), _probe_for(), _registry_hint(), _registry_record()

### Community 85 - "trace_stub"
Cohesion: 0.22
Nodes (3): CompiledHandoffTests, reset_target(), trace_stub()

### Community 86 - "updi_probe.py"
Cohesion: 0.22
Nodes (8): identify_mcu(), _is_access_error(), _port_busy(), probe_firmware_identity(), probe_target_sib(), read_firmware_flash(), _require_safe(), _run_bounded()

### Community 87 - "SPIClass"
Cohesion: 0.14
Nodes (3): SPIClass, SPISettings, beginTransaction()

### Community 90 - "Controller"
Cohesion: 0.13
Nodes (12): Controller, last_led1_toggle_, last_tx_toggle_, led1_interval_ms_, led1_on_, led1_pin_, led2_pin_, led_off_level_ (+4 more)

### Community 91 - "stdio"
Cohesion: 0.13
Nodes (3): main(), reset_radio(), main()

### Community 96 - "role_log_test.cpp"
Cohesion: 0.10
Nodes (7): DecodeLoraConfig(), EepromSpy, reads, writes, main(), clear_capture(), main()

### Community 97 - "Session"
Cohesion: 0.11
Nodes (3): Console, main(), Session

### Community 98 - "ErrataDiagnosticsTests"
Cohesion: 0.12
Nodes (5): ErrataDiagnosticsTests, decode_snapshot(), interpret_rx(), link_budget(), main()

### Community 99 - "firmware_identity.py"
Cohesion: 0.17
Nodes (8): FirmwareIdentity, crc8(), FingerprintResult, IdentityParseResult, match_flash_fingerprint(), parse_identity_stream(), _valid_build(), _valid_timestamp()

### Community 102 - "reliable_app.cpp"
Cohesion: 0.18
Nodes (5): AcceptData(), ArmRadio(), Initialize(), InitializeGpio(), RecordTransportEvent()

### Community 103 - "sender.cpp"
Cohesion: 0.20
Nodes (10): arq::ArmSender(), arq::HandleControlFrame(), arq::HandleTxCompletion(), arq::InitSender(), arq::IsSenderActive(), arq::PollSender(), arq::RequestTransmission(), arq::StopSender() (+2 more)

### Community 105 - "Pins"
Cohesion: 0.14
Nodes (14): Pins, ANALOG_IN_0, ANALOG_IN_1, DEBUG_RX, DEBUG_TX, HOST_INT, LED1, LED2 (+6 more)

### Community 106 - "mvp_app.cpp"
Cohesion: 0.37
Nodes (12): debug_init(), debug_write(), debug_write_float(), debug_write_hex(), debug_write_int(), Initialize(), Poll(), RecordStartupStage() (+4 more)

### Community 107 - "Pair"
Cohesion: 0.15
Nodes (12): Application, applied, reject, Pair, a, aa, b, bb (+4 more)

### Community 110 - "ssot_codec.cpp"
Cohesion: 0.33
Nodes (8): DecodePayloadFields(), EncodeControlPayload(), ssot::AckMatches(), ssot::DecodeFrame(), ssot::DecodePayload(), ssot::EncodeAckPayload(), ssot::EncodeNackPayload(), DecodeRadioHeader()

### Community 111 - "ReportEntry"
Cohesion: 0.14
Nodes (22): ReportEntry, day, hour, latitude, longitude, minute, month, quality (+14 more)

### Community 114 - "sender/appcode/reliable.cpp"
Cohesion: 0.18
Nodes (4): HandleRoleCommand(), PollRoleRadio(), PollWrongDestination(), RequestData()

### Community 115 - "tracker_config.h"
Cohesion: 0.33
Nodes (6): Checkpoint, INVALID_GNSS_DATE, SPI_CTRL_BEFORE_LORA, SPI_CTRL_BEFORE_PWR_ON, TRACKER_AFTER_GNSS_ON, TRACKER_BEFORE_GNSS_ON

### Community 117 - "State"
Cohesion: 0.17
Nodes (12): State, begin_count, cs_high_seen, cs_low_seen, cs_pin, initialized, route, swap_count (+4 more)

### Community 119 - "gate1_live.py"
Cohesion: 0.17
Nodes (24): controlled_cpu_reset(), firmware_identity_from_events(), gpr_roundtrip_succeeded(), halted_gpr_roundtrip(), mailbox_snapshot(), main(), _parse_block(), part_from_signature() (+16 more)

### Community 120 - "avr128da28_device.h"
Cohesion: 0.15
Nodes (12): IsAppCodeRange(), PORT_struct, PORT_t, SPI_struct, SPI_t, TWI_struct, TWI_t, TwiHold (+4 more)

### Community 121 - "mvp_board.cpp"
Cohesion: 0.23
Nodes (5): delay(), main(), pump(), state_name(), step()

### Community 122 - "Radio915ValidationTests"
Cohesion: 0.17
Nodes (3): Radio915ValidationTests, valid_profile(), write_toml()

### Community 123 - "AdcTemp"
Cohesion: 0.17
Nodes (12): AdcTemp, ADC_MAX_COUNTS, CTRLA_ENABLE_12BIT, FIXED_POINT_SHIFT, INIT_DELAY_SETTING, KELVIN_TO_CELSIUS, MUX_TEMP_CHANNEL, PRESCALER_SETTING (+4 more)

### Community 124 - "Json"
Cohesion: 0.11
Nodes (3): fixture(), I2cRadioConfigTests, ihex_record()

### Community 126 - "reliable_transport_test.cpp"
Cohesion: 0.36
Nodes (9): count_transition(), deliver(), dropped(), finish_reply(), loss_scenario(), main(), start_data(), stress_round_trips() (+1 more)

### Community 128 - "ssot_codec.h"
Cohesion: 0.20
Nodes (7): ssot::EncodeAckFrame(), ssot::EncodeDataFrame(), EncodeRadioHeader(), RadioHeader, campaign_id, destination, source

### Community 130 - "compare_snapshots"
Cohesion: 0.17
Nodes (3): classify(), compare_snapshots(), delta()

### Community 131 - "PacketBoot"
Cohesion: 0.25
Nodes (7): PacketBoot, checkpoint, config, device_model, firmware, reset_flags, type

### Community 133 - "ErrorCode"
Cohesion: 0.20
Nodes (10): ErrorCode, CONFIG_FILE_READ_FAILED, CONFIG_PART_NOT_FOUND, CONFIG_VOL_INIT_FAILED, DATA_PARTITION_NOT_FOUND, LOG_PARTITION_NOT_FOUND, LOGGER_SETUP_FAILED, LORA_INIT_FAILED (+2 more)

### Community 134 - "ProvisioningResult"
Cohesion: 0.25
Nodes (9): ProvisioningResult, kInvalidArgument, kOk, kUnprovisioned, kUnsupported, IsHmacKeyProvisioned(), ReadDeviceUid(), ReadHmacKey() (+1 more)

### Community 135 - "EventStats"
Cohesion: 0.18
Nodes (11): EventStats, ack_accepted, ack_tx, data_tx, destination_discards, duplicates, failures, nack_received (+3 more)

### Community 137 - "radio.cpp"
Cohesion: 0.24
Nodes (6): arq_board, InitializeRadio(), ReadRadioRegister(), PrepareTrackerForRadioOnly(), board_ssot_init(), Initialize()

### Community 138 - "SdFile"
Cohesion: 0.14
Nodes (9): get_data_and_log_partitions(), open_file_in_root(), read_line(), SdFile, data_, length_, position_, SdVolume (+1 more)

### Community 139 - "shutil"
Cohesion: 0.36
Nodes (6): bootstrap(), create_temp_dir(), main(), bootstrap(), create_temp_dir(), main()

### Community 140 - "Frame"
Cohesion: 0.22
Nodes (9): Frame, dst, length, payload, reason, sequence, session, src (+1 more)

### Community 141 - "TaskScheduler"
Cohesion: 0.25
Nodes (4): TaskScheduler::GetTaskCount(), TaskScheduler, task_count_, tasks_

### Community 143 - "validate_live_proof"
Cohesion: 0.38
Nodes (4): complete_campaign_logs(), packet_event(), payload_event(), RfEvidenceTests

### Community 145 - "raw_mvp_stub/Arduino.h"
Cohesion: 0.27
Nodes (5): begin(), digitalWrite(), end(), ltoa(), push_back()

### Community 148 - "Connect to a virtual UART on an AVR via UPDI"
Cohesion: 0.22
Nodes (8): Connect to a virtual UART on an AVR via UPDI, Demo program, License, Prerequisites, UPDI interface, Upditerm, Usage, Virtual UART

### Community 149 - "check_cpp.sh"
Cohesion: 0.70
Nodes (4): PATH, record_support(), run_support(), check_cpp.sh script

### Community 150 - "gate1.py"
Cohesion: 0.17
Nodes (4): assess(), response(), _status(), verify_hashes()

### Community 151 - "Result"
Cohesion: 0.29
Nodes (7): Result, kOk, kPending, kProtocolError, kRadioError, kRejected, kTimeoutExhausted

### Community 152 - "Gateway-to-Receiver SF7 Hello World"
Cohesion: 0.25
Nodes (7): Current result — Receiver installed, normal startup unresolved, Gateway-to-Receiver SF7 Hello World, No-meter read-only hardware verified; Receiver write wiring unconfirmed, Receiver boot incompatibility, Remaining physical prerequisites, Single-packet behavior and identities, Verified software result

### Community 154 - "SenderState"
Cohesion: 0.29
Nodes (7): SenderState, kBackoff, kDelivered, kFailed, kIdle, kTransmitting, kWaitingAck

### Community 157 - "C++ Refactoring Baseline"
Cohesion: 0.22
Nodes (7): C++ Refactoring Baseline, Parent-revision measurements, Production and analysis scope, Repository snapshot, Toolchain and limits, Adding and checking libraries, `stable_lib`

### Community 160 - "codec.cpp"
Cohesion: 0.60
Nodes (3): arq::DecodeFrame(), arq::EncodeFrame(), arq::IsValidFrame()

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

### Community 170 - "tracker_radio_packets.h"
Cohesion: 0.17
Nodes (8): DecodePacketMaintenanceAck(), PacketMaintenanceAck, response, type, PacketReport, report, seq, type

### Community 172 - "Tasks"
Cohesion: 0.22
Nodes (9): Tasks, ENABLE_HEARTBEAT_TASK, HEARTBEAT_NAME, HEARTBEAT_OFF_MS, HEARTBEAT_ON_MS, HEARTBEAT_PERIOD_MS, I2C_RESET_SETTLE_MS, LED1_TOGGLE_INTERVAL_MS (+1 more)

### Community 173 - "PacketReportWithAck"
Cohesion: 0.33
Nodes (5): DecodePacketReportWithAck(), PacketReportWithAck, report, seq, type

### Community 174 - "Revision"
Cohesion: 0.50
Nodes (4): Revision, major, minor, raw_revision_id

### Community 175 - "normalize_ihex_region"
Cohesion: 0.20
Nodes (4): BuildIdentityImagesTests, normalize_ihex_region(), _parse_ihex(), prepare()

### Community 179 - "DuplicateTracker"
Cohesion: 0.25
Nodes (9): DuplicateTracker, campaign_id, initialized, seen, source, ResetDuplicateSession(), ssot::DuplicateTrackerInit(), ssot::DuplicateTrackerObserve() (+1 more)

### Community 180 - "AVR128DA28 LoRa firmware"
Cohesion: 0.29
Nodes (6): Application configuration, AVR128DA28 LoRa firmware, Build, Host tests, Preserved boundaries, Static analysis and formatting

### Community 186 - "Comm"
Cohesion: 0.25
Nodes (8): Comm, AIR_CONFIG_NODE_ADDR, DEBUG_BAUD_RATE, ENABLE_I2C_WIRE, GATEWAY_ANYCAST_ADDR, GATEWAY_DEFAULT_ADDR, I2C_ADDRESS_BASE, I2C_ADDRESS_STRAP_SHIFT

### Community 188 - "Offline LoRa firmware refactor"
Cohesion: 0.33
Nodes (5): Application and dependency audit, Firmware matrix, Historical BOOT and deployment status, Offline LoRa firmware refactor, Wire and host evidence

### Community 189 - "Fixed settings and checks"
Cohesion: 0.40
Nodes (4): Fixed settings and checks, Runtime settings, Scope, Tracker Configuration SSOT

### Community 190 - "Frame"
Cohesion: 0.33
Nodes (6): Frame, campaign_id, destination, sequence, source, type

### Community 194 - "CampaignState"
Cohesion: 0.33
Nodes (6): CampaignState, kArmed, kCompleted, kFailed, kIdle, kRunning

### Community 196 - "RestartTask"
Cohesion: 0.33
Nodes (3): RestartTask, completions, entries

### Community 200 - "ReceiverState"
Cohesion: 0.40
Nodes (5): ReceiverState, kListening, kReturningToRx, kSendingResponse, kValidating

### Community 204 - "core_test.cpp"
Cohesion: 0.38
Nodes (12): absolute_deadline(), ack_matrix(), codec(), control(), data(), fault_harness(), fresh(), main() (+4 more)

### Community 206 - "install_cpp_quality_tools.sh"
Cohesion: 0.50
Nodes (3): find_tool(), PATH, install_cpp_quality_tools.sh script

### Community 207 - "PacketMaintenance"
Cohesion: 0.40
Nodes (4): DecodePacketMaintenance(), PacketMaintenance, command, type

### Community 214 - "mvp_stub/Arduino.h"
Cohesion: 0.25
Nodes (3): CPUINT(), digitalWrite(), digitalWriteFast()

### Community 220 - "Json"
Cohesion: 0.26
Nodes (4): read_snapshot(), read_snapshot_command(), require_preserved(), verify_live_receipt()

### Community 233 - "application_bounds_for_environment"
Cohesion: 0.19
Nodes (6): DirectionalTests, RadioOnlyTests, TargetLayoutTests, application_bounds_for_environment(), _config_int(), target_fuses()

### Community 237 - "ExcludedSx1262Experiment"
Cohesion: 0.10
Nodes (21): 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates, Gateway Hardware SSOT — Rudolph Gateway, H1 (10-pin; only pins 1–5 used in the source schematic) (+13 more)

### Community 260 - "Result"
Cohesion: 0.22
Nodes (8): Result, kAccepted, kAckTimeout, kInvalidArgument, kPending, kRadioError, kRejected, kTxTimeout

### Community 299 - "sleep.cpp"
Cohesion: 0.14
Nodes (9): SetUnixTime(), SleepState, force_wakeup, is_sleeping, last_rtc_ticks, unix_time, GetTotalSeconds(), InitializeTime() (+1 more)

### Community 304 - "State"
Cohesion: 0.22
Nodes (8): State, kComplete, kFailed, kRetryPending, kRxWait, kTxData, kTxResponse, kWaitResponse

### Community 313 - "lora/library.json"
Cohesion: 0.25
Nodes (8): jgromes/RadioLib, build, includeDir, srcDir, dependencies, jgromes/RadioLib@7.1.2, name, version

### Community 315 - "time-utils/library.json"
Cohesion: 0.25
Nodes (8): paulstoffregen/Time, build, includeDir, srcDir, dependencies, paulstoffregen/Time@^1.6.1, name, version

### Community 319 - "usb_inventory.py"
Cohesion: 0.12
Nodes (8): _print_result(), discover_usb_devices(), InventoryResult, _normalize_hex(), parse_udev_properties(), _run_command(), start_udev_monitor(), _usb_instance()

### Community 335 - "arduino"
Cohesion: 0.14
Nodes (4): ReportRoleReadyAtStartup(), Initialize(), InitializeRadio(), InitializeReceiverGpio()

### Community 341 - "ใช้งาน Codex Goal — LoRa E2E Feature-Based"
Cohesion: 0.40
Nodes (4): ความต่างระหว่าง Goal กับ config, จุดที่ต้องพิสูจน์, แหล่งอ้างอิง, ใช้งาน Codex Goal — LoRa E2E Feature-Based

## Knowledge Gaps
- **574 isolated node(s):** `day`, `fixquality`, `_gga_received`, `hour`, `latitude` (+569 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1565 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **110 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `State` connect `State` to `stdint`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **What connects `day`, `fixquality`, `_gga_received` to the rest of the system?**
  _574 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.07650273224043716 - nodes in this community are weakly interconnected._
- **Why does `LoRa` connect `LoRa` to `radio_link.cpp`, `SX1276`, `Offline LoRa firmware refactor`, `Module`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Should `Storage` be split into smaller, more focused modules?**
  _Cohesion score 0.08108108108108109 - nodes in this community are weakly interconnected._
- **Why does `Transport` connect `Transport` to `Result`, `reliable_app.cpp`, `EventQueue`, `Pair`, `State`, `.EmitEvent`, `reliable_transport_test.cpp`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Should `analyze` be split into smaller, more focused modules?**
  _Cohesion score 0.14245014245014245 - nodes in this community are weakly interconnected._