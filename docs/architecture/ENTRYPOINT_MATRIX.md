# Entrypoint Matrix

Snapshot: `f0ca01554c156b2034ac29c304571ec7dcb02acb`, 2026-11-16. `platformio.ini` sets `lib_dir = stable_lib`, `default_envs = sender, receiver`, one shared `src/main.cpp`, and a source filter that currently selects only `main.cpp`. `generated/lora_platformio.ini` contains target-layout and flash-geometry values, not role environments. No explicit `lib_ldf_mode` is set. The pre-build script validates configuration and writes build identity only under `.pio/build/`.

| Environment(s) | App define | Active implementation | Role in the current matrix |
|---|---|---|---|
| `sender` | `LORA_APP_GATEWAY` | `stable_lib/gateway_app/` | Default Gateway; I2C command side plus LoRa DATA sender |
| `receiver`, `sender_hello`, `sender_hello_spi`, `sender_hello_5dbm`, `receiver_spi`, `receiver_5dbm` | `LORA_APP_RELIABLE` | `stable_lib/reliable_app/` | Reliable DATA/ACK sender or receiver; SPI/power variants retain this implementation |
| `sender_mvp`, `receiver_mvp` | `LORA_APP_MVP` | `stable_lib/mvp_app/` | MVP radio bring-up |
| `sender_arq`, `receiver_arq`, `sender_arq_test`, `receiver_arq_test`, `sender_arq_radio_only`, `receiver_arq_radio_only`, `sender_arq_radio_only_reverse`, `receiver_arq_radio_only_reverse` | `LORA_APP_ARQ` | `stable_lib/arq/src/arq/` | Separate ARQ diagnostic/protocol path |
| `sender_reverse_raw`, `receiver_reverse_raw` | `LORA_APP_REVERSE_RAW` | `stable_lib/reverse_raw_app/` | Reverse raw-radio diagnostic |

There are 19 role-bearing environments. `debug` and `release` are configuration bases and the pre-build script intentionally rejects them without a role. Legacy sender/receiver libraries are not selected by these supported environments.

The default sender and receiver builds compile successfully. A fresh compile-only run of all 19 role-bearing environments passed; the largest reported image used 38,988 bytes Flash and the largest static RAM use was 6,837 bytes. These are build measurements, not stack high-water or physical runtime evidence.
