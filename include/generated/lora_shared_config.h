#pragma once
// Generated from config/lora_system.json.
#ifdef HELLO_RF_FREQUENCY_MHZ
static_assert(HELLO_RF_FREQUENCY_MHZ == 923.0f, "Conflicting FREQUENCY_MHZ; use SSOT");
#else
#define HELLO_RF_FREQUENCY_MHZ 923.0f
#endif
#ifdef HELLO_RF_TX_POWER_DBM
static_assert(HELLO_RF_TX_POWER_DBM == 10, "Conflicting TX_POWER_DBM; use SSOT");
#else
#define HELLO_RF_TX_POWER_DBM 10
#endif
#ifdef HELLO_RF_SPREADING_FACTOR
static_assert(HELLO_RF_SPREADING_FACTOR == 7, "Conflicting SPREADING_FACTOR; use SSOT");
#else
#define HELLO_RF_SPREADING_FACTOR 7
#endif
#ifdef HELLO_RF_BANDWIDTH_KHZ
static_assert(HELLO_RF_BANDWIDTH_KHZ == 125, "Conflicting BANDWIDTH_KHZ; use SSOT");
#else
#define HELLO_RF_BANDWIDTH_KHZ 125
#endif
#ifdef HELLO_RF_CODING_RATE
static_assert(HELLO_RF_CODING_RATE == 5, "Conflicting CODING_RATE; use SSOT");
#else
#define HELLO_RF_CODING_RATE 5
#endif
#ifdef HELLO_RF_SYNC_WORD
static_assert(HELLO_RF_SYNC_WORD == 18, "Conflicting SYNC_WORD; use SSOT");
#else
#define HELLO_RF_SYNC_WORD 18
#endif
#ifdef HELLO_RF_PREAMBLE_SYMBOLS
static_assert(HELLO_RF_PREAMBLE_SYMBOLS == 8, "Conflicting PREAMBLE_SYMBOLS; use SSOT");
#else
#define HELLO_RF_PREAMBLE_SYMBOLS 8
#endif
#ifdef HELLO_RF_CRC_ENABLED
static_assert(HELLO_RF_CRC_ENABLED == 1, "Conflicting CRC_ENABLED; use SSOT");
#else
#define HELLO_RF_CRC_ENABLED 1
#endif
#ifdef HELLO_RF_IQ_INVERTED
static_assert(HELLO_RF_IQ_INVERTED == 0, "Conflicting IQ_INVERTED; use SSOT");
#else
#define HELLO_RF_IQ_INVERTED 0
#endif
#define HELLO_RF_LONG_RANGE 0
#define LORA_CONFIG_FINGERPRINT "58543a4bdbe53f64c4b1871503c698556d4c9507967d171fb46ba10cf6feb232"
#define LORA_PROTOCOL_VERSION 2
#define LORA_PROTOCOL_VERSION_TEXT "2"
#define LORA_MAX_RETRIES 3
#define LORA_HELLO_PAYLOAD "hello world"
#define LORA_ACK_TIMEOUT_MS 3000
#define LORA_TX_TIMEOUT_MS 3000
#define LORA_SENDER_ADDRESS 0
#define LORA_RECEIVER_ADDRESS 1
#define LORA_SEQUENCE 1
#define LORA_DATA_TYPE 8
#define LORA_ACK_TYPE 3
#define LORA_NACK_TYPE 9
