#ifndef IW_CORE_BYTE_CODEC_H_
#define IW_CORE_BYTE_CODEC_H_

// Declares the allocation-free little-endian codec shared by fixed formats.
#include <stdint.h>

namespace iw::core {

// The caller owns both buffers and must provide at least two destination or
// source bytes. These functions intentionally do not allocate or inspect
// buffer lengths; fixed-format callers validate their packet length first.
// Loads two bytes from source in little-endian order. The caller provides at
// least two readable bytes and retains ownership of the buffer.
uint16_t LoadLittleEndian16(const uint8_t* source) noexcept;

// Loads four bytes from source in little-endian order. The caller provides at
// least four readable bytes and retains ownership of the buffer.
uint32_t LoadLittleEndian32(const uint8_t* source) noexcept;

// Stores value as two little-endian bytes in destination, which must have
// room for at least two bytes.
void StoreLittleEndian16(uint8_t* destination, uint16_t value) noexcept;

// Stores value as four little-endian bytes in destination, which must have
// room for at least four bytes.
void StoreLittleEndian32(uint8_t* destination, uint32_t value) noexcept;

}  // namespace iw::core

#endif  // IW_CORE_BYTE_CODEC_H_
