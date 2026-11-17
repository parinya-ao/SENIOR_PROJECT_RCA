// Retains the alternative receiver application used by host round-trip tests.

#if defined(LORA_APP_LEGACY_RECEIVER)

#include "legacy_receiver.h"

#include <Arduino.h>
#include <ssot/ssot.h>
#include <string.h>

#include "application_config.h"
#include "generated/lora_receiver_board.h"
#include "hello_config.h"
#include "lora.h"
#include "role_log.h"
#include "status_leds.h"
#include "tracker_config.h"

namespace legacy_receiver {

static constexpr Address kReceiverAddress = LORA_RECEIVER_ADDRESS;
static constexpr Address kSenderAddress = LORA_SENDER_ADDRESS;
// Static radio state is initialized only after board power sequencing in setup.
static LoRa lora(LORA_PIN_CS, LORA_PIN_IRQ, LORA_PIN_RST, LORA_PIN_DIO1);
static status_leds::Controller led_status(
    LORA_PIN_LED1, LORA_PIN_LED2, tracker_cfg::SystemConstants::LED_ON_LEVEL,
    tracker_cfg::SystemConstants::LED_OFF_LEVEL,
    tracker_cfg::SystemConstants::LED1_TOGGLE_INTERVAL_MS,
    tracker_cfg::SystemConstants::LORA_TX_LED_TOGGLE_INTERVAL_MS);
// Foreground lifecycle and SPI route latches; no ISR accesses them.
static bool radio_ready = false, boot_logged = false, spi_selected = false;
// Duplicate history survives failed ACK TX so retries cannot redeliver payload.
static bool have_accepted = false;
// Sequence zero after UINT8_MAX means no further new DATA is expected.
static uint8_t last_sequence = 0, next_sequence = ssot::kSequence;
// Owns the accepted bytes used to distinguish a duplicate from changed DATA.
static uint8_t last_payload[ssot::kHelloPayloadSize];

// Selects SPI once and initializes the generated profile without transmitting.
static bool InitializeRadio();

// Keeps GPS/SD off and their shared bus safe before enabling LoRa power.
static void InitializeReceiverGpio() {
  digitalWriteFast(LORA_PIN_ENABLE, !LORA_POWER_ACTIVE_LEVEL);
  digitalWriteFast(LORA_PIN_GPS_ENABLE, HIGH);
  digitalWriteFast(LORA_PIN_SD_ENABLE, HIGH);
  pinModeFast(LORA_PIN_ENABLE, OUTPUT);
  pinModeFast(LORA_PIN_GPS_ENABLE, OUTPUT);
  pinModeFast(LORA_PIN_SD_ENABLE, OUTPUT);
  pinModeFast(LORA_PIN_SD_DETECT, INPUT);
  pinModeFast(LORA_PIN_RST, INPUT);
  pinModeFast(LORA_PIN_IRQ, INPUT);
  pinModeFast(LORA_PIN_DIO1, INPUT);
  led_status.Begin(millis());
  digitalWriteFast(LORA_PIN_SD_CS, HIGH);
  pinModeFast(LORA_PIN_SD_CS, OUTPUT);
  digitalWriteFast(LORA_PIN_ENABLE, LORA_POWER_ACTIVE_LEVEL);
  delay(application_config::startup::kRadioSettleMs);
  digitalWriteFast(LORA_PIN_CS, HIGH);
  pinModeFast(LORA_PIN_CS, OUTPUT);
}

// Establishes safe GPIO levels before radio initialization.
void Initialize() {
  InitializeReceiverGpio();
  radio_ready = InitializeRadio();
}

static bool InitializeRadio() {
  if (!spi_selected) {
    if (!SPI.swap(LORA_SPI_ROUTE)) return false;
    spi_selected = true;
  }
  return lora.init(kReceiverAddress, HELLO_RF_FREQUENCY_MHZ,
                   HELLO_RF_TX_POWER_DBM, HELLO_RF_LONG_RANGE) == 0;
}

// Validates one DATA and completes its bounded ACK/NACK before receiving again.
void Poll() {
  led_status.Poll(millis(), false);
  if (!boot_logged && updi_uart_enabled()) {
    updi_role_log_identity("RECEIVER", "receiver", __DATE__, __TIME__);
    updi_role_log_boot("RECEIVER", "receiver", __DATE__, __TIME__);
    updi_role_log("RECEIVER", "BUILD_ID=" LORA_BUILD_ID);
    updi_role_log("RECEIVER",
                  radio_ready ? "RADIO_READY" : "RADIO_INIT_FAILED");
    boot_logged = true;
  }
  if (!radio_ready || !lora.available()) {
    delay(1);
    return;
  }

  Address source = 0, destination = 0;
  uint8_t packet[256] = {}, size = 0;
  if (lora.recv(&source, &destination, packet, sizeof packet, &size) < 0) {
    updi_role_log("RECEIVER", "RX_DISCARD");
    return;
  }
  if (size > 251 || source != kSenderAddress ||
      destination != kReceiverAddress || size < 2) {
    updi_role_log("RECEIVER", "RX_DISCARD");
    return;
  }

  const uint8_t type = packet[0], sequence = packet[1];
  if (type != ssot::kDataType) return;
  ssot::Frame frame = {};
  const bool decoded =
      ssot::DecodePayload(destination, source, 0, 0, packet, size, &frame);
  const bool payload_valid =
      decoded && size == ssot::kDataPayloadSize &&
      memcmp(packet + 2, LORA_HELLO_PAYLOAD, ssot::kHelloPayloadSize) == 0;
  const bool duplicate =
      payload_valid && have_accepted && frame.sequence == last_sequence &&
      memcmp(packet + 2, last_payload, sizeof last_payload) == 0;
  const bool valid =
      payload_valid && (duplicate || frame.sequence == next_sequence);
  if (valid) {
    if (!duplicate) {
      have_accepted = true;
      last_sequence = sequence;
      memcpy(last_payload, packet + 2, sizeof last_payload);
      next_sequence =
          sequence == UINT8_MAX ? 0 : static_cast<uint8_t>(sequence + 1);
    }
    updi_role_log("RECEIVER", duplicate ? "DATA_DUP" : "DATA_RX");
  } else {
    updi_role_log("RECEIVER", "DATA_REJECTED");
  }

#if !HELLO_RF_DIAGNOSTIC_ONLY
  uint8_t reply[ssot::kAckPayloadSize];
  size_t reply_size = 0;
  const bool encoded =
      valid
          ? ssot::EncodeAckPayload(sequence, reply, sizeof reply, &reply_size)
          : ssot::EncodeNackPayload(sequence, reply, sizeof reply, &reply_size);
  if (!encoded) return;
  if (lora.send(source, reply, static_cast<uint8_t>(reply_size)) < 0) {
    updi_role_log("RECEIVER", "ACK_TX_FAILED");
    return;
  }
  led_status.Poll(millis(), true);
  const uint32_t started = millis();
  int16_t status = 0;
  while ((status = lora.send_done()) == 0 &&
         millis() - started < LORA_TX_TIMEOUT_MS) {
    led_status.Poll(millis(), true);
    delay(1);
  }
  led_status.Poll(millis(), false);
  if (status == 1)
    updi_role_log("RECEIVER", valid ? "ACK_TX" : "NACK_TX");
  else {
    radio_ready = false;
    updi_role_log("RECEIVER", "ACK_TX_TIMEOUT");
  }
#endif
}

}  // namespace legacy_receiver

#endif  // LORA_APP_LEGACY_RECEIVER
