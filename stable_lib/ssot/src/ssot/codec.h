// Defines and encodes the existing RadioHead-compatible SSOT wire format.

#ifndef SENIOR_PROJECT_RCA_SRC_SSOT_CODEC_H_
#define SENIOR_PROJECT_RCA_SRC_SSOT_CODEC_H_
#include <stddef.h>
#include <stdint.h>

#include "generated/lora_shared_config.h"
namespace ssot {
// Generated wire constants remain separate from native state
// representation.
inline constexpr size_t kRadioHeaderSize = 4U;
inline constexpr uint8_t kDataType = LORA_DATA_TYPE;
inline constexpr uint8_t kAckType = LORA_ACK_TYPE;
inline constexpr uint8_t kNackType = LORA_NACK_TYPE;
inline constexpr uint8_t kSenderAddress = LORA_SENDER_ADDRESS;
inline constexpr uint8_t kReceiverAddress = LORA_RECEIVER_ADDRESS;
inline constexpr uint8_t kSequence = LORA_SEQUENCE;
inline constexpr size_t kHelloPayloadSize = sizeof(LORA_HELLO_PAYLOAD) - 1U;
inline constexpr size_t kDataPayloadSize = 2U + kHelloPayloadSize;
inline constexpr size_t kAckPayloadSize = 2U;
inline constexpr size_t kDataFrameSize = kRadioHeaderSize + kDataPayloadSize;
inline constexpr size_t kAckFrameSize = kRadioHeaderSize + kAckPayloadSize;
inline constexpr uint8_t kMaxRetries = LORA_MAX_RETRIES;
inline constexpr uint8_t kMaxAttempts = 1U + kMaxRetries;

/// @param current Current wire campaign ID.
/// @return Successor campaign ID, skipping the unbound value zero.
inline constexpr uint16_t NextCampaignId(uint16_t current) {
  return current == UINT16_MAX ? 1 : static_cast<uint16_t>(current + 1U);
}

/// Holds decoded fields only; native object bytes are never used as a wire
/// frame.
struct Frame {
  uint8_t destination;   ///< Destination address.
  uint8_t source;        ///< Source address.
  uint16_t campaign_id;  ///< Transaction campaign identifier.
  uint8_t type;          ///< Wire packet type.
  uint8_t sequence;      ///< Wire sequence within the campaign.
};

// Encodes the existing DATA frame, including its four-byte header.
// Output and size pointers may be null (failure). Resets a non-null size to
// zero before validation; insufficient capacity leaves output bytes unchanged.
bool EncodeDataFrame(uint8_t destination, uint8_t source, uint16_t campaign_id,
                     uint8_t sequence, uint8_t* output, size_t capacity,
                     size_t* output_size);
// Writes type, sequence and exactly 11 application bytes without a terminator.
// Uses the same nullable output/size and capacity contract as the frame
// encoder.
bool EncodeDataPayload(uint8_t sequence, uint8_t* output, size_t capacity,
                       size_t* output_size);
// Writes the two-byte ACK payload; follows the DATA encoder output contract.
bool EncodeAckPayload(uint8_t sequence, uint8_t* output, size_t capacity,
                      size_t* output_size);
// Writes the two-byte NACK payload; follows the DATA encoder output contract.
bool EncodeNackPayload(uint8_t sequence, uint8_t* output, size_t capacity,
                       size_t* output_size);
// Writes the existing ACK frame; follows the DATA encoder output contract.
bool EncodeAckFrame(uint8_t destination, uint8_t source, uint16_t campaign_id,
                    uint8_t sequence, uint8_t* output, size_t capacity,
                    size_t* output_size);
// Validates an entire wire frame and overwrites frame only on success.
// Null input or frame fails; input must contain input_size readable bytes.
bool DecodeFrame(const uint8_t* input, size_t input_size, Frame* frame);
// Validates a header already separated by the radio HAL and its exact payload.
// Null payload/frame fails; leaves frame unchanged on failure. Retains no
// pointers.
bool DecodePayload(uint8_t destination, uint8_t source, uint8_t id,
                   uint8_t flags, const uint8_t* payload, size_t payload_size,
                   Frame* frame);
// Returns ACK/NACK type for this session, or zero for unrelated/invalid
// context. Null payload/frame returns zero. A matching DATA context populates
// frame even when malformed application bytes cause a NACK; session zero is
// never accepted.
uint8_t ReplyForData(uint8_t destination, uint8_t source, uint8_t id,
                     uint8_t flags, const uint8_t* payload, size_t payload_size,
                     uint16_t session, Frame* frame);
// Matches ACK type, both peers, campaign and sequence; a null frame never
// matches.
bool AckMatches(const Frame* frame, uint8_t source, uint8_t destination,
                uint16_t campaign_id, uint8_t sequence);
}  // namespace ssot
#endif  // SENIOR_PROJECT_RCA_SRC_SSOT_CODEC_H_
