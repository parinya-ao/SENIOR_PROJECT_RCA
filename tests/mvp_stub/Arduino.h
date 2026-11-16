#pragma once
#include <stdint.h>
#include <SPI.h>

enum { INPUT = 0, OUTPUT = 1 };
enum {
    PIN_PA0 = 0, PIN_PA1 = 1, PIN_PA4 = 4, PIN_PA5 = 5, PIN_PA6 = 6, PIN_PA7 = 7,
    PIN_PC0 = 16, PIN_PC1 = 17, PIN_PC2 = 18, PIN_PC3 = 19,
    PIN_PD0 = 24, PIN_PD1 = 25, PIN_PD2 = 26, PIN_PD3 = 27,
    PIN_PD5 = 29, PIN_PD6 = 30,
};
extern uint32_t host_ms;
inline uint32_t millis() { return host_ms; }
void delay(unsigned ms);
inline void digitalWriteFast(uint8_t pin, uint8_t value) { digitalWrite(pin, value); }
inline void pinModeFast(uint8_t, uint8_t) {}
struct CpuIntStub { uint8_t CTRLA; };
[[maybe_unused]] inline CpuIntStub CPUINT{};
#define _PROTECTED_WRITE(reg, value) ((reg) = (value))
