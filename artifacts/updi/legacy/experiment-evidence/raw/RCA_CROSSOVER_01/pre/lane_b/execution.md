# Lane B pre-crossover execution record

- Adapter: VID:PID `10c4:ea60`; serial `0001` (2 adapters expose this duplicate); ID_PATH `pci-0000:00:14.0-usb-0:1:1.0`.
- Sysfs: `/sys/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0/ttyUSB1/tty/ttyUSB1`.
- By-path link: `/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0`; current tty locator at preflight: `/dev/ttyUSB1`.
- Preflight: exactly one live adapter matched ID_PATH; by-path resolved to the current tty; `fuser` returned exit 1 with empty output, so the port was unowned.
- Exact command: see `command.txt`.
- Wall start UTC: `2026-10-26T21:18:32.106295+00:00`.
- Wall end UTC: `2026-10-26T21:18:54.027076+00:00`.
- Monotonic start: `39897318210185 ns`.
- Monotonic end: `39919238974281 ns`.
- Monotonic duration: `21.920764 s`.
- Exit code: `1` (the CLI reports nonzero when any probe fails).
- Stdout: exact captured CLI output is in `stdout.txt`.
- Stderr: empty, 0 bytes.
- SHA-256 `command.txt`: `700dca875d1a45a73834adb3d55ee9f5dc53764e11203b1d988067955f54a693`.
- SHA-256 `stdout.txt`: `aa9f27a65727670155d425fe7882e04aeba968a6a330fac5906ee0756a2be7fe`.
- SHA-256 `stderr.txt` (empty): `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Target identity: `UNKNOWN_TARGET`; the baseline did not reach a target identity response.
- Target write policy: no STCS, STS, programming key, reset, NVM write, fuse write, or flash operation.

## Condition results

| Condition | N | Pass | Fail | Failure stage | Median ms | P95 ms | Wilson 95% success CI |
|---|---:|---:|---:|---|---:|---:|---:|
| SIB | 10 | 0 | 10 | LOCAL_ECHO 10/10 | 1061.647 | 1064.128 | 0.000%–27.754% |
| Control snapshot | 10 | 0 | 10 | LOCAL_ECHO 10/10 | 1061.556 | 1063.475 | 0.000%–27.754% |

Across SIB, first BREAK echo was empty in 8/10 and exact `00` in 2/10; after the 2 exact first echoes, the second BREAK echo was empty. Across control, first BREAK echo was empty in 9/10 and exact `00` in 1/10; that second BREAK echo was empty. No SIB request (`55 e6`), LDCS request, or target response occurred. Exact per-attempt raw paths and hashes are recorded in each condition summary JSON. All 10 raw hashes per condition were recomputed and matched.

- SIB summary SHA-256: `d5701554adda8b9227632eece9f5513cf85d9c15f2b4fa33a7b23d67de690997`.
- Control summary SHA-256: `0ae0e694396525806064ed02a6de72e4b472f28b719a28acd379895ffa8c037b`.
