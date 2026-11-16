#include <cstdio>
#include <Arduino.h>
#include "lora.h"

namespace fake_radio { State state{}; }
namespace fake_spi { State state{}; }
SPIClass SPI;

int main() {
    SPI.reset();
    LoRa radio(PIN_PC3, PIN_PD2, PIN_PD0, PIN_PD3);
    if (!radio.init(0, 915.0f, 2, 0)) return 1;
    const uint8_t packet[] = {3, 1};
    radio.send(1, packet, sizeof(packet));
    if (fake_radio::state.tx_size != sizeof(packet) + 4) return 2;
    std::puts("PASS stable LoRa ACK payload transmit");
    return 0;
}
