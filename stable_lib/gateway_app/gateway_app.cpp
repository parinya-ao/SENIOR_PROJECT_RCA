// Owns the gateway scheduler, ADC sampling and Arduino application lifecycle.

#include "gateway_app.h"

#include <Arduino.h>
#include <Wire.h>
#include <stdlib.h>

#include "application_config.h"
#include "debug.h"
#include "espcomm.h"
#include "hello_config.h"
#include "io.h"
#include "iw/avr128da28/adc.h"
#include "iw/avr128da28/provisioning.h"
#include "iw/core/ring_buffer.h"
#include "iw/tracker/radio/packets.h"
#include "lora_rx.h"
#include "role_log.h"
#include "status_leds.h"
#include "task.h"

namespace gateway_app {

using namespace iw::tracker::radio;

// Result storage is static and bounded; host communication borrows it.
iw::core::RingBuffer<GatewaySSOT::Memory::SHARED_RINGBUF_BYTES> ringbuf;

// Borrows static tasks and advances them from the Arduino foreground loop.
TaskScheduler scheduler;
// Foreground ADC result exposed to the I2C command task in degrees Celsius.
int16_t current_temperature;
// Emits build identity once after a monitor becomes available.
static bool role_identity_logged = false;
static status_leds::Controller led_status(
    GatewaySSOT::Pins::LED1, GatewaySSOT::Pins::LED2,
    GatewaySSOT::Pins::LED_ON_LEVEL, GatewaySSOT::Pins::LED_OFF_LEVEL,
    GatewaySSOT::Tasks::LED1_TOGGLE_INTERVAL_MS,
    GatewaySSOT::Tasks::LORA_TX_LED_TOGGLE_INTERVAL_MS);

/***********************************************
 *
 */
int16_t ReadTemperatureCelsius() {
  uint16_t raw_sample = 0U;
  if (iw::avr128da28::ReadTemperatureAdc(&raw_sample) !=
      iw::avr128da28::PlatformResult::kOk) {
    return 0;
  }
  uint16_t sigrow_slope = 0U;
  uint16_t sigrow_offset = 0U;
  (void)iw::avr128da28::ReadTemperatureCalibration(&sigrow_slope,
                                                   &sigrow_offset);

  uint32_t temp = sigrow_offset - raw_sample;
  temp *= sigrow_slope;  // Result will overflow 16-bit variable
  temp += GatewaySSOT::AdcTemp::ROUNDING_OFFSET;
  temp >>= GatewaySSOT::AdcTemp::FIXED_POINT_SHIFT;
  return static_cast<int16_t>(temp) - GatewaySSOT::AdcTemp::KELVIN_TO_CELSIUS;
}

/***********************************************
 *
 */
// Retains the disabled legacy LED task and its continuation timestamp.
class HeartbeatTask : public virtual Task {
 private:
  uint32_t timestamp_ms_;

 public:
  virtual const char* GetName() { return GatewaySSOT::Tasks::HEARTBEAT_NAME; }

  virtual TASK(Run()) {
    TASK_BEGIN();

    for (;;) {
      LED2_ON();
      TASK_DELAY(GatewaySSOT::Tasks::HEARTBEAT_ON_MS, timestamp_ms_);
      LED2_OFF();
      TASK_DELAY(GatewaySSOT::Tasks::HEARTBEAT_OFF_MS, timestamp_ms_);
    }
    TASK_END();
  }
} heartbeat_task;

// Initializes GPIO and ADC before registering communication/radio tasks.
void Initialize() {
  InitializeGpio();
  led_status.Begin(millis());
  static_cast<void>(iw::avr128da28::InitializeAdc());
  Serial.begin(GatewaySSOT::Comm::DEBUG_BAUD_RATE);
  pinMode(GatewaySSOT::Pins::ANALOG_IN_0, INPUT);
  pinMode(GatewaySSOT::Pins::ANALOG_IN_1, INPUT);
  DEBUG_TS("Start app.\r\n");

  if (GatewaySSOT::Tasks::ENABLE_HEARTBEAT_TASK) scheduler.Add(&heartbeat_task);
  if (GatewaySSOT::System::ENABLE_ESPCOMM && GatewaySSOT::Comm::ENABLE_I2C_WIRE)
    InitializeEspCommunication();
  if (GatewaySSOT::System::ENABLE_LORA_RX) RegisterRadioTask();
#if HELLO_TEST_MODE
  StartHelloTestIfEnabled();
#endif
}

// Samples temperature and runs each cooperative task once; no new scheduling
// layer.
void Poll() {
  if (!role_identity_logged && updi_uart_enabled()) {
#if HELLO_TEST_MODE
    updi_role_log_identity("SENDER", "sender_hello", __DATE__, __TIME__);
#else
    updi_role_log_identity("SENDER", "sender", __DATE__, __TIME__);
#endif
    role_identity_logged = true;
  }
  current_temperature = ReadTemperatureCelsius();
  scheduler.Loop();
  led_status.Poll(millis(), IsRadioTransmitting());
}

}  // namespace gateway_app
