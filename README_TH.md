# เริ่มต้นใช้งานเฟิร์มแวร์ LoRa AVR128DA28

Gateway ทำหน้าที่ส่ง DATA ส่วน Tracker รับข้อมูล ตรวจที่อยู่และเนื้อหา แล้ว
ตอบ ACK หรือ NACK ตามโปรโตคอลที่มีอยู่. ภายในระบบมีการทดสอบหลายรูปแบบ
จึงควรดูชื่อ build environment และรูปแบบแพ็กเกตก่อนเปรียบเทียบผล.

## ค่าคลื่นวิทยุที่ตั้งไว้

ค่าหลักมาจาก config/radio_915.toml. คำอธิบายสั้น ๆ มีดังนี้.

| ค่า | ความหมาย |
|---|---|
| 915 MHz | ความถี่กลางที่ตั้งในโปรไฟล์ปัจจุบัน |
| BW 125 kHz | แบนด์วิดท์ของช่องสัญญาณ |
| SF7 | spreading factor ที่ใช้ในโปรไฟล์มาตรฐาน |
| coding rate 5 | ค่ารูปแบบ RadioLib สำหรับอัตรา 4/5 |
| sync word 0x12 | ช่วยแยกกลุ่มแพ็กเกตของระบบนี้ |
| TX 2 dBm | กำลังส่งที่ตั้งในโปรไฟล์ |
| preamble 8 symbols | ช่วงนำหน้าที่ช่วยให้ตัวรับตรวจจับแพ็กเกต |
| current limit 200 mA | ขีดจำกัดกระแสของภาคส่งตามค่าในโปรไฟล์ |
| automatic gain 0 | RadioLib ใช้ค่า 0 เพื่อเปิดวงจรควบคุม gain อัตโนมัติ |
| CRC เปิด, explicit header, IQ ไม่กลับด้าน | ตรวจความผิดพลาดและคงรูปแบบแพ็กเกตมาตรฐานของโปรเจกต์ |

ความหมายของ coding-rate denominator และ gain=0 ตรวจเทียบกับ
[RadioLib 7.1.2 SX1278 implementation](https://raw.githubusercontent.com/jgromes/RadioLib/7.1.2/src/modules/SX127x/SX1278.cpp).

SPI ใช้ SPI1_SWAP_DEFAULT ไปยัง PC0-PC3. โปรไฟล์ ARQ ระบุ clock 1 MHz
สำหรับ adapter นั้น ส่วน addressed RadioLib adapter ไม่ได้กำหนด clock ใน
radio profile และยังไม่ได้วัด clock จริงในบอร์ด.

อุปกรณ์สองบทบาทใช้ขา CS, RESET, IRQ และ DIO1 คนละชุด. ดู
[แผนผัง source](src/README.md), [ตารางขาและสถานะการตรวจสอบ](PIN_MAPPING_AUDIT.md),
[รายละเอียด ACK/NACK และผลทดสอบ](docs/testing/LORA_ACK_NACK.md),
[แผนผังสถาปัตยกรรมปัจจุบัน](docs/architecture/FINAL_ARCHITECTURE.md),
[ตาราง regression](docs/testing/REGRESSION_MATRIX.md),
[หลักฐานทดสอบ RF จริง](docs/testing/REAL_RADIO_EVIDENCE.md),
[Gateway SSOT](GATEWAY_SSOT.md) และ [Tracker SSOT](TRACKER_SSOT.md).

ผล build และ host test เป็นหลักฐานจากซอฟต์แวร์ ไม่ยืนยันว่าบอร์ดจริงรับส่ง RF
ได้. การทดสอบจริงต้องมีอุปกรณ์ที่ตรวจ identity แล้วและ log จากทั้งสองฝั่ง.

## ใช้งาน Codex Goal — LoRa E2E Feature-Based

1. เปิด Codex ใน **repository ที่ต้องการแก้** (ไม่ใช่ reference repo) แล้วตรวจ `pwd` และ `git status`.
2. ตรวจว่า Codex client ที่ใช้อยู่รองรับ native `/goal` แล้วตรวจสถานะว่า Goal ทำงานจริง. การมี TOML หรือ Markdown ไม่ได้ทำให้ Goal ใน thread เริ่มทำงานเอง.
3. คัดลอกบรรทัดแรกของ `CODEX_GOAL.md` ที่ขึ้นต้นด้วย `/goal` ส่งเป็นข้อความใน Codex.
4. ส่งเนื้อหาที่เหลือทั้งหมดของ `CODEX_GOAL.md` เป็นคำสั่งประกอบใน thread เดิม. หาก Codex client รองรับ paste ข้อความยาวในคำสั่งเดียว จะส่งพร้อมกันก็ได้ แต่ห้ามละ Hard Constraints.
5. ให้ Codex ตรวจ/รวม `AGENTS_APPEND.md` กับ AGENTS.md เดิมตามความเหมาะสม และใช้ `GOAL_POLICY.toml` เป็น project-owned policy หากไม่มีของเดิม.
6. ห้ามเปิด `multi_agent = true` ใน `~/.codex/config.toml` หรือใช้ฟีเจอร์ parallel agents.
7. หากมี graphify-out ให้ใช้ `graphify query` ก่อนค้นหรือเปิด source และใช้ `graphify update .` หลังแก้โค้ด. ใช้ CodeGraph เมื่อ repository มี index ที่ใช้งานได้. อย่าติดตั้งหรือสร้าง index ใหม่โดยไม่จำเป็น.
8. สำหรับการส่งคลื่น RF จริง ให้ยืนยันความถี่/กำลังส่ง/หน้าที่ของอุปกรณ์/port ก่อนทดสอบ และอย่า upload firmware ลง BOOT/fuses.

## ความต่างระหว่าง Goal กับ config
`/goal` เป็นสถานะต่อเนื่องของ **Codex thread** ไม่ใช่ค่าที่ Codex อ่านจากไฟล์ `GOAL_POLICY.toml` โดยอัตโนมัติ. ไฟล์ TOML นี้เป็น template นโยบายของ repository เพื่อสร้าง runner/ตรวจ acceptance เท่านั้น.

## จุดที่ต้องพิสูจน์
- RadioLib SX127x `setNodeAddress` ใช้กับ FSK hardware filtering เท่านั้น ไม่ใช่ LoRa.
- Snapshot ของโปรเจกต์ถูก compress และลบ comments: อ่าน source ต้นฉบับก่อนตัดสินใจ.
- Entry points ปัจจุบันอยู่ที่ `src/sender/appcode/main.cpp` และ `src/receiver/appcode/main.cpp`; `lib_dir = stable_lib`. ตรวจ platformio.ini และ source filters จาก checkout ปัจจุบันก่อนตัดสินใจ.
- หลักฐาน real radio ต้องมี log Sender+Receiver, git SHA, config, ports, TX→RX→ACK และ rejection สำหรับ destination ผิด. ดู [คู่มือ ACK/NACK และสถานะทดสอบ](docs/testing/LORA_ACK_NACK.md).

## แหล่งอ้างอิง
- https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
- https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex
- https://google.github.io/styleguide/cppguide
- https://jgromes.github.io/RadioLib/class_s_x127x.html
- https://github.com/Graphify-Labs/graphify
- https://docs.platformio.org/en/stable/projectconf/sections/platformio/options/directory/lib_dir.html
