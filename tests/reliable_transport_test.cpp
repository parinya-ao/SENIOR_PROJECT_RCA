// Tests reliable DATA/ACK/NACK transitions, bounded retries, and duplicates.
#include "features/reliable_transfer/reliable_transport.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

struct FakeRadio {
  uint8_t local = 0, source = 0, destination = 0, length = 0, bytes[256] = {};
  uint16_t campaign_id = 0, incoming_campaign_id = 0;
  bool incoming = false, done = false, init_ok = true;
  unsigned starts = 0, inits = 0, sleeps = 0;
  int16_t send_error = 0, completion_error = 0, receive_error = 0;

  int16_t init(uint8_t address, float, int8_t, uint8_t) {
    ++inits;
    local = address;
    incoming = false;
    done = false;
    return init_ok ? 0 : -1;
  }
  int16_t send(uint8_t dst, const uint8_t* payload, uint8_t size) {
    return send(dst, 0, payload, size);
  }
  int16_t send(uint8_t dst, uint16_t campaign, const uint8_t* payload,
               uint8_t size) {
    ++starts;
    done = false;
    destination = dst;
    campaign_id = campaign;
    length = size;
    memcpy(bytes, payload, size);
    return send_error;
  }
  int16_t send_done() {
    if (completion_error) return completion_error;
    return done ? int16_t{1} : int16_t{0};
  }
  bool available() { return incoming; }
  int16_t recv(uint8_t* src, uint8_t* dst, uint8_t* payload, size_t capacity,
               uint8_t* size) {
    return recv(src, dst, nullptr, payload, capacity, size);
  }
  int16_t recv(uint8_t* src, uint8_t* dst, uint16_t* campaign, uint8_t* payload,
               size_t capacity, uint8_t* size) {
    incoming = false;
    *src = source;
    *dst = destination;
    if (campaign) *campaign = incoming_campaign_id;
    *size = length;
    if (receive_error) {
      *size = 0;
      return receive_error;
    }
    assert(length <= capacity);
    memcpy(payload, bytes, length);
    return 0;
  }
  int16_t sleep() {
    ++sleeps;
    return 0;
  }
};

using Transport = reliable::Transport<FakeRadio>;
struct Application {
  unsigned applied = 0;
  bool reject = false;
};
struct EventStats {
  unsigned data_tx = 0, ack_tx = 0, nack_tx = 0, ack_accepted = 0,
           nack_received = 0, destination_discards = 0;
  unsigned retries = 0, duplicates = 0, failures = 0, total = 0;
};

static void count_event(void* context, const char* event, uint8_t, uint8_t,
                        int16_t) {
  EventStats* stats = static_cast<EventStats*>(context);
  ++stats->total;
  if (!strcmp(event, "DATA_TX_BEGIN"))
    ++stats->data_tx;
  else if (!strcmp(event, "ACK_TX_BEGIN"))
    ++stats->ack_tx;
  else if (!strcmp(event, "NACK_TX_BEGIN"))
    ++stats->nack_tx;
  else if (!strcmp(event, "ACK_ACCEPTED"))
    ++stats->ack_accepted;
  else if (!strcmp(event, "NACK_RX"))
    ++stats->nack_received;
  else if (!strcmp(event, "RETRY_SCHEDULED"))
    ++stats->retries;
  else if (!strcmp(event, "DATA_DUP"))
    ++stats->duplicates;
  else if (!strcmp(event, "TRANSACTION_FAILED"))
    ++stats->failures;
  else if (!strcmp(event, "RX_DISCARD_DEST"))
    ++stats->destination_discards;
}

static bool accept(void* context, uint8_t sequence, const uint8_t* data,
                   uint8_t size) {
  assert(sequence != 0);
  Application* app = static_cast<Application*>(context);
  if (app->reject || size == 0 || data[0] != 'h') return false;
  ++app->applied;
  return true;
}
static const uint8_t hello[] = "hello world";

struct Pair {
  FakeRadio a, b;
  Application aa, bb;
  EventStats events;
  Transport x, y;
  uint16_t session_id;
  explicit Pair(uint8_t first = 0) : x(a, 915.0f, 2, 0), y(b, 915.0f, 2, 0) {
    session_id = 0x1234;
    x.SetEventCallback(count_event, &events);
    y.SetEventCallback(count_event, &events);
    assert(x.Arm(first, first ^ 1, accept, &aa, session_id));
    assert(y.Arm(first ^ 1, first, accept, &bb));
  }
};

static void deliver(FakeRadio& from, FakeRadio& to) {
  to.source = from.local;
  to.destination = from.destination;
  to.incoming_campaign_id = from.campaign_id;
  to.length = from.length;
  memcpy(to.bytes, from.bytes, from.length);
  to.incoming = true;
}

static void start_data(Pair& p, uint8_t sequence = 1, uint32_t now = 0) {
  assert(p.x.SendReliableData(sequence, hello, sizeof(hello) - 1, now));
  assert(p.a.campaign_id == p.session_id && p.a.length == 13 &&
         p.a.bytes[0] == ssot::kDataType && p.a.bytes[1] == sequence &&
         !memcmp(p.a.bytes + 2, hello, sizeof(hello) - 1));
  p.a.done = true;
  p.x.Poll(now + 1);
}

static void finish_reply(FakeRadio& radio, Transport& transport, uint32_t now) {
  radio.done = true;
  transport.Poll(now);
}

static void successful_round_trip(Pair& p, uint32_t now = 0) {
  deliver(p.a, p.b);
  p.y.Poll(now + 2);
  assert(p.b.length == 2 && p.b.bytes[0] == ssot::kAckType &&
         p.b.bytes[1] == 1 && p.b.campaign_id == p.session_id);
  finish_reply(p.b, p.y, now + 3);
  deliver(p.b, p.a);
  p.x.Poll(now + 4);
  assert(p.x.result() == Transport::Result::kAccepted);
}

static bool dropped(unsigned loss_percent, uint32_t& random) {
  random = random * 1664525U + 1013904223U;
  return random % 100U < loss_percent;
}

struct LossMetrics {
  unsigned attempts = 0, ack_tx = 0, nack_tx = 0, retries = 0, timeouts = 0,
           duplicates = 0;
};

static bool loss_scenario(unsigned loss_percent, uint32_t seed,
                          LossMetrics* metrics) {
  Pair p;
  uint32_t now = 0, random = seed;
  assert(p.x.SendReliableData(1, hello, sizeof(hello) - 1, now));
  p.a.done = true;
  p.x.Poll(++now);
  for (unsigned attempt = 0; attempt < ssot::kMaxAttempts &&
                             p.x.result() == Transport::Result::kPending;
       ++attempt) {
    if (!dropped(loss_percent, random)) {
      deliver(p.a, p.b);
      p.y.Poll(++now);
      if (p.y.state() == Transport::State::kTxResponse) {
        finish_reply(p.b, p.y, ++now);
        if (!dropped(loss_percent, random)) {
          deliver(p.b, p.a);
          p.x.Poll(++now);
        }
      }
    }
    if (p.x.result() == Transport::Result::kAccepted) break;
    if (p.x.state() == Transport::State::kWaitResponse) {
      ++metrics->timeouts;
      now += LORA_ACK_TIMEOUT_MS + 1U;
      p.x.Poll(now);
    }
    if (p.x.state() == Transport::State::kRetryPending) {
      p.x.Poll(++now);
      if (p.x.state() == Transport::State::kTxData) {
        p.a.done = true;
        p.x.Poll(++now);
      }
    }
  }
  assert(p.x.attempts() <= ssot::kMaxAttempts);
  if (p.x.result() == Transport::Result::kAccepted)
    assert(p.bb.applied == 1);
  else
    assert(p.x.result() == Transport::Result::kAckTimeout);
  metrics->attempts = p.x.attempts();
  metrics->ack_tx = p.events.ack_tx;
  metrics->nack_tx = p.events.nack_tx;
  metrics->retries = p.events.retries + p.events.nack_received;
  metrics->duplicates = p.events.duplicates;
  return p.x.result() == Transport::Result::kAccepted;
}

template <class T, class Action>
static void count_transition(T& transport, unsigned& transitions,
                             Action action) {
  const typename T::State before = transport.state();
  action();
  transitions += before != transport.state();
}

static void stress_round_trips(unsigned transactions) {
  Pair p;
  unsigned transitions = 0;
  for (unsigned i = 0; i < transactions; ++i) {
    const uint32_t now = i * 10U;
    if (i) {
      p.session_id = static_cast<uint16_t>(i);
      if (!p.session_id) p.session_id = 1;
      count_transition(p.x, transitions, [&] {
        assert(p.x.Arm(0, 1, accept, &p.aa, p.session_id));
      });
      count_transition(p.y, transitions,
                       [&] { assert(p.y.Arm(1, 0, accept, &p.bb)); });
    }
    count_transition(p.x, transitions, [&] {
      assert(p.x.SendReliableData(1, hello, sizeof(hello) - 1, now));
    });
    p.a.done = true;
    count_transition(p.x, transitions, [&] { p.x.Poll(now + 1); });
    deliver(p.a, p.b);
    count_transition(p.y, transitions, [&] { p.y.Poll(now + 2); });
    assert(p.b.bytes[0] == ssot::kAckType);
    p.b.done = true;
    count_transition(p.y, transitions, [&] { p.y.Poll(now + 3); });
    deliver(p.b, p.a);
    count_transition(p.x, transitions, [&] { p.x.Poll(now + 4); });
    assert(p.x.result() == Transport::Result::kAccepted);
    assert(p.x.attempts() == 1 && p.y.duplicates() == 0);
    assert(p.bb.applied == i + 1);
  }
  assert(transitions >= 10000);
  assert(p.events.ack_accepted == transactions &&
         p.events.ack_tx == transactions);
  printf(
      "STRESS transactions=%u state_transitions=%u accepted=%u duplicates=%u\n",
      transactions, transitions, p.events.ack_accepted, p.events.duplicates);
}

int main() {
  for (uint8_t first = 0; first < 2; ++first) {
    Pair p(first);
    start_data(p);
    successful_round_trip(p);
    assert(p.bb.applied == 1);
  }

  // Continuous unrelated traffic cannot keep a response window or retry open.
  {
    Pair p;
    start_data(p, 1, UINT32_MAX - 100);
    uint32_t now = UINT32_MAX - 99;
    for (unsigned i = 1; i <= ssot::kMaxAttempts; ++i) {
      p.a.incoming = true;
      p.a.source = 9;
      now += LORA_ACK_TIMEOUT_MS;
      p.x.Poll(now);
      if (i == ssot::kMaxAttempts) break;
      assert(p.x.state() == Transport::State::kRetryPending);
      p.a.incoming = true;
      p.x.Poll(++now);
      assert(p.x.state() == Transport::State::kTxData && p.a.starts == i + 1);
      p.a.done = true;
      p.x.Poll(++now);
    }
    assert(p.x.result() == Transport::Result::kAckTimeout);
  }

  // A delayed poll cannot extend the absolute transaction cap across wrap.
  {
    Pair p;
    constexpr uint32_t start = UINT32_MAX - 500;
    constexpr uint32_t cap =
        ssot::kMaxAttempts * (LORA_TX_TIMEOUT_MS + LORA_ACK_TIMEOUT_MS);
    start_data(p, 1, start);
    p.x.Poll(start + cap);
    assert(p.x.result() == Transport::Result::kAckTimeout && p.a.starts == 1);
  }

  // Invalid identity cannot bind an unarmed receiver to a campaign.
  for (unsigned fault = 0; fault < 4; ++fault) {
    Pair p;
    start_data(p);
    deliver(p.a, p.b);
    switch (fault) {
      case 0:
        p.b.incoming_campaign_id = 0;
        break;
      case 1:
        p.b.bytes[1] = 0;
        break;
      case 2:
        p.b.receive_error = RADIOLIB_ERR_CRC_MISMATCH;
        break;
      case 3:
        p.b.length = 2;
        break;
      default:
        assert(false);
    }
    p.y.Poll(1);
    assert(p.y.campaign_id() == 0 && p.bb.applied == 0 && p.b.starts == 0);
  }

  // A completed request cannot share its identity with a delayed ACK.
  {
    Pair p;
    start_data(p);
    successful_round_trip(p);
    assert(!p.x.SendReliableData(1, hello, sizeof(hello) - 1, 5));
    assert(p.x.Arm(0, 1, accept, &p.aa, p.session_id));
    assert(!p.x.SendReliableData(1, hello, sizeof(hello) - 1, 6));
    assert(p.a.starts == 1);
    start_data(p, 2, 7);
    p.a.source = 1;
    p.a.destination = 0;
    p.a.incoming_campaign_id = p.session_id;
    p.a.length = 2;
    p.a.bytes[0] = ssot::kAckType;
    p.a.bytes[1] = 1;
    p.a.incoming = true;
    p.x.Poll(9);
    assert(p.x.state() == Transport::State::kWaitResponse);
  }

  for (uint16_t i = 0; i < 10; ++i) {
    Pair p;
    p.session_id += i;
    assert(p.x.Arm(0, 1, accept, &p.aa, p.session_id));
    start_data(p);
    deliver(p.a, p.b);
    p.b.destination = 2;
    p.y.Poll(2);
    assert(p.events.destination_discards == 1 && p.bb.applied == 0 &&
           p.b.starts == 0 && p.y.campaign_id() == 0);
    successful_round_trip(p);
  }

  // Only the next 16-bit campaign can follow sequence 255 without RX rearm.
  {
    Pair p;
    p.session_id = UINT16_MAX;
    assert(p.x.Arm(0, 1, accept, &p.aa, p.session_id));
    for (unsigned seq = 1; seq <= UINT8_MAX; ++seq) {
      const uint32_t now = seq * 10;
      start_data(p, static_cast<uint8_t>(seq), now);
      deliver(p.a, p.b);
      p.y.Poll(now + 2);
      assert(p.b.bytes[0] == ssot::kAckType && p.b.bytes[1] == seq);
      finish_reply(p.b, p.y, now + 3);
      deliver(p.b, p.a);
      p.x.Poll(now + 4);
      assert(p.x.result() == Transport::Result::kAccepted);
    }
    assert(!p.x.SendReliableData(1, hello, sizeof(hello) - 1, 2600));
    p.session_id = 1;
    assert(p.x.Arm(0, 1, accept, &p.aa, p.session_id));
    start_data(p, 1, 2601);
    deliver(p.a, p.b);
    p.b.incoming_campaign_id = UINT16_MAX - 1;
    p.y.Poll(2602);
    assert(p.bb.applied == 255 && p.b.starts == 255);
    successful_round_trip(p, 2601);
    assert(p.bb.applied == 256 && p.y.campaign_id() == 1);
  }

  // A NACK requests a bounded retransmission; the next matching ACK accepts it.
  {
    Pair p;
    p.bb.reject = true;
    start_data(p);
    deliver(p.a, p.b);
    p.y.Poll(2);
    assert(p.b.bytes[0] == ssot::kNackType && p.b.bytes[1] == 1);
    finish_reply(p.b, p.y, 3);
    deliver(p.b, p.a);
    p.x.Poll(4);
    assert(p.x.state() == Transport::State::kRetryPending &&
           p.x.attempts() == 1);
    p.bb.reject = false;
    p.x.Poll(5);
    assert(p.a.starts == 2 && p.a.bytes[0] == ssot::kDataType);
    p.a.done = true;
    p.x.Poll(6);
    deliver(p.a, p.b);
    p.y.Poll(7);
    finish_reply(p.b, p.y, 8);
    deliver(p.b, p.a);
    p.x.Poll(9);
    assert(p.x.result() == Transport::Result::kAccepted && p.bb.applied == 1);
    printf(
        "NACK retry data_tx=%u nack_tx=%u nack_rx=%u ack_tx=%u "
        "ack_accepted=%u\n",
        p.events.data_tx, p.events.nack_tx, p.events.nack_received,
        p.events.ack_tx, p.events.ack_accepted);
  }

  // A lost NACK times out; a later NACK still schedules a bounded retry.
  {
    Pair p;
    p.bb.reject = true;
    start_data(p);
    deliver(p.a, p.b);
    p.y.Poll(2);
    finish_reply(p.b, p.y, 3);  // Drop NACK.
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 2);
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 3);
    p.a.done = true;
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 4);
    deliver(p.a, p.b);
    p.y.Poll(LORA_ACK_TIMEOUT_MS + 5);
    assert(p.b.bytes[0] == ssot::kNackType);
    finish_reply(p.b, p.y, LORA_ACK_TIMEOUT_MS + 6);
    deliver(p.b, p.a);
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 7);
    assert(p.x.state() == Transport::State::kRetryPending);
    assert(p.x.attempts() == 2);
  }

  // A lost ACK causes a retry; the receiver ACKs the duplicate without
  // reapplying it.
  // Re-arming the same receiver object after ACK loss must retain the accepted
  // session's duplicate record and replay its ACK without invoking the app.
  {
    Pair p;
    start_data(p);
    deliver(p.a, p.b);
    p.y.Poll(2);
    finish_reply(p.b, p.y, 3);
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 2);
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 3);
    assert(p.a.starts == 2);
    p.a.done = true;
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 4);
    deliver(p.a, p.b);
    p.y.Poll(LORA_ACK_TIMEOUT_MS + 5);
    assert(p.bb.applied == 1 && p.y.duplicates() == 1);
    finish_reply(p.b, p.y, LORA_ACK_TIMEOUT_MS + 6);
    deliver(p.b, p.a);
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 7);
    assert(p.x.result() == Transport::Result::kAccepted);
  }

  // An ACK arriving after the timeout cannot accept an attempt already queued
  // for retry.
  {
    Pair p;
    start_data(p);
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 2);
    assert(p.x.state() == Transport::State::kRetryPending);
    p.a.source = 1;
    p.a.destination = 0;
    p.a.incoming_campaign_id = p.session_id;
    p.a.length = 2;
    p.a.bytes[0] = ssot::kAckType;
    p.a.bytes[1] = 1;
    p.a.incoming = true;
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 3);
    assert(p.x.state() == Transport::State::kTxData &&
           p.x.result() == Transport::Result::kPending && p.a.starts == 2);
    p.a.done = true;
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 5);
    p.a.incoming = true;
    p.a.source = 1;
    p.a.destination = 0;
    p.a.incoming_campaign_id = p.session_id;
    p.a.length = 2;
    p.a.bytes[0] = ssot::kAckType;
    p.a.bytes[1] = 1;
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 6);
    assert(p.x.result() == Transport::Result::kAccepted);
    p.a.incoming = true;
    p.a.source = 1;
    p.a.destination = 0;
    p.a.incoming_campaign_id = p.session_id;
    p.a.length = 2;
    p.a.bytes[0] = ssot::kAckType;
    p.a.bytes[1] = 1;
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 7);
    assert(p.x.result() == Transport::Result::kAccepted);
  }

  // Invalid, unrelated and oversized packets are discarded without resetting
  // the radio.
  {
    Pair p;
    const unsigned before = p.b.inits;
    p.b.source = 9;
    p.b.destination = 1;
    p.b.length = 3;
    p.b.bytes[0] = ssot::kDataType;
    p.b.bytes[1] = 1;
    p.b.bytes[2] = 'x';
    p.b.incoming = true;
    p.y.Poll(1);
    assert(p.b.inits == before && p.bb.applied == 0);
    p.b.source = 0;
    p.b.destination = 0;
    p.b.incoming_campaign_id = p.session_id;
    p.b.length = 13;
    p.b.bytes[0] = ssot::kDataType;
    p.b.bytes[1] = 1;
    memcpy(p.b.bytes + 2, hello, sizeof(hello) - 1);
    p.b.incoming = true;
    p.y.Poll(2);
    assert(p.b.inits == before && p.bb.applied == 0 && p.b.starts == 0);
    assert(p.events.destination_discards == 1);
    p.b.destination = 1;
    p.b.length = 252;
    p.b.incoming = true;
    p.y.Poll(3);
    assert(p.b.inits == before && p.bb.applied == 0 && p.b.starts == 0);
  }

  // Invalid arguments and malformed ACK/NACK responses never accept a
  // transaction.
  {
    Pair p;
    uint8_t payload[250];
    memset(payload, 'h', sizeof(payload));
    assert(!p.x.SendReliableData(0, hello, sizeof(hello) - 1, 0));
    assert(!p.x.SendReliableData(1, hello, 0, 0));
    assert(!p.x.SendReliableData(1, payload, sizeof(payload), 0));
    assert(p.a.starts == 0);
  }
  {
    Pair p;
    start_data(p);
    const uint8_t frames[][3] = {{ssot::kAckType, 2, 0},
                                 {ssot::kNackType, 2, 0},
                                 {ssot::kAckType, 1, 0xAA},
                                 {ssot::kNackType, 1, 0xAA},
                                 {0xFE, 1, 0},
                                 {ssot::kAckType, 1, 0}};
    const uint8_t sizes[] = {2, 2, 3, 3, 2, 2};
    for (unsigned i = 0; i < sizeof(sizes); ++i) {
      p.a.source = (i == 0) ? 9 : 1;
      p.a.destination = (i == 1 || i == 5) ? 1 : 0;
      p.a.incoming_campaign_id = p.session_id;
      p.a.length = sizes[i];
      memcpy(p.a.bytes, frames[i], sizes[i]);
      p.a.incoming = true;
      p.x.Poll(4 + i);
      assert(p.x.state() == Transport::State::kWaitResponse &&
             p.x.result() == Transport::Result::kPending);
    }
  }

  // Corrupted application data is rejected and produces a NACK.
  {
    Pair p;
    start_data(p);
    deliver(p.a, p.b);
    p.b.bytes[2] ^= 1;
    p.y.Poll(2);
    assert(p.bb.applied == 0 && p.b.bytes[0] == ssot::kNackType);
  }

  // The payload maximum keeps RadioHead's four-byte header within 255 bytes.
  {
    Pair p;
    uint8_t data[249];
    memset(data, 'h', sizeof(data));
    assert(p.x.SendReliableData(1, data, sizeof(data), 0));
    assert(p.a.length == 251 && p.a.bytes[0] == ssot::kDataType);
  }

  // Radio initialization failure is reported; TX timeout stops without an
  // unbounded loop.
  {
    FakeRadio radio;
    Application app;
    Transport transport(radio, 915.0f, 2, 0);
    radio.init_ok = false;
    assert(!transport.Arm(0, 1, accept, &app));
    assert(transport.result() == Transport::Result::kRadioError);
    radio.init_ok = true;
    assert(transport.Arm(0, 1, accept, &app));
    assert(!transport.SendReliableData(1, hello, sizeof(hello) - 1, 0));
    assert(radio.starts == 0);
  }
  {
    Pair p;
    start_data(p);
    deliver(p.a, p.b);
    p.b.receive_error = -6;
    p.y.Poll(2);
    assert(p.y.result() == Transport::Result::kRadioError && !p.y.IsActive());
    p.b.receive_error = 0;
    assert(p.y.Arm(1, 0, accept, &p.bb));
  }
  {
    Pair p;
    assert(p.x.SendReliableData(1, hello, sizeof(hello) - 1, 0));
    p.x.Poll(LORA_TX_TIMEOUT_MS + 1);
    assert(p.x.result() == Transport::Result::kTxTimeout && !p.x.IsActive());
  }

  // A fresh arm supports another bounded communication session.
  {
    Pair p;
    start_data(p);
    successful_round_trip(p);
    p.session_id = 0x2345;
    assert(p.x.Arm(0, 1, accept, &p.aa, p.session_id));
    assert(p.y.Arm(1, 0, accept, &p.bb));
    start_data(p, 1, 10000);
    successful_round_trip(p, 10000);
    assert(p.bb.applied == 2);
  }
  // NACK retry exhaustion is explicit and never exceeds the configured attempt
  // limit.
  {
    Pair p;
    p.bb.reject = true;
    start_data(p);
    uint32_t now = 1;
    for (unsigned attempt = 1; attempt <= ssot::kMaxAttempts; ++attempt) {
      deliver(p.a, p.b);
      p.y.Poll(++now);
      assert(p.b.bytes[0] == ssot::kNackType && p.b.bytes[1] == 1);
      finish_reply(p.b, p.y, ++now);
      deliver(p.b, p.a);
      p.x.Poll(++now);
      if (attempt < ssot::kMaxAttempts) {
        assert(p.x.state() == Transport::State::kRetryPending);
        p.x.Poll(++now);
        p.a.done = true;
        p.x.Poll(++now);
      }
    }
    assert(p.x.result() == Transport::Result::kRejected);
    assert(p.x.attempts() == ssot::kMaxAttempts);
    printf(
        "NACK exhaustion data_tx=%u nack_tx=%u result=Rejected "
        "attempts=%u/%u\n",
        p.events.data_tx, p.events.nack_tx, p.x.attempts(), ssot::kMaxAttempts);
  }

  // A stale ACK with the same peer and sequence cannot finish a new session.
  {
    Pair p;
    start_data(p);
    assert(p.a.campaign_id == p.session_id);
    p.a.source = 1;
    p.a.destination = 0;
    p.a.incoming_campaign_id = 0x4321;
    p.a.length = 2;
    p.a.bytes[0] = ssot::kAckType;
    p.a.bytes[1] = 1;
    p.a.incoming = true;
    p.x.Poll(4);
    assert(p.x.result() == Transport::Result::kPending);
    assert(p.x.state() == Transport::State::kWaitResponse);

    p.a.incoming_campaign_id = p.session_id;
    p.a.incoming = true;
    p.x.Poll(5);
    assert(p.x.result() == Transport::Result::kAccepted);
  }
  // DATA for a different campaign from the expected peer is discarded before
  // application delivery or ACK/NACK generation.
  {
    Pair p;
    start_data(p);
    deliver(p.a, p.b);
    p.y.Poll(2);
    finish_reply(p.b, p.y, 3);
    assert(p.bb.applied == 1 && p.b.starts == 1);
    p.b.source = 0;
    p.b.destination = 1;
    p.b.incoming_campaign_id = 0x4321;
    p.b.length = 13;
    p.b.bytes[0] = ssot::kDataType;
    p.b.bytes[1] = 2;
    memcpy(p.b.bytes + 2, hello, sizeof(hello) - 1);
    p.b.incoming = true;
    p.y.Poll(4);
    assert(p.bb.applied == 1 && p.b.starts == 1);
  }
  {
    Pair p;
    start_data(p);
    deliver(p.a, p.b);
    p.y.Poll(2);
    assert(p.bb.applied == 1);
    finish_reply(p.b, p.y, 3);  // ACK lost; receiver restarts.
    assert(p.y.Arm(1, 0, accept, &p.bb));
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 2);
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 3);
    p.a.done = true;
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 4);
    deliver(p.a, p.b);
    p.y.Poll(LORA_ACK_TIMEOUT_MS + 5);
    assert(p.bb.applied == 1 && p.y.duplicates() == 1);
    assert(p.b.bytes[0] == ssot::kAckType);
    finish_reply(p.b, p.y, LORA_ACK_TIMEOUT_MS + 6);
    deliver(p.b, p.a);
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 7);
    assert(p.x.result() == Transport::Result::kAccepted);
  }

  {
    Pair p;
    p.y.SuppressNextResponse();
    start_data(p);
    deliver(p.a, p.b);
    p.y.Poll(2);
    assert(p.bb.applied == 1 && p.b.starts == 0 && !p.y.IsActive());
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 2);
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 3);
    p.a.done = true;
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 4);
    deliver(p.a, p.b);
    p.y.Poll(LORA_ACK_TIMEOUT_MS + 5);
    assert(p.bb.applied == 1 && p.y.duplicates() == 1);
    finish_reply(p.b, p.y, LORA_ACK_TIMEOUT_MS + 6);
    deliver(p.b, p.a);
    p.x.Poll(LORA_ACK_TIMEOUT_MS + 7);
    assert(p.x.result() == Transport::Result::kAccepted && p.a.starts == 2);
  }

  const unsigned losses[] = {0U, 1U, 5U, 10U, 20U, 30U, 50U, 100U};
  for (size_t rate = 0; rate < sizeof(losses) / sizeof(losses[0]); ++rate) {
    unsigned delivered = 0, total_attempts = 0, total_acks = 0, total_nacks = 0;
    unsigned total_retries = 0, total_timeouts = 0, total_duplicates = 0;
    for (uint32_t scenario = 0; scenario < 100; ++scenario) {
      LossMetrics metrics;
      delivered += loss_scenario(
          losses[rate], scenario + losses[rate] * 1000U + 1U, &metrics);
      total_attempts += metrics.attempts;
      total_acks += metrics.ack_tx;
      total_nacks += metrics.nack_tx;
      total_retries += metrics.retries;
      total_timeouts += metrics.timeouts;
      total_duplicates += metrics.duplicates;
    }
    assert(total_attempts <= 100U * ssot::kMaxAttempts);
    if (losses[rate] == 0) assert(delivered == 100 && total_timeouts == 0);
    if (losses[rate] == 100)
      assert(delivered == 0 && total_attempts == 100U * ssot::kMaxAttempts);
    printf(
        "LOSS %u%% seed_start=%u transactions=100 delivered=%u/100 data_tx=%u "
        "ack_tx=%u nack_tx=%u retries=%u timeouts=%u duplicates=%u\n",
        losses[rate], losses[rate] * 1000U + 1U, delivered, total_attempts,
        total_acks, total_nacks, total_retries, total_timeouts,
        total_duplicates);
  }
  {
    Pair p;
    p.a.send_error = -4;
    assert(!p.x.SendReliableData(1, hello, 11, 0));
    assert(p.x.result() == Transport::Result::kRadioError);
    assert(p.x.radio_error() == -4);
  }
  stress_round_trips(3000);
  puts(
      "PASS stable-API transport: ACK/NACK, bounded retry, duplicate, bounds "
      "and rearm");
}
