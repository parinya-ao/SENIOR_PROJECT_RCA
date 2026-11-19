// Owns Gateway radio transactions for both I2C and the UPDI bench.
#if defined(LORA_APP_GATEWAY)

#define LORA_NONBLOCKING_LOG 1
#include <Arduino.h>
#include <lora.h>
#include <shared/diagnostics/reliable_log.h>
#include <shared/protocol/reliable_transport.h>
#include <ssot.h>

#include "gateway_app.h"
#include "hello_config.h"
#include "lora_rx.h"
#include "sender/appcode/campaign_id.h"

using Transport = reliable::Transport<LoRa>;
static constexpr char kRole[] = "GATEWAY";
static LoRa lora(LORA_PIN_CS, LORA_PIN_IRQ, LORA_PIN_RST, LORA_PIN_DIO1);
static Transport transport(lora, HELLO_RF_FREQUENCY_MHZ, HELLO_RF_TX_POWER_DBM,
                           HELLO_RF_LONG_RANGE);
static Address local_address = LORA_SENDER_ADDRESS;
static bool radio_ready = false;
static bool bench = false;
static bool bench_park = false;
static bool leave_bench = false;
static bool boot_logged = false;
static radio_diagnostics::EventQueue events;

#if !HELLO_RF_DIAGNOSTIC_ONLY
static bool spi_selected = false;
static uint8_t sequence = ssot::kSequence;
static uint16_t campaign = 0;
enum class Request : uint8_t { kNone, kData, kWrongDestination, kMalformed };
static Request request = Request::kNone;
static bool data_pending = false, probe_pending = false;
static uint32_t probe_started = 0;

// Gateway only initiates transactions, so unsolicited DATA cannot bind it.
static bool RejectData(void*, uint8_t, const uint8_t*, uint8_t) {
  return false;
}

// Retain operation evidence in RAM until the timing-sensitive work is over.
static void RecordEvent(void*, const char* name, uint8_t type, uint8_t seq,
                        int16_t error) {
  if (bench)
    events.Push(
        {name, millis(), error, type, seq, transport.event_campaign_id()});
}

// Restore the radio after a driver failure without changing the wire identity.
static bool ArmRadio() {
  if (radio_ready) return true;
  if (!spi_selected) {
    if (!SPI.swap(LORA_SPI_ROUTE)) return false;
    spi_selected = true;
  }
  if (!campaign) campaign = lora_app::NextCampaignId(LORA_BUILD_ID);
  if (!sequence) {
    campaign = ssot::NextCampaignId(campaign);
    sequence = ssot::kSequence;
  }
  transport.SetEventCallback(RecordEvent, nullptr);
  radio_ready = transport.Arm(local_address, LORA_RECEIVER_ADDRESS, RejectData,
                              nullptr, campaign);
  return radio_ready;
}

// Starts a single physical test frame without consuming the production
// sequence.
static void StartProbe(Request probe, uint32_t now) {
  constexpr Address kWrongDestination = 2;
  static_assert(kWrongDestination != LORA_SENDER_ADDRESS &&
                    kWrongDestination != LORA_RECEIVER_ADDRESS,
                "bench destination must differ from both roles");
  uint8_t packet[2 + ssot::kHelloPayloadSize] = {ssot::kDataType, sequence};
  memcpy(packet + 2, LORA_HELLO_PAYLOAD, ssot::kHelloPayloadSize);
  const bool malformed = probe == Request::kMalformed;
  const Address destination =
      malformed ? LORA_RECEIVER_ADDRESS : kWrongDestination;
  const uint8_t size =
      static_cast<uint8_t>(sizeof packet - (malformed ? 1 : 0));
  const int16_t error = lora.send(destination, campaign, packet, size);
  probe_started = now;
  probe_pending = error == 0;
  if (!probe_pending) {
    updi_role_log_status(kRole, "BENCH_PROBE_FAILED", error);
    return;
  }
  char line[70];
  snprintf(line, sizeof line, "BENCH_PROBE_BEGIN SID=%04X Q=%u DST=%u APP=%u",
           campaign, sequence, destination, size - 2);
  updi_role_log(kRole, line);
}

// Advance a diagnostic TX with the normal driver timeout and receive rearm.
static void PollProbe(uint32_t now) {
  const int16_t status = lora.send_done();
  if (status == 0 && now - probe_started < LORA_TX_TIMEOUT_MS) return;
  probe_pending = false;
  if (status != 1) StopRadio();
  updi_role_log_status(
      kRole, status == 1 ? "BENCH_PROBE_DONE" : "BENCH_PROBE_FAILED", status);
}

// Consume one request from either entry point using one sequence and retry
// state.
static void RunRequest(uint32_t now) {
  const Request next = request;
  request = Request::kNone;
  if (!sequence) radio_ready = false;
  if (!ArmRadio()) {
    updi_role_log(kRole, "DATA_START_FAILED");
  } else if (next != Request::kData) {
    StartProbe(next, now);
  } else {
    data_pending = transport.SendReliableData(
        sequence, reinterpret_cast<const uint8_t*>(LORA_HELLO_PAYLOAD),
        ssot::kHelloPayloadSize, now);
    if (data_pending)
      RecordEvent(nullptr, "DATA_TX_REQUESTED", ssot::kDataType, sequence, 0);
    else {
      radio_ready = false;
      updi_role_log(kRole, "DATA_START_FAILED");
    }
  }
}

// Run the driver's foreground poll and advance sequence only after an ACK.
static void PollRadio() {
  const uint32_t now = millis();
  if (probe_pending) {
    PollProbe(now);
    return;
  }
  if (bench_park && !transport.IsTransmitting()) {
    const bool spi_ready = spi_selected || ArmRadio();
    StopRadio();
    bench_park = false;
    if (leave_bench) bench = false;
    leave_bench = false;
    updi_role_log_status(kRole, "PARKED",
                         spi_ready ? lora.park() : RADIOLIB_ERR_WRONG_MODEM);
    return;
  }
  if (request != Request::kNone) RunRequest(now);
  if (data_pending || (bench && radio_ready)) transport.Poll(now, false);
  if (!data_pending || transport.IsActive()) return;
  data_pending = false;
  if (transport.result() == Transport::Result::kAccepted) {
    ++sequence;
    if (!bench) updi_role_log(kRole, "ACK_ACCEPTED");
  } else {
    radio_ready = false;
    if (!bench) updi_role_log(kRole, "TRANSACTION_FAILED");
  }
}
#endif

// Keep the configured I2C address stable during an active transaction.
void InitializeRadio(Address address) {
#if !HELLO_RF_DIAGNOSTIC_ONLY
  if (transport.IsActive() || probe_pending || request != Request::kNone)
    return;
  if (address != local_address) {
    StopRadio();
    local_address = address;
    campaign = 0;
    sequence = ssot::kSequence;
  }
  updi_role_log(kRole, ArmRadio() ? "RADIO_READY" : "RADIO_INIT_FAILED");
#else
  static_cast<void>(address);
  updi_role_log(kRole, "RADIO_INIT_SKIPPED_DIAGNOSTIC");
#endif
}

// The existing scheduler owns foreground radio progress for both callers.
class RadioTransactionTask : public virtual Task {
 public:
  const char* GetName() override { return "LORA-ACK"; }
  TASK(Run()) override {
    TASK_BEGIN();
    for (;;) {
#if !HELLO_RF_DIAGNOSTIC_ONLY
      PollRadio();
#endif
      TASK_YIELD();
    }
    TASK_END();
  }
} radio_task;

void RegisterRadioTask() { gateway_app::scheduler.Add(&radio_task); }

void RejectRadioConfiguration() {
  StopRadio();
  updi_role_log(kRole, "RADIO_CONFIG_REJECTED");
}

void StartRadioTransaction() {
#if !HELLO_RF_DIAGNOSTIC_ONLY
  if (request == Request::kNone && !data_pending && !probe_pending &&
      !bench_park)
    request = Request::kData;
#endif
}

void StopRadio() {
#if !HELLO_RF_DIAGNOSTIC_ONLY
  const bool radio_in_use = radio_ready || data_pending || probe_pending;
  request = Request::kNone;
  data_pending = false;
  probe_pending = false;
  if (radio_in_use) static_cast<void>(transport.Stop());
#endif
  radio_ready = false;
}

void StartHelloTestIfEnabled() {
#if HELLO_TEST_MODE
  StartRadioTransaction();
#endif
}

bool IsRadioTransmitting() {
#if !HELLO_RF_DIAGNOSTIC_ONLY
  return transport.IsTransmitting() || probe_pending;
#else
  return false;
#endif
}

bool IsRadioBenchActive() { return bench; }

// Read one command per scheduler cycle; park requests cannot schedule retries.
void PollRadioConsole() {
  if (!IsRadioTransmitting() &&
      (!transport.IsActive() ||
       transport.state() == Transport::State::kRetryPending)) {
#if defined(LORA_NONBLOCKING_LOG) && LORA_NONBLOCKING_LOG
    updi_role_log_service();
#endif
    if (!boot_logged && updi_uart_enabled()) {
      updi_role_log_identity("SENDER", "sender", __DATE__, __TIME__);
      updi_role_log_boot(kRole, "sender", __DATE__, __TIME__);
      radio_diagnostics::ReportConfig(kRole);
      boot_logged = true;
    }
    radio_diagnostics::FlushEvent(events, kRole, nullptr);
  }
  if (!updi_uart_rx_poll()) return;
  const char command = static_cast<char>(updi_uart_rx());
  if (command == '?' && !transport.IsActive() && !IsRadioTransmitting()) {
    radio_diagnostics::ReportRadioStatus(kRole, lora, radio_ready, events);
    if (bench && radio_ready) radio_diagnostics::ReportRegisters(kRole, lora);
    return;
  }
#if !HELLO_RF_DIAGNOSTIC_ONLY
  if (command == 'B' && !bench && !data_pending && !probe_pending &&
      request == Request::kNone) {
    bench = true;
    StopRadio();
    events.Clear();
    local_address = LORA_SENDER_ADDRESS;
    if (campaign) campaign = ssot::NextCampaignId(campaign);
    sequence = ssot::kSequence;
    updi_role_log(kRole, "BENCH_READY");
  }
  if (!bench) return;
  if (command == 'P' || command == 'E') {
    request = Request::kNone;
    bench_park = true;
    leave_bench = command == 'E';
    return;
  }
  if (data_pending || probe_pending || bench_park || request != Request::kNone)
    return;
  if (command == 'R') InitializeRadio(local_address);
  if (command == 'S') StartRadioTransaction();
  if (command == 'W') request = Request::kWrongDestination;
  if (command == 'M') request = Request::kMalformed;
#endif
}
#endif  // LORA_APP_GATEWAY
