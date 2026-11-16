// Offline execution of the actual SEND parser against existing fake SPI/radio.
#include <assert.h>

#include "../src/arq/diagnostics.cpp"
#include "../src/reverse_raw/main.cpp"
const arq_board board_ssot = {3, 4, 5, 6};
void board_ssot_init(void) {}
static void text(const char* s) {
  for (; *s; s++) FeedCommandByte(*s);
}
int main(int argc, char** argv) {
  assert(argc == 2);
  setup();
  assert(ready && !active && !tx_starts);
  if (!strcmp(argv[1], "wrong")) {
    text("SEND 4865\n");
    assert(!tx_starts && !active);
    return 0;
  }
  if (!strcmp(argv[1], "overflow")) {
    for (int i = 0; i < 64; i++) FeedCommandByte('A');
    FeedCommandByte('\n');
    assert(!tx_starts && !active && !input_overflow);
    return 0;
  }
  if (!strcmp(argv[1], "backpressure")) {
    monitor = false;
    registers[1] = 1;
    for (int i = 0; i < 16; i++) RecordEvent("FILL", 0);
  }
  text("SEND 48656C6C6F20576F726C64");
  assert(!tx_starts);
  text("\r\n");
  assert(tx_starts == 1 && active && sent_length == 11 &&
         !memcmp(sent, "Hello World", 11));
  text("SEND 48656C6C6F20576F726C64\n");
  assert(tx_starts == 1);
  // A disconnected logger must not prevent bounded radio cleanup.
  clock_ms += 3001;
  loop();
  assert(!active && cleanups == 1);
  if (!strcmp(argv[1], "backpressure"))
    assert(arq::diagnostics::OverflowCount() > 0);
}
