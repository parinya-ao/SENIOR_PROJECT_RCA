// No repository-wide license is declared; existing rights are unchanged.

// Retains an excluded SX1262 experiment; current role targets do not compile
// it.

#if defined(LORA_APP_LEGACY_SENDER)

#include <Arduino.h>
#include <RadioLib.h>

#include "gateway_ssot.hpp"
#include "hello_config.h"
#include "legacy_sender.h"

namespace legacy_sender {

// Example pins: NSS, DIO1, RESET, BUSY
SX1262 radio = new Module(
    GatewaySSOT::ExcludedSx1262Experiment::NSS_PIN,
    GatewaySSOT::ExcludedSx1262Experiment::DIO1_PIN,
    GatewaySSOT::ExcludedSx1262Experiment::RESET_PIN,
    GatewaySSOT::ExcludedSx1262Experiment::BUSY_PIN);

constexpr uint8_t
    kPackets[GatewaySSOT::ExcludedSx1262Experiment::PACKET_COUNT]
            [GatewaySSOT::ExcludedSx1262Experiment::PACKET_BYTES] = {
    {0x00, 0x48, 0x65, 0x6C, 0x6C},
    {0x01, 0x6F, 0x20, 0x57, 0x6F},
    {0x02, 0x72, 0x6C, 0x64, 0x00},
};

void Initialize() {
  Serial.begin(GatewaySSOT::Comm::DEBUG_BAUD_RATE);

  ConfigLoRa_t config;
  config.frequency = HELLO_RF_FREQUENCY_MHZ;
  config.bandwidth = HELLO_RF_BANDWIDTH_KHZ;
  config.spreadingFactor = HELLO_RF_SPREADING_FACTOR;
  config.codingRate = HELLO_RF_CODING_RATE;

  // Configure TCXO/RF switch if required by hardware.
  const int state = radio.begin(config);

  if (state != RADIOLIB_ERR_NONE) {
    Serial.println("Radio init failed");
    while (true) {
      delay(GatewaySSOT::ExcludedSx1262Experiment::ERROR_RETRY_DELAY_MS);
    }
  }

  Serial.println("Sender ready");
}

void Poll() {
  for (uint8_t i = 0;
       i < GatewaySSOT::ExcludedSx1262Experiment::PACKET_COUNT; ++i) {
    const int state = radio.transmit(kPackets[i], sizeof(kPackets[i]));

    if (state != RADIOLIB_ERR_NONE) {
      Serial.println("TX failed");
      break;
    }

    Serial.print("Sent packet ");
    Serial.println(i);

    delay(GatewaySSOT::ExcludedSx1262Experiment::PACKET_GAP_MS);
  }

  // Send once for this experiment.
  while (true) {
    delay(GatewaySSOT::ExcludedSx1262Experiment::POST_SEND_DELAY_MS);
  }
}

}  // namespace legacy_sender

#endif  // LORA_APP_LEGACY_SENDER
