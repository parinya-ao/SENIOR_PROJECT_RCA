// Reads device identity and provisioned secrets from AVR128DA28 fuse regions.
#include "iw/avr128da28/provisioning.h"

#if defined(__AVR__)
#include <avr/io.h>
#endif

namespace iw::avr128da28 {

bool IsHmacKeyProvisioned(const uint8_t key[kHmacKeyBytes]) noexcept {
  if (key == nullptr) {
    return false;
  }
  bool all_zero = true;
  bool all_ff = true;
  for (uint8_t index = 0U; index < kHmacKeyBytes; ++index) {
    all_zero = all_zero && key[index] == 0U;
    all_ff = all_ff && key[index] == 0xFFU;
  }
  return !all_zero && !all_ff;
}

ProvisioningResult ReadHmacKey(uint8_t output[kHmacKeyBytes]) noexcept {
  if (output == nullptr) {
    return ProvisioningResult::kInvalidArgument;
  }
#if defined(__AVR__)
  // P10-AVR-001: USERROW is a hardware-mapped AVR fuse region.
  volatile const uint8_t* userrow = reinterpret_cast<volatile const uint8_t*>(
      &USERROW.USERROW0);  // P10-AVR-001
  for (uint8_t index = 0U; index < kHmacKeyBytes; ++index) {
    output[index] = userrow[index];
  }
  return IsHmacKeyProvisioned(output) ? ProvisioningResult::kOk
                                      : ProvisioningResult::kUnprovisioned;
#else
  return ProvisioningResult::kUnsupported;
#endif
}

ProvisioningResult ReadDeviceUid(uint8_t output[kDeviceUidBytes]) noexcept {
  if (output == nullptr) {
    return ProvisioningResult::kInvalidArgument;
  }
#if defined(__AVR__)
  // P10-AVR-001: SIGROW is a hardware-mapped AVR serial-number region.
  volatile const uint8_t* serial = reinterpret_cast<volatile const uint8_t*>(
      &SIGROW.SERNUM0);  // P10-AVR-001
  for (uint8_t index = 0U; index < kDeviceUidBytes; ++index) {
    output[index] = serial[index];
  }
  return ProvisioningResult::kOk;
#else
  return ProvisioningResult::kUnsupported;
#endif
}

ProvisioningResult ReadTemperatureCalibration(uint16_t* slope,
                                              uint16_t* offset) noexcept {
#if defined(__AVR__)
  if (slope == nullptr || offset == nullptr) {
    return ProvisioningResult::kInvalidArgument;
  }
  *slope = SIGROW.TEMPSENSE0;
  *offset = SIGROW.TEMPSENSE1;
  return ProvisioningResult::kOk;
#else
  (void)slope;
  (void)offset;
  return ProvisioningResult::kUnsupported;
#endif
}

}  // namespace iw::avr128da28
