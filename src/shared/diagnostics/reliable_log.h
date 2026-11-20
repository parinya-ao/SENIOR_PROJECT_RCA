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
/// Bounds each DATA fragment by both transport and exact-byte evidence capacity.
inline uint8_t InteractivePayloadLimit(uint8_t transport_limit) {
  const uint8_t log_limit = updi_role_log_payload_limit();
  return log_limit < transport_limit ? log_limit : transport_limit;
}

/// Reports the shared Echo contract for an available production radio.
inline void ReportInteractiveCapability(const char* role, const char* event,
                                        uint8_t transport_limit) {
  char line[64];
  snprintf(line, sizeof line, "%s MAX_DATA=%u ECHO=1", event,
           static_cast<unsigned>(InteractivePayloadLimit(transport_limit)));
  updi_role_log(role, line);
}


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

/// Takes a foreground SPI snapshot only for an idle, armed production radio.
inline void ReportRegisters(const char* role, LoRa& radio) {
  unsigned version_matches = 0;
  for (uint32_t i = 0; i < application_config::startup::kVersionProbeAttempts;
       ++i) {
    if (radio.read_register(0x42) == 0x12) ++version_matches;
  }
  const uint8_t pa = radio.read_register(0x09);
  const uint8_t ocp = radio.read_register(0x0B);
  const uint8_t lna = radio.read_register(0x0C);
  const uint8_t dac = radio.read_register(0x4D);
  char power[66];
  snprintf(power, sizeof power,
           "RADIO_POWER VERSIONS=%u PA=%02X OCP=%02X LNA=%02X DAC=%02X",
           version_matches, pa, ocp, lna, dac);
  updi_role_log(role, power);
  const uint8_t mode = radio.read_register(0x01);
  const uint8_t frf_msb = radio.read_register(0x06);
  const uint8_t frf_mid = radio.read_register(0x07);
  const uint8_t frf_lsb = radio.read_register(0x08);
  const uint8_t modem1 = radio.read_register(0x1D);
  const uint8_t modem2 = radio.read_register(0x1E);
  const uint8_t modem3 = radio.read_register(0x26);
  const uint16_t preamble =
      (static_cast<uint16_t>(radio.read_register(0x20)) << 8U) |
      radio.read_register(0x21);
  const uint8_t iq = radio.read_register(0x33);
  const uint8_t sync = radio.read_register(0x39);
  const uint8_t dio = radio.read_register(0x40);
  const uint8_t irq_mask = radio.read_register(0x11);
  char line[114];
  snprintf(line, sizeof line,
           "RADIO_REG MODE=%02X FRF=%02X%02X%02X MC=%02X%02X%02X PRE=%u "
           "IQ=%02X SYNC=%02X DIO=%02X MASK=%02X",
           mode, frf_msb, frf_mid, frf_lsb, modem1, modem2, modem3, preamble,
           iq, sync, dio, irq_mask);
  updi_role_log(role, line);
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
                       const uint8_t* accepted_payload,
                       uint8_t accepted_payload_size, uint8_t local_address,
                       uint8_t peer_address) {
  if (!event_queue.size() || !updi_uart_enabled()) return;
#if defined(LORA_NONBLOCKING_LOG) && LORA_NONBLOCKING_LOG
  // The Receiver can enqueue three lines for one validated DATA observation.
  if (!updi_role_log_has_space(3U * application_config::logging::kSlotBytes))
    return;
#endif
  radio_diagnostics::Event event{};
  if (!event_queue.Pop(&event)) return;
  char line[80];
  snprintf(line, sizeof line, "%s SID=%04X T=%lu TYPE=%u Q=%u E=%d", event.name,
           event.campaign_id, static_cast<unsigned long>(event.time_ms),
           event.type, event.sequence, event.error);
  updi_role_log(role, line);
  if (accepted_payload && !strcmp(event.name, "DATA_VALIDATED")) {
    updi_role_log_payload(role, "PAYLOAD_BYTES", event.campaign_id,
                          event.time_ms, event.type, event.sequence,
                          accepted_payload, accepted_payload_size);
    // DATA_VALIDATED follows decoded peer, destination and RadioLib CRC checks.
    snprintf(line, sizeof line,
             "DATA_ADDRESS SID=%04X T=%lu TYPE=%u Q=%u SRC=%u DST=%u CRC=OK",
             event.campaign_id, static_cast<unsigned long>(event.time_ms),
             event.type, event.sequence, peer_address, local_address);
    updi_role_log(role, line);
  }
}

}  // namespace radio_diagnostics
