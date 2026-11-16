# Execution journal

## E00 — Baseline and source references

Hypothesis: existing ARQ already isolates some peripheral activity and the HF candidate may be present.

Hardware: two connected CP2102 adapters at stable paths port 1/port 4. No scope, logic analyzer or independent RF instrument.

Commands: Git status/HEAD, Graphify query, CodeGraph explore (no usable index), scoped source reads, three schematic PDF extractions, manufacturer and exact-version source browsing. See [baseline](baseline.json), [raw initial diff](raw/baseline.diff), [references](references/SOURCE_LOG.md).

Observed: HF candidate already in dirty worktree. Generated Tracker setup already commands GPS/SD off. GPS UART is PF0/PF1; unbuffered shared SD bus requires an empty socket if power is removed. Preserved 4,596 existing source/evidence files in an initial hash ledger. No legacy repository file edited.

Decision: implement explicit diagnostic startup and tests without adding unused sensor/task infrastructure.

## E01 — TDD and build

Hypothesis: startup can safely release GPS interfaces and refuse use of an unpowered SD card while retaining the existing radio/protocol path.

Commands and raw results: [test report](RADIO_ONLY_TEST_RESULTS.md).

Observed: RED for missing USART shutdown; GREEN after minimal helper. Further RED when the actual generated board setup removed SD-detect pull-up; GREEN after conditional generator correction. 83 focused tests and 8 firmware builds passed. Installed RadioLib HAL test passed 12 modeled candidate TX/RX cycles. Full discovery retained 7 missing-g++ errors and 2 skips; not reported as green.

Eliminated within software model: accidental Tracker gate policy on Gateway, SPI startup with a detected SD card, mode-field clobbering, loss of HF selection during modeled transitions. Physical behavior remains unverified.

## E02 — Live preserved-firmware STATUS and register observation

Hypothesis: preserved firmware still supports reliable non-RF diagnostics, allowing direct observation of peripheral GPIO and current radio configuration.

Command:

```bash
uv run python docs/rca/20261114T044136Z-radio-only/experiments/non_rf_status.py
```

Hardware: Tracker serial `42032240221092150158013400000000`, Gateway serial `42032240221023150129012600000000`; both MCU signatures `1e970a`. Stable USB location and owner check precede exclusive open. These are MCU identities, not the adapters' duplicated USB serial `0001`.

Observed: Tracker 20/20 STATUS; Gateway 1/1; no first failure; both thread pairs closed. Two BREAKs per acquisition; zero CPU resets/resumes requested. GPS/SD commands already high, GPS UART released, PA7 low. Both radios remain baseline standby 0x89 with matching PHY. Raw data: [Tracker](raw/receiver/), [Gateway](raw/gateway/), [summary](live-summary.json).

Eliminated in this window: persistent wrong-target selection, current STATUS silence and parser failure for the returned blocks. RF, TX-load stability and historical reset mechanism remain unresolved.

## E03 — RF/programming decision

No RF or programming command executed. The latest repository RF-path hold remains unsatisfied; source wiring and empty SD socket cannot be established by USB/STATUS. Candidate verification is limited to builds and modeled-driver tests. The existing baseline already commands GPS/SD off, so a peripheral-load reduction cannot be credited without measurements.

Next experiment: one bounded HF-only H01 comparison after physical preconditions, preserving image identity and separating it from diagnostic peripheral policy. Full requirements and unresolved boundaries: [final report](RADIO_ONLY_FINAL_REPORT.md).

## E04 — Integrity

Five historical bundle manifests: 328 referenced file records, zero missing/mismatches. Final source/evidence comparison and new-run SHA-256 verification are recorded in [preservation](preservation.json), [manifest](manifest.json) and [hash ledger](sha256.json). Intentional source/generator updates are not described as zero changed production source files.


## Verified bring-up implementation — 2026-11-14

Operator reports Hardware Team assembly handoff to Firmware Team, completed power/common-ground/UPDI connections, and installed antennas on both boards. This is operator-reported assembly readiness. CP2102 backfeed and Tracker SD socket occupancy remain UNKNOWN. External voltage, current, and transient measurements are NOT_MEASURED; no meter, oscilloscope, or current probe is available.

Fresh read-only UPDI checks at 13:01 UTC matched both configured AVR128DA28 serials and signature `1e970a`. Both boards returned BODCFG/CODESIZE/BOOTSIZE = 0/0/0. Stable USB paths resolved and were unowned before access. Raw transactions and readbacks are in [verified-bringup/raw](verified-bringup/raw/). No CPU reset, NVM write, or RF transmission was requested by these checks. Saved GPIOR0 remains historical reset evidence, not a POR timing measurement.

Implemented current-inventory identity checks, LF-bank refusal, extended 24-register ARQ snapshots, `--radio-only-bringup`, and separately gated `--hello-lora`. Both modes use radio-only candidates and park them using X without normal-firmware reflashing. Candidates must match the current generated source/build identity and embedded image identity before programming. Programming still uses bounded page erase/readback and preservation checks. The SD guard and GPS isolation remain enabled; a guard refusal is retained in raw events and the bring-up report.

Radio-only builds now use exactly `HELLO_LORA` and zero retries. Normal firmware retains its configured payload/retries. The existing reader-free radio-only caller uses the same diagnostic payload. The new exchange validator requires one physical DATA attempt, sequence zero, matching DATA/ACK frames and session, Tracker acceptance, Tracker ACK TX_DONE, and Gateway DELIVERED. Missing checkpoints remain UNKNOWN. DATA airtime is 56.576 ms; ACK airtime is 41.216 ms; the 75 ms response guard plus ACK fits the 2 s minimum ACK deadline. These are calculations, not physical timing measurements.

Both affected radio-only targets built successfully. [candidate-images.json](verified-bringup/candidate-images.json) records replacement HEX/ELF hashes, build IDs, reset targets, bounds, and rounded write ranges: Tracker [0, 38400), Gateway [0, 36864), within [0, 130048). [builds.txt](verified-bringup/builds.txt) retains build output. [host-tests.txt](verified-bringup/host-tests.txt): 141 tests ran, OK with one skip. The skipped class is the archived BOOTSIZE=44 boot repair, which does not apply to the replacement Receiver; it was not counted as a passing check. Regression runs first demonstrated current-Tracker refusal, LF-bank acceptance, old retry/payload behavior, and stale-candidate acceptance, then passed after fixes.

Programming was not run: the existing power gate requires safe supply/backfeed conditions, which the current handoff does not establish. Physical candidate readback, running build identity, radio register verification, and post-program preservation comparisons therefore remain UNKNOWN. RF authorization and permitted antenna/power conditions remain pending independently. No SEND was issued. No soak receipt is required by either new mode.

Graphify AST update completed and retained 1527 nodes from 74 existing files after a corpus/filter warning; see [graph-update.txt](verified-bringup/graph-update.txt). No API extraction was used. Pre-existing workspace changes were preserved; no commit or push was made.


## Bring-up resume — 2026-11-14 13:16 UTC

Source review found that `sequence()` in the Gateway firmware logs `sender.frame.sequence`, so DELIVERED retains transmitted sequence zero even after the sender advances its internal next sequence. The host exchange validator incorrectly required DELIVERED q=1. A corrected physical-event fixture failed against the old validator, while an adapter assertion confirmed the real firmware logs DELIVERED q=0. The validator now requires q=0; a q=1 terminal is rejected. This is a host validation fix; firmware binaries are unchanged.

[Fresh host verification](verified-bringup/resume-host-tests.txt): 141 tests ran successfully with one skipped archived boot-repair class. Both candidate HEX/ELF hashes, embedded/current generated identities, upload preservation flags, mapped paths, application bounds and rounded page ends were rechecked successfully against the existing candidate ledger. Unchanged images were reused without another build.

[Fresh read-only UPDI evidence](verified-bringup/20261114T131630462243Z-read-only/raw/) again matched both configured serials and signature 1e970a, with BODCFG/CODESIZE/BOOTSIZE all zero. USB paths and ownership were checked before opening ports. No NVM write, CPU reset or RF TX was requested.

Actual invocation of each new mode with verified mapping but without the unsupported power attestation refused at the CLI before hardware access: [bring-up gate](verified-bringup/resume-radio-only-bringup-gate.txt), [exchange gate](verified-bringup/resume-hello-lora-gate.txt). Operator-reported assembly handoff does not establish CP2102 backfeed safety. Programming/readback and physical radio-register verification remain pending that prerequisite. SD occupancy remains UNKNOWN, the guard remains enabled, and voltage/current/transient measurements remain NOT_MEASURED. RF release and permitted antenna/power conditions remain separately pending. No SEND was issued and no normal image was reflashed.

[Graphify update](verified-bringup/resume-graph-update.txt) refreshes the changed AST entries. No subagents were used for this resume. No commit or push was made.
