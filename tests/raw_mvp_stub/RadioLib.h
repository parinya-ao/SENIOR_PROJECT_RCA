#pragma once
#include "SPI.h"
#include <string.h>
#include <assert.h>
#define RADIOLIB_SX1278_CHIP_VERSION 0x12
#define RADIOLIB_SX1278_CHIP_VERSION_ALT 0x13
#define RADIOLIB_SX1278_CHIP_VERSION_RFM9X 0x11
#define RADIOLIB_ERR_NONE 0
#define RADIOLIB_ERR_CHIP_NOT_FOUND -2
#define RADIOLIB_ERR_CRC_MISMATCH -7
#define RADIOLIB_SX127X_CLEAR_IRQ_FLAG_RX_DONE 0x40
#define RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE 0x08
#define RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR 0x20
static uint16_t irq_flags;
static int rx_starts, tx_starts, cleanups, init_status, data_status, cleanup_status, rx_status;
static size_t packet_length;
static uint8_t packet[255], sent[255];
static size_t sent_length;
struct Module { Module(int, int, int, int, SPIClass&, SPISettings) {} };
struct SX1276 {
    explicit SX1276(Module*) {}
    void reset() {}
    int begin(float f, float bw, int sf, int cr, int sync, int p, int pre, int gain) {
        assert(f == 915 && bw == 125 && sf == 7 && cr == 5 && sync == 0x12 && p == 2 && pre == 8 && gain == 0);
        return init_status;
    }
    int setOutputPower(int p, bool rfo) { assert(p == 2 && !rfo); return init_status; }
    int explicitHeader() { return 0; }
    int setCRC(bool crc) { assert(crc); return 0; }
    int invertIQ(bool invert) { assert(!invert); return 0; }
    int startReceive() { ++rx_starts; irq_flags = 0; return rx_status; }
    uint16_t getIRQFlags() { return irq_flags; }
    int standby() { return 0; }
    size_t getPacketLength() { return packet_length; }
    int readData(uint8_t* bytes, size_t capacity) {
        assert(capacity == 32);
        memcpy(bytes, packet, packet_length < capacity ? packet_length : capacity);
        return data_status;
    }
    float getRSSI() { return -83.5f; }
    float getSNR() { return -1.25f; }
    int startTransmit(const uint8_t* bytes, size_t length) {
        ++tx_starts; sent_length = length; memcpy(sent, bytes, length); return 0;
    }
    int finishTransmit() { ++cleanups; irq_flags = 0; return cleanup_status; }
};
