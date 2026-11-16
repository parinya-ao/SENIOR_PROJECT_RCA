#pragma once

#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC) && defined(LORA_ROLE_RECEIVER)
static bool radio_only_prepare_tracker() {
    // Startup only: ARQ has no GPS/SD/sensor tasks to stop. Never call this between DATA and ACK.
    // SAM-M10Q main power is active-low PD5; release USART2/PF0-PF1 before removing it.
    USART2.CTRLA=0;
    USART2.CTRLB=0;
    pinMode(PIN_PF0,INPUT);digitalWrite(PIN_PF0,LOW);
    pinMode(PIN_PF1,INPUT);digitalWrite(PIN_PF1,LOW);
    pinMode(PIN_PD4,INPUT);digitalWrite(PIN_PD4,LOW); // GPS TIMEPULSE: no pull-up into unpowered IO.
    digitalWrite(PIN_PD5,HIGH);pinMode(PIN_PD5,OUTPUT);
    // GNSS V_BCKP stays connected. IMU/EEPROM remain on main 3V3, with no application traffic.
    pinMode(PIN_PA5,INPUT);digitalWrite(PIN_PA5,LOW);
    pinMode(PIN_PA6,INPUT);digitalWrite(PIN_PA6,LOW); // Do not use LED_BUILTIN: it aliases EN-LORA/PA7.
    // SD shares LoRa SPI without isolation. With power off, a fitted card forbids any SPI drive.
    pinMode(PIN_PC3,INPUT);digitalWrite(PIN_PC3,LOW);
    digitalWrite(PIN_PD6,HIGH);pinMode(PIN_PD6,OUTPUT);
    pinMode(PIN_PA4,INPUT_PULLUP); // CARD1 detect switch closes to ground when a card is fitted.
    digitalWrite(PIN_PA7,HIGH);pinMode(PIN_PA7,OUTPUT);
    return digitalRead(PIN_PA4)==HIGH;
}
#endif
