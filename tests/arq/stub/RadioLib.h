// Fake RadioLib module for controlled ARQ send, receive, IRQ, and error tests.
#ifndef SENIOR_PROJECT_RCA_TESTS_ARQ_STUB_RADIOLIB_H_
#define SENIOR_PROJECT_RCA_TESTS_ARQ_STUB_RADIOLIB_H_

#include <assert.h>
#include <stdint.h>
#include <string.h>

#include "SPI.h"
#define RADIOLIB_SX1278_CHIP_VERSION 0x12
#define RADIOLIB_SX1278_CHIP_VERSION_ALT 0x13
#define RADIOLIB_SX1278_CHIP_VERSION_RFM9X 0x11
#define RADIOLIB_ERR_NONE 0
#define RADIOLIB_ERR_CHIP_NOT_FOUND -2
#define RADIOLIB_ERR_CRC_MISMATCH -7
#define RADIOLIB_SX127X_CLEAR_IRQ_FLAG_RX_DONE 0x40
#define RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE 0x08
#define RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR 0x20
#define RADIOLIB_SX127X_REG_OP_MODE 0x01
static uint16_t irq_flags;
static int16_t power_status, header_status, crc_status, iq_status,
    standby_status;
static int rx_starts, tx_starts, cleanups;
static int16_t init_status, data_status, cleanup_status, rx_status, tx_status;
static size_t packet_length;
static uint8_t packet[255], sent[255];
static size_t sent_length;
static uint8_t raw_regs[128];
static float last_begin_frequency_mhz;
struct Module {
  Module(int, int, int, int, SPIClass&, SPISettings) noexcept {}
  uint8_t SPIreadRegister(uint8_t address) {
    return address == 0x12 ? irq_flags : raw_regs[address];
  }
  int16_t SPIsetRegValue(uint32_t address, uint8_t value, uint8_t msb = 7,
                         uint8_t lsb = 0, uint8_t = 2, uint8_t = 0xff,
                         bool = false) {
    uint8_t mask = static_cast<uint8_t>(((1u << (msb - lsb + 1)) - 1u) << lsb);
    raw_regs[address] = static_cast<uint8_t>((raw_regs[address] & ~mask) |
                                             ((value << lsb) & mask));
    return 0;
  }
};
struct SX1276 {
  explicit SX1276(Module*) noexcept {}
  void reset() { raw_regs[1] = 0x01; }
  int16_t begin(float f, float bw, int sf, int cr, int sync, int p, int pre,
                int gain) {
    last_begin_frequency_mhz = f;
    assert(f == 915 && bw == 125 && sf == 7 && cr == 5 && sync == 0x12 &&
           p == 2 && pre == 8 && gain == 0);
    raw_regs[1] = 0x89;  // RadioLib enters LoRa standby but preserves
                         // reset-default LF bit.
    return init_status;
  }
  int16_t setOutputPower(int p, bool rfo) {
    assert(p == 2 && !rfo);
    return power_status;
  }
  int16_t explicitHeader() { return header_status; }
  int16_t setCRC(bool crc) {
    assert(crc);
    return crc_status;
  }
  int16_t invertIQ(bool invert) {
    assert(!invert);
    return iq_status;
  }
  int16_t startReceive() {
    ++rx_starts;
    irq_flags = 0;
    raw_regs[1] = (raw_regs[1] & 0xf8) | 0x05;
    return rx_status;
  }
  uint16_t getIRQFlags() { return irq_flags; }
  int16_t standby() {
    raw_regs[1] = (raw_regs[1] & 0xf8) | 0x01;
    return standby_status;
  }
  size_t getPacketLength() { return packet_length; }
  int16_t readData(uint8_t* bytes, size_t capacity) {
    assert(capacity > 0 && capacity <= 44);
    memcpy(bytes, packet, packet_length < capacity ? packet_length : capacity);
    irq_flags = 0;
    return data_status;
  }
  float getRSSI() { return -83.5f; }
  float getSNR() { return -1.25f; }
  int16_t startTransmit(const uint8_t* bytes, size_t length) {
    raw_regs[1] = (raw_regs[1] & 0xf8) | 0x03;
    ++tx_starts;
    sent_length = length;
    memcpy(sent, bytes, length);
    return tx_status;
  }
  int16_t finishTransmit() {
    ++cleanups;
    irq_flags = 0;
    return cleanup_status;
  }
};

#endif  // SENIOR_PROJECT_RCA_TESTS_ARQ_STUB_RADIOLIB_H_
