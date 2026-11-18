// Exercises LoRa initialization, addressed frames, asynchronous TX completion,
// and bounded RX reads.
#include <Arduino.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "lora.h"

namespace fake_radio {
State state;
}
namespace fake_spi {
State state;
}
SPIClass SPI;
uint32_t host_ms;
void* operator new(size_t size) { return malloc(size); }

#define CHECK(c)                                           \
  do {                                                     \
    if (!(c)) {                                            \
      fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); \
      return EXIT_FAILURE;                                 \
    }                                                      \
  } while (0)

static void reset_radio() {
  fake_radio::state = {};
  SPI.reset();
}

int main() {
  reset_radio();
  LoRa radio(PIN_PC3, PIN_PD2, PIN_PD0, PIN_PD3);
  CHECK(radio.init(0, 915.0f, 2, 0) == 0);
  CHECK(radio.version() == 0x12);
  CHECK(fake_radio::state.frequency_mhz == 915.0f);
  CHECK(fake_radio::state.tx_power_dbm == 2);
  CHECK(fake_radio::state.spreading_factor == 7);
  CHECK(fake_radio::state.bandwidth_khz == 125.0f);
  CHECK(fake_radio::state.coding_rate == 5);
  CHECK(fake_radio::state.crc_enabled);
  CHECK(fake_radio::state.receive_starts == 1);
  CHECK(!radio.available());
  CHECK(radio.my_address() == 0);
  radio.set_my_address(7);
  CHECK(radio.my_address() == 7);
  radio.set_my_address(0);
  radio.set_power(5);
  CHECK(fake_radio::state.tx_power_dbm == 5);
  radio.set_frequency(868.0f);
  CHECK(fake_radio::state.frequency_mhz == 868.0f);
  CHECK(radio.sleep() == RADIOLIB_ERR_NONE);
  CHECK(fake_radio::state.sleep_calls == 1);
  CHECK(radio.init(0, 915.0f, 2, 0) == 0);
  CHECK(fake_radio::state.begin_calls == 2);
  CHECK(fake_radio::state.frequency_mhz == 915.0f);
  CHECK(fake_radio::state.tx_power_dbm == 2);

  const uint8_t data[] = {8, 1, 'h', 'e', 'l', 'l', 'o'};
  radio.send(1, data, sizeof(data));
  const uint8_t expected[] = {1, 0, 0, 0, 8, 1, 'h', 'e', 'l', 'l', 'o'};
  CHECK(fake_radio::state.tx_size == sizeof(expected));
  CHECK(memcmp(fake_radio::state.tx_copy, expected, sizeof(expected)) == 0);
  CHECK(!radio.send_done());
  fake_radio::state.sent_action();
  CHECK(radio.send_done());
  CHECK(fake_radio::state.receive_starts == 3);

  CHECK(radio.send(1, 0x1234, data, sizeof(data)) == RADIOLIB_ERR_NONE);
  CHECK(fake_radio::state.tx_copy[0] == 1 && fake_radio::state.tx_copy[1] == 0);
  CHECK(fake_radio::state.tx_copy[2] == 0x34 &&
        fake_radio::state.tx_copy[3] == 0x12);
  fake_radio::state.sent_action();
  CHECK(radio.send_done());

  reset_radio();
  LoRa receiver(PIN_PD0, PIN_PD3, PIN_PD1, PIN_PD2);
  CHECK(receiver.init(1, 915.0f, 2, 0) == 0);
  uint8_t packet[255] = {1, 0, 0, 0};
  for (size_t i = 4; i < sizeof(packet); ++i) packet[i] = (uint8_t)i;
  memcpy(fake_radio::state.rx_data, packet, sizeof(packet));
  fake_radio::state.rx_size = sizeof(packet);
  fake_radio::state.received_action();
  CHECK(receiver.available());
  Address source = 0, destination = 0;
  uint8_t output[256] = {}, length = 0;
  CHECK(receiver.recv(&source, &destination, output, sizeof output, &length) ==
        0);
  CHECK(source == 0 && destination == 1);
  CHECK(length == 251 && output[250] == 254);
  CHECK(receiver.get_last_rssi() == -42);
  CHECK(!receiver.available());

  packet[2] = 0x34;
  packet[3] = 0x12;
  memcpy(fake_radio::state.rx_data, packet, sizeof(packet));
  fake_radio::state.rx_size = sizeof(packet);
  fake_radio::state.received_action();
  uint16_t campaign_id = 0;
  CHECK(receiver.recv(&source, &destination, &campaign_id, output,
                      sizeof output, &length) == 0);
  CHECK(campaign_id == 0x1234 && source == 0 && destination == 1);

  reset_radio();
  LoRa unreadable(PIN_PC3, PIN_PD2, PIN_PD0, PIN_PD3);
  fake_radio::state.chip_version = -9;
  CHECK(unreadable.init(0, 915.0f, 2, 0) == -9);
  CHECK(fake_radio::state.receive_starts == 0);

  puts(
      "PASS stable LoRa init, addressed DATA/ACK framing, TX completion and "
      "max RX payload");
  return EXIT_SUCCESS;
}
