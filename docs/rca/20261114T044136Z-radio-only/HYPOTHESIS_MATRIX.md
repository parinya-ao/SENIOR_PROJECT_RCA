# Hypothesis Matrix

Statuses describe evidence from this investigation only. `CONFIRMED` is reserved for a demonstrated cause; source mismatch alone does not prove a physical RF cause.

| ID | Hypothesis | Evidence / contradiction | Status | Decisive next test |
|---|---|---|---|---|
| H01 | HF register-bank selection is wrong in preserved firmware | Preserved 915 MHz RX observation `0x8D`; source now clears bit 3 for 923 MHz | **Source configuration defect confirmed; H01 causal role unknown** | Flash candidate after preflight; compare runtime registers and DATA/ACK under one controlled profile |
| H02 | Gateway runtime PHY differs from Tracker | Shared ARQ candidate is generated from one profile; no candidate hardware readback | **UNKNOWN** | Read both devices' radio configuration after safe flash |
| H03 | Tracker runtime PHY differs from Gateway | Same as H02 | **UNKNOWN** | Read both devices' radio configuration after safe flash |
| H04 | DIO/IRQ pin map is swapped | Static source matches board-specific schematics; physical traces/IRQ not captured | **Not supported by source; hardware UNKNOWN** | Observe radio IRQ and MCU event on actual board |
| H05 | RadioLib 7.1.2 mode transition causes failure | 923 MHz installed-driver HAL model passed 12 TX/RX cycles; model is not silicon/RF | **Not reproduced in model; hardware UNKNOWN** | Capture actual mode/IRQ transitions on both boards |
| H06 | Gateway does not enter TX | Historical 10 local `TX_DONE` events | **TX_DONE observed; independent RF emission UNKNOWN** | Independent receiver or suitable RF instrument plus runtime registers |
| H07 | Tracker does not receive DATA | Tracker was RX Continuous before H01; no surviving RX_DONE evidence | **UNKNOWN** | Capture Tracker IRQ/RX_DONE and raw FIFO for one packet |
| H08 | Tracker rejects DATA in application | No accepted-data event survived; host protocol tests pass | **UNKNOWN physically** | Capture raw packet, CRC, parser result and session/sequence |
| H09 | Tracker fails to construct ACK | No ACK-prepared event survived | **UNKNOWN** | Instrument ACK preparation after accepted DATA |
| H10 | Tracker fails to transmit ACK | No ACK TX_START/TX_DONE evidence survived | **UNKNOWN** | Capture Tracker mode/IRQ and ACK bytes |
| H11 | Gateway ACK window/timing is wrong | Historical 10 ACK-window timeouts; no timestamped Tracker path | **Possible, unisolated** | One exchange with synchronized RX-ready/TX/ACK events |
| H12 | Gateway receives but rejects ACK | No ACK_RX_DONE or parser event; accepted count 0 | **UNKNOWN** | Preserve raw received ACK and parser decision |
| H13 | CP2102 power capacity causes POR | CP2102 USB descriptors show bus-powered, MaxPower 100mA; target output/current unmeasured | **UNKNOWN** | Inspect adapter topology and measure rails/current during bounded TX |
| H14 | Connector, ground, or cable resistance causes POR | No physical wiring inspection or voltage measurement | **UNKNOWN** | Inspect and measure at MCU/radio supply points |
| H15 | Q1/PA7 LoRa switching causes POR | Source implements active-low control; no rail waveform or time-localized reset | **UNKNOWN** | Measure EN-LORA, MCU VDD, 3V3-LORA and reset marker |
| H16 | GPS load/UART back-power contributes | Diagnostic source isolates UART and commands GPS main rail off; no rail/I/O measurement | **Code policy present; electrical effect UNKNOWN** | Verify off-rail I/O/3V3-GPS and compare one controlled candidate |
| H17 | SD/shared SPI/back-power contributes | Fail-closed card-detect guard exists; socket state not observed | **UNKNOWN** | Inspect socket/card detect and test guard before radio startup |
| H18 | UPDI monitor caused the RF symptom | H01 included reader-free trials; no candidate RF test attached/detached | **Not established as necessary; observer effect UNKNOWN** | Paired no-monitor/idle/active STATUS RF trials after gates |
| H19 | PORF is stale or misinterpreted | Session 9 saved `GPIOR0 0x20→0x01`, `RSTFR 0`; exact time/trigger unknown; fresh read-only values later unchanged | **Recorded PORF transition; provenance/timing incomplete** | Capture early-boot reset cause with a synchronized hardware marker |
| H20 | Multiple independent defects exist | HF mismatch and tooling defects are distinct; no physical counterfactual | **POSSIBLE** | Complete one-packet DATA/ACK and separate supply A/B/A tests |

The programmer role-map bug and host-test-stage source/flag bugs are confirmed tooling defects and fixed. Neither is evidence of an RF or POR cause.
