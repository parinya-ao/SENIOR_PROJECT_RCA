#ifndef IW_AVR128DA28_SLEEP_H_
#define IW_AVR128DA28_SLEEP_H_

// Declares RTC and standby-sleep primitives owned by the AVR128DA28 platform.
#if defined(__AVR__) && !defined(__AVR_AVR128DA28__)
#error "This project supports AVR128DA28 only."
#endif

#include <stdint.h>

namespace iw::avr128da28 {

/// @brief Initializes the RTC peripheral used as the sleep time base.
void InitializeRtc() noexcept;

/// @brief Configures the AVR sleep controller for standby mode without
/// sleeping.
void ConfigureStandbySleep() noexcept;

/// @brief Enters standby until an interrupt wakes the MCU.
/// @pre Standby mode and the required wake source have been configured.
/// @post Returns after a wake interrupt without clearing caller state.
void EnterStandbySleep() noexcept;

/// @brief Reads the current RTC tick count.
/// @return Monotonically increasing ticks since the counter was initialized.
uint32_t ReadRtcTicks() noexcept;

/// @brief Resets the RTC tick counter.
/// @post Subsequent reads begin from zero.
void ResetRtcTicks() noexcept;

}  // namespace iw::avr128da28

#endif  // IW_AVR128DA28_SLEEP_H_
