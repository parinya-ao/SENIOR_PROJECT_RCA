#include <Arduino.h>
#include <RadioLib.h>

// Example pins: NSS, DIO1, RESET, BUSY
SX1262 radio = new Module(10, 2, 3, 9);

constexpr uint8_t packets[3][5] = {
    {0x00, 0x48, 0x65, 0x6C, 0x6C},
    {0x01, 0x6F, 0x20, 0x57, 0x6F},
    {0x02, 0x72, 0x6C, 0x64, 0x00},
};

void setup() {
    Serial.begin(9600);

    ConfigLoRa_t config;
    config.frequency = 922.0;
    config.bandwidth = 125.0;
    config.spreadingFactor = 7;
    config.codingRate = 5;

    // Configure TCXO/RF switch if required by hardware.
    const int state = radio.begin(config);

    if (state != RADIOLIB_ERR_NONE) {
        Serial.println("Radio init failed");
        while (true) {
            delay(1000);
        }
    }

    Serial.println("Sender ready");
}

void loop() {
    for (uint8_t i = 0; i < 3; ++i) {
        const int state = radio.transmit(
            packets[i], sizeof(packets[i]));

        if (state != RADIOLIB_ERR_NONE) {
            Serial.println("TX failed");
            break;
        }

        Serial.print("Sent packet ");
        Serial.println(i);

        delay(500);
    }

    // Send once for this experiment.
    while (true) {
        delay(1000);
    }
}
