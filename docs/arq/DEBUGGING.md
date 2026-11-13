# ARQ debugging

เริ่มจาก evidence อย่าเปลี่ยน timing แบบสุ่ม. `STATUS` replays startup,
build/config identity, counters, last result and RTT diagnostics.

| Symptom | Check |
| --- | --- |
| No command ACK | UPDI owner, mailbox connection, newline, bounded hex syntax; both boards must ARM same session |
| BOOT rc nonzero / ready=0 | RegVersion, SPI route generated from pin TOML, receiver power enable, PA_BOOST and RadioLib return codes |
| No DATA | Unarmed/stopped Sender, SEND syntax, one outstanding transaction, 3 s spacing |
| DATA but no ACK | CRC counter, exact case-sensitive Hello World, peer IDs/session/sequence, RX restoration, TX errors |
| REJECTED | Wrong application bytes; expected for H02; new session before another request |
| PROTOCOL_ERROR | Receiver expected sequence differs; do not force RF to change session; re-arm both with fresh session |
| TIMEOUT_EXHAUSTED | Five attempts maximum; inspect immutable DATA and exponential intervals; separate suppression from RF loss |
| Missing/partial lines | `overflow`, disconnected logger, UPDI byte readiness; trial invalid, protocol must still progress |
| Duplicate application delivery | Acceptance/dedup state lost by reset, or wrong payload-validation ordering; invalidate trial on reset |

`python tools/arq_trial.py --validate <bundle.json>` checks file integrity and
exchange completeness, not authenticity. Keep acquired bundles and simulated
fixtures separate. Raw logs alone are insufficient proof of physical RF.
Use full-memory snapshots before any recovery; never erase whole Flash or
alter fuses/BOOTSIZE/EEPROM to repair an ARQ test. Existing bounded application
writer is reused; no changes to UPDI programming protocol.

RTT is one MCU's TxDone-to-ACK interval, first attempts only. Compare sample
counts and local timestamps; never subtract Receiver and Sender clocks.
Power integrity has not been measured. Deduplication does not survive reset.

## UPDI register evidence

`REG`, `TX_STATE` and Sender `RX_STATE` contain bytes read directly over SPI,
in this address order (not a protocol frame):

`01 06 07 08 09 4D 1D 1E 26 39 33 3B 12 13 10 1B 40 11 18 31`.

| Offset | Register | Interpretation |
| --- | --- | --- |
| 0 | OpMode 01 | Bit 7 LoRa; mode bits 2:0 = 3 TX, 5 continuous RX |
| 1–3 | Frf 06–08 | E4 C0 00 = 915 MHz with 32 MHz reference |
| 4–5 | PA_CONFIG / PA_DAC | F0 / 84 = selected 2 dBm PA_BOOST profile |
| 6–11 | Modem1 / Modem2 / Modem3 / sync / IQ / IQ2 | 72 / 74 / 04 / 12 / 27 / 1D |
| 12 | IrqFlags 12 | RxDone 40; payload CRC error 20; TxDone 08 |
| 13–15 | RxNbBytes / FIFO RX current / RSSI value | Raw receive/FIFO/noise observations |
| 16 | DioMapping1 40 | DIO0 bits 7:6 = 00 RxDone, 01 TxDone; IRQ polling does not require DIO interrupts |
| 17–19 | IrqFlagsMask / ModemStatus / DetectOptimize | Raw IRQ mask, modem activity, detector configuration |

`RX_READY rc=0` follows the actual `startReceive()` return. Compare local
TX_DONE → RX_READY/RX_STATE times to test the turnaround boundary. Consult the
[Semtech SX1276 datasheet](https://core-electronics.com.au/attachments/localcontent/SX1276_Datasheet_52573f9f913.pdf)
for register definitions. RegVersion does not prove the physical module's
frequency variant or its antenna connection.

Sender board schematic routes ANT to SMA through SB1 or U.FL through SB2;
an attached antenna also needs the corresponding bridge closed. See
[Gateway SSOT](../ssot/GATEWAY_SSOT.md). The operator confirmed approximately
one metre indoor separation on 2026-11-13. Later clarification supersedes
the earlier antenna assumption: installed connector, SB1/SB2 continuity,
antenna attachment and actual module/frequency marking are **PHYSICAL
INSPECTION REQUIRED**. BOM/schematic specify RFM95W; they do not verify the
populated module. Do not transmit again until the operator confirms inspection.
