// Implements the canonical little-endian byte codec used by first-party wire
// and persistent formats.
#include "iw/core/byte_codec.h"

namespace iw::core {

uint16_t LoadLittleEndian16(const uint8_t* source) noexcept {
  return static_cast<uint16_t>(static_cast<uint16_t>(source[0]) |
                               (static_cast<uint16_t>(source[1]) << 8U));
}

uint32_t LoadLittleEndian32(const uint8_t* source) noexcept {
  return static_cast<uint32_t>(source[0]) |
         (static_cast<uint32_t>(source[1]) << 8U) |
         (static_cast<uint32_t>(source[2]) << 16U) |
         (static_cast<uint32_t>(source[3]) << 24U);
}

void StoreLittleEndian16(uint8_t* destination, uint16_t value) noexcept {
  destination[0] = static_cast<uint8_t>(value & 0xFFU);
  destination[1] = static_cast<uint8_t>((value >> 8U) & 0xFFU);
}

void StoreLittleEndian32(uint8_t* destination, uint32_t value) noexcept {
  destination[0] = static_cast<uint8_t>(value & 0xFFU);
  destination[1] = static_cast<uint8_t>((value >> 8U) & 0xFFU);
  destination[2] = static_cast<uint8_t>((value >> 16U) & 0xFFU);
  destination[3] = static_cast<uint8_t>((value >> 24U) & 0xFFU);
}

}  // namespace iw::core
