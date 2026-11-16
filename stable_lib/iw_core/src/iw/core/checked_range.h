#ifndef IW_CORE_CHECKED_RANGE_H_
#define IW_CORE_CHECKED_RANGE_H_

// Provides overflow-safe unsigned range arithmetic for fixed-format data and
// platform geometry checks.
#include <stdint.h>

namespace iw::core {

// Returns true when left + right would exceed the uint32_t range.
constexpr bool AdditionOverflows(uint32_t left, uint32_t right) noexcept {
  return right > (UINT32_MAX - left);
}

// Returns whether [start, start + length) is contained in
// [container_start, container_start + container_length). Empty ranges are
// valid at the container end; arithmetic is checked before every addition.
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
