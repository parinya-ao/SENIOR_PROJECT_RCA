// Implements the existing RadioHead-compatible DATA/ACK/NACK byte encoding.
#include "ssot_codec.h"

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

// Exact application bytes; the trailing C++ string terminator is never sent.
constexpr char kHelloPayload[] = LORA_HELLO_PAYLOAD;

static_assert(sizeof(kHelloPayload) - 1U == ssot::kHelloPayloadSize,
              "generated hello payload size mismatch");

namespace {

// Writes the four-byte RadioHead-compatible header into an already sized frame.
void EncodeHeader(uint8_t destination, uint8_t source, uint16_t campaign_id,
                  uint8_t* output) {
  output[0] = destination;
  output[1] = source;
  // Campaign IDs stay little-endian to preserve the existing wire format.
  output[2] = static_cast<uint8_t>(campaign_id & 0xffU);
  output[3] = static_cast<uint8_t>(campaign_id >> 8U);
}

}  // namespace

bool ssot::EncodeDataPayload(uint8_t sequence, uint8_t* output, size_t capacity,
                             size_t* output_size) {
  if (output_size == nullptr) {
    return false;
  }
  *output_size = 0U;
  if (output == nullptr || capacity < ssot::kDataPayloadSize) {
    return false;
  }

  output[0] = static_cast<uint8_t>(ssot::kDataType);
  output[1] = sequence;
  memcpy(output + 2U, kHelloPayload, ssot::kHelloPayloadSize);
  *output_size = ssot::kDataPayloadSize;
  return true;
}

namespace {

// Shares the two-byte control encoding without changing the packet type values.
bool EncodeControlPayload(uint8_t type, uint8_t sequence, uint8_t* output,
                          size_t capacity, size_t* output_size) {
  if (output_size == nullptr) {
    return false;
  }
  *output_size = 0U;
  if (output == nullptr || capacity < ssot::kAckPayloadSize) {
    return false;
  }

  output[0] = type;
  output[1] = sequence;
  *output_size = ssot::kAckPayloadSize;
  return true;
}

}  // namespace

bool ssot::EncodeAckPayload(uint8_t sequence, uint8_t* output, size_t capacity,
                            size_t* output_size) {
  return EncodeControlPayload(static_cast<uint8_t>(ssot::kAckType), sequence,
                              output, capacity, output_size);
}

bool ssot::EncodeNackPayload(uint8_t sequence, uint8_t* output, size_t capacity,
                             size_t* output_size) {
  return EncodeControlPayload(static_cast<uint8_t>(ssot::kNackType), sequence,
                              output, capacity, output_size);
}

bool ssot::EncodeDataFrame(uint8_t destination, uint8_t source,
                           uint16_t campaign_id, uint8_t sequence,
                           uint8_t* output, size_t capacity,
                           size_t* output_size) {
  if (output_size == nullptr) {
    return false;
  }
  *output_size = 0U;
  if (output == nullptr || capacity < ssot::kDataFrameSize) {
    return false;
  }

  EncodeHeader(destination, source, campaign_id, output);
  size_t payload_size = 0U;
  if (!ssot::EncodeDataPayload(sequence, output + ssot::kRadioHeaderSize,
                               capacity - ssot::kRadioHeaderSize,
                               &payload_size)) {
    return false;
  }
  *output_size = ssot::kRadioHeaderSize + payload_size;
  return true;
}

bool ssot::EncodeAckFrame(uint8_t destination, uint8_t source,
                          uint16_t campaign_id, uint8_t sequence,
                          uint8_t* output, size_t capacity,
                          size_t* output_size) {
  if (output_size == nullptr) {
    return false;
  }
  *output_size = 0U;
  if (output == nullptr || capacity < ssot::kAckFrameSize) {
    return false;
  }

  EncodeHeader(destination, source, campaign_id, output);
  size_t payload_size = 0U;
  if (!ssot::EncodeAckPayload(sequence, output + ssot::kRadioHeaderSize,
                              capacity - ssot::kRadioHeaderSize,
                              &payload_size)) {
    return false;
  }
  *output_size = ssot::kRadioHeaderSize + payload_size;
  return true;
}

namespace {

// Validates the full payload before publishing any fields to the caller.
bool DecodePayloadFields(uint8_t destination, uint8_t source, uint8_t id,
                         uint8_t flags, const uint8_t* payload,
                         size_t payload_size, ssot::Frame* frame) {
  if (payload == nullptr || frame == nullptr || payload_size < 1U) {
    return false;
  }

  if (payload[0] == ssot::kDataType) {
    if (payload_size != ssot::kDataPayloadSize ||
        memcmp(payload + 2U, kHelloPayload, ssot::kHelloPayloadSize) != 0) {
      return false;
    }
  } else if (payload[0] == ssot::kAckType || payload[0] == ssot::kNackType) {
    if (payload_size != ssot::kAckPayloadSize) {
      return false;
    }
  } else {
    return false;
  }

  frame->destination = destination;
  frame->source = source;
  frame->campaign_id =
      static_cast<uint16_t>(id | (static_cast<uint32_t>(flags) << 8U));
  frame->type = payload[0];
  frame->sequence = payload[1];
  return true;
}

}  // namespace

bool ssot::DecodePayload(uint8_t destination, uint8_t source, uint8_t id,
                         uint8_t flags, const uint8_t* payload,
                         size_t payload_size, ssot::Frame* frame) {
  return DecodePayloadFields(destination, source, id, flags, payload,
                             payload_size, frame);
}

bool ssot::DecodeFrame(const uint8_t* input, size_t input_size,
                       ssot::Frame* frame) {
  if (input == nullptr || frame == nullptr ||
      input_size < ssot::kRadioHeaderSize + 1U) {
    return false;
  }
  return DecodePayloadFields(input[0], input[1], input[2], input[3],
                             input + ssot::kRadioHeaderSize,
                             input_size - ssot::kRadioHeaderSize, frame);
}

uint8_t ssot::ReplyForData(uint8_t destination, uint8_t source, uint8_t id,
                           uint8_t flags, const uint8_t* payload,
                           size_t payload_size, uint16_t session,
                           ssot::Frame* frame) {
  const uint16_t received =
      static_cast<uint16_t>(id | (static_cast<uint32_t>(flags) << 8U));
  if (session == 0U || received != session || source != ssot::kSenderAddress ||
      destination != ssot::kReceiverAddress || payload == nullptr ||
      payload_size < 2U || payload[0] != ssot::kDataType ||
      payload[1] != ssot::kSequence || frame == nullptr) {
    return 0U;
  }

  *frame = ssot::Frame{destination, source, session,
                       static_cast<uint8_t>(ssot::kDataType),
                       static_cast<uint8_t>(ssot::kSequence)};
  return DecodePayloadFields(destination, source, id, flags, payload,
                             payload_size, frame)
             ? static_cast<uint8_t>(ssot::kAckType)
             : static_cast<uint8_t>(ssot::kNackType);
}

bool ssot::AckMatches(const ssot::Frame* frame, uint8_t source,
                      uint8_t destination, uint16_t campaign_id,
                      uint8_t sequence) {
  return frame != nullptr && frame->type == ssot::kAckType &&
         frame->source == source && frame->destination == destination &&
         frame->campaign_id == campaign_id && frame->sequence == sequence;
}
