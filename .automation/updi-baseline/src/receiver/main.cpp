#include <Arduino.h>

#include "updi_uart.h"

namespace {

void UpdiWrite(const char* text) {
  while (*text != '\0') {
    updi_uart_tx(static_cast<uint8_t>(*text));
    ++text;
  }
}

}  // namespace

void setup() {}

void loop() {
  if (!updi_uart_enabled()) {
    delay(10);
    return;
  }

  UpdiWrite("HELLO WORLD\r\n");
  delay(1000);
}
