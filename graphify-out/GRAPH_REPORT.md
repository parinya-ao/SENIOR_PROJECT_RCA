# Graph Report - SENIOR_PROJECT_RCA  (2026-11-17)

## Corpus Check
- 426 files · ~301,174 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 29 file(s) not represented in the graph (top: (none) 9, .toml 6, .diff 5)

## Summary
- 3943 nodes · 7168 edges · 365 communities (188 shown, 177 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 469 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f0ca0155`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- pathlib
- rf_proof.py
- Storage
- analyze
- mcurses.c
- arq_trial.py
- CaptureTests
- Json
- State
- GNSS
- SystemConstants
- ArqSoakPlanTests
- generate_lora_config.py
- sender.cpp
- LoRa
- RadioBringupTests
- RawStorage
- role_log.h
- Raw LoRa ARQ V1 — STAR report
- Hardware
- install
- Transport
- Gate1Tests
- RepositoryIsolationTests
- load
- stdint
- main
- ._run_capture
- application.cpp
- run_gate1
- Logger
- ring_buffer.h
- detect_devices.py
- SD.h
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
- FlashSafetyTests
- diagnostics.h
- AGENTS.md — AVR128DA28 / LoRa Embedded Engineering
- Frame
- UPDI
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
- .test_no_meter_identity_uses_live_unique_serial_without_checklist
- RfTestContinuationTests
- validate_live_proof
- ERRATA_FOLLOWUP_STAR.md
- Forensic RCA — reverse raw LoRa, 2026-11-13
- Event
- radio_link.cpp
- Port
- Json
- Final RCA — AVR128DA28 Tracker / RFM95W ARQ V1
- 20261114T044136Z-radio-only/FINAL_RCA.md
- hardware_blockers
- 20261114T094223Z-soak-validation/FINAL_RCA.md
- device.h
- src/codec.cpp
- role_detector.py
- Gate 1 live UPDI report — 20261113T153146Z
- 20261113T211753Z/README.md
- Final RCA — Tracker to Gateway LoRa ARQ V1
- Final RCA — LoRa ARQ Hardware Recovery
- Autonomous engineering verification — 2026-11-14
- Controller
- os
- string
- I2cResetTask
- role_log_test.cpp
- Session
- ErrataDiagnosticsTests
- firmware_identity.py
- RCA_REPORT.md
- OPERATING CONTRACT — READ ALL BEFORE EDITING
- Regression and preservation results
- Sd2Card
- Pins
- mvp_app.cpp
- Pair
- SleepState
- probe_firmware_identity
- ReportEntry
- time-utils/time-utils.h
- SSOT review — Tracker, Gateway and reverse-raw role mapping
- SerialPort
- C++ migration verification
- Checkpoint
- State
- SenderState
- gate1_live.py
- Result
- Receiver
- 20261114T023251Z/FINAL_RCA.md
- Gateway Hardware SSOT — Rudolph Gateway
- .test_guarded_app_writer_erases_only_its_page_with_installed_avrdude_dryrun
- Tasks
- reliable_transport_test.cpp
- ReliableTransportTests
- Command
- BuildEnvironment
- Baseline and scope
- LoRa-only ARQ recovery — RCA continuation
- 915 MHz deployment and bidirectional diagnostic verification
- ErrorCode
- ProvisioningResult
- EventStats
- StableLoraSafetyTests
- main
- SdFile
- Program source finding — SX127x high-band mode
- Tracker Hardware SSOT — LoRa Tracker RFM
- PacketBoot
- ControlInput
- complete_campaign_logs
- Module
- Comm
- Connect to a virtual UART on an AVR via UPDI
- Execution journal
- UPDI-only Hello World MVP — STAR report
- Gateway-to-Receiver SF7 Hello World
- ssot/codec.cpp
- Frame
- Board
- .test_runner_uses_receiver_ready_then_one_gateway_start
- Scope and baseline
- External code and primary-source review
- Test-first and physical validation results
- Execution Journal
- Long-Duration Hardware Soak Readiness — Final RCA Continuation
- Wire.h
- RadioTransactionTask
- TraceBus
- LossMetrics
- discover_ports
- AdcTemp
- STAR — Tracker→Rudolph receiver errata and transport follow-up
- SenderStableTransportTests
- Exact RadioLib and register audit
- Hardware topology
- Regression results
- H01 reader-free hardware result
- .test_rf_enabled_upload_does_not_require_rf_authorization
- ReceiverBootTests
- stub/Arduino.h
- packets.h
- AVR128DA28 LoRa firmware
- PacketAck
- UPDI first-failure boundary
- Execution journal
- Experiment plan and next decision
- ARQ and packet path
- Root-cause analysis
- Corrective actions
- Source log
- Radio and protocol boundaries
- Execution Summary
- RF Configuration and Toolchain Follow-up
- PacketAdvertise
- Embedded C++ readability refactor verification
- DirectionalTests
- MonitorConsole
- CppInterfaceTests
- core_test.cpp
- SsotProtocolTests
- System
- Evidence index
- Source and transport audit
- SX127x HF-mode verification
- Implementation summary
- Power and Interface Topology
- PROGRAMMER_VERIFICATION.md
- Reliability Results
- mvp_stub/Arduino.h
- EventQueue
- C++ migration baseline
- .test_fresh_readback_rejects_wrong_image_or_target_serial
- SingleFirmwareEntryTests
- Power and reset evidence
- ARQ test plan
- Strict Python static analysis
- 04_hypothesis_register.md
- Next discriminating experiment
- Regression Results — Current Continuation
- Sender
- RadioOnlyTests
- SerialUPDI
- Ownership Map
- PacketMaintenance
- ExcludedSx1262Experiment
- HeartbeatTask
- RADIOLIB.md
- PROTOCOL.md
- STANDARDS.md
- BASELINE.md
- FIXES.md
- GATE1_ROOT_CAUSE.md
- HARDWARE_MEASUREMENTS.md
- HYPOTHESES.md
- LIVE_TOPOLOGY.md
- REGRESSION.md
- REVERSE_RF_ROOT_CAUSE.md
- firmware/README.md
- instruments/README.md
- plots/README.md
- radio/README.md
- raw/README.md
- serial/README.md
- updi/README.md
- 06_HYPOTHESES.md
- Console
- Result
- link_budget
- string
- sleep.cpp
- lora
- State
- .EmitEvent
- .test_unsafe_image_makes_build_stage_fail
- upditerm.py
- reader_free_h01_summary
- verify_hashes
- GatewayI2cTests
- main
- lora/library.json
- time-utils/library.json
- receiver_gpio_test.cpp
- TaskRestartTests
- require_preserved
- usb_inventory.py
- I2cRadioConfigTests
- Proposed discriminating experiments — NOT executed or authorized here
- RadioLibHalTests
- debug_protocol_ack_nack.py
- RestartTask
- PacketMaintenanceAck
- Regression Matrix
- Baseline Graph
- RadioDiagnosticsTests
- ใช้งาน Codex Goal — LoRa E2E Feature-Based
- PacketReportWithAck
- checked_cpp
- Suggested append-only AGENTS.md contract (merge; do not overwrite existing instructions)
- parse_raw_mvp_logs
- ENTRYPOINT_MATRIX.md
- ._connect_verified
- DELETION_AUDIT.md
- Real-Radio Evidence

## God Nodes (most connected - your core abstractions)
1. `Transport` - 54 edges
2. `SystemConstants` - 46 edges
3. `Gate1Tests` - 46 edges
4. `State` - 45 edges
5. `Hardware` - 36 edges
6. `HardwareGateTests` - 36 edges
7. `Sender` - 35 edges
8. `analyze()` - 35 edges
9. `LoRa` - 34 edges
10. `RCATests` - 33 edges

## Surprising Connections (you probably didn't know these)
- `Radio SPI and interrupt contract` --references--> `ExcludedSx1262Experiment`  [INFERRED]
  docs/ssot/GATEWAY_SSOT.md → include/gateway_ssot.hpp
- `Scope` --references--> `TrackerConfig`  [INFERRED]
  docs/ssot/TRACKER_CONFIG_SSOT.md → include/tracker_config.h
- `Graph tools` --references--> `LoRa`  [INFERRED]
  docs/architecture/BASELINE_GRAPH.md → src/features/radio_link/radio_link.h
- `Verification and limits` --references--> `TransportError`  [INFERRED]
  docs/UPDI_HELLO_WORLD_STAR.md → third_party/upditerm/upditerm.py
- `Live non-RF experiment E01` --references--> `Gate1Audit`  [INFERRED]
  docs/rca/20261114T044136Z-radio-only/RADIO_ONLY_TEST_RESULTS.md → tools/rca/gate1_live.py

## Import Cycles
- None detected.

## Communities (365 total, 177 thin omitted)

### Community 1 - "rf_proof.py"
Cohesion: 0.08
Nodes (57): TargetLayoutTests, application_bounds_for_environment(), application_layout_verified(), authorized_application_pages(), boot_fuses_match(), build_flag_defines(), capture_radio_spi_log(), capture_usb_topology() (+49 more)

### Community 2 - "Storage"
Cohesion: 0.09
Nodes (11): Storage, _first, _raw, _start_block, Storage<T>::clear(), Storage<T>::_load_state(), Storage<T>::peek(), Storage<T>::pop() (+3 more)

### Community 4 - "analyze"
Cohesion: 0.07
Nodes (9): RCATests, analyze(), load(), read(), classify(), compare_snapshots(), delta(), main() (+1 more)

### Community 5 - "mcurses.c"
Cohesion: 0.13
Nodes (35): addch(), addstr(), addstr_P(), attrset(), clear(), clrtobot(), clrtoeol(), curs_set() (+27 more)

### Community 6 - "arq_trial.py"
Cohesion: 0.12
Nodes (25): build_soak_plan(), capture_tracker_diagnostics(), checked_events(), close_updi_without_recovery(), diagnostic_case(), drain_updi_messages(), hardware_gate_errors(), hello_airtime_budget() (+17 more)

### Community 7 - "CaptureTests"
Cohesion: 0.06
Nodes (3): CaptureTests, command(), monotonic()

### Community 8 - "Json"
Cohesion: 0.13
Nodes (21): error(), campaign(), progress(), run_one(), Capture, complete(), park_reverse(), prepare() (+13 more)

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
Nodes (15): ArqSoakPlanTests, fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), fake_campaign(), confirmed_rf_preflight(), dynamic_attr() (+7 more)

### Community 13 - "generate_lora_config.py"
Cohesion: 0.05
Nodes (27): Radio915ValidationTests, valid_profile(), RawMvpTests, ReceiverHardwareTests, SourceFingerprintTests, artifacts(), canonical(), digest() (+19 more)

### Community 14 - "sender.cpp"
Cohesion: 0.20
Nodes (10): arq::ArmSender(), arq::HandleControlFrame(), arq::HandleTxCompletion(), arq::InitSender(), arq::IsSenderActive(), arq::PollSender(), arq::RequestTransmission(), arq::StopSender() (+2 more)

### Community 15 - "LoRa"
Cohesion: 0.11
Nodes (15): 1. Mandatory first phase: read-only inventory and graph analysis, Address and radio API call sites, Address, LoRa, _active, _hardware, _initialized, _last_rssi (+7 more)

### Community 16 - "RadioBringupTests"
Cohesion: 0.08
Nodes (7): DirectionalHostTests, RadioBringupTests, acquire(), command(), audit_radio_configuration(), read_radio(), validate_hello_exchange()

### Community 17 - "RawStorage"
Cohesion: 0.36
Nodes (5): ui64toa(), RawStorage, _cached_block, _cached_pos, Storage<T>::_save_state()

### Community 18 - "role_log.h"
Cohesion: 0.13
Nodes (29): InitializeRadio(), IsRadioTransmitting(), FlushTransportEvent(), Poll(), ReportStatus(), Poll(), ReadTemperatureCelsius(), Poll() (+21 more)

### Community 19 - "Raw LoRa ARQ V1 — STAR report"
Cohesion: 0.06
Nodes (28): ARQ debugging, UPDI register evidence, Reverse-raw acquisition — 2026-11-13 12:06:29 UTC, Reverse raw — 2026-11-13 12:15:06 UTC, Driver and IRQ audit, Physical result, Repository and prior evidence, Reverse raw readiness and radio audit — 20261113T123510Z (+20 more)

### Community 22 - "Hardware"
Cohesion: 0.14
Nodes (3): wire(), assess_exhaustion(), Hardware

### Community 23 - "install"
Cohesion: 0.26
Nodes (6): boot(), BootPackageTests, recording_command(), install(), load_package(), sha()

### Community 24 - "Transport"
Cohesion: 0.06
Nodes (27): Transport, armed_, context_, error_, event_context_, frequency_, have_accepted_, kMaxData (+19 more)

### Community 26 - "Gate1Tests"
Cohesion: 0.12
Nodes (3): Gate1Tests, rows(), transaction()

### Community 28 - "load"
Cohesion: 0.17
Nodes (5): ConfigurationTests, load(), main(), unique_object(), validate()

### Community 29 - "stdint"
Cohesion: 0.05
Nodes (21): Memory, I2C_MAILBOX_BYTES, SHARED_RINGBUF_BYTES, RegisterRadioTask(), RejectRadioConfiguration(), StartHelloTestIfEnabled(), StartRadioTransaction(), StopRadio() (+13 more)

### Community 30 - "main"
Cohesion: 0.10
Nodes (4): ArqTests, ReaderFreeH01SummaryTests, main(), reader_free_rx_idle_summary()

### Community 31 - "._run_capture"
Cohesion: 0.09
Nodes (10): fixture(), add(), LiveProofTests, emit(), start(), write(), symmetric_fixture(), add() (+2 more)

### Community 32 - "application.cpp"
Cohesion: 0.34
Nodes (14): CurrentSession(), ExecuteCommand(), FailAdapter(), FeedCommandByte(), FlushStatus(), GetEventContext(), HandleReceive(), Initialize() (+6 more)

### Community 34 - "run_gate1"
Cohesion: 0.17
Nodes (13): firmware_identity_from_events(), Gate1Audit, gpr_roundtrip_succeeded(), main(), _parse_block(), preservation_diff(), _read_block(), _readline() (+5 more)

### Community 35 - "Logger"
Cohesion: 0.31
Nodes (5): Logger, _capacity, _cursor, _raw, _start_block

### Community 36 - "ring_buffer.h"
Cohesion: 0.09
Nodes (11): RingBuffer, buffer_, RingBuffer<Capacity>::Read(), RingBuffer<Capacity>::ReadByte(), RingBuffer<Capacity>::Write(), RingBuffer<Capacity>::WriteByte(), RingBuffer<Capacity>::WriteFrame(), first_free_ (+3 more)

### Community 37 - "detect_devices.py"
Cohesion: 0.15
Nodes (10): build_parser(), _load_registry(), main(), _run_self_test(), SafetyArgumentParser, _scan(), _watch(), FirmwareReference (+2 more)

### Community 38 - "SD.h"
Cohesion: 0.25
Nodes (8): mbr_t, mbrSig0, mbrSig1, part, SdPartition, firstSector, totalSectors, type

### Community 39 - "EventId"
Cohesion: 0.05
Nodes (41): Component, kApplication, kBoot, kHil, kNvm, Event(), EventId, kAuthenticationStarted (+33 more)

### Community 41 - "ScanResult"
Cohesion: 0.12
Nodes (5): _print_result(), DetectedDevice, ScanResult, format_text(), result_to_json()

### Community 42 - "reverse_raw_app.cpp"
Cohesion: 0.33
Nodes (11): arq_board, ExecuteCommand(), FeedCommandByte(), IsPayloadCommand(), ParkRadio(), Poll(), ReadStableCounter(), RecordConfiguration() (+3 more)

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

### Community 49 - "TracePort"
Cohesion: 0.09
Nodes (3): instrument(), open_exclusive(), TracePort

### Community 51 - "diagnostics.h"
Cohesion: 0.08
Nodes (25): board_ssot_init(), AcquireLine(), EventContext, FlushByte(), OverflowCount(), PendingLineCount(), RecordDiscard(), RecordEvent() (+17 more)

### Community 52 - "AGENTS.md — AVR128DA28 / LoRa Embedded Engineering"
Cohesion: 0.10
Nodes (20): 10. Logging, measurement, and evidence, 11. Decision and intervention policy, 12. Response contract, 13. Technical references (read when relevant; do not substitute for active SSOT), 1. Mission and current MVP, 2. Operating philosophy, 3. Project truth and protected files, 4. Target architecture (+12 more)

### Community 53 - "Frame"
Cohesion: 0.33
Nodes (6): Frame, campaign_id, destination, sequence, source, type

### Community 54 - "UPDI"
Cohesion: 0.27
Nodes (3): Normal UPDI Monitor path, Host UPDI / STATUS path, UPDI

### Community 55 - "TrackerConfig"
Cohesion: 0.10
Nodes (18): TrackerConfig, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 57 - "Task"
Cohesion: 0.13
Nodes (10): Task::Task(), TaskScheduler::GetTaskCount(), Task, is_paused_, pt_, wakeup_time_, TaskScheduler, task_count_ (+2 more)

### Community 58 - "FakeRadio"
Cohesion: 0.09
Nodes (17): FakeRadio, bytes, campaign_id, completion_error, destination, done, incoming, incoming_campaign_id (+9 more)

### Community 59 - "ReceiveTests"
Cohesion: 0.13
Nodes (3): ReceiveTests, wait(), wait()

### Community 62 - "Config"
Cohesion: 0.11
Nodes (18): Config, ack_timeout, collect_interval_day, collect_interval_night, day_end_hour, day_start_hour, gps_max_wait_for_fix, long_range (+10 more)

### Community 63 - "reliable_app_test.cpp"
Cohesion: 0.21
Nodes (8): RecordTransportEvent(), updi_role_log_dropped(), command(), complete_tx(), deliver(), main(), updi_uart_try_tx(), updi_uart_tx()

### Community 65 - "load"
Cohesion: 0.09
Nodes (11): ApplicationConfigTests, ReverseRawTests, audit_raw_configuration(), reverse_exchange(), status(), validate_reverse(), load(), raw_payload() (+3 more)

### Community 66 - "HardwareGateTests"
Cohesion: 0.12
Nodes (3): dynamic_attr(), effective_platformio_config(), HardwareGateTests

### Community 67 - "require"
Cohesion: 0.09
Nodes (15): DeviceReconnectTests, make_device(), make_probe(), require(), crc8(), FirmwareIdentityTests, ihex_record(), marker() (+7 more)

### Community 70 - "validate_live_proof"
Cohesion: 0.12
Nodes (11): parse_rf_campaign(), radio_startup_matches(), run_wrong_destination_rf_test(), command(), pump_until(), record(), shared_identity_matches(), single_packet_evidence_passed() (+3 more)

### Community 71 - "ERRATA_FOLLOWUP_STAR.md"
Cohesion: 0.14
Nodes (11): Applicability to 915 MHz / BW125 / SF7, Counter and receive-event interpretation, Exact receiver-IF candidate, RadioLib implementation of record, Receiver errata audit — offline follow-up, 2026-11-13, Exact register comparison and real-driver write order, FACT: option0, 25 modeled register writes, FACT: option1, 29 modeled register writes (+3 more)

### Community 72 - "Forensic RCA — reverse raw LoRa, 2026-11-13"
Cohesion: 0.12
Nodes (16): 10. Unresolved questions, 11. Root cause verdict, 12. Recommended corrective action, 13. Verification plan, 14. Risks and limitations, 15. STAR summary, 1. Executive summary, 2. Scope (+8 more)

### Community 73 - "Event"
Cohesion: 0.20
Nodes (9): Event, campaign_id, error, name, sequence, time_ms, type, radio_diagnostics::EventQueue::Pop() (+1 more)

### Community 75 - "Port"
Cohesion: 0.21
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 76 - "Json"
Cohesion: 0.09
Nodes (12): BootAnalysisTests, analyze(), main(), normalize_ihex_region(), _parse_ihex(), ihex(), prepare(), read_snapshot() (+4 more)

### Community 77 - "Final RCA — AVR128DA28 Tracker / RFM95W ARQ V1"
Cohesion: 0.13
Nodes (15): Business impact, Confirmed findings, Corrective action, Evidence index, Executive summary, Final RCA — AVR128DA28 Tracker / RFM95W ARQ V1, Program-source addendum, Remaining hypotheses (+7 more)

### Community 78 - "20261114T044136Z-radio-only/FINAL_RCA.md"
Cohesion: 0.23
Nodes (4): Hypothesis Matrix, Power A/B/A Results, 2026-11-14 continuation: 923 MHz test profile, Primary-source log

### Community 80 - "20261114T094223Z-soak-validation/FINAL_RCA.md"
Cohesion: 0.14
Nodes (11): Changes, Explicitly not verified, Soak Runner Implementation and Regression, TDD and verification, Current execution status, Implemented, Long-Duration Soak Plan and Readiness, Progressive stages (+3 more)

### Community 81 - "device.h"
Cohesion: 0.10
Nodes (17): PORT_struct, PORT_t, Revision, major, minor, raw_revision_id, SPI_struct, SPI_t (+9 more)

### Community 82 - "src/codec.cpp"
Cohesion: 0.27
Nodes (14): DecodePacketReport(), DecodePacketReportWithAck(), DecodeReportEntry(), EncodeConfig(), EncodePacketBoot(), EncodePacketReport(), EncodePacketReportWithAck(), EncodeReportEntry() (+6 more)

### Community 83 - "role_detector.py"
Cohesion: 0.17
Nodes (7): USBDevice, classify_devices(), diff_device_presence(), _identity_role(), _probe_for(), _registry_hint(), _registry_record()

### Community 84 - "Gate 1 live UPDI report — 20261113T153146Z"
Cohesion: 0.15
Nodes (11): A — Action, Findings, Gate 1 live UPDI report — 20261113T153146Z, Next step, R — Result, S — Situation, T — Task, Gate 1 source audit (+3 more)

### Community 85 - "20261113T211753Z/README.md"
Cohesion: 0.14
Nodes (8): Incident timeline, Execution journal, Hardware measurements and gaps, Forward-link sanity check, SX127x register and RF evidence, Cross-experiment comparison, LoRa ARQ V1 root-cause investigation — 20261113T211753Z, Review map

### Community 86 - "Final RCA — Tracker to Gateway LoRa ARQ V1"
Cohesion: 0.14
Nodes (14): Business impact, Confirmed causes, Evidence index, Executive summary, Final RCA — Tracker to Gateway LoRa ARQ V1, Final verdict, Next decision, RC-01 — UPDI STATUS mailbox write-width defect (+6 more)

### Community 87 - "Final RCA — LoRa ARQ Hardware Recovery"
Cohesion: 0.14
Nodes (14): A — Action, Confirmed software defects, Evidence index, Executive summary, Final RCA — LoRa ARQ Hardware Recovery, Final verdict, Physical inventory and gates, R — Result (+6 more)

### Community 88 - "Autonomous engineering verification — 2026-11-14"
Cohesion: 0.14
Nodes (12): A. Executive Verdict, Autonomous engineering verification — 2026-11-14, B. Changes Implemented, C. Actual Test Results, D. Build Verification, E. ACK Validation, F. Physical Verification, G. RF Verification (+4 more)

### Community 90 - "Controller"
Cohesion: 0.13
Nodes (12): Controller, last_led1_toggle_, last_tx_toggle_, led1_interval_ms_, led1_on_, led1_pin_, led2_pin_, led_off_level_ (+4 more)

### Community 91 - "os"
Cohesion: 0.18
Nodes (7): bootstrap(), create_temp_dir(), main(), BuildIdentityImagesTests, bootstrap(), create_temp_dir(), main()

### Community 94 - "string"
Cohesion: 0.04
Nodes (4): beginTransaction(), SPIClass, SPISettings, beginTransaction()

### Community 96 - "role_log_test.cpp"
Cohesion: 0.07
Nodes (11): DecodeLoraConfig(), delay(), main(), pump(), state_name(), step(), EepromSpy, reads (+3 more)

### Community 98 - "ErrataDiagnosticsTests"
Cohesion: 0.21
Nodes (3): ErrataDiagnosticsTests, decode_snapshot(), interpret_rx()

### Community 99 - "firmware_identity.py"
Cohesion: 0.20
Nodes (8): FirmwareIdentity, crc8(), FingerprintResult, IdentityParseResult, match_flash_fingerprint(), parse_identity_stream(), _valid_build(), _valid_timestamp()

### Community 100 - "RCA_REPORT.md"
Cohesion: 0.29
Nodes (4): Confirmed and derived findings only, Firmware SEND audit, Hypothesis matrix, Offline RCA — Tracker to Rudolph

### Community 101 - "OPERATING CONTRACT — READ ALL BEFORE EDITING"
Cohesion: 0.14
Nodes (13): 0. Target, boundaries, priorities, 10. Mandatory negative and protocol matrix, 11. Acceptance criteria — NOT negotiable, 12. Agentic self-repair loop — persistent, evidence-driven, bounded, 13. First actions — execute in this exact order, 2. Reference repo: behavior parity without copying defects, 3. IMPORTANT RADIO FACT: SX127x `setNodeAddress`, 4. Test FIRST using real radios, BEFORE migration (+5 more)

### Community 102 - "Regression and preservation results"
Cohesion: 0.15
Nodes (10): Evidence, Experiment, Matched Tracker RX-idle control, Result, Firmware and configuration, Hardware counts, Preservation, Python tests (+2 more)

### Community 105 - "Pins"
Cohesion: 0.14
Nodes (14): Pins, ANALOG_IN_0, ANALOG_IN_1, DEBUG_RX, DEBUG_TX, HOST_INT, LED1, LED2 (+6 more)

### Community 106 - "mvp_app.cpp"
Cohesion: 0.23
Nodes (14): Build and application selection, onPreMain(), debug_init(), debug_write(), debug_write_float(), debug_write_hex(), debug_write_int(), Initialize() (+6 more)

### Community 107 - "Pair"
Cohesion: 0.15
Nodes (12): Application, applied, reject, Pair, a, aa, b, bb (+4 more)

### Community 108 - "SleepState"
Cohesion: 0.40
Nodes (5): SleepState, force_wakeup, is_sleeping, last_rtc_ticks, unix_time

### Community 109 - "probe_firmware_identity"
Cohesion: 0.19
Nodes (11): _probe_device(), ProbeEvidence, firmware_fingerprint_evidence(), identify_mcu(), _is_access_error(), _port_busy(), probe_firmware_identity(), probe_target_sib() (+3 more)

### Community 110 - "ReportEntry"
Cohesion: 0.15
Nodes (13): ReportEntry, day, hour, latitude, longitude, minute, month, quality (+5 more)

### Community 111 - "time-utils/time-utils.h"
Cohesion: 0.28
Nodes (9): second, GetUnixTime(), GetCurrentTimeString(), GetDay(), GetHours(), GetMinutes(), GetMonth(), GetSeconds() (+1 more)

### Community 112 - "SSOT review — Tracker, Gateway and reverse-raw role mapping"
Cohesion: 0.20
Nodes (8): Design facts and physical unknowns, 3.3 V, H1 and UPDI interpretation, Board-level SSOT versus firmware roles, Decision, Finding, Gate 1 boundary, Reverse-raw image assignment, SSOT review — Tracker, Gateway and reverse-raw role mapping

### Community 113 - "SerialPort"
Cohesion: 0.23
Nodes (3): Result, SerialPort, TransportError

### Community 114 - "C++ migration verification"
Cohesion: 0.17
Nodes (12): A. Migration summary, Analysis, formatting and review, B. Files changed, C. Architecture, C++ migration verification, D. C++ improvements and comments, E. Verification, F. Resource comparison (+4 more)

### Community 115 - "Checkpoint"
Cohesion: 0.18
Nodes (10): Fixed settings and checks, Runtime settings, Scope, Tracker Configuration SSOT, Checkpoint, INVALID_GNSS_DATE, SPI_CTRL_BEFORE_LORA, SPI_CTRL_BEFORE_PWR_ON (+2 more)

### Community 117 - "State"
Cohesion: 0.17
Nodes (12): State, begin_count, cs_high_seen, cs_low_seen, cs_pin, initialized, route, swap_count (+4 more)

### Community 118 - "SenderState"
Cohesion: 0.29
Nodes (7): SenderState, kBackoff, kDelivered, kFailed, kIdle, kTransmitting, kWaitingAck

### Community 119 - "gate1_live.py"
Cohesion: 0.17
Nodes (14): read(), controlled_cpu_reset(), halted_gpr_roundtrip(), mailbox_snapshot(), part_from_signature(), read_data_space_byte(), read_updi_pesig(), reenable_uart_output() (+6 more)

### Community 120 - "Result"
Cohesion: 0.29
Nodes (7): Result, kOk, kPending, kProtocolError, kRadioError, kRejected, kTimeoutExhausted

### Community 121 - "Receiver"
Cohesion: 0.05
Nodes (37): Configuration and maintenance, Firmware architecture, Implementation contracts, Protocol and ownership, Resulting module map, arq::DecodeFrame(), arq::EncodeFrame(), arq::IsValidFrame() (+29 more)

### Community 122 - "20261114T023251Z/FINAL_RCA.md"
Cohesion: 0.22
Nodes (6): Power, reset, and measurement limits, Reset-cause capture, Tracker supply path, What was not measured, Key evidence, RCA continuation — 2026-11-14

### Community 123 - "Gateway Hardware SSOT — Rudolph Gateway"
Cohesion: 0.18
Nodes (11): 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates, Gateway Hardware SSOT — Rudolph Gateway, H1 (10-pin; only pins 1–5 used in the source schematic) (+3 more)

### Community 124 - ".test_guarded_app_writer_erases_only_its_page_with_installed_avrdude_dryrun"
Cohesion: 0.25
Nodes (3): 6. Verification, Host tests, CompiledHandoffTests

### Community 125 - "Tasks"
Cohesion: 0.22
Nodes (9): Tasks, ENABLE_HEARTBEAT_TASK, HEARTBEAT_NAME, HEARTBEAT_OFF_MS, HEARTBEAT_ON_MS, HEARTBEAT_PERIOD_MS, I2C_RESET_SETTLE_MS, LED1_TOGGLE_INTERVAL_MS (+1 more)

### Community 126 - "reliable_transport_test.cpp"
Cohesion: 0.36
Nodes (9): count_transition(), deliver(), dropped(), finish_reply(), loss_scenario(), main(), start_data(), stress_round_trips() (+1 more)

### Community 128 - "Command"
Cohesion: 0.15
Nodes (13): Command, budget, kind, payload, payload_length, session, stride, CommandKind (+5 more)

### Community 130 - "Baseline and scope"
Cohesion: 0.20
Nodes (8): Active hardware configuration, Baseline and scope, Environment, Historical classifications kept intact, Preservation, Scope, Diagnostic runner preflight failures, Execution journal

### Community 131 - "LoRa-only ARQ recovery — RCA continuation"
Cohesion: 0.20
Nodes (10): Acceptance verdict, Action, LoRa-only ARQ recovery — RCA continuation, Next physical decision, Observation classification, Regulatory and execution follow-up, Required final questions, Result (+2 more)

### Community 132 - "915 MHz deployment and bidirectional diagnostic verification"
Cohesion: 0.20
Nodes (9): 915 MHz deployment and bidirectional diagnostic verification, Action, Build and preservation, Evidence, Final physical status, Remaining limits, Result, Situation (+1 more)

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
Cohesion: 0.14
Nodes (10): Host tests, get_data_and_log_partitions(), open_file_in_root(), read_line(), SdFile, data_, length_, position_ (+2 more)

### Community 139 - "Program source finding — SX127x high-band mode"
Cohesion: 0.22
Nodes (9): Evidence, Observed runtime state, Program source finding — SX127x high-band mode, Smallest causal experiment, Source path, Test-first correction, Verdict, Verification in this continuation (+1 more)

### Community 140 - "Tracker Hardware SSOT — LoRa Tracker RFM"
Cohesion: 0.22
Nodes (9): 1. Board identity and components, 2. AVR128DA28 pin and net SSOT, 3. Power and startup contract, 4. Minimal firmware implementation contract, 5. Acceptance criteria / physical evidence, 6. Firmware configuration, Exact LoRa RFM95W signal map, Sources (+1 more)

### Community 141 - "PacketBoot"
Cohesion: 0.18
Nodes (10): DecodeConfig(), DecodePacketBoot(), LoadFloat(), PacketBoot, checkpoint, config, device_model, firmware (+2 more)

### Community 142 - "ControlInput"
Cohesion: 0.22
Nodes (9): ControlInput, command, digits, last_ms, reading, triggered, value, ssot::ControlInputFeed() (+1 more)

### Community 143 - "complete_campaign_logs"
Cohesion: 0.38
Nodes (4): complete_campaign_logs(), packet_event(), payload_event(), RfEvidenceTests

### Community 145 - "Comm"
Cohesion: 0.25
Nodes (8): Comm, AIR_CONFIG_NODE_ADDR, DEBUG_BAUD_RATE, ENABLE_I2C_WIRE, GATEWAY_ANYCAST_ADDR, GATEWAY_DEFAULT_ADDR, I2C_ADDRESS_BASE, I2C_ADDRESS_STRAP_SHIFT

### Community 148 - "Connect to a virtual UART on an AVR via UPDI"
Cohesion: 0.22
Nodes (8): Connect to a virtual UART on an AVR via UPDI, Demo program, License, Prerequisites, UPDI interface, Upditerm, Usage, Virtual UART

### Community 150 - "Execution journal"
Cohesion: 0.25
Nodes (8): Bring-up resume — 2026-11-14 13:16 UTC, E00 — Baseline and source references, E01 — TDD and build, E02 — Live preserved-firmware STATUS and register observation, E03 — RF/programming decision, E04 — Integrity, Execution journal, Verified bring-up implementation — 2026-11-14

### Community 151 - "UPDI-only Hello World MVP — STAR report"
Cohesion: 0.25
Nodes (7): Action, Evidence, Result, Situation, Task, UPDI-only Hello World MVP — STAR report, Verification and limits

### Community 152 - "Gateway-to-Receiver SF7 Hello World"
Cohesion: 0.25
Nodes (7): Current result — Receiver installed, normal startup unresolved, Gateway-to-Receiver SF7 Hello World, No-meter read-only hardware verified; Receiver write wiring unconfirmed, Receiver boot incompatibility, Remaining physical prerequisites, Single-packet behavior and identities, Verified software result

### Community 153 - "ssot/codec.cpp"
Cohesion: 0.26
Nodes (11): DecodePayloadFields(), EncodeControlPayload(), EncodeHeader(), ssot::AckMatches(), ssot::DecodeFrame(), ssot::DecodePayload(), ssot::EncodeAckFrame(), ssot::EncodeAckPayload() (+3 more)

### Community 154 - "Frame"
Cohesion: 0.22
Nodes (9): Frame, dst, length, payload, reason, sequence, session, src (+1 more)

### Community 157 - "Scope and baseline"
Cohesion: 0.29
Nodes (5): LoRa ARQ V1 root cause war room — 20261113T174604Z, Measurement limits, Preservation, Scope, Scope and baseline

### Community 158 - "External code and primary-source review"
Cohesion: 0.29
Nodes (5): External code and primary-source review, Manufacturer facts used, RadioLib behavior relevant to this run, Reuse decisions, Source log

### Community 159 - "Test-first and physical validation results"
Cohesion: 0.29
Nodes (7): 923 MHz continuation, Commands actually executed, Live non-RF experiment E01, Physical RF and power matrix, RED → GREEN, Software results, Test-first and physical validation results

### Community 160 - "Execution Journal"
Cohesion: 0.29
Nodes (6): Execution Journal, Experiment: Clean build matrix, Experiment: Full host regression, Experiment: Physical soak preflight gate, Experiment: Soak stage ledger and retry recovery, Experiment: Stale runner recovery

### Community 161 - "Long-Duration Hardware Soak Readiness — Final RCA Continuation"
Cohesion: 0.29
Nodes (7): A — Action, Evidence index, Long-Duration Hardware Soak Readiness — Final RCA Continuation, R — Result, Required answers, S — Situation, T — Task

### Community 162 - "Wire.h"
Cohesion: 0.22
Nodes (8): Evidence basis, H1 connector, H2 connector and board signals, Pin Mapping Audit — AVR128DA28 / RFM95W, Radio and MCU pins, RF connector path, Verification, begin()

### Community 164 - "TraceBus"
Cohesion: 0.28
Nodes (3): TraceBus, sensitivity_writes, stage

### Community 166 - "LossMetrics"
Cohesion: 0.29
Nodes (7): LossMetrics, ack_tx, attempts, duplicates, nack_tx, retries, timeouts

### Community 169 - "AdcTemp"
Cohesion: 0.17
Nodes (12): AdcTemp, ADC_MAX_COUNTS, CTRLA_ENABLE_12BIT, FIXED_POINT_SHIFT, INIT_DELAY_SETTING, KELVIN_TO_CELSIUS, MUX_TEMP_CHANNEL, PRESCALER_SETTING (+4 more)

### Community 170 - "STAR — Tracker→Rudolph receiver errata and transport follow-up"
Cohesion: 0.33
Nodes (6): A — Decision logic and execution, R — Result, proposed minimum correction and limits, Reproduce offline, S — Situation, STAR — Tracker→Rudolph receiver errata and transport follow-up, T — Task and hard constraints

### Community 172 - "Exact RadioLib and register audit"
Cohesion: 0.33
Nodes (5): Confirmed errata configuration concern, causal status UNKNOWN, Exact RadioLib and register audit, Initialization and lifecycle, Register definitions and operational evidence, Version clues, not upgrades

### Community 173 - "Hardware topology"
Cohesion: 0.33
Nodes (5): Board pin maps, Hardware topology, Image identity, Power tree, Runtime roles

### Community 174 - "Regression results"
Cohesion: 0.33
Nodes (5): Configuration and firmware builds, Evidence integrity and restoration, Hardware counts, Python, Regression results

### Community 175 - "H01 reader-free hardware result"
Cohesion: 0.33
Nodes (5): Evidence, Experiment, H01 reader-free hardware result, Interpretation, Observations

### Community 177 - "ReceiverBootTests"
Cohesion: 0.17
Nodes (3): ReceiverBootTests, page_write_command(), patch_page0()

### Community 178 - "stub/Arduino.h"
Cohesion: 0.11
Nodes (7): random(), randomSeed(), begin(), digitalWrite(), end(), ltoa(), push_back()

### Community 179 - "packets.h"
Cohesion: 0.40
Nodes (4): PacketReport, report, seq, type

### Community 180 - "AVR128DA28 LoRa firmware"
Cohesion: 0.33
Nodes (6): Application configuration, AVR128DA28 LoRa firmware, Build, Host tests, Preserved boundaries, Static analysis and formatting

### Community 185 - "PacketAck"
Cohesion: 0.33
Nodes (5): DecodePacketAck(), EncodePacketAck(), PacketAck, seq, type

### Community 186 - "UPDI first-failure boundary"
Cohesion: 0.40
Nodes (5): Actual call graph and contracts, Captured evidence, Framing, adapter and lifecycle, Manufacturer cross-check and missing telemetry, UPDI first-failure boundary

### Community 187 - "Execution journal"
Cohesion: 0.40
Nodes (4): Execution journal, Gate 1 live, Next discriminating experiment, SSOT read-only review

### Community 188 - "Experiment plan and next decision"
Cohesion: 0.40
Nodes (4): Business ranking, Completed discriminating experiments, Experiment plan and next decision, Next experiment — synchronized power/reset capture

### Community 189 - "ARQ and packet path"
Cohesion: 0.40
Nodes (4): ARQ and packet path, Historical raw incident, Normal ARQ and ACK, Reverse-raw path

### Community 190 - "Root-cause analysis"
Cohesion: 0.40
Nodes (4): Competing explanations and counterfactuals, Root-cause analysis, Track A — Gate 1 STATUS silence, Track B — reverse RF

### Community 191 - "Corrective actions"
Cohesion: 0.40
Nodes (4): Applied and verified, Corrective actions, Minimum proposed repair, Not applied

### Community 192 - "Source log"
Cohesion: 0.40
Nodes (4): Claim limits, External technical sources, Local implementation sources, Source log

### Community 193 - "Radio and protocol boundaries"
Cohesion: 0.40
Nodes (4): Radio and protocol boundaries, RadioLib and errata, Runtime configuration observed, What the H01 logs establish

### Community 194 - "Execution Summary"
Cohesion: 0.40
Nodes (4): Completed in software, Execution Summary, Next physical action, Physical work and result

### Community 195 - "RF Configuration and Toolchain Follow-up"
Cohesion: 0.40
Nodes (4): Host compiler and test stage, Remaining physical dependencies, RF Configuration and Toolchain Follow-up, Thai RF test profile

### Community 196 - "PacketAdvertise"
Cohesion: 0.33
Nodes (5): DecodePacketAdvertise(), EncodePacketAdvertise(), PacketAdvertise, seq, type

### Community 198 - "Embedded C++ readability refactor verification"
Cohesion: 0.22
Nodes (9): 1. Summary, 2. Architecture before and after, 3. C++ refactoring, 4. Readability and configuration, 5. Files changed, 7. Memory and performance, 8. Remaining risks, 9. Final assessment (+1 more)

### Community 204 - "core_test.cpp"
Cohesion: 0.40
Nodes (11): absolute_deadline(), ack_matrix(), codec(), control(), data(), fault_harness(), fresh(), main() (+3 more)

### Community 206 - "System"
Cohesion: 0.40
Nodes (5): System, ENABLE_ESPCOMM, ENABLE_LORA_RX, ENABLE_WATCHDOG, WDT_TIMEOUT_PERIOD

### Community 207 - "Evidence index"
Cohesion: 0.50
Nodes (4): 20261113T121506Z-reverse-raw, 20261113T123620Z-reverse-raw, 20261113T123837Z-standby, Evidence index

### Community 208 - "Source and transport audit"
Cohesion: 0.50
Nodes (3): Firmware command and reset-state path, Host Monitor response failure, Source and transport audit

### Community 209 - "SX127x HF-mode verification"
Cohesion: 0.50
Nodes (4): Preserved-firmware hardware baseline, Register rule and candidate, Software verification, SX127x HF-mode verification

### Community 210 - "Implementation summary"
Cohesion: 0.50
Nodes (4): Implementation summary, Implemented, Remaining physical work, Verification

### Community 211 - "Power and Interface Topology"
Cohesion: 0.50
Nodes (4): Gateway — Rudolph Gateway radio and main-board schematics, Live Host evidence and limits, Power and Interface Topology, Tracker — Tracker RFM schematic, 2025-02-16

### Community 212 - "PROGRAMMER_VERIFICATION.md"
Cohesion: 0.50
Nodes (3): Identity and non-destructive controls, Programmer Verification, Source and bounds

### Community 213 - "Reliability Results"
Cohesion: 0.50
Nodes (3): Physical results, Reliability Results, Software-only results

### Community 214 - "mvp_stub/Arduino.h"
Cohesion: 0.25
Nodes (3): CPUINT(), digitalWrite(), digitalWriteFast()

### Community 217 - "EventQueue"
Cohesion: 0.24
Nodes (6): EventQueue, count_, events_, head_, kCapacity, main()

### Community 222 - "C++ migration baseline"
Cohesion: 0.40
Nodes (5): C++ migration baseline, Dependencies and risks, Hardware and build, Original results, Source inventory

### Community 225 - "Power and reset evidence"
Cohesion: 0.67
Nodes (3): DA-specific fuse/reset interpretation, Power and reset evidence, Smallest discriminating measurements — future authorization only

### Community 230 - "Regression Results — Current Continuation"
Cohesion: 0.67
Nodes (3): Historical run results, Regression Results — Current Continuation, Test-first fixes

### Community 231 - "Sender"
Cohesion: 0.10
Nodes (20): Sender, armed, attempts, frame, has_start, interval, last_start, result (+12 more)

### Community 235 - "Ownership Map"
Cohesion: 0.50
Nodes (3): 6. Build isolation and migration constraints, Ownership Map, loop()

### Community 236 - "PacketMaintenance"
Cohesion: 0.33
Nodes (5): DecodePacketMaintenance(), EncodePacketMaintenance(), PacketMaintenance, command, type

### Community 237 - "ExcludedSx1262Experiment"
Cohesion: 0.20
Nodes (10): ExcludedSx1262Experiment, BUSY_PIN, DIO1_PIN, ERROR_RETRY_DELAY_MS, NSS_PIN, PACKET_BYTES, PACKET_COUNT, PACKET_GAP_MS (+2 more)

### Community 260 - "Result"
Cohesion: 0.22
Nodes (8): Result, kAccepted, kAckTimeout, kInvalidArgument, kPending, kRadioError, kRejected, kTxTimeout

### Community 264 - "string"
Cohesion: 0.06
Nodes (8): Build and restore, Existing protocol and evidence names, LoRa-only diagnostic implementation, Scope and baseline, Source and test boundaries, Startup sequence, main(), reset_radio()

### Community 299 - "sleep.cpp"
Cohesion: 0.16
Nodes (6): SetUnixTime(), SleepFor(), PowerSavingTaskScheduler, GetTotalSeconds(), InitializeTime(), SetTime()

### Community 304 - "State"
Cohesion: 0.22
Nodes (8): State, kComplete, kFailed, kRetryPending, kRxWait, kTxData, kTxResponse, kWaitResponse

### Community 309 - "reader_free_h01_summary"
Cohesion: 0.33
Nodes (4): TDD and diagnostic-tool changes, Test-harness dispatch mistake, reader_free_h01_summary(), frame_seen()

### Community 313 - "lora/library.json"
Cohesion: 0.25
Nodes (8): jgromes/RadioLib, build, includeDir, srcDir, dependencies, jgromes/RadioLib@7.1.2, name, version

### Community 315 - "time-utils/library.json"
Cohesion: 0.25
Nodes (8): paulstoffregen/Time, build, includeDir, srcDir, dependencies, paulstoffregen/Time@^1.6.1, name, version

### Community 318 - "require_preserved"
Cohesion: 0.15
Nodes (3): ApplicationPageWriteTests, command(), require_preserved()

### Community 319 - "usb_inventory.py"
Cohesion: 0.15
Nodes (6): discover_usb_devices(), InventoryResult, _normalize_hex(), parse_udev_properties(), _run_command(), _usb_instance()

### Community 332 - "Proposed discriminating experiments — NOT executed or authorized here"
Cohesion: 0.33
Nodes (5): Evidence-ranked hypothesis matrix, Gate 1 — transport and power evidence, Gate 2 — receiver-only IF A/B, Gate 3 — reference isolation and business ranking, Proposed discriminating experiments — NOT executed or authorized here

### Community 335 - "RestartTask"
Cohesion: 0.33
Nodes (3): RestartTask, completions, entries

### Community 336 - "PacketMaintenanceAck"
Cohesion: 0.33
Nodes (5): DecodePacketMaintenanceAck(), EncodePacketMaintenanceAck(), PacketMaintenanceAck, response, type

### Community 337 - "Regression Matrix"
Cohesion: 0.33
Nodes (5): C++ comments, Firmware builds, Physical hardware, Regression Matrix, Session and duplicate behavior

### Community 338 - "Baseline Graph"
Cohesion: 0.40
Nodes (4): Baseline Graph, Graph tools, Hardware baseline, Source-confirmed paths

### Community 341 - "ใช้งาน Codex Goal — LoRa E2E Feature-Based"
Cohesion: 0.40
Nodes (4): ความต่างระหว่าง Goal กับ config, จุดที่ต้องพิสูจน์, แหล่งอ้างอิง, ใช้งาน Codex Goal — LoRa E2E Feature-Based

### Community 342 - "PacketReportWithAck"
Cohesion: 0.40
Nodes (4): PacketReportWithAck, report, seq, type

### Community 359 - "Real-Radio Evidence"
Cohesion: 0.33
Nodes (5): Board identity and current installation, Current application images, Physical RF acceptance, Real-Radio Evidence, Software verification

## Knowledge Gaps
- **571 isolated node(s):** `LED1`, `LED2`, `LED_ON_LEVEL`, `LED_OFF_LEVEL`, `ANALOG_IN_0` (+566 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1922 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **177 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SX1276` connect `SX1276` to `string`, `radio_link.cpp`, `Exact RadioLib and register audit`, `LoRa`, `Module`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **What connects `LED1`, `LED2`, `LED_ON_LEVEL` to the rest of the system?**
  _571 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.07523510971786834 - nodes in this community are weakly interconnected._
- **Why does `Transport` connect `Transport` to `Result`, `Event`, `Pair`, `State`, `.EmitEvent`, `stdint`, `reliable_transport_test.cpp`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Should `rf_proof.py` be split into smaller, more focused modules?**
  _Cohesion score 0.083089905874716 - nodes in this community are weakly interconnected._
- **Why does `Sender` connect `Sender` to `core_test.cpp`, `sender.cpp`, `SenderState`, `Result`, `Receiver`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Should `Storage` be split into smaller, more focused modules?**
  _Cohesion score 0.09401709401709402 - nodes in this community are weakly interconnected._