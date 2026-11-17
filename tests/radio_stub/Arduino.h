// Minimal Arduino timing and interrupt shim for native LoRa wrapper tests.
#ifndef SENIOR_PROJECT_RCA_TESTS_RADIO_STUB_ARDUINO_H_
#define SENIOR_PROJECT_RCA_TESTS_RADIO_STUB_ARDUINO_H_

#include <stdint.h>
#define LOW 0
#define HIGH 1
#define INPUT 0
#define OUTPUT 1
#ifndef PIN_PA0
#define PIN_PA0 0
#endif
#ifndef PIN_PA1
#define PIN_PA1 1
#endif
#ifndef PIN_PA4
#define PIN_PA4 4
#endif
#ifndef PIN_PA5
#define PIN_PA5 5
#endif
#ifndef PIN_PA6
#define PIN_PA6 6
#endif
#define PIN_PA7 7
#define VREF_REFSEL_2V048_gc 0
#define ADC_PRESC_DIV4_gc 0
#define ADC_MUXPOS_TEMPSENSE_gc 0
#define ADC_INITDLY_DLY32_gc 0
#define ADC_ENABLE_bm 0
#define ADC_RESSEL_12BIT_gc 0
extern uint32_t host_ms;
#ifndef RADIO_STUB_EXTERNAL_MILLIS
inline uint32_t millis() { return host_ms; }
#endif

#ifndef PIN_PC0
#define PIN_PC0 10
#endif
#ifndef PIN_PC1
#define PIN_PC1 11
#endif
#ifndef PIN_PC2
#define PIN_PC2 12
#endif
#ifndef PIN_PC3
#define PIN_PC3 13
#endif
#ifndef PIN_PD0
#define PIN_PD0 20
#endif
#ifndef PIN_PD1
#define PIN_PD1 21
#endif
#ifndef PIN_PD2
#define PIN_PD2 22
#endif
#ifndef PIN_PD3
#define PIN_PD3 23
#endif
#ifndef PIN_PA7
#define PIN_PA7 37
#endif

#endif  // SENIOR_PROJECT_RCA_TESTS_RADIO_STUB_ARDUINO_H_
