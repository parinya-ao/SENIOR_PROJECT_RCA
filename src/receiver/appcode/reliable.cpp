// Board-owned startup and reliable transport actions.
#if defined(LORA_APP_RELIABLE)

#include <Arduino.h>
#include <status_leds.h>

#include "app/reliable_role.h"
#include "application_config.h"
#include "generated/lora_receiver_board.h"
#include "role_log.h"
#include "tracker_config.h"

namespace reliable_app {

const char kRole[] = "RECEIVER";
const char kFirmware[] = "receiver";
static status_leds::Controller led_status(
    LORA_PIN_LED1, LORA_PIN_LED2, tracker_cfg::SystemConstants::LED_ON_LEVEL,
    tracker_cfg::SystemConstants::LED_OFF_LEVEL,
    tracker_cfg::SystemConstants::LED1_TOGGLE_INTERVAL_MS,
    tracker_cfg::SystemConstants::LORA_TX_LED_TOGGLE_INTERVAL_MS);

void InitializeRoleGpio() {
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

void PollRoleLeds(uint32_t now, bool transmitting) {
  led_status.Poll(now, transmitting);
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
const char kReadyEvent[] = "RX_READY";

void ReportRoleReadyAtStartup() { updi_role_log(kRole, kReadyEvent); }

bool ArmRole() {
  return transport.Arm(LORA_RECEIVER_ADDRESS, LORA_SENDER_ADDRESS, AcceptData,
                       nullptr);
}

void PollRoleRadio(uint32_t now) { transport.Poll(now); }
bool RoleCommandPending() { return false; }
void ResetRoleTransaction() {}
void HandleRoleCommand(char) {}
#endif

}  // namespace reliable_app
#endif  // LORA_APP_RELIABLE
