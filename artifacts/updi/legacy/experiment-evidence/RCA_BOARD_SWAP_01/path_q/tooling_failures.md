# Q PRE host-tool failures

Epoch RCA_BOARD_SWAP_01. These were host-side Python wrapper errors, not UPDI results. No target probe JSON was produced and no serial session began.

## Attempt 1 — parse-time error

- Approximate invocation time: 2026-10-27 01:58 UTC; exact UTC and monotonic timestamps were not retained by the tool call.
- Command line: PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python - <<'PY' with a single-use inline campaign wrapper.
- Exit code: numeric status was not retained.
- Captured tool output (stdout/stderr separation was not retained):

  File "<stdin>", line 147  
  SyntaxError: no binding for nonlocal 'halt_reason' found

- Effect: Python rejected the wrapper before executing it. Zero attempts; no serial open.

## Attempt 2 — host runtime error

- Approximate invocation time: 2026-10-27 01:58 UTC; exact UTC and monotonic timestamps were not retained by the tool call.
- Command line: PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python - <<'PY' with a corrected single-use inline campaign wrapper.
- Exit code: numeric status was not retained.
- Captured tool output (stdout/stderr separation was not retained):

  Traceback (most recent call last):  
    File "<stdin>", line 155, in <module>  
  NameError: name 'source_files' is not defined

- Effect: the wrapper stopped before run_campaign; the output directory pre/Q_PRE_SIB_20261027T015802Z/attempts/ is empty. Zero attempts; no serial open. The wrapper's immediate ownership-check output was held only in memory and was not saved, so this error is classified only as HOST_TOOL_ERROR, not as evidence of PORT_BUSY.

Coordinator instruction: do not develop or rerun a wrapper. The coordinator owns any future batch invocation.
