#ifndef MAIN_H
#define MAIN_H

#include "iw/core/ring_buffer.h"
#include "task.h"

int16_t ReadTemperatureCelsius();

extern iw::core::RingBuffer<4096> ringbuf;
extern TaskScheduler scheduler;

#endif
