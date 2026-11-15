# Autonomous engineering verification — 2026-11-14

## A. Executive Verdict

**SOFTWARE_VERIFICATION_INCOMPLETE.** Functional host verification and all 15 application builds pass. Strict Python lint/type/format gates fail, so this report does not assert that all software release gates pass. Physical bring-up and RF remain blocked. No device programming, target power switching, reset, fuse write, UPDI transaction, or RF SEND was performed in this run.

Source: commit `f8092bc70eae4d99d197427708b74ef19c11be13`, branch `fix/receiver-rfm-rev1-pins`, with pre-existing dirty work preserved. [baseline.json](baseline.json) and [baseline.diff](baseline.diff) capture the starting state; current source hashes and artifacts are in [all-artifacts.json](all-artifacts.json). No commits, pushes, or subagents were used.

Critical blockers: missing measured electrical/backfeed safety evidence; missing RF laboratory and frequency/antenna/power authorization. Strict static analysis and target stack/timing validation are also unresolved release checks.

## B. Changes Implemented

| Files | Defect and root cause | Minimal correction | Regression evidence |
| --- | --- | --- | --- |
| `src/arq/sender.c`, `src/arq/main.cpp`; `tests/arq/core_test.c`, `tests/arq/adapter_test.cpp`, `tests/test_arq.py` | Receive runs before deadline polling. A matching ACK could mark a transaction DELIVERED at/after its absolute terminal deadline. | Apply the existing wrap-safe absolute deadline check inside control handling; fail without sequence/RTT advancement and classify the rejected control. Retry-deadline acceptance before polling remains unchanged. | [deadline-red.log](deadline-red.log) reproduced the fault in both core and real adapter; [deadline-green.log](deadline-green.log) passes. Tests cover deadline−1/deadline/deadline+1 and clock wrap. |
| `tools/arq_trial.py`, `tests/test_radio_bringup.py` | HELLO proof checked event presence, allowing duplicates and impossible event ordering to produce complete=true. | Require the expected causal event sequence independently for each board. Cross-board stream interleaving remains valid. | [evidence-order-red.log](evidence-order-red.log): seven false-positive cases reproduced. [protocol-green.log](protocol-green.log) and final discovery pass. |
| `lib/task/src/task.cpp`, `tests/task_restart_test.cpp`, `tests/test_mvp_roundtrip.py` | PT_RESTART expands to `return PT_WAITING` inside a void method. The previous host test stripped Werror and used fpermissive. | Use PT_INIT, the continuation initializer already used by the constructor; remove that compiler workaround. | [task-restart-red.log](task-restart-red.log), [task-restart-green.log](task-restart-green.log). Runtime asserts restart clears pause/wakeup state and resumes from the task entry. |
| `tests/test_live_rf_proof.py` | The fixture supplied only historical backup identities, so the current-hardware verifier correctly refused it. | Supply the current inventory and deliberately disagreeing historical identity. Preserve wrong-image/signature/serial rejection. | Failure in [baseline-host.log](baseline-host.log); [current-fixture-green.log](current-fixture-green.log) passes. |

Expanded existing core/adapter tests check every uint16 sequence, wrong controls, duplicate controls, reset/session isolation, wrap exhaustion, and accurate terminal logging. Added bounded mixed-valid/invalid parser fuzzing; no new framework or production dependency.

## C. Actual Test Results

[Machine-readable final results](host-tests.json), [full output](host-verification-final.log), [exact command/time/exit](host-verification-final.json):

- Discovered: **342 methods**.
- Executed: **337**; passed: **337**; failed/errors: **0**.
- Skipped: **one class containing five methods**. Archived BOOTSIZE=44 boot repair is inapplicable to the current replacement Receiver. The portable compiled boot-handoff tests still execute.
- Existing methods passing: 335; new methods passing: 2. Existing core and adapter methods also contain new C/C++ assertions; those assertions are not counted as extra unittest methods.
- ACK stress/property checks: all **65,536** sequence values; mismatched ACK fields and duplicate ACKs checked at each value.
- Parser fuzz: **50,000** mixed valid/invalid inputs, seed **0x4c4f5241**, under address/undefined-behavior sanitizers.
- Critical subset: **five successful repetitions**, no flakiness observed ([repeat-critical.log](repeat-critical.log)). This does not prove absence of all nondeterminism.

The original 141 checks were a focused subset. Initial full discovery executed 313 tests and failed with one fixture failure, eight environment errors, and two skips; those results remain in [baseline-host.log](baseline-host.log). Subsequent diagnostic failures, including temporary generated-file staleness and missing C++ headers, are retained rather than replaced by the final result.

Host prerequisites: locked uv Python 3.14.10 supplies pyserial. Missing g++/C++ headers were addressed with a task-local Clang C++ wrapper and extracted Fedora libstdc++ development headers, without installing system packages. The wrapper uses no-PIE linking to match the tests' GCC C objects; the unused-link-option diagnostic is disabled only for wrapper compile-only calls. [host-toolchain.json](host-toolchain.json) and [host-bin/g++](host-bin/g++) record the exact setup. This is **Clang validation, not a native G++ run**.

Strict checks remain **FAIL**: Ruff 4,860 findings across 57 files; mypy 2,171 errors in 52 files (58 checked); formatting reports 53 files needing changes. See [Ruff](strict-final-ruff.log), [mypy](strict-final-mypy.log), [format](strict-final-format.log). Most findings are missing annotations, style, and documentation; dynamic SCons `Import/env` names account for the undefined-name reports. Other findings have not all been adjudicated. No blanket suppression or repository-wide rewrite was applied. These are unresolved checks, not passing gates.

## D. Build Verification

[Toolchains](toolchains.log): PlatformIO 6.2.0; AVR-GCC 7.3.0; host Clang 23.1.4 / GCC C 16.2.1; uv 0.13.7. MCU: AVR128DA28. Fifteen concrete application environments were cleaned then built successfully ([clean](clean-final-all.log), [build](build-final-all.log)); debug/release are inherited configuration templates, not standalone role targets.

Compiler warnings: **0** in the 15-target build. DxCore emits its existing informational PROGMEM_MAPPED notice. All images and page-rounded writes fit the configured application bounds; static SRAM remains below 16,384 bytes. Upload mapping and flash preservation flags pass inspection. These are build/host checks, not physical readback.

| Environment | Flash bytes | Static SRAM bytes | HEX SHA-256 |
| --- | ---: | ---: | --- |
| sender | 36114 | 6710 | `27c3657ec3d0583421eb9032952e429d5e8351cca75cc90c93301be313e1401f` |
| receiver | 33152 | 2258 | `ea5829bc9313731f52ca89d7e801354479390927b6bfd10cdd5c6e2048b654cf` |
| sender_hello | 40908 | 7374 | `c51d7dc5b951632c65cc915640e4011dd1ad775bc57d4dbadada21eb7e5833ca` |
| sender_hello_spi | 39350 | 7259 | `1aa6ddf3a7e5fa146ff99388a0ac917a5b1ed888b6385745296c3572038daeee` |
| receiver_spi | 30156 | 1836 | `3ced0b24ac325d2b5bb761ba6e2bbfc448abc3412fe842b580ce2cbc273a8d6d` |
| sender_mvp | 31016 | 1360 | `10c5fae78e93155cca279939102d16e275c44c43312a5637d7aa56363b960431` |
| receiver_mvp | 31478 | 1390 | `d002dca1607eaa83907dd423c17025ee0e320b30b4075f9eb7a01da0ecb58c54` |
| sender_arq | 37014 | 5225 | `c2eed40c5d6c11116b5ac7d5c959a08ceba0aca1eeab8fe2c2617265e3864215` |
| receiver_arq | 36120 | 5221 | `ce8b924afe5c6a700eea1b6067a65c17b3340602997b08718aa82e5698313f01` |
| sender_arq_test | 37014 | 5225 | `25327b7c62a4d50f414ecac4768b16183e203d0d2e0cbbb38b260df0fc0bb983` |
| receiver_arq_test | 38098 | 5255 | `10b53e0d904e54b135ab61fcb0a04f289cf7329684eb301454434e65e325031b` |
| sender_arq_radio_only | 36958 | 5237 | `cb52c044eddc23fa0794da6afc8cc5403fa13c36ec602f815d57d61ec6ff1c61` |
| receiver_arq_radio_only | 38388 | 5285 | `9a36560e767ad6ed9d0717864064e0ba22b132e23e6f7173dbfe31eae7f2d82e` |
| sender_reverse_raw | 31868 | 4666 | `267746a73e193e11c6532e14bf13db39710a51e6c935efd73050dcbe6677dedf` |
| receiver_reverse_raw | 30738 | 4485 | `a131e7595f003b017f1136c01e72bf1d9142285023237cda267e857b072adaa7` |

The table records **current** candidates in [current-candidates.json](current-candidates.json). That manifest identifies the correct saved artifact directory for every image. HEX and ELF identities are verified for all ARQ and reverse-raw targets. Normal `sender`, `sender_mvp`, and `receiver_mvp` omit the generated ID from their binaries; their build headers/hashes/source manifests provide provenance, but runtime build identity is not established for these three targets.

A repeated clean radio-only build succeeded. Raw HEX/ELF hashes differ because RadioLib `src/BuildOpt.h:548` embeds __DATE__/__TIME__. For both radio-only images, normalized flash differs **only inside the single Compiled timestamp**, and generated build IDs remain identical ([repeatability.json](repeatability.json)). Raw byte reproducibility is therefore not claimed. The earlier ARQ snapshot predates the Task source change and is historical, not a same-input reproducibility test.

ELF sections and ARQ symbol lists are saved under `firmware/`. A linker map was not generated. LTO leaves the .su files empty, so worst-case target stack depth and stack high-water remain **NOT_MEASURED**. Static SRAM headroom is not a stack proof. Device latency/energy/throughput have not been measured; no target performance threshold was invented.

## E. ACK Validation

Execution map: explicit ARM establishes a uint32 session → SEND copies one payload into the single pending frame and assigns the current uint16 sequence → encoder emits a versioned 12-byte header plus payload → adapter starts TX → TxDone/cleanup/RX arming establishes WAITING_ACK → decoder validates lengths/type/reason → sender matches endpoint IDs/session/sequence/state → ACK sets DELIVERED and advances next sequence → logger reports `sender.frame.sequence` from the completed frame.

There is **one pending transaction, no multi-message queue**. Requests while active are refused. Retries retain the immutable frame identity. Normal firmware retains four retries (five attempts); the radio-only HELLO diagnostic permits one attempt. At sequence wrap the sender is marked used_up and requires a fresh session before reusing zero. Reset clears armed/pending state; the host must establish a fresh session, with no persistent resume or hostile-replay guarantee claimed.

The historical q=1 issue was a **host evidence expectation defect**: firmware already logged transmitted frame sequence zero, while its next counter had advanced to one. No physical evidence established that firmware actually emitted DELIVERED q=1. Current adapter assertions verify logs/state for 0, 1, 32768 and 65535, including no duplicate delivery event. Do not describe the old fixture as a measured wire/log failure.

Wrong endpoints/session/sequence/type/length/reason, malformed/truncated frames, early ACK, duplicate ACK, stale prior transaction/session, missing ACK, retry ACK, retry exhaustion, absolute expiration, clock wrap, and reset are covered across the core, adapter and discovery suite. Radio CRC rejection is exercised through the adapter. A matching ACK at a retry deadline may be processed before retry polling by design; the absolute lifetime and terminal failed state cannot be revived. No cryptographic ACK authentication is implemented by this protocol.

## F. Physical Verification

[Fresh OS enumeration](usb-discovery.log): CP2102 adapters at USB paths 1 → ttyUSB1 and 4 → ttyUSB0. USB serial numbers are duplicated, so stable physical paths remain essential. Current MCU identity/fuses were **not reread in this run**. The earlier safe UPDI captures are historical references only.

`ELECTRICAL_MEASUREMENTS=NOT_MEASURED`. Board assembly, wiring and installed antennas remain operator-reported handoff facts. Backfeed safety, external voltage/current/transients and SD socket occupancy remain unverified. Preserve the SD guard and GPS isolation. No measurement instruments were supplied.

H2 safety: **BLOCKED**. Programming, readback, physical radio initialization/register verification, fuse/EEPROM/lock/outside-page preservation after a write and HIL: **BLOCKED / NOT_TESTED**. Actual bring-up CLI invocation without unsupported attestations refused with exit 2 before hardware access ([bringup-safety-gate.log](bringup-safety-gate.log)). See [physical-gates.json](physical-gates.json).

## G. RF Verification

Laboratory authorization, approved frequency/channel, permitted radio power and antenna/load arrangement: **UNKNOWN / NOT_SUPPLIED**. Both installed antennas were reported by the operator; this does not approve an operating arrangement. RF CLI refusal is captured in [rf-safety-gate.log](rf-safety-gate.log).

`RF_TRANSMISSION=BLOCKED`. Physical TX, RX, Tracker ACK TxDone, Gateway ACK acceptance and HELLO_LORA end-to-end: **NOT_TESTED**. No SEND issued. Mock/in-process exchanges in host tests are not RF evidence. Firmware candidate settings remain 923 MHz, SF7/BW125/CR4/5, +2 dBm PA_BOOST; those settings are configuration facts, not regulatory authorization.

## H. Evidence

- [Baseline](baseline.json), [starting patch](baseline.diff), [final test report](host-tests.json), [final output](host-verification-final.log).
- [All-target build output](build-final-all.log), [source/artifact manifest](all-artifacts.json), [current candidates](current-candidates.json), [repeatability](repeatability.json), saved firmware and size/symbol reports.
- [Physical gates](physical-gates.json), [strict lint](strict-final-ruff.log), [strict typing](strict-final-mypy.log).
- [Run journal](EXECUTION_JOURNAL.md); prior history stays in `../20261114T044136Z-radio-only/EXECUTION_JOURNAL.md`.
- [Graph update](graph-update.log), [graph schema/provenance](graph-evidence.json). AST graph update succeeded; 1,527 nodes from 74 existing files were retained after a corpus/filter warning. Historical source nodes remain historical. Graph structure is not itself a PASS receipt; current claims point to this run's executed checks and manifests.

Each check has a neighboring JSON record with command, UTC start, duration, exit code and log path. [evidence-manifest.json](evidence-manifest.json) records provenance and final classifications. Diagnostic failures are retained.

## I. Remaining Risks

1. **Unverified physical safety**: no measured backfeed/voltage/current/transient evidence; programming cannot proceed.
2. **Unverified RF operating conditions and delivery**: no authorized physical DATA/ACK result exists.
3. **Known failing strict static gates**: unresolved typing/lint/format findings prevent a blanket software-release claim.
4. **Target stack and runtime timing unmeasured**; static memory and host sanitizer coverage do not prove target timing/power/reset behavior.
5. Raw builds embed a timestamp; three non-ARQ images lack an embedded generated ID. These limits are recorded explicitly.
6. Historical graph nodes remain retained after the filter warning; their presence supplies no fresh validation.

## J. Final Decision

**Partially verified, not RELEASE_READY.** Current host functional behavior, ACK regressions, bounded parser robustness, all application builds, candidate bounds and hashes have executed evidence. Strict static analysis remains failing; electrical/HIL/RF prerequisites remain missing. No physical success or completion of the HELLO_LORA objective is claimed. Continue physical work only after the missing operation-specific evidence/authorization exists; preserve the current diagnostic candidates and historical evidence meanwhile.
