#include "lora.h"
#include <cstdio>

namespace fake_radio { State state{}; }
namespace fake_spi { State state{}; }
SPIClass SPI;

int main() {
    SPI.reset();
    LoRa radio;
    if (!radio.init(0)) return 1;
    const uint8_t payload = 8;
    if (radio.send(1, &payload, 1) == RADIOLIB_ERR_NONE) return 2;
    if (fake_radio::state.tx_size != 0) return 3;
    std::puts("PASS RF-disabled send protection");
    return 0;
}
