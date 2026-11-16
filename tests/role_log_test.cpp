#include <stdint.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#define _Bool bool
#include "role_log.h"
#undef _Bool

static char captured[256];
static size_t captured_size;
static unsigned checks;

static void clear_capture() {
    captured_size = 0;
    captured[0] = '\0';
}

extern "C" bool updi_uart_enabled(void) { return true; }
extern "C" void updi_uart_tx(uint8_t byte) {
    if (captured_size + 1 < sizeof(captured)) {
        captured[captured_size++] = static_cast<char>(byte);
        captured[captured_size] = '\0';
    }
}
extern "C" bool updi_uart_rx_poll(void) { return false; }
extern "C" uint8_t updi_uart_rx(void) { return 0; }

#define CHECK(condition) do { \
    ++checks; \
    if (!(condition)) { \
        std::fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); \
        return EXIT_FAILURE; \
    } \
} while (0)

int main() {
    char fixed_width[5];
    updi_role_log_format_hex(fixed_width, 0x0393, 4);
    CHECK(std::strcmp(fixed_width, "0393") == 0);
#ifndef UPDI_ROLE_LOG_IDENTITY_V1
    CHECK(false && "versioned role identity marker is not implemented");
#else
    updi_role_log_identity("SENDER", "sender_hello", "Nov  6 2026", "05:00:00");
    CHECK(std::strcmp(captured,
          "[SENDER] ID V1 sender_hello Nov  6 2026 05:00:00 CRC=E1\r\n") == 0);
    clear_capture();
#endif
    updi_role_log_boot("GATEWAY", "sender_hello", "Nov  6 2026", "00:00:00");
    CHECK(std::strcmp(captured,
          "[GATEWAY] BOOT sender_hello Nov  6 2026 00:00:00\r\n") == 0);
    clear_capture();
    updi_role_log_packet("GATEWAY", "DATA_TX", 0x1234, 1, 4);
    CHECK(std::strcmp(captured,
          "[GATEWAY] DATA_TX C=1234 S=01 A=4\r\n") == 0);
    clear_capture();
    const uint8_t hello_payload[] = {
        'h', 'e', 'l', 'l', 'o', ' ', 'w', 'o', 'r', 'l', 'd'
    };
    updi_role_log_payload("RECEIVER", "PAYLOAD_BYTES", 0x1234, 1,
                          hello_payload, sizeof(hello_payload));
    CHECK(std::strcmp(captured,
          "[RECEIVER] PAYLOAD_BYTES C=1234 S=01 LEN=11 "
          "HEX=68656C6C6F20776F726C64 ASCII=hello world\r\n") == 0);
    clear_capture();
    updi_role_log_campaign("GATEWAY", "TEST_COMPLETED", 0x1234);
    CHECK(std::strcmp(captured,
          "[GATEWAY] TEST_COMPLETED C=1234\r\n") == 0);
    clear_capture();
    updi_role_log_campaign("RECEIVER", "SESSION_READY", 0x0393);
    CHECK(std::strcmp(captured,
          "[RECEIVER] SESSION_READY C=0393\r\n") == 0);
    clear_capture();
    updi_role_log_packet("RECEIVER", "PAYLOAD_MATCH", 0x0393, 1, 0);
    CHECK(std::strcmp(captured,
          "[RECEIVER] PAYLOAD_MATCH C=0393 S=01 A=0\r\n") == 0);
    clear_capture();
    updi_role_log_rtt("GATEWAY", "ACK_RX", 0x1234, 1, 42);
    CHECK(std::strcmp(captured,
          "[GATEWAY] ACK_RX C=1234 S=01 RTT=42\r\n") == 0);
    clear_capture();
    updi_role_log_airtime("RECEIVER", "ACK_TX", 0x1234, 1, 0, 123456);
    CHECK(std::strcmp(captured,
          "[RECEIVER] ACK_TX C=1234 S=01 A=0 TOA_US=123456\r\n") == 0);
    clear_capture();
    updi_role_log_radio_version("RECEIVER", 0x12);
    CHECK(std::strcmp(captured,
          "[RECEIVER] RADIO_SPI_VERSION=0x12\r\n") == 0);
    clear_capture();
    updi_role_log_radio_profile("GATEWAY", 915.0f, 10, 7, 125, 5,
                                0x12, 8, true, false);
    CHECK(std::strcmp(captured,
          "[GATEWAY] RADIO_PROFILE F100=91500 P=10\r\n"
          "[GATEWAY] RADIO_MOD SF=7 BW=125 CR=5\r\n"
          "[GATEWAY] RADIO_FRAME SW=12 PRE=8 CRC=1 HDR=E IQ=0\r\n") == 0);
    clear_capture();
    updi_role_log_status("GATEWAY", "RADIO_INIT", -5);
    CHECK(std::strcmp(captured,
          "[GATEWAY] RADIO_INIT E=-5\r\n") == 0);
    std::printf("PASS %u role-log checks\n", checks);
    return EXIT_SUCCESS;
}
