// No repository-wide license is declared; existing rights are unchanged.

// Selects application policy without redefining the generated board/radio SSOT.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_CONFIG_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_CONFIG_H_
#include "application_config.h"
#include "generated/arq_config.h"
#if defined(ARQ_REVERSE_DIAGNOSTIC) && !defined(ARQ_RADIO_ONLY_DIAGNOSTIC)
#error "Role reversal is restricted to radio-only diagnostics"
#endif
#if defined(LORA_ROLE_SENDER) != defined(ARQ_REVERSE_DIAGNOSTIC)
#define ARQ_ROLE_SENDER 1
#endif
namespace arq {
namespace config {
#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC)
inline constexpr uint8_t kMaxRetries =
    application_config::diagnostics::kMaxRetries;
inline constexpr auto& kPayload = application_config::diagnostics::kPayload;
#if defined(ARQ_REVERSE_DIAGNOSTIC)
// Reverse DATA direction without changing either physical board's identity.
inline constexpr uint8_t kSenderId = ARQ_RECEIVER_ID;
inline constexpr uint8_t kReceiverId = ARQ_SENDER_ID;
inline constexpr auto& kDirectionPayload =
    application_config::diagnostics::kTrackerPayload;
#else
inline constexpr uint8_t kSenderId = ARQ_SENDER_ID;
inline constexpr uint8_t kReceiverId = ARQ_RECEIVER_ID;
inline constexpr auto& kDirectionPayload =
    application_config::diagnostics::kGatewayPayload;
#endif
#else
inline constexpr uint8_t kMaxRetries = ARQ_MAX_RETRIES;
inline constexpr char kPayload[] = ARQ_PAYLOAD;
inline constexpr uint8_t kSenderId = ARQ_SENDER_ID;
inline constexpr uint8_t kReceiverId = ARQ_RECEIVER_ID;
#endif
}  // namespace config
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_CONFIG_H_
