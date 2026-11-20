// Formats role-tagged UART diagnostics with bounded buffers and an optional
// nonblocking foreground queue. Logging loss never changes radio state.
#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_UPDI_UART_SRC_ROLE_LOG_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_UPDI_UART_SRC_ROLE_LOG_H_

#include <stdint.h>
#include <stdio.h>

#include "updi_uart.h"

inline constexpr uint8_t kUpdiRoleLogMessageLimit = 120U;

// Version tag for the CRC-protected firmware identity line.
#define UPDI_ROLE_LOG_IDENTITY_V1 1
#ifndef LORA_DEBUG_OUTPUT
#define LORA_DEBUG_OUTPUT 1
#endif
#if LORA_DEBUG_OUTPUT != 0 && LORA_DEBUG_OUTPUT != 1
#error "LORA_DEBUG_OUTPUT must be 0 or 1"
#endif
#if defined(LORA_NONBLOCKING_LOG) && LORA_NONBLOCKING_LOG
// Only the main loop produces and drains this queue; radio ISRs do not log.
static uint8_t updi_log_queue[1024];
static uint16_t updi_log_head, updi_log_count, updi_log_drops;
// Returns the saturating count of log bytes dropped because the queue was full.
inline uint16_t updi_role_log_dropped() { return updi_log_drops; }
// Lets deferred producers wait for a complete multi-line observation to fit.
inline bool updi_role_log_has_space(uint16_t bytes) {
  return sizeof(updi_log_queue) - updi_log_count >= bytes;
}
// Transmits at most one queued byte when the UPDI mailbox is ready.
inline void updi_role_log_service() {
  if (updi_log_count && updi_uart_try_tx(updi_log_queue[updi_log_head])) {
    updi_log_head = (updi_log_head + 1U) % sizeof(updi_log_queue);
    --updi_log_count;
  }
}
// Adds one byte to the nonblocking queue. The caller reserves the complete
// record first; only the foreground producer may call this helper.
inline void updi_role_log_byte(uint8_t byte) {
  updi_log_queue[(updi_log_head + updi_log_count) % sizeof(updi_log_queue)] =
      byte;
  ++updi_log_count;
}
#endif

// Writes `width` uppercase hexadecimal digits and a NUL terminator. `output`
// must have width+1 bytes and width must be at most 8.
inline void updi_role_log_format_hex(char* output, uint32_t value,
                                     uint8_t width) {
  static constexpr char digits[] = "0123456789ABCDEF";
  for (uint8_t i = 0; i < width; ++i) {
    const uint8_t shift = static_cast<uint8_t>(4U * (width - i - 1U));
    output[i] = digits[(value >> shift) & 0x0fU];
  }
  output[width] = '\0';
}

// Emits one `[role] message` line. Strings are borrowed for the call and
// truncated to 12/120 bytes. Debug-off emits nothing; queued mode may drop a
// full record and saturates its drop counter. Foreground only; not ISR-safe.
inline void updi_role_log(const char* role, const char* message) {
#if !LORA_DEBUG_OUTPUT
  (void)role;
  (void)message;
  return;
#endif
  if (!updi_uart_enabled()) return;
#if defined(LORA_NONBLOCKING_LOG) && LORA_NONBLOCKING_LOG
  uint8_t role_len = 0, message_len = 0;
  while (role && role_len < 12 && role[role_len]) ++role_len;
  while (message && message_len < kUpdiRoleLogMessageLimit && message[message_len])
    ++message_len;
  if (sizeof(updi_log_queue) - updi_log_count < 5U + role_len + message_len) {
    if (updi_log_drops != UINT16_MAX) ++updi_log_drops;
    return;
  }
  updi_role_log_byte('[');
  for (uint8_t i = 0; i < role_len; ++i) updi_role_log_byte(role[i]);
  updi_role_log_byte(']');
  updi_role_log_byte(' ');
  for (uint8_t i = 0; i < message_len; ++i) updi_role_log_byte(message[i]);
  updi_role_log_byte('\r');
  updi_role_log_byte('\n');
#else

  updi_uart_tx('[');
  for (uint8_t i = 0; role != nullptr && role[i] != '\0' && i < 12; ++i) {
    updi_uart_tx(static_cast<uint8_t>(role[i]));
  }
  updi_uart_tx(']');
  updi_uart_tx(' ');
  for (uint8_t i = 0; message != nullptr && message[i] != '\0' &&
                       i < kUpdiRoleLogMessageLimit;
       ++i) {
    updi_uart_tx(static_cast<uint8_t>(message[i]));
  }
  updi_uart_tx('\r');
  updi_uart_tx('\n');
#endif
}

// Logs the SX127x RegVersion value as two uppercase hexadecimal digits.
inline void updi_role_log_radio_version(const char* role, uint8_t version) {
  char message[32];
  char hex[3];
  updi_role_log_format_hex(hex, version, 2);
  snprintf(message, sizeof(message), "RADIO_SPI_VERSION=0x%s", hex);
  updi_role_log(role, message);
}

// Logs one named event with the supplied radio or protocol status code.
inline void updi_role_log_status(const char* role, const char* event,
                                 int16_t status) {
  char message[48];
  snprintf(message, sizeof(message), "%s E=%d", event,
           static_cast<int>(status));
  updi_role_log(role, message);
}

// Emits profile, modulation, and frame lines. Frequency is MHz, power is dBm,
// bandwidth is kHz, and preamble length is symbols.
inline void updi_role_log_radio_profile(const char* role, float frequency_mhz,
                                        int8_t tx_power_dbm,
                                        uint8_t spreading_factor,
                                        uint16_t bandwidth_khz,
                                        uint8_t coding_rate, uint8_t sync_word,
                                        uint8_t preamble_symbols,
                                        bool crc_enabled, bool iq_inverted) {
  const int32_t frequency_centi_mhz =
      static_cast<int32_t>(frequency_mhz * 100.0f + 0.5f);
  char message[48];
  snprintf(message, sizeof(message), "RADIO_PROFILE F100=%ld P=%d",
           static_cast<long>(frequency_centi_mhz),
           static_cast<int>(tx_power_dbm));
  updi_role_log(role, message);
  snprintf(message, sizeof(message), "RADIO_MOD SF=%u BW=%u CR=%u",
           static_cast<unsigned>(spreading_factor),
           static_cast<unsigned>(bandwidth_khz),
           static_cast<unsigned>(coding_rate));
  updi_role_log(role, message);
  char sync_hex[3];
  updi_role_log_format_hex(sync_hex, sync_word, 2);
  snprintf(
      message, sizeof(message), "RADIO_FRAME SW=%s PRE=%u CRC=%u HDR=E IQ=%u",
      sync_hex, static_cast<unsigned>(preamble_symbols),
      static_cast<unsigned>(crc_enabled), static_cast<unsigned>(iq_inverted));
  updi_role_log(role, message);
}

// Logs a compact build/date/time marker; all strings are borrowed for the call.
inline void updi_role_log_boot(const char* role, const char* build,
                               const char* date, const char* time) {
  char message[48];
  snprintf(message, sizeof(message), "BOOT %s %s %s", build, date, time);
  updi_role_log(role, message);
}

// Returns CRC-8/ATM (polynomial 0x07, initial value zero) over the exact V1
// identity fields. Any null component returns zero.
inline uint8_t updi_role_log_identity_crc8(const char* role, const char* build,
                                           const char* date, const char* time) {
  const char* parts[] = {role, "|", "V1", "|", build, "|", date, "|", time};
  uint8_t crc = 0;
  for (const char* part : parts) {
    if (part == nullptr) return 0;
    while (*part != '\0') {
      crc ^= static_cast<uint8_t>(*part++);
      for (uint8_t bit = 0; bit < 8; ++bit) {
        crc = static_cast<uint8_t>((crc & 0x80U) != 0 ? (crc << 1) ^ 0x07U
                                                      : crc << 1);
      }
    }
  }
  return crc;
}

// Emits a V1 identity record with CRC; null fields are ignored.
inline void updi_role_log_identity(const char* role, const char* build,
                                   const char* date, const char* time) {
  if (role == nullptr || build == nullptr || date == nullptr || time == nullptr)
    return;
  char message[48];
  const uint8_t crc = updi_role_log_identity_crc8(role, build, date, time);
  char crc_hex[3];
  updi_role_log_format_hex(crc_hex, crc, 2);
  snprintf(message, sizeof(message), "ID V1 %s %s %s CRC=%s", build, date, time,
           crc_hex);
  updi_role_log(role, message);
}

// Logs a 16-bit campaign identifier as four uppercase hexadecimal digits.
inline void updi_role_log_campaign(const char* role, const char* event,
                                   uint16_t campaign_id) {
  char message[48];
  char campaign_hex[5];
  updi_role_log_format_hex(campaign_hex, campaign_id, 4);
  snprintf(message, sizeof(message), "%s C=%s", event, campaign_hex);
  updi_role_log(role, message);
}

// Logs campaign, sequence, and bounded-attempt correlation fields.
inline void updi_role_log_packet(const char* role, const char* event,
                                 uint16_t campaign_id, uint8_t sequence,
                                 uint8_t attempt) {
  char message[48];
  char campaign_hex[5];
  char sequence_hex[3];
  updi_role_log_format_hex(campaign_hex, campaign_id, 4);
  updi_role_log_format_hex(sequence_hex, sequence, 2);
  snprintf(message, sizeof(message), "%s C=%s S=%s A=%u", event, campaign_hex,
           sequence_hex, static_cast<unsigned>(attempt));
  updi_role_log(role, message);
}

// Return the largest exact payload that fits one role-log record.
inline uint8_t updi_role_log_payload_limit() {
  char prefix[96];
  const int prefix_size = snprintf(
      prefix, sizeof(prefix),
      "PAYLOAD_BYTES SID=FFFF T=%lu TYPE=%u Q=%u LEN=%u HEX=",
      static_cast<unsigned long>(UINT32_MAX), static_cast<unsigned>(UINT8_MAX),
      static_cast<unsigned>(UINT8_MAX), static_cast<unsigned>(UINT8_MAX));
  if (prefix_size < 0 ||
      static_cast<size_t>(prefix_size) >= kUpdiRoleLogMessageLimit)
    return 0U;
  return static_cast<uint8_t>(
      (kUpdiRoleLogMessageLimit - static_cast<size_t>(prefix_size)) / 2U);
}

// Logs exact payload bytes as hex; printable text is decoded by the host.
inline void updi_role_log_payload(const char* role, const char* event,
                                  uint16_t campaign_id, uint32_t time_ms,
                                  uint8_t type, uint8_t sequence,
                                  const uint8_t* payload,
                                  uint8_t payload_size) {
  if (!updi_uart_enabled() || event == nullptr || payload == nullptr ||
      payload_size > updi_role_log_payload_limit())
    return;

  char message[128];
  char campaign_hex[5];
  updi_role_log_format_hex(campaign_hex, campaign_id, 4);
  const int prefix_length = snprintf(
      message, sizeof(message), "%s SID=%s T=%lu TYPE=%u Q=%u LEN=%u HEX=",
      event, campaign_hex, static_cast<unsigned long>(time_ms),
      static_cast<unsigned>(type), static_cast<unsigned>(sequence),
      static_cast<unsigned>(payload_size));
  if (prefix_length < 0 ||
      static_cast<size_t>(prefix_length) >= sizeof(message)) {
    return;
  }

  static constexpr char hex[] = "0123456789ABCDEF";
  size_t position = static_cast<size_t>(prefix_length);
  for (uint8_t i = 0; i < payload_size; ++i) {
    if (position + 2 >= sizeof(message)) return;
    message[position++] = hex[payload[i] >> 4];
    message[position++] = hex[payload[i] & 0x0fU];
  }
  message[position] = '\0';
  updi_role_log(role, message);
}

// Logs measured radio airtime in microseconds for one packet attempt.
inline void updi_role_log_airtime(const char* role, const char* event,
                                  uint16_t campaign_id, uint8_t sequence,
                                  uint8_t attempt, uint32_t airtime_us) {
  char message[48];
  char campaign_hex[5];
  char sequence_hex[3];
  updi_role_log_format_hex(campaign_hex, campaign_id, 4);
  updi_role_log_format_hex(sequence_hex, sequence, 2);
  snprintf(message, sizeof(message), "%s C=%s S=%s A=%u TOA_US=%lu", event,
           campaign_hex, sequence_hex, static_cast<unsigned>(attempt),
           static_cast<unsigned long>(airtime_us));
  updi_role_log(role, message);
}

// Logs elapsed transaction time in milliseconds.
inline void updi_role_log_rtt(const char* role, const char* event,
                              uint16_t campaign_id, uint8_t sequence,
                              uint32_t elapsed_ms) {
  char message[48];
  char campaign_hex[5];
  char sequence_hex[3];
  updi_role_log_format_hex(campaign_hex, campaign_id, 4);
  updi_role_log_format_hex(sequence_hex, sequence, 2);
  snprintf(message, sizeof(message), "%s C=%s S=%s RTT=%lu", event,
           campaign_hex, sequence_hex, static_cast<unsigned long>(elapsed_ms));
  updi_role_log(role, message);
}

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_UPDI_UART_SRC_ROLE_LOG_H_
