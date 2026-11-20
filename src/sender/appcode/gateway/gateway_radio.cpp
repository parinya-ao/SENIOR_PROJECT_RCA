// Owns Gateway radio transactions for both I2C and the UPDI bench.
#if defined(LORA_APP_GATEWAY)

#define LORA_NONBLOCKING_LOG 1
#include <Arduino.h>
#include <lora.h>
#include <string.h>
#include <shared/diagnostics/reliable_log.h>
#include <shared/protocol/interactive_command.h>
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
static reliable::HexDataCommandDecoder<Transport::kMaxData> host_decoder;
static uint8_t host_payload[Transport::kMaxData] = {};
static uint8_t host_payload_size = 0U;
static bool interactive_mode = false;
static bool interactive_transaction = false;
static bool awaiting_echo = false;
static bool echo_data_validated = false;
static uint8_t echo_confirmations = 0U;
static bool echo_ack_transmitted = false;
static uint32_t echo_wait_started = 0U;

// Accept only the exact Tracker echo for the active Gateway payload.
static bool AcceptEcho(void*, uint8_t received_sequence, const uint8_t* data,
                       uint8_t length) {
  if (!interactive_transaction || !awaiting_echo || !data ||
      received_sequence != sequence || length != host_payload_size ||
      memcmp(data, host_payload, length) != 0)
    return false;
  echo_data_validated = true;
  return true;
}

// Retain operation evidence in RAM until the timing-sensitive work is over.
static void RecordEvent(void*, const char* name, uint8_t type, uint8_t seq,
                        int16_t error) {
  if (bench)
    events.Push(
        {name, millis(), error, type, seq, transport.event_campaign_id()});
  if (interactive_transaction && awaiting_echo && type == ssot::kAckType &&
      seq == sequence && strcmp(name, "ACK_CONFIRM_TX_DONE") == 0) {
    ++echo_confirmations;
    echo_wait_started = millis();
  }
  if (interactive_transaction && awaiting_echo && type == ssot::kAckType &&
      seq == sequence && strcmp(name, "ACK_TX_DONE") == 0)
    echo_ack_transmitted = true;
}

// Start or retry the tagged DATA handoff within the existing attempt budget.
static void SendEchoConfirmation(uint32_t now) {
  if (transport.SendAckConfirmation(sequence, now)) {
    if (echo_confirmations)
      RecordEvent(nullptr, "ACK_CONFIRM_RETRY", ssot::kAckType, sequence, 0);
    return;
  }
  interactive_transaction = false;
  awaiting_echo = false;
  radio_ready = false;
  updi_role_log(kRole, "ACK_CONFIRM_START_FAILED");
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
  radio_ready = transport.Arm(local_address, LORA_RECEIVER_ADDRESS, AcceptEcho,
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
    const uint8_t* payload = interactive_transaction
                                 ? host_payload
                                 : reinterpret_cast<const uint8_t*>(LORA_HELLO_PAYLOAD);
    const uint8_t payload_size =
        interactive_transaction ? host_payload_size : ssot::kHelloPayloadSize;
    data_pending = transport.SendReliableData(
        sequence, payload, payload_size, now);
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
  // Keep acknowledging exact Echo duplicates until the host advances or parks.
  // AcceptEcho still rejects any new DATA outside the active handoff.
  if (data_pending || (bench && radio_ready)) transport.Poll(now, interactive_mode);
  if (data_pending && !transport.IsActive()) {
    data_pending = false;
    if (transport.result() == Transport::Result::kAccepted) {
      if (interactive_transaction) {
        awaiting_echo = true;
        echo_data_validated = false;
        echo_confirmations = 0U;
        echo_ack_transmitted = false;
        SendEchoConfirmation(now);
      } else {
        ++sequence;
        if (!bench) updi_role_log(kRole, "ACK_ACCEPTED");
      }
    } else {
      radio_ready = false;
      if (!bench) updi_role_log(kRole, "TRANSACTION_FAILED");
      interactive_transaction = false;
      awaiting_echo = false;
      host_payload_size = 0U;
      host_decoder.Reset();
    }
    return;
  }
  if (awaiting_echo && transport.state() == Transport::State::kFailed) {
    interactive_transaction = false;
    awaiting_echo = false;
    radio_ready = false;
    return;
  }
  if (awaiting_echo && !echo_data_validated && !transport.IsActive() &&
      echo_confirmations < ssot::kMaxAttempts &&
      now - echo_wait_started >= LORA_ACK_TIMEOUT_MS) {
    SendEchoConfirmation(now);
    return;
  }
  if (awaiting_echo && !echo_data_validated && !transport.IsActive() &&
      now - echo_wait_started >= Transport::kTransactionTimeoutMs) {
    char line[72];
    snprintf(line, sizeof line,
             "ECHO_TIMEOUT SID=%04X T=%lu TYPE=%u Q=%u E=-1", campaign,
             static_cast<unsigned long>(now), ssot::kDataType, sequence);
    updi_role_log(kRole, line);
    interactive_transaction = false;
    awaiting_echo = false;
    host_payload_size = 0U;
    host_decoder.Reset();
    return;
  }
  if (awaiting_echo && echo_data_validated && echo_ack_transmitted &&
      !transport.IsActive() && events.size() == 0U) {
    const uint16_t completed_campaign = campaign;
    const uint8_t completed_sequence = sequence;
    interactive_transaction = false;
    awaiting_echo = false;
    echo_confirmations = 0U;
    echo_ack_transmitted = false;
    echo_data_validated = false;
    host_payload_size = 0U;
    host_decoder.Reset();
    ++sequence;
    char line[72];
    snprintf(line, sizeof line,
             "ROUND_TRIP_DONE SID=%04X T=%lu TYPE=%u Q=%u E=0",
             completed_campaign, static_cast<unsigned long>(now), ssot::kDataType,
             completed_sequence);
    updi_role_log(kRole, line);
  }
}
#endif

// Keep the configured I2C address stable during an active transaction.
void InitializeRadio(Address address) {
#if !HELLO_RF_DIAGNOSTIC_ONLY
  if (transport.IsActive() || probe_pending || request != Request::kNone ||
      interactive_transaction)
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
  if (!interactive_mode && request == Request::kNone && !data_pending &&
      !probe_pending && !bench_park)
    request = Request::kData;
#endif
}

void StopRadio() {
#if !HELLO_RF_DIAGNOSTIC_ONLY
  const bool radio_in_use = radio_ready || data_pending || probe_pending;
  request = Request::kNone;
  data_pending = false;
  probe_pending = false;
  interactive_mode = false;
  interactive_transaction = false;
  awaiting_echo = false;
  echo_data_validated = echo_ack_transmitted = false;
  echo_confirmations = 0U;
  host_payload_size = 0U;
  host_decoder.Reset();
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
  bool flush_events = !transport.IsActive() ||
                      transport.state() == Transport::State::kRetryPending;
#if !HELLO_RF_DIAGNOSTIC_ONLY
  flush_events |= interactive_mode;
#endif
  if (!IsRadioTransmitting() && flush_events) {
#if defined(LORA_NONBLOCKING_LOG) && LORA_NONBLOCKING_LOG
    updi_role_log_service();
#endif
    if (!boot_logged && updi_uart_enabled()) {
      updi_role_log_identity("SENDER", "sender", __DATE__, __TIME__);
      updi_role_log_boot(kRole, "sender", __DATE__, __TIME__);
      radio_diagnostics::ReportConfig(kRole);
      boot_logged = true;
    }
    const uint8_t* payload = nullptr;
    uint8_t payload_size = 0U;
#if !HELLO_RF_DIAGNOSTIC_ONLY
    if (interactive_transaction) {
      payload = host_payload;
      payload_size = host_payload_size;
    }
#endif
    radio_diagnostics::FlushEvent(events, kRole, payload, payload_size,
                                  LORA_SENDER_ADDRESS, LORA_RECEIVER_ADDRESS);
  }
  if (!updi_uart_rx_poll()) return;
  const char command = static_cast<char>(updi_uart_rx());
  bool frame_byte = false;
#if !HELLO_RF_DIAGNOSTIC_ONLY
  frame_byte = host_decoder.Consumes(static_cast<uint8_t>(command));
#endif
  if (command == '?' && !frame_byte && !transport.IsActive() &&
      !IsRadioTransmitting()) {
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
    interactive_mode = false;
    interactive_transaction = false;
    awaiting_echo = false;
    host_payload_size = 0U;
    host_decoder.Reset();
    updi_role_log(kRole, "BENCH_READY");
  }
  if (!bench) return;
  if (!frame_byte && command == 'V') {
    radio_diagnostics::ReportInteractiveCapability(
        kRole, "INTERACTIVE_CAPS", Transport::kMaxData);
    return;
  }
  if (!frame_byte && command == 'I') {
    if (radio_ready && !data_pending && !awaiting_echo) {
      interactive_mode = true;
      radio_diagnostics::ReportInteractiveCapability(
          kRole, "INTERACTIVE_READY", Transport::kMaxData);
    }
    return;
  }
  if (!frame_byte && (command == 'P' || command == 'E')) {
    request = Request::kNone;
    bench_park = true;
    leave_bench = command == 'E';
    interactive_mode = false;
    interactive_transaction = false;
    awaiting_echo = false;
    host_payload_size = 0U;
    host_decoder.Reset();
    return;
  }
  if (frame_byte) {
    if (!interactive_mode || !radio_ready || data_pending || awaiting_echo ||
        bench_park || request != Request::kNone || interactive_transaction) {
      host_decoder.Reset();
      host_payload_size = 0U;
      updi_role_log(kRole, "HOST_DATA_REJECTED MODE_OR_BUSY");
      return;
    }
    const auto result =
        host_decoder.Feed(static_cast<uint8_t>(command), host_payload,
                          sizeof(host_payload));
    if (result == decltype(host_decoder)::Result::kInvalidHex) {
      updi_role_log(kRole, "HOST_DATA_REJECTED HEX");
    } else if (result == decltype(host_decoder)::Result::kInvalidLength ||
               result == decltype(host_decoder)::Result::kInvalidBuffer) {
      updi_role_log(kRole, "HOST_DATA_REJECTED LENGTH");
    } else if (result == decltype(host_decoder)::Result::kComplete) {
      host_payload_size = host_decoder.size();
      const uint8_t limit =
          radio_diagnostics::InteractivePayloadLimit(Transport::kMaxData);
      if (host_payload_size > limit) {
        host_payload_size = 0U;
        host_decoder.Reset();
        updi_role_log(kRole, "HOST_DATA_REJECTED LOG_LIMIT");
        return;
      }
      interactive_transaction = true;
      request = Request::kData;
      char line[72];
      snprintf(line, sizeof line, "HOST_DATA_ACCEPTED LEN=%u MAX_DATA=%u",
               static_cast<unsigned>(host_payload_size),
               static_cast<unsigned>(limit));
      updi_role_log(kRole, line);
    }
    return;
  }
  if (data_pending || probe_pending || bench_park || request != Request::kNone ||
      interactive_transaction)
    return;
  if (command == 'R') InitializeRadio(local_address);
  if (command == 'S') StartRadioTransaction();
  if (command == 'W') request = Request::kWrongDestination;
  if (command == 'M') request = Request::kMalformed;
#endif
}
#endif  // LORA_APP_GATEWAY
