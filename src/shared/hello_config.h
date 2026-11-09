#pragma once
#include "../../include/generated/lora_shared_config.h"
#include "../../include/generated/radio_915_config.h"

#ifndef HELLO_TEST_MODE
#define HELLO_TEST_MODE 0
#endif

#ifndef HELLO_RAM_ONLY_TEST
#define HELLO_RAM_ONLY_TEST 0
#endif

#if HELLO_RAM_ONLY_TEST && !HELLO_TEST_MODE
#error "RAM-only one-shot mode is restricted to the Hello test firmware."
#endif

#ifndef HELLO_RF_DIAGNOSTIC_ONLY
#define HELLO_RF_DIAGNOSTIC_ONLY 0
#endif

static_assert(HELLO_RF_FREQUENCY_MHZ == 915.0f &&
                  HELLO_RF_TX_POWER_DBM == 10 && HELLO_RF_LONG_RANGE == 0 &&
                  HELLO_RF_SPREADING_FACTOR == 7 && HELLO_RF_BANDWIDTH_KHZ == 125 &&
                  HELLO_RF_CODING_RATE == 5 && HELLO_RF_SYNC_WORD == 0x12 &&
                  HELLO_RF_PREAMBLE_SYMBOLS == 8 && HELLO_RF_CRC_ENABLED == 1 &&
                  HELLO_RF_EXPLICIT_HEADER == 1 && HELLO_RF_IQ_INVERTED == 0 &&
                  HELLO_RF_CURRENT_LIMIT_MA == 200 && HELLO_RF_AUTOMATIC_GAIN == 0,
              "The generated radio profile must match the validated 915 MHz SSOT.");
