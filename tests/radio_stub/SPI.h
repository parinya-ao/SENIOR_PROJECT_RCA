#pragma once

#include <stddef.h>
#include <stdint.h>

#define SPI1_SWAP_DEFAULT 0x80
#define LOW 0
#define HIGH 1
#define MSBFIRST 1
#define SPI_MODE0 0
#define RADIOLIB_DEFAULT_SPI_SETTINGS SPISettings(1000000, MSBFIRST, SPI_MODE0)

class SPISettings {
public:
    SPISettings(uint32_t, uint8_t, uint8_t) {}
};

namespace fake_spi {
struct State {
    bool swap_succeeds;
    bool initialized;
    bool cs_low_seen;
    bool cs_high_seen;
    uint8_t route;
    uint8_t version;
    uint8_t transfer_bytes[2];
    size_t transfer_count;
    size_t begin_count;
    size_t swap_count;
    uint32_t cs_pin;
};

extern State state;
}

class SPIClass {
public:
    bool swap(uint8_t route) {
        ++fake_spi::state.swap_count;
        if (fake_spi::state.initialized || !fake_spi::state.swap_succeeds) {
            return false;
        }
        fake_spi::state.route = route;
        return true;
    }

    void begin() {
        fake_spi::state.initialized = true;
        ++fake_spi::state.begin_count;
    }

    void beginTransaction(SPISettings) {}
    void endTransaction() {}

    uint8_t transfer(uint8_t value) {
        const size_t index = fake_spi::state.transfer_count++;
        if (index < sizeof(fake_spi::state.transfer_bytes)) {
            fake_spi::state.transfer_bytes[index] = value;
        }
        return index == 1 ? fake_spi::state.version : 0;
    }

    void reset() {
        fake_spi::state = fake_spi::State{};
        fake_spi::state.swap_succeeds = true;
        fake_spi::state.version = 0x12;
    }
};

extern SPIClass SPI;

inline void digitalWrite(uint32_t pin, uint8_t value) {
    if (value == LOW) {
        fake_spi::state.cs_pin = pin;
        fake_spi::state.cs_low_seen = true;
    } else if (value == HIGH) {
        fake_spi::state.cs_pin = pin;
        fake_spi::state.cs_high_seen = true;
    }
}
