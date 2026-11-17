// License: No repository-wide license is declared.
// Existing rights and third-party notices are unchanged.
// Validates SSOT wire bytes, campaign transitions, command input, and duplicate
// tracking.

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "ssot/ssot.h"

static_assert(sizeof(ssot::CampaignState) == sizeof(int),
              "Preserve campaign state layout");

int main(void) {
  static const uint8_t expected[] = {0x01, 0x00, 0x34, 0x12, 0x08, 0x01,
                                     'h',  'e',  'l',  'l',  'o',  ' ',
                                     'w',  'o',  'r',  'l',  'd'};
  uint8_t frame[sizeof expected];
  size_t frame_size = 0U;

  assert(ssot::EncodeDataFrame(1U, 0U, 0x1234U, 1U, frame, sizeof frame,
                               &frame_size));
  assert(frame_size == sizeof expected);
  assert(memcmp(frame, expected, sizeof expected) == 0);

  static const uint8_t expected_ack[] = {0x00, 0x01, 0x34, 0x12, 0x03, 0x01};
  assert(ssot::EncodeAckFrame(0U, 1U, 0x1234U, 1U, frame, sizeof frame,
                              &frame_size));
  assert(frame_size == sizeof expected_ack);
  assert(memcmp(frame, expected_ack, sizeof expected_ack) == 0);
  frame_size = sizeof frame;
  assert(!ssot::EncodeAckFrame(0U, 1U, 0x1234U, 1U, frame,
                               sizeof expected_ack - 1U, &frame_size));
  assert(frame_size == 0U);

  static const uint8_t expected_data_payload[] = {
      0x08, 0x01, 'h', 'e', 'l', 'l', 'o', ' ', 'w', 'o', 'r', 'l', 'd'};
  static const uint8_t expected_ack_payload[] = {0x03, 0x01};
  static const uint8_t expected_nack_payload[] = {0x09, 0x01};
  uint8_t payload[ssot::kDataPayloadSize];
  size_t payload_size = 0U;
  assert(ssot::EncodeDataPayload(1U, payload, sizeof payload, &payload_size));
  assert(payload_size == sizeof expected_data_payload);
  assert(memcmp(payload, expected_data_payload, sizeof expected_data_payload) ==
         0);
  assert(ssot::EncodeAckPayload(1U, payload, sizeof payload, &payload_size));
  assert(payload_size == sizeof expected_ack_payload);
  assert(memcmp(payload, expected_ack_payload, sizeof expected_ack_payload) ==
         0);
  assert(ssot::EncodeNackPayload(1U, payload, sizeof payload, &payload_size));
  assert(payload_size == sizeof expected_nack_payload);
  assert(memcmp(payload, expected_nack_payload, sizeof expected_nack_payload) ==
         0);

  ssot::Frame decoded{};
  assert(ssot::DecodeFrame(expected, sizeof expected, &decoded));
  assert(decoded.destination == 1U && decoded.source == 0U);
  assert(decoded.campaign_id == 0x1234U && decoded.sequence == 1U);
  assert(decoded.type == 8U);
  assert(!ssot::DecodeFrame(expected, sizeof expected - 1U, &decoded));
  assert(ssot::DecodePayload(1U, 0U, 0x34U, 0x12U, expected + 4U,
                             sizeof expected - 4U, &decoded));
  assert(decoded.type == 8U && decoded.campaign_id == 0x1234U);
  assert(ssot::ReplyForData(1U, 0U, 0x34U, 0x12U, expected + 4U,
                            sizeof expected - 4U, 0x1234U, &decoded) == 3U);
  assert(decoded.type == 8U && decoded.sequence == 1U);
  assert(ssot::ReplyForData(1U, 0U, 0x34U, 0x12U, expected + 4U,
                            sizeof expected - 5U, 0x1234U, &decoded) == 9U);
  assert(ssot::ReplyForData(1U, 0U, 0x34U, 0x12U, expected + 4U,
                            sizeof expected - 4U, 0x1235U, &decoded) == 0U);

  const ssot::Frame correct_ack = {0U, 1U, 0x1234U, 3U, 1U};
  assert(ssot::AckMatches(&correct_ack, 1U, 0U, 0x1234U, 1U));
  assert(!ssot::AckMatches(&correct_ack, 1U, 0U, 0x1235U, 1U));

  ssot::Campaign campaign;
  ssot::CampaignInit(&campaign, 0U, 1U, true);
  assert(campaign.state == ssot::CampaignState::kIdle);
  assert(!ssot::CampaignNormalReceptionEnabled(&campaign));
  assert(ssot::CampaignArm(&campaign, 0x1234U));
  assert(!ssot::CampaignArm(&campaign, 0x1235U));
  assert(ssot::CampaignStart(&campaign));
  assert(ssot::CampaignMarkSent(&campaign));
  assert(!ssot::CampaignAcknowledge(&campaign, &decoded));
  assert(ssot::CampaignAcknowledge(&campaign, &correct_ack));
  assert(campaign.state == ssot::CampaignState::kCompleted &&
         campaign.sequence == 1U);
  assert(!ssot::CampaignMarkSent(&campaign));
  assert(!ssot::CampaignNormalReceptionEnabled(&campaign));

  ssot::Campaign retries;
  ssot::CampaignInit(&retries, 0U, 1U, false);
  assert(ssot::CampaignArm(&retries, 0x2001U));
  assert(ssot::CampaignStart(&retries));
  for (uint8_t attempt = 0U; attempt < ssot::kMaxAttempts; ++attempt) {
    assert(ssot::CampaignMarkSent(&retries));
    assert(ssot::CampaignTimeout(&retries) ==
           (attempt + 1U < ssot::kMaxAttempts));
  }
  assert(retries.state == ssot::CampaignState::kFailed);
  assert(ssot::CampaignNormalReceptionEnabled(&retries));

#if defined(HELLO_RAM_ONLY_TEST) && HELLO_RAM_ONLY_TEST
  ssot::Campaign ram_only;
  ssot::CampaignInit(&ram_only, 0U, 1U, true);
  assert(ssot::CampaignArm(&ram_only, 0x3001U));
  assert(ssot::CampaignStart(&ram_only));
  assert(ssot::CampaignMarkSent(&ram_only));
  assert(!ssot::CampaignMarkSent(&ram_only));
  assert(!ssot::CampaignTimeout(&ram_only));
  assert(ram_only.state == ssot::CampaignState::kFailed);
#endif

  assert(ssot::CampaignBuildId(nullptr) == 0U);
  assert(ssot::CampaignBuildId("sender build-a") != 0U);
  assert(ssot::CampaignBuildId("sender build-a") != UINT32_MAX);
  assert(ssot::CampaignBuildId("sender build-a") ==
         ssot::CampaignBuildId("sender build-a"));
  assert(ssot::CampaignBuildId("sender build-a") !=
         ssot::CampaignBuildId("sender build-b"));
  assert(ssot::MinIntervalMsForOnePercent(0U) == 0U);
  assert(ssot::MinIntervalMsForOnePercent(1U) == 1U);
  assert(ssot::MinIntervalMsForOnePercent(1000U) == 100U);
  assert(ssot::MinIntervalMsForOnePercent(1001U) == 101U);
  assert(ssot::MinIntervalMsForOnePercent(1000000U) == 100000U);

  ssot::DuplicateTracker duplicates;
  ssot::DuplicateTrackerInit(&duplicates);
  assert(!ssot::DuplicateTrackerObserve(&duplicates, 0U, 0x1234U, 1U));
  assert(ssot::DuplicateTrackerObserve(&duplicates, 0U, 0x1234U, 1U));
  assert(!ssot::DuplicateTrackerObserve(&duplicates, 0U, 0x1234U, 2U));
  assert(ssot::DuplicateTrackerObserve(&duplicates, 0U, 0x1234U, 1U));
  assert(!ssot::DuplicateTrackerObserve(&duplicates, 0U, 0x1235U, 1U));
  assert(!ssot::DuplicateTrackerObserve(&duplicates, 1U, 0x1235U, 1U));
  assert(!ssot::DuplicateTrackerObserve(&duplicates, 1U, 0x1235U, 255U));
  assert(ssot::DuplicateTrackerObserve(&duplicates, 1U, 0x1235U, 255U));
  ssot::DuplicateTrackerReset(&duplicates);
  assert(!ssot::DuplicateTrackerObserve(&duplicates, 1U, 0x1235U, 255U));

  ssot::ControlInput control;
  uint16_t session = 0U;
  ssot::ControlInputInit(&control, 'S');
  assert(!ssot::ControlInputFeed(&control, 'C', 0U, &session));
  assert(!ssot::ControlInputFeed(&control, 'S', 1U, &session));
  assert(!ssot::ControlInputFeed(&control, '1', 2U, &session));
  assert(!ssot::ControlInputFeed(&control, '2', 3U, &session));
  assert(!ssot::ControlInputFeed(&control, '3', 4U, &session));
  assert(ssot::ControlInputFeed(&control, '4', 5U, &session));
  assert(session == 0x1234U);
  assert(!ssot::ControlInputFeed(&control, 'S', 6U, &session));

  ssot::ControlInputInit(&control, 'S');
  assert(!ssot::ControlInputFeed(&control, 'S', 0U, &session));
  assert(!ssot::ControlInputFeed(&control, '1', 2000U, &session));
  assert(!ssot::ControlInputFeed(&control, '2', 2001U, &session));
  assert(!ssot::ControlInputFeed(&control, '3', 2002U, &session));
  assert(!ssot::ControlInputFeed(&control, '4', 2003U, &session));
  // A failed decode must leave the caller's last valid frame intact.
  decoded = correct_ack;
  assert(!ssot::DecodeFrame(nullptr, sizeof expected, &decoded));
  assert(memcmp(&decoded, &correct_ack, sizeof decoded) == 0);
  assert(!ssot::DecodeFrame(expected, sizeof expected, nullptr));
  frame_size = 99U;
  assert(!ssot::EncodeDataFrame(1U, 0U, 1U, 1U, nullptr, 0U, &frame_size));
  assert(frame_size == 0U);
  assert(!ssot::EncodeDataPayload(1U, payload, sizeof payload, nullptr));

  // The inter-byte deadline uses elapsed unsigned time across millis rollover.
  ssot::ControlInputInit(&control, 'S');
  assert(!ssot::ControlInputFeed(&control, 'S', UINT32_MAX - 2U, &session));
  assert(!ssot::ControlInputFeed(&control, '0', UINT32_MAX - 1U, &session));
  assert(!ssot::ControlInputFeed(&control, '0', UINT32_MAX, &session));
  assert(!ssot::ControlInputFeed(&control, '0', 0U, &session));
  assert(ssot::ControlInputFeed(&control, '1', 1U, &session));
  assert(session == 1U);
  puts("PASS C++ protocol tests");
  return 0;
}
