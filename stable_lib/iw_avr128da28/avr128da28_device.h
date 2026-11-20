#ifndef IW_AVR128DA28_DEVICE_H_
#define IW_AVR128DA28_DEVICE_H_

/// @file
/// Declares AVR128DA28-only reset, interrupt, watchdog, ADC and routing APIs.
#include <stdint.h>

#if defined(__AVR__) && !defined(__AVR_AVR128DA28__)
#error "This project supports AVR128DA28 only."
#endif
#if defined(__AVR__)
#include <avr/io.h>
#else
/// Host-only incomplete SPI peripheral type used by compile-time stubs.
struct SPI_struct;
/// Host-only incomplete PORT peripheral type used by compile-time stubs.
struct PORT_struct;
/// Host-only incomplete TWI peripheral type used by compile-time stubs.
struct TWI_struct;
/// Host-only incomplete USART peripheral type used by compile-time stubs.
struct USART_struct;
using SPI_t = SPI_struct;      ///< SPI peripheral handle type.
using PORT_t = PORT_struct;    ///< PORT peripheral handle type.
using TWI_t = TWI_struct;      ///< TWI peripheral handle type.
using USART_t = USART_struct;  ///< USART peripheral handle type.
#endif

#include "avr128da28_memory_layout.h"

namespace iw::avr128da28 {

/// Result codes returned by AVR platform operations.
enum class PlatformResult : uint8_t {
  kOk = 0,           ///< Operation completed.
  kInvalidArgument,  ///< A required argument is invalid.
  kOutOfRange,       ///< Address or value is outside the device range.
  kBusy,             ///< Hardware is already owned by another operation.
  kHardwareError,    ///< The peripheral reported an error.
  kUnsupported,      ///< The operation is unavailable on this build target.
  kForbidden,        ///< The requested operation violates a platform policy.
  kVerifyFailed,     ///< Hardware readback did not match the requested value.
  kTimeout,          ///< The peripheral did not complete before its deadline.
};

/// Decoded silicon revision captured during platform initialization.
struct Revision {
  uint8_t raw_revision_id;  ///< Raw SYSCFG.REVID byte.
  uint8_t major;            ///< High-nibble revision number.
  uint8_t minor;            ///< Low-nibble revision number.
};

/// Verifies fuse-selected geometry and applies the reset-time BOD policy.
/// @return kOk when platform initialization succeeds; kUnsupported on host
/// builds that have no AVR hardware.
[[nodiscard]] PlatformResult Init() noexcept;

/// Returns the cached silicon revision captured during Init().
/// @return Cached revision fields; call Init() before relying on the value.
[[nodiscard]] Revision GetRevision() noexcept;

/// Checks whether a complete byte range lies in generated APPCODE bounds.
/// @param address Physical Flash start address.
/// @param length Range length in bytes.
/// @return True when the non-overflowing range is wholly inside APPCODE.
[[nodiscard]] constexpr bool IsAppCodeRange(uint32_t address,
                                            uint32_t length) noexcept {
  return !DeviceLayout::AdditionOverflows(address, length) &&
         address >= DeviceLayout::kApplicationStart &&
         address <= DeviceLayout::kApplicationEnd &&
         length <= DeviceLayout::kApplicationEnd - address;
}

/// Applies the AVR128DA28 host-mode SPI workaround to a peripheral.
/// @param spi SPI peripheral to configure; null is rejected.
/// @return kOk on success, otherwise the platform error.
[[nodiscard]] PlatformResult EnforceSpiHost(SPI_t* spi) noexcept;

/// Applies the board-wide pin, SPI and TWI routing configuration.
/// @return kOk on success, otherwise the first platform error.
[[nodiscard]] PlatformResult ConfigureAllPinPullups() noexcept;

/// Selects the board's SPI route without configuring radio or SD protocols.
/// @return kOk on success, otherwise the platform error.
[[nodiscard]] PlatformResult ConfigureSpiRoute() noexcept;

/// Selects the board's TWI route without owning I2C device codecs.
/// @return kOk on success, otherwise the platform error.
[[nodiscard]] PlatformResult ConfigureTwiRoute() noexcept;

/// Writes SLPCTRL with the silicon-required instruction spacing.
/// @param value Encoded SLPCTRL register value.
/// @return kOk on hardware, or kUnsupported on native host builds.
[[nodiscard]] PlatformResult WriteSleepControl(uint8_t value) noexcept;
/// Disables global interrupts through the platform-owned AVR instruction path.
void DisableInterrupts() noexcept;

/// Enables global interrupts after a caller completes its critical section.
void EnableInterrupts() noexcept;

/// Saves SREG and disables interrupts for a bounded critical section.
/// @return Prior SREG value to pass to RestoreInterruptState().
[[nodiscard]] uint8_t SaveAndDisableInterrupts() noexcept;

/// Restores the exact status value returned by SaveAndDisableInterrupts().
/// @param saved_status Previously saved SREG value.
void RestoreInterruptState(uint8_t saved_status) noexcept;

/// Selects the bootloader interrupt vector table.
void SelectBootVectorTable() noexcept;

/// Selects the application interrupt vector table.
void SelectApplicationVectorTable() noexcept;

/// Transfers control to the generated APPCODE origin and does not return.
/// @pre The caller has disabled interrupts and shut down board peripherals.
[[noreturn]] __attribute__((noinline)) void EnterApplication() noexcept;

/// Configures the watchdog period used by normal application boots.
void ConfigureApplicationWatchdog() noexcept;

/// Configures the shorter watchdog period used during a trial boot.
void ConfigureTrialWatchdog() noexcept;

/// Clears the watchdog reset condition without changing application policy.
void ResetWatchdog() noexcept;

/// Requests the AVR software reset sequence; hardware does not return.
void SoftwareReset() noexcept;

/// Reads and clears RSTCTRL.RSTFR before framework initialization.
/// @return Reset cause flags captured before they are cleared.
uint8_t ReadAndClearResetCause() noexcept;

/// Prepares TWI pins and a peripheral for the board's active bus mode.
/// @param port Port containing the SDA/SCL pins; null is rejected.
/// @param sda_mask Bit mask for the SDA pin.
/// @param scl_mask Bit mask for the SCL pin.
/// @return kOk on success, otherwise the platform error.
[[nodiscard]] PlatformResult PrepareTwiEnable(PORT_t* port, uint8_t sda_mask,
                                              uint8_t scl_mask) noexcept;
/// Supported TWI SDA hold encodings.
enum class TwiHold : uint8_t { k50Ns = 0, k300Ns };

/// Applies the silicon-specific SDA hold encoding to a TWI peripheral.
/// @param twi TWI peripheral to configure; null is rejected.
/// @param hold Requested SDA hold interval.
/// @return kOk on success, otherwise the platform error.
[[nodiscard]] PlatformResult SetTwiHold(TWI_t* twi, TwiHold hold) noexcept;

/// Recovers a TWI bus left stuck by the target-side erratum path.
/// @param twi TWI peripheral to recover; null is rejected.
/// @return kOk on success, otherwise the platform error.
[[nodiscard]] PlatformResult RecoverTwi(TWI_t* twi) noexcept;

/// Switches a USART into the active mode required before application traffic.
/// @param usart USART peripheral to configure; null is rejected.
/// @return kOk on success, otherwise the platform error.
[[nodiscard]] PlatformResult EnterUsartActive(USART_t* usart) noexcept;

}  // namespace iw::avr128da28

#endif  // IW_AVR128DA28_DEVICE_H_
