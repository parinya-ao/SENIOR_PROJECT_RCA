# Target Electrical Investigator — RCA_PHY_01

Updated 2026-10-27. Scope: H017, H018, H035, H036–H053 and physical-layer methodology. No hardware was accessed, no serial port was opened, and no shared source/report/CSV was changed.

## Finding

The inherited failure is confined to the first observed transaction boundary for the failing Q+Y pairing: the 38400-baud baseline passed 0/100 SIB and 0/100 control attempts; all 200 failures were classified at LOCAL_ECHO before a SIB/LDCS target request or response. Wilson 95% success interval is 0–3.70% per 100-attempt condition. The separate pre-crossover confirmation was Q+Y 0/10 in each condition (Wilson 95% 0–27.75%); successful P+X was 10/10 in each (72.25–100%). The inherited 38400 P+X baseline passed 100/100 in each condition (96.30–100%).

The historical unheld LDS result, 19 missing ACC responses in 60 attempts after an exact echo, is a later and distinct failure class. It must not be merged with Q+Y’s TX/local-echo failures. Neither result identifies a component: P/Q remain adapter USB paths, X/Y remain provisional target labels, both targets are UNKNOWN_TARGET, and no adapter/target crossover was measured (N=0). These observations do not prove a target fault or board-local fault.

No physical waveform, VDD, ground-offset, RESET, continuity, component-population, or target-end UPDI measurement exists in this epoch (N=0). The current physical measurement request remains blocked by reported lack of instruments and unsafe crossover. Evidence scores and BLOCKED statuses remain those in the shared seed/status ledger; no hypothesis status or score was changed here.

## Board artifact audit

I ran a scoped Graphify query for the AVR128DA28 schematic, BOM, UPDI net, regulator, RESET connector and decoupling; it surfaced RCA plans, reports and software, but no board design. CodeGraph exploration for those hardware artifacts likewise surfaced software sources only. A scoped repository inventory for schematic, PCB, netlist and BOM formats found no local board schematic, BOM, layout or netlist. The only local electronics references found were Microchip AVR DA datasheet/errata PDFs and generated RCA reports.

Accordingly, the physical package, supply source/value, ground return, header pinout, harness mapping, UPDI series element, pull-up/down, ESD part, attached loads, decoupler part/value/location, net routing, and board assembly state are UNKNOWN / UNVERIFIED. The Microchip recommended circuits are reference circuits; they do not prove the candidate board follows them.

## Hypothesis-specific falsifiers and least-cost discriminators

All falsifiers below require an electrically qualified bench with the actual circuit topology identified. A single clean snapshot only weakens an intermittent hypothesis; component-level falsification needs repeated measurements under the triggering condition. No proposed physical action was performed.

| ID | Candidate | Falsifier or strong disconfirmation | Cheapest discriminating evidence |
|---|---|---|---|
| H017 | High contact resistance in VDD/GND jumper wires | Across repeated failing attach/RUN events, voltage drop from supply endpoints to MCU VDD/GND remains stable and within measurement uncertainty while the failure reproduces. | Simultaneous differential capture across supply-to-MCU VDD and source-ground-to-MCU-local-GND during BREAK and RUN; if current is known safely, measure each jumper drop under that load. |
| H018 | Poor ground connection between adapter and board | Adapter ground and MCU-local ground show no transient offset during repeated failures, with enough resolution to exclude a shift relevant to UPDI levels. | Differential capture of adapter GND versus MCU local GND aligned to adapter TX, both BREAKs, and RUN. |
| H035 | Adapter/board voltage mismatch (3.3 V versus 5 V) | Actual adapter TX, target-side UPDI, target VDD and local ground remain within target operating/stress limits through repeat failures; a VDD label alone is insufficient. | Simultaneous capture of adapter TX and both UPDI nodes relative to MCU local GND plus MCU VDD. Datasheet Rev E does not give a separate guaranteed UPDI VIH/VIL value. |
| H036 | Cold or cracked header-pin solder joint | Repeated capture shows no discontinuity or waveform change across the verified header-to-board path while the failure reproduces. | Inspect the identified joint and compare adapter-side/target-side UPDI under the failing BREAK sequence; intermittent mechanical fault needs repeated observations. |
| H037 | Header pin fails to contact jumper | Verified contact resistance and the same waveform on each side of the actual contact remain stable during failures. | Non-powered contact inspection/continuity after a qualified operator verifies isolation and connector orientation; do not move the present wiring. |
| H038 | Loose jumper contact changes after reconnection | A controlled, safe reconnection series fails to move either symptom or waveform and shows stable continuity; not testable in the present unsafe state. | Only after qualified safe isolation, a documented A/B/A reconnection sequence with one connection changed at a time. |
| H039 | Broken or hairline-cracked UPDI trace | Verified continuity and identical target-side/source-side waveform through repeated failures disfavor an open trace; a static pass alone cannot exclude a crack that opens under stress. | Compare both sides of the verified trace/series path while the exact BREAK failure occurs; unpowered continuity inspection can complement it. |
| H040 | Cold solder joint on AVR UPDI pad | Repeated target-pin waveform remains identical to the upstream node with no contact intermittency; this weakens but does not prove away a latent pad joint. | Magnified inspection plus waveform at the verified MCU pin and upstream node; topology and safe probe access must be established first. |
| H041 | UPDI pad bridged to adjacent pin | A verified, unpowered net inspection finds no unintended conductive bridge and the adjacent signal is not coupled during the failing sequence. | Inspect the identified package/pad under magnification and perform safe unpowered isolation/continuity checks. |
| H042 | UPDI trace shorted to another trace | Verified net inspection and unpowered resistance/isolation check show no unintended connection; a scope snapshot can only disfavor dynamic coupling. | Review the actual layout/netlist, then safe unpowered resistance checks on the identified nets. |
| H043 | Leakage on UPDI line | Idle line level and measured leakage remain normal under the actual target supply and across repeat events; no valid numerical UPDI leakage limit was located in the reviewed table. | Measure actual idle voltage/current and target-side edge shape with known topology; isolate only if safely authorized. |
| H044 | Excessive parasitic capacitance on UPDI line | Target-side edge settling remains repeatable and adequate for the transmitted frames during the failing state; no device-specific UPDI load-capacitance maximum was found, so this is only a disfavoring result. | Low-capacitance active probe on both verified UPDI nodes during BREAK/SYNC; compare edge/settling behavior without changing wiring. |
| H045 | Unintended pull-up/down or series resistor on board UPDI | Verified board schematic/BOM and physical net inspection show no unexpected network element, and measured idle/edge behavior matches the known path. | Obtain the actual BOM/netlist and inspect the identified UPDI path; no such artifact is present locally. |
| H046 | Leaky ESD/TVS diode on UPDI | Verified BOM/layout shows no such part, or its safely measured leakage is within its documented specification and it causes no waveform displacement. | First identify any protection component from the actual board design; then safe unpowered inspection/leakage measurement. No part is currently identified. |
| H047 | Other component attached to UPDI | Verified board netlist shows only the connector and MCU (plus explicitly documented series parts) and no other branch/load. | Inspect actual netlist and board routing; compare the two UPDI nodes during failure. Current design evidence is absent. |
| H048 | Long UPDI trace or noisy parallel trace causes crosstalk | Layout inspection does not show the proposed coupling route and repeated target-side waveforms show no disturbance correlated with adjacent switching activity. | Actual PCB layout plus simultaneous UPDI/adapter-TX capture during the exact failing BREAK and representative radio/switch activity; do not toggle unknown loads. |
| H049 | AVR UPDI pin damaged by ESD or overvoltage | A verified path produces valid read-only target responses from this same identified device with valid levels at the MCU pin. Current local-echo failure does not exercise a target request and therefore neither supports nor falsifies pin damage. | Only after an independently verified adapter path is available, perform a bounded read-only identity probe and verify levels at the actual MCU pin; no crossover is currently safe. |
| H050 | UPDI voltage level does not match target VDD | Simultaneous target VDD, local ground, adapter TX and target-side UPDI remain within documented device stress limits with valid frame levels. Exact UPDI VIH/VIL remains unspecified in the reviewed data sheet. | Capture those four quantities at the target during both BREAKs; compare to actual VDD, not a presumed 3.3 V/5 V system. |
| H051 | Unstable UPDI ground reference | Repeated adapter-to-target ground-offset capture has no transient coincident with TX/echo failure and enough bandwidth/resolution to see the event. | Same differential ground-offset capture as H018, synchronized with TX and both UPDI nodes. |
| H052 | Loose or drifting resistor in UPDI chain | The identified component and its connections measure stable over repeat failure events and both sides of it retain the same UPDI waveform. | First verify a resistor exists using the actual BOM/net; then safe continuity/resistance and simultaneous waveform on both sides. |
| H053 | EMI or crosstalk from radio/switching circuitry couples onto UPDI | No UPDI disturbance correlates with the relevant activity across repeat observations, and a safely controlled activity A/B does not move the failure. | Correlate the actual switching/radio state with target-side UPDI capture; no activity toggling or wiring changes are authorized here. |

The software evidence currently cannot separate the external adapter/half-duplex echo path from a board load that alters the local echo. It also cannot distinguish one board-local part from another.

## Smallest next physical discriminator

Do not perform a crossover or alter wiring. On a qualified bench, capture the existing failing pairing without changing its supply, connector, harness, reset state or adapter. Use low-capacitance, high-impedance probes and record probe loading. Capture the first and second BREAKs and a representative RUN interval in one synchronized acquisition:

1. MCU VDD at the device pin pair relative to the adjacent MCU-local GND.
2. Adapter GND relative to that MCU-local GND.
3. RESET relative to MCU-local GND.
4. Adapter TX relative to adapter GND.
5. UPDI at the adapter/board entry relative to MCU-local GND.
6. UPDI at the MCU pin relative to MCU-local GND; if a series element is confirmed, measure both sides without assuming its presence.

Trigger on the actual adapter TX transition that starts BREAK1 and retain the subsequent BREAK2/SYNC window; include at least 100 ms before/after each attach sequence and a separate RUN window using the same channel setup. Sample at ≥20 MS/s. Preserve scope-native files and probe bandwidth/capacitance, channel references, trigger, volts/div, timebase, sample rate, supply state, path ID, and exact host event timestamps. Do not inject RESET, high voltage, or any target command beyond the already authorized read-only campaign. If the failing target-side waveform is clean and the source/target nodes agree, a later known-good echo-plus-target-request capture is needed to assess target response; it is not available in this epoch.

This capture can sort rail/reference excursions from line-path waveform loss and adapter-TX/echo divergence. It cannot by itself name a cracked joint, specific capacitor, ESD part or silicon defect. To prove a component cause, first obtain the actual schematic/BOM/net and perform a one-variable, safe intervention with restoration evidence.

## Source evidence files

Source review and exact sections/URLs: experiments/updi_rca/evidence/RCA_PHY_01/target_path/OFFICIAL_SOURCE_REVIEW.md.

Fetched/raw evidence under experiments/updi_rca/evidence/RCA_PHY_01/target_path:

- AVR128DA28-32-48-64-DS40002183.pdf — SHA-256 0001076aa7fb795acef725a38e500e37efe01782b6328f02b54ac0dbb5482b3b
- AVR128DA28-32-48-64-DS40002183.txt — SHA-256 fc64a7fd158361733c7d74e6cbac11d8395a1b14d5840a4ad8c3a9817f0f8bb8
- AVR128DA-DS80000882.pdf — SHA-256 cae3820ed15d73ca0d5dec20e9de45a8d7b25e04c4bb9685df43072f1f782ee2
- AVR128DA-DS80000882.txt — SHA-256 a3014ca62b07f4705f38168091eda89e12aca851c6c60d4f8f809ca5a42cf67c
- microchip_avr_updi_interface.html — SHA-256 cb5635595bd975bc2fa0416cd6cad98ef041bedc6e3bd89dc707feded3c8d611

Local raw logs or target readings were not created by this investigator.
