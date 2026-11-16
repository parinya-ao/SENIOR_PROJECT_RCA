// No repository-wide license is declared; existing rights are unchanged.

#include "session.h"

#include <string.h>

#include "application_config.h"

#ifndef HELLO_TEST_MODE
#define HELLO_TEST_MODE 0
#endif

#ifndef HELLO_RAM_ONLY_TEST
#define HELLO_RAM_ONLY_TEST 0
#endif

#if HELLO_RAM_ONLY_TEST && !HELLO_TEST_MODE
#error "RAM-only one-shot mode is restricted to the Hello test firmware."
#endif

namespace {
constexpr uint8_t kCampaignMessages =
    application_config::ssot::kCampaignMessages;
}
void ssot::CampaignInit(ssot::Campaign* campaign, uint8_t source,
                        uint8_t destination, bool single_packet) {
  if (campaign == nullptr) {
    return;
  }
  *campaign = ssot::Campaign{
      source,       destination, 0U, 1U, 0U, ssot::CampaignState::kIdle,
      single_packet};
}

bool ssot::CampaignArm(ssot::Campaign* campaign, uint16_t campaign_id) {
  if (campaign == nullptr || campaign->state != ssot::CampaignState::kIdle) {
    return false;
  }
  campaign->campaign_id = campaign_id;
  campaign->state = ssot::CampaignState::kArmed;
  return true;
}

bool ssot::CampaignStart(ssot::Campaign* campaign) {
  if (campaign == nullptr || campaign->state != ssot::CampaignState::kArmed) {
    return false;
  }
  if (campaign->sequence == 1U) {
    campaign->attempts = 0U;
  }
  campaign->state = ssot::CampaignState::kRunning;
  return true;
}

bool ssot::CampaignMarkSent(ssot::Campaign* campaign) {
  uint8_t max_attempts = static_cast<uint8_t>(ssot::kMaxAttempts);
  if (campaign == nullptr || campaign->state != ssot::CampaignState::kRunning) {
    return false;
  }
#if HELLO_RAM_ONLY_TEST
  if (campaign->single_packet) {
    max_attempts = 1U;
  }
#endif
  if (campaign->attempts >= max_attempts) {
    return false;
  }
  ++campaign->attempts;
  return true;
}

bool ssot::CampaignTimeout(ssot::Campaign* campaign) {
  uint8_t max_attempts = static_cast<uint8_t>(ssot::kMaxAttempts);
  if (campaign == nullptr || campaign->state != ssot::CampaignState::kRunning ||
      campaign->attempts == 0U) {
    return false;
  }
#if HELLO_RAM_ONLY_TEST
  if (campaign->single_packet) {
    max_attempts = 1U;
  }
#endif
  if (campaign->attempts >= max_attempts) {
    campaign->state = ssot::CampaignState::kFailed;
    return false;
  }
  return true;
}

bool ssot::CampaignAcknowledge(ssot::Campaign* campaign,
                               const ssot::Frame* frame) {
  if (campaign == nullptr || campaign->state != ssot::CampaignState::kRunning ||
      campaign->attempts == 0U ||
      !ssot::AckMatches(frame, campaign->destination, campaign->source,
                        campaign->campaign_id, campaign->sequence)) {
    return false;
  }
  if (campaign->single_packet) {
    campaign->state = ssot::CampaignState::kCompleted;
  } else if (campaign->sequence == 1U) {
    campaign->sequence = 2U;
    campaign->attempts = 0U;
    campaign->state = ssot::CampaignState::kArmed;
  } else if (campaign->sequence == kCampaignMessages) {
    campaign->state = ssot::CampaignState::kCompleted;
  } else {
    ++campaign->sequence;
    campaign->attempts = 0U;
  }
  return true;
}

bool ssot::CampaignReject(ssot::Campaign* campaign, const ssot::Frame* frame) {
  if (campaign == nullptr || frame == nullptr ||
      frame->type != ssot::kNackType ||
      campaign->state != ssot::CampaignState::kRunning ||
      campaign->attempts == 0U) {
    return false;
  }
  ssot::Frame ack = *frame;
  ack.type = static_cast<uint8_t>(ssot::kAckType);
  return ssot::AckMatches(&ack, campaign->destination, campaign->source,
                          campaign->campaign_id, campaign->sequence) &&
         ssot::CampaignTimeout(campaign);
}

void ssot::CampaignFail(ssot::Campaign* campaign) {
  if (campaign != nullptr &&
      (campaign->state == ssot::CampaignState::kIdle ||
       campaign->state == ssot::CampaignState::kArmed ||
       campaign->state == ssot::CampaignState::kRunning)) {
    campaign->state = ssot::CampaignState::kFailed;
  }
}

bool ssot::CampaignNormalReceptionEnabled(const ssot::Campaign* campaign) {
  return campaign != nullptr && !campaign->single_packet &&
         campaign->state != ssot::CampaignState::kArmed &&
         campaign->state != ssot::CampaignState::kRunning;
}

uint32_t ssot::CampaignBuildId(const char* build_marker) {
  if (build_marker == nullptr) {
    return 0U;
  }
  uint32_t hash = UINT32_C(2166136261);
  while (*build_marker != '\0') {
    hash ^= static_cast<uint8_t>(*build_marker++);
    hash *= UINT32_C(16777619);
  }
  if (hash == 0U || hash == UINT32_MAX) {
    --hash;
  }
  return hash;
}

uint32_t ssot::MinIntervalMsForOnePercent(uint32_t airtime_us) {
  const uint64_t interval_ms =
      (static_cast<uint64_t>(airtime_us) * 100U + 999U) / 1000U;
  return static_cast<uint32_t>(interval_ms);
}

void ssot::DuplicateTrackerInit(ssot::DuplicateTracker* tracker) {
  if (tracker != nullptr) {
    *tracker = {};
  }
}

void ssot::DuplicateTrackerReset(ssot::DuplicateTracker* tracker) {
  if (tracker != nullptr) {
    memset(tracker->seen, 0, sizeof tracker->seen);
    tracker->initialized = false;
  }
}

namespace {

// Starts a fresh sequence bitmap when the peer or session changes.
void ResetDuplicateSession(ssot::DuplicateTracker* tracker, uint8_t source,
                           uint16_t campaign_id) {
  memset(tracker->seen, 0, sizeof tracker->seen);
  tracker->source = source;
  tracker->campaign_id = campaign_id;
  tracker->initialized = true;
}

}  // namespace

bool ssot::DuplicateTrackerObserve(ssot::DuplicateTracker* tracker,
                                   uint8_t source, uint16_t campaign_id,
                                   uint8_t sequence) {
  if (tracker == nullptr) {
    return false;
  }
  if (!tracker->initialized || tracker->source != source ||
      tracker->campaign_id != campaign_id) {
    ResetDuplicateSession(tracker, source, campaign_id);
  }

  const uint8_t mask = static_cast<uint8_t>(1U << (sequence & 7U));
  uint8_t* byte = &tracker->seen[sequence >> 3U];
  const bool duplicate = (*byte & mask) != 0U;
  *byte = static_cast<uint8_t>(*byte | mask);
  return duplicate;
}
