// Provides the legacy printf-style debug macros used by tracker tasks.
#ifndef IW_DEBUG_DEBUG_H_
#define IW_DEBUG_DEBUG_H_

#include <Arduino.h>

#include "printf.h"
#include "time-utils.h"

// P10-LOG-001: compile-time logging macros are the documented logging
// deviation; release builds erase the logging call sites.
#ifdef DEBUG
#define DEBUG_PRINT(x) Serial.print(x)
#define DEBUG_PRINTLN(x) Serial.println(x)
// P10-LOG-001
#define DEBUG_PRINTF(...) ::printf(Serial, __VA_ARGS__)

// this is hard-coded because Serial.flush() cannot be used as
// the RX pin is used for triggering maintenance mode
// P10-LOG-001
#define DEBUG_FLUSH() delay(10)

#else
// P10-LOG-001
#define DEBUG_PRINT(x)
// P10-LOG-001
#define DEBUG_PRINTLN(x)
// P10-LOG-001
#define DEBUG_PRINTF(...)
// P10-LOG-001
#define DEBUG_FLUSH()
#endif

// P10-LOG-001
#define DEBUG_TS(args...)                        \
  do {                                           \
    DEBUG_PRINTF("%s ", GetCurrentTimeString()); \
    DEBUG_PRINTF(args);                          \
  } while (0)

#endif  // IW_DEBUG_DEBUG_H_
