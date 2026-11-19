// Coordinates one cooperative gateway radio transaction through the stable
// transport.

#if defined(LORA_APP_GATEWAY)

#include <Arduino.h>
#include <features/reliable_transfer/reliable_transport.h>
#include <lora.h>
#include <ssot.h>
#include <string.h>

#include "app/campaign_id.h"
#include "gateway_app.h"
#include "hello_config.h"
#include "lora_rx.h"
#include "role_log.h"
#include "task.h"

#if !HELLO_RF_DIAGNOSTIC_ONLY
static constexpr Address kPeerAddress = LORA_RECEIVER_ADDRESS;
#endif
// Static radio and transport share application lifetime; initialization is
// explicit.
static LoRa lora(LORA_PIN_CS, LORA_PIN_IRQ, LORA_PIN_RST, LORA_PIN_DIO1);
static reliable::Transport<LoRa> transport(lora, HELLO_RF_FREQUENCY_MHZ,
                                           HELLO_RF_TX_POWER_DBM,
                                           HELLO_RF_LONG_RANGE);
// Foreground address and lifecycle state shared with the cooperative radio
// task.
static Address local_address = LORA_SENDER_ADDRESS;
static bool started = false, radio_ready = false;
#if !HELLO_RF_DIAGNOSTIC_ONLY
// Selects peripheral routing once; repeated starts must not reroute an active
// SPI bus.
static bool spi_selected = false;
static uint8_t sequence = ssot::kSequence;

// Accepts only the exact configured payload; caller retains the input buffer.
static bool AcceptData(void*, uint8_t seq, const uint8_t* data,
                       uint8_t length) {
  static_cast<void>(seq);
  return data && length == ssot::kHelloPayloadSize &&
         memcmp(data, LORA_HELLO_PAYLOAD, length) == 0;
}
#endif

void InitializeRadio(Address my_addr) {
  local_address = my_addr;
#if HELLO_RF_DIAGNOSTIC_ONLY
  radio_ready = false;
  updi_role_log("GATEWAY", "RADIO_INIT_SKIPPED_DIAGNOSTIC");
#else
  if (!spi_selected) {
    if (!SPI.swap(LORA_SPI_ROUTE)) {
      radio_ready = false;
      updi_role_log("GATEWAY", "SPI_ROUTE_FAILED");
      return;
    }
    spi_selected = true;
  }
  radio_ready = transport.Arm(local_address, kPeerAddress, AcceptData, nullptr,
                              lora_app::NextCampaignId(LORA_BUILD_ID));
  if (radio_ready) {
    sequence = ssot::kSequence;
    updi_role_log_radio_version("GATEWAY", lora.version());
    updi_role_log_radio_profile(
        "GATEWAY", HELLO_RF_FREQUENCY_MHZ, HELLO_RF_TX_POWER_DBM,
        HELLO_RF_SPREADING_FACTOR, HELLO_RF_BANDWIDTH_KHZ, HELLO_RF_CODING_RATE,
        HELLO_RF_SYNC_WORD, HELLO_RF_PREAMBLE_SYMBOLS, HELLO_RF_CRC_ENABLED,
        HELLO_RF_IQ_INVERTED);
  }
  updi_role_log("GATEWAY", radio_ready ? "RADIO_READY" : "RADIO_INIT_FAILED");
#endif
}

/// Owns scheduler continuation state outside Wire callbacks.
class RadioTransactionTask : public virtual Task {
 public:
  /// @return Task name shown by the scheduler.
  const char* GetName() override { return "LORA-ACK"; }

  /// Advances the cooperative radio transaction.
  TASK(Run()) override {
    TASK_BEGIN();
    for (;;) {
      TASK_WAIT_UNTIL(started);
#if HELLO_RF_DIAGNOSTIC_ONLY
      updi_role_log("GATEWAY", "RF_TX_DISABLED_DIAGNOSTIC");
      started = false;
      continue;
#else
      if (!radio_ready || sequence == 0) InitializeRadio(local_address);
      if (!radio_ready ||
          !transport.SendReliableData(
              sequence, reinterpret_cast<const uint8_t*>(LORA_HELLO_PAYLOAD),
              ssot::kHelloPayloadSize, millis())) {
        updi_role_log("GATEWAY", "DATA_START_FAILED");
        started = false;
        continue;
      }
      updi_role_log("GATEWAY", "DATA_TX_BEGIN");
      while (transport.IsActive()) {
        transport.Poll(millis());
        TASK_YIELD();
      }
      if (transport.result() == reliable::Transport<LoRa>::Result::kAccepted) {
        updi_role_log("GATEWAY", "ACK_ACCEPTED");
        ++sequence;
      } else {
        radio_ready =
            transport.state() != reliable::Transport<LoRa>::State::kFailed;
        updi_role_log(
            "GATEWAY",
            transport.result() == reliable::Transport<LoRa>::Result::kRejected
                ? "NACK_RETRY_EXHAUSTED"
                : "TRANSACTION_FAILED");
      }
      started = false;
#endif
    }
    TASK_END();
  }
} radio_task;

void RegisterRadioTask() { gateway_app::scheduler.Add(&radio_task); }

void RejectRadioConfiguration() {
  started = false;
  radio_ready = false;
  static_cast<void>(transport.Stop());
  updi_role_log("GATEWAY", "RADIO_CONFIG_REJECTED");
}

void StartRadioTransaction() {
  if (started) return;
  if (!radio_ready || sequence == 0) InitializeRadio(local_address);
  started = radio_ready;
}

void StopRadio() {
  started = false;
  radio_ready = false;
  static_cast<void>(transport.Stop());
}

void StartHelloTestIfEnabled() {
#if HELLO_TEST_MODE
  StartRadioTransaction();
#endif
}

bool IsRadioTransmitting() { return transport.IsTransmitting(); }

#endif  // LORA_APP_GATEWAY
