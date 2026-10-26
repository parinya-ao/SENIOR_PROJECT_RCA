# Reproduce the local upditerm delta

The upstream repository is https://github.com/streef/upditerm, pinned at
`f2222b02ceeff7668caab0f240d2e13298116356`. Its LICENSE and attribution remain
in `external/upditerm/`. The only upstream file changed is `upditerm.py`.

From a fresh project checkout without `external/upditerm/`:

```sh
git clone https://github.com/streef/upditerm external/upditerm
git -C external/upditerm checkout --detach f2222b02ceeff7668caab0f240d2e13298116356
git -C external/upditerm apply --check ../../patches/upditerm/0001-fail-fast.patch
git -C external/upditerm apply ../../patches/upditerm/0001-fail-fast.patch
.venv/bin/python -m unittest discover -s test -v
pio run
```

Do not reapply the patch to the already patched checkout. To check an existing
patched checkout, use `git -C external/upditerm apply --reverse --check
../../patches/upditerm/0001-fail-fast.patch`.

The delta adds contextual transport exceptions, cancellation and main-thread
failure propagation, explicit serial/log closure and terminal restoration. It
preserves upstream protocol commands, timing, echo checking, CLI options and
defaults. ACK bytes are named in diagnostics; their values are not newly
validated. Windows redirected input uses the standard Windows pipe-readiness
API; it has a mocked test, but no native Windows test has been run.

The project target adapter compiles upstream `updi_uart.c` and includes its
header. It maps `GPIOR2/3` to AVR DA `GPR_GPR2/3`; addresses remain
`0x001e/0x001f`, and upstream OCD addresses remain `0x0f18/0x0f19`.
There is no retry wrapper or protocol sequencing patch.
