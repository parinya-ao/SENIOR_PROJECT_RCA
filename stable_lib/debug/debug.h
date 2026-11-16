#pragma once

#include <Arduino.h>
#include "printf.h"
#include "time-utils.h"

#ifdef DEBUG
#define DEBUG_PRINT(x)    Serial.print(x)
#define DEBUG_PRINTLN(x)  Serial.println(x)
#define DEBUG_PRINTF(...) ::printf(Serial,__VA_ARGS__)

// this is hard-coded because Serial.flush() cannot be used as
// the RX pin is used for triggering maintenance mode
#define DEBUG_FLUSH()     delay(10)

#else
#define DEBUG_PRINT(x)
#define DEBUG_PRINTLN(x)
#define DEBUG_PRINTF(...)
#define DEBUG_FLUSH()
#endif

#define DEBUG_TS(args...)  \
    do { \
        DEBUG_PRINTF("%s ", get_current_time_str()); \
        DEBUG_PRINTF(args); \
    } while (0)
