// No repository-wide license is declared; existing rights are unchanged.

// Shares gateway scheduler and result storage across its cooperative tasks.

#include "application_config.h"
#ifndef SENIOR_PROJECT_RCA_SRC_SENDER_LIB_MAIN_H_
#define SENIOR_PROJECT_RCA_SRC_SENDER_LIB_MAIN_H_

#include "iw/core/ring_buffer.h"
#include "task.h"

// Reads calibrated MCU temperature; returns zero when ADC acquisition fails.
int16_t ReadTemperatureCelsius();

// Holds pending host result bytes; owned by the application for its lifetime.
extern iw::core::RingBuffer<application_config::gateway::kResultBufferBytes>
    ringbuf;
// Borrows static task objects; only the foreground loop advances them.
extern TaskScheduler scheduler;

#endif  // SENIOR_PROJECT_RCA_SRC_SENDER_LIB_MAIN_H_
