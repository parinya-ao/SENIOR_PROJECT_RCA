// No repository-wide license is declared; existing rights are unchanged.

// Generated application policy; edit config/application.toml.

#ifndef SENIOR_PROJECT_RCA_APPLICATION_CONFIG_H_
#define SENIOR_PROJECT_RCA_APPLICATION_CONFIG_H_
#include <stdint.h>
namespace application_config {
namespace diagnostics {
inline constexpr uint32_t kMaxRetries = 0UL;
inline constexpr char kPayload[] = "HELLO_LORA";
inline constexpr char kGatewayPayload[] = "HELLO_LORA_GW";
inline constexpr char kTrackerPayload[] = "HELLO_LORA_TR";
inline constexpr char kNegativePayload[] = "REJECT_LORA";
}  // namespace diagnostics
namespace logging {
inline constexpr uint32_t kSlotCount = 16UL;
inline constexpr uint32_t kSlotBytes = 192UL;
}  // namespace logging
namespace commands {
inline constexpr uint32_t kCapacity = 80UL;
inline constexpr uint32_t kInterByteTimeoutMs = 1000UL;
inline constexpr uint32_t kFaultLimit = 100UL;
}  // namespace commands
namespace ssot {
inline constexpr uint32_t kCampaignMessages = 20UL;
}  // namespace ssot
namespace startup {
inline constexpr uint32_t kRadioSettleMs = 10UL;
inline constexpr uint32_t kVersionProbeAttempts = 3UL;
}  // namespace startup
namespace raw {
inline constexpr char kPayload[] = "Hello World";
inline constexpr uint32_t kTransmitIntervalMs = 3000UL;
inline constexpr uint32_t kReceiveTimeoutMs = 15000UL;
inline constexpr uint32_t kLogByteTimeoutMs = 100UL;
inline constexpr uint32_t kLogBatchTimeoutMs = 3000UL;
inline constexpr uint32_t kPacketEventLimit = 2UL;
}  // namespace raw
namespace gateway {
inline constexpr uint32_t kResultBufferBytes = 4096UL;
inline constexpr uint32_t kUartBaud = 115200UL;
inline constexpr uint32_t kI2cResetIntervalMs = 60000UL;
}  // namespace gateway
}  // namespace application_config
#endif  // SENIOR_PROJECT_RCA_APPLICATION_CONFIG_H_
