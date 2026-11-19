// Exercises the real reliable app with deterministic RadioLib, SPI, and UPDI
// test doubles.
#include <Arduino.h>
#include <RadioLib.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>

namespace fake_radio {
State state;
}
namespace fake_spi {
State state;
}
SPIClass SPI;
uint32_t host_ms;
void delay(uint32_t ms) { host_ms += ms; }

static const char* input = "";
static char logs[12000];
static size_t used;
static bool mailbox_ready = true;
extern "C" bool updi_uart_enabled() { return true; }
extern "C" bool updi_uart_rx_poll() { return *input; }
extern "C" uint8_t updi_uart_rx() { return *input++; }
extern "C" void updi_uart_tx(uint8_t c) {
  assert(fake_radio::state.op_mode != 0x83);
  assert(used + 1 < sizeof logs);
  logs[used++] = static_cast<char>(c);
  logs[used] = 0;
}
extern "C" bool updi_uart_try_tx(uint8_t c) {
  if (!mailbox_ready) return false;
  updi_uart_tx(c);
  return true;
}
// Keep the app and its test doubles in one TU so tests can inspect private
// state.
// NOLINTBEGIN(bugprone-suspicious-include)
#include "../src/app/reliable_app.cpp"
#if defined(LORA_ROLE_RECEIVER)
#include "../src/receiver/appcode/reliable.cpp"
#else
#include "../src/sender/appcode/reliable.cpp"
#endif
// NOLINTEND(bugprone-suspicious-include)

using namespace reliable_app;

static void command(const char* text) {
  input = text;
  for (unsigned i = 0; i < 100; ++i) {
    reliable_app::Poll();
    ++host_ms;
  }
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
static void deliver(uint8_t source, uint8_t destination, const uint8_t* payload,
                    uint8_t length, uint16_t campaign_id = 0x1234) {
  fake_radio::state.rx_data[0] = destination;
  fake_radio::state.rx_data[1] = source;
  fake_radio::state.rx_data[2] = static_cast<uint8_t>(campaign_id);
  fake_radio::state.rx_data[3] = static_cast<uint8_t>(campaign_id >> 8U);
  memcpy(fake_radio::state.rx_data + 4, payload, length);
  fake_radio::state.rx_size = static_cast<size_t>(length) + 4;
  fake_radio::state.irq_flags = 0x40;
  fake_radio::state.received_action();
}

static void complete_tx() {
  fake_radio::state.irq_flags = 8;
  fake_radio::state.sent_action();
  reliable_app::Poll();
}
#endif

int main() {
#if defined(TEST_WRONG_DESTINATION)
  SPI.reset();
  reliable_app::Initialize();
  assert(radio_ready);
  input = "W";
  reliable_app::Poll();
  assert(strstr(logs, "WRONG_DEST_TX_BEGIN DST=2 TYPE=08 Q=1 APP=11") !=
         nullptr);
  assert(transport.campaign_id() != 0);
  const uint8_t wrong_destination_frame[] = {
      2,
      0,
      static_cast<uint8_t>(transport.campaign_id()),
      static_cast<uint8_t>(transport.campaign_id() >> 8U),
      ssot::kDataType,
      ssot::kSequence,
      'h',
      'e',
      'l',
      'l',
      'o',
      ' ',
      'w',
      'o',
      'r',
      'l',
      'd'};
  assert(fake_radio::state.transmit_starts == 1);
  assert(fake_radio::state.tx_size == sizeof wrong_destination_frame);
  assert(!memcmp(fake_radio::state.tx_copy, wrong_destination_frame,
                 sizeof wrong_destination_frame));
  complete_tx();
  assert(radio_ready && fake_radio::state.transmit_starts == 1);

  input = "W";
  reliable_app::Poll();
  assert(fake_radio::state.transmit_starts == 2);
  host_ms += LORA_TX_TIMEOUT_MS;
  reliable_app::Poll();
  assert(!radio_ready && fake_radio::state.sleep_calls > 0);
  puts("PASS one-shot wrong-destination frame and bounded TX timeout");
  return 0;
#endif
#if defined(TEST_LOG_DISABLED)
  SPI.reset();
  reliable_app::Initialize();
  command("S");
  assert(used == 0 && updi_log_count == 0);
  assert(fake_radio::state.transmit_starts == 1);
  puts("PASS radio progresses with logging disabled");
  return 0;
#endif
#if defined(TEST_LOG_BACKPRESSURE)
  {
    mailbox_ready = false;
    SPI.reset();
    reliable_app::Initialize();
    for (unsigned i = 0; i < 100; ++i) updi_role_log(kRole, "backpressure");
    assert(updi_role_log_dropped() > 0);
    for (unsigned i = 0; i < 30; ++i)
      RecordTransportEvent(nullptr, "TEST", 0, 0, 0);
    assert(event_queue.overflow_count() == 14);
    command("S");
    assert(fake_radio::state.transmit_starts == 1);
    complete_tx();
    const uint8_t ack[] = {ssot::kAckType, ssot::kSequence};
    const uint16_t campaign_id =
        static_cast<uint16_t>(fake_radio::state.tx_copy[2]) |
        (static_cast<uint16_t>(fake_radio::state.tx_copy[3]) << 8U);
    deliver(LORA_RECEIVER_ADDRESS, LORA_SENDER_ADDRESS, ack, sizeof ack,
            campaign_id);
    reliable_app::Poll();
    assert(transport.result() == decltype(transport)::Result::kAccepted);
    mailbox_ready = true;
    for (unsigned i = 0; i < 30; ++i) reliable_app::Poll();
    assert(used > 0);
    puts("PASS radio progresses while OCD is unavailable");
    return 0;
  }
#endif

  SPI.reset();
  reliable_app::Initialize();
#if HELLO_RF_DIAGNOSTIC_ONLY
  command("S");
  assert(fake_radio::state.transmit_starts == 0);
  puts("PASS diagnostic target stays RF-disabled");
#elif defined(LORA_ROLE_RECEIVER)
  assert(radio_ready);
  command("N");
  assert(strstr(logs, "RADIO_SPI_VERSION=0x12"));
  const uint8_t data[] = {ssot::kDataType,
                          ssot::kSequence,
                          'h',
                          'e',
                          'l',
                          'l',
                          'o',
                          ' ',
                          'w',
                          'o',
                          'r',
                          'l',
                          'd'};
  deliver(LORA_SENDER_ADDRESS, LORA_RECEIVER_ADDRESS, data, sizeof data);
  reliable_app::Poll();
  assert(fake_radio::state.tx_copy[4] == ssot::kNackType);
  complete_tx();
  assert(strstr(logs, "DATA_REJECTED_TEST"));
  // N rejects exactly one DATA; the retransmission must be accepted.
  deliver(LORA_SENDER_ADDRESS, LORA_RECEIVER_ADDRESS, data, sizeof data);
  reliable_app::Poll();
  assert(fake_radio::state.tx_copy[4] == ssot::kAckType);
  complete_tx();
  uint8_t next_data[sizeof data];
  memcpy(next_data, data, sizeof data);
  next_data[1] = 2;
  command("D");
  const int before = fake_radio::state.transmit_starts;
  deliver(LORA_SENDER_ADDRESS, LORA_RECEIVER_ADDRESS, next_data,
          sizeof next_data);
  reliable_app::Poll();
  assert(fake_radio::state.transmit_starts == before);
  deliver(LORA_SENDER_ADDRESS, LORA_RECEIVER_ADDRESS, next_data,
          sizeof next_data);
  reliable_app::Poll();
  assert(fake_radio::state.transmit_starts == before + 1 &&
         fake_radio::state.tx_copy[4] == ssot::kAckType);
  complete_tx();
  command("P");
  assert(!radio_ready);
  command("R");
  assert(radio_ready);
  puts(
      "PASS receiver validates DATA and transmits ACK/NACK with rearm and one "
      "dropped response");
#else
  assert(radio_ready);
  command("S");
  assert(fake_radio::state.transmit_starts == 1);
  assert(strstr(logs, "RADIO_SPI_VERSION=0x12"));
  const uint16_t campaign_id =
      static_cast<uint16_t>(fake_radio::state.tx_copy[2]) |
      (static_cast<uint16_t>(fake_radio::state.tx_copy[3]) << 8U);
  assert(campaign_id != 0);
  const uint8_t data[] = {LORA_RECEIVER_ADDRESS,
                          LORA_SENDER_ADDRESS,
                          static_cast<uint8_t>(campaign_id),
                          static_cast<uint8_t>(campaign_id >> 8U),
                          ssot::kDataType,
                          ssot::kSequence,
                          'h',
                          'e',
                          'l',
                          'l',
                          'o',
                          ' ',
                          'w',
                          'o',
                          'r',
                          'l',
                          'd'};
  assert(fake_radio::state.tx_size == sizeof data);
  assert(!memcmp(data, fake_radio::state.tx_copy, sizeof data));
  complete_tx();
  const uint8_t nack[] = {ssot::kNackType, ssot::kSequence};
  deliver(LORA_RECEIVER_ADDRESS, LORA_SENDER_ADDRESS, nack, sizeof nack,
          campaign_id);
  reliable_app::Poll();
  reliable_app::Poll();
  assert(fake_radio::state.transmit_starts == 2);
  complete_tx();
  const uint8_t ack[] = {ssot::kAckType, ssot::kSequence};
  deliver(LORA_RECEIVER_ADDRESS, LORA_SENDER_ADDRESS, ack, sizeof ack,
          campaign_id);
  reliable_app::Poll();
  assert(transport.result() == decltype(transport)::Result::kAccepted);
  command("");  // Drain deferred event logging after RF completes.
  assert(strstr(logs, "ACK_ACCEPTED"));
  char expected_session[10];
  snprintf(expected_session, sizeof expected_session, "SID=%04X", campaign_id);
  assert(strstr(logs, expected_session));
  command("P");
  assert(!radio_ready);
  command("R");
  assert(radio_ready);
  command("S");
  const uint16_t next_campaign_id =
      static_cast<uint16_t>(fake_radio::state.tx_copy[2]) |
      (static_cast<uint16_t>(fake_radio::state.tx_copy[3]) << 8U);
  assert(next_campaign_id == ssot::NextCampaignId(campaign_id));
  complete_tx();
  deliver(LORA_RECEIVER_ADDRESS, LORA_SENDER_ADDRESS, ack, sizeof ack,
          next_campaign_id);
  reliable_app::Poll();

  // The transport test exercises all 255 requests; fast-forward here to check
  // that the app actually rotates and sends sequence 1 after the final ACK.
  tx_sequence = UINT8_MAX;
  command("S");
  assert(fake_radio::state.tx_copy[5] == UINT8_MAX);
  complete_tx();
  const uint8_t final_ack[] = {ssot::kAckType, UINT8_MAX};
  deliver(LORA_RECEIVER_ADDRESS, LORA_SENDER_ADDRESS, final_ack,
          sizeof final_ack, next_campaign_id);
  reliable_app::Poll();
  assert(tx_sequence == 0);
  command("S");
  const uint16_t rolled_campaign_id =
      static_cast<uint16_t>(fake_radio::state.tx_copy[2]) |
      (static_cast<uint16_t>(fake_radio::state.tx_copy[3]) << 8U);
  assert(rolled_campaign_id == ssot::NextCampaignId(next_campaign_id));
  assert(fake_radio::state.tx_copy[5] == ssot::kSequence);
  complete_tx();
  command("P");
  puts("PASS sender retransmits NACK and accepts matching ACK");
#endif
}
