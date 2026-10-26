# Graph Report - lora  (2026-10-26)

## Corpus Check
- 1794 files · ~1,423,708 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 284 file(s) not represented in the graph (top: .stderr 130, .stdout 130, (none) 11)

## Summary
- 1414 nodes · 2521 edges · 96 communities (20 shown, 76 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 211 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- PymcuprogSessionConfigError
- demo.c
- upditerm.py
- pymcuprog_errors.py
- updi-session.py
- TransportTests
- application.py
- Connect to a virtual UART on an AVR via UPDI
- AVR128DA28 UPDI console engineering report
- PymcuprogError
- PtyTests
- updi-progress.md
- updi-sib.sh
- lora
- UpdiApplication
- hexfileutils.py
- cp210x.c
- Programmer
- MegaAvrJtagTarget
- UpdiDatalink
- pymcuprog_main.py
- Avr32Device
- Changelog
- NvmAccessProviderCmsisDapUpdi
- PymcuprogNotSupportedError
- NvmUpdiP3
- Optional arguments and switches
- NvmAccessProviderCmsisDapPic
- NvmAccessProviderCmsisDapXmega
- pymcuprog - Python MCU programmer
- pymcuprog/nvm.py
- PymcuprogSerialUpdiNvmTimeout
- get-platformio.py
- NvmUpdiP2
- NvmUpdiP5
- Backend
- NvmAccessProviderCmsisDapMegaAvrJtag
- NvmAccessProviderSerial
- ToolSerialConnection
- NvmAccessProviderCmsisDapSpi
- updi-diagnose.py
- AvrDevice
- TinyXAvrTarget
- XmegaAvrTarget
- AVR128DA28 UPDI root-cause report
- cp210x.c
- SamTarget
- AvrDebugger
- NvmAccessProviderCmsisDapDebugwire
- observe
- backend.py
- pymcuprog.py
- ToolUsbHidConnection
- SamD2xTarget
- WindowsInputTests
- NvmAccessProvider
- NvmAccessProviderCmsisDapTpi
- ScratchTests

## God Nodes (most connected - your core abstractions)
1. `Backend` - 48 edges
2. `PymcuprogError` - 46 edges
3. `AvrDebugger` - 38 edges
4. `PymcuprogSerialUpdiNvmTimeout` - 38 edges
5. `UpdiApplication` - 33 edges
6. `PymcuprogNotSupportedError` - 31 edges
7. `SamD2xTarget` - 26 edges
8. `NvmUpdi` - 24 edges
9. `Programmer` - 23 edges
10. `UpdiDatalink` - 23 edges

## Surprising Connections (you probably didn't know these)
- `run()` --uses--> `UpdiPhysical`  [INFERRED]
  tools/updi-diagnose.py → .automation/research/pymcuprog/pymcuprog/serialupdi/physical.py
- `run()` --uses--> `UpdiApplication`  [INFERRED]
  tools/updi-diagnose.py → .automation/research/pymcuprog/pymcuprog/serialupdi/application.py
- `run()` --uses--> `UpdiDatalink16bit`  [INFERRED]
  tools/updi-diagnose.py → .automation/research/pymcuprog/pymcuprog/serialupdi/link.py
- `run()` --uses--> `UpdiDatalink24bit`  [INFERRED]
  tools/updi-diagnose.py → .automation/research/pymcuprog/pymcuprog/serialupdi/link.py
- `run()` --uses--> `UpdiReadWrite`  [INFERRED]
  tools/updi-diagnose.py → .automation/research/pymcuprog/pymcuprog/serialupdi/readwrite.py

## Import Cycles
- 1-file cycle: `.automation/research/pymcuprog/pymcuprog/pymcuprog.py -> .automation/research/pymcuprog/pymcuprog/pymcuprog.py`

## Communities (96 total, 76 thin omitted)

### Community 0 - "PymcuprogSessionConfigError"
Cohesion: 0.10
Nodes (5): PymcuprogEraseError, PymcuprogSessionConfigError, PymcuprogTargetVoltageError, PymcuprogToolConfigurationError, PymcuprogToolConnectionError

### Community 1 - "demo.c"
Cohesion: 0.07
Nodes (16): updi_uart_enabled(), updi_uart_rx_poll(), updi_uart_tx(), loop(), UpdiWrite(), dump(), main(), pwm_init() (+8 more)

### Community 2 - "upditerm.py"
Cohesion: 0.06
Nodes (12): Console, cleanup(), error(), main(), parse_arguments(), SerialPort, SerialUPDI, session() (+4 more)

### Community 6 - "application.py"
Cohesion: 0.05
Nodes (4): PymcuprogSerialUpdiNvmError, NvmUpdi, NvmUpdiP4, Timeout

### Community 7 - "Connect to a virtual UART on an AVR via UPDI"
Cohesion: 0.22
Nodes (8): Connect to a virtual UART on an AVR via UPDI, Demo program, License, Prerequisites, UPDI interface, Upditerm, Usage, Virtual UART

### Community 8 - "AVR128DA28 UPDI console engineering report"
Cohesion: 0.18
Nodes (9): 1. Outcome, 2. Proven findings and remaining cause, 3. Hardware and baud, 4. Implementation and compatibility, 5. Verification and acceptance, 6. Commands and reproducible diffs, 7. Delivery limits and next required evidence, AVR128DA28 UPDI console engineering report (+1 more)

### Community 16 - "UpdiApplication"
Cohesion: 0.05
Nodes (8): PymcuprogSerialUpdiError, PymcuprogSerialUpdiLockedError, decode_sib(), UpdiApplication, UpdiDatalink16bit, UpdiDatalink24bit, UpdiReadWrite, run()

### Community 17 - "hexfileutils.py"
Cohesion: 0.17
Nodes (6): _add_data_to_hex(), read_memories_from_hex(), remove_phantom_bytes(), _write_hex_to_file(), write_memories_to_hex(), write_memory_to_hex()

### Community 18 - "cp210x.c"
Cohesion: 0.06
Nodes (46): cp2102_determine_quirks(), cp2102n_gpioconf_init(), cp2104_gpioconf_init(), cp2105_gpioconf_init(), cp2108_gpio_init(), cp210x_attach(), cp210x_break_ctl(), cp210x_change_speed() (+38 more)

### Community 24 - "pymcuprog_main.py"
Cohesion: 0.09
Nodes (26): _action_erase(), _action_getsupplyvoltage(), _action_getusbvoltage(), _action_getvoltage(), _action_makeuf2(), _action_ping(), _action_read(), _action_reboot_debugger() (+18 more)

### Community 27 - "Changelog"
Cohesion: 0.06
Nodes (33): [], [3.10] - October 2021, [3.13] - May 2022, [3.14] - October 2022, [3.16] - November 2023, [3.17] - March 2024, [3.19] - June 2025, [3.1.3] - June 2020 (+25 more)

### Community 29 - "PymcuprogNotSupportedError"
Cohesion: 0.09
Nodes (5): PymcuprogNotSupportedError, enum(), pad_to_size(), pagealign(), set_supply_voltage_setpoint()

### Community 31 - "Optional arguments and switches"
Cohesion: 0.07
Nodes (27): Actions (commands), Administrative arguments, Examples, General arguments, Memory access actions, Memory access arguments, Memory types, Optional arguments and switches (+19 more)

### Community 34 - "pymcuprog - Python MCU programmer"
Cohesion: 0.07
Nodes (27): Action: erase, Action: getsupplyvoltage, Action: getusbvoltage, Action: getvoltage, Action: makeuf2, Action: ping, Action: read, Action: reboot-debugger (+19 more)

### Community 35 - "pymcuprog/nvm.py"
Cohesion: 0.29
Nodes (3): NvmAccessProviderCmsisDapAvr, NvmAccessProviderCmsisDapTool, NvmAccessProviderCmsisDapMZeroPlus

### Community 37 - "get-platformio.py"
Cohesion: 0.52
Nodes (3): bootstrap(), create_temp_dir(), main()

### Community 49 - "AVR128DA28 UPDI root-cause report"
Cohesion: 0.07
Nodes (20): UpdiPhysical, 10. Supported mechanism, 11. Fix, 12. File changes, 13. Verification numbers, 14. Risks, 15. Software limitations and physical discriminators, 16. Source table (+12 more)

### Community 50 - "cp210x.c"
Cohesion: 0.11
Nodes (18): cp2102.pdf, error, url, cp210x.c, bytes, sha256, url, utc (+10 more)

### Community 57 - "backend.py"
Cohesion: 0.09
Nodes (6): SessionConfig, read_supply_voltage_setpoint(), read_target_voltage(), read_tool_info(), read_usb_voltage(), read_voltage_parameter()

### Community 58 - "pymcuprog.py"
Cohesion: 0.19
Nodes (3): _parse_literal(), main(), setup_logging()

## Knowledge Gaps
- **1 isolated node(s):** `lora`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 674 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **76 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PymcuprogError` connect `PymcuprogError` to `PymcuprogSessionConfigError`, `pymcuprog_errors.py`, `pymcuprog/nvm.py`, `.chip_erase_dsu`, `NvmAccessProviderCmsisDapMegaAvrJtag`, `TinyXAvrTarget`, `UpdiApplication`, `.read_flash`, `Programmer`, `SamD2xTarget`, `AvrDebugger`, `NvmAccessProviderCmsisDapDebugwire`, `pymcuprog_main.py`, `Avr32Device`, `._wait_for_break`, `NvmAccessProviderCmsisDapUpdi`, `PymcuprogNotSupportedError`, `backend.py`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `Backend` (e.g. with `Programmer` and `PymcuprogEraseError`) actually correct?**
  _`Backend` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `lora` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `PymcuprogSessionConfigError` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._
- **Why does `Backend` connect `Backend` to `PymcuprogSessionConfigError`, `pymcuprog_errors.py`, `.read_device_id`, `ToolSerialConnection`, `._is_tool_not_connected_raise`, `Programmer`, `._is_hid_tool_not_connected_raise`, `._is_session_not_active_raise`, `.hold_in_reset`, `pymcuprog_main.py`, `backend.py`, `.end_session`, `ToolUsbHidConnection`, `PymcuprogNotSupportedError`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `PymcuprogError` (e.g. with `AvrDebugger` and `NvmAccessProviderCmsisDapAvr32`) actually correct?**
  _`PymcuprogError` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `demo.c` be split into smaller, more focused modules?**
  _Cohesion score 0.06866002214839424 - nodes in this community are weakly interconnected._