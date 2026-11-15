# LoRa-only ARQ recovery — RCA continuation

> Historical snapshot from before the 923 MHz profile and final host-test-stage fixes. The current English STAR report is [FINAL_RCA.md](FINAL_RCA.md).

## Situation

Historical H01 sessions 8 and 9 produced **10 Gateway DATA TxDone events**, **10 ACK-window timeouts**, **2 TIMEOUT_EXHAUSTED results** and **0 accepted ACKs**. Session 9 recorded Tracker's saved reset cause changing **0x20 → 0x01**. Tracker RX, DATA acceptance and ACK TX were not captured; the reset was not independently time-localized. A separate continuous-RX idle control lasted **120.029947 s** without the same saved-cause transition. These observations do not identify an electrical component or prove when the reset occurred.

The prior source audit found that the fixed **915 MHz** profile retained RegOpMode bit 3. Its candidate correction was already present but unflashed. The new request was to retain that correction, provide a minimal LoRa-only mode and prove short-message DATA/ACK/NACK when physical preconditions permit.

## Task

Preserve existing work and incident evidence; reuse RadioLib **7.1.2**, DxCore **1.6.2** and corrected upditerm; isolate nonessential Tracker peripheral interfaces safely; build and test both physical-board roles; collect useful live observations; avoid claiming an RF or power fix from a build or STATUS response.

No oscilloscope, logic analyzer, independent RF receiver, voltage logger or controllable alternate supply was available. The latest repository safety hold requires assembled antenna/module/bridge inspection. Actual supply wiring and SD socket population were not remotely verifiable. The operator subsequently requested English, so this report is in English.

## Action

Reviewed the active ARQ adapter, generated board setup, protocol/core tests, current hardware config, previous RCA and raw manifests. Inspected all three supplied schematics from the legacy repository without modifying it. Consulted primary Semtech, u-blox, Microchip and versioned RadioLib/DxCore sources; [source log](references/SOURCE_LOG.md).

Implemented `ARQ_RADIO_ONLY_DIAGNOSTIC` in two dedicated environments. Tracker releases GPS UART/TIMEPULSE before commanding main power off, commands SD off and refuses radio startup if the shared unisolated SD bus has a detected card. It retains LoRa power for the exchange, excludes sensor/filesystem/tracking activities and avoids PA7's LED alias. Gateway keeps its separate board mapping. No protocol, payload, PHY or dependency upgrade was introduced. [Implementation](RADIO_ONLY_IMPLEMENTATION.md), [power policy](PERIPHERAL_POWER_POLICY.md).

Used RED → GREEN at the setup/loop boundary. Testing actual generated initialization revealed that it removed the diagnostic card-detect pull-up; corrected the generator under the diagnostic flag. Retained the existing HF field correction and verified RX/TX/retry/reinitialization behavior against real installed RadioLib source using a modeled electrical HAL. [Test report](RADIO_ONLY_TEST_RESULTS.md), [HF audit](HF_MODE_VERIFICATION.md).

Executed a fresh live non-RF experiment on both verified MCUs. Raw UPDI TX/RX, complete STATUS responses, MCU identity, peripheral register states, reset-state snapshots and cleanup were recorded. The preserved Tracker completed **20/20 STATUS**, Gateway **1/1**. No candidate was programmed and no RF command was sent. The live baseline still reads **0x89** in standby on both radios. [Live data](live-summary.json), [experiment script](experiments/non_rf_status.py).

The baseline already commands GPS/SD off and has USART2/PF0/PF1 disabled/released. Consequently, a claim that this candidate newly removes those baseline loads would be wrong. Its additional value is deterministic ordering, the SD refusal guard and an explicitly selected build.

## Result

| Metric | Actual result / evidence |
|---|---|
| Focused Host/firmware tests | **84 passed, 0 failed** — [log](tests/focused-gcc-final.txt) |
| PlatformIO environments | **10 succeeded, 0 failed** — [inventory](FIRMWARE_BUILD_RESULTS.json) |
| Real installed RadioLib HAL | **12 candidate TX/RX cycles**, two reset models; simulation — [log](tests/real-radiolib-hal.txt) |
| Full unittest suite | **301 run, 1 skipped, 0 failures/errors** with bundled GCC 16.2.1 through a temporary `uv` wrapper — [log](tests/full-suite-project-gcc-final.txt) |
| Tracker live STATUS | **20 passed / 20 attempted, 0 failed**, duration **152.886140 s** — [summary](live-summary.json) |
| Tracker STATUS latency | Minimum **7511.414 ms**, median **7645.854 ms**, maximum **7742.888 ms** |
| Gateway live STATUS | **1 passed / 1 attempted, 0 failed**, **7778.657 ms** |
| Startup/CPU control | **2 BREAKs per board; 0 requested resets, 0 CPU resumes** — [Tracker verdict](raw/receiver/verdict.json), [Gateway verdict](raw/gateway/verdict.json) |
| Raw UPDI records | **111,203** — [Tracker trace](raw/receiver/transport-trace.jsonl), [Gateway trace](raw/gateway/transport-trace.jsonl) |
| Candidate flashes | **0** — [candidate hashes/build IDs](candidate-builds.json) |
| New DATA/ACK/NACK RF sessions | **0 / 0 / 0**; physical hold remains |
| Newly observed RF TxDone/RxDone/accepted ACK | **0 captured** because no new RF trial occurred; not evidence of a new failed link |
| Reset evidence this sample | Tracker saved cause **0x01 → 0x01**; Gateway **0x20 → 0x20**; RSTFR **0 → 0** on each |
| Voltage/current | **UNKNOWN — requires rail/source measurements** |
| Historical manifests | **328 file records checked, 0 missing, 0 mismatches** — [integrity](historical-integrity.json) |
| New-run preservation and hashes | See [preservation](preservation.json) and [SHA-256 manifest](sha256.json); intentional source/generated changes are distinguished from archived evidence |

The STATUS run used the existing recorder's **180 s** total budget. Its duration exceeds the earlier separate **120 s** Gate 1 limit; this report claims a 20-response stability sample, not compliance with that old deadline.

### Regulatory and execution follow-up

NBTC's published general-use frequency table lists **920–925 MHz** for Non-RFID equipment with equipment and power conditions. The 2026 NBTC item found here is a consultation on a draft expansion, not proof that this 915 MHz prototype is authorized. No lab authorization, type approval, or applicable 915 MHz test permission was available. See the [NBTC Non-RFID 920–925 MHz announcement](https://www.nbtc.go.th/th/law/announce/688543/688545/701196/688752/) and [2026 consultation notice](https://www.nbtc.go.th/News/Press-Center/76325.aspx?lang=th-th).

No candidate image was flashed and no RF emission was attempted. The programming flow requires confirmed supply, ground, UPDI, application layout and RF suitability before it uploads an RF-capable image. STATUS proves non-RF responsiveness, not supply safety during programming or TX. Switching to 920–925 MHz also changes a controlled PHY variable and requires applicable equipment approval. See [execution blockers](REGULATORY_AND_TOOLCHAIN_FOLLOWUP.md).

### Observation classification

- **OBSERVED:** identity-bound STATUS replies, unchanged GPIO intent, baseline 0x89/E4C000, saved reset bytes and successful cleanup.
- **DERIVED:** decoded GPIO/mode fields and Host monotonic latencies.
- **INFERRED:** current firmware corresponds to archived restored build identity. A fresh complete Flash SHA-256 readback was not obtained.
- **HYPOTHESIS:** HF correction affects packet delivery; a power-path event contributes to historical POR; SD signal injection contributes if a card is fitted.
- **UNKNOWN:** actual off-rail voltages, current, RF radiation, Tracker RX/ACK boundaries during historical H01 and the POR trigger.

Unchanged GPIOR0=1 does not by itself exclude another POR. Sampled uptime increased across the responses; no new reset indicator was captured in this non-RF observation window. No result here proves stability during TX.

## Required final questions

| # | Question | Answer and supporting artifact |
|---:|---|---|
| 1 | HF defect corrected in source? | **Yes**, retained bit-3 field update — [HF audit](HF_MODE_VERIFICATION.md) |
| 2 | Candidate flashed to both correct devices? | **No, 0 flashes** — [manifest](candidate-builds.json) |
| 3 | Candidate HF mode read back on hardware? | **No**; preserved baseline reads 0x89 — [live records](live-summary.json) |
| 4 | SAM-M10Q main power actually disabled? | **COMMANDED OFF ONLY**: PD5 high; voltage UNKNOWN — [registers](raw/receiver/registers-after.json) |
| 5 | GPS interfaces electrically safe? | Software intent verified: USART2 off, PF0/PF1 inputs, no pull-ups in baseline; candidate ordering tested. Pin voltage/backfeed unmeasured — [policy](PERIPHERAL_POWER_POLICY.md) |
| 6 | SD main power actually disabled? | **COMMANDED OFF ONLY**: PD6 high; card presence and rail voltage UNKNOWN — [policy](PERIPHERAL_POWER_POLICY.md) |
| 7 | LoRa powered throughout DATA/ACK? | **UNKNOWN physically**; PA7 low is observed in standby and maintained in simulated DATA/ACK — [tests](RADIO_ONLY_TEST_RESULTS.md) |
| 8 | Tracker received DATA? | **UNKNOWN for candidate/historical failed H01** — no new RF trial and no surviving historical RX evidence — [historical RCA](../20261114T023251Z/FINAL_RCA.md) |
| 9 | Tracker accepted DATA? | **UNKNOWN physically**; portable core acceptance tests pass — [tests](RADIO_ONLY_TEST_RESULTS.md) |
| 10 | Tracker transmitted ACK? | **UNKNOWN physically**; no new ACK trial — [test matrix](RADIO_ONLY_TEST_RESULTS.md) |
| 11 | Gateway received/accepted ACK? | **Not demonstrated**: historical accepted ACK count 0; candidate trials 0 — [historical RCA](../20261114T023251Z/FINAL_RCA.md) |
| 12 | New POR? | **No new reset indicator captured in this non-RF sample**; saved POR already set at acquisition — [before](raw/receiver/registers-before.json), [after](raw/receiver/registers-after.json) |
| 13 | Did GPS/SD isolation change RF outcome? | **UNKNOWN**; no physical comparison, and baseline already commands them off — [power policy](PERIPHERAL_POWER_POLICY.md) |
| 14 | Did HF correction change RF outcome? | **UNKNOWN**, candidate not flashed — [HF audit](HF_MODE_VERIFICATION.md) |
| 15 | Supply transient measured? | **No**; MCU VDD/3V3-LORA minimum and timing UNKNOWN — [baseline](baseline.json) |
| 16 | Root cause isolated? | Configuration discrepancy isolated; **RF/POR mechanism remains PARTIALLY_ISOLATED** — [historical RCA](../20261114T023251Z/FINAL_RCA.md) |
| 17 | Combined fix safe for production? | **Not accepted for production**; requires physical validation, empty socket policy and RF/reset regression — [implementation constraints](RADIO_ONLY_IMPLEMENTATION.md) |
| 18 | Remaining proof? | Verify assembled antenna/bridge/module, source wiring and empty SD socket; perform identity/readback-bound HF-only H01 comparison; measure rails if POR recurs — [test matrix](RADIO_ONLY_TEST_RESULTS.md) |

## Next physical decision

The next single discriminating experiment is **one bounded HF-only H01 baseline/candidate comparison**, after physical antenna/load, supply wiring and empty-socket checks. Preserve the original firmware, independently verify programmed images, keep the baseline peripheral states/PHY unchanged, read back 0x81 standby/0x85 RX, and require Tracker DATA reception plus Gateway acceptance of the matching ACK. Stop at the first reset or transport failure; preserve it. If no ACK arrives, observe Tracker radio RX and response stages before adding another configuration change. Then test the combined diagnostic policy and existing H02 NACK separately.

A later power A/B/A needs a suitable isolated 3.3 V source and measurements. No capacitor, regulator or antenna replacement is justified by this continuation. No additional dependency or protocol framework was added.

## Acceptance verdict

**RADIO-ONLY BUILD: PASS** — 10/10 relevant builds; physical acceptance blocked.

**HF CONFIGURATION: UNVERIFIED** on candidate hardware; source and modeled driver verified.

**GPS MAIN POWER: COMMANDED OFF ONLY** in observed baseline; candidate unflashed.

**SD MAIN POWER: COMMANDED OFF ONLY** in observed baseline; empty socket unverified.

**TRACKER DATA RX: UNKNOWN**

**TRACKER ACK TX: UNKNOWN**

**GATEWAY ACK ACCEPTANCE: FAIL** as an acceptance criterion: no candidate success demonstrated; this is not a newly observed RF failure.

**POR STATUS: UNKNOWN** during candidate RF; no new indicator captured in the non-RF window.

**ROOT CAUSE: PARTIALLY_ISOLATED**

**NEXT BLOCKER:** physical antenna/module/bridge and supply-path verification, empty SD socket, then independent candidate image/register readback and one complete DATA/ACK exchange. Rail voltage and POR timing still require instrumentation. Deployment readiness is not established.
