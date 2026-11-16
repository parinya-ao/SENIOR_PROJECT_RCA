#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_GATEWAY_APP_GATEWAY_APP_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_GATEWAY_APP_GATEWAY_APP_H_

#include <stdint.h>

#include "application_config.h"
#include "iw/core/ring_buffer.h"
#include "task.h"

namespace gateway_app {

void Initialize();
void Poll();
int16_t ReadTemperatureCelsius();

extern iw::core::RingBuffer<application_config::gateway::kResultBufferBytes>
    ringbuf;
extern TaskScheduler scheduler;
extern int16_t current_temperature;

}  // namespace gateway_app

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_GATEWAY_APP_GATEWAY_APP_H_
