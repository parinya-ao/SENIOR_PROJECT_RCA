// License: No repository-wide license is declared.
// Existing rights and third-party notices are unchanged.

#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "arq.h"

static_assert(sizeof(arq::SenderState) == sizeof(int),
              "Preserve sender state layout");
static_assert(sizeof(arq::Result) == sizeof(int), "Preserve result layout");

static const uint8_t hello[] = "Hello World";
static arq::Frame data(void) {
  arq::Frame f = {arq::kData, 1, 2, 0x12345678, 0, 11, 0, {0}};
  memcpy(f.payload, hello, 11);
  return f;
}
static arq::Frame control(uint8_t type, uint8_t reason) {
  arq::Frame f = {type, 2, 1, 0x12345678, 0, 0, reason, {0}};
  return f;
}
static void codec(void) {
  const uint8_t golden[] = {1,   1,   1,   2,   0x78, 0x56, 0x34, 0x12,
                            0,   0,   11,  0,   'H',  'e',  'l',  'l',
                            'o', ' ', 'W', 'o', 'r',  'l',  'd'};
  uint8_t b[46];
  memset(b, 0xA5, sizeof b);
  arq::Frame f = data(), out;
  assert(arq::EncodeFrame(&f, b + 1, 44) == 23);
  assert(b[0] == 0xA5 && b[24] == 0xA5 && !memcmp(b + 1, golden, 23));
  assert(arq::DecodeFrame(&out, golden, 23) && out.session == 0x12345678);
  assert(!arq::EncodeFrame(&f, b, 22));
  for (size_t n = 0; n < 23; n++) assert(!arq::DecodeFrame(&out, golden, n));
  memcpy(b, golden, 23);
  b[0] = 2;
  assert(!arq::DecodeFrame(&out, b, 23));
  memcpy(b, golden, 23);
  b[1] = 4;
  assert(!arq::DecodeFrame(&out, b, 23));
  memcpy(b, golden, 23);
  b[10] = 33;
  assert(!arq::DecodeFrame(&out, b, 23));
  memcpy(b, golden, 23);
  b[11] = 1;
  assert(!arq::DecodeFrame(&out, b, 23));
  f = control(arq::kAck, 0);
  assert(arq::EncodeFrame(&f, b, 44) == 12);
  f.length = 1;
  assert(!arq::EncodeFrame(&f, b, 44));
  f = control(arq::kNack, 0);
  assert(!arq::EncodeFrame(&f, b, 44));
  for (int r = 1; r <= 3; r++) {
    f.reason = r;
    assert(arq::EncodeFrame(&f, b, 44) == 12);
  }
  f = data();
  f.length = 32;
  assert(arq::EncodeFrame(&f, b, 44) == 44);
  assert(arq::DecodeFrame(&out, b, 44));
  assert(!arq::DecodeFrame(&out, b, 45));
}
static arq::Sender fresh(uint32_t now) {
  arq::Sender s;
  arq::InitSender(&s);
  assert(!arq::RequestTransmission(&s, hello, 11, now, 2000));
  assert(arq::ArmSender(&s, 0x12345678));
  assert(arq::ArmSender(&s, 0x12345678));
  assert(arq::RequestTransmission(&s, hello, 11, now, 2000));
  assert(!arq::RequestTransmission(&s, hello, 11, now, 2000));
  assert(!arq::ArmSender(&s, 1));
  return s;
}
static void sender(void) {
  arq::Sender s = fresh(100);
  arq::Frame ack = control(arq::kAck, 0);
  assert(s.state == arq::SenderState::kTransmitting);
  arq::HandleTxCompletion(&s, 150, true);
  assert(s.state == arq::SenderState::kWaitingAck && s.retry_at == 2150);
  for (int field = 0; field < 5; field++) {
    arq::Frame bad = ack;
    if (field == 0) bad.src++;
    if (field == 1) bad.dst++;
    if (field == 2) bad.session++;
    if (field == 3) bad.sequence++;
    if (field == 4) bad.type = arq::kData;
    arq::HandleControlFrame(&s, &bad, 160);
    assert(s.state == arq::SenderState::kWaitingAck);
  }
  arq::HandleControlFrame(&s, &ack, 200);
  assert(s.state == arq::SenderState::kDelivered);
  assert(s.sequence == 1 && s.rtt_count == 1 && s.rtt_last == 50);
  assert(!arq::RequestTransmission(&s, hello, 11, 200, 1999));
  assert(arq::RequestTransmission(&s, hello, 11, 200, 2000));
  assert(s.state == arq::SenderState::kBackoff);
  arq::PollSender(&s, 3099);
  assert(s.attempts == 0);
  arq::PollSender(&s, 99 + ARQ_SPACING_MS);
  assert(s.attempts == 0);
  arq::PollSender(&s, 100 + ARQ_SPACING_MS);
  assert(s.state == arq::SenderState::kTransmitting);
  arq::HandleTxCompletion(&s, 3150, false);
  assert(s.result == arq::Result::kRadioError);
  assert(!arq::RequestTransmission(&s, hello, 11, 4000, 2000));
  for (int r = 1; r <= 2; r++) {
    s = fresh(0);
    arq::HandleTxCompletion(&s, 10, true);
    arq::Frame nack = control(arq::kNack, r);
    arq::HandleControlFrame(&s, &nack, 20);
    assert(s.state == arq::SenderState::kFailed && s.attempts == 1);
    assert(s.result ==
           (r == 1 ? arq::Result::kProtocolError : arq::Result::kRejected));
  }
  s = fresh(0);
  arq::Frame busy = control(arq::kNack, arq::kBusy);
  arq::HandleTxCompletion(&s, 10, true);
  uint32_t deadline = s.terminal_at;
  arq::HandleControlFrame(&s, &busy, 100);
  assert(s.state == arq::SenderState::kBackoff);
  for (uint32_t t = 200; t < 3000; t += 100)
    arq::HandleControlFrame(&s, &busy, t);
  assert(s.retry_at == 2010 && s.terminal_at == deadline);
  arq::HandleControlFrame(&s, &ack, 2999);
  assert(s.state == arq::SenderState::kDelivered);
  s = fresh(0);
  arq::Frame immutable = s.frame;
  for (int attempt = 1; attempt <= 5; attempt++) {
    assert(s.attempts == attempt &&
           !memcmp(&s.frame, &immutable, sizeof immutable));
    uint32_t done = s.last_start + 10;
    arq::HandleTxCompletion(&s, done, true);
    assert(s.interval == ((uint32_t)2000 << (attempt - 1)));
    arq::PollSender(&s, s.retry_at);
    if (s.state == arq::SenderState::kBackoff)
      arq::PollSender(&s, s.last_start + ARQ_SPACING_MS);
  }
  assert(s.result == arq::Result::kTimeoutExhausted && s.rtt_count == 0);
  s = fresh(UINT32_MAX - 100);
  arq::HandleTxCompletion(&s, UINT32_MAX - 50, true);
  arq::PollSender(&s, 1948);
  assert(s.state == arq::SenderState::kWaitingAck);
  arq::HandleControlFrame(&s, &ack, 1949);
  assert(s.state == arq::SenderState::kDelivered);
  s = fresh(0);
  s.sequence = 65535;
  s.frame.sequence = 65535;
  ack.sequence = 65535;
  arq::HandleTxCompletion(&s, 10, true);
  arq::HandleControlFrame(&s, &ack, 20);
  assert(s.sequence == 0 &&
         !arq::RequestTransmission(&s, hello, 11, 3000, 2000));
  assert(arq::ArmSender(&s, 0x12345679));
  s = fresh(0);
  arq::StopSender(&s);
  arq::HandleTxCompletion(&s, 10, true);
  ack.sequence = 0;
  arq::HandleControlFrame(&s, &ack, 20);
  assert(s.state == arq::SenderState::kDelivered &&
         !arq::RequestTransmission(&s, hello, 11, 3000, 2000));
  s = fresh(0);
  arq::PollSender(&s, 3000);
  assert(s.result == arq::Result::kRadioError);
  s = fresh(0);
  arq::HandleTxCompletion(&s, 10, true);
  ack.sequence = 0;
  arq::HandleControlFrame(&s, &ack, 20);
  assert(arq::ArmSender(&s, 0x12345679));
  assert(arq::RequestTransmission(&s, hello, 11, 30, 2000));
  assert(s.state == arq::SenderState::kBackoff);
  arq::PollSender(&s, ARQ_SPACING_MS - 1);
  assert(s.state == arq::SenderState::kBackoff);
  arq::PollSender(&s, ARQ_SPACING_MS);
  assert(s.state == arq::SenderState::kTransmitting);
}
static void absolute_deadline(void) {
  arq::Frame ack = control(arq::kAck, 0);
  const uint32_t starts[] = {0, UINT32_MAX - 100};
  for (size_t i = 0; i < sizeof starts / sizeof starts[0]; i++) {
    for (int offset = -1; offset <= 1; offset++) {
      arq::Sender s = fresh(starts[i]);
      arq::HandleTxCompletion(&s, starts[i] + 10, true);
      uint32_t now = s.terminal_at + offset;
      arq::HandleControlFrame(&s, &ack, now);
      if (offset < 0)
        assert(s.state == arq::SenderState::kDelivered &&
               s.result == arq::Result::kOk && s.sequence == 1);
      else
        assert(s.state == arq::SenderState::kFailed &&
               s.result == arq::Result::kTimeoutExhausted && s.sequence == 0 &&
               s.rtt_count == 0);
    }
  }
}

static void ack_matrix(void) {
  arq::Sender s;
  arq::Receiver r;
  arq::InitSender(&s);
  arq::InitReceiver(&r);
  assert(arq::ArmSender(&s, 0x12345678) && arq::ArmReceiver(&r, 0x12345678));
  uint32_t now = 0;
  for (uint32_t sequence = 0; sequence <= UINT16_MAX;
       sequence++, now += ARQ_SPACING_MS) {
    assert(arq::RequestTransmission(&s, hello, 11, now, ARQ_ACK_MIN_MS));
    assert(s.state == arq::SenderState::kTransmitting &&
           s.frame.sequence == sequence);
    arq::Frame ack = control(arq::kAck, 0);
    ack.sequence = (uint16_t)sequence;
    arq::HandleControlFrame(&s, &ack, now + 1);
    assert(s.state == arq::SenderState::kTransmitting);
    arq::HandleTxCompletion(&s, now + 10, true);
    for (unsigned field = 0; field < 8; field++) {
      arq::Frame bad = ack;
      if (field == 0) bad.src++;
      if (field == 1) bad.dst++;
      if (field == 2) bad.session++;
      if (field == 3) bad.sequence--;
      if (field == 4) bad.type = arq::kData;
      if (field == 5) bad.length = 1;
      if (field == 6) bad.reason = arq::kBusy;
      if (field == 7) bad.type = 0;
      arq::HandleControlFrame(&s, &bad, now + 15);
      assert(s.state == arq::SenderState::kWaitingAck &&
             s.sequence == sequence && s.rtt_count == sequence);
    }
    arq::Frame response;
    assert(arq::HandleDataFrame(&r, &s.frame, &response, false) &&
           response.type == arq::kAck);
    arq::HandleControlFrame(&s, &response, now + 20);
    assert(s.state == arq::SenderState::kDelivered &&
           s.result == arq::Result::kOk);
    assert(s.frame.sequence == sequence &&
           s.sequence == (uint16_t)(sequence + 1));
    assert(s.rtt_count == sequence + 1 && r.deliveries == sequence + 1);
    arq::HandleControlFrame(&s, &response, now + 21);
    assert(s.rtt_count == sequence + 1 &&
           s.state == arq::SenderState::kDelivered);
  }
  assert(s.used_up &&
         !arq::RequestTransmission(&s, hello, 11, now, ARQ_ACK_MIN_MS));
  s = fresh(0);
  arq::HandleTxCompletion(&s, 10, true);
  arq::Frame old = control(arq::kAck, 0);
  arq::InitSender(&s);
  arq::HandleControlFrame(&s, &old, 20);
  assert(s.state == arq::SenderState::kIdle && !s.armed);
  assert(arq::ArmSender(&s, 0x12345679));
  assert(
      arq::RequestTransmission(&s, hello, 11, ARQ_SPACING_MS, ARQ_ACK_MIN_MS));
  arq::HandleTxCompletion(&s, ARQ_SPACING_MS + 10, true);
  arq::HandleControlFrame(&s, &old, ARQ_SPACING_MS + 20);
  assert(s.state == arq::SenderState::kWaitingAck && s.rtt_count == 0);
  arq::PollSender(&s, s.terminal_at);
  old.session = s.session;
  arq::HandleControlFrame(&s, &old, s.terminal_at + 1);
  assert(s.state == arq::SenderState::kFailed &&
         s.result == arq::Result::kTimeoutExhausted && s.sequence == 0);
  puts(
      "ACK matrix: all 65536 sequences, mismatches, duplicates, reset and "
      "stale sessions PASS");
}

static void parser_fuzz(void) {
  uint32_t seed = 0x4c4f5241;
  for (unsigned iteration = 0; iteration < 50000; iteration++) {
    uint8_t input[64], encoded[44];
    seed = seed * 1664525U + 1013904223U;
    size_t length = seed % 65;
    for (size_t i = 0; i < length; i++) {
      seed = seed * 1664525U + 1013904223U;
      input[i] = (uint8_t)(seed >> 24);
    }
    if (iteration % 4 == 0) {
      arq::Frame f = data();
      f.length = (uint8_t)(seed % 33);
      length = arq::EncodeFrame(&f, input, sizeof input);
      if (iteration % 8 == 0) input[seed % length] ^= 0x80;
    }
    arq::Frame result, original;
    memset(&result, 0xA5, sizeof result);
    original = result;
    if (arq::DecodeFrame(&result, input, length)) {
      assert(arq::IsValidFrame(&result));
      size_t n = arq::EncodeFrame(&result, encoded, sizeof encoded);
      assert(n == length && !memcmp(input, encoded, n));
    } else
      assert(!memcmp(&result, &original, sizeof result));
  }
  puts("Parser fuzz: 50000 bounded inputs, seed 0x4c4f5241 PASS");
}

static void receiver(void) {
  arq::Receiver r;
  arq::InitReceiver(&r);
  arq::Frame f = data(), response;
  assert(!arq::HandleDataFrame(&r, &f, &response, false));
  assert(arq::ArmReceiver(&r, f.session));
  for (int field = 0; field < 4; field++) {
    arq::Frame bad = f;
    if (field == 0) bad.src++;
    if (field == 1) bad.dst++;
    if (field == 2) bad.session++;
    if (field == 3) bad.type = arq::kAck;
    assert(!arq::HandleDataFrame(&r, &bad, &response, false));
  }
  assert(arq::HandleDataFrame(&r, &f, &response, true));
  assert(response.reason == arq::kBusy);
  f.payload[0] = 'W';
  assert(arq::HandleDataFrame(&r, &f, &response, false));
  assert(response.reason == arq::kApplicationRejected && r.deliveries == 0);
  f = data();
  f.sequence = 1;
  assert(arq::HandleDataFrame(&r, &f, &response, false));
  assert(response.reason == arq::kUnexpectedSequence);
  f.sequence = 0;
  assert(arq::HandleDataFrame(&r, &f, &response, false));
  assert(response.type == arq::kAck);
  assert(r.deliveries == 1 && r.expected == 1);
  assert(arq::HandleDataFrame(&r, &f, &response, false));
  assert(r.deliveries == 1 && r.duplicates == 1);
  f.payload[0] = 'W';
  assert(arq::HandleDataFrame(&r, &f, &response, false));
  assert(response.reason == arq::kApplicationRejected && r.deliveries == 1);
  assert(arq::ArmReceiver(&r, 0x12345679));
  f = data();
  assert(!arq::HandleDataFrame(&r, &f, &response, false));
  assert(r.expected == 0);
  r.expected = 65535;
  f.session = r.session;
  f.sequence = 65535;
  assert(arq::HandleDataFrame(&r, &f, &response, false));
  assert(r.expected == 0);
  assert(arq::HandleDataFrame(&r, &f, &response, false));
  assert(response.type == arq::kAck);
}
static void fault_harness(void) {
  /* Each channel fault is injected at the real portable-module boundary. */
  for (int fault = 0; fault < 8; fault++) {
    arq::Sender s = fresh(0);
    arq::Receiver r;
    arq::InitReceiver(&r);
    arq::ArmReceiver(&r, s.session);
    arq::Frame response;
    arq::HandleTxCompletion(&s, 10, true);
    if (fault != 0 && fault != 4) {
      arq::Frame f = s.frame;
      if (fault == 3) f.payload[0] = 'W';
      assert(arq::HandleDataFrame(&r, &f, &response, fault == 5));
      if (fault == 2) {
        response.sequence++;
        arq::HandleControlFrame(&s, &response, 100);
      }
      if (fault == 5) arq::HandleControlFrame(&s, &response, 100);
      /* fault 1: dropped ACK; fault 3: dropped NACK; fault 4: CRC discard */
      if (fault == 6) {
        arq::PollSender(&s, 2010);
        arq::HandleControlFrame(&s, &response, 2500);
      }
    }
    if (s.state == arq::SenderState::kDelivered) continue;
    uint32_t retry_start = s.last_start + ARQ_SPACING_MS;
    arq::PollSender(&s, retry_start);
    assert(s.state == arq::SenderState::kTransmitting);
    if (fault == 7) {
      arq::HandleTxCompletion(&s, retry_start + 10, false);
      assert(s.result == arq::Result::kRadioError);
      continue;
    }
    arq::HandleTxCompletion(&s, retry_start + 10, true);
    assert(arq::HandleDataFrame(&r, &s.frame, &response, false));
    arq::HandleControlFrame(&s, &response, 3100);
    assert(s.state == arq::SenderState::kDelivered && r.deliveries == 1 &&
           s.rtt_count == 0);
  }
}
int main(void) {
  codec();
  sender();
  absolute_deadline();
  ack_matrix();
  parser_fuzz();
  receiver();
  fault_harness();
  puts("ARQ core: PASS");
}
