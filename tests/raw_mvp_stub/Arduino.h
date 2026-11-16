#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <vector>
#include <utility>
#define RADIO_STUB_EXTERNAL_MILLIS
#include "../radio_stub/Arduino.h"
#undef RADIO_STUB_EXTERNAL_MILLIS
#define PIN_PD5 25
#define PIN_PD6 26
#define PIN_PA6 36
#define PIN_PA5 35
#define PIN_PA4 34
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define _PROTECTED_WRITE(reg, value) ((reg) = (value))
static struct { uint8_t CTRLA; } CPUINT;
static uint8_t GPR_GPR0 = 4;
static uint8_t registers[2];
#define _SFR_MEM8(addr) registers[(addr) - 0x0f18]
static uint32_t clock_ms;
static uint32_t busy_until;
static bool monitor, input_pending;
static uint8_t input;
static std::vector<std::pair<int, int> > gpio;
inline uint32_t millis() {
    if (busy_until && clock_ms >= busy_until) { registers[1] = 0; busy_until = 0; }
    return clock_ms++;
}
inline void delay(uint32_t ms) { clock_ms += ms; }
inline void digitalWrite(int pin, int value) { gpio.push_back({pin, value}); }
inline void pinMode(int, int) {}
inline char* ltoa(long value, char* text, int) { sprintf(text, "%ld", value); return text; }
