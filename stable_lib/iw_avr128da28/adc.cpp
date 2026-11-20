// Implements the AVR128DA28 ADC and reference setup used by board sensors.
#include "avr128da28_adc.h"

#if defined(__AVR__)

#include <avr/io.h>

namespace iw::avr128da28 {
namespace {

// The ADC conversion is short on the target, but a broken peripheral must not
// turn a sensor read into an infinite wait. Keep this as a calibration knob
// for a board-clock change.
constexpr uint16_t kAdcPollLimit = 4096U;

bool WaitForConversion() noexcept {
  for (uint16_t poll = 0U; poll < kAdcPollLimit; ++poll) {
    if ((ADC0.INTFLAGS & ADC_RESRDY_bm) != 0U) {
      return true;
    }
  }
  return false;
}

PlatformResult ReadSample(uint8_t mux, uint8_t init_delay,
                          uint8_t sample_length,
                          uint16_t* raw_sample) noexcept {
  if (raw_sample == nullptr) {
    return PlatformResult::kInvalidArgument;
  }
  ADC0.MUXPOS = mux;
  ADC0.CTRLD = init_delay;
  ADC0.SAMPCTRL = sample_length;
  ADC0.CTRLA = ADC_ENABLE_bm | ADC_RESSEL_12BIT_gc;

  // Discard the first conversion after changing the input and sample timing.
  ADC0.INTFLAGS = ADC_RESRDY_bm;
  ADC0.COMMAND = ADC_STCONV_bm;
  if (!WaitForConversion()) {
    return PlatformResult::kTimeout;
  }
  (void)ADC0.RES;

  ADC0.INTFLAGS = ADC_RESRDY_bm;
  ADC0.COMMAND = ADC_STCONV_bm;
  if (!WaitForConversion()) {
    return PlatformResult::kTimeout;
  }
  *raw_sample = ADC0.RES;
  return PlatformResult::kOk;
}

}  // namespace

PlatformResult InitializeAdc() noexcept {
  // The board's battery divider and the AVR temperature sensor both use the
  // 2.048 V reference. The prescaler is fixed for the 4 MHz board clock.
  VREF.ADC0REF = VREF_REFSEL_2V048_gc;
  ADC0.CTRLC = ADC_PRESC_DIV4_gc;
  return PlatformResult::kOk;
}

PlatformResult ReadBatteryAdc(uint16_t* raw_sample) noexcept {
  // PD7/AIN7 is the board's analog-only battery probe.
  return ReadSample(ADC_MUXPOS_AIN7_gc, ADC_INITDLY_DLY16_gc, 10U, raw_sample);
}

PlatformResult ReadTemperatureAdc(uint16_t* raw_sample) noexcept {
  return ReadSample(ADC_MUXPOS_TEMPSENSE_gc, ADC_INITDLY_DLY32_gc, 50U,
                    raw_sample);
}

}  // namespace iw::avr128da28

#else

namespace iw::avr128da28 {

PlatformResult InitializeAdc() noexcept { return PlatformResult::kUnsupported; }

PlatformResult ReadBatteryAdc(uint16_t* raw_sample) noexcept {
  return raw_sample == nullptr ? PlatformResult::kInvalidArgument
                               : PlatformResult::kUnsupported;
}

PlatformResult ReadTemperatureAdc(uint16_t* raw_sample) noexcept {
  return raw_sample == nullptr ? PlatformResult::kInvalidArgument
                               : PlatformResult::kUnsupported;
}

}  // namespace iw::avr128da28

#endif  // defined(__AVR__)
