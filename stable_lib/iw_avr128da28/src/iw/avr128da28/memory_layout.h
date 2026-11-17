#ifndef IW_AVR128DA28_MEMORY_LAYOUT_H_
#define IW_AVR128DA28_MEMORY_LAYOUT_H_

// Defines the generated AVR128DA28 flash and EEPROM geometry used by FOTA.
#include <stdint.h>

#include "iw/avr128da28/generated_layout.h"
#include "iw/core/checked_range.h"

namespace iw::avr128da28 {

// Physical, byte-addressed Flash address. It is never an FLMAP window offset.
using FlashAddress = uint32_t;

// Stable public view of the single generated device geometry.
struct DeviceLayout {
  static constexpr FlashAddress kFlashSize = generated::kFlashBytes;
  static constexpr FlashAddress kFlashTotalBytes = generated::kFlashBytes;
  static constexpr FlashAddress kFlashEnd = generated::kFlashBytes;
  static constexpr uint16_t kPageSize = generated::kFlashPageBytes;
  static constexpr uint16_t kFlashPageBytes = generated::kFlashPageBytes;
  static constexpr uint16_t kEepromBytes = generated::kEepromBytes;
  static constexpr uint16_t kBootSizePages =
      generated::kProductionBootSizePages;
  static constexpr uint16_t kCodeSizePages =
      generated::kProductionCodeSizePages;
  static constexpr FlashAddress kBootStart = generated::kBootStart;
  static constexpr FlashAddress kBootEnd = generated::kBootEnd;
  static constexpr FlashAddress kApplicationStart =
      generated::kApplicationStart;
  static constexpr FlashAddress kApplicationEnd = generated::kApplicationEnd;
  static constexpr FlashAddress kAppDataStart = generated::kAppdataStart;
  static constexpr FlashAddress kMaximumApplicationImageBytes =
      generated::kApplicationCapacityBytes;
  static constexpr FlashAddress kApplicationImageEnd =
      generated::kApplicationEnd;
  static constexpr FlashAddress kPageCount = generated::kPageCount;

  static constexpr bool IsPageAligned(FlashAddress address) noexcept {
    return (address % kPageSize) == 0U;
  }

  static constexpr bool AdditionOverflows(FlashAddress address,
                                          FlashAddress length) noexcept {
    return iw::core::AdditionOverflows(address, length);
  }

  static constexpr bool IsPhysicalRange(FlashAddress address,
                                        FlashAddress length) noexcept {
    return iw::core::IsRangeWithin(address, length, 0U, kFlashSize);
  }

  static constexpr bool IsApplicationPage(FlashAddress address) noexcept {
    return IsPhysicalPage(address) && address >= kApplicationStart &&
           address + kPageSize <= kApplicationEnd;
  }

  static constexpr bool IsPhysicalPage(FlashAddress address) noexcept {
    return IsPageAligned(address) && !AdditionOverflows(address, kPageSize) &&
           address + kPageSize <= kFlashEnd;
  }
};

static_assert(DeviceLayout::kBootStart == generated::kBootStart,
              "BOOT start must come from generated board configuration");
static_assert(DeviceLayout::kBootEnd == generated::kBootEnd,
              "BOOT end must come from generated board configuration");
static_assert(DeviceLayout::kApplicationStart == generated::kApplicationStart,
              "APPCODE start must come from generated board configuration");
static_assert(DeviceLayout::kApplicationEnd == generated::kApplicationEnd,
              "APPCODE end must come from generated board configuration");

// Returns the first byte offset whose two fixed-size buffers differ, or
// length when all bytes match. The buffers must each contain length bytes.
inline uint16_t FirstMismatch(const uint8_t* lhs, const uint8_t* rhs,
                              uint16_t length) noexcept {
  uint16_t index = 0U;
  while (index < length && lhs[index] == rhs[index]) {
    ++index;
  }
  return index;
}

}  // namespace iw::avr128da28

#endif  // IW_AVR128DA28_MEMORY_LAYOUT_H_
