# Gateway-to-Receiver SF7 Hello World

## Current result — Receiver installed, normal startup unresolved

The owner's `OPERATOR_SAFETY_ATTESTATION` was accepted as the no-meter
programming assessment without inventing electrical measurements. The exact
approved Receiver installation **physically passed** in
[152319Z](artifacts/rf-proof/20261106T152319Z/receiver-boot-receipt.json):
RF-disabled APPCODE first, independent readback, BOOT page 0 last, and full
preservation checks. No fuse, EEPROM or lock write or chip erase occurred.
The Gateway has not been programmed.

The Receiver has not produced the new Build ID. Two confirmation cycles used
valid `RSTFR=0x20` baselines and observed fresh `0x02` BORF after release;
the separate zero-baseline `0x10` test is DxCore's intentional software reset.
See [the actual execution report](artifacts/rf-proof/20261106T154458Z/MISSION_RESULT.md).
One bounded read-only UPDI recovery at 57600 baud succeeded and freshly
confirmed BODCFG `0x54`. The final control snapshot shows RESET_REQ `0x00`,
SYS_STATUS `0xA2` and OCD_STATUS `0x00`. Normal startup and the physical cause
remain unresolved; SPI and RF success are not claimed. See
[the recovery/RCA evidence](artifacts/rf-proof/20261106T155949Z/UPDI_RECOVERY.md).

The affected Python suite passed **130 tests** after the attestation changes
([log](artifacts/rf-proof/20261106T153656Z/python-regression.stderr.log)).
Unchanged firmware/C++ tests were not repeated. Earlier status sections below
are retained as history and are superseded by this update where they differ.

## No-meter read-only hardware verified; Receiver write wiring unconfirmed

The proof runner now supports `--no-meter-mode`. It removes external instrument
and measured-voltage prerequisites for powered read-only target diagnostics.
Writes retain power-source/adapter/ground/UPDI observations, exact authorization,
fresh MCU serial checks, bounded page operations and preservation comparisons.
RF module and antenna suitability checks remain independent. Unknown voltages
remain null; this mode does not assert `power_verified`.

Actual live identification passed on both boards in
[20261106T145856Z](artifacts/rf-proof/20261106T145856Z/target-identification.log).
[Complete live memory reads](artifacts/rf-proof/20261106T145941Z/no-meter-target-readback.json)
confirmed both unique serials, fuses and lock state; both complete Flash images
equal their original backups byte for byte. The new boot handoff is not installed.
The Python suite now passes 128 tests, including no-meter rejection cases;
[logs](artifacts/rf-proof/20261106T150533Z/python-regression.stderr.log).
These changes do not alter firmware, generated configuration or existing builds.

A compiled 48-byte handoff and exact one-page BOOT overwrite/recovery package
are ready in [the specific approval report](artifacts/rf-proof/20261106T141150Z/APPROVAL.md).
It programs RF-disabled APPCODE pages 44–103 first, verifies them, then modifies
only BOOT page 0. Fourteen focused boot/package/programming tests and the 43
affected proof-runner tests pass. Installed AVRDUDE 8.1 dryrun verifies both
staged programming and restoration against complete Flash images. The guarded
writer now explicitly page-erases its bounded images instead of assuming -D
does so automatically. The existing application binaries and SSOT are unchanged.

The operator explicitly approved the exact Receiver-only application-first,
BOOT-page-0-last package and reviewed recovery procedure. Gateway programming
is excluded. The [approval record](artifacts/rf-proof/20261106T142617Z/operator-authorization.json)
preserves that scope; the approval package itself remains unchanged.

The operator reports both boards powered and connected. The
[physical-preflight record](artifacts/engineering-loop/physical-preflight.json)
now cites fresh live UPDI identity and full-memory reads as well as prior evidence.
The operator explicitly reports actual supply source, CP2102 VCC/backfeed,
physical ground/header inspection and unchanged safe wiring unconfirmed.
The [no-meter installer attempt](artifacts/rf-proof/20261106T150102Z/receiver-boot-install.log)
therefore stopped before any write. The remaining
[visual inspection checklist](artifacts/engineering-loop/PHYSICAL_PREFLIGHT_CHECKLIST.md)
requires no meter. No repeat Receiver approval is needed.

[Fresh non-destructive verification](artifacts/rf-proof/20261106T142617Z/approved-mission-verification.json)
checked all 13 backup hashes, the unchanged approved package, generated
configuration, effective Flash boundaries and all five existing image hashes.
No application rebuild or unrelated host-suite rerun was needed. The user-reported
`F1 START SEQUENCE` and `RED 1 ON` markers occur in the original Receiver backup
at 0x03A0 and 0x03BE; they support old-program runtime, not the new handoff.
Those earlier static checks opened no serial port. The later live readbacks
opened UPDI but performed no Flash write. Physical
boot repair, SPI and DATA/ACK remain unexecuted. On-target recovery has not been
demonstrated; simulator verification is not physical proof.

## Verified software result

The diagnostic configuration is maintained in [config/lora_system.json](config/lora_system.json).
Both boards consume generated pin definitions, SPI1 routing, radio/protocol constants,
retry limits and timeouts. Generated PlatformIO configuration owns the target-specific
Flash starts and expected fuses. Fuse expectations are compared with live reads;
they are never written by this workflow.

Production Gateway I2C configuration remains a separate mode. Diagnostic SF is
restricted to 7. Candidate settings are 923 MHz, 10 dBm, BW125, CR4/5, sync 0x12,
preamble 8, CRC enabled, explicit header, normal IQ. Physical radio and antenna
inventory remains unknown.

| Check | Actual result | Evidence |
|---|---|---|
| Python suite | 128 tests PASS after no-meter integration | [regression log](artifacts/rf-proof/20261106T150533Z/python-regression.stderr.log) |
| C++ protocol | 130 checks PASS | Same host evidence directory |
| C++ radio wrapper | 77 checks PASS | Same host evidence directory |
| Role logging | 10 checks PASS | Same host evidence directory |
| RF-disabled send protection | PASS; send denied even after successful stub initialization | diagnostic-protection-tests log |
| Five clean builds | PASS; all starts, ends and reset targets validated | [firmware measurements](artifacts/rf-proof/20261106T132834Z/firmware-measurements.json) |
| Generated artifacts | Validator and generator --check PASS | [manifest](generated/lora_manifest.json) |
| Saved Receiver boot | NO_APPLICATION_HANDOFF | [reachable boot audit](artifacts/rf-proof/20261106T132129Z/receiver-boot-audit.json) |
| Physical SPI/upload/DATA/ACK | NOT RUN; guarded stage blocked before serial open | [SPI stage log](artifacts/rf-proof/20261106T133004Z/radio-spi-smoke.log) |

The host tests deliberately contain synthetic logs and radio stubs. They are not
physical evidence. A pure parsed log is classified as structural validation;
physical success is emitted only by the live runner after its readback and
capture path completes.

## Single-packet behavior and identities

The Receiver first reports WAIT_SESSION. The runner sends R followed by four
uppercase hexadecimal session digits. After SESSION_READY and RX_READY, it
opens the Gateway monitor, verifies identity and WAIT_START, then sends S with
the same four digits. Session IDs are reserved in the evidence hierarchy and
are not reused while those records are retained.

The Gateway allows only sequence 1, retries within the SSOT limit, and enters a
terminal state after a matching ACK. It then stops its service loop and sleeps,
without falling through to the production report/ACK handler. Duplicate S and C cannot restart it.
The generic multi-message state machine remains available outside standalone
single-packet mode. The physical acceptance check is deliberately stricter:
it requires one clean DATA/ACK attempt and rejects duplicate success events.

Diagnostic protocol version 2 adds NACK type 0x09 to the existing four-byte
radio header and two-byte response framing. A NACK is returned only for an
addressed sequence-1 DATA frame with the armed session and invalid payload.
CRC/read failures, truncated headers and unrelated sessions are ignored.
A correlated NACK triggers only a bounded retry of sequence 1. Successful
acceptance still requires ACK type 0x03, matching addresses/session/sequence,
and the exact 11 bytes 68 65 6C 6C 6F 20 77 6F 72 6C 64.

Each environment has a deterministic runtime Build ID derived from source,
configuration, role and mode. Final ELF/HEX SHA-256 values stay on the host;
they are not embedded as self-references. Upload receipts require fresh
signature, hardware serial-number and Flash readback checks against the
current HEX and embedded Build ID. The RF stage requires that receipt and
performs another fresh readback before opening monitors. Its event journal
checks both configuration fingerprints, protocol versions, radio startup,
session, readiness, command order, payload and DATA/ACK completion. No C is sent.

These checks correlate an engineering test session; they are not cryptographic
authentication against someone able to alter local evidence or spoof the radio.

## Receiver boot incompatibility

The saved Receiver image SHA-256 is
a142fba14979cbc184d97c62cbfc8da75da01759b4cf6838f5b63aae36d4c943.
Its reset vector at 0x0000 branches to 0x00A4. Conservative traversal reaches
334 instructions, finds no unresolved indirect transfer, and finds no transfer
to APPCODE at 0x5800. Branch-like bytes elsewhere in the backup do not establish
a boot handoff.

The new Receiver ELF has vectors at 0x5800 and reset target 0x58A6. Its .init3
startup writes zero to CPUINT.CTRLA at 0x58D0, before constructors. This selects
the APPCODE vectors, consistent with
[Microchip's interrupt placement guidance](https://onlinedocs.microchip.com/oxy/GUID-CBA6F7C8-69DB-44BF-ACE3-6949CC30E98A-en-US-5/GUID-3B992030-F430-4DC1-95B4-24561BAF9A01.html).
A valid new reset vector does not make the saved boot image launch it.

Programming is blocked until a reviewed, target-specific boot handoff and
recovery path exists. No fuse modification, boot replacement, chip erase or
forced program-counter workaround was performed. The upload configuration
retains -D and rejects erase/fuse-write options.

## Remaining physical prerequisites

The existing physical-preflight measurement record is absent. Actual power,
ground, UPDI wiring and CP2102 backfeed conditions therefore remain
unestablished. Radio/antenna path and RF suitability evidence is also absent.
The guarded SPI command was run without asserting unsupported flags and
stopped before opening serial ports.

The supported validation commands are:

- uv run python tools/config/validate_lora_ssot.py config/lora_system.json
- uv run python tools/config/generate_lora_config.py
- uv run python tools/config/generate_lora_config.py --check
- uv run python tools/rf_proof.py --stage host-tests
- uv run python tools/rf_proof.py --stage builds
- uv run python tools/rf_proof.py --stage boot-analysis

After the physical and boot prerequisites are independently resolved, use the
existing guarded radio-spi-smoke stage before RF-enabled upload. The RF stage
uses --stage rf-test --single-packet and requires --upload-evidence pointing
to the physical-upload.json produced by a verified upload. Verification and
authorization options must reflect actual evidence.

Physical acceptance remains NOT RUN: no DATA reception or matching ACK was
observed. No RF packet, continuation command or 20-packet campaign was run.
