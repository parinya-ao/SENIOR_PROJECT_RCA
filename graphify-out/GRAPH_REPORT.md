# Graph Report - SENIOR_PROJECT_RCA  (2026-11-18)

## Corpus Check
- 278 files · ~150,977 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: (none) 10, .toml 6, .ini 2)

## Summary
- 3383 nodes · 6557 edges · 243 communities (140 shown, 103 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 432 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `380e8f70`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- pathlib
- rf_proof.py
- Storage
- arq_trial.py
- analyze
- mcurses.c
- parse_event
- CaptureTests
- Json
- State
- GNSS
- SystemConstants
- ArqSoakPlanTests
- generate_lora_config.py
- validate_repo_isolation.py
- LoRa
- RadioBringupTests
- RawStorage
- role_log.h
- validate_live_proof
- ControlInput
- receiver_boot.py
- Transport
- Receiver
- Gate1Tests
- RepositoryIsolationTests
- load
- gateway_radio.cpp
- main
- ._run_capture
- application.cpp
- Gate1Audit
- Logger
- ring_buffer.h
- detect_devices.py
- require
- EventId
- SX1276
- ScanResult
- reverse_raw_app.cpp
- DeviceLayout
- image_evidence
- PlatformResult
- Campaign
- Bus
- require
- TracePort
- ReverseRawTests
- diagnostics.h
- AGENTS.md — AVR128DA28 / LoRa Embedded Engineering
- symmetric_fixture
- upditerm.py
- TrackerConfig
- Task
- FakeRadio
- ReceiveTests
- assess
- DebugConsoleTests
- Config
- reliable_app_test.cpp
- MvpRoundtripTests
- load
- HardwareGateTests
- require
- OPERATING CONTRACT — READ ALL BEFORE EDITING
- RfTestContinuationTests
- check_cpp.py
- Tracker Hardware SSOT — LoRa Tracker RFM
- SD.h
- EventQueue
- radio_link.cpp
- Port
- test_device_reconnect.py
- Comm
- diagnostics.cpp
- 915 MHz LoRa bench procedure
- device.h
- src/codec.cpp
- role_detector.py
- Frame
- System
- arq/codec.cpp
- compare_snapshots
- reverse_raw_test.cpp
- Controller
- shutil
- string
- role_log_test.cpp
- Session
- ErrataDiagnosticsTests
- firmware_identity.py
- Json
- board_ssot.h
- Pins
- mvp_app.cpp
- Pair
- parse_updi
- probe_firmware_identity
- ReportEntry
- time-utils/time-utils.h
- GatewayI2cTests
- SleepState
- tracker_config.h
- State
- SenderState
- gate1_live.py
- Result
- commands.h
- RadioLibHalTests
- STATIC_ANALYSIS.md
- Tasks
- reliable_transport_test.cpp
- ReliableTransportTests
- Command
- BuildEnvironment
- Revision
- ErrorCode
- ProvisioningResult
- EventStats
- StableLoraSafetyTests
- main
- SdFile
- load
- COMMENT_POLICY.md
- PacketBoot
- CPP_STYLE.md
- validate_live_proof
- Module
- stub/Arduino.h
- Connect to a virtual UART on an AVR via UPDI
- check_cpp.sh script
- RadioDiagnosticsTests
- Gateway-to-Receiver SF7 Hello World
- ssot/codec.cpp
- Frame
- test_radio_915_ssot.py
- .test_runner_uses_receiver_ready_then_one_gateway_start
- Wire.h
- ReceiverState
- TraceBus
- LossMetrics
- discover_ports
- AdcTemp
- SenderStableTransportTests
- .test_rf_enabled_upload_does_not_require_rf_authorization
- stdint
- packets.h
- AVR128DA28 LoRa firmware
- RawMvpTests
- .test_T36_wide_gpr_counterfactual_uses_16_bit_sts_only_for_gprs
- PacketAck
- PacketAdvertise
- memory_layout.h
- MonitorConsole
- CppInterfaceTests
- core_test.cpp
- SsotProtocolTests
- install_cpp_quality_tools.sh
- mvp_stub/Arduino.h
- BuildIdentityImagesTests
- SingleFirmwareEntryTests
- Sender
- application_bounds_for_environment
- PacketMaintenance
- ExcludedSx1262Experiment
- Result
- arduino
- sleep.cpp
- lora
- State
- .EmitEvent
- lora/library.json
- time-utils/library.json
- usb_inventory.py
- stdio
- PacketMaintenanceAck
- ใช้งาน Codex Goal — LoRa E2E Feature-Based
- PacketReportWithAck
- Suggested append-only AGENTS.md contract (merge; do not overwrite existing instructions)
- Hardware

## God Nodes (most connected - your core abstractions)
1. `Transport` - 64 edges
2. `SystemConstants` - 46 edges
3. `Gate1Tests` - 46 edges
4. `State` - 45 edges
5. `Hardware` - 36 edges
6. `HardwareGateTests` - 36 edges
7. `analyze()` - 35 edges
8. `Sender` - 34 edges
9. `RCATests` - 33 edges
10. `error()` - 32 edges

## Surprising Connections (you probably didn't know these)
- `Scope` --references--> `TrackerConfig`  [INFERRED]
  TRACKER_CONFIG_SSOT.md → include/tracker_config.h
- `Fixed settings and checks` --references--> `SystemConstants`  [INFERRED]
  TRACKER_CONFIG_SSOT.md → include/tracker_config.h
- `Radio SPI and interrupt contract` --references--> `ExcludedSx1262Experiment`  [INFERRED]
  GATEWAY_SSOT.md → include/gateway_ssot.hpp
- `Fixed settings and checks` --references--> `TrackerConfig`  [INFERRED]
  TRACKER_CONFIG_SSOT.md → include/tracker_config.h
- `Fixed settings and checks` --references--> `ErrorCode`  [INFERRED]
  TRACKER_CONFIG_SSOT.md → include/tracker_config.h

## Import Cycles
- None detected.

## Communities (243 total, 103 thin omitted)

### Community 1 - "rf_proof.py"
Cohesion: 0.11
Nodes (43): application_layout_verified(), authorized_application_pages(), boot_fuses_match(), capture_radio_spi_log(), capture_usb_topology(), check_port_owners(), clean_builds(), firmware_measurement() (+35 more)

### Community 2 - "Storage"
Cohesion: 0.09
Nodes (11): Storage, _first, _raw, _start_block, Storage<T>::clear(), Storage<T>::_load_state(), Storage<T>::peek(), Storage<T>::pop() (+3 more)

### Community 3 - "arq_trial.py"
Cohesion: 0.13
Nodes (24): build_soak_plan(), capture_tracker_diagnostics(), close_updi_without_recovery(), diagnostic_case(), drain_updi_messages(), hardware_gate_errors(), hello_airtime_budget(), lora_time_on_air_us() (+16 more)

### Community 5 - "mcurses.c"
Cohesion: 0.13
Nodes (35): addch(), addstr(), addstr_P(), attrset(), clear(), clrtobot(), clrtoeol(), curs_set() (+27 more)

### Community 6 - "parse_event"
Cohesion: 0.15
Nodes (10): ArqTests, complete(), checked_events(), parse_event(), gateway_status(), reserve_session(), soak_result_metrics(), status_complete() (+2 more)

### Community 7 - "CaptureTests"
Cohesion: 0.06
Nodes (3): CaptureTests, command(), monotonic()

### Community 8 - "Json"
Cohesion: 0.15
Nodes (16): error(), campaign(), progress(), run_one(), Capture, prepare(), radio_only_bringup(), reader_free_h01() (+8 more)

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
Cohesion: 0.09
Nodes (12): ArqSoakPlanTests, fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), confirmed_rf_preflight(), dynamic_attr() (+4 more)

### Community 13 - "generate_lora_config.py"
Cohesion: 0.09
Nodes (13): BootAnalysisTests, SourceFingerprintTests, analyze(), main(), artifacts(), canonical(), digest(), load_radio_profile() (+5 more)

### Community 14 - "validate_repo_isolation.py"
Cohesion: 0.23
Nodes (11): _check_config(), _check_symlink(), _inside(), _items(), _label(), _local_dependency(), main(), _resolved() (+3 more)

### Community 15 - "LoRa"
Cohesion: 0.12
Nodes (12): 1. Mandatory first phase: read-only inventory and graph analysis, LoRa, _active, _hardware, _initialized, _last_rssi, _module, _my_addr (+4 more)

### Community 16 - "RadioBringupTests"
Cohesion: 0.08
Nodes (7): DirectionalHostTests, RadioBringupTests, acquire(), command(), audit_radio_configuration(), read_radio(), validate_hello_exchange()

### Community 17 - "RawStorage"
Cohesion: 0.23
Nodes (6): ui64toa(), RawStorage, _cached_block, _cached_pos, Storage<T>::_save_state(), Sd2Card

### Community 18 - "role_log.h"
Cohesion: 0.12
Nodes (37): InitializeRadio(), AcceptData(), ArmRadio(), FlushTransportEvent(), HandleRadioCommand(), Initialize(), InitializeGpio(), Poll() (+29 more)

### Community 19 - "validate_live_proof"
Cohesion: 0.10
Nodes (13): parse_rf_campaign(), radio_startup_matches(), identity(), lines(), run_wrong_destination_rf_test(), command(), pump_until(), record() (+5 more)

### Community 22 - "ControlInput"
Cohesion: 0.20
Nodes (9): ControlInput, command, digits, last_ms, reading, triggered, value, ssot::ControlInputFeed() (+1 more)

### Community 23 - "receiver_boot.py"
Cohesion: 0.05
Nodes (23): boot(), ApplicationPageWriteTests, BootPackageTests, CompiledHandoffTests, ReceiverBootTests, recording_command(), command(), normalize_ihex_region() (+15 more)

### Community 24 - "Transport"
Cohesion: 0.05
Nodes (30): Transport, armed_, context_, error_, event_context_, frequency_, have_accepted_, kMaxData (+22 more)

### Community 25 - "Receiver"
Cohesion: 0.15
Nodes (13): arq::ArmReceiver(), arq::HandleDataFrame(), arq::InitReceiver(), Receiver, accepted, armed, deliveries, duplicates (+5 more)

### Community 26 - "Gate1Tests"
Cohesion: 0.12
Nodes (3): Gate1Tests, rows(), transaction()

### Community 28 - "load"
Cohesion: 0.10
Nodes (7): ConfigurationTests, ReceiverHardwareTests, checked_cpp(), load(), main(), unique_object(), validate()

### Community 29 - "gateway_radio.cpp"
Cohesion: 0.08
Nodes (14): IsRadioTransmitting(), RadioTransactionTask, RegisterRadioTask(), RejectRadioConfiguration(), StartHelloTestIfEnabled(), StartRadioTransaction(), StopRadio(), I2cCommandTask (+6 more)

### Community 30 - "main"
Cohesion: 0.10
Nodes (5): ReaderFreeH01SummaryTests, main(), reader_free_h01_summary(), frame_seen(), reader_free_rx_idle_summary()

### Community 31 - "._run_capture"
Cohesion: 0.15
Nodes (6): fixture(), add(), LiveProofTests, emit(), start(), write()

### Community 32 - "application.cpp"
Cohesion: 0.45
Nodes (12): CurrentSession(), ExecuteCommand(), FailAdapter(), FeedCommandByte(), FlushStatus(), GetEventContext(), HandleReceive(), Poll() (+4 more)

### Community 34 - "Gate1Audit"
Cohesion: 0.18
Nodes (3): Gate1Audit, instrument(), open_exclusive()

### Community 35 - "Logger"
Cohesion: 0.27
Nodes (5): Logger, _capacity, _cursor, _raw, _start_block

### Community 36 - "ring_buffer.h"
Cohesion: 0.09
Nodes (11): RingBuffer, buffer_, RingBuffer<Capacity>::Read(), RingBuffer<Capacity>::ReadByte(), RingBuffer<Capacity>::Write(), RingBuffer<Capacity>::WriteByte(), RingBuffer<Capacity>::WriteFrame(), first_free_ (+3 more)

### Community 37 - "detect_devices.py"
Cohesion: 0.17
Nodes (12): build_parser(), _load_registry(), main(), _probe_device(), _run_self_test(), SafetyArgumentParser, _scan(), _watch() (+4 more)

### Community 38 - "require"
Cohesion: 0.23
Nodes (5): crc8(), FirmwareIdentityTests, ihex_record(), marker(), require()

### Community 39 - "EventId"
Cohesion: 0.05
Nodes (41): Component, kApplication, kBoot, kHil, kNvm, Event(), EventId, kAuthenticationStarted (+33 more)

### Community 41 - "ScanResult"
Cohesion: 0.12
Nodes (4): DetectedDevice, ScanResult, format_text(), result_to_json()

### Community 42 - "reverse_raw_app.cpp"
Cohesion: 0.42
Nodes (10): ExecuteCommand(), FeedCommandByte(), IsPayloadCommand(), ParkRadio(), Poll(), ReadStableCounter(), RecordConfiguration(), RecordEvent() (+2 more)

### Community 43 - "DeviceLayout"
Cohesion: 0.11
Nodes (19): IsAppCodeRange(), DeviceLayout, kAppDataStart, kApplicationEnd, kApplicationImageEnd, kApplicationStart, kBootEnd, kBootSizePages (+11 more)

### Community 44 - "image_evidence"
Cohesion: 0.18
Nodes (7): event(), image_evidence(), journal(), StableTransportProofTests, wrong_destination_journal(), assess(), validate_stable_transport()

### Community 45 - "PlatformResult"
Cohesion: 0.14
Nodes (18): InitializeAdc(), ReadBatteryAdc(), ReadSample(), ReadTemperatureAdc(), WaitForConversion(), PlatformResult, kBusy, kForbidden (+10 more)

### Community 46 - "Campaign"
Cohesion: 0.08
Nodes (32): Campaign, attempts, campaign_id, destination, sequence, single_packet, source, state (+24 more)

### Community 47 - "Bus"
Cohesion: 0.11
Nodes (6): Bus, fifo, finish_delay, regs, reset_mode, ticks

### Community 48 - "require"
Cohesion: 0.11
Nodes (4): DetectionIntegrationTests, pio(), runner(), require()

### Community 50 - "ReverseRawTests"
Cohesion: 0.20
Nodes (4): ReverseRawTests, audit_raw_configuration(), reverse_exchange(), status()

### Community 51 - "diagnostics.h"
Cohesion: 0.28
Nodes (9): drain_status(), main(), send_command(), QueuedLogLine(), ResetLog(), clear_log(), cmd(), logged() (+1 more)

### Community 52 - "AGENTS.md — AVR128DA28 / LoRa Embedded Engineering"
Cohesion: 0.10
Nodes (20): 10. Logging, measurement, and evidence, 11. Decision and intervention policy, 12. Response contract, 13. Technical references (read when relevant; do not substitute for active SSOT), 1. Mission and current MVP, 2. Operating philosophy, 3. Project truth and protected files, 4. Target architecture (+12 more)

### Community 53 - "symmetric_fixture"
Cohesion: 0.21
Nodes (4): symmetric_fixture(), add(), event(), SymmetricProofTests

### Community 54 - "upditerm.py"
Cohesion: 0.07
Nodes (8): Console, main(), parse_arguments(), SerialPort, SerialUPDI, Terminal, TransportError, UPDI

### Community 55 - "TrackerConfig"
Cohesion: 0.10
Nodes (18): TrackerConfig, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 57 - "Task"
Cohesion: 0.06
Nodes (17): I2cResetTask, timestamp_ms_, HeartbeatTask, timestamp_ms_, Task::Task(), TaskScheduler::GetTaskCount(), Task, is_paused_ (+9 more)

### Community 58 - "FakeRadio"
Cohesion: 0.09
Nodes (17): FakeRadio, bytes, campaign_id, completion_error, destination, done, incoming, incoming_campaign_id (+9 more)

### Community 59 - "ReceiveTests"
Cohesion: 0.13
Nodes (3): ReceiveTests, wait(), wait()

### Community 60 - "assess"
Cohesion: 0.17
Nodes (4): assess(), response(), _status(), verify_hashes()

### Community 62 - "Config"
Cohesion: 0.11
Nodes (18): Config, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 63 - "reliable_app_test.cpp"
Cohesion: 0.23
Nodes (7): updi_role_log_dropped(), command(), complete_tx(), deliver(), main(), updi_uart_try_tx(), updi_uart_tx()

### Community 64 - "MvpRoundtripTests"
Cohesion: 0.21
Nodes (4): Board, frames(), MvpRoundtripTests, write_toml()

### Community 65 - "load"
Cohesion: 0.12
Nodes (9): ApplicationConfigTests, RawEvidenceTests, validate_reverse(), load(), raw_payload(), raw_send_command(), render(), validate() (+1 more)

### Community 66 - "HardwareGateTests"
Cohesion: 0.05
Nodes (9): BuildAcceptanceTests, dynamic_attr(), effective_platformio_config(), FlashSafetyTests, HardwareGateTests, command(), ihex_record(), hardware_blockers() (+1 more)

### Community 67 - "require"
Cohesion: 0.26
Nodes (4): device(), probe(), require(), RoleDetectorTests

### Community 68 - "OPERATING CONTRACT — READ ALL BEFORE EDITING"
Cohesion: 0.14
Nodes (13): 0. Target, boundaries, priorities, 10. Mandatory negative and protocol matrix, 11. Acceptance criteria — NOT negotiable, 12. Agentic self-repair loop — persistent, evidence-driven, bounded, 13. First actions — execute in this exact order, 2. Reference repo: behavior parity without copying defects, 3. IMPORTANT RADIO FACT: SX127x `setNodeAddress`, 4. Test FIRST using real radios, BEFORE migration (+5 more)

### Community 70 - "check_cpp.py"
Cohesion: 0.36
Nodes (9): capture_host_commands(), check(), complexity_check(), firmware_checks(), main(), record(), resolve_tools(), run() (+1 more)

### Community 71 - "Tracker Hardware SSOT — LoRa Tracker RFM"
Cohesion: 0.18
Nodes (9): 1. Board identity and components, 2. AVR128DA28 pin and net SSOT, 3. Power and startup contract, 4. Minimal firmware implementation contract, 5. Acceptance criteria / physical evidence, 6. Firmware configuration, Exact LoRa RFM95W signal map, Sources (+1 more)

### Community 72 - "SD.h"
Cohesion: 0.25
Nodes (8): mbr_t, mbrSig0, mbrSig1, part, SdPartition, firstSector, totalSectors, type

### Community 73 - "EventQueue"
Cohesion: 0.12
Nodes (15): Event, campaign_id, error, name, sequence, time_ms, type, EventQueue (+7 more)

### Community 75 - "Port"
Cohesion: 0.21
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 76 - "test_device_reconnect.py"
Cohesion: 0.32
Nodes (4): DeviceReconnectTests, make_device(), make_probe(), require()

### Community 78 - "Comm"
Cohesion: 0.25
Nodes (8): Comm, AIR_CONFIG_NODE_ADDR, DEBUG_BAUD_RATE, ENABLE_I2C_WIRE, GATEWAY_ANYCAST_ADDR, GATEWAY_DEFAULT_ADDR, I2C_ADDRESS_BASE, I2C_ADDRESS_STRAP_SHIFT

### Community 79 - "diagnostics.cpp"
Cohesion: 0.24
Nodes (9): AcquireLine(), EventContext, FlushByte(), OverflowCount(), PendingLineCount(), RecordDiscard(), RecordEvent(), RecordFrame() (+1 more)

### Community 80 - "915 MHz LoRa bench procedure"
Cohesion: 0.29
Nodes (6): 915 MHz LoRa bench procedure, App-only programming after exact write approval, Hardware results, Refactor verification, RF conditions and acceptance, Verified candidates

### Community 81 - "device.h"
Cohesion: 0.17
Nodes (11): PORT_struct, PORT_t, SPI_struct, SPI_t, TWI_struct, TWI_t, TwiHold, k300Ns (+3 more)

### Community 82 - "src/codec.cpp"
Cohesion: 0.27
Nodes (14): DecodePacketReport(), DecodePacketReportWithAck(), DecodeReportEntry(), EncodeConfig(), EncodePacketBoot(), EncodePacketReport(), EncodePacketReportWithAck(), EncodeReportEntry() (+6 more)

### Community 83 - "role_detector.py"
Cohesion: 0.16
Nodes (7): USBDevice, classify_devices(), diff_device_presence(), _identity_role(), _probe_for(), _registry_hint(), _registry_record()

### Community 84 - "Frame"
Cohesion: 0.33
Nodes (6): Frame, campaign_id, destination, sequence, source, type

### Community 85 - "System"
Cohesion: 0.40
Nodes (5): System, ENABLE_ESPCOMM, ENABLE_LORA_RX, ENABLE_WATCHDOG, WDT_TIMEOUT_PERIOD

### Community 86 - "arq/codec.cpp"
Cohesion: 0.60
Nodes (3): arq::DecodeFrame(), arq::EncodeFrame(), arq::IsValidFrame()

### Community 87 - "compare_snapshots"
Cohesion: 0.17
Nodes (3): classify(), compare_snapshots(), delta()

### Community 88 - "reverse_raw_test.cpp"
Cohesion: 0.27
Nodes (5): main(), text(), cmd(), logged(), main()

### Community 90 - "Controller"
Cohesion: 0.13
Nodes (12): Controller, last_led1_toggle_, last_tx_toggle_, led1_interval_ms_, led1_on_, led1_pin_, led2_pin_, led_off_level_ (+4 more)

### Community 91 - "shutil"
Cohesion: 0.36
Nodes (6): bootstrap(), create_temp_dir(), main(), bootstrap(), create_temp_dir(), main()

### Community 94 - "string"
Cohesion: 0.04
Nodes (4): beginTransaction(), SPIClass, SPISettings, beginTransaction()

### Community 96 - "role_log_test.cpp"
Cohesion: 0.07
Nodes (11): DecodeLoraConfig(), delay(), main(), pump(), state_name(), step(), EepromSpy, reads (+3 more)

### Community 97 - "Session"
Cohesion: 0.11
Nodes (3): Console, main(), Session

### Community 98 - "ErrataDiagnosticsTests"
Cohesion: 0.12
Nodes (5): ErrataDiagnosticsTests, decode_snapshot(), interpret_rx(), link_budget(), main()

### Community 99 - "firmware_identity.py"
Cohesion: 0.14
Nodes (8): FirmwareIdentity, crc8(), FingerprintResult, IdentityParseResult, match_flash_fingerprint(), parse_identity_stream(), _valid_build(), _valid_timestamp()

### Community 103 - "board_ssot.h"
Cohesion: 0.25
Nodes (6): arq_board, Initialize(), board_ssot_init(), PrepareTrackerForRadioOnly(), Initialize(), randomSeed()

### Community 105 - "Pins"
Cohesion: 0.14
Nodes (14): Pins, ANALOG_IN_0, ANALOG_IN_1, DEBUG_RX, DEBUG_TX, HOST_INT, LED1, LED2 (+6 more)

### Community 106 - "mvp_app.cpp"
Cohesion: 0.21
Nodes (15): 6. Build isolation and migration constraints, loop(), onPreMain(), debug_init(), debug_write(), debug_write_float(), debug_write_hex(), debug_write_int() (+7 more)

### Community 107 - "Pair"
Cohesion: 0.15
Nodes (12): Application, applied, reject, Pair, a, aa, b, bb (+4 more)

### Community 109 - "probe_firmware_identity"
Cohesion: 0.22
Nodes (8): identify_mcu(), _is_access_error(), _port_busy(), probe_firmware_identity(), probe_target_sib(), read_firmware_flash(), _require_safe(), _run_bounded()

### Community 110 - "ReportEntry"
Cohesion: 0.14
Nodes (14): ReportEntry, day, hour, latitude, longitude, minute, month, quality (+6 more)

### Community 111 - "time-utils/time-utils.h"
Cohesion: 0.32
Nodes (8): GetUnixTime(), GetCurrentTimeString(), GetDay(), GetHours(), GetMinutes(), GetMonth(), GetSeconds(), GetYear()

### Community 114 - "SleepState"
Cohesion: 0.40
Nodes (5): SleepState, force_wakeup, is_sleeping, last_rtc_ticks, unix_time

### Community 115 - "tracker_config.h"
Cohesion: 0.20
Nodes (10): Checkpoint, INVALID_GNSS_DATE, SPI_CTRL_BEFORE_LORA, SPI_CTRL_BEFORE_PWR_ON, TRACKER_AFTER_GNSS_ON, TRACKER_BEFORE_GNSS_ON, Fixed settings and checks, Runtime settings (+2 more)

### Community 117 - "State"
Cohesion: 0.17
Nodes (12): State, begin_count, cs_high_seen, cs_low_seen, cs_pin, initialized, route, swap_count (+4 more)

### Community 118 - "SenderState"
Cohesion: 0.18
Nodes (7): SenderState, kBackoff, kDelivered, kFailed, kIdle, kTransmitting, kWaitingAck

### Community 119 - "gate1_live.py"
Cohesion: 0.15
Nodes (23): controlled_cpu_reset(), firmware_identity_from_events(), gpr_roundtrip_succeeded(), halted_gpr_roundtrip(), mailbox_snapshot(), main(), _parse_block(), part_from_signature() (+15 more)

### Community 120 - "Result"
Cohesion: 0.29
Nodes (7): Result, kOk, kPending, kProtocolError, kRadioError, kRejected, kTimeoutExhausted

### Community 121 - "commands.h"
Cohesion: 0.15
Nodes (12): CommandInput, buffer_, length_, overflow_, DecodeHexDigit(), InputResult, kComplete, kOverflow (+4 more)

### Community 125 - "Tasks"
Cohesion: 0.22
Nodes (9): Tasks, ENABLE_HEARTBEAT_TASK, HEARTBEAT_NAME, HEARTBEAT_OFF_MS, HEARTBEAT_ON_MS, HEARTBEAT_PERIOD_MS, I2C_RESET_SETTLE_MS, LED1_TOGGLE_INTERVAL_MS (+1 more)

### Community 126 - "reliable_transport_test.cpp"
Cohesion: 0.36
Nodes (9): count_transition(), deliver(), dropped(), finish_reply(), loss_scenario(), main(), start_data(), stress_round_trips() (+1 more)

### Community 128 - "Command"
Cohesion: 0.15
Nodes (13): Command, budget, kind, payload, payload_length, session, stride, CommandKind (+5 more)

### Community 130 - "Revision"
Cohesion: 0.50
Nodes (4): Revision, major, minor, raw_revision_id

### Community 133 - "ErrorCode"
Cohesion: 0.20
Nodes (10): ErrorCode, CONFIG_FILE_READ_FAILED, CONFIG_PART_NOT_FOUND, CONFIG_VOL_INIT_FAILED, DATA_PARTITION_NOT_FOUND, LOG_PARTITION_NOT_FOUND, LOGGER_SETUP_FAILED, LORA_INIT_FAILED (+2 more)

### Community 134 - "ProvisioningResult"
Cohesion: 0.27
Nodes (9): ProvisioningResult, kInvalidArgument, kOk, kUnprovisioned, kUnsupported, IsHmacKeyProvisioned(), ReadDeviceUid(), ReadHmacKey() (+1 more)

### Community 135 - "EventStats"
Cohesion: 0.18
Nodes (11): EventStats, ack_accepted, ack_tx, data_tx, destination_discards, duplicates, failures, nack_received (+3 more)

### Community 138 - "SdFile"
Cohesion: 0.15
Nodes (9): get_data_and_log_partitions(), open_file_in_root(), read_line(), SdFile, data_, length_, position_, SdVolume (+1 more)

### Community 141 - "PacketBoot"
Cohesion: 0.18
Nodes (10): DecodeConfig(), DecodePacketBoot(), LoadFloat(), PacketBoot, checkpoint, config, device_model, firmware (+2 more)

### Community 143 - "validate_live_proof"
Cohesion: 0.38
Nodes (4): complete_campaign_logs(), packet_event(), payload_event(), RfEvidenceTests

### Community 145 - "stub/Arduino.h"
Cohesion: 0.12
Nodes (6): random(), begin(), digitalWrite(), end(), ltoa(), push_back()

### Community 148 - "Connect to a virtual UART on an AVR via UPDI"
Cohesion: 0.22
Nodes (8): Connect to a virtual UART on an AVR via UPDI, Demo program, License, Prerequisites, UPDI interface, Upditerm, Usage, Virtual UART

### Community 152 - "Gateway-to-Receiver SF7 Hello World"
Cohesion: 0.25
Nodes (7): Current result — Receiver installed, normal startup unresolved, Gateway-to-Receiver SF7 Hello World, No-meter read-only hardware verified; Receiver write wiring unconfirmed, Receiver boot incompatibility, Remaining physical prerequisites, Single-packet behavior and identities, Verified software result

### Community 153 - "ssot/codec.cpp"
Cohesion: 0.26
Nodes (11): DecodePayloadFields(), EncodeControlPayload(), EncodeHeader(), ssot::AckMatches(), ssot::DecodeFrame(), ssot::DecodePayload(), ssot::EncodeAckFrame(), ssot::EncodeAckPayload() (+3 more)

### Community 154 - "Frame"
Cohesion: 0.22
Nodes (9): Frame, dst, length, payload, reason, sequence, session, src (+1 more)

### Community 155 - "test_radio_915_ssot.py"
Cohesion: 0.15
Nodes (4): I2cRadioConfigTests, Radio915ValidationTests, valid_profile(), validate_radio_profile()

### Community 162 - "Wire.h"
Cohesion: 0.22
Nodes (8): Evidence basis, H1 connector, H2 connector and board signals, Pin Mapping Audit — AVR128DA28 / RFM95W, Radio and MCU pins, RF connector path, Verification, begin()

### Community 163 - "ReceiverState"
Cohesion: 0.40
Nodes (5): ReceiverState, kListening, kReturningToRx, kSendingResponse, kValidating

### Community 164 - "TraceBus"
Cohesion: 0.24
Nodes (4): main(), TraceBus, sensitivity_writes, stage

### Community 166 - "LossMetrics"
Cohesion: 0.29
Nodes (7): LossMetrics, ack_tx, attempts, duplicates, nack_tx, retries, timeouts

### Community 169 - "AdcTemp"
Cohesion: 0.17
Nodes (12): AdcTemp, ADC_MAX_COUNTS, CTRLA_ENABLE_12BIT, FIXED_POINT_SHIFT, INIT_DELAY_SETTING, KELVIN_TO_CELSIUS, MUX_TEMP_CHANNEL, PRESCALER_SETTING (+4 more)

### Community 178 - "stdint"
Cohesion: 0.07
Nodes (5): Memory, I2C_MAILBOX_BYTES, SHARED_RINGBUF_BYTES, Poll(), ReadTemperatureCelsius()

### Community 179 - "packets.h"
Cohesion: 0.40
Nodes (4): PacketReport, report, seq, type

### Community 180 - "AVR128DA28 LoRa firmware"
Cohesion: 0.29
Nodes (6): Application configuration, AVR128DA28 LoRa firmware, Build, Host tests, Preserved boundaries, Static analysis and formatting

### Community 185 - "PacketAck"
Cohesion: 0.33
Nodes (5): DecodePacketAck(), EncodePacketAck(), PacketAck, seq, type

### Community 196 - "PacketAdvertise"
Cohesion: 0.33
Nodes (5): DecodePacketAdvertise(), EncodePacketAdvertise(), PacketAdvertise, seq, type

### Community 204 - "core_test.cpp"
Cohesion: 0.34
Nodes (12): absolute_deadline(), ack_matrix(), codec(), control(), data(), fault_harness(), fresh(), main() (+4 more)

### Community 206 - "install_cpp_quality_tools.sh"
Cohesion: 0.67
Nodes (3): find_tool(), PATH, install_cpp_quality_tools.sh script

### Community 214 - "mvp_stub/Arduino.h"
Cohesion: 0.25
Nodes (3): CPUINT(), digitalWrite(), digitalWriteFast()

### Community 231 - "Sender"
Cohesion: 0.08
Nodes (30): arq::ArmSender(), arq::HandleControlFrame(), arq::HandleTxCompletion(), arq::InitSender(), arq::IsSenderActive(), arq::PollSender(), arq::RequestTransmission(), arq::StopSender() (+22 more)

### Community 233 - "application_bounds_for_environment"
Cohesion: 0.13
Nodes (13): DirectionalTests, RadioOnlyTests, TargetLayoutTests, application_bounds_for_environment(), build_flag_defines(), _config_int(), effective_project_sections(), radio_profile_compile_flags() (+5 more)

### Community 236 - "PacketMaintenance"
Cohesion: 0.33
Nodes (5): DecodePacketMaintenance(), EncodePacketMaintenance(), PacketMaintenance, command, type

### Community 237 - "ExcludedSx1262Experiment"
Cohesion: 0.10
Nodes (21): 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates, Gateway Hardware SSOT — Rudolph Gateway, H1 (10-pin; only pins 1–5 used in the source schematic) (+13 more)

### Community 260 - "Result"
Cohesion: 0.22
Nodes (8): Result, kAccepted, kAckTimeout, kInvalidArgument, kPending, kRadioError, kRejected, kTxTimeout

### Community 264 - "arduino"
Cohesion: 0.10
Nodes (5): NextCampaignId(), Initialize(), InitializeRadio(), InitializeReceiverGpio(), main()

### Community 299 - "sleep.cpp"
Cohesion: 0.16
Nodes (6): SetUnixTime(), SleepFor(), PowerSavingTaskScheduler, GetTotalSeconds(), InitializeTime(), SetTime()

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

### Community 336 - "PacketMaintenanceAck"
Cohesion: 0.33
Nodes (5): DecodePacketMaintenanceAck(), EncodePacketMaintenanceAck(), PacketMaintenanceAck, response, type

### Community 341 - "ใช้งาน Codex Goal — LoRa E2E Feature-Based"
Cohesion: 0.40
Nodes (4): ความต่างระหว่าง Goal กับ config, จุดที่ต้องพิสูจน์, แหล่งอ้างอิง, ใช้งาน Codex Goal — LoRa E2E Feature-Based

### Community 342 - "PacketReportWithAck"
Cohesion: 0.40
Nodes (4): PacketReportWithAck, report, seq, type

## Knowledge Gaps
- **575 isolated node(s):** `kRxWait`, `kTxData`, `kWaitResponse`, `kRetryPending`, `kTxResponse` (+570 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1533 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **103 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Transport` connect `Transport` to `Result`, `EventQueue`, `Pair`, `State`, `stdint`, `.EmitEvent`, `reliable_transport_test.cpp`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **What connects `kRxWait`, `kTxData`, `kWaitResponse` to the rest of the system?**
  _575 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.08552388004442799 - nodes in this community are weakly interconnected._
- **Why does `TrackerConfig` connect `TrackerConfig` to `stdint`, `tracker_config.h`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Should `rf_proof.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1135593220338983 - nodes in this community are weakly interconnected._
- **Should `Storage` be split into smaller, more focused modules?**
  _Cohesion score 0.09401709401709402 - nodes in this community are weakly interconnected._
- **Should `arq_trial.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13063063063063063 - nodes in this community are weakly interconnected._