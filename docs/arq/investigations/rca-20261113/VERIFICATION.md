# Reproducible verification

All commands are offline except manufacturer/upstream documentation retrieval.
No serial device was opened. Test subprocesses have explicit bounds (compiler30s,
fake executable5–10s); evidence analysis has size/path/entry bounds.

| Check | Command / method | Actual result |
| --- | --- | --- |
| RED analyzer | unittest discover `test_rca.py` before module existed | Missing tools.rca import, retained [log](verification/red.log) |
| RED fake SEND harness | Same before isolated harness existed | Expected missing harness compile failure, [log](verification/send-red.log) |
| RED errata harness | Same before isolated driver harness existed | Expected missing harness compile failure, [log](verification/errata-red.log) |
| GREEN focused | Same with local host C++ compiler environment |30 tests OK before final supplemental-integrity test; [log](verification/green.log) |
| Full regression | `uv run python -m unittest discover -v -s tests` |221 tests, OK, one obsolete BOOT-repair class skipped; includes31 RCA tests |
| Original preservation | SHA256 of all1553 pre-existing files before/after RCA | No changes; [result](preservation-of-originals.json) |
| Incident analysis | Three README analyzer commands | Original hashes, raw/journal equality, firmware/source/config relationships pass |
| Protected memory | Existing require_preserved + normalized HEX comparison on6 archived before/after pairs | All PASS; [result](preservation.json) |
| Config consistency | `uv run python tools/config/generate_lora_config.py --check` | PASS; no regeneration/build/upload |
| Diff whitespace | `git diff --check` | PASS |
| Graph | `graphify update .` | AST graph updated; no LLM delegation |

Host C++ setup is the pre-existing local extracted toolchain, not a new dependency:
prepend `.automation/ack-investigation/toolchain/root/usr/bin` to PATH; set
CPLUS_INCLUDE_PATH to its `usr/include/c++/16`, `.../16/x86_64-redhat-linux`,
`.../16/backward`; LIBRARY_PATH to `usr/lib/gcc/x86_64-redhat-linux/16`.
Without this environment the standalone errata characterization cannot find g++.
The earlier supplemental RED run also encountered that toolchain error; its
integrity assertion independently failed for the intended missing behavior.
Use the full configured run as the regression result.

Final output: [full-suite.log](verification/full-suite.log).
Upstream JSON/diffs retained under verification are research artifacts, not
implementation replacements. Historical190-test/six-build results remain in
the original incidents; no firmware build or flash is claimed in this RCA.
