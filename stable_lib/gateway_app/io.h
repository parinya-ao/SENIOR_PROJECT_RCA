// Defines the existing gateway control signals; radio pins come from board
// SSOT.

#ifndef SENIOR_PROJECT_RCA_SRC_SENDER_LIB_IO_H_
#define SENIOR_PROJECT_RCA_SRC_SENDER_LIB_IO_H_
#include <generated/lora_sender_board.h>
#include <generated/radio_915_config.h>

#include <gateway_ssot.hpp>

// DxCore USART0 direction; the H1 TX/RX net labels are reversed.
#define PIN_DEBUG_RX GatewaySSOT::Pins::DEBUG_RX
#define PIN_DEBUG_TX GatewaySSOT::Pins::DEBUG_TX

#define PIN_INT GatewaySSOT::Pins::HOST_INT
#define PIN_LORA_CS GatewaySSOT::Pins::LORA_CS
#define PIN_LORA_RST GatewaySSOT::Pins::LORA_RST
#define PIN_LORA_IRQ GatewaySSOT::Pins::LORA_IRQ
#define PIN_LORA_DIO1 GatewaySSOT::Pins::LORA_DIO1

#define LED1_ON() digitalWrite(GatewaySSOT::Pins::LED1, LOW)
#define LED1_OFF() digitalWrite(GatewaySSOT::Pins::LED1, HIGH)
#define LED2_ON() digitalWrite(GatewaySSOT::Pins::LED2, LOW)
#define LED2_OFF() digitalWrite(GatewaySSOT::Pins::LED2, HIGH)

#define SHORT_BLINK(led_pin, on_duration, off_duration) \
  do {                                                  \
    digitalWriteFast(led_pin, LOW);                     \
    delay(on_duration);                                 \
    digitalWriteFast(led_pin, HIGH);                    \
    delay(off_duration);                                \
  } while (0)

/// @brief Configures gateway GPIO levels, pull-ups, and the existing TWI route.
/// @pre The selected board pin configuration has been generated.
/// @post Call before communication tasks or radio initialization.
void InitializeGpio();

#endif  // SENIOR_PROJECT_RCA_SRC_SENDER_LIB_IO_H_
