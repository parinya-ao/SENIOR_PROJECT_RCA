// No repository-wide license is declared; existing rights are unchanged.

// Isolates tracker peripherals only during radio-only diagnostic startup.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_RADIO_ONLY_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_RADIO_ONLY_H_

#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC) && defined(LORA_ROLE_RECEIVER)
#include <Arduino.h>

#include "generated/lora_receiver_board.h"
#include "generated/radio_915_config.h"
// Disables GNSS/SD drive before board init; refuses SPI use with a fitted SD
// card. Never call between DATA and ACK. Returns true only when the shared bus
// is safe.
static bool PrepareTrackerForRadioOnly() {
  // Startup only: ARQ has no GPS/SD/sensor tasks to stop. Never call this
  // between DATA and ACK. SAM-M10Q main power is active-low PD5; release
  // USART2/PF0-PF1 before removing it.
  USART2.CTRLA = 0;
  USART2.CTRLB = 0;
  pinMode(PIN_PF0, INPUT);
  digitalWrite(PIN_PF0, LOW);
  pinMode(PIN_PF1, INPUT);
  digitalWrite(PIN_PF1, LOW);
  pinMode(PIN_PD4, INPUT);
  digitalWrite(PIN_PD4, LOW);  // GPS TIMEPULSE: no pull-up into unpowered IO.
  digitalWrite(LORA_PIN_GPS_ENABLE, HIGH);
  pinMode(LORA_PIN_GPS_ENABLE, OUTPUT);
  // GNSS V_BCKP stays connected. IMU/EEPROM remain on main 3V3, with no
  // application traffic.
  pinMode(LORA_PIN_LED2, INPUT);
  digitalWrite(LORA_PIN_LED2, LOW);
  pinMode(LORA_PIN_LED1, INPUT);
  digitalWrite(LORA_PIN_LED1,
               LOW);  // Do not use LED_BUILTIN: it aliases EN-LORA/PA7.
  // SD shares LoRa SPI without isolation. With power off, a fitted card forbids
  // any SPI drive.
  pinMode(LORA_PIN_SD_CS, INPUT);
  digitalWrite(LORA_PIN_SD_CS, LOW);
  digitalWrite(LORA_PIN_SD_ENABLE, HIGH);
  pinMode(LORA_PIN_SD_ENABLE, OUTPUT);
  pinMode(LORA_PIN_SD_DETECT, INPUT_PULLUP);  // CARD1 detect switch closes to
                                              // ground when a card is fitted.
  digitalWrite(LORA_PIN_ENABLE, HIGH);
  pinMode(LORA_PIN_ENABLE, OUTPUT);
  return digitalRead(LORA_PIN_SD_DETECT) == HIGH;
}
#endif

#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_RADIO_ONLY_H_
