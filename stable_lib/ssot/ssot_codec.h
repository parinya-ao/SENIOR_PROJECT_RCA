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

/// @brief Returns the next nonzero campaign identifier.
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

/// @brief Encodes a DATA frame using the existing four-byte radio header.
/// @param destination Destination address written to the radio header.
/// @param source Source address written to the radio header.
/// @param campaign_id Nonzero campaign identifier written to the header.
/// @param sequence DATA sequence number.
/// @param output Writable destination buffer.
/// @param capacity Writable bytes available in `output`.
/// @param output_size Receives the encoded length, or zero on failure.
/// @return True when the frame was encoded; false for null pointers, invalid
///   fields, or insufficient capacity. Failure leaves output bytes unchanged.
bool EncodeDataFrame(uint8_t destination, uint8_t source, uint16_t campaign_id,
                     uint8_t sequence, uint8_t* output, size_t capacity,
                     size_t* output_size);
/// @brief Encodes the configured application payload without a terminator.
/// @param sequence DATA sequence number.
/// @param output Writable destination buffer.
/// @param capacity Writable bytes available in `output`.
/// @param output_size Receives the encoded length, or zero on failure.
/// @return True when type, sequence, and configured payload fit in the buffer.
bool EncodeDataPayload(uint8_t sequence, uint8_t* output, size_t capacity,
                       size_t* output_size);
/// @brief Encodes the two-byte ACK payload.
/// @param sequence Acknowledged DATA sequence.
/// @param output Writable destination buffer.
/// @param capacity Writable bytes available in `output`.
/// @param output_size Receives the encoded length, or zero on failure.
/// @return True when the ACK payload fits; false for invalid output arguments.
bool EncodeAckPayload(uint8_t sequence, uint8_t* output, size_t capacity,
                      size_t* output_size);
/// @brief Encodes the two-byte NACK payload.
/// @param sequence Rejected DATA sequence.
/// @param output Writable destination buffer.
/// @param capacity Writable bytes available in `output`.
/// @param output_size Receives the encoded length, or zero on failure.
/// @return True when the NACK payload fits; false for invalid output arguments.
bool EncodeNackPayload(uint8_t sequence, uint8_t* output, size_t capacity,
                       size_t* output_size);
/// @brief Encodes an ACK frame using the existing four-byte radio header.
/// @param destination Destination address written to the radio header.
/// @param source Source address written to the radio header.
/// @param campaign_id Campaign identifier belonging to the DATA transaction.
/// @param sequence Acknowledged DATA sequence.
/// @param output Writable destination buffer.
/// @param capacity Writable bytes available in `output`.
/// @param output_size Receives the encoded length, or zero on failure.
/// @return True on success; false on invalid fields, null pointers, or
///   insufficient capacity.
bool EncodeAckFrame(uint8_t destination, uint8_t source, uint16_t campaign_id,
                    uint8_t sequence, uint8_t* output, size_t capacity,
                    size_t* output_size);
/// @brief Validates and decodes the complete radio frame.
/// @param input Readable wire-frame bytes.
/// @param input_size Number of readable bytes in `input`.
/// @param frame Receives decoded fields only after full validation.
/// @return True for a valid frame; false for malformed input or null pointers.
bool DecodeFrame(const uint8_t* input, size_t input_size, Frame* frame);
/// @brief Validates a radio header and its separately received payload.
/// @param destination Destination address from the radio HAL.
/// @param source Source address from the radio HAL.
/// @param id Existing radio-header ID byte.
/// @param flags Existing radio-header flags byte.
/// @param payload Readable payload bytes.
/// @param payload_size Exact payload length.
/// @param frame Receives decoded fields only after full validation.
/// @return True for a valid frame; false on malformed input. No input pointers
///   are retained and `frame` is unchanged on failure.
bool DecodePayload(uint8_t destination, uint8_t source, uint8_t id,
                   uint8_t flags, const uint8_t* payload, size_t payload_size,
                   Frame* frame);
/// @brief Validates a DATA context and selects its ACK or NACK response.
/// @param destination Destination address from the radio HAL.
/// @param source Source address from the radio HAL.
/// @param id Existing radio-header ID byte.
/// @param flags Existing radio-header flags byte.
/// @param payload Readable DATA payload bytes.
/// @param payload_size Exact payload length.
/// @param session Expected nonzero campaign identifier.
/// @param frame Receives the decoded frame for a matching DATA context.
/// @return ACK or NACK type for a matching session, or zero for unrelated or
///   invalid context. A matching malformed application payload selects NACK.
uint8_t ReplyForData(uint8_t destination, uint8_t source, uint8_t id,
                     uint8_t flags, const uint8_t* payload, size_t payload_size,
                     uint16_t session, Frame* frame);
/// @brief Checks whether an ACK completes the specified DATA transaction.
/// @param frame Decoded control frame, or null.
/// @param source Expected ACK sender.
/// @param destination Expected ACK recipient.
/// @param campaign_id Expected campaign identifier.
/// @param sequence Outstanding DATA sequence.
/// @return True only when type, peers, campaign, and sequence all match.
bool AckMatches(const Frame* frame, uint8_t source, uint8_t destination,
                uint16_t campaign_id, uint8_t sequence);
}  // namespace ssot
#endif  // SENIOR_PROJECT_RCA_SRC_SSOT_CODEC_H_
