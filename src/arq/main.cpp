// No repository-wide license is declared; existing rights are unchanged.

// Arduino entry points for all ARQ bench variants. See application.cpp for
// flow.

#include <Arduino.h>

#include "application.h"
// Preserve vector routing before Arduino startup; no radio access occurs here.
void onPreMain() { _PROTECTED_WRITE(CPUINT.CTRLA, 0); }
// Initialize board power, SPI and radio before foreground processing.
void setup() { arq::app::Initialize(); }
// Process bounded radio work and diagnostics; failures remain visible in
// status.
void loop() { arq::app::Poll(); }
