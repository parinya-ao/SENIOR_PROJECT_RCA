# AVR128DA28 UPDI root-cause investigation

This directory owns the first-party UPDI RCA Python source, tests, scripts, configuration, and its third-party Python dependencies. Generated evidence lives under `../../artifacts/updi/`; human-maintained RCA documents live under `../../docs/rca/updi/`.

## Current result

- Adapter lanes are mapped by stable `ID_PATH`; both CP2102 adapters report duplicate USB serial `0001`.
- Strict 38400 baseline: Lane A passed 100/100 SIB and 100/100 control reads; Lane B failed 100/100 in each condition at `LOCAL_ECHO`, before any target response.
- Follow-up GPR2 read: Lane A returned `0x03` in 100/100 direct LDS reads at `0x001e`; `FLAG_RX` and `FLAG_ENABLE` were set in all 100. Reads were sequential observations of persistent state, not evidence of 100 new receive events.
- A bounded Lane A OCD snapshot (n=1) captured the 15-byte message `HEYYY fuckkkk\r\n`; `OCDMV=1` preceded every byte and cleared afterward.
- Both target identities remain `UNKNOWN_TARGET`; current firmware and fuse hashes are unverified.
- No flash, fuse, USERROW, EEPROM, reset, BOD, or chip-erase write was issued in this investigation.
- Board versus adapter attribution is unresolved because each adapter stayed paired with one target. See [STAR RCA](../../artifacts/updi/legacy/experiment-reports/STAR_RCA.md).

## Host tooling

Run the isolated host suite from this directory:

```sh
uv sync
uv run pytest
```

The CLI can inventory adapters without opening a serial port:

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli inventory
```

Raw probes are bounded and read-only. Each one resolves a live adapter by `ID_PATH`, opens its stable by-path link, persists the raw JSON, then closes the port.

`probe ocd-message` reads `ASI_OCD_STATUS` and valid `ASI_OCD_MESSAGE` bytes without register writes. Reading consumes the volatile OCD message queue, so the recorded one-shot snapshot is the evidence; rerunning can consume different bytes.

## Evidence map

- `../../artifacts/updi/legacy/experiment-evidence/raw/` — historical lane JSON logs and terminal transcript.
- `../../artifacts/updi/legacy/experiment-reports/` — historical inventory, run/event, hypothesis, pairwise, fuse, flash-budget, and ranking CSVs.
- `../../artifacts/updi/fresh/` — RCA_FRESH_01 raw captures, reports, and verifier inputs.
- `memory/` — plan, sources, evidence log, decisions, and handoff.
- `target/` — one unflashed SILENT-then-HEARTBEAT diagnostic image.
- `diagrams/` — cause/evidence D2 source; generated SVGs are under `../../artifacts/updi/legacy/diagrams/`.

Historical notes retain paths from their capture time; the artifact locations above are canonical now.

All hypothesis labels in the CSVs are translated to English with stable H001–H168 identifiers; the supplied wording remains preserved in `../../docs/development/PROMPT.md` as the source.
