#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_GATEWAY_APP_GATEWAY_APP_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_GATEWAY_APP_GATEWAY_APP_H_

#include <stdint.h>

#include "application_config.h"
#include "iw/core/ring_buffer.h"
#include "task.h"

// Owns Gateway startup and foreground scheduling state for the selected image.
namespace gateway_app {

// Configures board GPIO/ADC and registers the enabled host and radio tasks.
// Call once after Arduino initialization; hardware side effects occur here.
void Initialize();
// Advances one cooperative application step. Call regularly from the Arduino
// foreground loop; this function does not wait for host input.
void Poll();
// Returns the latest calibrated internal temperature in degrees Celsius, or
// zero when the ADC conversion fails.
int16_t ReadTemperatureCelsius();

// Static host-result storage; tasks borrow it for the lifetime of the image.
// Access it only from the cooperative foreground context.
extern iw::core::RingBuffer<application_config::gateway::kResultBufferBytes>
    ringbuf;
// Scheduler storage owned by this application and advanced only by Poll().
extern TaskScheduler scheduler;
// Latest temperature sample in degrees Celsius; initially zero.
extern int16_t current_temperature;

}  // namespace gateway_app

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_GATEWAY_APP_GATEWAY_APP_H_
