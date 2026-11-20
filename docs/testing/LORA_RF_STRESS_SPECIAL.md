# Isolated LoRa RF stress suite

This suite is an explicitly invoked, special test tool. It is outside the normal `test_*.py` collection and is not a CI dependency. The default command writes a host-only case plan and never opens a serial port or transmits.

```bash
mise run rf_stress
uv tool run --from pytest pytest -q -o python_files=spec_*.py tests/rf_stress_special
```

The case planner uses the configured ARQ payload limit and spacing from `config/arq_test.toml`. The active radio profile comes from `config/radio_915.toml` and must match the ARQ PHY settings. The plan records a seed, payload bytes and SHA-256 per frame, direction, expected fault, session, sequence, payload limit and spacing. Fifty-two letters are scheduled in each direction. The 52-byte alternating payload is split at the actual configured frame limit. Binary framing is listed as a separate capability-gated case.

Stress transmission requires `--real-rf`, an explicit `--rf-profile radio_915`, a full saved readback and its historical image receipt. Torture also requires `--long-duration`. The firmware's configured TX spacing is 10 seconds. The existing soak airtime planner calculates a 60-second case interval for the configured 44-byte frame and five-attempt worst case. The plan also records a bounded timeout-based worst-case runtime. A runtime cap that cannot accommodate the planned cases blocks transmission.

```bash
uv run --locked python -m tools.rf_stress \
  --real-rf --profile smoke --seed 12345 --rf-profile radio_915 \
  --readback artifacts/rf-debug/sram-readback-20261119T140936Z \
  --historical-receipt artifacts/rf-proof/20261118T095311Z/physical-upload.json
```

The enrolled `sender_hello` / `receiver` images support the fixed-payload ACK and one-shot NACK proof. They do not expose the variable-payload, Tracker TX, receiver payload-byte, or duplicate-counter interfaces needed by this suite. The special host transaction transport is also not implemented. The stress command validates the supplied saved images and records `BLOCKED` before any RF command. It does not install firmware. The existing `tools.installed_rf` command remains the bounded 10 ACK / 10 NACK test for the currently installed pair.

Offline replay reads a prior `manifest.json`, its sibling `cases.jsonl` and `events.jsonl`, and writes a separate report. It never opens a radio or overwrites the source evidence.

```bash
uv run --locked python -m tools.rf_stress \
  --replay artifacts/rf-stress/RUN_ID/manifest.json \
  --case-id case-00001
```

An RF `PASS` requires a correlated sender DATA completion, receiver-side exact `PAYLOAD_HEX`, receiver response TX completion and sender response acceptance for the same session and sequence. Missing receiver bytes produce `UNVERIFIED`. RSSI, SNR and airtime stay `null` unless captured in event fields. Gateway and Tracker uptime clocks are never subtracted from each other.
