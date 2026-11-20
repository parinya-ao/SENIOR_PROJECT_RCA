#ifndef IW_AVR128DA28_GENERATED_LAYOUT_H_
#define IW_AVR128DA28_GENERATED_LAYOUT_H_

#include <stdint.h>

#if defined(LORA_RECEIVER_BOARD)
#include <generated/lora_receiver_board.h>
#else
#include <generated/lora_sender_board.h>
#endif

namespace iw::avr128da28::generated {
inline constexpr uint32_t kFlashBytes = LORA_FLASH_BYTES;
inline constexpr uint16_t kFlashPageBytes = LORA_FLASH_PAGE_BYTES;
inline constexpr uint16_t kEepromBytes = LORA_EEPROM_BYTES;
inline constexpr uint16_t kProductionBootSizePages = LORA_BOOTSIZE_PAGES;
inline constexpr uint16_t kProductionCodeSizePages = LORA_CODESIZE_PAGES;
inline constexpr uint32_t kBootStart = 0U;
inline constexpr uint32_t kBootEnd =
    kProductionBootSizePages == 0U
        ? kFlashBytes
        : static_cast<uint32_t>(kProductionBootSizePages) * kFlashPageBytes;
inline constexpr uint32_t kBootCapacityBytes = kBootEnd - kBootStart;
inline constexpr bool kHasApplicationCode =
    kProductionBootSizePages > 0U &&
    (kProductionCodeSizePages == 0U ||
     kProductionCodeSizePages > kProductionBootSizePages);
inline constexpr uint32_t kApplicationStart =
    kHasApplicationCode ? kBootEnd : kFlashBytes;
inline constexpr uint32_t kApplicationEnd =
    !kHasApplicationCode
        ? kFlashBytes
        : (kProductionCodeSizePages == 0U
               ? kFlashBytes
               : static_cast<uint32_t>(kProductionCodeSizePages) *
                     kFlashPageBytes);
inline constexpr uint32_t kApplicationCapacityBytes =
    kApplicationEnd - kApplicationStart;
inline constexpr uint32_t kAppdataStart =
    kProductionBootSizePages == 0U || kProductionCodeSizePages == 0U
        ? kFlashBytes
        : (kProductionCodeSizePages <= kProductionBootSizePages
               ? kBootEnd
               : static_cast<uint32_t>(kProductionCodeSizePages) *
                     kFlashPageBytes);
inline constexpr uint32_t kAppdataEnd = kFlashBytes;
inline constexpr uint32_t kPageCount = kFlashBytes / kFlashPageBytes;
}  // namespace iw::avr128da28::generated

#endif  // IW_AVR128DA28_GENERATED_LAYOUT_H_
