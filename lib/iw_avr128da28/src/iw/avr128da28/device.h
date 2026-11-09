#ifndef IW_AVR128DA28_DEVICE_H_
#define IW_AVR128DA28_DEVICE_H_

// Declares the AVR128DA28-only reset, interrupt, watchdog, and routing APIs.
#include <stdint.h>

#if defined(__AVR__) && !defined(__AVR_AVR128DA28__)
#error "This project supports AVR128DA28 only."
#endif
#if defined(__AVR__)
#include <avr/io.h>
#else
struct SPI_struct;
struct PORT_struct;
struct TWI_struct;
struct USART_struct;
using SPI_t = SPI_struct;
using PORT_t = PORT_struct;
using TWI_t = TWI_struct;
using USART_t = USART_struct;
#endif

#include "iw/avr128da28/memory_layout.h"

namespace iw::avr128da28 {

enum class PlatformResult : uint8_t {
  kOk = 0,
  kInvalidArgument,
  kOutOfRange,
  kBusy,
  kHardwareError,
  kUnsupported,
  kForbidden,
  kVerifyFailed,
  kTimeout,
};

struct Revision {
  uint8_t raw_revision_id;  // Raw silicon revision byte from SYSCFG.REVID.
  uint8_t major;            // High-nibble revision number.
  uint8_t minor;            // Low-nibble revision number.
};

// Verifies the fuse-selected geometry and applies the reset-time BOD policy.
// On native builds this returns kUnsupported; no fake hardware state is
// exposed to package or boot policy code.
[[nodiscard]] PlatformResult Init() noexcept;

// Returns the cached silicon revision captured during Init().
[[nodiscard]] Revision GetRevision() noexcept;

// Returns true when [address, address + length) lies entirely in APPCODE.
[[nodiscard]] constexpr bool IsAppCodeRange(uint32_t address,
                                            uint32_t length) noexcept {
  return !DeviceLayout::AdditionOverflows(address, length) &&
         address >= DeviceLayout::kApplicationStart &&
         address <= DeviceLayout::kApplicationEnd &&
         length <= DeviceLayout::kApplicationEnd - address;
}

// Applies the AVR128DA28 host-mode SPI workaround to the supplied peripheral.
[[nodiscard]] PlatformResult EnforceSpiHost(SPI_t* spi) noexcept;

// Applies board-wide pin, SPI, and TWI routing configuration.
[[nodiscard]] PlatformResult ConfigureAllPinPullups() noexcept;

// Selects the board's SPI route without configuring the radio or SD protocol.
[[nodiscard]] PlatformResult ConfigureSpiRoute() noexcept;

// Selects the board's TWI route without owning I2C device codecs.
[[nodiscard]] PlatformResult ConfigureTwiRoute() noexcept;

// Performs the protected SLPCTRL write, including the silicon-required
// instruction spacing.
[[nodiscard]] PlatformResult WriteSleepControl(uint8_t value) noexcept;
// Owns the AVR global-interrupt and vector-table control instructions so
// boot/application orchestration never writes CPUINT or emits cli/sei itself.
void DisableInterrupts() noexcept;

// Enables global interrupts after a caller has completed its critical section.
void EnableInterrupts() noexcept;

// Disables interrupts and returns the prior SREG value for later restoration.
[[nodiscard]] uint8_t SaveAndDisableInterrupts() noexcept;

// Restores the SREG value returned by SaveAndDisableInterrupts().
void RestoreInterruptState(uint8_t saved_status) noexcept;

// Selects the bootloader or application interrupt vector table.
void SelectBootVectorTable() noexcept;

// Selects the application interrupt vector table.
void SelectApplicationVectorTable() noexcept;

// Transfers control to the generated APPCODE origin. The caller must disable
// interrupts and finish board-specific peripheral shutdown first.
[[noreturn]] __attribute__((noinline)) void EnterApplication() noexcept;

// Configures the watchdog periods used by normal and trial boots.
void ConfigureApplicationWatchdog() noexcept;

// Configures the shorter watchdog period used during a trial boot.
void ConfigureTrialWatchdog() noexcept;

// Clears the watchdog reset condition without changing application policy.
void ResetWatchdog() noexcept;

// Requests the AVR software reset sequence and does not return on hardware.
void SoftwareReset() noexcept;

// Reads and clears RSTCTRL.RSTFR before framework initialization can touch it.
uint8_t ReadAndClearResetCause() noexcept;

// Prepares the TWI pins and peripheral for the board's active bus mode.
[[nodiscard]] PlatformResult PrepareTwiEnable(PORT_t* port, uint8_t sda_mask,
                                              uint8_t scl_mask) noexcept;
enum class TwiHold : uint8_t { k50Ns = 0, k300Ns };

// Applies the silicon-specific SDA hold encoding to the supplied TWI module.
[[nodiscard]] PlatformResult SetTwiHold(TWI_t* twi, TwiHold hold) noexcept;

// Recovers a TWI bus left in a stuck state by the target-side erratum path.
[[nodiscard]] PlatformResult RecoverTwi(TWI_t* twi) noexcept;

// Switches a USART into the active mode required before application traffic.
[[nodiscard]] PlatformResult EnterUsartActive(USART_t* usart) noexcept;

}  // namespace iw::avr128da28

#endif  // IW_AVR128DA28_DEVICE_H_
