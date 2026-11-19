# Real-radio verification evidence

## Status: BLOCKED, no physical trials run

The required physical acceptance needs 10 independent valid DATA/ACK exchanges
and 10 wrong-destination trials with zero application acceptance and zero
ACK/NACK transmissions. No such trials ran in this verification. Device
discovery returned `status=MISSING` for both `SENDER` and `RECEIVER`; the
`/dev/serial/by-path` directory is absent. There are no current device
identities, installed-image hashes, or paired captures to report.

| Trial | Required evidence | Current result |
|---|---|---|
| Valid DATA/ACK | Gateway sends the 11 bytes `hello world`, sequence 1; Tracker accepts all 11 bytes and transmits ACK type `0x03`, sequence 1; Gateway receives and accepts that matching ACK | **0/10 run — BLOCKED** |
| Wrong destination | Ten addressed DATA attempts; zero application accepts and zero ACK/NACK transmissions | **0/10 run — BLOCKED** |
| NACK/retry | Paired endpoint logs prove the existing NACK and bounded retry behavior | **NOT TESTED** |
| RF timing/reliability | Monotonic paired timestamps and actual radio results | **NOT TESTED** |
| Fuse readback/power recovery | Physical readback and controlled recovery evidence | **NOT TESTED** |

The passive command used was:

```sh
uv run --no-sync python tools/detect_devices.py --scan --json --explain
```

It exited 2 with both roles missing. No UPDI probe, firmware upload, fuse
operation, or RF transmission was attempted. Host tests, fake radios, register
fixtures, and parser validation are software evidence only; they do not count
as physical RF trials.

Before recording a physical PASS, preserve paired logs that show target
identity, firmware identity, packet semantics, CRC/decode outcome, ACK
acceptance, and timestamps for both endpoints. The exact pin and radio profile
reference is the [hardware pin audit](../../PIN_MAPPING_AUDIT.md); protocol
requirements and software tests are in the
[ACK/NACK guide](LORA_ACK_NACK.md). The configured receiver `BOOTSIZE=0` and
application start `0x0000` leave active BOOT/APPCODE pairing and FOTA
installation **BLOCKED** pending approved memory geometry and installer scope.
