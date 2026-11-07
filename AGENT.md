# FIRMWARE MVP EXECUTION MODE

## Mission

Gateway = Sender. Tracker = Receiver.

Primary objective: run one real LoRa DATA/ACK exchange.

- DATA payload: `hello world`
- Payload length: 11 bytes
- DATA sequence: 1
- ACK type: 0x03
- ACK sequence: 1

## Execution Priority

1. Implement working firmware.
2. Identify physical target.
3. Deploy approved application firmware.
4. Verify real SPI.
5. Send real LoRa DATA.
6. Receive real LoRa ACK.
7. Report actual outcome.

Do not expand the mission into hardware certification, FOTA, SD storage, or production readiness.

## Stop Process Overhead

Do not create new STAR reports, plans, checklists, RCA documents, workflow state snapshots or technician handoffs.

Do not invoke optional planning or multi-agent workflows unless directly necessary for an identified technical failure.

Do not repeat completed builds or host tests without relevant source changes.

Do not ask for information the Project Owner has already provided.

Do not request third-party technician certification.

## Preserve SSOT

Never change or delete:

- `config/lora_system.json`
- `docs/ssot/GATEWAY_SSOT.md`
- `docs/ssot/TRACKER_SSOT.md`
- `include/generated/`
- `generated/lora_platformio.ini`

Preserve existing BOOT, BOD, fuses, EEPROM, firmware backups and protected memory.

## Hardware Scope

The Project Owner is responsible for the physical assembly.

Use existing evidence to determine whether the actual current setup supports safe target access.

Do not repeatedly treat historical BORF as proof of a new reset. Distinguish old observations from fresh ones.

If there is an unresolved electrical hazard, identify only the exact missing fact or correction rather than starting a full hardware investigation.

Never assume unknown wiring is safe.

## Deployment

Use the current verified RF-enabled firmware candidates.

Confirm the actual MCU identity and exact target/image/range before programming.

Require explicit authorization only for the precise firmware write that is necessary.

Use the existing application-only upload and readback procedure.

Do not use chip erase or modify protected regions.

## Physical Radio Execution

After safe target access and installation are established:

1. Verify both physical radios through SPI.
2. Start Tracker Receiver.
3. Wait for RX_READY.
4. Start Gateway Sender.
5. Transmit one 11-byte DATA frame.
6. Verify Tracker DATA_RX and payload match 11/11.
7. Verify Tracker ACK_TX.
8. Verify Gateway ACK_RX.
9. Stop after the completed exchange.

Do not use host simulation as evidence of physical RF.

## Output

Maximum five lines:

ACTION: Actual operation.
RESULT: Actual output.
FIRMWARE: PASS/FAIL.
PHYSICAL_RF: PASS/FAIL/NOT_RUN.
NEXT: One exact next action.

No documentation-only response.

Focus on implementation and execution.
