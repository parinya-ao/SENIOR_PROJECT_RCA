#ifndef IW_AVR128DA28_ADC_H_
#define IW_AVR128DA28_ADC_H_

// Declares AVR128DA28 ADC register sequencing for board sensor channels.
#include <stdint.h>

#include "iw/avr128da28/device.h"

namespace iw::avr128da28 {

// ADC register sequencing belongs to the AVR owner. Callers retain only the
// sensor-domain conversion math and receive a raw 12-bit sample.
[[nodiscard]] PlatformResult InitializeAdc() noexcept;

// Reads the board battery channel into raw_sample without applying board
// calibration or converting the result to volts.
[[nodiscard]] PlatformResult ReadBatteryAdc(uint16_t* raw_sample) noexcept;

// Reads the internal temperature channel into raw_sample without applying
// the factory calibration coefficients.
[[nodiscard]] PlatformResult ReadTemperatureAdc(uint16_t* raw_sample) noexcept;

}  // namespace iw::avr128da28

#endif  // IW_AVR128DA28_ADC_H_
