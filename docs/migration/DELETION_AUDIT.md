# Source and documentation deletion audit

## Current continuation

The final worktree diff contains **0 deleted files** and **0 deleted Markdown
files**. No source implementation or unique historical evidence was removed
in this continuation. `IsDeadlineDue` was moved unchanged from
`stable_lib/arq/sender.cpp` into the shared inline
`stable_lib/arq/arq_deadline.h`; the Sender implementation remains in place.
The new role-header regression and final link maps verify that the move did not
retain a wrong-role transaction dependency.

## Earlier source-ownership migration

The source moves that were already part of the current HEAD are recorded in
[Source Ownership V2](../refactoring/SOURCE_OWNERSHIP_V2.md). The final
current-tree map and role evidence are in
[Final Architecture](../architecture/FINAL_ARCHITECTURE.md). The reviewed
migration included:

| Former responsibility/path | Current owner | Removal evidence retained in |
|---|---|---|
| Shared role-dispatching ARQ application | `src/sender/appcode/arq/` and `src/receiver/appcode/arq/` | Directional tests, build filters, per-role ELF maps |
| Raw ARQ radio setup outside the shared boundary | `src/shared/radio/arq_radio.*` | Radio-only/fault fixtures and all ARQ builds |
| Role-conditional reliable lifecycle | Sender and Receiver `reliable.cpp` files | Addressed transport tests and role-selected builds |
| Feature collection for radio, transport, and diagnostics | `src/shared/{radio,protocol,diagnostics}/` | HAL, codec, transport, and diagnostic tests |
| Top-level handoff fixture | `src/receiver/bootloader/handoff/` | Standalone fixture map, disassembly, HEX, and six vector traces |

Those historical moves were not repeated in this worktree. The V2 report
contains its file-by-file migration table and before/after build evidence.

## Markdown inventory and references

The final scan found 66 Markdown files: 19 tracked, ten new requested guides,
and 37 ignored or archived files. The tracked count stayed 19; no Markdown was
deleted or consolidated. The active documentation set has 28 files and 91
relative links, all resolving.

The ignored historical snapshot `artifacts/rf-proof/20261116T043313Z/report.md`
had 18 absolute links into a prior checkout. Their displayed path labels and
captured targets were preserved as literal text; only the nonfunctional link
markup was removed. A byte-for-byte copy of the original is at
`/tmp/lora-v4-evidence/report.md.before-link-cleanup`. The full 66-file scan
now finds zero broken links. See the [ACK/NACK guide](../testing/LORA_ACK_NACK.md)
for current documentation and protocol status.
