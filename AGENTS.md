# AGENTS.md — AVR128DA28 / LoRa Embedded Engineering

> Repository-level working instructions for coding agents. Work like a practical embedded engineer: inspect, implement, build, test, deploy when permitted, and report what the hardware actually did. Keep process overhead minimal.

## 1. Mission and current MVP

- **Gateway = DATA sender; Tracker = DATA receiver.** The immediate milestone is **one real bidirectional LoRa DATA/ACK exchange**, not FOTA, certification, or productization.
- DATA application payload: ASCII `hello world` (exactly **11 bytes**, no trailing NUL or newline).
- DATA sequence: `1` using the **existing** on-wire protocol encoding.
- Expected ACK: existing protocol type `0x03`, sequence `1`.
- Prove: Gateway `DATA_TX` -> Tracker `DATA_RX` with payload **11/11 bytes** -> Tracker `ACK_TX` -> Gateway `ACK_RX` and **ACK accepted**.
- The project's requested diagnostic frequency is **915.000 MHz**. Use the existing configured profile and an already-established appropriate RF test arrangement. Do not turn each firmware task into a new site/approval review; if the actual arrangement is unresolved, finish non-transmitting work and state the one specific blocker.
- Stop after one verified exchange. T01–T04, NACK, ARQ, SD, FOTA, security enhancements, UI, and production readiness are **follow-up tasks only when explicitly requested**.

## 2. Operating philosophy

1. **Make the smallest working change.** KISS, YAGNI, Occam's Razor, Gall's Law.
2. **Investigate the immediate failing boundary**, not every theoretical failure mode.
3. **Reuse the existing project**: drivers, command parsers, protocol frames, test tools, PlatformIO environments, radio profiles, and upload scripts.
4. **Source evidence beats assumptions.** Compiler output is build evidence; SPI readback is register evidence; two-sided serial captures are RF exchange evidence.
5. **Progress autonomously through reversible steps**: inspect -> patch -> focused build -> focused test -> physical verify.
6. **Do not create process artifacts by default**: no plans, STAR reports, RCA documents, checklists, workflow snapshots, handoff notes, or multi-agent jobs unless directly needed to solve the task.
7. **Do not ask again for facts already provided.** Ask only for a genuinely missing physical fact, a required write authorization, or an irreducible safety blocker. Keep questions precise.
8. **Do not invent** serial numbers, commands, firmware hashes, protocol layout, measured RF metrics, ports, or PASS results.
9. If work is blocked, complete every independent, non-destructive engineering action first; report `BLOCKED` with the exact blocker.
10. Prefer boring, reliable C and small state machines over frameworks, dependencies, and abstractions.

## 3. Project truth and protected files

Read these before making changes that depend on pins, radio parameters, build targets, or programming boundaries:

- `config/lora_system.json`
- `docs/ssot/GATEWAY_SSOT.md`
- `docs/ssot/TRACKER_SSOT.md`
- `include/generated/`
- `generated/lora_platformio.ini`

**Read these, but do not edit, delete, or regenerate them** as a side effect of ordinary firmware work. They are the project SSOT and generated outputs. If they disagree with observed hardware, report the discrepancy and change only the relevant source or application code after confirming the correct mapping. Do not silently redefine the hardware.

Prior bring-up results, logs, source code, and schematics are evidence, not substitutes for fresh checks. Treat the specific active repository scripts and environment names as discoverable; **do not invent commands or paths**.

Keep **BOOT, BOD, fuses, EEPROM, USERROW, calibration, factory identity, firmware backups, and protected Flash** unchanged. Do not use chip erase or a programming operation whose erase/write range is unknown. Apply firmware updates to the confirmed application range only.

## 4. Target architecture

- MCU: **Microchip AVR128DA28**, 8-bit AVR DA family, **128 KiB Flash**, **16 KiB SRAM**, **512 B EEPROM**.
- Radio: **RFM95W / Semtech SX127x-class LoRa transceiver**, controlled over SPI. Determine the exact module/variant from the active SSOT and physical hardware.
- Two different physical board designs may be present. They do **not** necessarily share pin mappings.
- Gateway-side physical design may include an ESP32 carrier and multiple AVR-based LoRa daughterboards. Do not equate an ESP32 UART, a USB adapter, and the intended AVR radio target without identity evidence.
- Use `avr-gcc` / the project's existing PlatformIO and UPDI workflow. Prefer `stdint.h`, static allocation, bounded buffers, explicit timeouts, and simple state machines.
- Keep interrupts short. Move logging, parsing, SPI transactions, and retries out of long-running ISRs where practical.
- Avoid heap allocation, recursion, large stack buffers, gratuitous `printf`, and duplicate payload copies unless the existing application needs them.

### Board-specific signal reference (schematic context; SSOT overrides)

These are **schematic reference mappings**, not permission to override current wiring or SSOT:

| Signal | Tracker (RFM95W) | Gateway LoRa daughterboard (RFM95/98) |
|---|---|---|
| SPI MOSI | PC0 | PC0 |
| SPI MISO | PC1 | PC1 |
| SPI SCK | PC2 | PC2 |
| Radio NSS/CS | PD0 | PC3 |
| Radio RESET | PD1 | PD0 |
| Radio DIO0 / IRQ | PD3 (`RF_IRQ`) | PD2 (`DIO0`) |
| Radio DIO1 | PD2 (`RF_DIO1`) | PD3 (`DIO1`) |
| Radio power enable | PA7 (`EN-LORA`) | Verify carrier/daughterboard power control |

Use role-specific pin definitions from the active configuration; never merge pin maps merely because both use AVR128DA28. GPS/SD power isolation on Tracker is intentional and should remain untouched during radio-only tests.

## 5. Board and serial-port identity

- `/dev/ttyUSB0` and `/dev/ttyUSB1` are **transient adapter names**; USB enumeration can reverse between runs.
- Prior observation: physical adapter port 1 appeared as `ttyUSB0`, and port 4 as `ttyUSB1`. This is **not** a role assignment.
- Read each target's **AVR MCU serial/identity** via the established UPDI or diagnostic method; compare with the verified project evidence.
- Only then map `GATEWAY_PORT` and `TRACKER_PORT`. The variable value is a port, while the **identity check** decides which role receives it.
- If two identities are missing, duplicated, or inconsistent, do not program or transmit using a guessed mapping.
- Keep programmer access and serial logging separate when tools cannot share a port. Ensure adapters are released before reusing them.

## 6. AVR128DA28 implementation details

### SPI and GPIO

- Match the actual MCU `PORTMUX`, SPI peripheral, CS routing, and peripheral clock configuration to the board's active pin map.
- Confirm SPI host mode and expected SPI mode/timing. CS must remain asserted for an entire register or FIFO transaction; deassert between independent transactions.
- Verify **real** SPI on the intended board with a stable register read such as SX127x `RegVersion` (`0x42`), expected `0x12` for the known working devices.
- Read multiple relevant registers after configuration. A successful write API call alone does **not** prove the register took effect.
- Preserve silicon workarounds. In particular, for affected AVR DA revisions, when `PORTMUX.SPIROUTE = NONE`, `SPIx.CTRLB.SSD` must be set to maintain SPI host mode. Do not regress the existing corrected code.
- Respect GPIO direction and power-enable sequencing; do not infer an RF failure from an unpowered module.

### Memory and programming

- **Application-only programming**: identify MCU, image, address range, and erase behavior before upload. Confirm BOOT and other protected ranges remain outside it.
- Require explicit approval only when a **specific new physical firmware write** is necessary and not already authorized. Supply target identity, image path/hash, and write ranges in that request; do not ask generic repetitive approval questions.
- Prefer existing UPDI application-only write/readback scripts; do not invent flags or use generic `upload` blindly.
- Verify readback for written bytes. Avoid reflashing identical installed images.
- Treat flash mapping, multi-page erase, and EEPROM erase silicon errata as engineering hazards; preserve any existing workarounds.
- Preserve observed BOD/POR state evidence. **Historical `BORF` does not demonstrate a fresh reset**. Compare new timestamped captures and current reset flags.

## 7. SX127x LoRa driver rules

### Register-level diagnostics

- `RegVersion` = `0x42`; known-good observed value = `0x12`.
- `RegOpMode` = `0x01`. In LoRa mode, `0x81` is standby and `0x85` is RX continuous **for the verified HF configuration**; do not generalize these constants to all modes.
- `RegFrfMsb/Mid/Lsb` = `0x06/0x07/0x08`; observed `E4 C0 00` corresponds to **915.000 MHz** with the documented **32 MHz** reference clock.
- The existing **HF-mode correction** matters: `RegOpMode` bit 3 (`LowFrequencyModeOn`) is **0** for the verified 915 MHz setup. Preserve the correct sleep/standby sequencing when changing LoRa modem mode.
- `RegIrqFlags` = `0x12`: `RxDone` bit 6, `PayloadCrcError` bit 5, `TxDone` bit 3. Clear IRQ flags using the chip's documented write-one-to-clear behavior; do not accidentally clear unrelated evidence before capturing it.
- Check the active FIFO base/address pointer, payload length, header mode, RX byte count, DIO mapping, and frequency settings when a packet is missing or malformed.
- Prefer checking actual status registers over assuming an interrupt callback fired correctly.

### PHY agreement

Both endpoints must agree on the **entire** PHY profile, not just center frequency:

- Frequency, bandwidth, spreading factor, coding rate
- Preamble length, explicit/implicit header mode
- Payload CRC enabled/disabled and modem mode
- Sync word, IQ inversion, LNA/PA path and radio power state
- DIO0/DIO1 mappings, IRQ masks, and FIFO handling

Read these from SSOT/existing profiles. **Do not introduce a new radio profile** merely to run `hello world` if a known working candidate exists. `RegVersion`/FRF agreement is necessary but not sufficient proof of an RF link.

### Transmit and receive sequencing

- Start the Tracker first; obtain a **fresh** `RX_READY` observation before sending.
- On Gateway: load the existing DATA frame to FIFO, start TX, wait for `TxDone` with a bounded timeout, clear relevant IRQ, and switch promptly into RX for ACK.
- On Tracker: detect `RxDone`, reject CRC-error frames, read the full received packet, decode the **existing** frame format, validate DATA sequence `1` and the **11-byte application payload** `hello world`; then send a real ACK using existing format/type `0x03`, sequence `1`.
- On Gateway: distinguish `ACK_RX` from `ACK_ACCEPTED`. Accept the ACK only if actual received bytes decode as the expected type, session/peer context where applicable, and matching sequence `1`.
- Report the observed sender/receiver-side timestamps. Use bounded wait/retry behavior; **do not retry forever** or transmit repeatedly after success.
- Derive timeout budgets from the configured LoRa PHY airtime plus TX/RX turnaround and measured firmware overhead; avoid arbitrary short constants that systematically reject valid packets.
- Prefer event-driven handling when working; fall back to bounded IRQ-flag polling for diagnostics when DIO wiring/IRQ routing is suspect.
- No fake `DATA_RX`, local loopback, forced `ACK_ACCEPTED`, or host-only simulation may count as physical RF success.

## 8. MVP test method

**Expected one-shot exchange** (using existing command syntax discovered in the repository):

1. Identify both MCUs by serial and resolve correct role-to-port mapping.
2. Confirm correct installed application image or obtain approval for the exact necessary app-only write.
3. Read actual SPI registers on **both** radios; confirm matching PHY and working power/isolation state.
4. Start separate non-overflowing captures for both targets.
5. Start Tracker receive; observe a new `RX_READY` event.
6. Issue exactly **one** Gateway DATA request with application payload `hello world`, length `11`, sequence `1`.
7. Capture Gateway `DATA_TX`/`TxDone`, Tracker `DATA_RX`/CRC/payload comparison, Tracker `ACK_TX`, and Gateway `ACK_RX`/`ACK_ACCEPTED`.
8. Return both radios to standby (known-good observed `0x81`), stop captures, and report the result.

If a single exchange fails, classify the **first broken boundary**:

| Boundary | First checks |
|---|---|
| MCU identity/target | Serial number, UPDI target, role map, powered device |
| SPI | Power enable, clock, CS, GPIO direction, PORTMUX/SSD, `RegVersion` |
| Radio configuration | HF bit, FRF, BW/SF/CR, sync word, CRC, IQ, DIO mapping |
| Gateway TX | FIFO length/address, mode transition, `TxDone`, IRQ flags |
| Tracker RX | `RX_READY`, `RxDone`, CRC flag, packet count, FIFO payload |
| Tracker ACK TX | Existing frame encoder, sequence, TX state, `TxDone` |
| Gateway ACK RX | Timely RX rearm, IRQ, payload decode, ACK validation |
| Logging/reset | Incremental `STATUS`, UART backpressure, fresh reset evidence |

Patch only the confirmed fault. Preserve all unrelated working logic. Rerun the one test that proves the fix and any narrow regression tests affected by source changes.

## 9. Build, tests, and deployment

- Inspect the repository's active `platformio.ini`, generated environment, and scripts first; **do not assume a universal target name or hard-code an unverified command**.
- Run the smallest build/test set that covers modified sources. Reuse valid prior results when there are no relevant changes.
- Check compiler warnings, linked Flash/SRAM sizes, stack risk, and section/address boundaries on any changed image.
- Host unit tests validate protocol state machines; they do **not** prove physical SPI or physical RF.
- If a build fails, read the **first actionable compiler/linker error**, fix it, and rerun that target rather than rebuilding the entire matrix.
- Only flash when a new verified application image is necessary. Avoid writes to protected areas; verify identity and readback afterward.
- Do not expand the MVP into bootloader changes, SD/FOTA staging, filesystem work, codebase-wide lint, repository refactoring, or report generation.

## 10. Logging, measurement, and evidence

- Keep serial output compact, structured, and incremental. **Do not concatenate large `STATUS` strings into bounded buffers**, which previously caused logger overflow.
- Prefer events such as `RX_READY`, `DATA_TX`, `TX_DONE`, `DATA_RX`, `CRC_OK`, `ACK_TX`, `ACK_RX`, `ACK_ACCEPTED`, and `TIMEOUT`, following existing command/log naming where possible.
- Capture both boards' identity, timestamps, packet type/sequence, payload byte count, decode/CRC result, IRQ status, and failure reason.
- RSSI/SNR and latency are useful **only if actually observed**; never fabricate unavailable measurement values.
- A Gateway `TX_DONE` is not evidence Tracker received anything. Tracker `ACK_TX` is not evidence Gateway accepted the ACK.
- A PASS requires **both sides' actual hardware evidence** and matching packet semantics.
- Keep logs in existing artifact locations when the harness already writes them; do not generate new documentation for its own sake.

## 11. Decision and intervention policy

**Default: do engineering work, not project management.**

Proceed without discussion for read-only inspection, source edits, focused builds/tests, serial capture, and ordinary non-destructive diagnostics. Continue through reversible changes autonomously.

For a necessary physical firmware write, request the one exact permission described above unless already covered by explicit authorization. Use only established, safe physical access and RF connections; never assume unknown wiring, input power, or RF path is safe. For RF transmission, use the verified test arrangement and bounded one-shot commands; if a prerequisite is genuinely missing, name the fact in `NEXT` rather than initiating broad reviews.

Stop only at a **real** blocker: missing/ambiguous target identity, unsafe or unknown electrical/RF connection, unauthorized/destructive programming requirement, incompatible installed image, inability to reach the device, or a reproducible technical failure that cannot be resolved with available evidence. Never conceal a blocker or relabel `NOT_RUN` as `PASS`.

## 12. Response contract

For normal MVP execution, return **at most five lines**:

```text
ACTION: <actual command/change/operation performed>
RESULT: <specific observed output, including bytes/sequence when available>
FIRMWARE: PASS|FAIL|NOT_RUN
PHYSICAL_RF: PASS|FAIL|NOT_RUN
NEXT: <one exact next action, or NONE>
```

Use `PHYSICAL_RF: PASS` **only** when Gateway physically sends DATA, Tracker actually receives all 11 `hello world` payload bytes, Tracker physically transmits ACK type `0x03` sequence `1`, and Gateway actually receives **and accepts** it.

Do not add STAR, RCA, executive summaries, success theater, or a documentation-only response unless the user explicitly requests documentation or deeper analysis. For detailed investigations requested by the user, expand the explanation as needed, but keep it technical and evidence-based.

## 13. Technical references (read when relevant; do not substitute for active SSOT)

- Microchip AVR128DA28/32/48/64 datasheet, DS40002183: https://www.microchip.com/content/dam/mchp/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-DS40002183.pdf
- Microchip AVR128DA silicon errata, DS80000882F: https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/Errata/AVR128DA-28-32-48-64-SilConErrataClarif-DS80000882.pdf
- Semtech SX1276/77/78/79 datasheet, Rev 7: https://cdn.sparkfun.com/assets/7/7/3/2/2/SX1276_Datasheet.pdf
- PlatformIO AVR128DA28 board: https://docs.platformio.org/en/latest/boards/atmelmegaavr/AVR128DA28.html
- PlatformIO Atmel megaAVR programming: https://docs.platformio.org/en/latest/platforms/atmelmegaavr.html
- Codex repository instructions: https://learn.chatgpt.com/docs/agent-configuration/agents-md

**Bottom line:** deliver one reproducible real-radio `hello world` / ACK exchange on the two correctly identified AVR128DA28 boards, with the smallest necessary firmware change and no unnecessary ceremony.
