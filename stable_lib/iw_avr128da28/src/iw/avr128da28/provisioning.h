#ifndef IW_AVR128DA28_PROVISIONING_H_
#define IW_AVR128DA28_PROVISIONING_H_

// Declares AVR128DA28 USERROW/SIGROW provisioning and identity reads.
#if defined(__AVR__) && !defined(__AVR_AVR128DA28__)
#error "This project supports AVR128DA28 only."
#endif

#include <stdint.h>

namespace iw::avr128da28 {

inline constexpr uint8_t kHmacKeyBytes = 32U;
inline constexpr uint8_t kDeviceUidBytes = 16U;

enum class ProvisioningResult : uint8_t {
  kOk = 0,
  kInvalidArgument,
  kUnprovisioned,
  kUnsupported,
};

// Returns false for a null key or the erased/all-zero provisioning value.
[[nodiscard]] bool IsHmacKeyProvisioned(
    const uint8_t key[kHmacKeyBytes]) noexcept;

// Reads the provisioned USERROW HMAC key without exposing USERROW to callers.
[[nodiscard]] ProvisioningResult ReadHmacKey(
    uint8_t output[kHmacKeyBytes]) noexcept;

// Reads the stable device UID from SIGROW into the caller-owned buffer.
[[nodiscard]] ProvisioningResult ReadDeviceUid(
    uint8_t output[kDeviceUidBytes]) noexcept;

// Reads the factory temperature calibration coefficients from SIGROW.
[[nodiscard]] ProvisioningResult ReadTemperatureCalibration(
    uint16_t* slope, uint16_t* offset) noexcept;

}  // namespace iw::avr128da28

#endif  // IW_AVR128DA28_PROVISIONING_H_
