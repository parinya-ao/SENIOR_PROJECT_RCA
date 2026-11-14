# Execution journal

## SSOT read-only review

- Compared `docs/ssot/TRACKER_SSOT.md`, `docs/ssot/GATEWAY_SSOT.md`, `config/current_hardware.json`, generated manifests, `src/arq/board_ssot.c`, `platformio_generate.py`, `src/reverse_raw/main.cpp`, and reverse-raw programmer commands.
- Result: board pin maps agree; reverse functional role inversion is intentional; physical continuity and power remain unmeasured.
- Commands: `uv run python tools/config/generate_lora_config.py --check` (exit0); `uv run python tools/config/validate_lora_ssot.py config/lora_system.json` (valid, physical suitability unverified); static Python comparison (PASS).

## Gate 1 live

- Evidence: `artifacts/arq/gate1-updi/20261113T153146Z/`.
- Identity: Tracker AVR128DA28 signature `1e970a`, serial matched config. Port owner check empty. Two BREAKs; no reset invoked.
- Host request: STATUS once, raw seven bytes `5354415455530a`. All low-level UPDI protocol operations completed without exception before deadline.
- Result: no Monitor stdout, status response timeout at120.004039 s; stopped at request1. No retries.
- No RF or memory programming occurred. Normal disable cleanup was attempted but failed after the bounded Host timeout had closed the serial handle.

## Next discriminating experiment

- E-MBOX: one STATUS command with read-only snapshots of GPIOR2 (flags), GPIOR3 (RX byte), GPIOR0 (application-saved reset flags), RSTCTRL.RSTFR, ASI_OCD_STATUS and firmware's OCDMS mailbox register immediately before and after input consumption. The probe uses the existing Monitor connection and no firmware or fuse changes. Its key discriminators are: RX-full remains set (firmware did not consume final newline), RX-full clears and OCDMS remains idle (handler/logger path), or reset flag evidence changes. The probe is separately logged and never retries within one session.
