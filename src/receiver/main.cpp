#include <Arduino.h>
#include "updi_uart.h"

void setup() {}

void loop() {
  if (!updi_uart_enabled()) {
    delay(10);
    return;
  }

  const char* msg = "HEYYY fuckkkk\r\n";

  while (*msg) {
    updi_uart_tx(*msg++);
  }

  delay(2000);
}
