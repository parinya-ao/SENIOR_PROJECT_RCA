// Board-owned startup and reliable transport actions.
#if defined(LORA_APP_RELIABLE)

#include <Arduino.h>
#include <status_leds.h>
#include <stdio.h>
#include <string.h>

#include "app/campaign_id.h"
#include "app/reliable_role.h"
#include "gateway_ssot.hpp"
#include "generated/lora_sender_board.h"
#include "role_log.h"

namespace reliable_app {

const char kRole[] = "GATEWAY";
const char kFirmware[] = "sender_hello";
static status_leds::Controller led_status(
    GatewaySSOT::Pins::LED1, GatewaySSOT::Pins::LED2,
    GatewaySSOT::Pins::LED_ON_LEVEL, GatewaySSOT::Pins::LED_OFF_LEVEL,
    GatewaySSOT::Tasks::LED1_TOGGLE_INTERVAL_MS,
    GatewaySSOT::Tasks::LORA_TX_LED_TOGGLE_INTERVAL_MS);

void InitializeRoleGpio() { led_status.Begin(millis()); }
void PollRoleLeds(uint32_t now, bool transmitting) {
  led_status.Poll(now, transmitting);
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
const char kReadyEvent[] = "WAIT_START";
void ReportRoleReadyAtStartup() {}

bool ArmRole() {
  return transport.Arm(LORA_SENDER_ADDRESS, LORA_RECEIVER_ADDRESS, AcceptData,
                       nullptr, lora_app::NextCampaignId(LORA_BUILD_ID));
}

static bool completion_reported = false;
static uint8_t tx_sequence = ssot::kSequence;

#if HELLO_TEST_MODE
static constexpr Address kWrongDestinationAddress = 2;
static_assert(kWrongDestinationAddress != LORA_SENDER_ADDRESS &&
                  kWrongDestinationAddress != LORA_RECEIVER_ADDRESS &&
                  kWrongDestinationAddress != UINT8_MAX,
              "wrong-destination test address must be a distinct unicast");
static bool wrong_destination_tx_pending = false;
static uint32_t wrong_destination_started_at = 0;

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

void PollRoleRadio(uint32_t now) {
#if HELLO_TEST_MODE
  if (wrong_destination_tx_pending)
    PollWrongDestination(now);
  else
#endif
    transport.Poll(now);
  if (transport.result() == decltype(transport)::Result::kAccepted &&
      !completion_reported) {
    completion_reported = true;
    ++tx_sequence;
  }
}

bool RoleCommandPending() {
#if HELLO_TEST_MODE
  return wrong_destination_tx_pending;
#else
  return false;
#endif
}

void ResetRoleTransaction() {
  completion_reported = false;
  tx_sequence = ssot::kSequence;
}

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

void HandleRoleCommand(char command) {
  if (command == 'S') RequestData();
#if HELLO_TEST_MODE
  if (command == 'W') SendWrongDestination();
#endif
}
#endif

}  // namespace reliable_app
#endif  // LORA_APP_RELIABLE
