#ifndef IW_CORE_CHECKED_RANGE_H_
#define IW_CORE_CHECKED_RANGE_H_

// Provides overflow-safe unsigned range arithmetic for fixed-format data and
// platform geometry checks.
#include <stdint.h>

namespace iw::core {

/// @brief Checks whether unsigned addition would overflow.
/// @param left First addend.
/// @param right Second addend.
/// @return True when the mathematical sum exceeds `uint32_t`.
constexpr bool AdditionOverflows(uint32_t left, uint32_t right) noexcept {
  return right > (UINT32_MAX - left);
}

/// @brief Checks whether a half-open range is inside another range.
/// @param start Range start address.
/// @param length Range length in bytes.
/// @param container_start Container start address.
/// @param container_length Container length in bytes.
/// @return True when both range ends are representable and the requested range
///   is contained in the container. Empty ranges at the container end are
///   valid.
constexpr bool IsRangeWithin(uint32_t start, uint32_t length,
                             uint32_t container_start,
                             uint32_t container_length) noexcept {
  if (AdditionOverflows(start, length) ||
      AdditionOverflows(container_start, container_length)) {
    return false;
  }
  const uint32_t end = start + length;
  const uint32_t container_end = container_start + container_length;
  return start >= container_start && end <= container_end;
}

}  // namespace iw::core

#endif  // IW_CORE_CHECKED_RANGE_H_
