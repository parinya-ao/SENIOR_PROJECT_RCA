#pragma once

#include <SD.h>

/**************************************************************************
 * Device's 8-bit address
 */
#ifndef DEFAULT_LORA_DEVICE_ADDRESS
#define DEFAULT_LORA_DEVICE_ADDRESS  0x01
#endif

/**************************************************************************
 * Gateway's 8-bit address
 */
#ifndef DEFAULT_LORA_GATEWAY_ADDRESS
#define DEFAULT_LORA_GATEWAY_ADDRESS   0x00
#endif

/**************************************************************************
 * Central frequency for LoRa module
 */
#ifndef DEFAULT_LORA_FREQ
#define DEFAULT_LORA_FREQ        450.0
#endif

/**************************************************************************
 * Transmission power in dBm
 */
#ifndef DEFAULT_LORA_TX_POWER
#define DEFAULT_LORA_TX_POWER    23
#endif

/**************************************************************************
 * Day-time data collection interval (in seconds)
 */
#ifndef DEFAULT_COLLECT_INTERVAL_DAY
#define DEFAULT_COLLECT_INTERVAL_DAY  600
#endif

/**************************************************************************
 * Night-time data collection interval (in seconds)
 */
#ifndef DEFAULT_COLLECT_INTERVAL_NIGHT
#define DEFAULT_COLLECT_INTERVAL_NIGHT  3600
#endif

/**************************************************************************
 * Hour (0-23) that marks the start of day
 */
#ifndef DEFAULT_DAY_START_HOUR
#define DEFAULT_DAY_START_HOUR  6
#endif

/**************************************************************************
 * Hour (0-23) that marks the end of day
 */
#ifndef DEFAULT_DAY_END_HOUR
#define DEFAULT_DAY_END_HOUR  18
#endif

/**************************************************************************
 * Time zone, measured in hours (+/-) from UTC
 */
#ifndef DEFAULT_TIME_ZONE
#define DEFAULT_TIME_ZONE  7
#endif

/**************************************************************************
 * Use ack from gateway to reliably upload data
 */
#ifndef DEFAULT_USE_ACK
#define DEFAULT_USE_ACK   0
#endif

/**************************************************************************
 * Time waiting for gateway before next retransmission attempt (in seconds)
 * (for ack method only)
 */
#ifndef DEFAULT_ACK_TIMEOUT
#define DEFAULT_ACK_TIMEOUT       5
#endif

/**************************************************************************
 * Long-range mode enable flag
 * 0 - high-speed, short-range
 * 1 - low-speed, long-range
 */
#ifndef DEFAULT_LONG_RANGE
#define DEFAULT_LONG_RANGE        1
#endif

/**************************************************************************
 * Number of duplicate transmissions per report
 * (for low-power method only)
 */
#ifndef DEFAULT_TX_REPEAT
#define DEFAULT_TX_REPEAT         3
#endif

/**************************************************************************
 * Amount of time to wait for GPS to acquire fix before giving up
 * (in seconds)
 */
#ifndef DEFAULT_GPS_MAX_WAIT_FOR_FIX
#define DEFAULT_GPS_MAX_WAIT_FOR_FIX  120
#endif

/**************************************************************************
 * Amount of time to wait before the next attempt after no fix was acquired
 * (in seconds)
 */
#ifndef DEFAULT_NEXT_COLLECT_NO_FIX
#define DEFAULT_NEXT_COLLECT_NO_FIX  120  // seconds
#endif

/**************************************************************************
 * Amount of time to try waiting for NMEA from the GPS module after fix has
 * been acquired (in seconds)
 */
#ifndef DEFAULT_GPS_NMEA_TIMEOUT
#define DEFAULT_GPS_NMEA_TIMEOUT  5  // seconds
#endif

/**************************************************************************
 * Number of slots
 * (for low-power method only)
 */
#ifndef DEFAULT_TOTAL_SLOTS
#define DEFAULT_TOTAL_SLOTS  40
#endif

/**************************************************************************
 * Slot interval in seconds
 * (for low-power method only)
 */
#ifndef DEFAULT_SLOT_INTERVAL
#define DEFAULT_SLOT_INTERVAL  10
#endif

/**************************************************************************
 * Name of the configuration file on the configuration partition
 */
#ifndef CONFIG_FILE_NAME
#define CONFIG_FILE_NAME   "CONFIG.TXT"
#endif

struct Config {
    uint8_t  lora_device_address;
    uint8_t  lora_gateway_address;
    float    lora_freq;
    uint8_t  lora_tx_power;
    uint16_t collect_interval_day;
    uint16_t collect_interval_night;
    uint8_t  day_start_hour;
    uint8_t  day_end_hour;
    int8_t   time_zone;
    uint8_t  use_ack;
    uint16_t ack_timeout;
    uint8_t  long_range;
    uint8_t  tx_repeat;
    uint16_t gps_max_wait_for_fix;
    uint16_t next_collect_no_fix;
    uint16_t total_slots;
    uint16_t slot_interval;

    Config() {
        lora_device_address    = DEFAULT_LORA_DEVICE_ADDRESS;
        lora_gateway_address   = DEFAULT_LORA_GATEWAY_ADDRESS;
        lora_freq              = DEFAULT_LORA_FREQ;
        lora_tx_power          = DEFAULT_LORA_TX_POWER;
        collect_interval_day   = DEFAULT_COLLECT_INTERVAL_DAY;
        collect_interval_night = DEFAULT_COLLECT_INTERVAL_NIGHT;
        day_start_hour         = DEFAULT_DAY_START_HOUR;
        day_end_hour           = DEFAULT_DAY_END_HOUR;
        time_zone              = DEFAULT_TIME_ZONE;
        use_ack                = DEFAULT_USE_ACK;
        ack_timeout            = DEFAULT_ACK_TIMEOUT;
        long_range             = DEFAULT_LONG_RANGE;
        tx_repeat              = DEFAULT_TX_REPEAT;
        gps_max_wait_for_fix   = DEFAULT_GPS_MAX_WAIT_FOR_FIX;
        next_collect_no_fix    = DEFAULT_NEXT_COLLECT_NO_FIX;
        total_slots            = DEFAULT_TOTAL_SLOTS;
        slot_interval          = DEFAULT_SLOT_INTERVAL;
    }
} __attribute__((packed));
