// Minimal board, timing, and serial shim for raw-MVP host tests.
#ifndef SENIOR_PROJECT_RCA_TESTS_RAW_MVP_STUB_ARDUINO_H_
#define SENIOR_PROJECT_RCA_TESTS_RAW_MVP_STUB_ARDUINO_H_

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#define RADIO_STUB_EXTERNAL_MILLIS
#include "../radio_stub/Arduino.h"
#undef RADIO_STUB_EXTERNAL_MILLIS
#define PIN_PD5 25
#define PIN_PD6 26
#undef PIN_PA6
#undef PIN_PA5
#undef PIN_PA4
#define PIN_PA6 36
#define PIN_PA5 35
#define PIN_PA4 34
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define _PROTECTED_WRITE(reg, value) ((reg) = (value))
static struct {
  uint8_t CTRLA;
} CPUINT;
static uint8_t GPR_GPR0 = 4;
static uint8_t registers[2];
#define _SFR_MEM8(addr) registers[(addr) - 0x0f18]
static uint32_t clock_ms;
static uint32_t busy_until;
static bool monitor, input_pending;
static uint8_t input;
struct GpioWrite {
  int first;
  int second;
};
struct GpioLog {
  GpioWrite writes[32]{};
  size_t count = 0;
  GpioWrite* begin() { return writes; }
  GpioWrite* end() { return writes + count; }
  void push_back(GpioWrite write) {
    if (count < sizeof(writes) / sizeof(writes[0])) writes[count++] = write;
  }
};
static GpioLog gpio;
inline uint32_t millis() {
  if (busy_until && clock_ms >= busy_until) {
    registers[1] = 0;
    busy_until = 0;
  }
  return clock_ms++;
}
inline void delay(uint32_t ms) { clock_ms += ms; }
inline void digitalWrite(int pin, int value) { gpio.push_back({pin, value}); }
inline void pinMode(int, int) {}
inline char* ltoa(long value, char* text, int) {
  sprintf(text, "%ld", value);
  return text;
}

#endif  // SENIOR_PROJECT_RCA_TESTS_RAW_MVP_STUB_ARDUINO_H_
