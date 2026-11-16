# Strict Python static analysis

Start from four needs:

1. Code can be syntactically valid and still contain suspicious operations, unused names, insecure patterns, or confusing control flow. Ruff lint checks these patterns.
2. Functions can disagree about the kinds of values they exchange. Mypy checks type contracts; strict mode also requires annotations on functions.
3. Formatting differences waste review time. Ruff format checks one consistent style without changing files.
4. A check only enforces a rule if violations fail it. Every task below returns a nonzero exit code on violations; there is no success baseline or blanket missing-import suppression.

Configuration lives in `pyproject.toml`. Development tools and pyserial type stubs are recorded in `uv.lock`; use `--locked` so the same versions run each time. Python 3.14 follows the project's declared minimum, and `uv run` selects the project interpreter.

Run all checks:

```sh
mise run lint:python
```

Or run each check directly:

```sh
uv run --locked ruff check src/lora tools tests
uv run --locked ruff format --check src/lora tools tests
uv run --locked mypy
```

The scope is maintained application code, host tools, and tests. Generated radio profiles, dependencies, firmware build directories, archived RCA experiments, and graph outputs are excluded. Tests keep the existing unittest assertion and exception APIs; test assertions are permitted. Formatter-conflicting lint rules are disabled so the formatter and linter agree. All other stable Ruff rules are selected. Mypy uses strict mode, additional checks, unreachable-code checks, and errors for types imported through unresolved dependencies. Unknown imports are reported, not silently accepted.

Strictness exposes existing debt immediately. A configured tool is not evidence that the repository passes it. Fix findings in scoped changes; don't weaken the configuration to make an unrelated change appear clean. Static analysis complements host tests and physical hardware checks; it cannot establish electrical safety or DATA/ACK delivery.

References: [Ruff linter](https://docs.astral.sh/ruff/linter/), [formatter compatibility](https://docs.astral.sh/ruff/formatter/#conflicting-lint-rules), [mypy configuration](https://mypy.readthedocs.io/en/stable/config_file.html).

## Verified initial result (2026-11-14)

- Ruff: 4,846 findings across 57 files; exit 1.
- Formatting: 53 files would change, four already formatted; exit 1.
- Mypy: 2,166 errors in 52 files, with 58 source files checked; exit 1.
- The combined mise task fails as intended on existing violations.
- Negative probes confirmed unused-import detection, incompatible argument rejection, and required function annotations.

No bulk fixes or formatting were applied. These counts describe the current working tree, including pre-existing work and the bring-up changes. No CI workflow was added; run the local tasks above.
