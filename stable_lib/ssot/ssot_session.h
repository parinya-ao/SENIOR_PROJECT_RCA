// Tracks campaign progress and duplicates in caller-owned foreground state.

#ifndef SENIOR_PROJECT_RCA_SRC_SSOT_SESSION_H_
#define SENIOR_PROJECT_RCA_SRC_SSOT_SESSION_H_
#include "ssot_codec.h"
namespace ssot {
// Represents campaign progress; keeps the original native integer
// representation.
enum class CampaignState { kIdle, kArmed, kRunning, kCompleted, kFailed };

/// Tracks one foreground-only campaign. Initialize before use; never share with
/// an ISR.
struct Campaign {
  uint8_t source;        ///< Peer source address.
  uint8_t destination;   ///< Destination address.
  uint16_t campaign_id;  ///< Session identifier.
  uint8_t sequence;      ///< Current DATA sequence.
  uint8_t attempts;      ///< DATA attempts for the current sequence.
  CampaignState state;   ///< Current campaign phase.
  bool single_packet;    ///< Whether the campaign stops after one message.
};

/// Remembers all 256 byte-sized sequence values for one peer/session pair.
struct DuplicateTracker {
  uint8_t source;        ///< Peer source address.
  uint16_t campaign_id;  ///< Session identifier.
  bool initialized;      ///< Whether the source and campaign are bound.
  uint8_t seen[32];      ///< Bitmap indexed by the eight-bit sequence.
};

/// @brief Initializes caller-owned campaign state.
/// @param campaign Campaign state to reset; null is ignored.
/// @param source Local/source address.
/// @param destination Remote/destination address.
/// @param single_packet Whether completion of one sequence completes the
///   campaign.
void CampaignInit(Campaign* campaign, uint8_t source, uint8_t destination,
                  bool single_packet);
/// @brief Binds an idle campaign to a nonzero session identifier.
/// @param campaign Campaign to arm.
/// @param campaign_id Nonzero session identifier.
/// @return True if the campaign entered the armed state.
bool CampaignArm(Campaign* campaign, uint16_t campaign_id);
/// @brief Starts a campaign that is currently armed.
/// @param campaign Campaign to start.
/// @return True if the campaign entered the running state.
bool CampaignStart(Campaign* campaign);
/// @brief Records one DATA attempt within the configured retry budget.
/// @param campaign Running campaign to update.
/// @return True when the attempt is permitted; false for invalid state or an
///   exhausted retry budget. Single-packet RAM tests allow one attempt.
bool CampaignMarkSent(Campaign* campaign);
/// @brief Applies the retry budget after a DATA timeout.
/// @param campaign Running campaign whose last attempt timed out.
/// @return True when another attempt remains; false otherwise. Exhaustion
///   marks the campaign failed.
bool CampaignTimeout(Campaign* campaign);
/// @brief Advances a campaign after its matching ACK arrives.
/// @param campaign Campaign with an outstanding sent sequence.
/// @param frame Decoded ACK frame.
/// @return True when the ACK matches and campaign state advances.
bool CampaignAcknowledge(Campaign* campaign, const Frame* frame);
/// @brief Applies the retry budget after a matching NACK.
/// @param campaign Campaign with an outstanding sent sequence.
/// @param frame Decoded NACK frame.
/// @return True when the NACK matched and another attempt remains.
bool CampaignReject(Campaign* campaign, const Frame* frame);
/// @brief Marks a nonterminal campaign failed.
/// @param campaign Campaign to update; null is ignored.
/// @post Completed and already-failed campaigns remain unchanged.
void CampaignFail(Campaign* campaign);
/// @brief Reports whether normal receive handling is permitted.
/// @param campaign Campaign to inspect.
/// @return True outside a running multi-packet campaign.
bool CampaignNormalReceptionEnabled(const Campaign* campaign);
/// @brief Computes the protocol's deterministic build marker identifier.
/// @param build_marker Null-terminated marker string, or null.
/// @return Identifier derived from the string, or zero for null.
uint32_t CampaignBuildId(const char* build_marker);
/// @brief Computes the minimum one-percent duty-cycle interval.
/// @param airtime_us Packet airtime in microseconds.
/// @return Airtime interval rounded up to milliseconds without uint32 overflow.
uint32_t MinIntervalMsForOnePercent(uint32_t airtime_us);
/// @brief Clears duplicate history and session binding.
/// @param tracker Tracker to initialize; null is ignored.
void DuplicateTrackerInit(DuplicateTracker* tracker);
/// @brief Checks and records a sequence for one peer and campaign.
/// @param tracker Caller-owned duplicate history.
/// @param source DATA source address.
/// @param campaign_id DATA campaign identifier.
/// @param sequence DATA sequence number.
/// @return True if the sequence was already present; false otherwise or for a
///   null tracker. A changed peer/session clears the bitmap.
bool DuplicateTrackerObserve(DuplicateTracker* tracker, uint8_t source,
                             uint16_t campaign_id, uint8_t sequence);
/// @brief Clears remembered sequences and session validity.
/// @param tracker Tracker to reset; null is ignored.
void DuplicateTrackerReset(DuplicateTracker* tracker);
}  // namespace ssot
#endif  // SENIOR_PROJECT_RCA_SRC_SSOT_SESSION_H_
