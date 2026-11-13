# UPDI-only Hello World MVP — STAR report

Date: 2026-11-13. **Physical RF result: PASS.**

## Situation

The archived Receiver used BOOTSIZE `0x2c` and application origin `0x5800`.
Fresh read-only UPDI checks instead found a replacement Receiver with serial
`42032240221092150158013400000000` and BOOTSIZE `0x00`. The original identity
guard rejected it before programming. The operator confirmed this replacement,
USB port 1 = Receiver, USB port 4 = original Sender, and suitable 915 MHz modules
and connected antenna paths.

The latest available schematic was inspected as both extracted text and a rendered
sheet: `../iwing-tracker/device-lora/pcb/2025-02-16/Schematic_LoRa-Tracker-RFM_2025-02-16.pdf`,
revision 1.0. The operator confirmed it covers the replacement. Its mapping agrees
with the archived Tracker design: PA7 active-low radio power, PD0 NSS, PD1 reset,
PD3 DIO0, PD2 DIO1, PC0–PC2 SPI1, PC3 SD CS. GPS/SD power controls are PD5/PD6.

Current identities and exact expected fuse bytes are recorded in
[current_hardware.json](../config/current_hardware.json). Historical backups remain intact.

## Task

Transmit exactly the eleven bytes `Hello World`, hexadecimal
`48 65 6C 6C 6F 20 57 6F 72 6C 64`, without application headers or a null terminator.
Use 915 MHz, 2 dBm PA_BOOST, BW125, SF7, CR4/5, sync `0x12`, preamble 8,
explicit LoRa header, CRC enabled, normal IQ, and UPDI-only diagnostics.

## Action

- Added isolated `receiver_mvp` / `sender_mvp` environments and the shared
  [raw entrypoint](../src/mvp/main.cpp). Existing ACK/NACK targets remain available.
  Their shared profile remains 10 dBm with lowercase protocol payload; that shared
  manifest describes the existing protocol, **not the raw MVP profile**. The MVP's
  actual settings are recorded in its physical logs and run metadata.
- Updated the Receiver application origin to `0x0000` to match its existing
  BOOTSIZE of zero. No BOOTSIZE, BOD, oscillator, other fuse, EEPROM, or lock writes
  were made. The Sender configuration remains unchanged.
- Selected SPI1 before SPI initialization; used Mode 0, MSB first, 1 MHz. Kept
  reset high impedance until radio power stabilized and SD CS inactive. Reset and
  probed the radio with bounded retries before RadioLib initialization.
- Used binary RadioLib APIs, hardware IRQ polling without DIO interrupt handlers,
  a bounded 32-byte receive buffer, exact length/content and integrity checks,
  RX restart checks, a three-second TX timeout, and `X` to stop further attempts.
- Retained startup stages in RAM for attachment. DxCore saves RSTFR in GPR0 before
  clearing it; firmware copies that value. Logging permits up to 100 ms per byte
  and three seconds per record, so detached/stalled logging cannot wait forever.
- Programmed Receiver before Sender with explicit 512-byte page erasure, AVRDUDE
  verification, fresh serial/fuse checks, independent full-memory readback, and
  comparisons against the fresh baseline. The final written ranges were
  Receiver `[0x0000, 0x7c00)` and Sender `[0x0000, 0x7a00)`.
- Captured Receiver-ready evidence before Sender programming and again before
  starting the Sender monitor. Separate UPDIterm captures used `-l` at 38400 baud.

An initial monitor was started before independent readback completed, causing port
contention. It was stopped; independent readback was repeated successfully before
continuing. Initial 2 ms and then 20 ms byte waits also produced truncated logs.
Both latency limits were reproduced with failing host checks, corrected, rebuilt,
and physically retested. These failed captures are retained as attempt-1 evidence.

## Result

| Observation | Actual result |
|---|---|
| `pio run -e receiver_mvp` | PASS |
| `pio run -e sender_mvp` | PASS |
| Existing `sender_hello` and `receiver` builds | PASS |
| Final Receiver programming + independent readback | PASS |
| Final Sender programming + independent readback | PASS |
| Signature, MCU serial, fuses, lock, EEPROM, Flash outside written pages | Preserved against fresh baseline, both boards |
| Receiver RegVersion / Sender RegVersion | `0x12` / `0x12`, first probe on each |
| Receiver startup | All eight stages successful, including `RX_READY rc=0` |
| Sender startup | All applicable stages successful; `RADIO_INIT rc=0` |
| Reset flags in final startup logs | Both `0x20` = UPDI reset; BORF bit absent |
| Complete matching receptions captured | **3** |
| Hardware lengths / readData status / IRQ flags | `11` / `0` / `80` (`0x50`: RxDone + ValidHeader), all three |
| RX restart status | `0`, all three |
| Final Receiver counters | RX `17`, matching `17`, CRC errors `0` |
| Sender final attempt counter | `15`; stopped with `X` |
| Complete TX start/TxDone pairs in final log | `2`, attempts `14` and `15`; cleanup `0` |
| RSSI for the three captured packets | `-107.00`, `-107.00`, `-106.00` dBm |
| SNR for the three captured packets | `9.00`, `8.75`, `9.00` dB |
| Negative-control interval after STOP + 3.5 s grace | **15.000374 s**, zero new matching receptions and zero new TX starts |
| Final state | Sender stopped; Receiver listening; monitors closed |

A subsequent monitor attachment without reset still reported RX `17`, matching
`17`, CRC errors `0`, and retained `RX_READY` startup status. This independently
checks that packet counters did not advance during the negative control.

RX and TX cumulative counters are local to each MCU's startup. The Receiver also
heard packets around programmer-triggered Sender restarts and before monitor
attachment; the cumulative totals are not a one-to-one capture correlation.
The three complete final receive records provide the physical payload evidence.
TX completion alone was not treated as delivery.

### Evidence

All evidence is in [artifacts/rf-proof/20261113T062148Z](../artifacts/rf-proof/20261113T062148Z):

- [Receiver UPDIterm log](../artifacts/rf-proof/20261113T062148Z/receiver-final.upditerm.log)
  and [Sender UPDIterm log](../artifacts/rf-proof/20261113T062148Z/sender-final.upditerm.log).
- [Physical summary](../artifacts/rf-proof/20261113T062148Z/raw-mvp-physical-summary.json),
  [timestamped event journal](../artifacts/rf-proof/20261113T062148Z/raw-mvp-events.jsonl),
  and [run metadata](../artifacts/rf-proof/20261113T062148Z/raw-mvp-run-metadata.json).
- [Preservation results and image hashes](../artifacts/rf-proof/20261113T062148Z/final-preservation.json),
  baseline/final raw memory readbacks, final ELF/HEX images, and exact programming commands.
- Build logs, full host-suite output, capture driver, and earlier failed diagnostics.

Recheck the raw log structure separately from ACK/NACK campaigns:

```bash
uv run python tools/rf_proof.py --raw-mvp-logs \
  artifacts/rf-proof/20261113T062148Z/sender-final.upditerm.log \
  artifacts/rf-proof/20261113T062148Z/receiver-final.upditerm.log
```

That parser verifies log structure. Physical provenance and the negative-control
duration are supplied separately by the readbacks and timestamped capture journal.
Synthetic fixtures are host-test evidence only.

### Verification and limits

Seven focused MVP tests pass, covering raw bytes, length 0/10/11/12/oversized,
lowercase/CRC/header rejection, interrupt-free polling, TX timeout/cleanup, RX
restart, absent/stalled/delayed logging, current-target identity/fuse guards, and
the raw evidence CLI. Host C++ checks used temporary Zig/Clang tooling because
`g++` is unavailable; compatibility warning flags were needed for legacy tests.
No project dependency was added. AVR builds used the installed AVR-GCC toolchain.

The full host suite is **not green**: 158 tests ran; two pre-existing tests in
`test_upditerm_transport.py` generate four error records because `TransportError`
and the expected `recv(length, expected)` interface do not exist in the bundled
UPDIterm. The archived BOOTSIZE=44 package-test class is skipped for the replacement
Receiver. Its refusal to prepare that legacy repair for the current geometry is tested.

Voltages, power integrity, calibrated RF frequency/output power: **NOT MEASURED**.
Actual CRC-error injection, forced radio TX timeout, oversized physical packets,
and stalled physical monitor: **NOT TESTED on hardware**; exercised with host stubs.
Historical BORF on the removed board does not establish a new brownout here.
No extra measurement equipment or physical UART was used.

SRAM address-based diagnostic readback was unnecessary after complete UPDIterm
logging worked; no SRAM retention across reset/power loss is assumed. ACK/NACK
campaigns, FOTA, SD, gateway integration, boot changes, and commits remain deferred.
The Sender's `X` stop is volatile: resetting or power-cycling it resumes attempts.
