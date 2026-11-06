#pragma once

#include <stdint.h>
#include <stdio.h>
#include "updi_uart.h"

#define UPDI_ROLE_LOG_IDENTITY_V1 1

inline void updi_role_log(const char* role, const char* message) {
    if (!updi_uart_enabled()) return;

    updi_uart_tx('[');
    for (uint8_t i = 0; role != nullptr && role[i] != '\0' && i < 12; ++i) {
        updi_uart_tx(static_cast<uint8_t>(role[i]));
    }
    updi_uart_tx(']');
    updi_uart_tx(' ');
    for (uint8_t i = 0; message != nullptr && message[i] != '\0' && i < 120; ++i) {
        updi_uart_tx(static_cast<uint8_t>(message[i]));
    }
    updi_uart_tx('\r');
    updi_uart_tx('\n');
}

inline void updi_role_log_radio_version(const char* role, uint8_t version) {
    char message[32];
    snprintf(message, sizeof(message), "RADIO_SPI_VERSION=0x%02X",
             static_cast<unsigned>(version));
    updi_role_log(role, message);
}

inline void updi_role_log_status(const char* role, const char* event,
                                 int16_t status) {
    char message[48];
    snprintf(message, sizeof(message), "%s E=%d", event,
             static_cast<int>(status));
    updi_role_log(role, message);
}

inline void updi_role_log_radio_profile(const char* role, float frequency_mhz,
                                        int8_t tx_power_dbm,
                                        uint8_t spreading_factor,
                                        uint16_t bandwidth_khz,
                                        uint8_t coding_rate,
                                        uint8_t sync_word,
                                        uint8_t preamble_symbols,
                                        bool crc_enabled,
                                        bool iq_inverted) {
    const int32_t frequency_centi_mhz =
        static_cast<int32_t>(frequency_mhz * 100.0f + 0.5f);
    char message[48];
    snprintf(message, sizeof(message), "RADIO_PROFILE F100=%ld P=%d",
             static_cast<long>(frequency_centi_mhz),
             static_cast<int>(tx_power_dbm));
    updi_role_log(role, message);
    snprintf(message, sizeof(message), "RADIO_MOD SF=%u BW=%u CR=%u",
             static_cast<unsigned>(spreading_factor),
             static_cast<unsigned>(bandwidth_khz),
             static_cast<unsigned>(coding_rate));
    updi_role_log(role, message);
    snprintf(message, sizeof(message), "RADIO_FRAME SW=%02X PRE=%u CRC=%u HDR=E IQ=%u",
             static_cast<unsigned>(sync_word),
             static_cast<unsigned>(preamble_symbols),
             static_cast<unsigned>(crc_enabled),
             static_cast<unsigned>(iq_inverted));
    updi_role_log(role, message);
}

inline void updi_role_log_boot(const char* role, const char* build,
                               const char* date, const char* time) {
    char message[48];
    snprintf(message, sizeof(message), "BOOT %s %s %s", build, date, time);
    updi_role_log(role, message);
}

inline uint8_t updi_role_log_identity_crc8(const char* role, const char* build,
                                           const char* date, const char* time) {
    const char* parts[] = {role, "|", "V1", "|", build, "|", date, "|", time};
    uint8_t crc = 0;
    for (const char* part : parts) {
        if (part == nullptr) return 0;
        while (*part != '\0') {
            crc ^= static_cast<uint8_t>(*part++);
            for (uint8_t bit = 0; bit < 8; ++bit) {
                crc = static_cast<uint8_t>((crc & 0x80U) != 0
                                               ? (crc << 1) ^ 0x07U
                                               : crc << 1);
            }
        }
    }
    return crc;
}

inline void updi_role_log_identity(const char* role, const char* build,
                                   const char* date, const char* time) {
    if (role == nullptr || build == nullptr || date == nullptr || time == nullptr) return;
    char message[48];
    const uint8_t crc = updi_role_log_identity_crc8(role, build, date, time);
    snprintf(message, sizeof(message), "ID V1 %s %s %s CRC=%02X",
             build, date, time, static_cast<unsigned>(crc));
    updi_role_log(role, message);
}

inline void updi_role_log_campaign(const char* role, const char* event,
                                   uint16_t campaign_id) {
    char message[48];
    snprintf(message, sizeof(message), "%s C=%04X", event,
             static_cast<unsigned>(campaign_id));
    updi_role_log(role, message);
}

inline void updi_role_log_packet(const char* role, const char* event,
                                 uint16_t campaign_id, uint8_t sequence,
                                 uint8_t attempt) {
    char message[48];
    snprintf(message, sizeof(message), "%s C=%04X S=%02X A=%u", event,
             static_cast<unsigned>(campaign_id), static_cast<unsigned>(sequence),
             static_cast<unsigned>(attempt));
    updi_role_log(role, message);
}

inline void updi_role_log_payload(const char* role, const char* event,
                                  uint16_t campaign_id, uint8_t sequence,
                                  const uint8_t* payload, uint8_t payload_size) {
    if (!updi_uart_enabled() || event == nullptr || payload == nullptr) return;

    char message[128];
    const int prefix_length = snprintf(
        message, sizeof(message), "%s C=%04X S=%02X LEN=%u HEX=", event,
        static_cast<unsigned>(campaign_id), static_cast<unsigned>(sequence),
        static_cast<unsigned>(payload_size));
    if (prefix_length < 0 || static_cast<size_t>(prefix_length) >= sizeof(message)) {
        return;
    }

    static constexpr char hex[] = "0123456789ABCDEF";
    size_t position = static_cast<size_t>(prefix_length);
    for (uint8_t i = 0; i < payload_size; ++i) {
        if (position + 2 >= sizeof(message)) return;
        message[position++] = hex[payload[i] >> 4];
        message[position++] = hex[payload[i] & 0x0fU];
    }
    constexpr char ascii_prefix[] = " ASCII=";
    for (char character : ascii_prefix) {
        if (character == '\0') break;
        if (position + 1 >= sizeof(message)) return;
        message[position++] = character;
    }
    for (uint8_t i = 0; i < payload_size; ++i) {
        if (position + 1 >= sizeof(message)) return;
        const uint8_t byte = payload[i];
        message[position++] = byte >= 0x20 && byte <= 0x7e
                                  ? static_cast<char>(byte)
                                  : '.';
    }
    message[position] = '\0';
    updi_role_log(role, message);
}

inline void updi_role_log_airtime(const char* role, const char* event,
                                  uint16_t campaign_id, uint8_t sequence,
                                  uint8_t attempt, uint32_t airtime_us) {
    char message[48];
    snprintf(message, sizeof(message),
             "%s C=%04X S=%02X A=%u TOA_US=%lu", event,
             static_cast<unsigned>(campaign_id), static_cast<unsigned>(sequence),
             static_cast<unsigned>(attempt), static_cast<unsigned long>(airtime_us));
    updi_role_log(role, message);
}

inline void updi_role_log_rtt(const char* role, const char* event,
                              uint16_t campaign_id, uint8_t sequence,
                              uint32_t elapsed_ms) {
    char message[48];
    snprintf(message, sizeof(message), "%s C=%04X S=%02X RTT=%lu", event,
             static_cast<unsigned>(campaign_id), static_cast<unsigned>(sequence),
             static_cast<unsigned long>(elapsed_ms));
    updi_role_log(role, message);
}
