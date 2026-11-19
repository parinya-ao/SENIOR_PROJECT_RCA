/// @file
/// Owns the gateway scheduler, ADC sampling and Arduino application lifecycle.

#include "gateway_app.h"

#include <Arduino.h>
#include <Wire.h>
#include <stdlib.h>

#include "application_config.h"
#include "avr128da28_adc.h"
#include "avr128da28_provisioning.h"
#include "debug.h"
#include "espcomm.h"
#include "hello_config.h"
#include "io.h"
#include "lora_rx.h"
#include "ring_buffer.h"
#include "status_leds.h"
#include "task.h"
#include "tracker_radio_packets.h"

namespace gateway_app {

using namespace iw::tracker::radio;

/// Bounded result storage borrowed by the host communication task.
iw::core::RingBuffer<GatewaySSOT::Memory::SHARED_RINGBUF_BYTES> ringbuf;

/// Scheduler invoked by the Arduino foreground loop; task objects are borrowed.
TaskScheduler scheduler;
/// Latest foreground temperature sample in degrees Celsius.
int16_t current_temperature;
static status_leds::Controller led_status(
    GatewaySSOT::Pins::LED1, GatewaySSOT::Pins::LED2,
    GatewaySSOT::Pins::LED_ON_LEVEL, GatewaySSOT::Pins::LED_OFF_LEVEL,
    GatewaySSOT::Tasks::LED1_TOGGLE_INTERVAL_MS,
    GatewaySSOT::Tasks::LORA_TX_LED_TOGGLE_INTERVAL_MS);

/// Reads the calibrated internal temperature sensor.
/// @return Temperature in degrees Celsius, or zero when ADC sampling fails.
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

/// Retains the disabled legacy heartbeat task and its continuation timestamp.
class HeartbeatTask : public virtual Task {
 private:
  uint32_t timestamp_ms_;  ///< Timestamp reused by the two heartbeat delays.

 public:
  /// @return Stable scheduler diagnostic name.
  virtual const char* GetName() { return GatewaySSOT::Tasks::HEARTBEAT_NAME; }

  /// Defines one bounded step of the legacy heartbeat sequence.
  /// @return Continuation status defined by the vendored PT_* macros.
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
} heartbeat_task;  ///< Disabled legacy heartbeat task retained for
                   ///< compatibility.

/// Initializes GPIO and ADC before registering enabled application tasks.
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

/// Samples temperature, advances the scheduler and updates status LEDs.
void Poll() {
  current_temperature = ReadTemperatureCelsius();
  PollRadioConsole();
  scheduler.Loop();
  led_status.Poll(millis(), IsRadioTransmitting());
}

}  // namespace gateway_app
