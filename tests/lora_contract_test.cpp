// Verifies public LoRa wrapper overloads and the frozen RadioHead header shape.
#include <Arduino.h>
#include <assert.h>
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

int main() {
  SPI.reset();
  LoRa sender(PIN_PC3, PIN_PD2, PIN_PD0, PIN_PD3);
  assert(fake_radio::state.module_cs_pin == PIN_PC3);
  assert(fake_radio::state.module_irq_pin == PIN_PD2);
  assert(fake_radio::state.module_reset_pin == PIN_PD0);
  assert(fake_radio::state.module_dio1_pin == PIN_PD3);
  assert(sender.init(0, 915.0f, 2, 0) == 0);

  const uint8_t data[] = {8, 1, 'h', 'i'};
  sender.send(1, data, sizeof(data));
  const uint8_t expected[] = {1, 0, 0, 0, 8, 1, 'h', 'i'};
  assert(fake_radio::state.tx_size == sizeof(expected));
  assert(memcmp(fake_radio::state.tx_copy, expected, sizeof(expected)) == 0);
  assert(!sender.send_done());
  fake_radio::state.sent_action();
  assert(sender.send_done());

  LoRa receiver(PIN_PD0, PIN_PD3, PIN_PD1, PIN_PD2);
  assert(receiver.init(1, 915.0f, 2, 0) == 0);
  const uint8_t ack[] = {1, 0, 0, 0, 3, 1};
  memcpy(fake_radio::state.rx_data, ack, sizeof(ack));
  fake_radio::state.rx_size = sizeof(ack);
  fake_radio::state.received_action();
  assert(receiver.available());
  Address source = 0, destination = 0;
  uint8_t payload[256] = {}, length = 0;
  assert(receiver.recv(&source, &destination, payload, sizeof payload,
                       &length) == 0);
  assert(source == 0 && destination == 1);
  assert(length == 2 && payload[0] == 3 && payload[1] == 1);
  assert(!receiver.available());

  const uint8_t nack[] = {9, 1};
  const uint8_t expected_nack[] = {0, 1, 0x34, 0x12, 9, 1};
  assert(receiver.send(0, 0x1234, nack, sizeof nack) == 0);
  assert(fake_radio::state.tx_size == sizeof expected_nack);
  assert(
      !memcmp(fake_radio::state.tx_copy, expected_nack, sizeof expected_nack));
}
