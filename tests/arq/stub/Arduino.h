#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include "../../radio_stub/Arduino.h"
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define _PROTECTED_WRITE(reg,value) ((reg)=(value))
static struct { uint8_t CTRLA; } CPUINT;
static uint8_t GPR_GPR0=4,registers[2];
#define _SFR_MEM8(addr) registers[(addr)-0x0f18]
static uint32_t clock_ms;
static bool monitor,input_pending;
static uint8_t input;
inline uint32_t millis(){return clock_ms++;}
inline uint32_t micros(){return clock_ms*1000;}
inline void delay(uint32_t ms){clock_ms+=ms;}
inline void pinMode(int,int){}
inline void digitalWrite(int,int){}
inline void randomSeed(uint32_t){}
inline long random(long limit){return limit/2;}
