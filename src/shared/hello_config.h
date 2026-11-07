#pragma once
#include "../../include/generated/lora_shared_config.h"

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

#if !defined(HELLO_RF_FREQUENCY_MHZ) || !defined(HELLO_RF_TX_POWER_DBM) || \
    !defined(HELLO_RF_LONG_RANGE) || !defined(HELLO_RF_SPREADING_FACTOR) || \
    !defined(HELLO_RF_BANDWIDTH_KHZ) || !defined(HELLO_RF_CODING_RATE) || \
    !defined(HELLO_RF_SYNC_WORD) || !defined(HELLO_RF_PREAMBLE_SYMBOLS) || \
    !defined(HELLO_RF_CRC_ENABLED) || !defined(HELLO_RF_IQ_INVERTED)
#error "The shared Hello World RF profile must be supplied by PlatformIO."
#endif

static_assert(HELLO_RF_FREQUENCY_MHZ >= 920.0f &&
                  HELLO_RF_FREQUENCY_MHZ <= 925.0f,
              "Hello World bench frequency must be within 920-925 MHz.");
static_assert(HELLO_RF_TX_POWER_DBM >= 2 && HELLO_RF_TX_POWER_DBM <= 20,
              "Hello World TX power is outside the SX1276 range.");
static_assert(HELLO_RF_LONG_RANGE == 0 && HELLO_RF_SPREADING_FACTOR == 7,
              "Hello World diagnostics support SF7 only.");
static_assert(HELLO_RF_BANDWIDTH_KHZ == 125 && HELLO_RF_CODING_RATE == 5,
              "Hello World SF7 profile requires BW125 and coding rate 4/5.");
static_assert(HELLO_RF_SYNC_WORD == 0x12 && HELLO_RF_PREAMBLE_SYMBOLS == 8,
              "Hello World profile requires sync word 0x12 and preamble 8.");
static_assert(HELLO_RF_CRC_ENABLED == 1 && HELLO_RF_IQ_INVERTED == 0,
              "Hello World profile requires CRC on and normal IQ.");
