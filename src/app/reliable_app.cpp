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
#include "campaign_id.h"
#include "hello_config.h"
#include "lora.h"
#include "role_log.h"
#include "status_leds.h"

#if defined(LORA_ROLE_RECEIVER)
#include "generated/lora_receiver_board.h"
#include "tracker_config.h"
#if !HELLO_RF_DIAGNOSTIC_ONLY
static constexpr uint8_t kLocalAddress = LORA_RECEIVER_ADDRESS;
static constexpr uint8_t kPeerAddress = LORA_SENDER_ADDRESS;
#endif
static const char kRole[] = "RECEIVER";
static const char kFirmware[] = "receiver";
static status_leds::Controller led_status(
    LORA_PIN_LED1, LORA_PIN_LED2, tracker_cfg::SystemConstants::LED_ON_LEVEL,
    tracker_cfg::SystemConstants::LED_OFF_LEVEL,
    tracker_cfg::SystemConstants::LED1_TOGGLE_INTERVAL_MS,
    tracker_cfg::SystemConstants::LORA_TX_LED_TOGGLE_INTERVAL_MS);
#else
#include "gateway_ssot.hpp"
#include "generated/lora_sender_board.h"
#if !HELLO_RF_DIAGNOSTIC_ONLY
static constexpr uint8_t kLocalAddress = LORA_SENDER_ADDRESS;
static constexpr uint8_t kPeerAddress = LORA_RECEIVER_ADDRESS;
#endif
static const char kRole[] = "GATEWAY";
static const char kFirmware[] = "sender_hello";
static status_leds::Controller led_status(
    GatewaySSOT::Pins::LED1, GatewaySSOT::Pins::LED2,
    GatewaySSOT::Pins::LED_ON_LEVEL, GatewaySSOT::Pins::LED_OFF_LEVEL,
    GatewaySSOT::Tasks::LED1_TOGGLE_INTERVAL_MS,
    GatewaySSOT::Tasks::LORA_TX_LED_TOGGLE_INTERVAL_MS);
#endif

// Radio and transport have application lifetime; setup performs all hardware
// I/O.
namespace reliable_app {

static LoRa lora(LORA_PIN_CS, LORA_PIN_IRQ, LORA_PIN_RST, LORA_PIN_DIO1);
static reliable::Transport<LoRa> transport(lora, HELLO_RF_FREQUENCY_MHZ,
                                           HELLO_RF_TX_POWER_DBM,
                                           HELLO_RF_LONG_RANGE);
// Foreground lifecycle latches; no ISR reads or writes these values.
static bool radio_ready = false, boot_logged = false;
#if !HELLO_RF_DIAGNOSTIC_ONLY
// Explicit diagnostic controls remain independent of protocol state.
static bool reject_data = false, spi_selected = false;
static bool completion_reported = false;
static uint8_t tx_sequence = ssot::kSequence;
#if !defined(LORA_ROLE_RECEIVER) && HELLO_TEST_MODE
static constexpr Address kWrongDestinationAddress = 2;
static_assert(kWrongDestinationAddress != LORA_SENDER_ADDRESS &&
                  kWrongDestinationAddress != LORA_RECEIVER_ADDRESS &&
                  kWrongDestinationAddress != UINT8_MAX,
              "wrong-destination test address must be a distinct unicast");
static bool wrong_destination_tx_pending = false;
static uint32_t wrong_destination_started_at = 0;
#endif
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
static void RecordTransportEvent(void*, const char* event, uint8_t type,
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
static bool AcceptData(void*, uint8_t sequence, const uint8_t* data,
                       uint8_t length) {
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
#if defined(LORA_ROLE_RECEIVER)
  digitalWriteFast(LORA_PIN_ENABLE, !LORA_POWER_ACTIVE_LEVEL);
  digitalWriteFast(LORA_PIN_GPS_ENABLE, HIGH);
  digitalWriteFast(LORA_PIN_SD_ENABLE, HIGH);
  pinModeFast(LORA_PIN_ENABLE, OUTPUT);
  pinModeFast(LORA_PIN_GPS_ENABLE, OUTPUT);
  pinModeFast(LORA_PIN_SD_ENABLE, OUTPUT);
  pinModeFast(LORA_PIN_SD_DETECT, INPUT);
  pinModeFast(LORA_PIN_RST, INPUT);
  led_status.Begin(millis());
  digitalWriteFast(LORA_PIN_SD_CS, HIGH);
  pinModeFast(LORA_PIN_SD_CS, OUTPUT);
  digitalWriteFast(LORA_PIN_ENABLE, LORA_POWER_ACTIVE_LEVEL);
  delay(application_config::startup::kRadioSettleMs);
#else
  led_status.Begin(millis());
#endif
  pinModeFast(LORA_PIN_IRQ, INPUT);
  pinModeFast(LORA_PIN_DIO1, INPUT);
  digitalWriteFast(LORA_PIN_CS, HIGH);
  pinModeFast(LORA_PIN_CS, OUTPUT);
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
/// @brief Selects SPI once and arms the configured radio session.
/// @return True when Transport has initialized and armed the radio.
/// @post Receiver adopts its first DATA campaign; sender creates a new one.
static bool ArmRadio() {
  if (!spi_selected) {
    if (!SPI.swap(LORA_SPI_ROUTE)) return false;
    spi_selected = true;
  }
#if defined(LORA_ROLE_RECEIVER)
  return transport.Arm(kLocalAddress, kPeerAddress, AcceptData, nullptr);
#else
  return transport.Arm(kLocalAddress, kPeerAddress, AcceptData, nullptr,
                       lora_app::NextCampaignId(LORA_BUILD_ID));
#endif
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
#if defined(LORA_ROLE_RECEIVER)
  if (radio_ready) updi_role_log(kRole, "RX_READY");
#endif
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
#if defined(LORA_ROLE_RECEIVER)
    updi_role_log(kRole, "RX_READY");
#else
    updi_role_log(kRole, "WAIT_START");
#endif
  }
#endif
  boot_logged = true;
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
#if !defined(LORA_ROLE_RECEIVER) && HELLO_TEST_MODE
/// @brief Polls the wrong-destination diagnostic transmission.
/// @param now Wrapping millisecond counter used for the TX timeout.
/// @post Timeout or driver failure parks the radio and marks it unready.
static void PollWrongDestination(uint32_t now) {
  const int16_t status = lora.send_done();
  if (status == 1) {
    wrong_destination_tx_pending = false;
    updi_role_log(kRole, "WRONG_DEST_TX_DONE");
  } else if (status < 0) {
    wrong_destination_tx_pending = false;
    radio_ready = false;
    updi_role_log_status(kRole, "WRONG_DEST_TX_FAILED", status);
  } else if (now - wrong_destination_started_at >= LORA_TX_TIMEOUT_MS) {
    wrong_destination_tx_pending = false;
    radio_ready = false;
    const int16_t stopped = lora.sleep();
    updi_role_log(kRole, "WRONG_DEST_TX_TIMEOUT");
    updi_role_log_status(kRole, "WRONG_DEST_SLEEP", stopped);
  }
}

/// @brief Starts the test DATA frame with a deliberately wrong destination.
/// @post Uses the configured PHY but does not open an ACK window or retry.
static void SendWrongDestination() {
  if (!radio_ready || transport.IsActive()) return;
  uint8_t packet[2 + ssot::kHelloPayloadSize] = {ssot::kDataType,
                                                 ssot::kSequence};
  memcpy(packet + 2, LORA_HELLO_PAYLOAD, ssot::kHelloPayloadSize);
  char line[64];
  snprintf(line, sizeof line,
           "WRONG_DEST_TX_BEGIN DST=%u TYPE=%02X Q=%u APP=%u",
           kWrongDestinationAddress, ssot::kDataType, ssot::kSequence,
           static_cast<unsigned>(ssot::kHelloPayloadSize));
  updi_role_log(kRole, line);
  const int16_t status =
      lora.send(kWrongDestinationAddress, transport.campaign_id(), packet,
                static_cast<uint8_t>(sizeof packet));
  if (status < 0) {
    radio_ready = false;
    updi_role_log_status(kRole, "WRONG_DEST_TX_FAILED", status);
    return;
  }
  wrong_destination_started_at = millis();
  wrong_destination_tx_pending = true;
}
#endif

/// @brief Polls radio work and advances the sender sequence on matching ACK.
/// @param now Wrapping millisecond counter used by the transport deadlines.
static void PollRadio(uint32_t now) {
#if !defined(LORA_ROLE_RECEIVER) && HELLO_TEST_MODE
  if (wrong_destination_tx_pending)
    PollWrongDestination(now);
  else
#endif
    transport.Poll(now);
  if (transport.state() == decltype(transport)::State::kFailed)
    radio_ready = false;
  if (transport.result() == decltype(transport)::Result::kAccepted &&
      !completion_reported) {
    completion_reported = true;
    ++tx_sequence;
  }
  led_status.Poll(now, transport.IsTransmitting());
}

#if !defined(LORA_ROLE_RECEIVER)
/// @brief Starts one bounded DATA transaction from the configured payload.
/// @post Starts a new campaign before sequence zero could be sent on the wire.
static void RequestData() {
  if (!radio_ready || transport.IsActive()) return;
  if (tx_sequence == 0) {
    radio_ready = ArmRadio();
    if (!radio_ready) return;
    tx_sequence = ssot::kSequence;
  }
  completion_reported = false;
  if (transport.SendReliableData(
          tx_sequence, reinterpret_cast<const uint8_t*>(LORA_HELLO_PAYLOAD),
          ssot::kHelloPayloadSize, millis()))
    RecordTransportEvent(nullptr, "DATA_TX_REQUESTED", ssot::kDataType,
                         tx_sequence, 0);
}
#endif

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
      completion_reported = false;
      tx_sequence = ssot::kSequence;
      updi_role_log(kRole, radio_ready ? "RX_READY" : "RADIO_INIT_FAILED");
      break;
#if !defined(LORA_ROLE_RECEIVER)
    case 'S':
      RequestData();
      break;
#if HELLO_TEST_MODE
    case 'W':
      SendWrongDestination();
      break;
#endif
#endif
    default:
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
  led_status.Poll(millis(), false);
#else
  PollRadio(millis());
#endif
  while (updi_uart_rx_poll()) {
    const char command = static_cast<char>(updi_uart_rx());
#if !HELLO_RF_DIAGNOSTIC_ONLY && !defined(LORA_ROLE_RECEIVER) && HELLO_TEST_MODE
    if (wrong_destination_tx_pending) continue;
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
