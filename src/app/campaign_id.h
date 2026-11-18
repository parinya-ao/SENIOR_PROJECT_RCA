#ifndef SENIOR_PROJECT_RCA_SRC_APP_CAMPAIGN_ID_H_
#define SENIOR_PROJECT_RCA_SRC_APP_CAMPAIGN_ID_H_

#include <Arduino.h>
#include <ssot/ssot.h>
#include <stdint.h>

// Creates the runtime correlation identifier carried by reliable DATA/ACK.
namespace lora_app {

// Seeds the foreground campaign counter from the build identity and timer.
// Subsequent calls advance the counter, skipping zero.
// shortcut: 16-bit IDs can collide across resets or counter wrap, upgrade
// with retained state or a wider field when reset-safe uniqueness is needed.
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
