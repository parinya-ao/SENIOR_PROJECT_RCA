# AVR128DA28 BREAK / LOCAL_ECHO focused RCA

Epoch: **RCA_PHY_01**. Disposition: **BLOCKED_PHYSICAL** under stopping condition 4. The observed protocol boundary is LEVEL 1. No LEVEL 2 path attribution, LEVEL 4 component, or LEVEL 5 mechanism has been established.

## Situation

There are **2 external paths and 2 presumed targets**, with **0 independently identified targets**, **0 measured crossed cells**, and **0 completed causal A/B/A cycles**. Both USB descriptors are `10c4:ea60`, serial `0001`; identity is resolved by physical USB path while USB plugs stay fixed. P is `pci-0000:00:14.0-usb-0:4:1.0`, Q is `pci-0000:00:14.0-usb-0:1:1.0`. X/Y denote provisional targets paired with P/Q in the preserved evidence. Current target continuity, connector pinout and actual harness boundary are unconfirmed.

The immutable starting ledger has **509 run rows / 6,387 event rows**. The earlier continuation adds **40 run rows / 546 events**, giving **549 / 6,933**. This focused epoch adds **0 hardware run rows / 0 hardware events**. Replaying existing raw records is analysis, not a new experiment. The 40-row `break_attempts.csv` is a derived view of existing observations and must not be appended to the hardware ledger.

| Source epoch | Pairing | Condition | N | Pass / fail | Pass rate | Wilson 95% success CI | Median / p95 latency, ms |
|---|---|---|---:|---:|---:|---:|---:|
| Inherited baseline | P+X | SIB | 100 | 100 / 0 | 100% | 96.30–100% | 157.092 / 159.884 |
| Inherited baseline | P+X | Control | 100 | 100 / 0 | 100% | 96.30–100% | 201.537 / 204.744 |
| Inherited baseline | Q+Y | SIB | 100 | 0 / 100 | 0% | 0–3.70% | 1060.951 / 1064.443 |
| Inherited baseline | Q+Y | Control | 100 | 0 / 100 | 0% | 0–3.70% | 1061.433 / 1064.452 |
| RCA_CROSSOVER_01 | P+X | SIB | 10 | 10 / 0 | 100% | 72.25–100% | 156.332 / 158.131 |
| RCA_CROSSOVER_01 | P+X | Control | 10 | 10 / 0 | 100% | 72.25–100% | 201.944 / 203.732 |
| RCA_CROSSOVER_01 | Q+Y | SIB | 10 | 0 / 10 | 0% | 0–27.75% | 1061.647 / 1064.128 |
| RCA_CROSSOVER_01 | Q+Y | Control | 10 | 0 / 10 | 0% | 0–27.75% | 1061.556 / 1063.475 |

These intervals are descriptive binomial intervals; serial attempts may be correlated. They describe the tested pairing/operation, not the probability of a cause. Evidence score **1** describes observed-stage repeatability. Candidate-specific discriminating evidence score remains **0** because no entity has been crossed or physically measured.

The historical **19/60** missing ACC-data responses occurred **after exact echo**. That failure class remains a separate causal record. No new ACC attempt, reset event or runtime failure is inferred from this BREAK campaign.

## Task

Isolate the current first/second BREAK local-echo loss among **33 primary physical candidates**, with **8 methodology guards**, using the smallest experiment that removes the external-path/target confound. Preserve the existing **168** historical hypotheses and evidence without importing broad historical reset/runtime rankings into this physical-stage analysis. No repair, firmware rewrite, baud change, retry, timing workaround or component claim is justified by the current **0** causal interventions.

## Action

### Controls and source review

The coordinator re-read `PROMPT.md`, preserved reports/ledgers and actual probe implementation; `updi_rca_ai_agent_prompt.md` remains absent. The supplied focused specification controls this phase. Exactly the two existing workers were reused for external-path and target-electrical analysis. Neither opened a port or manipulated hardware. All shared code, reports and causal decisions remained with the coordinator.

The strict probe performs two serial `00` exchanges at **300 baud**, checking each local echo, before SIB/LDCS at nominal **38,400 baud**. A successful API write count establishes host acceptance, not voltage at the CP2102 or MCU. `EMPTY` means the serial read returned zero bytes in the logged read interval. Under ideal 8E2 framing, zero gives 10 continuous low host bit periods, **33.333 ms** at 300 baud, exceeding DS40002183E Table 35-3's worst-case recommended **24.60 ms**. Its 12-bit derivation uses the recovered UPDI timing, not 12 host 300-baud periods. This nominal calculation is not a waveform measurement or evidence of a BREAK violation. Actual low duration, levels and target-side reception remain unmeasured.

Primary-source findings, exact revisions and limits are preserved in [target source review](../evidence/RCA_PHY_01/target_path/OFFICIAL_SOURCE_REVIEW.md) and [external source review](../memory/EXTERNAL_PATH_AGENT.md):

- **Microchip DS40002183E, Rev. E, 09/2024**, and **DS80000882F, Rev. F, 09/2024** were fetched from the current official device links. Device-specific UPDI, supply, connector, RESET and layout sections were reviewed. No assembled-board schematic/BOM/netlist was found, so a reference circuit cannot establish actual population or topology. [Official data sheet](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-DS40002183.pdf), [official errata](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/Errata/AVR128DA-28-32-48-64-SilConErrataClarif-DS80000882.pdf).
- **Decoupling ambiguity:** current §4.2 / Figure 4-1 labels C1=100 nF primary, C2=1–10 nF high-frequency, C3=1 µF optional for specified transient/cycling circumstances. Current connector figures repeat 100 nF. Yet §41.4 says Rev. B changed primary decoupling from 100 nF to 1 µF. The coordinator checked both printed pages 21 and 696 visually. Both statements are recorded; no capacitor replacement or noncompliance conclusion follows. Placement guidance calls for close supply-pair decoupling and short supply/return paths. Actual board values/placement: **0 verified measurements**.
- DS40002183E gives **1.8–5.5 V** operating supply and maximum supply slew **0.25 V/µs** in the cited tables. Its general I/O threshold table is not a separately specified UPDI VIH/VIL guarantee. The current target voltage, operating clock and UPDI margins are unmeasured, so no guaranteed clock/voltage or target-UPDI threshold envelope is invented.
- **Silicon Labs classic CP2102/9 Rev. 1.8, January 2017**, Table 4: CP2102 RX VIH minimum **2.0 V**, VIL maximum **0.8 V**; guaranteed TX high/low values depend on supply and specified current. For example, VOH ≥ VDD−0.7 V at −3 mA and VOL ≤0.6 V at 8.5 mA under the table conditions. These are classic-device limits; actual chip marking/revision remains unverified. Duplicate configurable default descriptors do not authenticate the units. No CP2102C/N limits were substituted. [Official CP2102/9 data sheet](https://www.silabs.com/documents/public/data-sheets/CP2102-9.pdf).
- Vendored Streef Upditerm HEAD is **f2222b02ceeff7668caab0f240d2e13298116356**, version **1.1**, with local modifications preserved. The raw measurements use isolated RCA `probes.py`, so vendored revision alone cannot explain the failure. Reference wiring describes TX through a series resistor to shared UPDI, RX on the shared node and common GND; the actual resistor, supply routing and harness are unknown. [Pinned upstream source](https://github.com/streef/upditerm/tree/f2222b02ceeff7668caab0f240d2e13298116356).
- Linux USB errors/URBs/usbmon describe host-side transfer observations, not target VDD or UART/UPDI waveforms. This phase has **0 attempt-correlated kernel traces and 0 usbmon captures**. `usb_correlation.csv` contains **40 UNKNOWN correlations**, not 40 clean-USB results. [USB error codes](https://docs.kernel.org/driver-api/usb/error-codes.html), [USB host APIs](https://docs.kernel.org/driver-api/usb/usb.html), [usbmon](https://docs.kernel.org/usb/usbmon.html).

The current read-only preflight resolved both stable paths and observed **0 owner PIDs** for their current tty locators. ModemManager and brltty were inactive. Host mains was online; this is not a charger-effect experiment. Target power, movement, current physical pairing and instrument availability remain unknown. No serial port was opened.

### Test-first host tooling and replay

The inherited **53** tests passed through the isolated project. Required identity, immutable target labels, first/second BREAK, earliest-failure gating and conservative proof behavior were tested before implementation. Initial RED: **15 expected failures / 5 existing behaviors passing**; GREEN: **20 passing**. A subsequent all-four-cell effect test failed on its missing API, then the focused suite passed **22** tests. The full RCA suite passed **75**.

The small offline analyzer preserves first/second BREAK ordinal, exact TX/echo, expected/actual length, missing/extra count, first mismatch, XOR and overlapping-byte Hamming distance, host write/read timestamps and read latency. A zero Hamming distance over zero overlapping bytes does not indicate an exact echo. Missing capture and a zero-byte observed read are different states. A short host write stays HOST_TX. A later response cannot override an earlier failed echo.

Existing matrix classifiers were reused. Descriptive adapter/target/difference-of-differences effects require all four observed cells. With **2 original cells and 0 crossed cells per condition**, all three effects remain UNKNOWN. The locality-proof helper requires controlled movement/restoration and conservative repeated A/B/A evidence; it does not identify a component from a target effect.

### Physical gate and experiment decision

The earlier user response was **“Cannot do this safely.”** Safe power isolation, connector orientation and the actual harness boundary have not since been established. The coordinator therefore performed **0 new N=20 reproduction attempts**, **0 crossed screens**, **0 restorations**, **0 component substitutions**, and **0 repairs**.

For future crossover, the external bundle must explicitly include its physical USB port, cable, CP2102, bridge/resistor and adapter-side jumper. Swap target PCB connection only after safe isolation. The earlier proposed wording about swapping a complete target-side harness is superseded for future experiments: moving a jumper/resistor with the target could change two variables. No prior crossover occurred, so no historical observation is rewritten.

The written experiment contract in [FOCUSED_PLAN.md](../memory/FOCUSED_PLAN.md) specifies hypothesis, prediction, independent variable, controls, measurement, pass/fail criteria and interpretation before execution. The conditional sequence is N=20 original-pair SIB synchronization attempts per path, N=30 crossed screen per pairing, N=100 only if rates/uncertainty require it, then original-state restoration and repeated A/B/A. Handling sensitivity, both-fail setup changes and interaction remain separate outcomes.

## Result

### Observed stage and byte distribution

| Source epoch | Pairing | N attempts | BREAK1 empty | BREAK1 exact then BREAK2 empty | SIB/LDCS requests after failed sync |
|---|---|---:|---:|---:|---:|
| Inherited baseline | Q+Y | 200 | 171 (85.5%) | 29 (14.5%) | 0 |
| RCA_CROSSOVER_01 | Q+Y | 20 | 17 (85%) | 3 (15%) | 0 |

The earlier 40-attempt precheck yields **63 observed BREAK echo frames**: P+X **40 EXACT**; Q+Y **3 EXACT and 20 EMPTY**. There are **0 observed CORRUPT, SHORT, EXTRA or SHIFTED BREAK frames** in that precheck. Every failed BREAK sent `00`, with **1 byte accepted by the host write API** and **0 bytes returned by the echo read**. The inherited Q failure-stage counts are **200 LOCAL_ECHO**, with **0 valid target requests**; continuation counts are **20 LOCAL_ECHO**, with **0 valid target requests**. Failure-read timing is captured per frame; overall attempt medians/p95s are in the Situation table and [metrics CSV](focused_run_metrics.csv).

This establishes **LEVEL 1: host-observed BREAK/LOCAL_ECHO failure**, evidence score **1**, N=200 in the inherited failing-lane sample and N=20 in the continuation sample. It leaves **LEVEL 2 external versus target/reference unresolved**: **0 crossed observations, 0 causal repeats, 0 electrical measurements**, candidate evidence score **0**, causal-effect CI/latency **not applicable**.

### Causal decision record

| Question | Answer | Numeric / measurement boundary |
|---|---|---|
| Did failure follow the target? | BLOCKED | 0 crossed observations; 0 independently identified targets |
| Did failure follow external path/adapter? | BLOCKED | 0 crossed observations; port/cable/unit/resistor/harness still paired |
| Did reconnect alone change outcome? | UNKNOWN | 0 controlled reconnect experiments |
| Was there path×target interaction? | BLOCKED | 2/4 cells per condition, no complete matrix |
| Was USB error correlated with failure? | UNKNOWN | 0 attempt-correlated kernel/usbmon captures |
| Did exact local echo succeed? | YES on tested P pairings; failed on Q attempts | Q first echo sometimes exact, then second absent; 20/20 continuation attempts fail synchronization |
| Did control space succeed? | YES on P; NOT_REACHED on Q | Inherited P 100/100; Q 0 requests after failed sync |
| Did ACC fail after exact echo in this phase? | NOT_APPLICABLE | 0 new ACC attempts; historical 19/60 remains separate |
| Was failure RUNNING-state dependent? | UNKNOWN | 0 matched RUNNING/STOPPED state tests in focused phase |
| Was a new boot observed / reset flag correlated? | UNKNOWN | 0 independent boot markers; host SIGKILL and persistent BORF are not counted as resets |
| Are firmware hashes identical? | UNKNOWN | 0 paired current readbacks |
| Are fuses identical? | UNKNOWN | 0 paired current fuse snapshots |
| Were target VDD / ground offset / RESET / UPDI measured? | NO | 0 captures for each |
| Is a component cause proven? | NO — BLOCKED | 0 component-specific interventions or direct physical violations |

Focused status totals: **33 BLOCKED physical candidates, 8 UNRESOLVED methodology guards, 0 SUPPORTED, 0 STRONGLY_SUPPORTED, 0 PROVEN, 0 DISFAVORED, 0 FALSIFIED**. A prediction being compatible with a paired-lane result is not discriminating support for one component. The guard tests constrain interpretation; passing them does not prove the physical setup correct. Every target candidate has an explicit falsifier in [focused_hypotheses.csv](focused_hypotheses.csv).

The historical 168-row status tables remain **112 BLOCKED / 48 UNRESOLVED / 8 SUPPORTED**, unchanged. Their scores describe the broader prior investigation and are not probabilities or current physical-candidate evidence.

### Narrowest defensible conclusion

**Root-cause status: BLOCKED.** Software records establish host-observed BREAK1/BREAK2 LOCAL_ECHO loss on the Q+Y connection while tested P+X operations pass. They do not distinguish CP2102/USB/external contact, target shared-node loading, target power/GND/reference, interaction or multiple faults. No specific cable, resistor, header joint, capacitor or AVR defect is claimed.

**Smallest next action:** a qualified bench operator establishes safe power isolation, actual pinout and the frozen external-path/PCB boundary. If that gate can be satisfied, perform the written target-PCB-only crossover and restoration before choosing an external or target branch. Do not ask the user to repeat unsafe manipulation.

**If crossover remains physically inaccessible, exact required measurement:** capture a successful and failed first/second 300-baud `00` synchronization exchange with a common timestamped raw probe log. Simultaneously measure CP2102 TX, shared UPDI at adapter side, UPDI at target pad side, and MCU VDD relative to MCU-local GND; add adapter-GND versus MCU-local-GND offset with an appropriately rated differential setup/additional channel. Confirm power sources, probe grounding and low-capacitance loading first. Use ≥20 MS/s as an investigation floor and ≥100 ms pre/post-trigger where practical; trigger at the first/second BREAK. With only four channels, prioritize TX, target UPDI, local VDD and ground offset, then repeat under unchanged conditions to locate the series-node difference. These are investigation settings, not manufacturer MCU specifications. No scope trace is currently available.

No corrective action or post-repair regression is warranted until that measurement or repeated one-variable movement supports a causal candidate. No lower baud, longer timeout, random delay or reflash was used.

### Artifacts and verification

- [Focused hypothesis inventory](focused_hypotheses.csv): 33 primary candidates + 8 guards, each with prediction, discriminator, falsifier and status.
- [Crossover matrix](crossover_matrix.csv): 4 inherited original-condition rows and 4 explicitly blocked crossed rows; unmeasured success/failure/rate/CI fields are blank.
- [BREAK attempts](break_attempts.csv), [echo distribution](echo_error_distribution.csv), [metrics](focused_run_metrics.csv), [USB correlation](usb_correlation.csv), [proof ledger](root_cause_proof.csv), [effects](pairing_effects.csv), [current adapter inventory](focused_device_inventory.csv), [validation](focused_validation.csv).
- [Shared-node model SVG](../diagrams/focused_physical_model.svg) / [D2 source](../diagrams/focused_physical_model.d2); [isolation gate SVG](../diagrams/focused_isolation.svg) / [D2 source](../diagrams/focused_isolation.d2). Both rendered successfully with D2 v0.9.0 / TALA / theme 4. TALA is now open source/bundled; the installed skill's paid/proprietary statement is stale. [Current official TALA documentation](https://d2lang.com/blog/tala-is-open-source/).
- [Concise state](../memory/FOCUSED_CURRENT_STATE.md), [decisions](../memory/FOCUSED_DECISIONS.md), [external worker](../memory/EXTERNAL_PATH_AGENT.md), [target worker](../memory/TARGET_PATH_AGENT.md). Handwritten persistent memory is Markdown.

Verified full isolated host suite: **75 passed**. Inherited raw hashes **509/509**, continuation raw hashes **40/40**; inherited/continuation event rows remain **6,387/546**, unique and mapped, with **0 cross-ledger event-ID collisions**. The **21 frozen historical report/ledger files** retain their SHA-256 values. All **168** inherited hypothesis IDs and totals remain present; focused inventory is exactly **41** IDs. Source/manifests and focused artifact validation are recorded alongside the CSVs. Run rows use batch run IDs plus attempt keys; the unique analysis attempt key is `source_epoch:run_id:attempt`, not a tty alias.

Graphify was refreshed after code changes: **2,445 nodes / 4,012 edges** at that update. It reported existing external-header parse limitations, unsupported files and unavailable optional PDF extraction; these did not affect pytest, raw source reads or CSV verification. SVG XML/rendering was checked; raster visual export was unavailable because the installed ImageMagick SVG delegate is restricted, so no raster diagram QA is claimed.

Safety: **new flash writes=0; fuse writes=0; chip erases=0; BOD changes=0; physical interventions=0; serial opens=0 in RCA_PHY_01**. Historical flash/fuse budget remains preserved. Component-level uncertainty persists because no crossed pairing or electrical capture was possible.
