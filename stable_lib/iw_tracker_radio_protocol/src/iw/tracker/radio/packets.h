// Defines the legacy tracker radio packet schema and its frozen wire sizes.
#ifndef IW_TRACKER_RADIO_PACKETS_H_
#define IW_TRACKER_RADIO_PACKETS_H_

#include <stdint.h>

namespace iw::tracker::radio {

// These legacy names are part of the existing tracker protocol vocabulary;
// their numeric values and packed field order are frozen for compatibility.
inline constexpr uint8_t PKT_TYPE_ADVERTISE = 0x01U;
inline constexpr uint8_t PKT_TYPE_REPORT = 0x02U;
inline constexpr uint8_t PKT_TYPE_ACK = 0x03U;
inline constexpr uint8_t PKT_TYPE_BOOT = 0x04U;
inline constexpr uint8_t PKT_TYPE_REPORT_WITH_ACK = 0x05U;
inline constexpr uint8_t PKT_TYPE_MAINTENANCE = 0x06U;
inline constexpr uint8_t PKT_TYPE_MAINTENANCE_ACK = 0x07U;

inline constexpr uint8_t PKT_MAINT_CMD_NOP = 0x00U;
inline constexpr uint8_t PKT_MAINT_CMD_REBOOT = 0x01U;
inline constexpr uint8_t PKT_MAINT_CMD_OP_MODE_QUERY = 0x02U;
inline constexpr uint8_t PKT_MAINT_CMD_OP_MODE_SLEEP = 0x03U;
inline constexpr uint8_t PKT_MAINT_CMD_OP_MODE_NORMAL = 0x04U;

// Configuration is the legacy tracker application's persisted/radio schema,
// not FOTA configuration. The mixed widths intentionally preserve the old
// packed AVR packet ABI; this is not a FOTA configuration type.
struct Config {
  uint8_t lora_device_address;      // Local tracker radio address.
  uint8_t lora_gateway_address;     // Destination gateway radio address.
  float lora_freq;                  // Radio carrier frequency in MHz.
  uint8_t lora_tx_power;            // Radio output power in dBm.
  uint16_t collect_interval_day;    // Day collection period in seconds.
  uint16_t collect_interval_night;  // Night collection period in seconds.
  uint8_t day_start_hour;           // Inclusive start of day schedule.
  uint8_t day_end_hour;             // Exclusive end of day schedule.
  int8_t time_zone;                 // Local UTC offset in hours.
  uint8_t use_ack;                  // Nonzero when report ACKs are required.
  uint16_t ack_timeout;             // ACK wait budget in seconds.
  uint8_t long_range;             // Nonzero when long-range modulation is used.
  uint8_t tx_repeat;              // Number of report transmissions.
  uint16_t gps_max_wait_for_fix;  // Maximum GNSS wait in seconds.
  uint16_t next_collect_no_fix;   // Retry period after a missing fix.
  uint16_t total_slots;           // Number of tracker time slots.
  uint16_t slot_interval;         // Slot duration in seconds.

  Config()
      : lora_device_address(0x01U),
        lora_gateway_address(0x00U),
        lora_freq(450.0F),
        lora_tx_power(23U),
        collect_interval_day(600U),
        collect_interval_night(3600U),
        day_start_hour(6U),
        day_end_hour(18U),
        time_zone(7),
        use_ack(0U),
        ack_timeout(5U),
        long_range(1U),
        tx_repeat(3U),
        gps_max_wait_for_fix(120U),
        next_collect_no_fix(120U),
        total_slots(40U),
        slot_interval(10U) {}
} __attribute__((packed));

struct ReportEntry {
  uint8_t year, month, day;      // UTC calendar date.
  uint8_t hour, minute, second;  // UTC time of the report.
  uint16_t vbat;                 // in mV
  int32_t latitude, longitude;   // in 1/10000000 degrees
  uint8_t quality, satellites;
  int16_t temperature;  // in 1/100 degrees Celsius
  uint32_t ttf;         // time to obtain fix in ms
} __attribute__((packed));

struct PacketAdvertise {
  uint8_t type;  // PKT_TYPE_ADVERTISE.
  uint8_t seq;   // Legacy sequence number.
  PacketAdvertise() : type(PKT_TYPE_ADVERTISE), seq(0U) {}
} __attribute__((packed));

struct PacketReport {
  uint8_t type;        // PKT_TYPE_REPORT.
  uint8_t seq;         // Legacy sequence number.
  ReportEntry report;  // Sensor report payload.
  PacketReport() : type(PKT_TYPE_REPORT), seq(0U), report{} {}
} __attribute__((packed));

struct PacketReportWithAck {
  uint8_t type;        // PKT_TYPE_REPORT_WITH_ACK.
  uint8_t seq;         // Legacy sequence number.
  ReportEntry report;  // Sensor report payload.
  PacketReportWithAck() : type(PKT_TYPE_REPORT_WITH_ACK), seq(0U), report{} {}
} __attribute__((packed));

struct PacketAck {
  uint8_t type;  // PKT_TYPE_ACK.
  uint8_t seq;   // Report sequence being acknowledged.
  PacketAck() : type(PKT_TYPE_ACK), seq(0U) {}
} __attribute__((packed));

struct PacketBoot {
  uint8_t type;          // PKT_TYPE_BOOT.
  uint16_t firmware;     // Firmware version advertised by the tracker.
  uint8_t device_model;  // Legacy hardware model identifier.
  uint8_t reset_flags;   // Reset flags captured at boot.
  uint8_t checkpoint;    // Boot progress checkpoint.
  Config config;         // Legacy tracker configuration snapshot.
  PacketBoot()
      : type(PKT_TYPE_BOOT),
        firmware(0U),
        device_model(0U),
        reset_flags(0U),
        checkpoint(0U),
        config{} {}
} __attribute__((packed));

struct PacketMaintenance {
  uint8_t type;     // PKT_TYPE_MAINTENANCE.
  uint8_t command;  // PKT_MAINT_CMD_* value.
  PacketMaintenance() : type(PKT_TYPE_MAINTENANCE), command(0U) {}
} __attribute__((packed));

struct PacketMaintenanceAck {
  uint8_t type;      // PKT_TYPE_MAINTENANCE_ACK.
  uint8_t response;  // Response or echoed command.
  PacketMaintenanceAck() : type(PKT_TYPE_MAINTENANCE_ACK), response(0U) {}
} __attribute__((packed));

static_assert(sizeof(Config) == 27U, "legacy Config wire size changed");
static_assert(sizeof(ReportEntry) == 24U, "legacy report wire size changed");
static_assert(sizeof(PacketReport) == 26U,
              "legacy report packet wire size changed");
static_assert(sizeof(PacketReportWithAck) == 26U,
              "legacy report/ack packet wire size changed");
static_assert(sizeof(PacketBoot) == 33U,
              "legacy boot packet wire size changed");

}  // namespace iw::tracker::radio

#endif  // IW_TRACKER_RADIO_PACKETS_H_
