#include <algorithm>

#include "../stable_lib/mvp_app/mvp_app.cpp"

int main() {
  onPreMain();
  mvp_app::Initialize();
  assert(ready && swapped && begun && !monitor);
  assert(stage_count >= 7 && reset_flags == 4);
#if defined(LORA_ROLE_RECEIVER)
  assert(!transmitting && tx_started == 0 && tx_starts == 0);
  auto off = std::find(gpio.begin(), gpio.end(), std::make_pair(PIN_PA7, HIGH));
  auto sd = std::find(gpio.begin(), gpio.end(), std::make_pair(PIN_PC3, HIGH));
  auto on = std::find(gpio.begin(), gpio.end(), std::make_pair(PIN_PA7, LOW));
  assert(off < on && sd < on);
  for (size_t length : {0, 10, 11, 12, 33, 255}) {
    packet_length = length;
    memset(packet, 0, sizeof(packet));
    memcpy(packet, kPayload, kPayloadBytes);
    irq_flags = 0x40;
    const uint32_t old = matches;
    const int starts = rx_starts;
    mvp_app::Poll();
    assert(matches == old + (length == 11));
    assert(rx_starts == starts + 1);
  }
  packet_length = 11;
  memcpy(packet, "hello world", 11);
  irq_flags = 0x40;
  mvp_app::Poll();
  assert(matches == 1);
  memcpy(packet, kPayload, kPayloadBytes);
  data_status = RADIOLIB_ERR_CRC_MISMATCH;
  irq_flags = 0x60;
  mvp_app::Poll();
  assert(matches == 1 && crc_errors == 1);
  data_status = -24;
  irq_flags = 0x40;
  mvp_app::Poll();
  assert(matches == 1);
  data_status = 0;
  irq_flags = 0x40;
  rx_status = -1;
  mvp_app::Poll();
  assert(!ready);
#else
  mvp_app::Poll();
  assert(tx_starts == 1 && sent_length == 11 &&
         memcmp(sent, "Hello World", 11) == 0);
  irq_flags = 0x08;
  mvp_app::Poll();
  assert(!transmitting && cleanups == 1);
  mvp_app::Poll();
  assert(tx_starts == 1);
  clock_ms += 3000;
  mvp_app::Poll();
  assert(transmitting && tx_starts == 2);
  clock_ms += 3000;
  mvp_app::Poll();
  assert(!transmitting && cleanups == 2);
  input_pending = true;
  input = 'X';
  mvp_app::Poll();
  clock_ms += 15000;
  mvp_app::Poll();
  assert(stopped && tx_starts == 2);
  stopped = false;
  mvp_app::Poll();
  irq_flags = 0x08;
  cleanup_status = -1;
  mvp_app::Poll();
  assert(!ready);
#endif
  monitor = true;
  registers[1] = 1;
  busy_until = clock_ms + 50;
  debug_init();
  debug_write("USB latency");
  assert(log_ok);
  registers[1] = 1;
  const uint32_t before = clock_ms;
  mvp_app::Poll();
  assert(clock_ms - before < 2000);
  debug_init();
  debug_write_float(-1.25f);
  assert(!log_ok);
  return 0;
}
