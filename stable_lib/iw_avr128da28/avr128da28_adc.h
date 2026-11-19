#ifndef IW_AVR128DA28_ADC_H_
#define IW_AVR128DA28_ADC_H_

// Declares AVR128DA28 ADC register sequencing for board sensor channels.
#include <stdint.h>

#include "avr128da28_device.h"

namespace iw::avr128da28 {

/// @brief Initializes ADC hardware for the configured board channels.
/// @return Platform status; no sample is read.
[[nodiscard]] PlatformResult InitializeAdc() noexcept;

/// @brief Reads one raw sample from the board battery ADC channel.
/// @param raw_sample Receives the 12-bit ADC sample on success.
/// @return Platform status; null output or hardware failure is reported.
/// @post Does not apply board calibration or convert the sample to volts.
[[nodiscard]] PlatformResult ReadBatteryAdc(uint16_t* raw_sample) noexcept;

/// @brief Reads one raw sample from the internal temperature ADC channel.
/// @param raw_sample Receives the 12-bit ADC sample on success.
/// @return Platform status; null output or hardware failure is reported.
/// @post Does not apply factory calibration coefficients.
[[nodiscard]] PlatformResult ReadTemperatureAdc(uint16_t* raw_sample) noexcept;

}  // namespace iw::avr128da28

#endif  // IW_AVR128DA28_ADC_H_
