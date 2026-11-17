// Minimal Arduino time and GPIO shim for native MVP role tests; it drives no
// physical pins.
#ifndef SENIOR_PROJECT_RCA_TESTS_MVP_STUB_ARDUINO_H_
#define SENIOR_PROJECT_RCA_TESTS_MVP_STUB_ARDUINO_H_

#include <SPI.h>
#include <stdint.h>

enum { INPUT = 0, OUTPUT = 1 };
#define VREF_REFSEL_2V048_gc 0
#define ADC_PRESC_DIV4_gc 0
#define ADC_MUXPOS_TEMPSENSE_gc 0
#define ADC_INITDLY_DLY32_gc 0
#define ADC_ENABLE_bm 0
#define ADC_RESSEL_12BIT_gc 0
enum {
  PIN_PA0 = 0,
  PIN_PA1 = 1,
  PIN_PA4 = 4,
  PIN_PA5 = 5,
  PIN_PA6 = 6,
  PIN_PA7 = 7,
  PIN_PC0 = 16,
  PIN_PC1 = 17,
  PIN_PC2 = 18,
  PIN_PC3 = 19,
  PIN_PD0 = 24,
  PIN_PD1 = 25,
  PIN_PD2 = 26,
  PIN_PD3 = 27,
  PIN_PD5 = 29,
  PIN_PD6 = 30,
};
extern uint32_t host_ms;
inline uint32_t millis() { return host_ms; }
inline uint32_t micros() { return host_ms * 1000U; }
void delay(unsigned ms);
inline void digitalWrite(uint8_t, uint8_t) {}
inline void pinMode(uint8_t, uint8_t) {}
inline void digitalWriteFast(uint8_t pin, uint8_t value) {
  digitalWrite(pin, value);
}
inline void pinModeFast(uint8_t, uint8_t) {}
struct CpuIntStub {
  uint8_t CTRLA;
};
[[maybe_unused]] inline CpuIntStub CPUINT{};
#define _PROTECTED_WRITE(reg, value) ((reg) = (value))

#endif  // SENIOR_PROJECT_RCA_TESTS_MVP_STUB_ARDUINO_H_
