// Exercises the real callback-to-cooperative-task command handoff.
#include <assert.h>
#include <inttypes.h>
#include <string.h>

#include "../src/sender/appcode/gateway/espcomm.cpp"

uint32_t host_ms = 0;
namespace fake_spi {
State state{};
}
SPIClass SPI;
void delay(unsigned) {}
namespace gateway_app {
iw::core::RingBuffer<application_config::gateway::kResultBufferBytes> ringbuf;
TaskScheduler scheduler;
int16_t current_temperature = 0;
}  // namespace gateway_app
static int configurations, rejections;
void InitializeRadio(Address address) {
  assert(address == LORA_SENDER_ADDRESS);
  ++configurations;
}
void RejectRadioConfiguration() { ++rejections; }
void StartRadioTransaction() {}
void StopRadio() {}

int main() {
  const float frequency = HELLO_RF_FREQUENCY_MHZ;
  Wire.input[0] = kI2cConfigLora;
  Wire.input[1] = LORA_SENDER_ADDRESS;
  memcpy(Wire.input + 2, &frequency, sizeof frequency);
  Wire.input[6] = HELLO_RF_TX_POWER_DBM;
  Wire.input[7] = HELLO_RF_LONG_RANGE;
  HandleReceive(8);
  assert(!is_ready);
  i2c_command_task.Run();
  assert(configurations == 1 && rejections == 0 && is_ready);
  Wire.offset = 0;
  HandleReceive(7);
  i2c_command_task.Run();
  assert(configurations == 1 && rejections == 1 && is_ready);
}
