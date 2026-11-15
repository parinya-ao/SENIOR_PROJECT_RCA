#pragma once
#include <stdint.h>
extern uint32_t host_ms;
inline uint32_t millis() { return host_ms; }

#define PIN_PC0 10
#define PIN_PC1 11
#define PIN_PC2 12
#define PIN_PC3 13
#define PIN_PD0 20
#define PIN_PD1 21
#define PIN_PD2 22
#define PIN_PD3 23
#define PIN_PA7 37
