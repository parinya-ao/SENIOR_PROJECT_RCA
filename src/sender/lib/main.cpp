// No repository-wide license is declared; existing rights are unchanged.

// Owns the gateway scheduler, ADC sampling and Arduino application lifecycle.

#include "main.h"

#include <Arduino.h>
#include <Wire.h>
#include <stdlib.h>

#include "application_config.h"
#include "debug.h"
#include "io.h"
#include "iw/avr128da28/adc.h"
#include "iw/avr128da28/provisioning.h"
#include "iw/core/ring_buffer.h"
#include "iw/tracker/radio/packets.h"
#include "role_log.h"

using namespace iw::tracker::radio;
#include "espcomm.h"
#include "hello_config.h"
#include "lora_rx.h"
#include "task.h"

#define PIN_LED1 PIN_PA5
#define PIN_LED2 PIN_PA4
#define A0 PIN_PA7
#define A1 PIN_PA6

// Result storage is static and bounded; host communication borrows it.
iw::core::RingBuffer<application_config::gateway::kResultBufferBytes> ringbuf;

// Borrows static tasks and advances them from the Arduino foreground loop.
TaskScheduler scheduler;
// Foreground ADC result exposed to the I2C command task in degrees Celsius.
int16_t current_temperature;
// Emits build identity once after a monitor becomes available.
static bool role_identity_logged = false;

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
  temp += 0x0800;        // Add 4096/2 to get correct rounding on division below
  temp >>= 12;  // Round off to nearest degree in Kelvin, by dividing with 2^12
                // (4096)
  return static_cast<int16_t>(temp - 273U);
}

/***********************************************
 *
 */
// Retains the disabled legacy LED task and its continuation timestamp.
class HeartbeatTask : public virtual Task {
 private:
  uint32_t timestamp_ms_;

 public:
  virtual const char* GetName() { return "Heartbeat"; }

  virtual TASK(Run()) {
    TASK_BEGIN();

    for (;;) {
      LED2_ON();
      TASK_DELAY(50, timestamp_ms_);
      LED2_OFF();
      TASK_DELAY(1950, timestamp_ms_);
    }
    TASK_END();
  }
} heartbeat_task;

// Initializes GPIO and ADC before registering communication/radio tasks.
void setup() {
  InitializeGpio();
  static_cast<void>(iw::avr128da28::InitializeAdc());
  Serial.begin(application_config::gateway::kUartBaud);
  pinMode(PIN_LED1, OUTPUT);
  pinMode(PIN_LED2, OUTPUT);
  pinMode(A0, INPUT);
  pinMode(A1, INPUT);
  DEBUG_TS("Start app.\r\n");

  // scheduler.Add(&heartbeat_task);
  InitializeEspCommunication();
  RegisterRadioTask();
#if HELLO_TEST_MODE
  StartHelloTestIfEnabled();
#endif
}

// Samples temperature and runs each cooperative task once; no new scheduling
// layer.
void loop() {
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
}
