/// @file
/// @brief Coordinates the SSOT transport for Gateway and Tracker variants.

#if defined(LORA_APP_RELIABLE)

#include "reliable_app.h"

#include <Arduino.h>
#include <features/diagnostics/radio_diagnostics.h>
#include <features/reliable_transfer/reliable_transport.h>
#include <stdio.h>
#include <string.h>

#include "application_config.h"
#include "generated/board_ssot.h"
#include "hello_config.h"
#include "lora.h"
#include "reliable_role.h"
#include "role_log.h"

// Radio and transport have application lifetime; setup performs all hardware
// I/O.
namespace reliable_app {

/// Addressed LoRa adapter owned by the active reliable application.
LoRa lora(LORA_PIN_CS, LORA_PIN_IRQ, LORA_PIN_RST, LORA_PIN_DIO1);
/// Shared transaction engine configured with the existing radio profile.
reliable::Transport<LoRa> transport(lora, HELLO_RF_FREQUENCY_MHZ,
                                    HELLO_RF_TX_POWER_DBM, HELLO_RF_LONG_RANGE);
/// Foreground readiness latch shared with the role-specific commands.
bool radio_ready = false;
static bool boot_logged = false;
#if !HELLO_RF_DIAGNOSTIC_ONLY
// Explicit diagnostic controls remain independent of protocol state.
static bool reject_data = false, spi_selected = false;
#endif
// Retains the last accepted bytes until their queued diagnostic is flushed.
static uint8_t accepted_payload[ssot::kHelloPayloadSize];
// Event storage is bounded; dropped diagnostics never change delivery state.
static radio_diagnostics::EventQueue event_queue;

/// @brief Queues one event observation without blocking radio work.
/// @param event Event name, type, sequence, and driver status from Transport.
/// @param type Wire message type.
/// @param sequence Wire sequence number.
/// @param error Radio driver status, or zero.
/// @post Queue overflow is counted by EventQueue and does not change delivery.
void RecordTransportEvent(void*, const char* event, uint8_t type,
                          uint8_t sequence, int16_t error) {
  event_queue.Push(
      {event, millis(), error, type, sequence, transport.campaign_id()});
}

/// @brief Formats and emits one queued event when radio work permits.
/// @post Removes at most one event from the bounded queue.
static void FlushTransportEvent() {
  if (!event_queue.size() || !updi_uart_enabled()) return;
  radio_diagnostics::Event event{};
  if (!event_queue.Pop(&event)) return;
  char line[80];
  snprintf(line, sizeof line, "%s SID=%04X T=%lu TYPE=%u Q=%u E=%d", event.name,
           event.campaign_id, static_cast<unsigned long>(event.time_ms),
           event.type, event.sequence, event.error);
  updi_role_log(kRole, line);
  if (!strcmp(event.name, "DATA_VALIDATED"))
    updi_role_log_payload(kRole, "PAYLOAD_BYTES", event.campaign_id,
                          event.sequence, accepted_payload,
                          sizeof accepted_payload);
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
/// @brief Accepts only the configured application payload.
/// @param sequence Received DATA sequence used for diagnostic correlation.
/// @param data Borrowed payload bytes, valid only for this callback.
/// @param length Number of readable payload bytes.
/// @return True only when the full configured payload matches.
/// @post Rejection is returned to Transport, which sends the protocol NACK.
bool AcceptData(void*, uint8_t sequence, const uint8_t* data, uint8_t length) {
  if (reject_data) {
    reject_data = false;
    RecordTransportEvent(nullptr, "DATA_REJECTED_TEST", ssot::kDataType,
                         sequence, 0);
    return false;
  }
  if (length != ssot::kHelloPayloadSize || !data ||
      memcmp(data, LORA_HELLO_PAYLOAD, length) != 0) {
    RecordTransportEvent(nullptr, "DATA_REJECTED_PAYLOAD", ssot::kDataType,
                         sequence, 0);
    return false;
  }
  memcpy(accepted_payload, data, length);
  return true;
}
#endif

/// @brief Configures role-specific GPIO and applies Tracker power sequencing.
/// @post Tracker peripherals are isolated before radio SPI is enabled.
static void InitializeGpio() {
  InitializeRoleGpio();
  pinModeFast(LORA_PIN_IRQ, INPUT);
  pinModeFast(LORA_PIN_DIO1, INPUT);
  digitalWriteFast(LORA_PIN_CS, HIGH);
  pinModeFast(LORA_PIN_CS, OUTPUT);
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
/// @brief Selects SPI once and arms the configured radio session.
/// @return True when Transport has initialized and armed the radio.
/// @post Receiver adopts its first DATA campaign; sender creates a new one.
bool ArmRadio() {
  if (!spi_selected) {
    if (!SPI.swap(LORA_SPI_ROUTE)) return false;
    spi_selected = true;
  }
  return ArmRole();
}
#endif

/// @brief Registers event reporting, initializes the board, and arms the role.
/// @post Receiver logs RX_READY only after successful radio arming.
void Initialize() {
  transport.SetEventCallback(RecordTransportEvent, nullptr);
  InitializeGpio();
#if HELLO_RF_DIAGNOSTIC_ONLY
  updi_role_log(kRole, "RADIO_INIT_SKIPPED_DIAGNOSTIC");
  updi_role_log(kRole, "RF_TX_DISABLED_DIAGNOSTIC");
#else
  radio_ready = ArmRadio();
  if (radio_ready) ReportRoleReadyAtStartup();
#endif
}

/// @brief Emits current radio configuration and diagnostic queue status.
/// @post Does not change radio or transport state.
static void ReportStatus() {
  updi_role_log(kRole, radio_ready ? "RADIO_INIT_OK" : "RADIO_INIT_FAILED");
  updi_role_log(kRole, "BUILD_ID=" LORA_BUILD_ID);
  updi_role_log(kRole, "CONFIG_FINGERPRINT=" LORA_CONFIG_FINGERPRINT);
  updi_role_log(kRole, "PROTOCOL_VERSION=" LORA_PROTOCOL_VERSION_TEXT);
  if (radio_ready) {
    updi_role_log_radio_version(kRole, lora.version());
    updi_role_log_radio_profile(
        kRole, HELLO_RF_FREQUENCY_MHZ, HELLO_RF_TX_POWER_DBM,
        HELLO_RF_SPREADING_FACTOR, HELLO_RF_BANDWIDTH_KHZ, HELLO_RF_CODING_RATE,
        HELLO_RF_SYNC_WORD, HELLO_RF_PREAMBLE_SYMBOLS, HELLO_RF_CRC_ENABLED,
        HELLO_RF_IQ_INVERTED);
  }
  updi_role_log(kRole, radio_ready ? "RADIO_READY" : "RADIO_NOT_READY");
  if (event_queue.overflow_count()) {
    char line[32];
    snprintf(line, sizeof line, "LOG_OVERFLOW N=%u",
             static_cast<unsigned>(event_queue.overflow_count()));
    updi_role_log(kRole, line);
  }
}

/// @brief Emits startup identity once after a serial monitor becomes available.
/// @post Later status requests do not clear the one-time boot marker.
static void ReportBoot() {
  if (boot_logged || !updi_uart_enabled()) return;
  updi_role_log_identity(kRole, kFirmware, __DATE__, __TIME__);
  updi_role_log_boot(kRole, kFirmware, __DATE__, __TIME__);
  updi_role_log(kRole, "BUILD_ID=" LORA_BUILD_ID);
  updi_role_log(kRole, "CONFIG_FINGERPRINT=" LORA_CONFIG_FINGERPRINT);
  updi_role_log(kRole, "PROTOCOL_VERSION=" LORA_PROTOCOL_VERSION_TEXT);
#if HELLO_RF_DIAGNOSTIC_ONLY
  updi_role_log(kRole, "RF_TX_DISABLED_DIAGNOSTIC");
#else
  updi_role_log(kRole, radio_ready ? "RADIO_INIT_OK" : "RADIO_INIT_FAILED");
  if (radio_ready) {
    updi_role_log_radio_version(kRole, lora.version());
    updi_role_log_radio_profile(
        kRole, HELLO_RF_FREQUENCY_MHZ, HELLO_RF_TX_POWER_DBM,
        HELLO_RF_SPREADING_FACTOR, HELLO_RF_BANDWIDTH_KHZ, HELLO_RF_CODING_RATE,
        HELLO_RF_SYNC_WORD, HELLO_RF_PREAMBLE_SYMBOLS, HELLO_RF_CRC_ENABLED,
        HELLO_RF_IQ_INVERTED);
    updi_role_log(kRole, kReadyEvent);
  }
#endif
  boot_logged = true;
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
/// @brief Applies one foreground diagnostic command.
/// @param command Command byte polled from the host UART.
/// @post Fault-injection controls affect only their documented next operation.
static void HandleRadioCommand(char command) {
  switch (command) {
    case 'P': {
      const int16_t error = transport.Stop();
      radio_ready = false;
      updi_role_log_status(kRole, "PARKED", error);
      break;
    }
    case 'N':
      reject_data = true;
      break;
    case 'A':
      reject_data = false;
      break;
    case 'D':
      transport.SuppressNextResponse();
      break;
    case 'R':
      radio_ready = ArmRadio();
      ResetRoleTransaction();
      updi_role_log(kRole, radio_ready ? "RX_READY" : "RADIO_INIT_FAILED");
      break;
    default:
      HandleRoleCommand(command);
      break;
  }
}
#endif

/// @brief Services transport, host commands, and deferred events once.
/// @post Radio polling precedes commands and event output remains deferred
///   while a transaction is active.
void Poll() {
#if defined(LORA_NONBLOCKING_LOG) && LORA_NONBLOCKING_LOG
  if (!transport.IsActive()) updi_role_log_service();
#endif
  ReportBoot();
#if HELLO_RF_DIAGNOSTIC_ONLY
  PollRoleLeds(millis(), false);
#else
  const uint32_t now = millis();
  PollRoleRadio(now);
  if (transport.state() == decltype(transport)::State::kFailed)
    radio_ready = false;
  PollRoleLeds(now, transport.IsTransmitting());
#endif
  while (updi_uart_rx_poll()) {
    const char command = static_cast<char>(updi_uart_rx());
#if !HELLO_RF_DIAGNOSTIC_ONLY
    if (RoleCommandPending()) continue;
#endif
    if (command == '?') {
      ReportStatus();
      continue;
    }
#if !HELLO_RF_DIAGNOSTIC_ONLY
    HandleRadioCommand(command);
#endif
  }
  if (!transport.IsActive()) FlushTransportEvent();
}

}  // namespace reliable_app

#endif  // LORA_APP_RELIABLE
