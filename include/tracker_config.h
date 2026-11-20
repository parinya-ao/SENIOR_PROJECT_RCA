// Defines Tracker pin, timing, and conversion constants. LoRa PHY data comes
// from the generated radio profile.
#ifndef SENIOR_PROJECT_RCA_INCLUDE_TRACKER_CONFIG_H_
#define SENIOR_PROJECT_RCA_INCLUDE_TRACKER_CONFIG_H_

#include <stddef.h>
#include <stdint.h>

#include "generated/radio_915_config.h"

namespace tracker_cfg {

// Fixed firmware, hardware, timing, and conversion constants.
struct SystemConstants {
  static constexpr uint8_t DEVICE_MODEL = 0x03;
  static constexpr uint16_t EEPROM_ADDR_OP_MODE = 0x10;
  static constexpr uint16_t SD_SECTOR_SIZE_BYTES = 512;

  static constexpr size_t REPORT_RINGBUF_BYTES = 1024;
  static constexpr size_t LOG_RINGBUF_BYTES = 4096;

  static constexpr uint8_t USE_SPI_TRACKER = 0x01;
  static constexpr uint8_t USE_SPI_UPLOADER = 0x02;
  static constexpr uint8_t USE_SPI_MAINTENANCE = 0x04;

  static constexpr uint8_t LORA_BROADCAST_ADDR = 0xFF;
  static constexpr uint8_t MAINT_AIR_CONFIG_ADDR = 0xFE;
  static constexpr int16_t MAINT_LORA_TX_POWER_DBM = 2;
  static constexpr uint8_t MAINT_LORA_LONG_RANGE = 0;
  static constexpr uint8_t MAINT_BTN_TRIGGER_SEC = 3;
  static constexpr uint32_t LORA_SEND_DONE_TIMEOUT_MS = 5000;
  static constexpr uint8_t MAX_ACK_TIMEOUT_COUNT =
      3;  // Reserved; not used here.

  static constexpr uint32_t TX_EST_NON_ACK_LR_MS = 2500;
  static constexpr uint32_t TX_EST_NON_ACK_STD_MS = 200;
  static constexpr uint32_t TX_EST_ACK_LR_MS = 5000;
  static constexpr uint32_t TX_EST_ACK_STD_MS = 500;

  static constexpr uint32_t GNSS_SERIAL_BAUD = 9600;
  static constexpr uint32_t DEBUG_SERIAL_BAUD = 115200;
  static constexpr int32_t MIN_NEXT_COLLECT_GUARD_S = 3;
  static constexpr int32_t GNSS_SCALE_FACTOR = 10000000L;
  static constexpr int32_t BOOT_SENTINEL_COORD = 0x7FFFFFFFL;
  static constexpr uint16_t BOOT_SENTINEL_VBAT_MV = 65535;

  static constexpr uint32_t BOOT_DELAY_MS = 2000;
  static constexpr uint32_t SPI_POWER_ON_SETTLE_MS = 10;
  static constexpr uint32_t SD_INIT_SETTLE_MS = 50;
  static constexpr uint32_t SD_TASK_INIT_SETTLE_MS = 150;
  static constexpr uint32_t SD_FLUSH_BEFORE_OFF_MS = 50;
  static constexpr uint32_t GNSS_POWER_ON_SETTLE_MS = 50;
  static constexpr uint32_t ERROR_BLINK_TOTAL_MS = 10000;
  static constexpr uint32_t ERROR_BLINK_INTERVAL_MS = 200;
  static constexpr uint32_t LED1_TOGGLE_INTERVAL_MS = 1000;
  static constexpr uint32_t LORA_TX_LED_TOGGLE_INTERVAL_MS = 100;
  static constexpr uint8_t LED_ON_LEVEL = 0;
  static constexpr uint8_t LED_OFF_LEVEL = 1;

  // Battery millivolts = (raw * VBAT_SCALE_NUMERATOR + VBAT_ROUNDING_OFFSET)
  //                      / ADC_RESOLUTION_STEPS.
  static constexpr uint32_t ADC_VREF_MV = 2048;
  static constexpr uint32_t ADC_RESOLUTION_STEPS = 4096;
  static constexpr uint32_t VBAT_R_TOP_KOHM = 100;
  static constexpr uint32_t VBAT_R_BOTTOM_KOHM = 10;
  static constexpr uint32_t VBAT_DIVIDER_RATIO =
      (VBAT_R_TOP_KOHM + VBAT_R_BOTTOM_KOHM) / VBAT_R_BOTTOM_KOHM;
  static constexpr uint32_t VBAT_SCALE_NUMERATOR =
      ADC_VREF_MV * VBAT_DIVIDER_RATIO;
  static constexpr uint32_t VBAT_ROUNDING_OFFSET = ADC_RESOLUTION_STEPS / 2;
};

// Numeric values are persisted in diagnostic state; keep them stable.
enum class ErrorCode : uint8_t {
  SD_INIT_FAILED = 1,            // SD card initialization failed.
  LOG_PARTITION_NOT_FOUND = 2,   // The log partition was not found.
  LOGGER_SETUP_FAILED = 3,       // Logger setup failed.
  CONFIG_PART_NOT_FOUND = 4,     // The FAT16 config partition was not found.
  CONFIG_VOL_INIT_FAILED = 5,    // The FAT16 volume could not be opened.
  CONFIG_FILE_READ_FAILED = 6,   // The config file could not be read.
  DATA_PARTITION_NOT_FOUND = 7,  // The data partition was not found.
  STORAGE_SETUP_FAILED = 8,      // Storage setup failed.
  LORA_INIT_FAILED = 9           // LoRa initialization failed.
};

// Checkpoints identify the last marked step before a reset.
enum class Checkpoint : uint8_t {
  INVALID_GNSS_DATE = 1,        // GNSS date was invalid.
  SPI_CTRL_BEFORE_PWR_ON = 20,  // Before enabling the SPI power rail.
  SPI_CTRL_BEFORE_LORA = 21,    // Before initializing LoRa.
  TRACKER_BEFORE_GNSS_ON = 30,  // Before enabling GNSS power.
  TRACKER_AFTER_GNSS_ON = 31    // After GNSS power-on settling.
};

// The 17 runtime settings represented by the SD-card configuration format.
struct TrackerConfig {
  uint8_t lora_device_address;   // Node address; 0xFE and 0xFF are reserved.
  uint8_t lora_gateway_address;  // Gateway address; 0xFF accepts any gateway.
  float lora_freq;               // Radio frequency in MHz.
  int16_t lora_tx_power;         // Normal-mode transmit power in dBm.
  uint8_t long_range;            // 0 = standard mode, 1 = long-range mode.

  uint16_t collect_interval_day;    // Daytime collection interval in seconds.
  uint16_t collect_interval_night;  // Nighttime collection interval in seconds.
  uint8_t day_start_hour;  // Local hour when the daytime schedule starts.
  uint8_t day_end_hour;    // Local hour when the daytime schedule ends.
  int8_t time_zone;        // Local UTC offset in whole hours.

  uint16_t gps_max_wait_for_fix;  // Maximum GNSS fix wait in seconds.
  uint16_t
      next_collect_no_fix;  // Retry delay after a failed GNSS fix, in seconds.

  uint8_t use_ack;       // 0 = send without ACK; 1 = wait for an ACK.
  uint16_t ack_timeout;  // Maximum ACK wait in seconds.
  uint8_t tx_repeat;     // Repeats per record when ACK mode is disabled.

  uint16_t total_slots;    // Number of TDMA slots in one frame.
  uint16_t slot_interval;  // Duration of each TDMA slot in seconds.

  constexpr uint16_t my_tdma_slot() const {
    return total_slots > 0 ? lora_device_address % total_slots : 0;
  }

  constexpr uint32_t tdma_frame_period_sec() const {
    return static_cast<uint32_t>(total_slots) * slot_interval;
  }

  constexpr uint32_t estimated_tx_time_ms() const {
    if (use_ack != 0) {
      return long_range != 0 ? SystemConstants::TX_EST_ACK_LR_MS
                             : SystemConstants::TX_EST_ACK_STD_MS;
    }
    const uint32_t per_packet = long_range != 0
                                    ? SystemConstants::TX_EST_NON_ACK_LR_MS
                                    : SystemConstants::TX_EST_NON_ACK_STD_MS;
    return static_cast<uint32_t>(tx_repeat) * per_packet;
  }

  constexpr bool is_valid() const {
    return lora_device_address != SystemConstants::MAINT_AIR_CONFIG_ADDR &&
           lora_device_address != SystemConstants::LORA_BROADCAST_ADDR &&
           (lora_gateway_address == SystemConstants::LORA_BROADCAST_ADDR ||
            lora_gateway_address != SystemConstants::MAINT_AIR_CONFIG_ADDR) &&
           lora_freq == HELLO_RF_FREQUENCY_MHZ && long_range <= 1 &&
           collect_interval_day > 0 && collect_interval_night > 0 &&
           day_start_hour < 24 && day_end_hour <= 24 &&
           day_start_hour < day_end_hour && time_zone >= -12 &&
           time_zone <= 14 && use_ack <= 1 && total_slots > 0 &&
           slot_interval > 0 &&
           (use_ack != 0 ? ack_timeout > 0 : tx_repeat > 0);
  }
};

static_assert(__is_trivially_copyable(TrackerConfig),
              "TrackerConfig must remain safe for byte-wise copying.");

// Default Thailand profile: 15-minute daytime, hourly nighttime, ACK enabled.
constexpr TrackerConfig DEFAULT_THAILAND_CONFIG = {
    0x01,                    // lora_device_address
    0x00,                    // lora_gateway_address
    HELLO_RF_FREQUENCY_MHZ,  // lora_freq
    17,                      // lora_tx_power
    1,                       // long_range
    900,                     // collect_interval_day
    3600,                    // collect_interval_night
    6,                       // day_start_hour
    18,                      // day_end_hour
    7,                       // time_zone
    60,                      // gps_max_wait_for_fix
    300,                     // next_collect_no_fix
    1,                       // use_ack
    5,                       // ack_timeout
    1,                       // tx_repeat
    10,                      // total_slots
    6};                      // slot_interval

// Faster beacon profile: one-minute daytime, five-minute nighttime, no ACK.
constexpr TrackerConfig FAST_BEACON_NO_ACK_CONFIG = {
    0x02,                    // lora_device_address
    0xFF,                    // lora_gateway_address
    HELLO_RF_FREQUENCY_MHZ,  // lora_freq
    14,                      // lora_tx_power
    0,                       // long_range
    60,                      // collect_interval_day
    300,                     // collect_interval_night
    6,                       // day_start_hour
    19,                      // day_end_hour
    7,                       // time_zone
    30,                      // gps_max_wait_for_fix
    60,                      // next_collect_no_fix
    0,                       // use_ack
    0,                       // ack_timeout
    3,                       // tx_repeat
    20,                      // total_slots
    2};                      // slot_interval

static_assert(DEFAULT_THAILAND_CONFIG.is_valid(),
              "DEFAULT_THAILAND_CONFIG is invalid.");
static_assert(FAST_BEACON_NO_ACK_CONFIG.is_valid(),
              "FAST_BEACON_NO_ACK_CONFIG is invalid.");
static_assert(DEFAULT_THAILAND_CONFIG.estimated_tx_time_ms() <=
                  static_cast<uint32_t>(DEFAULT_THAILAND_CONFIG.slot_interval) *
                      1000UL,
              "Default ACK estimate exceeds its TDMA slot.");
static_assert(
    FAST_BEACON_NO_ACK_CONFIG.estimated_tx_time_ms() <=
        static_cast<uint32_t>(FAST_BEACON_NO_ACK_CONFIG.slot_interval) * 1000UL,
    "Default beacon estimate exceeds its TDMA slot.");

}  // namespace tracker_cfg

#endif  // SENIOR_PROJECT_RCA_INCLUDE_TRACKER_CONFIG_H_
