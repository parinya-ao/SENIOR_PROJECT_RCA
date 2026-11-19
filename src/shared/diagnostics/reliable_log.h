#pragma once

#include <Arduino.h>
#include <stdio.h>
#include <string.h>

#include "hello_config.h"
#include "radio_diagnostics.h"
#include "role_log.h"
#include "shared/radio/radio_link.h"
#include "ssot.h"

namespace radio_diagnostics {

// The UPDI logger's queue is local to the role's translation unit.
// Emits the configured build, PHY fingerprint, and protocol identity.
static void ReportConfig(const char* role) {
  updi_role_log(role, "BUILD_ID=" LORA_BUILD_ID);
  updi_role_log(role, "CONFIG_FINGERPRINT=" LORA_CONFIG_FINGERPRINT);
  updi_role_log(role, "PROTOCOL_VERSION=" LORA_PROTOCOL_VERSION_TEXT);
}

// Emits the live driver version and the configured PHY values.
static void ReportPhy(const char* role, const LoRa& radio) {
  updi_role_log_radio_version(role, radio.version());
  updi_role_log_radio_profile(role, HELLO_RF_FREQUENCY_MHZ,
                              HELLO_RF_TX_POWER_DBM, HELLO_RF_SPREADING_FACTOR,
                              HELLO_RF_BANDWIDTH_KHZ, HELLO_RF_CODING_RATE,
                              HELLO_RF_SYNC_WORD, HELLO_RF_PREAMBLE_SYMBOLS,
                              HELLO_RF_CRC_ENABLED, HELLO_RF_IQ_INVERTED);
}

/// Emits the build identity and startup marker for the selected application.
inline void ReportIdentity(const char* role, const char* firmware) {
  updi_role_log_identity(role, firmware, __DATE__, __TIME__);
  updi_role_log_boot(role, firmware, __DATE__, __TIME__);
  ReportConfig(role);
}

/// Emits configuration identity and the PHY profile when initialized.
inline void ReportRadioProfile(const char* role, const LoRa& radio,
                               bool ready) {
  updi_role_log(role, ready ? "RADIO_INIT_OK" : "RADIO_INIT_FAILED");
  if (ready) ReportPhy(role, radio);
}

/// Emits readiness and any bounded logger overflow for a status request.
inline void ReportRadioStatus(const char* role, const LoRa& radio,
                              bool radio_ready, const EventQueue& event_queue) {
  updi_role_log(role, radio_ready ? "RADIO_INIT_OK" : "RADIO_INIT_FAILED");
  ReportConfig(role);
  if (radio_ready) ReportPhy(role, radio);
  updi_role_log(role, radio_ready ? "RADIO_READY" : "RADIO_NOT_READY");
  if (event_queue.overflow_count()) {
    char line[32];
    snprintf(line, sizeof line, "LOG_OVERFLOW N=%u",
             static_cast<unsigned>(event_queue.overflow_count()));
    updi_role_log(role, line);
  }
}

/// Emits at most one queued observation when UPDI is available.
inline void FlushEvent(EventQueue& event_queue, const char* role,
                       const uint8_t* accepted_payload) {
  if (!event_queue.size() || !updi_uart_enabled()) return;
  radio_diagnostics::Event event{};
  if (!event_queue.Pop(&event)) return;
  char line[80];
  snprintf(line, sizeof line, "%s SID=%04X T=%lu TYPE=%u Q=%u E=%d", event.name,
           event.campaign_id, static_cast<unsigned long>(event.time_ms),
           event.type, event.sequence, event.error);
  updi_role_log(role, line);
  if (!strcmp(event.name, "DATA_VALIDATED"))
    updi_role_log_payload(role, "PAYLOAD_BYTES", event.campaign_id,
                          event.sequence, accepted_payload,
                          ssot::kHelloPayloadSize);
}

}  // namespace radio_diagnostics
