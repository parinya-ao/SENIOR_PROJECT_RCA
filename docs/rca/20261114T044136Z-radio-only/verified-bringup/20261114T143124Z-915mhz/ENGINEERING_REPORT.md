# 915 MHz deployment and bidirectional diagnostic verification

Status: **915_MHZ_DEPLOYMENT_VERIFIED — RF_FUNCTIONAL_VALIDATION_PENDING**.

## Situation

The prior physical baseline was 923 MHz with no candidate DATA/ACK test. Historical H01 reported Gateway TX_DONE without accepted ACK and a saved Tracker PORF; its electrical cause remains unknown. The original 915 MHz general-radio profile was already correct.

## Task

Restore ARQ and reverse-raw to 915 MHz, preserve HF/errata and board protections, deploy verified candidates, and prepare four bounded DATA/ACK/NACK tests. Radiated or conducted RF execution requires the actual authorized 915 MHz arrangement.

## Action

- Restored `config/arq_test.toml`, its strict validator, generated artifacts, and both host register audits to 915 MHz. General-radio `config/radio_915.toml` has no diff from HEAD. TX power remains configured +2 dBm, SF7/BW125/CR4/5.
- Added two reverse ARQ radio-only build variants, reusing the original codec, sender, receiver, and NACK type 3/reason 2. Physical board pins and endpoint identities remain Gateway=1 and Tracker=2; direction reverses only in diagnostic builds.
- Added exact T01/T03 payloads HELLO_LORA_GW/HELLO_LORA_TR. T02/T04 send valid DATA containing REJECT_LORA; the existing application policy rejects it and constructs a matching NACK. Legacy HELLO_LORA remains supported.
- Extended the existing one-shot runner with `--diagnostic-test T01|T02|T03|T04`. It arms the receiving board first, sends once, and requires matching endpoints, payload, session, sequence, reason, TX_DONE, application decision, response reception and local event order. RF gates remain independent from programming.
- Physically verified reverse-role candidates at 915 MHz. The initial forward run then demonstrated STATUS overflow: an unsolicited RX_IRQ with a zero-length packet discard overlapped the 14-line STATUS block in the 16-slot ring. Its origin is unknown; it was not project DATA acceptance.
- Reproduced the overflow in the actual firmware adapter host test. Changed STATUS to emit one line only when the existing logger is empty, leaving radio servicing active. The ring remains 16 slots; the cursor costs one SRAM byte. Regression covers RX bursts before and during STATUS, complete STATUS_END, zero overflow, and continued RX.
- Rebuilt, reverified candidates, reprogrammed the changed forward images Tracker first, and repeated the same non-transmitting physical audit successfully. No unchanged image was blindly reflashed.
- Preserved GPS UART/power isolation, SD guard, HF bit correction, RadioLib 7.1.2 errata flag, absolute ACK deadline, sequence logging, zero-retry diagnostics and normal retry behavior.

## Result

- **345 host test methods passed**, 350 discovered. Five methods in one archived boot-repair class were skipped for the documented replacement-board layout. Seven newly added test methods cover direction/host control; the existing adapter test gained the hardware-derived STATUS regression.
- **10 distinct environments built successfully after the final firmware edit**, with zero AVR compiler warnings. Across both build passes: 20 successful environment build executions. Host RadioLib compilation retains its pre-existing upstream Clang floating-point warnings.
- **Two devices programmed and verified**, six changed-image write operations across reverse preparation, initial forward deployment and corrected forward deployment. All six write operations passed readback and preservation; the initial forward radio/status audit was incomplete and remains recorded as UNKNOWN.
- Final successful physical run: `artifacts/arq/20261114T145521030475Z-radio-only-bringup`, session 15. Both radios reached RX Continuous, then parked in Standby. Raw monitor logs were independently matched against report events. Zero final logger overflows/capture errors.
- Reverse-role PHY was physically verified before the STATUS correction. Updated reverse-role variants are built and host-tested, but the final installed pair is forward-role.
- **No SEND command was issued. No project DATA, ACK or NACK was transmitted.** T01–T04 remain NOT_RUN because an actual authorized 915 MHz operating arrangement was not supplied. No protocol timeout occurred; the failed audit had two capture deadlines.

| Test | DATA direction | Response | Physical verdict |
|---|---|---|---|
| T01 | Gateway → Tracker | Tracker ACK | NOT_RUN |
| T02 | Gateway → Tracker | Tracker NACK | NOT_RUN |
| T03 | Tracker → Gateway | Gateway ACK | NOT_RUN |
| T04 | Tracker → Gateway | Gateway NACK | NOT_RUN |

## Final physical status

```text
915_MHZ_SOURCE_CONFIGURATION: PASS
915_MHZ_BUILD: PASS
GATEWAY_MCU_IDENTITY: 42032240221023150129012600000000
TRACKER_MCU_IDENTITY: 42032240221092150158013400000000
GATEWAY_FLASH: PASS
TRACKER_FLASH: PASS
GATEWAY_IMAGE_SHA256: 0802e35ee3267575b651571a50e6bed3b42e1718a8d642c48d537e0195f1f939
TRACKER_IMAGE_SHA256: a9ea8fc7d8cacd595e57d76c69478ed7a8e248056fe5fc9dc7bcb50a15c64314
GATEWAY_REGVERSION: 0x12
TRACKER_REGVERSION: 0x12
GATEWAY_FRF_REGISTERS: E4 C0 00
TRACKER_FRF_REGISTERS: E4 C0 00
GATEWAY_FREQUENCY: 915000000 Hz (register-derived, nominal 32 MHz reference)
TRACKER_FREQUENCY: 915000000 Hz (register-derived, nominal 32 MHz reference)
GATEWAY_HF_BIT: 0
TRACKER_HF_BIT: 0
TRACKER_RX_MODE: RX Continuous 0x85 verified; final Standby 0x81
PHY_MATCH: PASS
RF_TRANSMISSION_AUTHORIZED: UNKNOWN — no actual 915 MHz authorization supplied
GATEWAY_TX_DONE: NOT_RUN
TRACKER_RX_DONE: NOT_RUN (project DATA)
TRACKER_DATA_ACCEPTED: NOT_RUN
TRACKER_ACK_TX_DONE: NOT_RUN
GATEWAY_ACK_ACCEPTED: NOT_RUN
TOTAL_DATA_TX: 0
TOTAL_DATA_RX: 0 (accepted project DATA)
TOTAL_ACK_TX: 0
TOTAL_ACK_ACCEPTED: 0
TOTAL_NACK_TX: 0
TOTAL_NACK_ACCEPTED: 0
TOTAL_TIMEOUTS: 0 ARQ; 2 capture deadlines in failed initial forward audit
UNEXPECTED_RESET: NOT_OBSERVED during captured windows; expected UPDI reset flag 0x20
CONFIRMED_SOFTWARE_DEFECTS: Diagnostic profile mismatch; STATUS burst overflow
ROOT_CAUSE_CLASSIFICATION: CONFIGURATION + OBSERVABILITY; historical RF/POR root cause UNKNOWN
NEXT_UNRESOLVED_BOUNDARY: Actual authorized 915 MHz RF operating arrangement
```

SF7/BW125/CR4/5, CRC enabled, explicit header, sync 0x12, normal IQ, preamble 8, PA_BOOST configured +2 dBm, DIO maps and IRQ mask passed on both physical radios. RegDetectOptimize was 0x43 in RX, preserving the installed library workaround. Actual RF carrier/power and crystal accuracy were not instrument-measured.

## Build and preservation

| Final installed image | Flash bytes | Static SRAM bytes | Authorized written pages |
|---|---:|---:|---|
| Gateway sender_arq_radio_only | 37498 | 5238 | [0, 37888) |
| Tracker receiver_arq_radio_only | 39038 | 5312 | [0, 39424) |

Target AVR128DA28, AVR-GCC 7.3.0, DxCore 1.6.2, RadioLib 7.1.2. Application bounds [0,130048). Reset vectors independently decoded as valid relaxed RJMP instructions into the application. A JMP-only initial verification assumption was corrected after AVR objdump confirmed RJMP; no firmware vector defect was found.

Final fuses both `0000f0ffffd2f80000ffffffffffffff`, lock `5cc5c55c`. BODCFG/CODESIZE/BOOTSIZE remain 0/0/0. Full EEPROM, lock, fuses, and flash outside each permitted page range matched before/after snapshots. Both previous 923 MHz installed images also independently matched the initial pre-write snapshots and remain archived rollback references.

Programming used the existing AVRDUDE 8.1 bounded page erase/write/verify procedure with -D, no chip erase or fuse/EEPROM writes. Responsible-operator safety attestation is preserved verbatim in authorization.json. Electrical measurements remain NOT_MEASURED. Physical SD occupancy remains independently unconfirmed; the existing GPIO guard allowed startup and was not bypassed.

At 32 MHz, FSTEP=61.03515625 Hz and FRF=14991360=0xE4C000. This follows Semtech SX1276 datasheet §4.1.4; a manufacturer-authored mirrored PDF and extracted text are archived. The official product document viewer did not expose the PDF to download tools. Reference: [Semtech manufacturer datasheet](https://s3.amazonaws.com/snapeda/datasheet/SX1276_Semtech.pdf).

DATA airtime for all four selected payloads is 61696 µs; ACK/NACK is 41216 µs. The existing response guard is 75000 µs against minimum ACK deadline 2000 ms. Actual RF turnaround remains NOT_MEASURED.

## Evidence

- `verification-result.json`: independent final readback, preservation, raw capture, PHY and final mode checks.
- `final-candidates-915.json`, `final-arq-manifest-915.json`, `final-firmware/`: final candidate provenance and archived images.
- `status-fix-host-final.log/json`, `test-results.json`: final full software result and precise skip accounting.
- `status-fix-build.log/json`: final build commands, sizes and warnings.
- `status-burst-red.log`, `status-burst-green.log`: demonstrated STATUS bug and correction.
- `frequency-red.log`, `frequency-green.log`, `directional-red.log`, `directional-green.log`, `host-directional-red.log`, `host-directional-green.log`: staged regression evidence.
- `prepared-rf-tests.json`, `airtime-915.json`: four prepared one-shot cases and budgets; prepared commands fail closed without RF flags.
- `rollback-references.json`, `reverse-preservation.json`, `first-forward-preservation.json`: prior image/readback and earlier stage evidence.
- Hardware raw runs: reverse PASS `artifacts/arq/20261114T143954009160Z-radio-only-bringup`; first forward UNKNOWN `artifacts/arq/20261114T144342998640Z-radio-only-bringup`; corrected forward PASS `artifacts/arq/20261114T145521030475Z-radio-only-bringup`.
- `status-fix-graph.log`: AST graph updated to 4213 nodes/7077 edges. Historical retained nodes are not current execution proof. Graph extraction reports a stub-header parser warning and unavailable PDF extra; raw source/builds and structured execution evidence remain authoritative.
- `final-port-owners.json`: both ports free; radios parked; no automatic normal-firmware restore.

Review was performed inline without subagents, as requested. No commits or unrelated cleanup. One early focused test selection encountered stale generated metadata; regeneration and the final full suite resolved it. Historical failures, the initial forward failure, and old hashes remain preserved.

## Remaining limits

RF T01–T04 require the actual authorized 915 MHz radiated, isolated conducted or shielded arrangement, including antenna/load, power and shutdown conditions. The historical POR electrical cause remains UNKNOWN. Repository-wide strict lint cleanup, soak testing, FOTA and RF transmission were not run.
