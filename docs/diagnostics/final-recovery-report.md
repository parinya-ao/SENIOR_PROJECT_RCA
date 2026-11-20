# รายงานสรุปการกู้คืน LoRa Gateway ↔ Tracker

## S — สถานการณ์

คอนโซลเดิมรับได้เฉพาะ payload `hello world`; ภาพหน้าจอแสดง ANSI/CSI-u ปะปนใน
terminal และสถานะอุปกรณ์เป็น `DISCONNECTED`. การตรวจแบบอ่านอย่างเดียวล่าสุดใช้
run ID `20261120T035313.464528Z` และยืนยัน MCU signature, serial และ fuse ของ
Gateway/Tracker ได้ แต่ยังไม่เปิด runtime monitor เพราะ Flash ไม่ตรงกับ build
ปัจจุบัน.

ค่า fuse ที่อ่านได้จากทั้งสองบอร์ดคือ
`0000f0ffffd2f80000ffffffffffffff`: `BOOTSIZE=0`, `CODESIZE=0`. สำหรับ
AVR128DA28 ค่านี้จัด Flash ทั้งหมดเป็น BOOT และไม่มี APPCODE; ผลคือ
`FUSE_LAYOUT_VALID` แต่ `FOTA_LAYOUT_NOT_READY`.

## T — งานที่ต้องทำ

ซ่อม CLI และ firmware interface ให้รับ UTF-8 แบบจำกัดขนาด, ส่งทีละ fragment
ด้วย `reliable::Transport` เดิม, รอ ACK ทุก fragment, รับ Tracker Echo DATA
จริงและ ACK กลับ, แยก byte match ออกจาก fuse/FOTA/runtime status, ใช้ device
registry และ event parser ร่วมกัน, และไม่แฟลชหรือส่ง RF โดยอัตโนมัติ.

## A — การดำเนินการ

### การตัดสินใจ

- ใช้ Typer/Rich/prompt-toolkit ที่ติดตั้งอยู่และคง entry point เดิม
  `python -m tools.lora_chat`.
- ใช้ `config/current_hardware.json` ผ่าน hardware registry แทนพอร์ตที่ฝังใน
  source; ใช้ UPDI monitor command pipe เดิม ไม่เขียน application bytes เข้า
  SerialUPDI โดยตรง.
- เพิ่มคำสั่ง firmware แบบ bounded `V`, `I`, `X<length><hex>` และ Echo ผ่าน
  `reliable::Transport`; ไม่เพิ่ม ARQ หรือ buffer ขนาดเต็มข้อความบน AVR.
- Byte readback, fuse compatibility, runtime identity และ FOTA readiness
  נשארים סיווגים נפרדים; BOOTSIZE 0 ไม่ถูกแปลงเป็น APPCODE.

### สิ่งที่เปลี่ยน

- เพิ่ม capability negotiation, UTF-8 encoding, host-side fragmentation,
  reassembly, ACK/NACK/timeout/retry accounting และ Echo verification ใน
  `tools/lora_chat/`.
- เพิ่ม `src/shared/protocol/interactive_command.h`, ACK-confirm ใน shared
  transport, Tracker validation/Echo และ bounded hex payload logs.
- รวม event-line parsing, event names และ Gateway/Tracker role ไว้ใน
  `tools/device_detection/firmware_events.py` และ canonical device role.
- เปลี่ยน readback ให้รายงาน `FLASH_BYTES_MATCH/MISMATCH`, fuse status, FOTA
  status, runtime identity status, first mismatch address และ differing bytes.
- ย้าย receiver snapshot/monitor port lookup ไปที่ hardware registry; เพิ่ม
  pytest discovery scope เป็น `tests/` เพื่อไม่เก็บ archived tests ใต้
  `artifacts/`.
- เพิ่ม/ปรับ Typer, PTY, UTF-8, fragmentation, Echo, Flash-layout, SIB และ
  parser regression tests.

### ข้อแลกเปลี่ยนและความเสี่ยงที่เหลือ

`sender_hello` ยังคงเป็น legacy fixed-payload image. Interactive mode จะทำงาน
เฉพาะเมื่อ Gateway และ Tracker ที่รันอยู่ตอบ capability ตรงกัน. การ build
สำเร็จไม่ทำให้ image ที่ติดตั้งอยู่เปลี่ยนไป. ปัจจุบันทั้งสอง image ยังมี byte
mismatch และทั้งสองบอร์ดไม่มี APPCODE ตาม fuse; tool จึงหยุดก่อน monitor และ
ไม่พยายามเขียน BOOT.

## R — ผลการตรวจสอบ

### Software และ firmware build

| ตรวจสอบ | ผล |
|---|---|
| `uv run --no-sync pytest -q` | PASS — 490 passed, 5 skipped, 316 subtests |
| `uv run --no-sync ruff check tools tests` | PASS |
| `uv run --no-sync ruff format --check tools tests` | PASS — 27 files |
| `uv run --no-sync mypy` | PASS — 106 source files |
| `git diff --check` | PASS |
| `uv run --no-sync python -m tools.lora_chat --help` | PASS — exit 0, Typer options displayed |
| `uv run --no-sync python tools/config/generate_lora_config.py --prepare-build` | PASS |
| `pio run -e sender -e receiver -e sender_hello` | PASS — no upload/flash |

ขนาด linked image: `sender` RAM 9,652/16,384 bytes, Flash 44,562/131,072;
`receiver` RAM 4,677/16,384, Flash 38,648/131,072; `sender_hello` RAM
4,235/16,384, Flash 37,554/131,072.

### Hardware readback และ RF

run `artifacts/lora-chat/20261120T035313.464528Z/` ผ่าน target identity/fuse
checks; SIB ไม่มี part number จึงใช้ exact UPDI signature/serial readback เป็น
ตัวตัดสิน. ผลภาพ:

| Role | Serial | Image/build | Readback |
|---|---|---|---|
| Gateway | `42032240221023150129012600000000` | `sender`, build `87551c640fe4fb87fa866d8b5efbe50f17f9d98b0456c02bc67035f89b101abd` | `FLASH_BYTES_MISMATCH`, 43,554 bytes ต่าง, แรกสุด `0x0000` |
| Tracker | `42032240221092150158013400000000` | `receiver`, build `04c649c1e9c9f91207c65a7b056d302bcf5a25645f50341f1a8eb2894ed68e80` | `FLASH_BYTES_MISMATCH`, 37,253 bytes ต่าง, แรกสุด `0x001A` |

รายละเอียดรวมอยู่ใน
[`live-image-identities.json`](../../artifacts/lora-chat/20261120T035313.464528Z/preparation-84236744083904/live-image-identities.json),
[`target-identification.log`](../../artifacts/lora-chat/20261120T035313.464528Z/preparation-84236744083904/target-identification.log)
และ [`session.json`](../../artifacts/lora-chat/20261120T035313.464528Z/session.json).

คอนโซลจบที่ `APPLICATION_WRITE_PREFLIGHT` ด้วยข้อความว่า image mismatch
เตรียมแบบ application-only ไม่ได้ เพราะ BOOTSIZE=0; ไม่มีการเขียน Flash/fuse,
ไม่มี DATA TX, ไม่มี ACK/NACK/Echo และไม่มี runtime identity handshake.
session นี้บันทึก messages sent/received = 0, ACK/NACK = 0, retries = 0,
round trips = 0. `events.jsonl` มี host blocker เพียงหนึ่งรายการ และ
`messages.jsonl` ว่าง. ไม่มีค่า RTT ให้รายงาน.

หลักฐาน RF ทางกายภาพในอดีตจาก
[`sram-rf-20261119T141435.030695Z/summary.json`](../../artifacts/rf-debug/sram-rf-20261119T141435.030695Z/summary.json)
บันทึก legacy `hello world` DATA/ACK/NACK 20 trials: ACK 10, NACK 10,
34 attempts, 14 retries, 20 campaign IDs, ทั้งสองวิทยุ parked และไม่มี port
owner. หลักฐานนี้ไม่ทดสอบ Tracker Echo และไม่ใช่ HIL ของ source ปัจจุบัน.

### เกณฑ์ยอมรับ

| เกณฑ์ | สถานะ | เหตุผล |
|---|---|---|
| Gateway/Tracker source build | PASS | `sender`, `receiver`, `sender_hello` compile |
| Device identity | PASS | Signature/serial readback ตรงกับ registry |
| Fuse layout classification | PASS | ทั้งคู่ `FUSE_LAYOUT_VALID`; BOOTSIZE/CODESIZE ถูกอ่านจริง |
| Flash image verification | FAIL | มี byte mismatch ตาม address/count ด้านบน |
| FOTA/APPCODE readiness | BLOCKED | ทั้ง Flash เป็น BOOT; `FOTA_LAYOUT_NOT_READY` |
| Runtime identity | NOT RUN | Image mismatch หยุดก่อนเปิด monitor |
| Real Gateway ↔ Tracker Echo round trip | NOT RUN | ไม่มี DATA/ACK/Echo จาก run ปัจจุบัน |
| 10 consecutive current-image HIL transactions | BLOCKED | Firmware mismatch, BOOT-only layout, radio/antenna inventory ยัง null |
| Deterministic loss campaigns | NOT RUN as campaigns | Existing transport fault tests pass, แต่ไม่ได้รัน 10 seeded campaigns แยก |
| Clean shutdown / resource cleanup | PASS for startup run | `/quit` exit 0; ไม่ได้ acquire monitors หลัง image gate |

### ขั้นตอนถัดไป

ก่อน HIL ต้องมี recovery ที่ได้รับอนุญาตและปลอดภัยสำหรับ image mismatch ภายใต้
BOOTSIZE=0; application-only repair ใช้ไม่ได้และ tool จะไม่เขียน BOOT/fuse
แทน. จากนั้นต้องยืนยัน firmware capability `INTERACTIVE_CAPS`/`ECHO=1` บน
ทั้งสอง runtime, เติม radio/antenna inventory และรัน bounded RF test ที่มี
หลักฐานสองฝั่ง. จนถึงตอนนั้น Echo และ real round-trip ยังคง BLOCKED.

## ผลกระทบทางวิศวกรรม

การตรวจครั้งต่อไปแยกได้ทันทีว่า MCU identity/fuses ผ่าน แต่ image bytes ไม่ผ่าน
และ FOTA layout ไม่พร้อม. Shared parser/role/layout ลดโอกาสที่ CLI, RF stress
และ production tooling จะตีความ event, role หรือ page boundary คนละแบบ. ระบบ
ยังไม่อ้างความน่าเชื่อถือ RF เพิ่มขึ้นจาก host tests; ต้องรอ current-image HIL.
