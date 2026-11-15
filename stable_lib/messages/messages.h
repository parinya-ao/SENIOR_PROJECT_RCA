#pragma once

#include <stdint.h>
#include "config.h"

#define PKT_TYPE_ADVERTISE       0x01
#define PKT_TYPE_REPORT          0x02
#define PKT_TYPE_ACK             0x03
#define PKT_TYPE_BOOT            0x04
#define PKT_TYPE_REPORT_WITH_ACK 0x05
#define PKT_TYPE_MAINTENANCE     0x06
#define PKT_TYPE_MAINTENANCE_ACK 0x07

#define PKT_MAINT_CMD_NOP            0x00
#define PKT_MAINT_CMD_REBOOT         0x01
#define PKT_MAINT_CMD_OP_MODE_QUERY  0x02
#define PKT_MAINT_CMD_OP_MODE_SLEEP  0x03
#define PKT_MAINT_CMD_OP_MODE_NORMAL 0x04

struct ReportEntry {
    uint8_t year, month, day;
    uint8_t hour, minute, second;
    uint16_t vbat;  // in mV
    int32_t latitude, longitude; // in 1/10000000 degrees
    uint8_t quality, satellites;
    int16_t temperature;  // in 1/100 degrees Celsius
    uint32_t ttf;  // time to obtain fix in ms
} __attribute__((packed));

struct PacketAdvertise {
    uint8_t type;
    uint8_t seq;
    PacketAdvertise():type(PKT_TYPE_ADVERTISE) {}
} __attribute__((packed));

struct PacketReport {
    uint8_t type;
    uint8_t seq;
    ReportEntry report;
    PacketReport():type(PKT_TYPE_REPORT) {}
} __attribute__((packed));

struct PacketReportWithAck {
    uint8_t type;
    uint8_t seq;
    ReportEntry report;
    PacketReportWithAck():type(PKT_TYPE_REPORT_WITH_ACK) {}
} __attribute__((packed));

struct PacketAck {
    uint8_t type;
    uint8_t seq;
    PacketAck():type(PKT_TYPE_ACK) {}
} __attribute__((packed));

struct PacketBoot {
  uint8_t type;
  uint16_t firmware;
  uint8_t device_model;
  uint8_t reset_flags;
  uint8_t checkpoint;
  Config config;
  PacketBoot():type(PKT_TYPE_BOOT) {}
} __attribute__((packed));

struct PacketMaintenance {
    uint8_t type;
    uint8_t command;
    PacketMaintenance():type(PKT_TYPE_MAINTENANCE) {}
} __attribute__((packed));

struct PacketMaintenanceAck {
    uint8_t type;
    uint8_t response;
    PacketMaintenanceAck():type(PKT_TYPE_MAINTENANCE_ACK) {}
} __attribute__((packed));

