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

/// @brief Checks whether a candidate key contains provisioned data.
/// @param key Candidate key bytes, or null.
/// @return False for null, erased, or all-zero key data.
[[nodiscard]] bool IsHmacKeyProvisioned(
    const uint8_t key[kHmacKeyBytes]) noexcept;

/// @brief Reads the provisioned HMAC key from USERROW.
/// @param output Caller-owned buffer for `kHmacKeyBytes` bytes.
/// @return Provisioning status; output is written only on success.
/// @post Callers never access USERROW directly.
[[nodiscard]] ProvisioningResult ReadHmacKey(
    uint8_t output[kHmacKeyBytes]) noexcept;

/// @brief Reads the device UID from SIGROW.
/// @param output Caller-owned buffer for `kDeviceUidBytes` bytes.
/// @return Provisioning status; output is written only on success.
[[nodiscard]] ProvisioningResult ReadDeviceUid(
    uint8_t output[kDeviceUidBytes]) noexcept;

/// @brief Reads factory temperature calibration coefficients from SIGROW.
/// @param slope Receives the slope coefficient.
/// @param offset Receives the offset coefficient.
/// @return Provisioning status; outputs are written only on success.
[[nodiscard]] ProvisioningResult ReadTemperatureCalibration(
    uint16_t* slope, uint16_t* offset) noexcept;

}  // namespace iw::avr128da28

#endif  // IW_AVR128DA28_PROVISIONING_H_
