#ifndef IW_AVR128DA28_GENERATED_LAYOUT_H_
#define IW_AVR128DA28_GENERATED_LAYOUT_H_

#include <stdint.h>

#if defined(LORA_RECEIVER_BOARD)
#include <generated/lora_receiver_board.h>
#else
#include <generated/lora_sender_board.h>
#endif

namespace iw::avr128da28::generated {
inline constexpr uint32_t kFlashBytes = 0x20000UL;
inline constexpr uint16_t kFlashPageBytes = 512U;
inline constexpr uint16_t kEepromBytes = 512U;
inline constexpr uint32_t kBootStart = 0U;
inline constexpr uint32_t kBootEnd = LORA_IMAGE_START;
inline constexpr uint32_t kBootCapacityBytes = LORA_IMAGE_START;
inline constexpr uint32_t kApplicationStart = LORA_IMAGE_START;
inline constexpr uint32_t kApplicationEnd = LORA_IMAGE_END;
inline constexpr uint32_t kApplicationCapacityBytes =
    LORA_IMAGE_END - LORA_IMAGE_START;
inline constexpr uint32_t kAppdataStart = kFlashBytes;
inline constexpr uint32_t kAppdataEnd = kFlashBytes;
inline constexpr uint32_t kPageCount = kFlashBytes / kFlashPageBytes;
inline constexpr uint16_t kProductionBootSizePages =
    LORA_IMAGE_START / kFlashPageBytes;
inline constexpr uint16_t kProductionCodeSizePages = 0U;
}  // namespace iw::avr128da28::generated

#endif  // IW_AVR128DA28_GENERATED_LAYOUT_H_
