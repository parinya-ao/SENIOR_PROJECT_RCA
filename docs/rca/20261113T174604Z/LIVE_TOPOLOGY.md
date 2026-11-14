# Live topology and SSOT mapping

The current hardware map and both board SSOT documents agree on static pins. Tracker: PC0/PC1/PC2 SPI, PD0 NSS, PD1 RESET, PD3 DIO0/IRQ, PD2 DIO1, PA7 active-low LoRa power. Gateway: PC0/PC1/PC2 SPI, PC3 NSS, PD0 RESET, PD2 DIO0/IRQ, PD3 DIO1; PA7 is address strap A0.

Normal ARQ assigns Tracker the receiver board role and Rudolph the sender role. Reverse-raw deliberately reverses radio function while retaining board mapping: `receiver_reverse_raw` is programmed to Tracker and compiled `LORA_ROLE_RECEIVER` (TX branch); `sender_reverse_raw` is programmed to Gateway and compiled `LORA_ROLE_SENDER` (RX branch). The original Incident A commands, device serials, source mapping, and raw event roles corroborate this. Static pin-map swap is rejected as the present leading explanation, while physical continuity is unmeasured.

Power: Tracker MCU base `3V3` and switched `3V3-LORA` are distinct; Q1 uses PA7 active-low. Gateway `3V3-LORA` is a shared main-board rail with no per-daughterboard power enable. The operator reports confidence in 3.3 V UPDI; no voltage amplitude or rail waveform was measured.

The +2 dBm ARQ profile and +10 dBm general RadioLib profile belong to distinct generated configurations. The ARQ manifest and SSOT validators pass read-only checks.
