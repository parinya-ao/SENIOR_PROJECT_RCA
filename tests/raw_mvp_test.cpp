// Runs the real MVP application through the composition root with host hardware
// stubs.
#define LORA_APP_MVP 1
#if defined(LORA_ROLE_RECEIVER)
#include "../src/receiver/appcode/main.cpp"
#else
#include "../src/sender/appcode/main.cpp"
#endif
#include "../stable_lib/mvp_app/mvp_app.cpp"

using namespace mvp_app;

int main() {
  onPreMain();
  setup();
  assert(ready && swapped && begun && !monitor);
  assert(stage_count >= 7 && reset_flags == 4);
#if defined(LORA_ROLE_RECEIVER)
  assert(!transmitting && tx_started == 0 && tx_starts == 0);
  auto off = gpio.end();
  auto sd = gpio.end();
  auto on = gpio.end();
  for (auto it = gpio.begin(); it != gpio.end(); ++it) {
    if (it->first == PIN_PA7 && it->second == HIGH && off == gpio.end())
      off = it;
    if (it->first == PIN_PC3 && it->second == HIGH && sd == gpio.end()) sd = it;
    if (it->first == PIN_PA7 && it->second == LOW && on == gpio.end()) on = it;
  }
  assert(off < on && sd < on);
  const size_t lengths[] = {0, 10, 11, 12, 33, 255};
  for (size_t length : lengths) {
    packet_length = length;
    memset(packet, 0, sizeof(packet));
    memcpy(packet, kPayload, kPayloadBytes);
    irq_flags = 0x40;
    const uint32_t old = matches;
    const int starts = rx_starts;
    loop();
    assert(matches == old + (length == 11));
    assert(rx_starts == starts + 1);
  }
  packet_length = 11;
  memcpy(packet, "hello world", 11);
  irq_flags = 0x40;
  loop();
  assert(matches == 1);
  memcpy(packet, kPayload, kPayloadBytes);
  data_status = RADIOLIB_ERR_CRC_MISMATCH;
  irq_flags = 0x60;
  loop();
  assert(matches == 1 && crc_errors == 1);
  data_status = -24;
  irq_flags = 0x40;
  loop();
  assert(matches == 1);
  data_status = 0;
  irq_flags = 0x40;
  rx_status = -1;
  loop();
  assert(!ready);
#else
  loop();
  assert(tx_starts == 1 && sent_length == 11 &&
         memcmp(sent, "Hello World", 11) == 0);
  irq_flags = 0x08;
  loop();
  assert(!transmitting && cleanups == 1);
  loop();
  assert(tx_starts == 1);
  clock_ms += 3000;
  loop();
  assert(transmitting && tx_starts == 2);
  clock_ms += 3000;
  loop();
  assert(!transmitting && cleanups == 2);
  input_pending = true;
  input = 'X';
  loop();
  clock_ms += 15000;
  loop();
  assert(stopped && tx_starts == 2);
  stopped = false;
  loop();
  irq_flags = 0x08;
  cleanup_status = -1;
  loop();
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
  loop();
  assert(clock_ms - before < 2000);
  debug_init();
  debug_write_float(-1.25f);
  assert(!log_ok);
  return 0;
}
