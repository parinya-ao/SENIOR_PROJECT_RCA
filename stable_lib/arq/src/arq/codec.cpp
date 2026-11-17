// Encodes and decodes the bounded ARQ wire frame without radio access.
#include "codec.h"

#include <string.h>

namespace {
// ARQ has its own existing wire format, distinct from the SSOT DATA/ACK format.
constexpr uint8_t kWireVersion = 1;
constexpr size_t kHeaderSize = arq::kHeaderBytes;
constexpr size_t kPayloadCapacity = sizeof(arq::Frame::payload);
}  // namespace

bool arq::IsValidFrame(const arq::Frame* frame) {
  if (frame == nullptr || frame->length > kPayloadCapacity) {
    return false;
  }
  if (frame->type == arq::kData) {
    return frame->reason == arq::kNone;
  }
  if (frame->length != 0) {
    return false;
  }
  if (frame->type == arq::kAck) {
    return frame->reason == arq::kNone;
  }
  return frame->type == arq::kNack &&
         frame->reason >= arq::kUnexpectedSequence &&
         frame->reason <= arq::kBusy;
}

size_t arq::EncodeFrame(const arq::Frame* frame, uint8_t* output,
                        size_t capacity) {
  if (!arq::IsValidFrame(frame) || output == nullptr ||
      capacity < kHeaderSize + frame->length) {
    return 0;
  }
  output[0] = kWireVersion;
  output[1] = frame->type;
  output[2] = frame->src;
  output[3] = frame->dst;
  // Encode fields explicitly: native structure padding must never reach the
  // radio.
  for (uint8_t i = 0; i < 4; ++i) {
    output[4 + i] = static_cast<uint8_t>(frame->session >> (8U * i));
  }
  output[8] = static_cast<uint8_t>(frame->sequence);
  output[9] = static_cast<uint8_t>(frame->sequence >> 8U);
  output[10] = frame->length;
  output[11] = frame->reason;
  memcpy(output + kHeaderSize, frame->payload, frame->length);
  return kHeaderSize + frame->length;
}

bool arq::DecodeFrame(arq::Frame* frame, const uint8_t* input, size_t length) {
  if (frame == nullptr || input == nullptr || length < kHeaderSize ||
      length > kHeaderSize + kPayloadCapacity || input[0] != kWireVersion ||
      input[10] > kPayloadCapacity || length != kHeaderSize + input[10]) {
    return false;
  }
  arq::Frame value{};
  value.type = input[1];
  value.src = input[2];
  value.dst = input[3];
  for (uint8_t i = 0; i < 4; ++i) {
    value.session |= static_cast<uint32_t>(input[4 + i]) << (8U * i);
  }
  value.sequence =
      static_cast<uint16_t>(input[8] | (static_cast<uint32_t>(input[9]) << 8U));
  value.length = input[10];
  value.reason = input[11];
  if (!arq::IsValidFrame(&value)) {
    return false;
  }
  memcpy(value.payload, input + kHeaderSize, value.length);
  // Publish only after full validation, preserving the last decoded frame on
  // failure.
  *frame = value;
  return true;
}
