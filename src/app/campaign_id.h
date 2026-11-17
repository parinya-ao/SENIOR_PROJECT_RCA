#ifndef SENIOR_PROJECT_RCA_SRC_APP_CAMPAIGN_ID_H_
#define SENIOR_PROJECT_RCA_SRC_APP_CAMPAIGN_ID_H_

#include <Arduino.h>
#include <ssot/ssot.h>
#include <stdint.h>

// Creates the runtime correlation identifier carried by reliable DATA/ACK.
namespace lora_app {

// Returns a nonzero 16-bit ID for a new foreground session by mixing
// `build_marker` (the firmware build identity) with the MCU timer in
// microseconds. The marker is borrowed for this call; no allocation occurs.
// Function-local history adjusts an immediate collision, so call only from
// foreground code. This is correlation data, not authentication.
// shortcut: 16-bit IDs can collide across resets, upgrade with retained state
// or a wider field when reset-safe uniqueness is required.
inline uint16_t NextCampaignId(const char* build_marker) {
  static uint16_t previous = 0;
  const uint32_t mixed = ssot::CampaignBuildId(build_marker) ^ micros();
  uint16_t id = static_cast<uint16_t>(mixed ^ (mixed >> 16U));
  if (id == 0 || id == previous) {
    id = static_cast<uint16_t>(previous + 1U);
    if (id == 0) id = 1;
  }
  previous = id;
  return id;
}

}  // namespace lora_app
#endif  // SENIOR_PROJECT_RCA_SRC_APP_CAMPAIGN_ID_H_
