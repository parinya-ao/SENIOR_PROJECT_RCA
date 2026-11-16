# Tracker Configuration SSOT

`include/tracker_config.h` is the typed C++ source for the 17-field tracker
configuration, fixed firmware constants, diagnostic codes, validation, and
compile-time presets. It reads its radio frequency from the generated 915 MHz
profile; other frequencies fail `is_valid()`. Names and comments are English-only.

## Runtime settings

| Setting | Meaning |
|---|---|
| `lora_device_address` | This tracker's address; `0xFE` and `0xFF` are reserved. |
| `lora_gateway_address` | Gateway address; `0xFF` accepts any gateway. |
| `lora_freq` | LoRa frequency in MHz. |
| `lora_tx_power` | Normal-mode transmit power in dBm. |
| `long_range` | `0` for standard mode; `1` for long-range mode. |
| `collect_interval_day`, `collect_interval_night` | Day and night collection intervals in seconds. |
| `day_start_hour`, `day_end_hour` | Local-hour bounds for the daytime schedule; the end may be `24`. |
| `time_zone` | Whole-hour offset from UTC. |
| `gps_max_wait_for_fix` | Maximum GNSS fix wait in seconds. |
| `next_collect_no_fix` | Delay before retrying after a failed fix, in seconds. |
| `use_ack` | `1` waits for an ACK; `0` sends without ACK. |
| `ack_timeout` | Maximum ACK wait in seconds. |
| `tx_repeat` | Send count when ACK mode is disabled. |
| `total_slots`, `slot_interval` | TDMA slots per frame and seconds per slot. |

## Fixed settings and checks

`SystemConstants` groups storage addresses and sizes, ring-buffer sizes, SPI
ownership bits, maintenance radio settings, transmit-time estimates, serial
rates, GNSS timing, startup delays, error blink timing, coordinate sentinels,
LED polarity and blink timing, and battery ADC scaling. `ErrorCode` values are:
`1` SD init, `2` log partition,
`3` logger setup, `4` config partition, `5` config volume, `6` config file,
`7` data partition, `8` storage setup, and `9` LoRa init. `Checkpoint` values
mark invalid GNSS date (`1`), pre-SPI power (`20`), pre-LoRa init (`21`),
pre-GNSS power (`30`), and post-GNSS settling (`31`). Keep these values stable
when persisted diagnostics depend on them.

`TrackerConfig` computes its TDMA slot as `device_address % total_slots`, its
frame duration as `total_slots * slot_interval`, and an estimated transmit
budget from the ACK mode and range setting. `is_valid()` checks reserved
addresses, the generated frequency, collection intervals, schedule order, timezone,
boolean settings, TDMA sizes, and ACK/repeat requirements. Both presets are
checked at compile time for validity and slot budget. The struct is trivially
copyable, allowing `memcpy` between compatible builds; this does not define a
stable cross-version wire format.

LED1 toggles every 1000 ms. LED2 toggles every 100 ms only while DATA, ACK, or
NACK is being transmitted, then turns off.

The presets are `DEFAULT_THAILAND_CONFIG` and `FAST_BEACON_NO_ACK_CONFIG`. Both
use the active generated 915 MHz frequency.

## Scope

No runtime SD-card parser consumes `TrackerConfig` in this repository. Current
receiver firmware uses the generated profile and this header only for
compile-time LED settings. The radio remains configured by
`config/lora_system.json` and `config/radio_915.toml` at **915.000 MHz**.
