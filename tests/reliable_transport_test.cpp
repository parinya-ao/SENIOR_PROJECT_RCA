#include <assert.h>
#include <stdint.h>
#include <string.h>

#include "shared/protocol/interactive_command.h"
#include "shared/protocol/reliable_transport.h"

struct Packet {
  uint8_t source = 0U;
  uint8_t destination = 0U;
  uint16_t campaign = 0U;
  uint8_t size = 0U;
  uint8_t bytes[256] = {};
};

class FakeRadio {
 public:
  explicit FakeRadio(uint8_t address) : address_(address) {}

  int16_t init(uint8_t address, float, int8_t, uint8_t) {
    address_ = address;
    return 0;
  }

  int16_t send(uint8_t peer, uint16_t campaign, const uint8_t* bytes,
               size_t size) {
    assert(bytes != nullptr && size <= sizeof(last_tx_.bytes));
    last_tx_.source = address_;
    last_tx_.destination = peer;
    last_tx_.campaign = campaign;
    last_tx_.size = static_cast<uint8_t>(size);
    memcpy(last_tx_.bytes, bytes, size);
    tx_pending_ = true;
    return 0;
  }

  int16_t send_done(bool* tx_done, int16_t* rearm) {
    *tx_done = tx_pending_;
    *rearm = 0;
    if (!tx_pending_) return 0;
    tx_pending_ = false;
    return 1;
  }

  int16_t recv(uint8_t* source, uint8_t* destination, uint16_t* campaign,
               uint8_t* output, size_t capacity, uint8_t* size) {
    assert(rx_pending_ && rx_.size <= capacity);
    *source = rx_.source;
    *destination = rx_.destination;
    *campaign = rx_.campaign;
    *size = rx_.size;
    memcpy(output, rx_.bytes, rx_.size);
    rx_pending_ = false;
    return 0;
  }

  bool available() const { return rx_pending_; }
  int16_t sleep() { return 0; }
  const Packet& last_tx() const { return last_tx_; }
  void inject(const Packet& packet) {
    assert(!rx_pending_);
    rx_ = packet;
    rx_pending_ = true;
  }

 private:
  uint8_t address_;
  Packet last_tx_{};
  Packet rx_{};
  bool tx_pending_ = false;
  bool rx_pending_ = false;
};

struct EventLog {
  const char* names[64] = {};
  size_t count = 0U;
};

struct AcceptedPayload {
  uint8_t bytes[reliable::Transport<FakeRadio>::kMaxData] = {};
  uint8_t size = 0U;
  bool allow_new = true;
};

static bool AcceptPayload(void* context, uint8_t, const uint8_t* bytes,
                          uint8_t size) {
  auto* accepted = static_cast<AcceptedPayload*>(context);
  if (!accepted->allow_new || !bytes || !size || size > sizeof(accepted->bytes))
    return false;
  memcpy(accepted->bytes, bytes, size);
  accepted->size = size;
  return true;
}

static void Record(void* context, const char* event, uint8_t, uint8_t,
                   int16_t) {
  auto* events = static_cast<EventLog*>(context);
  assert(events->count < sizeof(events->names) / sizeof(events->names[0]));
  events->names[events->count++] = event;
}

static bool Has(const EventLog& events, const char* expected) {
  for (size_t i = 0; i < events.count; ++i) {
    if (strcmp(events.names[i], expected) == 0) return true;
  }
  return false;
}

static void TestBidirectionalAcknowledgmentHandoff() {
  using Transport = reliable::Transport<FakeRadio>;
  FakeRadio gateway_radio(0U), tracker_radio(1U);
  Transport gateway(gateway_radio, 915.0F, 2, 0U);
  Transport tracker(tracker_radio, 915.0F, 2, 0U);
  AcceptedPayload tracker_payload{}, gateway_payload{};
  EventLog gateway_events{}, tracker_events{};
  static const uint8_t payload[] = {'o', 'k'};

  gateway.SetEventCallback(Record, &gateway_events);
  tracker.SetEventCallback(Record, &tracker_events);
  assert(gateway.Arm(0U, 1U, AcceptPayload, &gateway_payload, 0x1234U));
  assert(tracker.Arm(1U, 0U, AcceptPayload, &tracker_payload, 0U));
  assert(gateway.SendReliableData(1U, payload, sizeof(payload), 0U));
  gateway.Poll(1U, false);
  tracker_radio.inject(gateway_radio.last_tx());
  tracker.Poll(2U, true);
  tracker.Poll(3U, true);
  assert(Has(tracker_events, "ACK_TX_DONE"));
  gateway_radio.inject(tracker_radio.last_tx());
  gateway.Poll(4U, false);
  assert(gateway.result() == Transport::Result::kAccepted);

  assert(gateway.SendAckConfirmation(1U, 5U));
  gateway.Poll(6U, false);
  assert(Has(gateway_events, "ACK_CONFIRM_TX_DONE"));
  assert(gateway_radio.last_tx().bytes[0] == ssot::kAckType);
  assert(gateway_radio.last_tx().bytes[1] == 1U);

  // Drop the first confirmation. The Gateway must be able to send it again.
  assert(gateway.SendAckConfirmation(1U, 7U));
  gateway.Poll(8U, false);
  Packet ordinary_ack = gateway_radio.last_tx();
  ordinary_ack.size = 2U;
  tracker_radio.inject(ordinary_ack);
  tracker.Poll(9U, true);
  assert(!Has(tracker_events, "ACK_CONFIRM_RX"));

  Packet stale_confirmation = gateway_radio.last_tx();
  stale_confirmation.campaign = 0x1235U;
  tracker_radio.inject(stale_confirmation);
  tracker.Poll(10U, true);
  assert(!Has(tracker_events, "ACK_CONFIRM_RX"));
  tracker_radio.inject(gateway_radio.last_tx());
  tracker.Poll(11U, true);
  assert(Has(tracker_events, "ACK_CONFIRM_RX"));

  assert(tracker.SendReliableData(1U, payload, sizeof(payload), 12U));
  tracker.Poll(13U, true);
  const Packet repeated_confirmation = gateway_radio.last_tx();
  tracker_radio.inject(repeated_confirmation);
  tracker.Poll(14U, true);
  assert(tracker.IsActive());
  gateway_radio.inject(tracker_radio.last_tx());
  gateway.Poll(15U, true);
  gateway.Poll(16U, true);
  assert(Has(gateway_events, "ACK_TX_DONE"));

  // Drop the Echo ACK. After completion, only exact repeats may be ACKed.
  gateway_payload.allow_new = false;
  const uint32_t retry_at = 13U + LORA_ACK_TIMEOUT_MS;
  tracker.Poll(retry_at, true);
  tracker.Poll(retry_at + 1U, true);
  tracker.Poll(retry_at + 2U, true);
  Packet unsolicited = tracker_radio.last_tx();
  unsolicited.bytes[2] = 'x';
  gateway_radio.inject(unsolicited);
  gateway.Poll(retry_at + 3U, true);
  gateway.Poll(retry_at + 4U, true);
  assert(gateway_radio.last_tx().bytes[0] == ssot::kNackType);
  gateway_radio.inject(tracker_radio.last_tx());
  gateway.Poll(retry_at + 5U, true);
  gateway.Poll(retry_at + 6U, true);
  assert(Has(gateway_events, "DATA_DUP"));
  tracker_radio.inject(gateway_radio.last_tx());
  tracker.Poll(retry_at + 7U, true);
  assert(tracker.result() == Transport::Result::kAccepted);
  assert(gateway_payload.size == sizeof(payload));
  assert(memcmp(gateway_payload.bytes, payload, sizeof(payload)) == 0);
  assert(tracker_payload.size == sizeof(payload));
  assert(memcmp(tracker_payload.bytes, payload, sizeof(payload)) == 0);
  assert(!gateway.IsActive() && !tracker.IsActive());
}

/// A NACK-driven retry is observable without waiting for an ACK timeout.
static void TestNackRetryEvidence() {
  using Transport = reliable::Transport<FakeRadio>;
  FakeRadio gateway_radio(0U);
  Transport gateway(gateway_radio, 915.0F, 2, 0U);
  AcceptedPayload payload{};
  EventLog events{};
  gateway.SetEventCallback(Record, &events);
  assert(gateway.Arm(0U, 1U, AcceptPayload, &payload, 0x1234U));
  const uint8_t byte = 'x';
  assert(gateway.SendReliableData(1U, &byte, 1U, 0U));
  gateway.Poll(1U);
  Packet nack{};
  nack.source = 1U;
  nack.campaign = 0x1234U;
  nack.size = 2U;
  nack.bytes[0] = ssot::kNackType;
  nack.bytes[1] = 1U;
  gateway_radio.inject(nack);
  gateway.Poll(2U);
  assert(Has(events, "NACK_RX"));
  assert(Has(events, "RETRY_SCHEDULED"));
  gateway.Poll(3U);
  assert(gateway.attempts() == 2U);
}

/// A payload's E nibble must stay in the decoder, while P can still abort.
static void TestInteractiveCommandRouting() {
  using Decoder = reliable::HexDataCommandDecoder<16>;
  Decoder decoder;
  uint8_t bytes[16] = {};
  assert(!decoder.Consumes('E'));
  assert(decoder.Consumes('X'));
  assert(decoder.Feed('X', bytes, sizeof(bytes)) == Decoder::Result::kPending);
  assert(!decoder.Consumes('P'));
  assert(decoder.Feed('0', bytes, sizeof(bytes)) == Decoder::Result::kPending);
  assert(decoder.Feed('1', bytes, sizeof(bytes)) == Decoder::Result::kPending);
  assert(decoder.Feed('6', bytes, sizeof(bytes)) == Decoder::Result::kPending);
  assert(decoder.Consumes('E'));
  assert(decoder.Feed('E', bytes, sizeof(bytes)) == Decoder::Result::kComplete);
  assert(decoder.size() == 1U && bytes[0] == 'n');
  decoder.Reset();
  assert(!decoder.Consumes('E'));
  assert(decoder.Feed('X', bytes, sizeof(bytes)) == Decoder::Result::kPending);
  assert(decoder.Feed('\n', bytes, sizeof(bytes)) ==
         Decoder::Result::kInvalidHex);
  assert(!decoder.Consumes('E'));
}

int main() {
  TestBidirectionalAcknowledgmentHandoff();
  TestNackRetryEvidence();
  TestInteractiveCommandRouting();
  return 0;
}
