#ifndef SENIOR_PROJECT_RCA_SSOT_RADIO_HEADER_H_
#define SENIOR_PROJECT_RCA_SSOT_RADIO_HEADER_H_

#include <stddef.h>
#include <stdint.h>

namespace ssot {

constexpr size_t kRadioHeaderSize = 4U;

/// RadioHead-compatible fields preceding an addressed payload.
struct RadioHeader {
  uint8_t destination;   ///< Destination address.
  uint8_t source;        ///< Source address.
  uint16_t campaign_id;  ///< Little-endian campaign ID, including legacy zero.
};

/// @brief Writes a header into a buffer of at least kRadioHeaderSize bytes.
inline void EncodeRadioHeader(const RadioHeader& header, uint8_t* output) {
  output[0] = header.destination;
  output[1] = header.source;
  output[2] = static_cast<uint8_t>(header.campaign_id);
  output[3] = static_cast<uint8_t>(header.campaign_id >> 8U);
}

/// @brief Decodes a header from at least kRadioHeaderSize readable bytes.
inline RadioHeader DecodeRadioHeader(const uint8_t* input) {
  return {input[0], input[1],
          static_cast<uint16_t>(input[2] |
                                (static_cast<uint16_t>(input[3]) << 8U))};
}

}  // namespace ssot

#endif  // SENIOR_PROJECT_RCA_SSOT_RADIO_HEADER_H_
