// Arduino entry point: delegate lifecycle work to the selected firmware app.

#include <Arduino.h>

#include "app/application.h"

#if !defined(LORA_APP_GATEWAY) && !defined(LORA_APP_LEGACY_SENDER)
void onPreMain() { firmware_app::PreMain(); }
#endif

void setup() { firmware_app::Initialize(); }

void loop() { firmware_app::Poll(); }
