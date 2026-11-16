#ifndef IW_AVR128DA28_SLEEP_H_
#define IW_AVR128DA28_SLEEP_H_

// Declares RTC and standby-sleep primitives owned by the AVR128DA28 platform.
#if defined(__AVR__) && !defined(__AVR_AVR128DA28__)
#error "This project supports AVR128DA28 only."
#endif

#include <stdint.h>

namespace iw::avr128da28 {

// Initializes the RTC peripheral used as the tracker sleep time base.
void InitializeRtc() noexcept;

// Configures the AVR sleep controller for standby mode.
void ConfigureStandbySleep() noexcept;

// Enters standby and returns after an RTC wakeup interrupt.
void EnterStandbySleep() noexcept;

// Returns the monotonically increasing RTC tick count.
uint32_t ReadRtcTicks() noexcept;

// Resets the RTC tick counter to zero.
void ResetRtcTicks() noexcept;

}  // namespace iw::avr128da28

#endif  // IW_AVR128DA28_SLEEP_H_
