#pragma once

#include <stdint.h>
#include <string.h>

#include "../../shared/hello_config.h"

struct LoraConfig {
    uint8_t addr;
};

static bool DecodeLoraConfig(const volatile uint8_t* input, uint8_t length,
                             LoraConfig* config) {
    if (input == nullptr || config == nullptr || length != 8) return false;
    const uint32_t frequency_bits = static_cast<uint32_t>(input[2]) |
                                    (static_cast<uint32_t>(input[3]) << 8) |
                                    (static_cast<uint32_t>(input[4]) << 16) |
                                    (static_cast<uint32_t>(input[5]) << 24);
    float frequency = 0.0f;
    memcpy(&frequency, &frequency_bits, sizeof(frequency));
    if (frequency != HELLO_RF_FREQUENCY_MHZ ||
        static_cast<int8_t>(input[6]) != HELLO_RF_TX_POWER_DBM ||
        input[7] != HELLO_RF_LONG_RANGE) return false;
    config->addr = input[1];
    return true;
}
