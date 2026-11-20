// Minimal deterministic Arduino timing, logging, and GPIO shim for ARQ tests.
#ifndef SENIOR_PROJECT_RCA_TESTS_ARQ_STUB_ARDUINO_H_
#define SENIOR_PROJECT_RCA_TESTS_ARQ_STUB_ARDUINO_H_

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#define RADIO_STUB_EXTERNAL_MILLIS
#include "../../radio_stub/Arduino.h"
#undef RADIO_STUB_EXTERNAL_MILLIS
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define PIN_PD4 24
#define PIN_PD5 25
#define PIN_PD6 26
#undef PIN_PA4
#undef PIN_PA5
#undef PIN_PA6
#define PIN_PA4 34
#define PIN_PA5 35
#define PIN_PA6 36
#define PIN_PF0 40
#define PIN_PF1 41
#define _PROTECTED_WRITE(reg, value) ((reg) = (value))
static struct {
  uint8_t CTRLA;
} CPUINT;
static uint8_t GPR_GPR0 = 4, registers[2];
#define _SFR_MEM8(addr) registers[(addr) - 0x0f18]
static uint32_t clock_ms;
static bool monitor, input_pending;
static struct {
  uint8_t CTRLA, CTRLB;
} USART2;
static int gpio_mode[64], gpio_value[64];
static bool sd_inserted;
static uint8_t input;
inline uint32_t millis() { return clock_ms++; }
inline uint32_t micros() { return clock_ms * 1000; }
inline void delay(uint32_t ms) { clock_ms += ms; }
inline void pinMode(int pin, int mode) { gpio_mode[pin] = mode; }
inline void digitalWrite(int pin, int value) {
#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC) && defined(LORA_ROLE_RECEIVER)
  if (pin == PIN_PD5 && value == HIGH) {
    if (USART2.CTRLA || USART2.CTRLB || gpio_mode[PIN_PF0] != INPUT ||
        gpio_mode[PIN_PF1] != INPUT || gpio_value[PIN_PF0] ||
        gpio_value[PIN_PF1])
      __builtin_trap();
  }
#endif
  gpio_value[pin] = value;
}
inline int digitalRead(int pin) {
  return pin == PIN_PA4 && sd_inserted ? LOW : HIGH;
}
inline void randomSeed(uint32_t) {}
inline long random(long limit) { return limit / 2; }

#endif  // SENIOR_PROJECT_RCA_TESTS_ARQ_STUB_ARDUINO_H_
