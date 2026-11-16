#include <stdint.h>
#include <cstdio>
#include <cstring>

#include "stable_lib/gateway_app/lora_config.h"

int main() {
    uint8_t frame[9] = {4, 7, 0x00, 0xc0, 0x64, 0x44, 2, 0, 0};
    LoraConfig config{};
    if (!DecodeLoraConfig(frame, 8, &config) || config.addr != 7) return 1;
    if (DecodeLoraConfig(frame, 7, &config) ||
        DecodeLoraConfig(frame, 9, &config)) return 2;

    const float alternate_frequency = 923.0f;
    uint32_t bits = 0;
    std::memcpy(&bits, &alternate_frequency, sizeof(bits));
    frame[2] = static_cast<uint8_t>(bits);
    frame[3] = static_cast<uint8_t>(bits >> 8);
    frame[4] = static_cast<uint8_t>(bits >> 16);
    frame[5] = static_cast<uint8_t>(bits >> 24);
    if (DecodeLoraConfig(frame, 8, &config)) return 3;

    frame[2] = 0x00; frame[3] = 0xc0; frame[4] = 0x64; frame[5] = 0x44;
    frame[6] = 14;
    if (DecodeLoraConfig(frame, 8, &config)) return 4;
    frame[6] = 2;
    frame[7] = 1;
    if (DecodeLoraConfig(frame, 8, &config)) return 5;
    std::puts("PASS I2C radio profile checks");
    return 0;
}
