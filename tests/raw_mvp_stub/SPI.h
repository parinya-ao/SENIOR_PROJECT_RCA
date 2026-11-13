#pragma once
#include "Arduino.h"
#define MSBFIRST 1
#define SPI_MODE0 0
#define SPI1_SWAP_DEFAULT 0x80
struct SPISettings {
    SPISettings(uint32_t speed, int order, int mode) {
        if (speed != 1000000 || order != MSBFIRST || mode != SPI_MODE0) __builtin_trap();
    }
};
static bool swapped, begun;
static uint8_t chip_version = 0x12;
struct SPIClass {
    bool swap(int route) { swapped = !begun && route == SPI1_SWAP_DEFAULT; return swapped; }
    void begin() { if (!swapped) __builtin_trap(); begun = true; }
    void beginTransaction(SPISettings) {}
    void endTransaction() {}
    uint8_t transfer(uint8_t) { return chip_version; }
};
static SPIClass SPI;
