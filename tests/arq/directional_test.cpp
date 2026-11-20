// License: No repository-wide license is declared.
// Existing rights and third-party notices are unchanged.

// Host adapter simulation; IRQ/FIFO observations here are not physical RF
// evidence.

#include <assert.h>

// Load the implementation in this fixture to observe private foreground state.
// NOLINTBEGIN(bugprone-suspicious-include)
#include "../../stable_lib/arq/arq_config.h"
#if defined(ARQ_ROLE_SENDER)
#include "../../src/sender/appcode/arq/sender.cpp"
#else
#include "../../src/receiver/appcode/arq/receiver.cpp"
#endif
#include "../../src/shared/diagnostics/arq_bench.cpp"
#include "../../src/shared/protocol/arq_ingress.cpp"
#include "../../src/shared/radio/arq_radio.cpp"
#include "../../stable_lib/arq/board_ssot.c"
#include "../../stable_lib/arq/commands.cpp"
#include "../../stable_lib/arq/diagnostics.cpp"
// NOLINTEND(bugprone-suspicious-include)
#include "diagnostics_test_access.h"
using namespace arq::app;

static void cmd(const char* text) {
  for (; *text; ++text) FeedCommandByte(*text);
  FeedCommandByte('\n');
}
static void clear_log() { ResetLog(); }
static bool logged(const char* name) {
  for (uint8_t i = 0; i < arq::diagnostics::PendingLineCount(); i++)
    if (strstr(QueuedLogLine(i), name)) return true;
  return false;
}
int main(int argc, char** argv) {
  bool nack = argc > 1 && !strcmp(argv[1], "nack");
  Initialize();
  assert(ready && parked && !tx_starts);
  cmd("ARM 12345678");
  assert(raw_regs[1] == 0x85);
  const char* payload =
      arq::config::kSenderId == 1 ? "HELLO_LORA_GW" : "HELLO_LORA_TR";
  if (nack) payload = "REJECT_LORA";
#if defined(ARQ_ROLE_SENDER)
  char text[80] = "SEND ";
  for (size_t i = 0; i < strlen(payload); i++)
    sprintf(text + 5 + 2 * i, "%02X", (uint8_t)payload[i]);
  cmd(text);
  Poll();
  assert(tx_starts == 1 && raw_regs[1] == 0x83);
  const uint8_t expected_header[] = {1,
                                     1,
                                     arq::config::kSenderId,
                                     arq::config::kReceiverId,
                                     0x78,
                                     0x56,
                                     0x34,
                                     0x12,
                                     0,
                                     0,
                                     static_cast<uint8_t>(strlen(payload)),
                                     0};
  assert(sent_length == sizeof expected_header + strlen(payload));
  assert(!memcmp(sent, expected_header, sizeof expected_header));
  assert(!memcmp(sent + sizeof expected_header, payload, strlen(payload)));
  arq::Frame data;
  assert(arq::DecodeFrame(&data, sent, sent_length));
  assert(data.src == arq::config::kSenderId &&
         data.dst == arq::config::kReceiverId);
  assert(data.sequence == 0 && data.session == 0x12345678);
  assert(data.length == strlen(payload) &&
         !memcmp(data.payload, payload, data.length));
  irq_flags = 8;
  Poll();
  assert(sender.state == arq::SenderState::kWaitingAck && raw_regs[1] == 0x85);
  arq::Frame response = {
      (uint8_t)(nack ? arq::kNack : arq::kAck),
      arq::config::kReceiverId,
      arq::config::kSenderId,
      0x12345678,
      0,
      0,
      (uint8_t)(nack ? arq::kApplicationRejected : arq::kNone),
      {0}};
  for (int invalid = 0; invalid < 4; invalid++) {
    arq::Frame bad = response;
    if (invalid == 0) ++bad.session;
    if (invalid == 1) ++bad.sequence;
    if (invalid == 2) bad.src = bad.dst;
    packet_length = arq::EncodeFrame(&bad, packet, 44);
    if (invalid == 3) --packet_length;
    irq_flags = 0x40;
    clear_log();
    Poll();
    assert(sender.state == arq::SenderState::kWaitingAck);
    assert(!logged("e=DELIVERED ") && !logged("e=REJECTED "));
  }
  packet_length = arq::EncodeFrame(&response, packet, 44);
  irq_flags = 0x40;
  clear_log();
  if (argc > 1 && !strcmp(argv[1], "expired")) {
    clock_ms = sender.terminal_at;
    Poll();
    assert(sender.result == arq::Result::kTimeoutExhausted &&
           sender.sequence == 0);
    assert(!logged("e=DELIVERED "));
    return 0;
  }
  Poll();
  assert(sender.result == (nack ? arq::Result::kRejected : arq::Result::kOk));
  assert(sender.sequence == (nack ? 0 : 1));
  assert(logged(nack ? "e=REJECTED " : "e=DELIVERED ") && logged(" q=0 "));
  irq_flags = 0x40;
  clear_log();
  Poll();  // duplicate control cannot repeat success
  assert(!logged("e=DELIVERED ") && !logged("e=REJECTED "));
#else
  arq::Frame data = {arq::kData,
                     arq::config::kSenderId,
                     arq::config::kReceiverId,
                     0x12345678,
                     0,
                     0,
                     0,
                     {0}};
  data.length = strlen(payload);
  memcpy(data.payload, payload, data.length);
  packet_length = arq::EncodeFrame(&data, packet, 44);
  irq_flags = 0x40;
  clear_log();
  Poll();
  assert(receiver.deliveries == (nack ? 0 : 1) && response_wait &&
         tx_starts == 0);
  assert(logged(nack ? "e=DATA_REJECT " : "e=ACCEPT "));
  clock_ms += ARQ_RESPONSE_GUARD_MS;
  clear_log();
  Poll();
  assert(tx_starts == 1 && raw_regs[1] == 0x83);
  const uint8_t expected_reply[] = {1,
                                    static_cast<uint8_t>(nack ? 3 : 2),
                                    arq::config::kReceiverId,
                                    arq::config::kSenderId,
                                    0x78,
                                    0x56,
                                    0x34,
                                    0x12,
                                    0,
                                    0,
                                    0,
                                    static_cast<uint8_t>(nack ? 2 : 0)};
  assert(sent_length == sizeof expected_reply);
  assert(!memcmp(sent, expected_reply, sizeof expected_reply));
  arq::Frame response;
  assert(arq::DecodeFrame(&response, sent, sent_length));
  assert(response.type == (nack ? arq::kNack : arq::kAck));
  assert(response.reason == (nack ? arq::kApplicationRejected : arq::kNone));
  assert(response.src == arq::config::kReceiverId &&
         response.dst == arq::config::kSenderId);
  assert(response.session == data.session &&
         response.sequence == data.sequence);
  irq_flags = 8;
  clear_log();
  Poll();
  assert(completed == 1 && raw_regs[1] == 0x85);
  assert(logged("e=TX_DONE ") && !arq::diagnostics::OverflowCount());
  irq_flags = 8;
  Poll();
  assert(completed == 1 && tx_starts == 1);  // stale TX IRQ
#endif
  clear_log();
  status_next = 4;
  FlushStatus();
  assert(logged(
#if defined(ARQ_ROLE_SENDER)
      "app=0 dup=0 gen=0 sup=0 att=1 done=0"
#else
      nack ? "app=0 dup=0 gen=1 sup=0 att=1 done=1"
           : "app=1 dup=0 gen=1 sup=0 att=1 done=1"
#endif
      ));
#if !defined(ARQ_ROLE_SENDER)
  clear_log();
  FlushStatus();
  assert(logged("e=RESULT s=12345678 q=0 a=0 rc=0 v=0"));
  clear_log();
  FlushStatus();
  assert(logged("e=RTT_LAST s=12345678 q=0 a=0 rc=0 v=0"));
#endif
  status_next = 0;
  cmd("X");
  Poll();
  assert(parked && raw_regs[1] == 0x81);
#if defined(LORA_ROLE_RECEIVER)
  assert(gpio_value[PIN_PA7] == LOW && gpio_value[PIN_PD5] == HIGH &&
         gpio_value[PIN_PD6] == HIGH);
#endif
}
