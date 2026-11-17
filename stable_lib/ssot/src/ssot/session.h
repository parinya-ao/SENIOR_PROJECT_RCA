// Tracks campaign progress and duplicates in caller-owned foreground state.

#ifndef SENIOR_PROJECT_RCA_SRC_SSOT_SESSION_H_
#define SENIOR_PROJECT_RCA_SRC_SSOT_SESSION_H_
#include "codec.h"
namespace ssot {
// Represents campaign progress; keeps the original native integer
// representation.
enum class CampaignState { kIdle, kArmed, kRunning, kCompleted, kFailed };

// Tracks one foreground-only campaign. Initialize before use; never share with
// an ISR.
struct Campaign {
  uint8_t source;
  uint8_t destination;
  uint16_t campaign_id;
  uint8_t sequence;
  uint8_t attempts;
  CampaignState state;
  bool single_packet;
};

// Remembers all 256 byte-sized sequence values for one peer/session pair.
struct DuplicateTracker {
  uint8_t source;
  uint16_t campaign_id;
  bool initialized;
  uint8_t seen[32];
};

// Resets caller-owned campaign state; a null campaign is ignored.
void CampaignInit(Campaign* campaign, uint8_t source, uint8_t destination,
                  bool single_packet);
// Arms an idle campaign with its session; null or non-idle state fails.
bool CampaignArm(Campaign* campaign, uint16_t campaign_id);
// Starts an armed campaign; null or any other state fails.
bool CampaignStart(Campaign* campaign);
// Counts one attempt in a running campaign, within the configured retry budget.
// Null/non-running campaigns fail; RAM-only single-packet tests allow one
// attempt.
bool CampaignMarkSent(Campaign* campaign);
// Returns whether another attempt is allowed, marking exhausted campaigns
// failed. Null/non-running campaigns or campaigns with no sent attempt return
// false.
bool CampaignTimeout(Campaign* campaign);
// Advances only for a matching ACK after a sent attempt; rejects null
// arguments.
bool CampaignAcknowledge(Campaign* campaign, const Frame* frame);
// Applies the timeout/retry budget to a matching NACK; rejects null arguments.
bool CampaignReject(Campaign* campaign, const Frame* frame);
// Makes a nonterminal campaign fail; ignores null and preserves terminal
// states.
void CampaignFail(Campaign* campaign);
// Allows normal reception outside multi-packet campaigns; null returns false.
bool CampaignNormalReceptionEnabled(const Campaign* campaign);
// Hashes a null-terminated build marker deterministically; null returns zero.
uint32_t CampaignBuildId(const char* build_marker);
// Rounds the 1% duty interval up to whole milliseconds without 32-bit overflow.
uint32_t MinIntervalMsForOnePercent(uint32_t airtime_us);
// Clears the entire caller-owned tracker; null is ignored.
void DuplicateTrackerInit(DuplicateTracker* tracker);
// Returns whether this sequence was seen, then records it. Null returns false.
// A changed source/session clears the bitmap; no payload pointer is retained.
bool DuplicateTrackerObserve(DuplicateTracker* tracker, uint8_t source,
                             uint16_t campaign_id, uint8_t sequence);
// Clears remembered sequences and session validity; null is ignored.
void DuplicateTrackerReset(DuplicateTracker* tracker);
}  // namespace ssot
#endif  // SENIOR_PROJECT_RCA_SRC_SSOT_SESSION_H_
