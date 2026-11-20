#ifndef IW_CORE_BYTE_CODEC_H_
#define IW_CORE_BYTE_CODEC_H_

// Declares the allocation-free little-endian codec shared by fixed formats.
#include <stdint.h>

namespace iw::core {

/// @brief Loads a little-endian 16-bit value from a fixed-format buffer.
/// @param source Caller-owned buffer with at least two readable bytes.
/// @return Value represented by the first two bytes.
/// @pre The caller has validated the input buffer length.
uint16_t LoadLittleEndian16(const uint8_t* source) noexcept;

/// @brief Loads a little-endian 32-bit value from a fixed-format buffer.
/// @param source Caller-owned buffer with at least four readable bytes.
/// @return Value represented by the first four bytes.
/// @pre The caller has validated the input buffer length.
uint32_t LoadLittleEndian32(const uint8_t* source) noexcept;

/// @brief Stores a 16-bit value in little-endian byte order.
/// @param destination Caller-owned buffer with room for at least two bytes.
/// @param value Value to serialize.
void StoreLittleEndian16(uint8_t* destination, uint16_t value) noexcept;

/// @brief Stores a 32-bit value in little-endian byte order.
/// @param destination Caller-owned buffer with room for at least four bytes.
/// @param value Value to serialize.
void StoreLittleEndian32(uint8_t* destination, uint32_t value) noexcept;

}  // namespace iw::core

#endif  // IW_CORE_BYTE_CODEC_H_
