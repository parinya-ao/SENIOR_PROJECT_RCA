# Graph Report - lora  (2026-10-27)

## Corpus Check
- 2784 files · ~2,164,560 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 482 file(s) not represented in the graph (top: .stderr 136, .stdout 136, .sha256 87)

## Summary
- 2794 nodes · 4644 edges · 179 communities (127 shown, 52 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 263 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c31d7e4b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Q host inventory — RCA_POST_SWAP_01 / CROSSED_UNTOUCHED
- updi_uart.c
- UPDI
- UPDI
- probes.py
- TransportTests
- PymcuprogSerialUpdiNvmTimeout
- Connect to a virtual UART on an AVR via UPDI
- AVR128DA28 UPDI console engineering report
- SEO optimization
- backend.py
- updi-progress.md
- updi-sib.sh
- lora
- hexfileutils.py
- pymcuprog.py
- cp210x.c
- upditerm.py
- Programmer
- finalize.py
- test_post_swap.py
- UpdiDatalink
- pymcuprog_main.py
- Avr32Device
- UPDI
- Changelog
- RCA.md
- enum
- NvmUpdiP3
- Optional arguments and switches
- PymcuprogError
- NvmAccessProviderCmsisDapXmega
- pymcuprog - Python MCU programmer
- Python Testing Patterns — Advanced Reference
- NvmUpdiP0
- Backend
- sys
- NvmUpdiP5
- test_fresh.py
- Design principles — what makes the output "professional"
- Per-attempt evidence and timing
- test_identity.py
- pathlib
- AvrDevice
- TinyXAvrTarget
- Design principles — what makes the output "professional"
- AVR128DA28 UPDI root-cause report
- cp210x.c
- samtarget.py
- time
- os
- SamD2xTarget
- Fresh UPDI RCA — RCA_FRESH_01
- UpdiApplication
- test_classifier.py
- Optional arguments and switches
- Specialized diagram syntax (quick reference)
- .claude/skills/d2/render.py
- D2 — Modern Diagram Generation
- classify_pairing_matrix
- pymcuprog/nvm.py
- D2 — Modern Diagram Generation
- How to run an RCA: the actual process
- MegaAvrJtagTarget
- NvmAccessProviderCmsisDapMegaAvrJtag
- UpdiPhysical
- ScratchTests
- PROMPT.md
- Console
- Frequently asked questions
- UPDI
- Python Code Executor
- NvmUpdiP4
- Fundamental Patterns
- fresh.py
- Common mistakes that make RCA useless
- The five RCA methods, explained with worked examples
- Usage
- snapshot_pairing
- classify.py
- test_board_swap.py
- When RCA is worth running
- RCA_POST_SWAP_01 — Lane P inventory
- AvrDebugger
- Dut
- 14. Phase-by-phase investigation
- Official-source review: AVR128DA target and power path
- Investigation Handoff
- classify_crossover
- Connect to a virtual UART on an AVR via UPDI
- AVR128DA28 UPDI RCA — Continuation `RCA_CROSSOVER_01`
- test_continuation.py
- Console
- Accessibility (a11y)
- Syntax cheat-sheet (most-used)
- Lane A
- _ReadOnlyLink
- WCAG 2.2 Quick Reference
- Target Electrical Investigator — RCA_PHY_01
- Focused physical-layer RCA plan
- 17. Hypothesis inventory and evidence model
- .test_reader_and_writer_failures_reach_wait_and_stop_both_workers
- AVR128DA28 board-swap RCA — PRE NO-GO checkpoint
- Tasks
- Accessibility Code Patterns
- Operable
- Common ARIA patterns
- Understandable
- D2-Diagram-Skill
- Syntax cheat-sheet (most-used)
- UpdiPhysical
- D2-Diagram-Skill
- STAR
- Frontend Design
- 19. Evidence standards for root-cause claims
- Lane B
- 11. TDD requirements for host automation
- Bash Defensive Patterns
- AVR128DA28 Dual-Board UPDI Root-Cause Analysis
- 5. Two-subagent architecture: exactly two workers
- Common issues by impact
- Continuation State
- 4. Hard safety and scope constraints
- 8. Persistent memory policy
- Testing checklist
- demo.c
- Evidence log
- Investigation Sources
- AVR128DA28 UPDI root-cause investigation
- terminal-observation-20261026.md
- updi_uart_rx
- Post-swap physical freeze
- updi-rca
- Result
- identity.py
- NvmAccessProviderCmsisDapDebugwire
- Board Swap RCA State
- Handoff — `RCA_CROSSOVER_01`
- hashlib
- Untouched crossed-state implementation plan
- test_probes.py
- test_physical.py
- FOCUSED_STAR_RCA.md
- RCA_PHY_01 — External Path Investigator
- capture_inventory.sh
- Lane B pre-crossover execution record
- preflight.sh
- STAR_BOARD_SWAP_RCA.md
- AVR128DA28 BREAK / LOCAL_ECHO focused RCA
- RCA_BOARD_SWAP_01 execution plan
- argparse
- Path Q lane — RCA_BOARD_SWAP_01
- Board Swap Evidence Log
- Board-swap physical freeze
- Result
- Fresh Q ownership check — read only
- Q PRE host-tool failures
- SWAP_DECISIONS.md
- Q crossed-untouched SIB-only batch — POST-00130
- ._log_incomplete_stack
- AVR128DA28 untouched crossed-state RCA
- Post-swap handoff
- Stable identity and path
- Post-swap RCA state
- fresh/STAR_RCA.md
- POST_SWAP_DECISIONS.md
- POST_SWAP_EVIDENCE_LOG.md
- POST_SWAP_SOURCES.md
- AVR128DA28 Dual-Board UPDI Root-Cause Investigation Agent Prompt

## God Nodes (most connected - your core abstractions)
1. `Backend` - 48 edges
2. `PymcuprogError` - 46 edges
3. `AvrDebugger` - 38 edges
4. `PymcuprogSerialUpdiNvmTimeout` - 38 edges
5. `UpdiApplication` - 33 edges
6. `Per-attempt evidence and timing` - 32 edges
7. `PymcuprogNotSupportedError` - 31 edges
8. `SamD2xTarget` - 26 edges
9. `NvmUpdi` - 24 edges
10. `Programmer` - 23 edges

## Surprising Connections (you probably didn't know these)
- ``hypothesis_status.csv`` --references--> `confidence_label()`  [INFERRED]
  PROMPT.md → experiments/updi_rca/src/updi_rca/classify.py
- `FLAG_RX follow-up decision` --references--> `updi_uart_rx()`  [INFERRED]
  experiments/updi_rca/memory/DECISIONS.md → external/upditerm/updi_uart.c
- `Read-only GPR2 / FLAG_RX follow-up` --references--> `updi_uart_rx()`  [INFERRED]
  experiments/updi_rca/memory/EVIDENCE_LOG.md → external/upditerm/updi_uart.c
- `Follow-up GPR2 / FLAG_RX reads` --references--> `updi_uart_rx()`  [INFERRED]
  experiments/updi_rca/memory/LANE_A.md → external/upditerm/updi_uart.c
- `FLAG_RX read-only follow-up` --references--> `updi_uart_rx()`  [INFERRED]
  experiments/updi_rca/reports/STAR_RCA.md → external/upditerm/updi_uart.c

## Import Cycles
- 1-file cycle: `.automation/research/pymcuprog/pymcuprog/pymcuprog.py -> .automation/research/pymcuprog/pymcuprog/pymcuprog.py`

## Communities (179 total, 52 thin omitted)

### Community 0 - "Q host inventory — RCA_POST_SWAP_01 / CROSSED_UNTOUCHED"
Cohesion: 0.15
Nodes (13): dmesg, Existing software identifiers (read-only), fuser, journalctl, Kernel log availability, lsof, Port ownership, Probe gate and proposed command (not run) (+5 more)

### Community 1 - "updi_uart.c"
Cohesion: 0.17
Nodes (6): loop(), UpdiWrite(), updi_uart_enabled(), updi_uart_rx_poll(), updi_uart_tx(), loop()

### Community 2 - "UPDI"
Cohesion: 0.11
Nodes (4): SerialPort, SerialUPDI, TransportError, UPDI

### Community 3 - "UPDI"
Cohesion: 0.07
Nodes (6): error(), SerialPort, SerialUPDI, Terminal, TransportError, UPDI

### Community 4 - "probes.py"
Cohesion: 0.14
Nodes (18): Approved PRE SIB batch, main(), _parser(), collect_ocd_messages(), _event_bytes(), _live_adapter(), ProbeResult, run_control_read() (+10 more)

### Community 6 - "PymcuprogSerialUpdiNvmTimeout"
Cohesion: 0.05
Nodes (5): PymcuprogSerialUpdiNvmError, PymcuprogSerialUpdiNvmTimeout, NvmUpdi, NvmUpdiP2, Timeout

### Community 7 - "Connect to a virtual UART on an AVR via UPDI"
Cohesion: 0.22
Nodes (8): Connect to a virtual UART on an AVR via UPDI, Demo program, License, Prerequisites, UPDI interface, Upditerm, Usage, Virtual UART

### Community 8 - "AVR128DA28 UPDI console engineering report"
Cohesion: 0.18
Nodes (9): 1. Outcome, 2. Proven findings and remaining cause, 3. Hardware and baud, 4. Implementation and compatibility, 5. Verification and acceptance, 6. Commands and reproducible diffs, 7. Delivery limits and next required evidence, AVR128DA28 UPDI console engineering report (+1 more)

### Community 9 - "SEO optimization"
Cohesion: 0.05
Nodes (38): Article, Breadcrumbs, FAQ, Organization, Product, Structured data reference, Validation, Agentic browsing and AI discoverability (+30 more)

### Community 10 - "backend.py"
Cohesion: 0.07
Nodes (9): PymcuprogNotSupportedError, pad_to_size(), pagealign(), read_supply_voltage_setpoint(), read_target_voltage(), read_tool_info(), read_usb_voltage(), read_voltage_parameter() (+1 more)

### Community 16 - "hexfileutils.py"
Cohesion: 0.17
Nodes (6): _add_data_to_hex(), read_memories_from_hex(), remove_phantom_bytes(), _write_hex_to_file(), write_memories_to_hex(), write_memory_to_hex()

### Community 17 - "pymcuprog.py"
Cohesion: 0.19
Nodes (3): _parse_literal(), main(), setup_logging()

### Community 18 - "cp210x.c"
Cohesion: 0.06
Nodes (46): cp2102_determine_quirks(), cp2102n_gpioconf_init(), cp2104_gpioconf_init(), cp2105_gpioconf_init(), cp2108_gpio_init(), cp210x_attach(), cp210x_break_ctl(), cp210x_change_speed() (+38 more)

### Community 19 - "upditerm.py"
Cohesion: 0.15
Nodes (5): error(), main(), parse_arguments(), session(), Terminal

### Community 21 - "finalize.py"
Cohesion: 0.08
Nodes (42): read_csv(), _all_run_rows(), canonical_attempt_paths(), classify_raw_event(), _event_rows(), _failure_stage(), finalize(), _hash_summary() (+34 more)

### Community 22 - "test_post_swap.py"
Cohesion: 0.29
Nodes (9): assess(), test_both_fail_does_not_claim_two_failed_boards(), test_both_pass_classifies_intervention_sensitive(), test_failure_movement_to_target_classifies_target_following(), test_failure_staying_on_path_classifies_path_following(), test_post_swap_phase_preserves_original_history(), test_power_cycle_is_recorded_as_confound(), test_raw_log_hashes_are_preserved() (+1 more)

### Community 24 - "pymcuprog_main.py"
Cohesion: 0.06
Nodes (30): SessionConfig, _action_erase(), _action_getsupplyvoltage(), _action_getusbvoltage(), _action_getvoltage(), _action_makeuf2(), _action_ping(), _action_read() (+22 more)

### Community 26 - "UPDI"
Cohesion: 0.12
Nodes (3): SerialPort, SerialUPDI, UPDI

### Community 27 - "Changelog"
Cohesion: 0.06
Nodes (33): [], [3.10] - October 2021, [3.13] - May 2022, [3.14] - October 2022, [3.16] - November 2023, [3.17] - March 2024, [3.19] - June 2025, [3.1.3] - June 2020 (+25 more)

### Community 28 - "RCA.md"
Cohesion: 0.22
Nodes (8): Current AVR128DA28 investigation — RCA_FRESH_01, Final thoughts, How to choose the right RCA method, How to write an RCA report, Introduction, Root cause vs. contributing factor vs. symptom, What is root cause analysis?, What weak vs. strong corrective actions look like

### Community 31 - "Optional arguments and switches"
Cohesion: 0.07
Nodes (27): Actions (commands), Administrative arguments, Examples, General arguments, Memory access actions, Memory access arguments, Memory types, Optional arguments and switches (+19 more)

### Community 32 - "PymcuprogError"
Cohesion: 0.05
Nodes (6): NvmAccessProviderCmsisDapUpdi, PymcuprogDeviceLockedError, PymcuprogEraseError, PymcuprogError, PymcuprogSessionError, PymcuprogToolConfigurationError

### Community 34 - "pymcuprog - Python MCU programmer"
Cohesion: 0.07
Nodes (27): Action: erase, Action: getsupplyvoltage, Action: getusbvoltage, Action: getvoltage, Action: makeuf2, Action: ping, Action: read, Action: reboot-debugger (+19 more)

### Community 35 - "Python Testing Patterns — Advanced Reference"
Cohesion: 0.05
Nodes (35): CI/CD Integration, Configuration Files, Pattern 10: Property-Based Testing, Pattern 6: Testing Async Code, Pattern 7: Monkeypatch for Testing, Pattern 8: Temporary Files and Directories, Pattern 9: Custom Fixtures and Conftest, Python Testing Patterns — Advanced Reference (+27 more)

### Community 38 - "sys"
Cohesion: 0.06
Nodes (12): main(), session(), Console, error(), main(), parse_arguments(), Terminal, Console (+4 more)

### Community 40 - "test_fresh.py"
Cohesion: 0.15
Nodes (30): adapters(), exchange(), fresh(), install_attempt(), discover(), execute(), mapping(), raw() (+22 more)

### Community 41 - "Design principles — what makes the output "professional""
Cohesion: 0.22
Nodes (9): Animation — only on actual data flow, Color discipline, Connections, Design principles — what makes the output "professional", Direction, Hierarchy & scope, Labels, Shape vocabulary — match the shape to the concept (+1 more)

### Community 42 - "Per-attempt evidence and timing"
Cohesion: 0.06
Nodes (31): Attempt 001, Attempt 002, Attempt 003, Attempt 004, Attempt 005, Attempt 006, Attempt 007, Attempt 008 (+23 more)

### Community 44 - "test_identity.py"
Cohesion: 0.30
Nodes (12): BoardIdentity, resolve_connection(), resolve_connections(), adapter(), board(), test_discovery_uses_sysfs_id_path_and_by_path_link(), test_duplicate_adapter_serials_keep_distinct_target_identities(), test_duplicate_id_path_is_rejected_as_ambiguous() (+4 more)

### Community 45 - "pathlib"
Cohesion: 0.11
Nodes (4): PtyTests, WindowsInputTests, observe(), scratch()

### Community 48 - "Design principles — what makes the output "professional""
Cohesion: 0.22
Nodes (9): Animation — only on actual data flow, Color discipline, Connections, Design principles — what makes the output "professional", Direction, Hierarchy & scope, Labels, Shape vocabulary — match the shape to the concept (+1 more)

### Community 49 - "AVR128DA28 UPDI root-cause report"
Cohesion: 0.10
Nodes (19): 10. Supported mechanism, 11. Fix, 12. File changes, 13. Verification numbers, 14. Risks, 15. Software limitations and physical discriminators, 16. Source table, 17. Reproduction commands (+11 more)

### Community 50 - "cp210x.c"
Cohesion: 0.11
Nodes (18): cp2102.pdf, error, url, cp210x.c, bytes, sha256, url, utc (+10 more)

### Community 51 - "samtarget.py"
Cohesion: 0.10
Nodes (3): PymcuprogTargetVoltageError, SamM4Target, SamTarget

### Community 52 - "time"
Cohesion: 0.28
Nodes (9): command(), main(), one_attempt(), record_raw(), sha(), source_hashes(), StopCampaign, utc_now() (+1 more)

### Community 54 - "os"
Cohesion: 0.25
Nodes (4): bootstrap(), create_temp_dir(), main(), capture()

### Community 56 - "Fresh UPDI RCA — RCA_FRESH_01"
Cohesion: 0.17
Nodes (12): Action, Decisions and stopping rules, Execution and batch results, Executive result, Fresh UPDI RCA — RCA_FRESH_01, Implementation and evidence controls, Result and causal level, Selected causal experiment: BREAK-triggered simultaneous electrical capture (+4 more)

### Community 57 - "UpdiApplication"
Cohesion: 0.04
Nodes (8): PymcuprogSerialUpdiError, PymcuprogSerialUpdiLockedError, decode_sib(), UpdiApplication, UpdiDatalink16bit, UpdiDatalink24bit, UpdiReadWrite, run()

### Community 58 - "test_classifier.py"
Cohesion: 0.13
Nodes (19): confidence_label(), _classify(), test_both_crossed_pairings_fail_without_claiming_both_targets_failed(), test_both_pass_after_reconnection_is_intervention_sensitive(), test_component_claim_needs_direct_measurement_or_remains_blocked(), test_contradicted_predictions_are_falsified_and_weak_fit_is_disfavored(), test_failure_following_adapter_classifies_adapter_path(), test_failure_following_target_classifies_target_local() (+11 more)

### Community 59 - "Optional arguments and switches"
Cohesion: 0.11
Nodes (17): Actions (commands), Administrative arguments, Examples, General arguments, Memory access actions, Memory access arguments, Memory types, Optional arguments and switches (+9 more)

### Community 60 - "Specialized diagram syntax (quick reference)"
Cohesion: 0.40
Nodes (5): Grid / matrix, Sequence diagram, Specialized diagram syntax (quick reference), SQL table (ERD), UML class

### Community 61 - ".claude/skills/d2/render.py"
Cohesion: 0.24
Nodes (4): build_d2_command(), main(), parse_d2_config(), render_one()

### Community 62 - "D2 — Modern Diagram Generation"
Cohesion: 0.09
Nodes (22): Common pitfalls (read these once), Core workflow, Custom palette via `theme-overrides`, D2 — Modern Diagram Generation, Diagram families → templates, Direct d2 CLI (when you need full control), Full palette catalog, Grid / matrix (+14 more)

### Community 63 - "classify_pairing_matrix"
Cohesion: 0.22
Nodes (7): test_07_interaction(), classify_pairing_matrix(), pairing_effects(), test_adapter_target_interaction_is_preserved(), test_partial_rate_difference_is_not_forced_into_binary_pass_fail(), test_two_factor_interaction_is_not_forced_to_single_cause(), test_partial_matrix_classifies_interaction()

### Community 64 - "pymcuprog/nvm.py"
Cohesion: 0.04
Nodes (10): get_nvm_access_provider(), NvmAccessProvider, NvmAccessProviderCmsisDapAvr, NvmAccessProviderCmsisDapTool, NvmAccessProviderCmsisDapAvr32, NvmAccessProviderCmsisDapMZeroPlus, NvmAccessProviderCmsisDapPic, NvmAccessProviderSerial (+2 more)

### Community 65 - "D2 — Modern Diagram Generation"
Cohesion: 0.11
Nodes (17): Common pitfalls (read these once), Core workflow, Custom palette via `theme-overrides`, D2 — Modern Diagram Generation, Diagram families → templates, Direct d2 CLI (when you need full control), Full palette catalog, Multi-board composition (when one board isn't enough) (+9 more)

### Community 66 - "How to run an RCA: the actual process"
Cohesion: 0.25
Nodes (8): How to run an RCA: the actual process, Step 1: Write a precise problem statement, Step 2: Collect evidence before forming a hypothesis, Step 3: Map contributing factors before narrowing to root cause, Step 4: Select your method and investigate, Step 5: Validate before you conclude, Step 6: Define corrective actions that address the cause, not the symptom, Step 7: Monitor whether the fix worked

### Community 71 - "PROMPT.md"
Cohesion: 0.08
Nodes (25): 0. Activate the investigation as an evidence-based Goal, 10. Failure-stage taxonomy, 12. Root-cause scoring rules, 13. Statistical test policy, 15. Python API expectations, 16. C target implementation expectations, 18. Tests that specifically attack methodology errors 161–168, 1. Required Superpowers workflow (+17 more)

### Community 73 - "Frequently asked questions"
Cohesion: 0.29
Nodes (7): Every team, every use case, the right momentum, Frequently asked questions, Q1. What are the 5 steps of root cause analysis?, Q2. What are the 5 core principles of RCA?, Q3. Is RCA part of Six Sigma?, Q4. What are the 7 steps of root cause analysis?, Q5. What are the 6 steps of RCA?

### Community 74 - "UPDI"
Cohesion: 0.12
Nodes (3): SerialPort, SerialUPDI, UPDI

### Community 75 - "Python Code Executor"
Cohesion: 0.08
Nodes (24): 3D Model Processing, 3D Processing, API Calls, App Details, Data Analysis with Visualization, Data Processing, Documentation, Documents & Graphics (+16 more)

### Community 77 - "Fundamental Patterns"
Cohesion: 0.09
Nodes (21): 1. Strict Mode, 2. Error Trapping and Cleanup, 3. Variable Safety, 4. Array Handling, 5. Conditional Safety, Advanced Defensive Techniques, bash-defensive-patterns — detailed patterns and worked examples, Core Defensive Principles (+13 more)

### Community 78 - "fresh.py"
Cohesion: 0.12
Nodes (24): Fresh RCA handoff — RCA_FRESH_01, verify(), sib_outcome(), control_allowed(), domain_scores(), failure_stage(), freeze_mapping(), initialize() (+16 more)

### Community 79 - "Common mistakes that make RCA useless"
Cohesion: 0.33
Nodes (6): 1\. Stopping at the first plausible answer, 2\. Treating "human error" as a root cause, 3\. Running the investigation with the people who built the thing, 4\. Writing corrective actions without assigning owners, 5\. Closing the report without scheduling a follow-up, Common mistakes that make RCA useless

### Community 80 - "The five RCA methods, explained with worked examples"
Cohesion: 0.33
Nodes (6): 1\. The 5 Whys, 2\. Fishbone diagram (Ishikawa diagram), 3\. Change analysis, 4\. Event analysis (timeline reconstruction), 5\. Pareto analysis, The five RCA methods, explained with worked examples

### Community 81 - "Usage"
Cohesion: 0.18
Nodes (10): CLI examples, CLI help, Debuggers / Tools, Devices, Library usage example, Notes for Linux® systems, pymcuprog - Python MCU programmer, Serial port UPDI (pyupdi) (+2 more)

### Community 82 - "snapshot_pairing"
Cohesion: 0.24
Nodes (10): ConnectionIdentity, PairingSnapshot, snapshot_pairing(), connection(), test_adapter_identity_follows_id_path_not_tty_number(), test_pairing_history_preserves_before_and_after_states(), test_target_label_survives_adapter_crossover(), test_tty_alias_never_defines_adapter_identity() (+2 more)

### Community 83 - "classify.py"
Cohesion: 0.14
Nodes (15): _bytes(), classify_event(), is_fresh_reset(), score_evidence(), _success_rate(), parse_upditerm_log(), events(), test_borf_alone_does_not_count_as_a_new_reset() (+7 more)

### Community 84 - "test_board_swap.py"
Cohesion: 0.28
Nodes (10): frame(), pairing(), swap(), test_break1_failure_and_break2_failure_are_distinct(), test_id_path_survives_tty_renumber(), test_local_echo_failure_does_not_become_acc_failure(), test_restore_phase_is_required_before_proven_status(), test_sib_outcome_keeps_command_echo_and_target_response_separate() (+2 more)

### Community 85 - "When RCA is worth running"
Cohesion: 0.40
Nodes (5): 1\. A production incident had customer impact, 2\. A release missed a hard commitment, 3\. A recurring process is consistently breaking, Something happened more than once, When RCA is worth running

### Community 86 - "RCA_POST_SWAP_01 — Lane P inventory"
Cohesion: 0.25
Nodes (7): Current P mapping, Evidence integrity, Ownership and host observations, POST-001 SIB-only result, Probe boundary, RCA_POST_SWAP_01 — Lane P inventory, Tool versions and source hashes

### Community 89 - "14. Phase-by-phase investigation"
Cohesion: 0.13
Nodes (15): 14. Phase-by-phase investigation, Mode HEARTBEAT, Mode SILENT, Optional LOAD phase, Phase 0 — Freeze and inventory, Phase 10 — Cross-over experiment if still ambiguous, Phase 1 — Baseline dual-board matrix at 38400, Phase 2 — Control vs data-space boundary (+7 more)

### Community 90 - "Official-source review: AVR128DA target and power path"
Cohesion: 0.22
Nodes (9): Device-specific electrical and layout guidance, Errata relevance and interpretation limit, Local board artifact audit, Official-source review: AVR128DA target and power path, Primary sources and revisions, Raw-source hashes, RESET and UPDI physical connection, Supply decoupling and placement (+1 more)

### Community 91 - "Investigation Handoff"
Cohesion: 0.33
Nodes (5): Current finding, Interpretation cautions, Investigation Handoff, Next discriminator, Safety/state

### Community 92 - "classify_crossover"
Cohesion: 0.10
Nodes (18): test_03_target_following(), test_04_path_following(), test_05_intervention_sensitive(), test_06_shared_failure_not_two_bad_boards(), test_10_restoration_and_three_cycles_required(), test_12_power_cycle_is_confound(), post_swap_assessment(), restoration_assessment() (+10 more)

### Community 93 - "Connect to a virtual UART on an AVR via UPDI"
Cohesion: 0.22
Nodes (8): Connect to a virtual UART on an AVR via UPDI, Demo program, License, Prerequisites, UPDI interface, Upditerm, Usage, Virtual UART

### Community 95 - "AVR128DA28 UPDI RCA — Continuation `RCA_CROSSOVER_01`"
Cohesion: 0.18
Nodes (10): Action, AVR128DA28 UPDI RCA — Continuation `RCA_CROSSOVER_01`, Continuation artifacts, Narrowest defensible conclusion, Required decision tree, Result, Situation, Smallest next action (+2 more)

### Community 96 - "test_continuation.py"
Cohesion: 0.31
Nodes (5): attempt_rows(), _echo_class(), rows(), test_acc_timeout_after_exact_echo_stays_later_than_local_echo(), test_run_event_rows_preserve_local_echo_failure_and_pairing_identity()

### Community 99 - "Accessibility (a11y)"
Cohesion: 0.17
Nodes (12): Accessibility (a11y), ARIA usage (4.1.2), Color contrast (1.4.3, 1.4.6), Conformance levels, Evidence-led audit workflow, Live regions (4.1.3), Media alternatives (1.2), Perceivable (+4 more)

### Community 100 - "Syntax cheat-sheet (most-used)"
Cohesion: 0.25
Nodes (8): Connections, Containers, Icons, Local icon library — check first, Markdown labels (C4-style hierarchy), Style (use sparingly — prefer classes), Syntax cheat-sheet (most-used), Title and legend

### Community 101 - "Lane A"
Cohesion: 0.11
Nodes (18): Adapter mapping (read-only; target port not opened), Authorized identity-only probes, Authorized identity probe attempt, Control-space condition, Control-space snapshot — pass, Coordinator's one-shot OCD message snapshot, Evidence and hashes, Final A in non-destructive SIB A/B/A discriminator (+10 more)

### Community 103 - "WCAG 2.2 Quick Reference"
Cohesion: 0.18
Nodes (8): Level A (minimum), Level AA (standard), Level AAA (enhanced), Sources, Success criteria by level, Testing tools, WCAG 2.2 Quick Reference, What changed from 2.1 to 2.2

### Community 104 - "Target Electrical Investigator — RCA_PHY_01"
Cohesion: 0.29
Nodes (6): Board artifact audit, Finding, Hypothesis-specific falsifiers and least-cost discriminators, Smallest next physical discriminator, Source evidence files, Target Electrical Investigator — RCA_PHY_01

### Community 105 - "Focused physical-layer RCA plan"
Cohesion: 0.33
Nodes (5): Authorized experiment design (pending safe physical access), Execution, Focused physical-layer RCA plan, Inherited boundary and physical gate, Safety and deliverables

### Community 106 - "17. Hypothesis inventory and evidence model"
Cohesion: 0.18
Nodes (11): 17. Hypothesis inventory and evidence model, A. Power / GND ฝั่ง board, B. UPDI path บน board, C. Reset / Watchdog / Reset cause, D. ตัว AVR chip, E. Fuse / Config ที่อาจต่างกัน, F. Firmware / Runtime behavior, G. Adapter / Host / Software (+3 more)

### Community 108 - "AVR128DA28 board-swap RCA — PRE NO-GO checkpoint"
Cohesion: 0.29
Nodes (7): Action, AVR128DA28 board-swap RCA — PRE NO-GO checkpoint, Identity and physical freeze, PRE experiment and decision, Situation, Software gate and workers, Task

### Community 109 - "Tasks"
Cohesion: 0.20
Nodes (9): 1. Freeze, inspect, and plan, 2. Observe both lanes, 3. TDD host tooling, 4. Select discriminating experiments, 5. Evidence, reports, diagram, verification, AVR128DA28 Dual-Board UPDI Root-Cause Investigation Plan, Global constraints, Review focus (+1 more)

### Community 110 - "Accessibility Code Patterns"
Cohesion: 0.22
Nodes (9): Accessibility Code Patterns, ARIA tabs, Dragging movements, Error handling, Form labels, Live regions and notifications, Modal focus trap, Screen reader commands (+1 more)

### Community 111 - "Operable"
Cohesion: 0.22
Nodes (9): Dragging movements (2.5.7) — new in 2.2, Focus not obscured (2.4.11) — new in 2.2, Focus visible (2.4.7), Keyboard accessible (2.1), Motion (2.3), Operable, Skip links (2.4.1), Target size (2.5.8) — new in 2.2 (+1 more)

### Community 112 - "Common ARIA patterns"
Cohesion: 0.25
Nodes (8): Buttons, Common ARIA patterns, Error states, Form fields, Links, Live regions, Modals, Navigation

### Community 113 - "Understandable"
Cohesion: 0.25
Nodes (8): Accessible authentication (3.3.8) — new in 2.2, Consistent help (3.2.6) — new in 2.2, Consistent navigation (3.2.3), Error handling (3.3.1, 3.3.3), Form labels (3.3.2), Page language (3.1.1), Redundant entry (3.3.7) — new in 2.2, Understandable

### Community 114 - "D2-Diagram-Skill"
Cohesion: 0.25
Nodes (7): D2-Diagram-Skill, Installation, License, Requirements, Usage, What it does, What you get

### Community 115 - "Syntax cheat-sheet (most-used)"
Cohesion: 0.17
Nodes (10): Connections, Containers, Icons, Local icon library — check first, Markdown labels (C4-style hierarchy), Shapes, Style (use sparingly — prefer classes), Syntax cheat-sheet (most-used) (+2 more)

### Community 117 - "D2-Diagram-Skill"
Cohesion: 0.25
Nodes (7): D2-Diagram-Skill, Installation, License, Requirements, Usage, What it does, What you get

### Community 118 - "STAR"
Cohesion: 0.25
Nodes (8): Action, Decision logic, Execution, Result, Situation, STAR, Task, Trade-offs

### Community 119 - "Frontend Design"
Cohesion: 0.29
Nodes (6): Design principles, Frontend Design, Ground your designs in the subject matter, More on writing in design, Process: plan, review against the brief, build, critique, Restraint and self-critique

### Community 120 - "19. Evidence standards for root-cause claims"
Cohesion: 0.29
Nodes (7): 19. Evidence standards for root-cause claims, BLOCKED, DISFAVORED, FALSIFIED, PROVEN, STRONGLY_SUPPORTED, SUPPORTED

### Community 121 - "Lane B"
Cohesion: 0.25
Nodes (7): Adapter observation, Fresh independent SIB sample, Lane B, Phase 1 baseline disposition, RCA_CROSSOVER_01 pre-crossover confirmation, Strict read-only Phase 1 baseline, Target and probe state

### Community 122 - "11. TDD requirements for host automation"
Cohesion: 0.33
Nodes (6): 11. TDD requirements for host automation, Classifier tests, Identity tests, Integration tests without hardware, Metrics tests, Parser/event tests

### Community 123 - "Bash Defensive Patterns"
Cohesion: 0.40
Nodes (4): Bash Defensive Patterns, Best Practices Summary, Detailed patterns and worked examples, When to Use This Skill

### Community 124 - "AVR128DA28 Dual-Board UPDI Root-Cause Analysis"
Cohesion: 0.20
Nodes (10): Action, AVR128DA28 Dual-Board UPDI Root-Cause Analysis, Evidence files, Fresh read-only baseline (100 attempts per lane and condition), Narrowest defensible conclusion, OCD text and reset interpretation, Result, Situation (+2 more)

### Community 125 - "5. Two-subagent architecture: exactly two workers"
Cohesion: 0.40
Nodes (5): 5. Two-subagent architecture: exactly two workers, Coordinator, Lane Worker A, Lane Worker B, Port contention rule

### Community 126 - "Common issues by impact"
Cohesion: 0.50
Nodes (4): Common issues by impact, Critical (fix immediately), Moderate (fix soon), Serious (fix before launch)

### Community 127 - "Continuation State"
Cohesion: 0.25
Nodes (7): Continuation State, Current causal boundary, Current physical labels (pending confirmation), New evidence in this epoch, Next smallest discriminator, Safety, Verified inherited evidence

### Community 128 - "4. Hard safety and scope constraints"
Cohesion: 0.50
Nodes (4): 4.1 Repository scope, 4.2 Flash/fuse safety, 4.3 Physical-action policy, 4. Hard safety and scope constraints

### Community 129 - "8. Persistent memory policy"
Cohesion: 0.50
Nodes (4): 8. Persistent memory policy, `memory/CURRENT_STATE.md`, `memory/DECISIONS.md`, `memory/EVIDENCE_LOG.md`

### Community 130 - "Testing checklist"
Cohesion: 0.67
Nodes (3): Automated testing, Manual testing, Testing checklist

### Community 131 - "demo.c"
Cohesion: 0.23
Nodes (7): dump(), main(), pwm_init(), pwm_set(), updi_getchar(), updi_putchar(), updi_stdio_init()

### Community 132 - "Evidence log"
Cohesion: 0.29
Nodes (6): Bounded OCD message snapshot, Evidence log, Final structured outputs, Historical input (not fresh lane-linked evidence), Scope correction for legacy probe records, Strict no-register-write 38400 baseline

### Community 134 - "AVR128DA28 UPDI root-cause investigation"
Cohesion: 0.33
Nodes (4): AVR128DA28 UPDI root-cause investigation, Current result, Evidence map, Host tooling

### Community 137 - "updi_uart_rx"
Cohesion: 0.29
Nodes (6): FLAG_RX follow-up decision, Investigation decisions, Read-only GPR2 / FLAG_RX follow-up, Follow-up GPR2 / FLAG_RX reads, FLAG_RX read-only follow-up, updi_uart_rx()

### Community 139 - "Post-swap physical freeze"
Cohesion: 0.33
Nodes (5): Confounds, Evidence boundary, Mapping provenance, Post-swap physical freeze, Software gate and safety

### Community 141 - "Result"
Cohesion: 0.40
Nodes (5): Artifacts and safety, Checkpoint verification, Current matrix, Required answers, Result

### Community 142 - "identity.py"
Cohesion: 0.15
Nodes (11): adapter_from_properties(), AdapterIdentity, discover_serial_ports(), _links_for(), parse_udev_properties(), _usb_numbers(), test_baseline_cli_runs_sib_and_control_on_selected_id_path(), test_inventory_cli_reports_stable_identity_and_marks_target_unknown() (+3 more)

### Community 145 - "Board Swap RCA State"
Cohesion: 0.22
Nodes (9): Board Swap RCA State, Causal classification, Current phase, Current result, Hard metrics, Last experiment, Next smallest discriminator, Physical mapping (+1 more)

### Community 147 - "Handoff — `RCA_CROSSOVER_01`"
Cohesion: 0.29
Nodes (6): Current finding, Handoff — `RCA_CROSSOVER_01`, Inherited state and safety, Next step, Physical boundary, Work completed

### Community 148 - "hashlib"
Cohesion: 0.16
Nodes (3): run(), utc_now(), main()

### Community 149 - "Untouched crossed-state implementation plan"
Cohesion: 0.50
Nodes (3): Experiment POST-001, Implementation and verification, Untouched crossed-state implementation plan

### Community 151 - "test_probes.py"
Cohesion: 0.31
Nodes (9): connection(), FakeSerial, install_serial(), test_control_probe_uses_only_ldcs_reads(), test_data_probe_uses_stable_by_path_and_keeps_target_failure_stage(), test_echo_failure_and_missing_target_response_are_separate(), test_probe_raw_evidence_survives_missing_response(), test_probe_refuses_to_open_when_stable_by_path_is_missing() (+1 more)

### Community 152 - "test_physical.py"
Cohesion: 0.30
Nodes (11): exchange(), physical(), test_echo_byte_forensics_preserves_missing_bytes(), test_exact_sync_and_response_require_both_breaks_and_command_echo(), test_first_break_failure_differs_from_second_break_failure(), test_interaction_effects_use_all_four_cells_without_forcing_locality(), test_local_echo_failure_stops_higher_layer_classification(), test_no_capture_is_not_fabricated_as_empty_echo() (+3 more)

### Community 153 - "FOCUSED_STAR_RCA.md"
Cohesion: 0.25
Nodes (3): Focused Current State, Focused Decisions, RCA_PHY_01

### Community 155 - "RCA_PHY_01 — External Path Investigator"
Cohesion: 0.25
Nodes (8): Candidate checks and falsifiers, Classic CP2102/9 limits and identity uncertainty, Evidence/source hashes, Finding, Host and Linux evidence boundaries, Local implementation and wiring limits, Physical gate and exact next action, RCA_PHY_01 — External Path Investigator

### Community 159 - "STAR_BOARD_SWAP_RCA.md"
Cohesion: 0.33
Nodes (3): Evidence integrity, Mapping and inventory, RCA_BOARD_SWAP_01 — Lane P state

### Community 160 - "AVR128DA28 BREAK / LOCAL_ECHO focused RCA"
Cohesion: 0.29
Nodes (7): Action, AVR128DA28 BREAK / LOCAL_ECHO focused RCA, Controls and source review, Physical gate and experiment decision, Situation, Task, Test-first host tooling and replay

### Community 161 - "RCA_BOARD_SWAP_01 execution plan"
Cohesion: 0.33
Nodes (5): Contract and physical gate, Hypothesis and experiment, RCA_BOARD_SWAP_01 execution plan, Safety and stop boundary, Software and ownership

### Community 162 - "argparse"
Cohesion: 0.21
Nodes (5): build_d2_command(), main(), parse_d2_config(), render_one(), parse_arguments()

### Community 164 - "Path Q lane — RCA_BOARD_SWAP_01"
Cohesion: 0.40
Nodes (4): Inventory, Ownership and host USB observations, Path Q lane — RCA_BOARD_SWAP_01, PRE batch status

### Community 165 - "Board Swap Evidence Log"
Cohesion: 0.40
Nodes (4): Board Swap Evidence Log, Current epoch, Inherited checkpoint, PRE NO-GO checkpoint

### Community 166 - "Board-swap physical freeze"
Cohesion: 0.40
Nodes (5): Board-swap physical freeze, External Path P, External Path Q, Frozen ledger boundary, Targets and shared controls

### Community 167 - "Result"
Cohesion: 0.40
Nodes (5): Artifacts and verification, Causal decision record, Narrowest defensible conclusion, Observed stage and byte distribution, Result

### Community 168 - "Fresh Q ownership check — read only"
Cohesion: 0.50
Nodes (3): Fresh Q ownership check — read only, Owner queries on the stable link, Resolver

### Community 169 - "Q PRE host-tool failures"
Cohesion: 0.50
Nodes (3): Attempt 1 — parse-time error, Attempt 2 — host runtime error, Q PRE host-tool failures

### Community 189 - "Q crossed-untouched SIB-only batch — POST-00130"
Cohesion: 0.18
Nodes (9): Batch result, Host identity and preflight, Post-batch path and ownership, Q crossed-untouched SIB-only batch — POST-00130, Software source identity, Stop state, Batch result, Evidence (+1 more)

### Community 193 - "AVR128DA28 untouched crossed-state RCA"
Cohesion: 0.29
Nodes (6): Action, AVR128DA28 untouched crossed-state RCA, Required answers, Result, Situation, Task

### Community 194 - "Post-swap handoff"
Cohesion: 0.40
Nodes (4): Measured B state, Pending human action, Post-swap handoff, Verification and artifacts

### Community 195 - "Stable identity and path"
Cohesion: 0.67
Nodes (3): Current by-path links, Resolve Q by stable path, Stable identity and path

### Community 197 - "fresh/STAR_RCA.md"
Cohesion: 0.24
Nodes (4): RCA_FRESH_01 execution ledger, Fresh AVR128DA28 UPDI RCA — RCA_FRESH_01, RCA_FRESH_01, Frozen current topology — RCA_FRESH_01

## Knowledge Gaps
- **2 isolated node(s):** `updi-rca`, `lora`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1441 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **52 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AvrDebugger` connect `AvrDebugger` to `PymcuprogError`, `backend.py`, `Syntax cheat-sheet (most-used)`, `._wait_for_break`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `Backend` (e.g. with `Programmer` and `PymcuprogEraseError`) actually correct?**
  _`Backend` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `updi-rca`, `lora` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `UPDI` be split into smaller, more focused modules?**
  _Cohesion score 0.10695187165775401 - nodes in this community are weakly interconnected._
- **Why does `PymcuprogError` connect `PymcuprogError` to `pymcuprog/nvm.py`, `NvmAccessProviderCmsisDapMegaAvrJtag`, `Backend`, `backend.py`, `NvmAccessProviderCmsisDapDebugwire`, `TinyXAvrTarget`, `samtarget.py`, `Programmer`, `._wait_for_break`, `SamD2xTarget`, `AvrDebugger`, `pymcuprog_main.py`, `UpdiApplication`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `PymcuprogError` (e.g. with `AvrDebugger` and `NvmAccessProviderCmsisDapAvr32`) actually correct?**
  _`PymcuprogError` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `UPDI` be split into smaller, more focused modules?**
  _Cohesion score 0.07171717171717172 - nodes in this community are weakly interconnected._