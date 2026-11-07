# Graph Report - lora  (2026-11-07)

## Corpus Check
- 113 files · ~96,845 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 76 file(s) not represented in the graph (top: .bin 39, .d2 18, (none) 9)

## Summary
- 1352 nodes · 2448 edges · 86 communities (64 shown, 22 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 260 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c29e43c9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- detect_devices.py
- usb_inventory.py
- FIRMWARE MVP EXECUTION MODE
- role_detector.py
- HardwareGateTests
- lora.cpp
- src/receiver/main.cpp
- Campaign
- generate_lora_config.py
- firmware_identity.py
- SEO optimization
- Python Testing Patterns — Advanced Reference
- Rendering
- main
- upditerm.py
- DetectedDevice
- .test_no_meter_identity_uses_live_unique_serial_without_checklist
- LoRa
- D2 — Modern Diagram Generation
- cstring
- Python Code Executor
- lib/main.cpp
- MvpRoundtripTests
- TaskLoraRx
- Fundamental Patterns
- require
- demo.c
- hello_protocol.h
- D2 — Modern Diagram Generation
- espcomm.cpp
- LiveProofTests
- lora_rx.cpp
- Syntax cheat-sheet (most-used)
- device
- subprocess
- Gateway-to-Receiver SF7 Hello World
- Accessibility (a11y)
- .parser
- SX1276
- Theme (color palette) — ask the user first
- WCAG 2.2 Quick Reference
- Port
- Accessibility Code Patterns
- Operable
- State
- Design principles — what makes the output "professional"
- Connect to a virtual UART on an AVR via UPDI
- Common ARIA patterns
- Understandable
- D2-Diagram-Skill
- SenderOneShotTests
- role_log.h
- D2-Diagram-Skill
- Syntax cheat-sheet (most-used)
- role_log_test.cpp
- Frontend Design
- State
- Design principles — what makes the output "professional"
- Gateway Hardware SSOT — Rudolph Gateway
- Specialized diagram syntax (quick reference)
- library.json
- FlashSafetyTests
- Bash Defensive Patterns
- updi_probe.py
- Common issues by impact
- hello_protocol.cpp
- Testing checklist
- rf_proof.py
- EepromBoundary
- DuplicateTracker
- lora
- main
- State
- updi-baseline/src/receiver/main.cpp
- RadioLib.h

## God Nodes (most connected - your core abstractions)
1. `LoRa` - 40 edges
2. `State` - 29 edges
3. `HardwareGateTests` - 29 edges
4. `SX1276` - 27 edges
5. `rf_test()` - 24 edges
6. `TaskLoraRx` - 22 edges
7. `main()` - 21 edges
8. `effective_platformio_config()` - 19 edges
9. `updi_role_log()` - 18 edges
10. `Campaign` - 17 edges

## Surprising Connections (you probably didn't know these)
- `Shapes` --references--> `step()`  [INFERRED]
  .agents/skills/d2/SKILL.md → tests/mvp_board.cpp
- `Shapes` --references--> `step()`  [INFERRED]
  .claude/skills/d2/SKILL.md → tests/mvp_board.cpp
- `SQL table (ERD)` --references--> `unique()`  [INFERRED]
  .agents/skills/d2/SKILL.md → tools/rf_proof.py
- `SQL table (ERD)` --references--> `unique()`  [INFERRED]
  .claude/skills/d2/SKILL.md → tools/rf_proof.py
- `Style (use sparingly — prefer classes)` --references--> `lines()`  [INFERRED]
  .agents/skills/d2/SKILL.md → tools/rf_proof.py

## Import Cycles
- None detected.

## Communities (86 total, 22 thin omitted)

### Community 0 - "detect_devices.py"
Cohesion: 0.18
Nodes (11): build_parser(), _load_registry(), main(), _print_result(), _run_self_test(), SafetyArgumentParser, _watch(), ScanResult (+3 more)

### Community 1 - "usb_inventory.py"
Cohesion: 0.19
Nodes (7): discover_usb_devices(), InventoryResult, _normalize_hex(), parse_udev_properties(), _run_command(), start_udev_monitor(), _usb_instance()

### Community 3 - "FIRMWARE MVP EXECUTION MODE"
Cohesion: 0.20
Nodes (9): Deployment, Execution Priority, FIRMWARE MVP EXECUTION MODE, Hardware Scope, Mission, Output, Physical Radio Execution, Preserve SSOT (+1 more)

### Community 4 - "role_detector.py"
Cohesion: 0.21
Nodes (7): USBDevice, classify_devices(), diff_device_presence(), _identity_role(), _probe_for(), _registry_hint(), _registry_record()

### Community 7 - "src/receiver/main.cpp"
Cohesion: 0.29
Nodes (3): init_receiver_gpio(), setup(), main()

### Community 8 - "Campaign"
Cohesion: 0.20
Nodes (5): Campaign, destination_, single_packet_, source_, main()

### Community 9 - "generate_lora_config.py"
Cohesion: 0.13
Nodes (11): ConfigurationTests, ReceiverHardwareTests, artifacts(), canonical(), digest(), generate(), source_fingerprint(), load() (+3 more)

### Community 10 - "firmware_identity.py"
Cohesion: 0.25
Nodes (9): FirmwareIdentity, crc8(), FingerprintResult, FirmwareReference, IdentityParseResult, match_flash_fingerprint(), parse_identity_stream(), _valid_build() (+1 more)

### Community 12 - "SEO optimization"
Cohesion: 0.05
Nodes (38): Article, Breadcrumbs, FAQ, Organization, Product, Structured data reference, Validation, Agentic browsing and AI discoverability (+30 more)

### Community 14 - "Python Testing Patterns — Advanced Reference"
Cohesion: 0.05
Nodes (35): CI/CD Integration, Configuration Files, Pattern 10: Property-Based Testing, Pattern 6: Testing Async Code, Pattern 7: Monkeypatch for Testing, Pattern 8: Temporary Files and Directories, Pattern 9: Custom Fixtures and Conftest, Python Testing Patterns — Advanced Reference (+27 more)

### Community 15 - "Rendering"
Cohesion: 0.50
Nodes (4): Direct d2 CLI (when you need full control), Output format → renderer, Quick render (recommended), Rendering

### Community 16 - "main"
Cohesion: 0.27
Nodes (4): complete_tx(), deliver(), main(), reset_radio()

### Community 17 - "upditerm.py"
Cohesion: 0.06
Nodes (11): Console, cleanup(), error(), main(), parse_arguments(), SerialPort, SerialUPDI, session() (+3 more)

### Community 20 - "LoRa"
Cohesion: 0.10
Nodes (20): LoRa, _active_radio, _cs_pin, _initialized, kMaxPayloadSize, kRadioHeaderSize, kSx127xVersionAlternate, kSx127xVersionOfficial (+12 more)

### Community 21 - "D2 — Modern Diagram Generation"
Cohesion: 0.14
Nodes (13): Common pitfalls (read these once), Core workflow, Custom palette via `theme-overrides`, D2 — Modern Diagram Generation, Diagram families → templates, Full palette catalog, Multi-board composition (when one board isn't enough), Professional defaults — always apply these (+5 more)

### Community 22 - "cstring"
Cohesion: 0.40
Nodes (3): EepromSpy, reads, writes

### Community 33 - "Python Code Executor"
Cohesion: 0.08
Nodes (24): 3D Model Processing, 3D Processing, API Calls, App Details, Data Analysis with Visualization, Data Processing, Documentation, Documents & Graphics (+16 more)

### Community 34 - "lib/main.cpp"
Cohesion: 0.11
Nodes (5): init_gpio(), loop(), ReadTemperatureCelsius(), TaskHeartbeat, _ts

### Community 35 - "MvpRoundtripTests"
Cohesion: 0.26
Nodes (3): Board, frames(), MvpRoundtripTests

### Community 36 - "TaskLoraRx"
Cohesion: 0.10
Nodes (16): TaskLoraRx, _ack, _ack_bytes, _campaign_id, _dst, _flags, _id, _len (+8 more)

### Community 37 - "Fundamental Patterns"
Cohesion: 0.09
Nodes (21): 1. Strict Mode, 2. Error Trapping and Cleanup, 3. Variable Safety, 4. Array Handling, 5. Conditional Safety, Advanced Defensive Techniques, bash-defensive-patterns — detailed patterns and worked examples, Core Defensive Principles (+13 more)

### Community 38 - "require"
Cohesion: 0.10
Nodes (9): DetectionIntegrationTests, pio(), runner(), require(), crc8(), FirmwareIdentityTests, ihex_record(), marker() (+1 more)

### Community 44 - "demo.c"
Cohesion: 0.13
Nodes (10): dump(), main(), pwm_init(), pwm_set(), updi_getchar(), updi_putchar(), updi_stdio_init(), updi_uart_rx() (+2 more)

### Community 47 - "hello_protocol.h"
Cohesion: 0.11
Nodes (8): ControlInput, command_, digits_, last_ms_, reading_, triggered_, value_, feed()

### Community 48 - "D2 — Modern Diagram Generation"
Cohesion: 0.14
Nodes (13): Common pitfalls (read these once), Core workflow, D2 — Modern Diagram Generation, Diagram families → templates, Direct d2 CLI (when you need full control), Multi-board composition (when one board isn't enough), Output format → renderer, Professional defaults — always apply these (+5 more)

### Community 50 - "espcomm.cpp"
Cohesion: 0.11
Nodes (13): DecodeLoraConfig(), LoraConfig, addr, freq, long_range, tx_power, StoreI2c16(), TaskI2CManager (+5 more)

### Community 54 - "LiveProofTests"
Cohesion: 0.06
Nodes (12): fixture(), add(), boot(), LiveProofTests, emit(), start(), write(), ApplicationPageWriteTests (+4 more)

### Community 55 - "lora_rx.cpp"
Cohesion: 0.09
Nodes (17): Shapes, Shapes, espcomm_setup(), CampaignBuildGateResult, AlreadyRun, ReadbackFailed, Ready, claim_campaign_build() (+9 more)

### Community 57 - "Syntax cheat-sheet (most-used)"
Cohesion: 0.20
Nodes (10): Connections, Containers, Icons, Local icon library — check first, Markdown labels (C4-style hierarchy), Style (use sparingly — prefer classes), Syntax cheat-sheet (most-used), Title and legend (+2 more)

### Community 61 - "device"
Cohesion: 0.19
Nodes (9): DeviceReconnectTests, make_device(), make_probe(), require(), device(), probe(), require(), RoleDetectorTests (+1 more)

### Community 62 - "subprocess"
Cohesion: 0.06
Nodes (17): build_d2_command(), main(), parse_d2_config(), render_one(), build_d2_command(), main(), parse_d2_config(), render_one() (+9 more)

### Community 68 - "Gateway-to-Receiver SF7 Hello World"
Cohesion: 0.25
Nodes (7): Current result — Receiver installed, normal startup unresolved, Gateway-to-Receiver SF7 Hello World, No-meter read-only hardware verified; Receiver write wiring unconfirmed, Receiver boot incompatibility, Remaining physical prerequisites, Single-packet behavior and identities, Verified software result

### Community 75 - "Accessibility (a11y)"
Cohesion: 0.17
Nodes (12): Accessibility (a11y), ARIA usage (4.1.2), Color contrast (1.4.3, 1.4.6), Conformance levels, Evidence-led audit workflow, Live regions (4.1.3), Media alternatives (1.2), Perceivable (+4 more)

### Community 79 - ".parser"
Cohesion: 0.38
Nodes (4): complete_campaign_logs(), packet_event(), payload_event(), RfEvidenceTests

### Community 82 - "Theme (color palette) — ask the user first"
Cohesion: 0.50
Nodes (4): Custom palette via `theme-overrides`, Full palette catalog, Theme (color palette) — ask the user first, Topic-matched palette picker

### Community 83 - "WCAG 2.2 Quick Reference"
Cohesion: 0.18
Nodes (8): Level A (minimum), Level AA (standard), Level AAA (enhanced), Sources, Success criteria by level, Testing tools, WCAG 2.2 Quick Reference, What changed from 2.1 to 2.2

### Community 95 - "Port"
Cohesion: 0.25
Nodes (4): Port, require(), USBInventoryTests, run()

### Community 98 - "Accessibility Code Patterns"
Cohesion: 0.22
Nodes (9): Accessibility Code Patterns, ARIA tabs, Dragging movements, Error handling, Form labels, Live regions and notifications, Modal focus trap, Screen reader commands (+1 more)

### Community 99 - "Operable"
Cohesion: 0.22
Nodes (9): Dragging movements (2.5.7) — new in 2.2, Focus not obscured (2.4.11) — new in 2.2, Focus visible (2.4.7), Keyboard accessible (2.1), Motion (2.3), Operable, Skip links (2.4.1), Target size (2.5.8) — new in 2.2 (+1 more)

### Community 102 - "State"
Cohesion: 0.07
Nodes (29): State, airtime_length, airtime_us, bandwidth_khz, begin_calls, begin_status, coding_rate, config_status (+21 more)

### Community 104 - "Design principles — what makes the output "professional""
Cohesion: 0.22
Nodes (9): Animation — only on actual data flow, Color discipline, Connections, Design principles — what makes the output "professional", Direction, Hierarchy & scope, Labels, Shape vocabulary — match the shape to the concept (+1 more)

### Community 114 - "Connect to a virtual UART on an AVR via UPDI"
Cohesion: 0.22
Nodes (8): Connect to a virtual UART on an AVR via UPDI, Demo program, License, Prerequisites, UPDI interface, Upditerm, Usage, Virtual UART

### Community 115 - "Common ARIA patterns"
Cohesion: 0.25
Nodes (8): Buttons, Common ARIA patterns, Error states, Form fields, Links, Live regions, Modals, Navigation

### Community 116 - "Understandable"
Cohesion: 0.25
Nodes (8): Accessible authentication (3.3.8) — new in 2.2, Consistent help (3.2.6) — new in 2.2, Consistent navigation (3.2.3), Error handling (3.3.1, 3.3.3), Form labels (3.3.2), Page language (3.1.1), Redundant entry (3.3.7) — new in 2.2, Understandable

### Community 117 - "D2-Diagram-Skill"
Cohesion: 0.25
Nodes (7): D2-Diagram-Skill, Installation, License, Requirements, Usage, What it does, What you get

### Community 119 - "role_log.h"
Cohesion: 0.29
Nodes (18): updi_role_log(), updi_role_log_airtime(), updi_role_log_boot(), updi_role_log_campaign(), updi_role_log_identity(), updi_role_log_identity_crc8(), updi_role_log_packet(), updi_role_log_payload() (+10 more)

### Community 121 - "D2-Diagram-Skill"
Cohesion: 0.25
Nodes (7): D2-Diagram-Skill, Installation, License, Requirements, Usage, What it does, What you get

### Community 122 - "Syntax cheat-sheet (most-used)"
Cohesion: 0.29
Nodes (7): Connections, Containers, Icons, Local icon library — check first, Markdown labels (C4-style hierarchy), Syntax cheat-sheet (most-used), Title and legend

### Community 130 - "Frontend Design"
Cohesion: 0.29
Nodes (6): Design principles, Frontend Design, Ground your designs in the subject matter, More on writing in design, Process: plan, review against the brief, build, critique, Restraint and self-critique

### Community 132 - "State"
Cohesion: 0.06
Nodes (24): Evidence basis, H1 connector, H2 connector and board signals, Pin Mapping Audit — AVR128DA28 / RFM95W, Radio and MCU pins, RF connector path, Verification, CPUINT() (+16 more)

### Community 140 - "Design principles — what makes the output "professional""
Cohesion: 0.22
Nodes (9): Animation — only on actual data flow, Color discipline, Connections, Design principles — what makes the output "professional", Direction, Hierarchy & scope, Labels, Shape vocabulary — match the shape to the concept (+1 more)

### Community 148 - "Gateway Hardware SSOT — Rudolph Gateway"
Cohesion: 0.10
Nodes (19): 1. System topology, 2. Daughterboard MCU and RFM95W SSOT, 3. Daughterboard external connectors, 4. Four module slot mappings from Main Board, 5. Power, RF and hardware safety, 6. Minimal validation gates, Gateway Hardware SSOT — Rudolph Gateway, H1 (10-pin; only pins 1–5 used in the source schematic) (+11 more)

### Community 150 - "Specialized diagram syntax (quick reference)"
Cohesion: 0.18
Nodes (11): Grid / matrix, Sequence diagram, Specialized diagram syntax (quick reference), SQL table (ERD), UML class, Grid / matrix, Sequence diagram, Specialized diagram syntax (quick reference) (+3 more)

### Community 151 - "library.json"
Cohesion: 0.33
Nodes (5): jgromes/RadioLib, dependencies, jgromes/RadioLib, name, version

### Community 153 - "Bash Defensive Patterns"
Cohesion: 0.40
Nodes (4): Bash Defensive Patterns, Best Practices Summary, Detailed patterns and worked examples, When to Use This Skill

### Community 252 - "updi_probe.py"
Cohesion: 0.20
Nodes (12): _probe_device(), _scan(), ProbeEvidence, firmware_fingerprint_evidence(), identify_mcu(), _is_access_error(), _port_busy(), probe_firmware_identity() (+4 more)

### Community 260 - "Common issues by impact"
Cohesion: 0.50
Nodes (4): Common issues by impact, Critical (fix immediately), Moderate (fix soon), Serious (fix before launch)

### Community 263 - "hello_protocol.cpp"
Cohesion: 0.36
Nodes (6): encode_ack_frame(), encode_ack_payload(), encode_data_frame(), encode_data_payload(), encode_header(), encode_nack_payload()

### Community 272 - "Testing checklist"
Cohesion: 0.67
Nodes (3): Automated testing, Manual testing, Testing checklist

### Community 285 - "rf_proof.py"
Cohesion: 0.06
Nodes (71): BootAnalysisTests, analyze(), main(), normalize_ihex_region(), _parse_ihex(), ihex(), install(), load_package() (+63 more)

### Community 298 - "EepromBoundary"
Cohesion: 0.25
Nodes (6): EepromBoundary, reads, stored, writes, written_bytes, wrong_address

### Community 300 - "DuplicateTracker"
Cohesion: 0.29
Nodes (5): DuplicateTracker, campaign_id_, initialized_, seen_, source_

### Community 312 - "main"
Cohesion: 0.19
Nodes (13): ack_matches(), campaign_build_id(), decode_frame(), decode_payload(), Frame, campaign_id, destination, sequence (+5 more)

### Community 313 - "State"
Cohesion: 0.33
Nodes (6): State, TEST_ARMED, TEST_COMPLETED, TEST_FAILED, TEST_IDLE, TEST_RUNNING

## Knowledge Gaps
- **116 isolated node(s):** `lora`, `jgromes/RadioLib`, `kRadioHeaderSize`, `kMaxPayloadSize`, `kSx127xVersionRegister` (+111 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 624 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `lines()` connect `Syntax cheat-sheet (most-used)` to `device`, `rf_proof.py`?**
  _High betweenness centrality (0.327) - this node is a cross-community bridge._
- **What connects `lora`, `jgromes/RadioLib`, `kRadioHeaderSize` to the rest of the system?**
  _116 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `HardwareGateTests` be split into smaller, more focused modules?**
  _Cohesion score 0.11578947368421053 - nodes in this community are weakly interconnected._
- **Why does `rf_test()` connect `rf_proof.py` to `detect_devices.py`, `HardwareGateTests`, `upditerm.py`, `Syntax cheat-sheet (most-used)`, `device`?**
  _High betweenness centrality (0.319) - this node is a cross-community bridge._
- **Should `generate_lora_config.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13054187192118227 - nodes in this community are weakly interconnected._
- **Should `SEO optimization` be split into smaller, more focused modules?**
  _Cohesion score 0.05 - nodes in this community are weakly interconnected._
- **Should `Python Testing Patterns — Advanced Reference` be split into smaller, more focused modules?**
  _Cohesion score 0.05263157894736842 - nodes in this community are weakly interconnected._