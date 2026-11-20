/// @file
/// Defines logical ARQ fields and fixed wire limits; objects are never
/// serialized raw.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_FRAME_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_FRAME_H_
#include <stddef.h>
#include <stdint.h>

#include "generated/arq_config.h"
namespace arq {
/// Encoded header width in bytes.
inline constexpr size_t kHeaderBytes = 12;
/// Maximum bytes available to the application in one DATA frame.
inline constexpr size_t kMaxPayloadBytes = ARQ_PAYLOAD_LIMIT;
/// Buffer capacity required for the largest encoded frame.
inline constexpr size_t kMaxFrameBytes = kHeaderBytes + kMaxPayloadBytes;
/// DATA frame type on the wire.
inline constexpr uint8_t kData = 1;
/// Positive acknowledgment type on the wire.
inline constexpr uint8_t kAck = 2;
/// Negative acknowledgment type on the wire.
inline constexpr uint8_t kNack = 3;
/// Reason code for DATA and ACK.
inline constexpr uint8_t kNone = 0;
/// NACK reason for an unexpected DATA sequence.
inline constexpr uint8_t kUnexpectedSequence = 1;
/// NACK reason for DATA rejected by the receiver's payload policy.
inline constexpr uint8_t kApplicationRejected = 2;
/// NACK reason for transient receiver backpressure.
inline constexpr uint8_t kBusy = 3;
/// Holds decoded fields and at most 32 payload bytes; never serialize object
/// memory.
struct Frame {
  /// Logical DATA, ACK or NACK wire code.
  uint8_t type;
  /// Source node identity.
  uint8_t src;
  /// Destination node identity.
  uint8_t dst;
  /// Session ID correlated by the receiver and sender.
  uint32_t session;
  /// ARQ transaction sequence.
  uint16_t sequence;
  /// Number of valid payload bytes.
  uint8_t length;
  /// Rejection reason, or zero for DATA and ACK.
  uint8_t reason;
  /// Owned DATA storage. Only the first length bytes go on wire.
  uint8_t payload[kMaxPayloadBytes];
};
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_FRAME_H_
