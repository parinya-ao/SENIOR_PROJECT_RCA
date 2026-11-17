# ใช้งาน Codex Goal — LoRa E2E Feature-Based

1. เปิด Codex ใน **repository ที่ต้องการแก้** (ไม่ใช่ reference repo) แล้วตรวจ `pwd` และ `git status`.
2. ต้องมี Codex CLI ที่รองรับ `/goal` (ตาม official docs: >= 0.128.0); ใช้ `codex --version` ตรวจ.
3. คัดลอกบรรทัดแรกของ `CODEX_GOAL.md` ที่ขึ้นต้นด้วย `/goal` ส่งเป็นข้อความใน Codex.
4. ส่งเนื้อหาที่เหลือทั้งหมดของ `CODEX_GOAL.md` เป็นคำสั่งประกอบใน thread เดิม. หาก Codex client รองรับ paste ข้อความยาวในคำสั่งเดียว จะส่งพร้อมกันก็ได้ แต่ห้ามละ Hard Constraints.
5. ให้ Codex ตรวจ/รวม `AGENTS_APPEND.md` กับ AGENTS.md เดิมตามความเหมาะสม และใช้ `GOAL_POLICY.toml` เป็น project-owned policy หากไม่มีของเดิม.
6. ห้ามเปิด `multi_agent = true` ใน `~/.codex/config.toml` หรือใช้ฟีเจอร์ parallel agents.
7. ติดตั้ง Graphify Local เมื่อจำเป็น: `uv tool install graphifyy`. จากนั้น `graphify --help`, `GRAPHIFY_BACKEND=none graphify extract . --code-only`, และ `graphify query "which code owns Sender Receiver DATA ACK?"`. ห้ามสมมติว่าโปรแกรมชื่อ `codegraph` เป็น CLI แบบใดโดยไม่ตรวจ `--help`.
8. สำหรับการส่งคลื่น RF จริง ให้ยืนยันความถี่/กำลังส่ง/หน้าที่ของอุปกรณ์/port ก่อนทดสอบ และอย่า upload firmware ลง BOOT/fuses.

## ความต่างระหว่าง Goal กับ config
`/goal` เป็นสถานะต่อเนื่องของ **Codex thread** ไม่ใช่ค่าที่ Codex อ่านจากไฟล์ `GOAL_POLICY.toml` โดยอัตโนมัติ. ไฟล์ TOML นี้เป็น template นโยบายของ repository เพื่อสร้าง runner/ตรวจ acceptance เท่านั้น.

## จุดที่ต้องพิสูจน์
- RadioLib SX127x `setNodeAddress` ใช้กับ FSK hardware filtering เท่านั้น ไม่ใช่ LoRa.
- Snapshot ของโปรเจกต์ถูก compress และลบ comments: อ่าน source ต้นฉบับก่อนตัดสินใจ.
- `src/main.cpp` ใน snapshot เรียก `firmware_app`; `lib_dir = stable_lib`; ต้องทำจริงเป็น production feature ไม่ใช่ dummy wrappers.
- หลักฐาน real radio ต้องมี log sender+receiver, git SHA, config, ports, TX→RX→ACK และ rejection สำหรับ destination ผิด.

## แหล่งอ้างอิง
- https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
- https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex
- https://google.github.io/styleguide/cppguide
- https://jgromes.github.io/RadioLib/class_s_x127x.html
- https://github.com/Graphify-Labs/graphify
- https://docs.platformio.org/en/stable/projectconf/sections/platformio/options/directory/lib_dir.html
