#include <Arduino.h>
#include <util/delay.h>

#include "updi_uart.h"

#define PIN_LED1 PIN_PA6
#define PIN_LED2 PIN_PA5
#define PIN_MAINTENANCE PIN_PA1
#define PIN_SD_EN PIN_PD6

#define PIN_LORA_EN PIN_PA7
#define PIN_LORA_CS PIN_PD0
#define PIN_LORA_RST PIN_PD1
#define PIN_LORA_DIO1 PIN_PD2
#define PIN_LORA_IRQ PIN_PD3

#define LED1_ON() digitalWriteFast(PIN_LED1, LOW)
#define LED1_OFF() digitalWriteFast(PIN_LED1, HIGH)

#define LED2_ON() digitalWriteFast(PIN_LED2, LOW)
#define LED2_OFF() digitalWriteFast(PIN_LED2, HIGH)

static void updi_print(const char* message) {
  if (!updi_uart_enabled()) {
    return;
  }

  for (const char* p = message; *p != '\0'; ++p) {
    updi_uart_tx(*p);
  }
}

int main() {
  pinModeFast(PIN_LED2, OUTPUT);
  LED2_OFF();

  while (true) {
    LED2_ON();
    _delay_ms(100);

    LED2_OFF();
    _delay_ms(100);

    updi_print("HEYYY fuckkkk\r\n");
  }
}
