// Initializes the existing gateway GPIO and peripheral routes in board order.

#include "io.h"

#include <Arduino.h>

#include "avr128da28_device.h"

/************************************************************
 * Enable pull-up on all pins to lower power
 * taken from https://www.avrfreaks.net/comment/3209046#comment-3209046
 */
/************************************************************
 *
 */
void InitializeGpio() {
  (void)iw::avr128da28::ConfigureAllPinPullups();
  pinModeFast(GatewaySSOT::Pins::LED1, OUTPUT);
  pinModeFast(GatewaySSOT::Pins::LED2, OUTPUT);
  pinModeFast(PIN_LORA_CS, OUTPUT);
  pinModeFast(PIN_LORA_RST, OUTPUT);
  pinModeFast(PIN_LORA_IRQ, INPUT);
  pinModeFast(PIN_LORA_DIO1, INPUT);
  pinModeFast(PIN_INT, OUTPUT);
  digitalWriteFast(GatewaySSOT::Pins::LED1, HIGH);
  digitalWriteFast(GatewaySSOT::Pins::LED2, HIGH);
  digitalWriteFast(PIN_LORA_CS, HIGH);
  digitalWriteFast(PIN_LORA_RST, HIGH);
  digitalWriteFast(PIN_INT, LOW);

  // Use default I2C pinset. See:
  // https://github.com/SpenceKonde/DxCore/blob/master/megaavr/extras/DA28.md#twi0-mux-options
  (void)iw::avr128da28::ConfigureTwiRoute();
}
