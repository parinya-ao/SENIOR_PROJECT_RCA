# ARQ test plan

ทดสอบ host ก่อนเขียน Flash; RED logs อยู่ใน `artifacts/arq-development/`.

1. `python -m unittest discover -s tests -p test_arq.py`: literal wire bytes,
   truncated/oversized/unsupported frames, bounded buffers; matching controls,
   wrong peer/session/sequence, immutable retries, exponential intervals,
   repeated BUSY bound, terminal errors, sequence/time wrap, one outstanding;
   payload rejection, duplicate ACK and single delivery, old session discard.
2. Deterministic C fault harness: dropped DATA/ACK/NACK, incorrect controls,
   delayed ACK in BACKOFF, CRC-discard boundary, BUSY, local TX error.
   Portable logic executes under Clang ASan/UBSan and heap-symbol inspection.
3. Adapter assertion harness: both roles, unarmed boot, command bounds,
   ACK before retry at deadline, fault injection, response/RX cleanup,
   nonblocking mailbox and sixteen-slot overflow. Host fixtures are synthetic.
4. `pio run -e sender_arq -e receiver_arq -e sender_arq_test -e receiver_arq_test`.
   Inspect AVR linker static SRAM/Flash, compile project objects separately
   without LTO for `.su` reports (DxCore requires LTO in full firmware).
5. `python tools/arq_trial.py --campaign --rf-path-confirmed`: fresh UPDI identification,
   current-target serial/fuses check, bounded application-page erase/write,
   independent full-memory comparisons. Receiver USB port 1, Sender port 4.

| Gate | Required evidence |
| --- | --- |
| H01 | 23-byte Hello World DATA -> acceptance -> 12-byte matching ACK -> DELIVERED |
| H02 | Wrong World -> APPLICATION_REJECTED NACK -> REJECTED, one attempt |
| H03 | First ACK suppressed; byte-identical retry, duplicate replay, one delivery |
| H04 | Ten unique sequences; complete outcomes/counters |
| H05 | 100 messages, only after preceding gates pass; actual delivery and first-attempt rates |
| H06 | Separate 100-message session; suppress ten selected first ACK opportunities, replay duplicate ACKs |

Each gate uses a fresh monotonically reserved session. Bundle contains raw
UPDI streams, host command times, MCU-local event times, exact frames,
RSSI/SNR in hundredths, RTT samples and response counters, image/config hashes
and programming snapshots. Do not subtract clocks across devices. Injected
ACK suppression is not natural RF loss. Overflow, reset, missing terminal,
hash or preservation mismatch invalidates completeness and stops later gates.

After trials: raw-MVP physical regression, restore verified normal ARQ images,
Sender unarmed/idle. Run generator `--check` and relevant existing host tests.
Record unrelated transport/toolchain failures separately.

## Immediate commands after physical inspection

Software builds and standby preparation are safe before RF inspection:

```sh
python -m unittest discover -s tests -p test_arq.py
python tools/config/generate_lora_config.py
pio run -e sender_arq -e receiver_arq -e sender_arq_test -e receiver_arq_test
python tools/arq_trial.py --prepare
```

`--prepare` sends only X and STATUS, verifies both OpMode standby, and performs
no ARM/SEND. It programs only unarmed normal ARQ images through the existing
bounded writer; full snapshots independently check image/preserved memory.

Only after the operator confirms connector, correct SB1/SB2 selection,
antenna attachment and actual RF-module marking:

```sh
python tools/arq_trial.py --mvp --rf-path-confirmed
```

This executes one DATA→ACK (H01), then application NACK (H02), first-ACK
suppression/recovery (H03), and ten exchanges (H04), each with a fresh session.
Any failed gate stops subsequent gates. Normal unarmed standby firmware is
restored in the runner's finally path. `--campaign --rf-path-confirmed` retains
the original full sequential campaign including the separate 100-message trials.
Neither RF mode runs without the explicit inspection flag.
