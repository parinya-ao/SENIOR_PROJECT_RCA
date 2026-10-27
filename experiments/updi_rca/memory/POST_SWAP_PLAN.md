# Untouched crossed-state implementation plan

Goal: measure the already-swapped boards before any further physical action.
Spec: latest user POST-SWAP specification; inherited PROMPT.md and SWAP_FREEZE.md.
Epoch: RCA_POST_SWAP_01. Initial phase: CROSSED_UNTOUCHED.

The coordinator owns shared code/reports. Reuse the two existing lane workers,
identity resolver, strict probe, runner, classifiers and metrics. No transport
changes or new dependencies. All handwritten investigation files stay here.

## Experiment POST-001

- Hypothesis: crossed observations distinguish target-following FC1 from external-path-following FC1, or expose shared/non-stationary state.
- Prediction: failure-stage rates differ across P→Y and Q→X in the pattern predicted by the owning entity.
- Independent variable: target assignment already changed by the user; no new physical intervention in this screen.
- Controlled variables: existing 38400 nominal baud, 300-baud BREAKs, 8E2, timeout 1.0 s, same strict read-only code, fixed USB paths and external bundles as reported.
- Measurement: 30 bounded SIB attempts per path; exact BREAK and command echoes, target responses, monotonic/wall times, source hashes and ownership checks.
- Expected observation: current four stage boundaries are separately measurable; target serial remains UNKNOWN unless read safely.
- Alternative interpretation: reseating, unknown power cycle/order, latest PRE non-stationarity, target power or mapping error can confound a historical comparison.
- Stopping rule: stop on ambiguous identity/port ownership or serial-open error. Complete the 30-screen for protocol failures. Choose confirmation only after comparing both lanes; no automatic giant matrix.

## Implementation and verification

1. Run inherited suite; add tests in tests/test_post_swap.py for the requested identities, history preservation, stage separation, crossed classification, confounds and restore gate. Observe RED on missing post-swap assessment.
2. Add only post_swap_assessment to src/updi_rca/board_swap.py. Retain tentative classification while withholding proof for absent restore/non-stationary baseline/unknown power intervention. Run full suite.
3. Freeze current host inventory and user-reported physical P→Y/Q→X mapping. Workers collect 30 SIB-only attempts using existing CLI; no custom protocol wrapper. Each preserves batch and per-attempt command evidence, local raw logs and hashes.
4. Coordinator creates versioned post_swap inventory/run/event/echo/matrix/hypothesis/proof CSVs, STAR report and Markdown state. Preserve all inherited CSV bytes.
5. Verify old and new hashes, unique IDs/mapping, 168 master IDs, focused IDs, row counts and zero flash/fuse writes. Refresh Graphify after code change.
6. Only after crossed evidence is persisted/verified, request one restoration action if supported and safe. Record power-cycle and connector confounds rather than inventing controls.

Review focus: unknown target must not inherit old identity; tty renumbering must not move an adapter; FC1 must not become FC2; absent restore must not grant proof; historical baseline non-stationarity must remain visible.
