# Q crossed-untouched SIB-only batch — POST-00130

Epoch: `RCA_POST_SWAP_01`; condition: `CROSSED_UNTOUCHED`; user-reported physical mapping: P→Y, Q→X. No power, cable, adapter, harness, firmware, fuse, or board changes were made by this lane. Physical target label is X; unique AVR identity remains `UNKNOWN_TARGET` because no SIB command was reached.

## Host identity and preflight

Q resolved by ID_PATH `pci-0000:00:14.0-usb-0:1:1.0`, VID:PID `10c4:ea60`, duplicate USB serial `0001`; serial was not used as identity. Current transient tty locator was `/dev/ttyUSB1`, sysfs `/sys/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0/ttyUSB1`, USB Bus 3 Port 1 Device 22 at preflight. The other CP210x was Bus 3 Port 4 Device 21. Full inventory and exact udev/topology output: [host_inventory.md](../host_inventory.md), SHA-256 `af987be92228f9fe9a01efc9dfaf03320c64fcf10f9db4eee5e00e15bf24c444`.

Fresh direct batch preflight: `udevadm info --query=property --name /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0` exit 0 at 03:32:59.999441574–03:33:00.013798836 UTC (monotonic 62365.21–62365.22); ID_PATH matched exactly. `fuser -v` exit 1, empty output, at 03:33:05.540971854–03:33:05.655113903 UTC (monotonic 62370.75–62370.86). `lsof` exit 1, only the tracefs warning and no owner, at 03:33:06.253483218–03:33:06.342749050 UTC (monotonic 62371.46–62371.55). This owner snapshot was about 71 seconds before attempt 001. Each existing CLI invocation independently rediscovered and resolved the unique live ID_PATH and opened the stable by-path exclusively; there were no SERIAL_OPEN or identity failures. A separate fuser/lsof query was not run before each CLI call. The post-batch owner check is clear.

## Batch result

N=30 distinct one-attempt CLI invocations; 30/30 exited 1 with `LOCAL_ECHO` (failure rate 100%, Wilson 95% CI 88.65%–100%). Median probe latency 1061.754 ms; nearest-rank p95 1063.539 ms. Every attempt first transmitted one BREAK byte `00` at 300 baud. In 24/30 attempts, BREAK1 had an empty local echo and the probe stopped. In 6/30, BREAK1 echo was exact `00`; BREAK2 was then transmitted and its echo was empty. Total: 36 BREAK TX events, 36 echo reads, 6 exact/nonempty echoes, 30 empty echoes. BREAK1 exact-echo rate 6/30=20.0% (Wilson95 9.51%–37.31%); BREAK2 exact-echo rate conditional on BREAK1 passing 0/6=0% (Wilson95 0%–39.03%).

No SIB command was transmitted, no target response bytes were read, and every raw `values` object is empty. SIB hex is `NOT_SENT`, not an empty SIB response. This is an echo/synchronization-stage result; it does not classify target response. No control, ACC, reset, key, data write, NVM, fuse, flash, or BOD operation occurred. No probe attempt used an internal retry. A client-side JS parse error occurred before attempt 001 and before any nested host command; it produced zero serial opens and is excluded from N=30.

## Per-attempt evidence and timing

Raw JSON is unchanged in `attempt_NNN.json`. Each file records wall `utc`, monotonic elapsed `latency_ms`, and monotonic serial event `ns/end_ns`. The table includes outer tool wall time. All 30 SHA-256 digests were recomputed from disk and matched the CLI-reported values. CLI output below is preserved as returned by exec_command; that API exposes a single combined stream, so stdout and stderr cannot be separated after the fact.

| # | raw UTC start | latency ms | tool wall s | first event ns | last event end ns | TX BREAK hex/event | echo hex/event | SIB hex | stage | raw SHA-256 |
|---:|---|---:|---:|---:|---:|---|---|---|---|---|
| 001 | 2026-10-27T03:34:17.854252+00:00 | 1065.147841 | 1.055 | 62443075144828 | 62444076345498 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | d52432456677840734689e1c7aa75a397047d2355a67d8f2e44c58fe79cd85d5 |
| 002 | 2026-10-27T03:34:49.649920+00:00 | 1063.53852 | 1.050 | 62474867132804 | 62475871079172 | 00,00 | 00,<empty> | NOT_SENT | LOCAL_ECHO | 2a61adb1bfd7f4a7705905f8c5029f67746ef321c3d626820a17b30f139dd741 |
| 003 | 2026-10-27T03:34:51.395393+00:00 | 1063.117726 | 1.043 | 62476612339940 | 62477616105122 | 00,00 | 00,<empty> | NOT_SENT | LOCAL_ECHO | 8ca843c6bde98c106318375ce5c811f6ce242c918278b81282d1aa5f12f19061 |
| 004 | 2026-10-27T03:34:53.155866+00:00 | 1063.017301 | 1.050 | 62478372853788 | 62479374190363 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 6f455f3cdb74ca661f8c5d0869d0ded96e07d4c917511a932124338142e59e1e |
| 005 | 2026-10-27T03:34:54.971835+00:00 | 1059.486527 | 1.046 | 62480188649200 | 62481189078226 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 723d2cc44decb8a9b9d0b3716ceb6664c6eeb51661c2f283bd3ae9173e52edef |
| 006 | 2026-10-27T03:34:56.723449+00:00 | 1062.590956 | 1.045 | 62481940436950 | 62482941778157 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | e079c7573e1ad5c7781edbcbd1c0b5c4aa996882870c577a1f239938faca2ab6 |
| 007 | 2026-10-27T03:34:58.510167+00:00 | 1063.008133 | 1.035 | 62483727310513 | 62484731032160 | 00,00 | 00,<empty> | NOT_SENT | LOCAL_ECHO | e554297340b8d2f5815936423c763cc20872b651ae8bc43f9c7b6da136d51264 |
| 008 | 2026-10-27T03:35:00.276238+00:00 | 1060.712688 | 1.046 | 62485494536315 | 62486495076408 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 51377b0230900d168dcce2cabf1d7c785a82b5f4f741ecc4dffe26fdace632fa |
| 009 | 2026-10-27T03:35:02.003352+00:00 | 1062.320074 | 1.037 | 62487220340303 | 62488221199551 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | d24a499aece3f48366a149b3112b5919589f945b38835590b5ab1d90d76c9575 |
| 010 | 2026-10-27T03:35:03.766534+00:00 | 1063.225981 | 1.046 | 62488983437997 | 62489987088052 | 00,00 | 00,<empty> | NOT_SENT | LOCAL_ECHO | 3af39e0d555bd631fb1d4cf3e18bd3e8bd810c9dabf397503de134020c9dcf3d |
| 011 | 2026-10-27T03:35:05.516758+00:00 | 1063.447032 | 1.036 | 62490734917586 | 62491736250953 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | d066a93ced15443a05c6af232d4864f815060a032c3f1c221b7fb18d7d28e590 |
| 012 | 2026-10-27T03:35:07.251491+00:00 | 1061.422773 | 1.037 | 62492468350737 | 62493469597906 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 2d568bdc833f1917981b25143811528c9d2fc5a1df9fef05e6485215537a203c |
| 013 | 2026-10-27T03:35:08.992023+00:00 | 1061.742505 | 1.046 | 62494208940870 | 62495210200583 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 1df23dab2cd7c6a9555a82ecb5fb179134b10a326781dfe41ad9a5ada3686a76 |
| 014 | 2026-10-27T03:35:10.762791+00:00 | 1060.476243 | 1.060 | 62495979874379 | 62496980197722 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 46213aeef22a57728cdfca03a06a453264e00968cfdeb247aad9324fb9ceb409 |
| 015 | 2026-10-27T03:35:12.532956+00:00 | 1061.225178 | 1.023 | 62497750913813 | 62498751106272 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | e3cb505e9c45595c70d0ff2f941bcd5599cfca28e904f5196b41a445edd4df1a |
| 016 | 2026-10-27T03:35:14.273785+00:00 | 1060.545943 | 1.032 | 62499490870132 | 62500491209638 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | e56c4454c753390975311e64182b0df331cafce3d23c6d345b0953063b4e0abe |
| 017 | 2026-10-27T03:35:16.021405+00:00 | 1062.605543 | 1.036 | 62501238429698 | 62502242088497 | 00,00 | 00,<empty> | NOT_SENT | LOCAL_ECHO | cf2f8f9d18bcc2b56eb6d892a333af257b47ee92956d0196704a870f5b0bf047 |
| 018 | 2026-10-27T03:35:17.800998+00:00 | 1061.765514 | 1.063 | 62503018156154 | 62504019423338 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | b4c9750f60a9c23b7751b98835a875ba528acca2f3b1efa5d77eb31d0bd9ecda |
| 019 | 2026-10-27T03:35:19.581001+00:00 | 1060.815486 | 1.027 | 62504797692476 | 62505798876220 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | e9d99411f12954847a0180074ddf9f12697f24300ec8e84ede9fa07b4c961bd5 |
| 020 | 2026-10-27T03:35:21.318883+00:00 | 1061.083752 | 1.043 | 62506535937971 | 62507537181271 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | fe3948b4594ddf031ccf2faf989da3d7615c341143f600b0467803771a4f5a62 |
| 021 | 2026-10-27T03:35:23.094066+00:00 | 1060.371003 | 1.042 | 62508311081323 | 62509312093367 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 0c5d069ceb22d59f727761fcefddb13e65bb1b2382f1014ec050e6530b3f6032 |
| 022 | 2026-10-27T03:35:24.846652+00:00 | 1060.81181 | 1.042 | 62510063835432 | 62511065050330 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 9dd9c95e55c3ad1516ba6ff005809e56eabc3fb7fa147b97dc9f0ef84aaddde2 |
| 023 | 2026-10-27T03:35:26.607793+00:00 | 1062.499311 | 1.034 | 62511824657338 | 62512828084348 | 00,00 | 00,<empty> | NOT_SENT | LOCAL_ECHO | 4e1c17f075556f8be5c9ea22317bdeb57cdb4637070c9ca6b406b5f625f837bd |
| 024 | 2026-10-27T03:35:28.382277+00:00 | 1062.740594 | 1.047 | 62513600583303 | 62514601194915 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | a09e75d3b117ffba4454ac33d4b93462d6c17103800d5c25930b6a3dab550c05 |
| 025 | 2026-10-27T03:35:30.132794+00:00 | 1059.932547 | 1.031 | 62515349890531 | 62516350114380 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 03de5b038ce1f47ea7f1a40ef9f9f4a567a75957b9fbbc7e1340c7044e70b32d |
| 026 | 2026-10-27T03:35:31.874250+00:00 | 1060.792724 | 1.039 | 62517091195716 | 62518092215174 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | c5130f57bb5594eb9c6c077ebd37822def05265b0ba9ac5f8da4fded0ecbb5c2 |
| 027 | 2026-10-27T03:35:33.633395+00:00 | 1063.199937 | 1.043 | 62518850470878 | 62519851820538 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | bcb95e7737a490d16ff47d1399aad3febd018bf27a8faa349b03c08a8c43f3c2 |
| 028 | 2026-10-27T03:35:35.448291+00:00 | 1061.096251 | 1.057 | 62520665291346 | 62521666572491 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 7ef708420dad7d91c2b946b821830382e7df2df339bb8fa0b1f6fbaaaa710f0f |
| 029 | 2026-10-27T03:35:37.200556+00:00 | 1062.061125 | 1.034 | 62522417973326 | 62523419266557 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 1680ab7cd2e7837eac61e71519171dc1377c7cc9aa9953040ec289d2cfd14373 |
| 030 | 2026-10-27T03:35:38.953074+00:00 | 1061.080943 | 1.041 | 62524170300018 | 62525171227640 | 00 | <empty> | NOT_SENT | LOCAL_ECHO | 04e40a24d0842cfcab96baaa27cd0019a1a7678630c863f77f0ef40faf6c9fc6 |

### Attempt 001

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_001.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.054583977 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1065.147841,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_001.json",
"raw_sha256": "d52432456677840734689e1c7aa75a397047d2355a67d8f2e44c58fe79cd85d5"
}
```

### Attempt 002

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_002.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.049687084 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "0000",
"echo_hex": "00",
"response_hex": "",
"latency_ms": 1063.53852,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_002.json",
"raw_sha256": "2a61adb1bfd7f4a7705905f8c5029f67746ef321c3d626820a17b30f139dd741"
}
```

### Attempt 003

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_003.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.043201581 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "0000",
"echo_hex": "00",
"response_hex": "",
"latency_ms": 1063.117726,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_003.json",
"raw_sha256": "8ca843c6bde98c106318375ce5c811f6ce242c918278b81282d1aa5f12f19061"
}
```

### Attempt 004

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_004.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.049954747 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1063.017301,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_004.json",
"raw_sha256": "6f455f3cdb74ca661f8c5d0869d0ded96e07d4c917511a932124338142e59e1e"
}
```

### Attempt 005

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_005.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.045876448 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1059.486527,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_005.json",
"raw_sha256": "723d2cc44decb8a9b9d0b3716ceb6664c6eeb51661c2f283bd3ae9173e52edef"
}
```

### Attempt 006

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_006.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.045422841 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1062.590956,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_006.json",
"raw_sha256": "e079c7573e1ad5c7781edbcbd1c0b5c4aa996882870c577a1f239938faca2ab6"
}
```

### Attempt 007

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_007.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.035171824 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "0000",
"echo_hex": "00",
"response_hex": "",
"latency_ms": 1063.008133,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_007.json",
"raw_sha256": "e554297340b8d2f5815936423c763cc20872b651ae8bc43f9c7b6da136d51264"
}
```

### Attempt 008

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_008.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.046208957 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1060.712688,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_008.json",
"raw_sha256": "51377b0230900d168dcce2cabf1d7c785a82b5f4f741ecc4dffe26fdace632fa"
}
```

### Attempt 009

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_009.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.036740618 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1062.320074,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_009.json",
"raw_sha256": "d24a499aece3f48366a149b3112b5919589f945b38835590b5ab1d90d76c9575"
}
```

### Attempt 010

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_010.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.046133480 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "0000",
"echo_hex": "00",
"response_hex": "",
"latency_ms": 1063.225981,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_010.json",
"raw_sha256": "3af39e0d555bd631fb1d4cf3e18bd3e8bd810c9dabf397503de134020c9dcf3d"
}
```

### Attempt 011

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_011.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.035505405 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1063.447032,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_011.json",
"raw_sha256": "d066a93ced15443a05c6af232d4864f815060a032c3f1c221b7fb18d7d28e590"
}
```

### Attempt 012

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_012.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.037184372 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1061.422773,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_012.json",
"raw_sha256": "2d568bdc833f1917981b25143811528c9d2fc5a1df9fef05e6485215537a203c"
}
```

### Attempt 013

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_013.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.046423797 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1061.742505,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_013.json",
"raw_sha256": "1df23dab2cd7c6a9555a82ecb5fb179134b10a326781dfe41ad9a5ada3686a76"
}
```

### Attempt 014

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_014.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.059929592 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1060.476243,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_014.json",
"raw_sha256": "46213aeef22a57728cdfca03a06a453264e00968cfdeb247aad9324fb9ceb409"
}
```

### Attempt 015

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_015.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.023218383 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1061.225178,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_015.json",
"raw_sha256": "e3cb505e9c45595c70d0ff2f941bcd5599cfca28e904f5196b41a445edd4df1a"
}
```

### Attempt 016

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_016.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.032330931 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1060.545943,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_016.json",
"raw_sha256": "e56c4454c753390975311e64182b0df331cafce3d23c6d345b0953063b4e0abe"
}
```

### Attempt 017

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_017.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.035521355 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "0000",
"echo_hex": "00",
"response_hex": "",
"latency_ms": 1062.605543,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_017.json",
"raw_sha256": "cf2f8f9d18bcc2b56eb6d892a333af257b47ee92956d0196704a870f5b0bf047"
}
```

### Attempt 018

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_018.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.063408127 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1061.765514,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_018.json",
"raw_sha256": "b4c9750f60a9c23b7751b98835a875ba528acca2f3b1efa5d77eb31d0bd9ecda"
}
```

### Attempt 019

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_019.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.027267347 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1060.815486,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_019.json",
"raw_sha256": "e9d99411f12954847a0180074ddf9f12697f24300ec8e84ede9fa07b4c961bd5"
}
```

### Attempt 020

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_020.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.043376511 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1061.083752,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_020.json",
"raw_sha256": "fe3948b4594ddf031ccf2faf989da3d7615c341143f600b0467803771a4f5a62"
}
```

### Attempt 021

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_021.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.041528358 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1060.371003,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_021.json",
"raw_sha256": "0c5d069ceb22d59f727761fcefddb13e65bb1b2382f1014ec050e6530b3f6032"
}
```

### Attempt 022

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_022.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.042497210 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1060.81181,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_022.json",
"raw_sha256": "9dd9c95e55c3ad1516ba6ff005809e56eabc3fb7fa147b97dc9f0ef84aaddde2"
}
```

### Attempt 023

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_023.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.034027283 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "0000",
"echo_hex": "00",
"response_hex": "",
"latency_ms": 1062.499311,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_023.json",
"raw_sha256": "4e1c17f075556f8be5c9ea22317bdeb57cdb4637070c9ca6b406b5f625f837bd"
}
```

### Attempt 024

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_024.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.047361818 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1062.740594,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_024.json",
"raw_sha256": "a09e75d3b117ffba4454ac33d4b93462d6c17103800d5c25930b6a3dab550c05"
}
```

### Attempt 025

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_025.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.030800127 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1059.932547,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_025.json",
"raw_sha256": "03de5b038ce1f47ea7f1a40ef9f9f4a567a75957b9fbbc7e1340c7044e70b32d"
}
```

### Attempt 026

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_026.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.038723429 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1060.792724,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_026.json",
"raw_sha256": "c5130f57bb5594eb9c6c077ebd37822def05265b0ba9ac5f8da4fded0ecbb5c2"
}
```

### Attempt 027

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_027.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.043456363 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1063.199937,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_027.json",
"raw_sha256": "bcb95e7737a490d16ff47d1399aad3febd018bf27a8faa349b03c08a8c43f3c2"
}
```

### Attempt 028

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_028.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.057448597 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1061.096251,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_028.json",
"raw_sha256": "7ef708420dad7d91c2b946b821830382e7df2df339bb8fa0b1f6fbaaaa710f0f"
}
```

### Attempt 029

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_029.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.034119746 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1062.061125,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_029.json",
"raw_sha256": "1680ab7cd2e7837eac61e71519171dc1377c7cc9aa9953040ec289d2cfd14373"
}
```

### Attempt 030

Command (exact):

```sh
PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli probe sib pci-0000:00:14.0-usb-0:1:1.0 experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_030.json --baud 38400 --timeout 1.0
```

Exit: 1; exec_command wall time: 1.040663486 s. The tool exposed a single combined output field (stdout/stderr not separately exposed); captured output verbatim:

```text
"success": false,
"stage": "LOCAL_ECHO",
"tx_hex": "00",
"echo_hex": "",
"response_hex": "",
"latency_ms": 1061.080943,
"error_type": "echo mismatch: expected 00 received ",
"raw_path": "/home/parinya/unversity/lora/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_q/POST-00130/attempt_030.json",
"raw_sha256": "04e40a24d0842cfcab96baaa27cd0019a1a7678630c863f77f0ef40faf6c9fc6"
}
```
## Post-batch path and ownership

Snapshot window 2026-10-27 03:37:25–03:37:30 UTC, monotonic uptime 62631.18–62635.58 s. ID_PATH and by-path remained unchanged. The symlink still resolved to `/dev/ttyUSB1`; USB stayed Bus 3 Port 1 Device 22 at 12 Mbit/s; the other CP210x remained Port 4 Device 21. No re-enumeration was observed. Post-batch fuser exit 1 with empty output; lsof exit 1 with only the tracefs warning. Exact outputs:

- `udevadm info --query=property --name /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0` — exit 0, tool wall 0.000046 s; output: `DEVPATH=/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0/ttyUSB1/tty/ttyUSB1 | DEVNAME=/dev/ttyUSB1 | MAJOR=188 | MINOR=1 | SUBSYSTEM=tty | USEC_INITIALIZED=61909231423 | ID_BUS=usb | ID_MODEL=CP2102_USB_to_UART_Bridge_Controller | ID_MODEL_ENC=CP2102\x20USB\x20to\x20UART\x20Bridge\x20Controller | ID_MODEL_ID=ea60 | ID_SERIAL=Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001 | ID_SERIAL_SHORT=0001 | ID_VENDOR=Silicon_Labs | ID_VENDOR_ENC=Silicon\x20Labs | ID_VENDOR_ID=10c4 | ID_REVISION=0100 | ID_TYPE=generic | ID_USB_MODEL=CP2102_USB_to_UART_Bridge_Controller | ID_USB_MODEL_ENC=CP2102\x20USB\x20to\x20UART\x20Bridge\x20Controller | ID_USB_MODEL_ID=ea60 | ID_USB_SERIAL=Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001 | ID_USB_SERIAL_SHORT=0001 | ID_USB_VENDOR=Silicon_Labs | ID_USB_VENDOR_ENC=Silicon\x20Labs | ID_USB_VENDOR_ID=10c4 | ID_USB_REVISION=0100 | ID_USB_TYPE=generic | ID_USB_INTERFACES=:ff0000: | ID_USB_INTERFACE_NUM=00 | ID_USB_DRIVER=cp210x | ID_VENDOR_FROM_DATABASE=Silicon Labs | ID_HARDWARE_WALLET=1 | ID_MODEL_FROM_DATABASE=CP210x UART Bridge | ID_PATH_WITH_USB_REVISION=pci-0000:00:14.0-usbv2-0:1:1.0 | ID_PATH=pci-0000:00:14.0-usb-0:1:1.0 | ID_PATH_TAG=pci-0000_00_14_0-usb-0_1_1_0 | ID_INTEGRATION=external | ID_MM_CANDIDATE=1 | ID_MM_DEVICE_IGNORE=1 | ID_MM_PORT_IGNORE=1 | DEVLINKS=/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0 /dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0 /dev/serial/by-path/pci-0000:00:14.0-usbv2-0:1:1.0-port0 | TAGS=:systemd: | CURRENT_TAGS=:systemd:`
- `readlink -f /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0` — exit 0, tool wall 0.000018 s; output: `/dev/ttyUSB1`
- `lsusb -t` — exit 0, tool wall 0.000079 s; output: `/:  Bus 001.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/1p, 480M | /:  Bus 002.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/3p, 20000M/x2 | /:  Bus 003.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/12p, 480M |     |__ Port 001: Dev 022, If 0, Class=Vendor Specific Class, Driver=cp210x, 12M |     |__ Port 004: Dev 021, If 0, Class=Vendor Specific Class, Driver=cp210x, 12M |     |__ Port 006: Dev 004, If 0, Class=Video, Driver=uvcvideo, 480M |     |__ Port 006: Dev 004, If 1, Class=Video, Driver=uvcvideo, 480M |     |__ Port 006: Dev 004, If 2, Class=Human Interface Device, Driver=usbhid, 480M |     |__ Port 006: Dev 004, If 3, Class=Application Specific Interface, Driver=[none], 480M |     |__ Port 009: Dev 005, If 0, Class=Vendor Specific Class, Driver=[none], 12M |     |__ Port 010: Dev 006, If 0, Class=Wireless, Driver=btusb, 12M |     |__ Port 010: Dev 006, If 1, Class=Wireless, Driver=btusb, 12M | /:  Bus 004.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/4p, 10000M`
- `for f in /sys/bus/usb/devices/3-1/{idVendor,idProduct,serial,busnum,devnum,speed,authorized,power/control,power/runtime_status,power/autosuspend_delay_ms}; do printf '%s=' "$f"; cat "$f" 2>&1; done` — exit 0, tool wall 0.000038 s; output: `/sys/bus/usb/devices/3-1/idVendor=10c4 | /sys/bus/usb/devices/3-1/idProduct=ea60 | /sys/bus/usb/devices/3-1/serial=0001 | /sys/bus/usb/devices/3-1/busnum=3 | /sys/bus/usb/devices/3-1/devnum=22 | /sys/bus/usb/devices/3-1/speed=12 | /sys/bus/usb/devices/3-1/authorized=1 | /sys/bus/usb/devices/3-1/power/control=on | /sys/bus/usb/devices/3-1/power/runtime_status=active | /sys/bus/usb/devices/3-1/power/autosuspend_delay_ms=2000`
- `fuser -v /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0` — exit 1, tool wall 0.000023 s; output: (empty)
- `lsof /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0` — exit 1, tool wall 0.000016 s; output: `lsof: WARNING: can't stat() tracefs file system /sys/kernel/debug/tracing |       Output information may be incomplete.`

## Software source identity

Relevant source hashes at batch time matched host inventory: `cli.py` fe1776dc56695d713312f42c304b4a977cfc2b0d0886b59b49697eba5ed5d1e9; `probes.py` db783316cc16653d12b90040507a89d178622374bb61ec87fecd5a2f3fe347e8; `identity.py` 0f905d6e7cd391575753ed7239ca8b97fab7e209cc58366b55017e447788192e; `runner.py` 7f737b0fe624967829dd51525cc0256cfd6c847840710eacc078c1ff9f6f8997. No source code was changed by this lane.

## Stop state

All 30 authorized attempts are complete; the port is closed and the post-batch ownership check is clear. Await coordinator direction. Do not treat this as a SIB response failure or proof of a target board defect.

