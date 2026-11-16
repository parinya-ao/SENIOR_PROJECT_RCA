// No repository-wide license is declared; existing rights are unchanged.

// Defines logical ARQ fields and fixed wire limits; objects are never
// serialized raw.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_FRAME_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_FRAME_H_
#include <stddef.h>
#include <stdint.h>

#include "generated/arq_config.h"
namespace arq {
inline constexpr size_t kHeaderBytes = 12;
inline constexpr size_t kMaxPayloadBytes = ARQ_PAYLOAD_LIMIT;
inline constexpr size_t kMaxFrameBytes = kHeaderBytes + kMaxPayloadBytes;
// Wire values are fixed byte codes, independent of the typed local
// states below.
inline constexpr uint8_t kData = 1;
inline constexpr uint8_t kAck = 2;
inline constexpr uint8_t kNack = 3;
inline constexpr uint8_t kNone = 0;
inline constexpr uint8_t kUnexpectedSequence = 1;
inline constexpr uint8_t kApplicationRejected = 2;
inline constexpr uint8_t kBusy = 3;
// Holds decoded fields and at most 32 payload bytes; never serialize object
// memory.
struct Frame {
  uint8_t type;
  uint8_t src;
  uint8_t dst;
  uint32_t session;
  uint16_t sequence;
  uint8_t length;
  uint8_t reason;
  uint8_t payload[kMaxPayloadBytes];
};
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_FRAME_H_
