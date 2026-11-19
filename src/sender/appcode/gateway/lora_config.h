/// @file
/// Validates the legacy eight-byte I2C radio configuration against generated
/// PHY.

#ifndef SENIOR_PROJECT_RCA_SRC_SENDER_LIB_LORA_CONFIG_H_
#define SENIOR_PROJECT_RCA_SRC_SENDER_LIB_LORA_CONFIG_H_

#include <hello_config.h>
#include <stdint.h>
#include <string.h>

#include "espcomm.h"

/// Holds the accepted local address after generated-PHY validation.
struct LoraConfig {
  uint8_t addr;  ///< Local wire address accepted from the I2C frame.
};

/// Validates the I2C radio profile and copies its local address.
///
/// The caller selects the CONFIG command first. Frequency, power and range
/// must match generated SSOT values; this function does not configure hardware.
///
/// @param input Borrowed I2C mailbox bytes; may be volatile.
/// @param length Number of available bytes, which must equal the frame size.
/// @param config Non-null output updated only after validation succeeds.
/// @return True when the frame has the expected shape and generated PHY.
static bool DecodeLoraConfig(const volatile uint8_t* input, uint8_t length,
                             LoraConfig* config) {
  if (input == nullptr || config == nullptr || length != kI2cConfigFrameBytes)
    return false;
  const uint32_t frequency_bits =
      static_cast<uint32_t>(input[kI2cConfigFrequencyOffset]) |
      (static_cast<uint32_t>(input[kI2cConfigFrequencyOffset + 1]) << 8) |
      (static_cast<uint32_t>(input[kI2cConfigFrequencyOffset + 2]) << 16) |
      (static_cast<uint32_t>(input[kI2cConfigFrequencyOffset + 3]) << 24);
  float frequency = 0.0f;
  memcpy(&frequency, &frequency_bits, sizeof(frequency));
  if (frequency != HELLO_RF_FREQUENCY_MHZ ||
      static_cast<int8_t>(input[kI2cConfigTxPowerOffset]) !=
          HELLO_RF_TX_POWER_DBM ||
      input[kI2cConfigLongRangeOffset] != HELLO_RF_LONG_RANGE)
    return false;
  config->addr = input[kI2cConfigAddressOffset];
  return true;
}

#endif  // SENIOR_PROJECT_RCA_SRC_SENDER_LIB_LORA_CONFIG_H_
