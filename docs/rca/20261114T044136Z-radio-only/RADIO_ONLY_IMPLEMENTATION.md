# LoRa-only diagnostic implementation

## Scope and baseline

Run `20261114T044136Z-radio-only`, repository HEAD `f8092bc70eae4d99d197427708b74ef19c11be13`, branch `fix/receiver-rfm-rev1-pins`. The run directory was created at 04:42:44 UTC; its identifier was reserved earlier during inspection. See [baseline](baseline.json), [initial dirty state](raw/git-status.txt) and [initial diff](raw/baseline.diff). Pre-existing work was retained. No commit was created.

The 915 MHz HF correction was already present in the dirty worktree. This continuation retains it and adds an isolated startup policy, tests and two build environments. The generated board implementation is updated through its generator.

## Build and restore

```bash
uv run pio run -e sender_arq_radio_only -e receiver_arq_radio_only
```

Both environments define `ARQ_RADIO_ONLY_DIAGNOSTIC=1` and inherit the existing ARQ test adapter. They remain unarmed and in standby at boot. `ARQ_TEST_MODE` permits the existing bounded ACK-suppression command; it does not create traffic automatically. Gateway uses Sender pins; Tracker uses Receiver pins.

Use the normal `sender_arq` / `receiver_arq` environments to omit this startup policy. Rebuild and independently verify the application image through the existing bounded application programming path after hardware preconditions are established. This run did not flash an image, so no on-device restore was necessary. Existing BOOT, fuses, EEPROM and identity were not programmed.

## Startup sequence

1. Preserve the existing core-saved reset cause in `reset_flags`.
2. On diagnostic Tracker only, disable USART2 interrupts/transceiver and release PF0/PF1 and GPS TIMEPULSE PD4 without pull-ups.
3. Command EN-GPS PD5 high. GNSS backup power is unchanged.
4. Leave nonessential LED pins PA5/PA6 as inputs without pull-ups; never use the core's PA7 `LED_BUILTIN` alias.
5. Release SD CS while removing SD power through PD6. Read the mechanical SD detect input PA4 with a pull-up.
6. If a card is detected, keep EN-LORA high and return before SPI/radio initialization. Report `SD_PRESENT_BLOCKED`, not a working radio.
7. With an empty socket, reuse generated board initialization: SD CS high, LoRa NSS high, PA7 low. Retain the existing 10 ms startup guard; it is not a measured rail-settling time.
8. Initialize the existing SPI1 route and RadioLib 7.1.2. Clear only RegOpMode bit 3 after successful `begin()`, propagate its readback-check error, and enter standby.
9. Reuse ARM, SEND, DATA/ACK/NACK, RX restoration and timeout handling unchanged.

The guard checks card presence at startup. The socket must remain empty throughout the experiment; hot insertion is unsupported. Mechanical detection cannot establish electrical isolation on a faulty or modified PCB.

## Source and test boundaries

- [Tracker policy](../../../src/arq/radio_only.h): startup-only helper, not a runtime peripheral manager.
- [ARQ setup and status](../../../src/arq/main.cpp): selected helper, retained HF correction, `RADIO_ONLY` status marker.
- [Board generator](../../../tools/config/arq_config.py): retains the diagnostic card-detect pull-up when generated initialization runs.
- [Environment selection](../../../tools/config/platformio_generate.py) and [PlatformIO environments](../../../platformio.ini).
- [Adapter boundary test](../../../tests/arq/adapter_test.cpp) executes the actual generated board initialization, with GPIO/radio electrical boundaries simulated.
- [Diagnostic test entry](../../../tests/test_arq_radio_only.py) runs both roles and the occupied-SD fail-closed case.
- [Installed-driver HAL test](../../../tests/radiolib_hal_test.cpp) executes actual RadioLib source against a modeled SPI device.

ARQ's source filter already excludes GPS acquisition, SD filesystem, tracking, IMU polling, EEPROM transactions and update tasks. Disabling them again would add unused code. No new library, protocol or peripheral scheduler was introduced.

## Existing protocol and evidence names

Keep the SSOT payload **`Hello World`**, 11 bytes, rather than adding `HELLO_LORA`, which the current receiver intentionally rejects. H02's negative payload is `Wrong World`. DATA is 23 bytes with the existing 12-byte header; ACK/NACK is 12 bytes. Application rejection, unexpected sequence and BUSY have defined NACK reasons. PHY CRC errors are discarded and RX is restored; they do not require an application NACK.

| Requested boundary | Existing evidence |
|---|---|
| Startup/reset/build | BOOT, IDENTITY, STATUS, RADIO_ONLY; saved GPIOR0 and RSTFR readouts |
| RX active | RX_READY return code plus RX_STATE/REG mode readback |
| DATA prepared / TX start | REQUEST and TX frame, TX_STATE register snapshot |
| Local TX completion | TX_DONE with IRQ bit 0x08; remote delivery still requires RX |
| RX / valid application bytes | RX_IRQ then RX bytes after driver CRC checking |
| Application acceptance/rejection | ACCEPT, DATA_DISCARD or response frame type/reason |
| ACK/NACK queued and transmitted | TX frame type 2/3, TX_STATE, then TX_DONE |
| ACK accepted / retry exhausted | DELIVERED, REJECTED, PROTOCOL_ERROR, TIMEOUT_EXHAUSTED |
| Return to RX / cleanup | RX_READY, RX_STATE; STANDBY/PARKED |

Event timestamps are local MCU clocks or Host receipt clocks. They are not synchronized RF measurements. The new marker does not claim rail voltages or packet delivery.
