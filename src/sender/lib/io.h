#pragma once
#include "../../../include/generated/lora_sender_board.h"
#include "../../../include/generated/radio_915_config.h"

#define PIN_LED1      PIN_PA5
#define PIN_LED2      PIN_PA4
// DxCore USART0 direction; the H1 TX/RX net labels are reversed.
#define PIN_DEBUG_RX  PIN_PA1
#define PIN_DEBUG_TX  PIN_PA0

#define PIN_INT       PIN_PD1
#define PIN_LORA_CS   LORA_PIN_CS
#define PIN_LORA_RST  LORA_PIN_RST
#define PIN_LORA_IRQ  LORA_PIN_IRQ
#define PIN_LORA_DIO1 LORA_PIN_DIO1

#define LED1_ON()   digitalWrite(PIN_LED1, LOW)
#define LED1_OFF()  digitalWrite(PIN_LED1, HIGH)
#define LED2_ON()   digitalWrite(PIN_LED2, LOW)
#define LED2_OFF()  digitalWrite(PIN_LED2, HIGH)

#define SHORT_BLINK(led_pin, on_duration, off_duration) \
    do { \
        digitalWriteFast(led_pin, LOW); \
        delay(on_duration); \
        digitalWriteFast(led_pin, HIGH); \
        delay(off_duration); \
    } while (0)


void init_gpio();
