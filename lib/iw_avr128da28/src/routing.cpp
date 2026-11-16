// Implements AVR128DA28 peripheral routing and board pull-up configuration.
#include "iw/avr128da28/device.h"

#if defined(__AVR__)
#include <SPI.h>
#if !defined(NVM_HIL)
#include <Wire.h>
#endif
#endif

namespace iw::avr128da28 {

PlatformResult ConfigureAllPinPullups() noexcept {
#if defined(__AVR__)
  // P10-AVR-001: DxCore exposes the PORT register block as a hardware-mapped
  // byte array; this cast is limited to the register access boundary.
  for (uint8_t index = 0U; index < 8U; ++index) {
    // P10-AVR-001: hardware register access boundary.
    reinterpret_cast<volatile uint8_t*>(&PORTA)[0x10U + index] =
        PORT_PULLUPEN_bm;
    // P10-AVR-001: hardware register access boundary.
    reinterpret_cast<volatile uint8_t*>(&PORTC)[0x10U + index] =
        PORT_PULLUPEN_bm;
    // P10-AVR-001: hardware register access boundary.
    reinterpret_cast<volatile uint8_t*>(&PORTD)[0x10U + index] =
        PORT_PULLUPEN_bm;
    // P10-AVR-001: hardware register access boundary.
    reinterpret_cast<volatile uint8_t*>(&PORTF)[0x10U + index] =
        PORT_PULLUPEN_bm;
  }
  return PlatformResult::kOk;
#else
  return PlatformResult::kUnsupported;
#endif
}

PlatformResult ConfigureSpiRoute() noexcept {
#if defined(__AVR__)
  // P10-AVR-001: SPI.swap is the DxCore hardware route boundary.
  if (!SPI.swap(SPI1_SWAP_DEFAULT)) {
    return PlatformResult::kUnsupported;
  }
  return PlatformResult::kOk;
#else
  return PlatformResult::kUnsupported;
#endif
}

PlatformResult ConfigureTwiRoute() noexcept {
#if defined(__AVR__) && defined(TWI0) && !defined(NVM_HIL)
#if defined(TWI1)
  // TWI0-only parts have no second module or alternate Wire object to swap.
  if (!Wire.swap(0U)) {
    return PlatformResult::kUnsupported;
  }
#endif
  return PlatformResult::kOk;
#else
  return PlatformResult::kUnsupported;
#endif
}

}  // namespace iw::avr128da28
