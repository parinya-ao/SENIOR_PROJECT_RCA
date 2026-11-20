#ifndef IW_AVR128DA28_MEMORY_LAYOUT_H_
#define IW_AVR128DA28_MEMORY_LAYOUT_H_

/// @file
/// Exposes generated AVR128DA28 Flash and EEPROM geometry.
#include <stdint.h>

#include "avr128da28_generated_layout.h"
#include "checked_range.h"

namespace iw::avr128da28 {

/// Physical byte address in Flash, never an FLMAP window offset.
using FlashAddress = uint32_t;

/// Stable public view of the generated device geometry and safe range checks.
struct DeviceLayout {
  static constexpr FlashAddress kFlashSize =
      generated::kFlashBytes;  ///< Total physical Flash size in bytes.
  static constexpr FlashAddress kFlashTotalBytes =
      generated::kFlashBytes;  ///< Alias for the total Flash size.
  static constexpr FlashAddress kFlashEnd =
      generated::kFlashBytes;  ///< Exclusive physical Flash end address.
  static constexpr uint16_t kPageSize =
      generated::kFlashPageBytes;  ///< Flash erase/program page size.
  static constexpr uint16_t kFlashPageBytes =
      generated::kFlashPageBytes;  ///< Alias for the Flash page size.
  static constexpr uint16_t kEepromBytes =
      generated::kEepromBytes;  ///< Total EEPROM size in bytes.
  static constexpr uint16_t kBootSizePages =
      generated::kProductionBootSizePages;  ///< Production BOOT size in pages.
  static constexpr uint16_t kCodeSizePages =
      generated::kProductionCodeSizePages;  ///< Production APPCODE size.
  static constexpr FlashAddress kBootStart =
      generated::kBootStart;  ///< Inclusive BOOT start address.
  static constexpr FlashAddress kBootEnd =
      generated::kBootEnd;  ///< Exclusive BOOT end address.
  static constexpr FlashAddress kApplicationStart =
      generated::kApplicationStart;  ///< Inclusive APPCODE start address.
  static constexpr FlashAddress kApplicationEnd =
      generated::kApplicationEnd;  ///< Exclusive APPCODE end address.
  static constexpr FlashAddress kAppDataStart =
      generated::kAppdataStart;  ///< Start of application data region.
  static constexpr FlashAddress kMaximumApplicationImageBytes =
      generated::kApplicationCapacityBytes;  ///< Maximum APPCODE image size.
  static constexpr FlashAddress kApplicationImageEnd =
      generated::kApplicationEnd;  ///< Exclusive APPCODE image end.
  static constexpr FlashAddress kPageCount =
      generated::kPageCount;  ///< Number of physical Flash pages.

  /// Checks whether a Flash address is page-aligned.
  /// @param address Physical Flash byte address.
  /// @return True when address is aligned to kPageSize.
  static constexpr bool IsPageAligned(FlashAddress address) noexcept {
    return (address % kPageSize) == 0U;
  }

  /// Checks whether address plus length overflows FlashAddress.
  /// @param address Starting byte address.
  /// @param length Range length in bytes.
  /// @return True when the addition cannot be represented.
  static constexpr bool AdditionOverflows(FlashAddress address,
                                          FlashAddress length) noexcept {
    return iw::core::AdditionOverflows(address, length);
  }

  /// Checks whether a byte range lies within physical Flash.
  /// @param address Starting physical Flash byte address.
  /// @param length Range length in bytes.
  /// @return True when the whole half-open range is inside Flash.
  static constexpr bool IsPhysicalRange(FlashAddress address,
                                        FlashAddress length) noexcept {
    return iw::core::IsRangeWithin(address, length, 0U, kFlashSize);
  }

  /// Checks whether a complete Flash page belongs to APPCODE.
  /// @param address Physical start address of a candidate page.
  /// @return True when the page is aligned and contained in APPCODE.
  static constexpr bool IsApplicationPage(FlashAddress address) noexcept {
    return IsPhysicalPage(address) && address >= kApplicationStart &&
           address + kPageSize <= kApplicationEnd;
  }

  /// Checks whether a complete Flash page lies within physical Flash.
  /// @param address Physical start address of a candidate page.
  /// @return True when the page is aligned and contained in Flash.
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

/// Finds the first differing byte in two fixed-size buffers.
/// @param lhs First readable buffer containing length bytes.
/// @param rhs Second readable buffer containing length bytes.
/// @param length Number of bytes to compare.
/// @return First mismatch offset, or length when the buffers match.
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
