#include <assert.h>

#include "../stable_lib/arq/src/arq/diagnostics.cpp"
#include "../stable_lib/reverse_raw_app/reverse_raw_app.cpp"
#include "arq/diagnostics_test_access.h"
const arq_board board_ssot = {3, 4, 5, 6};
void board_ssot_init(void) {}
static void cmd(const char* s) {
  for (; *s; s++) FeedCommandByte(*s);
  FeedCommandByte('\n');
}
static const char* logged(const char* name) {
  for (unsigned i = 0; i < arq::diagnostics::PendingLineCount(); i++)
    if (strstr(QueuedLogLine(i), name)) return QueuedLogLine(i);
  return "";
}
int main(int argc, char** argv) {
  reverse_raw_app::Initialize();
  assert(ready && !active && !tx_starts);
  assert(last_begin_frequency_mhz == 915.0f);
  assert((raw_regs[RADIOLIB_SX127X_REG_OP_MODE] & 0x08) == 0);
  if (argc > 1) {
#if defined(LORA_ROLE_SENDER)
    if (!strcmp(argv[1], "diagnostics")) {
      cmd("RX");
      assert(strstr(logged("RAW_RX_READY"), "mode=133"));
      raw_regs[0x14] = 0x12;
      raw_regs[0x15] = 0x34;
      raw_regs[0x16] = 0;
      raw_regs[0x17] = 1;
      raw_regs[0x18] = 0x10;
      raw_regs[0x1c] = 0x40;
      memcpy(packet, "Hello World", 11);
      packet_length = 11;
      irq_flags = 0x50;
      cmd("RX");
      assert(rx_starts == 1 && irq_flags == 0x50);
      clock_ms += 15001;
      reverse_raw_app::Poll();
      assert(matches == 1 && !active && !irq_flags);
      assert(strstr(logged("RAW_RX_DONE"), "flags=80 headers=4660 packets=1"));
      assert(!*logged("RAW_RX_TIMEOUT"));
      assert(!arq::diagnostics::OverflowCount());
      return 0;
    }
    if (!strcmp(argv[1], "rx-error")) {
      rx_status = -1;
      cmd("RX");
      assert(!active);
      return 0;
    }
    cmd("RX");
    if (!strcmp(argv[1], "timeout")) {
      clock_ms += 15001;
      reverse_raw_app::Poll();
      assert(!active && !matches);
      assert(strstr(logged("RAW_RX_TIMEOUT"), "headers=0 packets=0"));
      return 0;
    }
    if (!strcmp(argv[1], "bad-length")) {
      packet_length = 255;
      irq_flags = 0x40;
      reverse_raw_app::Poll();
      assert(active && !matches);
      cmd("X");
      return 0;
    }
#else
    if (!strcmp(argv[1], "tx-error")) {
      tx_status = -1;
      cmd("SEND 48656C6C6F20576F726C64");
      assert(!active && cleanups == 1);
      cmd("SEND 48656C6C6F20576F726C64");
      assert(tx_starts == 1);
      return 0;
    }
    cmd("SEND 48656C6C6F20576F726C64");
    irq_flags = 8;
    reverse_raw_app::Poll();
    assert(!active && cleanups == 1);
    return 0;
#endif
  }
  cmd("SEND 00");
  assert(!tx_starts);
#if defined(LORA_ROLE_RECEIVER)
  cmd("SEND 48656C6C6F20576F726C64");
  assert(tx_starts == 1 && sent_length == 11);
  assert(!memcmp(sent, "Hello World", 11));
  cmd("SEND 48656C6C6F20576F726C64");
  assert(tx_starts == 1);
  clock_ms += 3001;
  reverse_raw_app::Poll();
  assert(!active && cleanups == 1);
  cmd("SEND 48656C6C6F20576F726C64");
  assert(tx_starts == 1);
#else
  cmd("RX");
  assert(active && rx_starts == 1);
  memcpy(packet, "Hello World", 11);
  packet_length = 11;
  irq_flags = 0x60;
  reverse_raw_app::Poll();
  assert(!matches && active);
  packet_length = 11;
  irq_flags = 0x40;
  reverse_raw_app::Poll();
  assert(matches == 1 && !active);
  cmd("RX");
  assert(!active);  // a run has exactly one bounded observation
#endif
  cmd("X");
  assert(!active);
}
