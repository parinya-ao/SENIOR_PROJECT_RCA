# Investigation Handoff

## Current finding

The fresh 38400 baseline has Lane A SIB/control at 100/100 pass each and Lane B at 0/100 each, failing at local echo before target response. Wilson 95% success intervals are Lane A 96.30%–100.00% and Lane B 0.00%–3.70%. This is lane-bound evidence; adapter and target remain paired and target identity is unknown.

Historical unheld LDS evidence remains separate: 19/60 ACC data responses missing after exact echo (31.67% failure, Wilson 95% failure interval 21.31%–44.23%). Do not merge it with the current TX/echo failures.

A separate bounded Lane A OCD snapshot passed 1/1 in 284.286 ms (Wilson 95% success interval 20.65%–100.00%) and read 15 valid message bytes: `HEYYY fuckkkk\r\n` (hex `4845595959206675636b6b6b6b0d0a`). Status was 0x10 before every byte and 0x00 after. This matches the visible console line, but the original 9-line terminal session still lacks timestamps and identity. The read consumed the volatile 15-byte message queue.

The separate GPR2 campaign returned `0x03` in 100/100 LDS reads; `FLAG_RX` was set in 100/100 (descriptive Wilson interval 96.30%–100.00%), median/p95 147.597/150.083 ms. No virtual-UART payload was written. This confirms persistent flag state during those sequential observations, not 100 new receive events or the source of the flag. In the inspected upstream virtual-UART helper, `FLAG_RX` means RX buffer full and is cleared when firmware reads GPIOR3; current target firmware is unknown. This register is separate from the captured target-to-host OCD message bytes.

## Safety/state

No current fuse or firmware snapshots were obtained and the built diagnostic image (SHA-256 `729162b13f65bdcd464a20f8305857dde3d1f91b90e9084ff003a251268ba055`) was not flashed. No new flash writes occurred. The prior verified historical write remains in `reports/flash_budget.csv`.

## Next discriminator

Perform one no-programming adapter crossover with boards labeled, then repeat the 100-attempt SIB/control conditions. If the failure follows a target, obtain the simultaneous capture specified in `reports/STAR_RCA.md`: MCU VDD/local GND, ground offset, RESET, UPDI at both sides of the series element, and adapter TX during attach and RUN, low-capacitance probes, >=20 MS/s.

## Interpretation cautions

- The terminal transcript has 9 lines and no per-line timing/identity. A later Lane A read captured 15 bytes matching one line, with OCDMV=1 before each byte and 0x00 afterward; SIGKILL is a host process exit, not a target reset.
- GPR2 `0x001e` returned `0x03` and `FLAG_RX` remained set in 100/100 sequential Lane A reads; this is persistent observed state, not proof of 100 fresh receive events or “always active” behavior. The inspected upstream helper defines it as RX buffer full and clears it only after an RX read; current firmware is unknown. It does not represent the target-to-host OCD output channel.
- `OCDMV=1`, `OCD_STOPPED=0`, raw status 0x10, and SYS_STATUS 0x82 were observed on Lane A. One message snapshot read 15 bytes; intentional no-output SILENT firmware was not flashed, so that condition remains untested.
- BORF without an independently observed new boot marker is historical state.
- All 168 hypothesis rows remain in the inventory; current statuses: PROVEN=0, STRONGLY_SUPPORTED=0, SUPPORTED=8, UNRESOLVED=48, DISFAVORED=0, FALSIFIED=0, BLOCKED=112.
