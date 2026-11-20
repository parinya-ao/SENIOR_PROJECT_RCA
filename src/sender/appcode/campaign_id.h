#ifndef SENIOR_PROJECT_RCA_SRC_APP_CAMPAIGN_ID_H_
#define SENIOR_PROJECT_RCA_SRC_APP_CAMPAIGN_ID_H_

#include <Arduino.h>
#include <ssot.h>
#include <stdint.h>

/// @file
/// @brief Generates runtime correlation identifiers for reliable DATA/ACK.
namespace lora_app {

/// @brief Generates the next runtime campaign identifier.
/// @param build_marker Null-terminated build marker used for initial seeding.
/// @return A nonzero 16-bit identifier that advances and skips zero.
/// @note The counter is foreground static state and is not reset-safe; IDs may
///   collide after a reset or full counter wrap.
inline uint16_t NextCampaignId(const char* build_marker) {
  static uint16_t previous = 0;
  if (previous == 0) {
    const uint32_t mixed = ssot::CampaignBuildId(build_marker) ^ micros();
    previous = static_cast<uint16_t>(mixed ^ (mixed >> 16U));
  }
  previous = ssot::NextCampaignId(previous);
  return previous;
}

}  // namespace lora_app
#endif  // SENIOR_PROJECT_RCA_SRC_APP_CAMPAIGN_ID_H_
