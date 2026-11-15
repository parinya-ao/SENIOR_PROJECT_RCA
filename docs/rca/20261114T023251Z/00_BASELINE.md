# Baseline and scope

## Scope

Continue the hardware-in-the-loop investigation of Tracker reset and Tracker↔Gateway LoRa ARQ. The Gateway is the DATA transmitter in H01; the Tracker is in RX Continuous and may transmit an ACK. Application role labels are not used to infer instantaneous radio mode.

## Environment

| Item | Observed value |
|---|---|
| Repository | `/home/parinya/university/SENIOR_PROJECT_RCA` |
| Branch / starting commit | `fix/receiver-rfm-rev1-pins` / `cad40a9923f36b76b6531417e2e432bc66467636` |
| Python invocation | `uv run`; project Python 3.14.10; `uv 0.13.7`; pySerial 3.5 |
| PlatformIO | platform `atmelmegaavr 1.10.0`, DxCore `1.6.2`, AVRDUDE `8.1.0` |
| RadioLib | `7.1.2`, from the installed PlatformIO package and `platformio.ini` |
| Tracker | AVR128DA28, serial `42032240221092150158013400000000`, stable path USB port 1 |
| Gateway | AVR128DA28, serial `42032240221023150129012600000000`, stable path USB port 4 |
| UPDI adapters | Silicon Labs CP2102, VID `10c4`, PID `ea60`; tty numbering is not identity |
| External voltage/RF instruments | None connected: no oscilloscope, logic analyzer, SDR, spectrum analyzer, or voltage logger |

The operator reports that the Tracker board receives nominal 3.3 V through the UPDI adapter/H1 connection. This is an **operator-reported topology**, not a measured voltage or transient. The USB device enumeration identifies CP2102 adapters but does not prove which adapter VDD pin is physically connected to H1.

During this investigation the branch HEAD advanced from `cad40a9` through `5b715df` and `19ef9cc` to `f8092bc` via repository commits; the investigator issued no commits. The H01 session-8 bundle records `19ef9cc`; session 9 and the RX-idle control record `f8092bc`. Each hardware bundle preserves its source revision.

## Active hardware configuration

The current [LoRa SSOT](../../ssot/TRACKER_SSOT.md) maps Tracker radio power enable to PA7, active low. `board_ssot_init()` asserts PA7 low during setup; `SEND` does not create a PA7 transition. Current `config/lora_system.json` and generated PlatformIO settings specify `BOOTSIZE=0`, `CODESIZE=0`, and image start `0`. No fuse was written. The separate `tools/receiver_boot.py` utility describes a different historical `0x5800` layout and was not used.

The Gateway uses its own board mapping and PA7 is an address strap, not Tracker radio power control.

## Preservation

- The three original 2026-11-13 artifact manifests were rechecked: 64 + 90 + 67 = **221 files**, no missing files or SHA-256 mismatches.
- The 1,553-file baseline manifest currently has **7 changed paths** and 0 missing paths. `tools/arq_trial.py` was already dirty at the start of this continuation and was extended for the authorized diagnostic; therefore the 7-path count is not attributed solely to this run. No `src/` or `lib/` file changed.
- Active firmware test images were temporarily installed with the existing bounded application writer. Signature, serial, fuses, lock, EEPROM and Flash readbacks were retained before/after; the final normal standby verifier reports `standby=true`, `rf_transmissions=0` for both roles.
- No source under `src/` or `lib/` was changed. The legacy `/home/parinya/university/iwing-tracker` worktree was not modified.

## Historical classifications kept intact

- `20261113T121506Z`: `PHYSICAL_RF_FAILURE_UNISOLATED`.
- `20261113T123620Z`: `HOST_TRANSPORT_ERROR / RF INCONCLUSIVE`.
- `20261113T142138Z`: Gate 1 preflight blocked before STATUS; not a hardware result.
