// Board-owned startup and reliable transport actions.
#if defined(LORA_APP_RELIABLE)

#include "reliable.h"

#include <Arduino.h>
#include <status_leds.h>
#include <string.h>

#include "application_config.h"
#include "generated/lora_receiver_board.h"
#include "hello_config.h"
#include "role_log.h"
#include "shared/diagnostics/reliable_log.h"
#include "shared/protocol/reliable_transport.h"
#include "shared/radio/radio_link.h"
#include "tracker_config.h"

namespace reliable_app {

static const char kRole[] = "RECEIVER";
static const char kFirmware[] = "receiver";
/// Addressed LoRa adapter owned by the active reliable application.
static LoRa lora(LORA_PIN_CS, LORA_PIN_IRQ, LORA_PIN_RST, LORA_PIN_DIO1);
/// Shared transaction engine configured with the existing radio profile.
using Transport = reliable::Transport<LoRa>;
static Transport transport(lora, HELLO_RF_FREQUENCY_MHZ, HELLO_RF_TX_POWER_DBM,
                           HELLO_RF_LONG_RANGE);
/// Foreground readiness latch shared with the role-specific commands.
static bool radio_ready = false;
static bool boot_logged = false;
#if !HELLO_RF_DIAGNOSTIC_ONLY
// Explicit diagnostic controls remain independent of protocol state.
static bool reject_data = false, spi_selected = false;
static bool bench = false, park_requested = false, leave_bench = false;
static bool bench_reply_enabled = false;
static bool fresh_campaign = false;
static bool interactive_mode = false;
static bool echo_pending = false;
static bool echo_confirmed = false;
static uint8_t echo_sequence = 0U;
static uint16_t echo_campaign = 0U;
static uint32_t echo_wait_started = 0U;
#endif
// Retains the last accepted bytes until their queued diagnostic is flushed.
static uint8_t accepted_payload[Transport::kMaxData];
static uint8_t accepted_payload_size = 0U;
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
      {event, millis(), error, type, sequence, transport.event_campaign_id()});
#if !HELLO_RF_DIAGNOSTIC_ONLY
  if (interactive_mode && echo_pending &&
      strcmp(event, "ACK_CONFIRM_RX") == 0 && type == ssot::kAckType &&
      sequence == echo_sequence && transport.event_campaign_id() == echo_campaign)
    echo_confirmed = true;
#endif
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
/// @brief Accepts the legacy payload or one bounded interactive message chunk.
/// @param sequence Received DATA sequence used for diagnostic correlation.
/// @param data Borrowed payload bytes, valid only for this callback.
/// @param length Number of readable payload bytes.
/// @return True only for a supported, nonempty payload within the log evidence bound.
/// @post Rejection is returned to Transport, which sends the protocol NACK.
static bool AcceptData(void*, uint8_t sequence, const uint8_t* data,
                       uint8_t length) {
  if (reject_data) {
    reject_data = false;
    RecordTransportEvent(nullptr, "DATA_REJECTED_TEST", ssot::kDataType,
                         sequence, 0);
    return false;
  }
  const uint8_t log_limit =
      radio_diagnostics::InteractivePayloadLimit(Transport::kMaxData);
  if (!data || !length || length > log_limit || (interactive_mode && echo_pending) ||
      (!interactive_mode &&
       (length != ssot::kHelloPayloadSize ||
        memcmp(data, LORA_HELLO_PAYLOAD, ssot::kHelloPayloadSize) != 0))) {
    RecordTransportEvent(nullptr, "DATA_REJECTED_PAYLOAD", ssot::kDataType,
                         sequence, 0);
    return false;
  }
  memcpy(accepted_payload, data, length);
  accepted_payload_size = length;
  if (interactive_mode) {
    echo_pending = true;
    echo_confirmed = false;
    echo_sequence = sequence;
    echo_campaign = transport.event_campaign_id();
    echo_wait_started = millis();
  }
  return true;
}

#endif

static status_leds::Controller led_status(
    LORA_PIN_LED1, LORA_PIN_LED2, tracker_cfg::SystemConstants::LED_ON_LEVEL,
    tracker_cfg::SystemConstants::LED_OFF_LEVEL,
    tracker_cfg::SystemConstants::LED1_TOGGLE_INTERVAL_MS,
    tracker_cfg::SystemConstants::LORA_TX_LED_TOGGLE_INTERVAL_MS);

// Configures board-owned GPIO and the LED controller.
static void InitializeRoleGpio() {
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
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
static const char kReadyEvent[] = "RX_READY";

/// @brief Selects SPI once and arms the configured radio session.
/// @return True when Transport has initialized and armed the radio.
/// @post Receiver adopts its first DATA campaign; sender creates a new one.
static bool ArmRadio() {
  if (!spi_selected) {
    if (!SPI.swap(LORA_SPI_ROUTE)) return false;
    spi_selected = true;
  }
  const uint16_t binding = fresh_campaign ? 0 : transport.campaign_id();
  if (!transport.Arm(LORA_RECEIVER_ADDRESS, LORA_SENDER_ADDRESS, AcceptData,
                     nullptr, binding))
    return false;
  fresh_campaign = false;
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
  if (radio_ready) updi_role_log(kRole, kReadyEvent);
#endif
}

/// @brief Emits startup identity once after a serial monitor becomes available.
/// @post Later status requests do not clear the one-time boot marker.
static void ReportBoot() {
  if (boot_logged || !updi_uart_enabled()) return;
  radio_diagnostics::ReportIdentity(kRole, kFirmware);
#if HELLO_RF_DIAGNOSTIC_ONLY
  updi_role_log(kRole, "RF_TX_DISABLED_DIAGNOSTIC");
#else
  radio_diagnostics::ReportRadioProfile(kRole, lora, radio_ready);
  if (radio_ready) updi_role_log(kRole, kReadyEvent);
#endif
  boot_logged = true;
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
/// @brief Applies one foreground diagnostic command.
/// @param command Command byte polled from the host UART.
/// @post Fault-injection controls affect only their documented next operation.
static void HandleRadioCommand(char command) {
  using Fault = decltype(transport)::ResponseFault;
  if (transport.IsActive() && command != 'P' && command != 'E') return;
  switch (command) {
    case 'B':
      if (!bench) {
        bench = true;
        bench_reply_enabled = false;
        fresh_campaign = true;
        interactive_mode = false;
        echo_pending = echo_confirmed = false;
        accepted_payload_size = 0U;
        event_queue.Clear();
        updi_role_log(kRole, "BENCH_READY");
      }
      break;
    case 'E':
    case 'P':
      park_requested = true;
      bench_reply_enabled = false;
      leave_bench = command == 'E';
      reject_data = false;
      interactive_mode = false;
      echo_pending = echo_confirmed = false;
      accepted_payload_size = 0U;
      transport.SetResponseFault(Fault::kNone);
      break;
    case 'V':
      if (bench && !park_requested)
        radio_diagnostics::ReportInteractiveCapability(
            kRole, "INTERACTIVE_CAPS", Transport::kMaxData);
      break;
    case 'I':
      if (bench && radio_ready && !park_requested && !echo_pending) {
        interactive_mode = true;
        radio_diagnostics::ReportInteractiveCapability(
            kRole, "INTERACTIVE_READY", Transport::kMaxData);
      }
      break;
    case 'T':
      if (bench && radio_ready && !park_requested) {
        bench_reply_enabled = true;
        updi_role_log(kRole, "BENCH_TX_READY");
      }
      break;
    case 'N':
      if (bench && !park_requested) reject_data = true;
      break;
    case 'A':
      reject_data = false;
      break;
    case 'D':
      if (bench && !park_requested) transport.SetResponseFault(Fault::kDrop);
      break;
    case 'C':
      if (bench && !park_requested)
        transport.SetResponseFault(Fault::kCampaign);
      break;
    case 'Q':
      if (bench && !park_requested)
        transport.SetResponseFault(Fault::kSequence);
      break;
    case 'U':
      if (bench && !park_requested)
        transport.SetResponseFault(Fault::kDuplicate);
      break;
    case 'R':
      if (park_requested) break;
      radio_ready = ArmRadio();
      updi_role_log(kRole, radio_ready ? "RX_READY" : "RADIO_INIT_FAILED");
      break;
    default:
      break;
  }
}
#endif

/// @brief Services transport, host commands, and deferred events once.
/// @post Radio polling precedes commands; Echo diagnostics can drain in RX.
void Poll() {
#if defined(LORA_NONBLOCKING_LOG) && LORA_NONBLOCKING_LOG
  bool service_log = !transport.IsActive();
#if !HELLO_RF_DIAGNOSTIC_ONLY
  service_log |= interactive_mode && !transport.IsTransmitting();
#endif
  if (service_log) updi_role_log_service();
#endif
  ReportBoot();
#if HELLO_RF_DIAGNOSTIC_ONLY
  led_status.Poll(millis(), false);
#else
  const uint32_t now = millis();
  transport.Poll(now, !bench || bench_reply_enabled);
  if (transport.state() == decltype(transport)::State::kFailed)
    radio_ready = false;
  // Keep the validated bytes through the forward ARQ and confirmation budgets.
  if (echo_pending && !echo_confirmed &&
      now - echo_wait_started >= 2U * Transport::kTransactionTimeoutMs) {
    char line[72];
    snprintf(line, sizeof line,
             "ACK_CONFIRM_TIMEOUT SID=%04X T=%lu TYPE=%u Q=%u E=-1",
             echo_campaign, static_cast<unsigned long>(now), ssot::kAckType,
             echo_sequence);
    updi_role_log(kRole, line);
    echo_pending = false;
  }
  if (interactive_mode && echo_pending && echo_confirmed &&
      transport.state() == decltype(transport)::State::kRxWait &&
      !transport.IsActive()) {
    echo_pending = false;
    if (!transport.SendReliableData(echo_sequence, accepted_payload,
                                    accepted_payload_size, now)) {
      radio_ready = false;
      updi_role_log(kRole, "ECHO_DATA_START_FAILED");
    }
  }
  led_status.Poll(now, transport.IsTransmitting());
#endif
  while (updi_uart_rx_poll()) {
    const char command = static_cast<char>(updi_uart_rx());
    if (command == '?') {
      if (transport.IsActive()) continue;
      radio_diagnostics::ReportRadioStatus(kRole, lora, radio_ready,
                                           event_queue);
#if !HELLO_RF_DIAGNOSTIC_ONLY
      if (bench && radio_ready) {
        char pins[38];
        snprintf(pins, sizeof pins, "TRACKER_GPIO LORA_EN=%d SD_CS=%d",
                 digitalReadFast(LORA_PIN_ENABLE),
                 digitalReadFast(LORA_PIN_SD_CS));
        updi_role_log(kRole, pins);
        radio_diagnostics::ReportRegisters(kRole, lora);
      }
#endif
      continue;
    }
#if !HELLO_RF_DIAGNOSTIC_ONLY
    HandleRadioCommand(command);
#endif
  }
#if !HELLO_RF_DIAGNOSTIC_ONLY
  if (park_requested && !transport.IsTransmitting()) {
    if (spi_selected) static_cast<void>(transport.Stop());
    radio_ready = false;
    park_requested = false;
    if (leave_bench) bench = false;
    interactive_mode = false;
    echo_pending = echo_confirmed = false;
    accepted_payload_size = 0U;
    updi_role_log_status(kRole, "PARKED",
                         spi_selected ? lora.park() : RADIOLIB_ERR_WRONG_MODEM);
  }
#endif
  bool flush_events = !transport.IsActive();
#if !HELLO_RF_DIAGNOSTIC_ONLY
  flush_events |= interactive_mode && !transport.IsTransmitting();
#endif
  if (flush_events)
    radio_diagnostics::FlushEvent(event_queue, kRole, accepted_payload,
                                  accepted_payload_size, LORA_RECEIVER_ADDRESS,
                                  LORA_SENDER_ADDRESS);
}

}  // namespace reliable_app
#endif  // LORA_APP_RELIABLE
