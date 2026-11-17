// Deterministic SX127x/RadioLib double for wrapper lifecycle and packet I/O.
#ifndef SENIOR_PROJECT_RCA_TESTS_RADIO_STUB_RADIOLIB_H_
#define SENIOR_PROJECT_RCA_TESTS_RADIO_STUB_RADIOLIB_H_

#include <SPI.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define RADIOLIB_ERR_NONE 0
#define RADIOLIB_ERR_UNKNOWN -1
#define RADIOLIB_ERR_PACKET_TOO_LONG -4
#define RADIOLIB_ERR_RX_TIMEOUT -6
#define RADIOLIB_ERR_NULL_POINTER -28
#define RADIOLIB_ERR_CRC_MISMATCH -7
#define RADIOLIB_ERR_WRONG_MODEM -20

namespace fake_radio {
struct State {
  int16_t begin_status;
  int16_t config_status;
  int16_t start_receive_status;
  int16_t start_transmit_status;
  int16_t finish_transmit_status;
  int16_t read_data_status;
  int16_t sleep_status;
  int16_t chip_version = 0x12;
  uint32_t irq_flags;
  uint8_t op_mode;
  int16_t standby_status;
  size_t rx_size;
  uint32_t airtime_us;
  size_t airtime_length;
  uint8_t rx_data[255];
  uint8_t* tx_data;
  uint8_t tx_copy[255];
  uint8_t tx_size;
  float frequency_mhz;
  int8_t tx_power_dbm;
  float bandwidth_khz;
  uint8_t spreading_factor;
  uint8_t coding_rate;
  uint8_t sync_word;
  size_t preamble_symbols;
  bool crc_enabled;
  bool iq_inverted;
  bool explicit_header;
  uint8_t current_limit_ma;
  uint8_t gain;
  uint32_t module_cs_pin;
  uint32_t module_irq_pin;
  uint32_t module_reset_pin;
  uint32_t module_dio1_pin;
  int16_t current_limit_calls;
  int16_t frequency_set_calls;
  int16_t output_power_set_calls;
  int16_t receive_starts;
  int16_t finish_transmits;
  int16_t sleep_calls;
  int16_t transmit_starts;
  int16_t begin_calls;
  int16_t node_address_calls;
  bool spi1_route_at_begin;
  void (*sent_action)();
  void (*received_action)();
};

extern State state;
}  // namespace fake_radio

class Module {
 public:
  int16_t SPIsetRegValue(uint8_t, uint8_t value, uint8_t = 7, uint8_t = 0) {
    fake_radio::state.op_mode = value;
    return fake_radio::state.config_status;
  }
  uint8_t SPIgetRegValue(uint8_t) { return fake_radio::state.op_mode; }
  Module(uint32_t cs, uint32_t irq, uint32_t reset, uint32_t dio1) {
    fake_radio::state.module_cs_pin = cs;
    fake_radio::state.module_irq_pin = irq;
    fake_radio::state.module_reset_pin = reset;
    fake_radio::state.module_dio1_pin = dio1;
  }
};

class SX1276 {
 public:
  explicit SX1276(Module*) {}

  int16_t getChipVersion() { return fake_radio::state.chip_version; }

  void reset() {}
  int16_t begin() {
    ++fake_radio::state.begin_calls;
    fake_radio::state.spi1_route_at_begin =
        fake_spi::state.route == SPI1_SWAP_DEFAULT;
    return fake_radio::state.begin_status;
  }
  int16_t begin(float frequency, float bandwidth, uint8_t spreading_factor,
                uint8_t coding_rate, uint8_t sync_word, int8_t power,
                uint16_t preamble, uint8_t gain) {
    ++fake_radio::state.begin_calls;
    fake_radio::state.spi1_route_at_begin =
        fake_spi::state.route == SPI1_SWAP_DEFAULT;
    fake_radio::state.frequency_mhz = frequency;
    fake_radio::state.bandwidth_khz = bandwidth;
    fake_radio::state.spreading_factor = spreading_factor;
    fake_radio::state.coding_rate = coding_rate;
    fake_radio::state.sync_word = sync_word;
    fake_radio::state.tx_power_dbm = power;
    fake_radio::state.preamble_symbols = preamble;
    fake_radio::state.gain = gain;
    SPI.begin();
    return fake_radio::state.begin_status;
  }
  int16_t setFrequency(float value) {
    ++fake_radio::state.frequency_set_calls;
    fake_radio::state.frequency_mhz = value;
    return fake_radio::state.config_status;
  }
  int16_t setOutputPower(int8_t value, bool) {
    ++fake_radio::state.output_power_set_calls;
    fake_radio::state.tx_power_dbm = value;
    return fake_radio::state.config_status;
  }
  int16_t setNodeAddress(uint8_t) {
    ++fake_radio::state.node_address_calls;
    return RADIOLIB_ERR_WRONG_MODEM;
  }
  int16_t setCurrentLimit(uint8_t value) {
    ++fake_radio::state.current_limit_calls;
    fake_radio::state.current_limit_ma = value;
    return fake_radio::state.config_status;
  }
  int16_t setCRC(bool enabled) {
    fake_radio::state.crc_enabled = enabled;
    return fake_radio::state.config_status;
  }
  int16_t invertIQ(bool inverted) {
    fake_radio::state.iq_inverted = inverted;
    return fake_radio::state.config_status;
  }
  int16_t explicitHeader() {
    fake_radio::state.explicit_header = true;
    return fake_radio::state.config_status;
  }
  int16_t setSpreadingFactor(uint8_t value) {
    fake_radio::state.spreading_factor = value;
    return fake_radio::state.config_status;
  }
  int16_t setBandwidth(float value) {
    fake_radio::state.bandwidth_khz = value;
    return fake_radio::state.config_status;
  }
  int16_t setCodingRate(uint8_t value) {
    fake_radio::state.coding_rate = value;
    return fake_radio::state.config_status;
  }
  void setPacketSentAction(void (*action)()) {
    fake_radio::state.sent_action = action;
  }
  void setPacketReceivedAction(void (*action)()) {
    fake_radio::state.received_action = action;
  }
  int16_t startReceive() {
    ++fake_radio::state.receive_starts;
    fake_radio::state.irq_flags = 0;
    fake_radio::state.op_mode = 0x85;
    return fake_radio::state.start_receive_status;
  }
  int16_t startTransmit(uint8_t* data, uint8_t len) {
    ++fake_radio::state.transmit_starts;
    fake_radio::state.irq_flags = 0;
    fake_radio::state.op_mode = 0x83;
    fake_radio::state.tx_data = data;
    fake_radio::state.tx_size = len;
    memcpy(fake_radio::state.tx_copy, data, len);
    return fake_radio::state.start_transmit_status;
  }
  int16_t finishTransmit() {
    ++fake_radio::state.finish_transmits;
    fake_radio::state.irq_flags = 0;
    return fake_radio::state.finish_transmit_status;
  }
  size_t getPacketLength() { return fake_radio::state.rx_size; }
  int16_t readData(uint8_t* data, uint8_t len) {
    if (fake_radio::state.read_data_status != RADIOLIB_ERR_NONE) {
      return fake_radio::state.read_data_status;
    }
    for (uint8_t i = 0; i < len; ++i) data[i] = fake_radio::state.rx_data[i];
    return RADIOLIB_ERR_NONE;
  }
  float getRSSI() { return -42.0f; }
  uint32_t getTimeOnAir(size_t len) {
    fake_radio::state.airtime_length = len;
    return fake_radio::state.airtime_us;
  }
  int16_t sleep() {
    ++fake_radio::state.sleep_calls;
    if (fake_radio::state.sleep_status == RADIOLIB_ERR_NONE)
      fake_radio::state.op_mode = 0x80;
    return fake_radio::state.sleep_status;
  }
  int16_t standby() {
    fake_radio::state.op_mode = 0x81;
    return fake_radio::state.standby_status;
  }
  uint32_t getIrqFlags() { return fake_radio::state.irq_flags; }
  int16_t clearIrqFlags(uint32_t flags) {
    fake_radio::state.irq_flags &= ~flags;
    return 0;
  }
};

#endif  // SENIOR_PROJECT_RCA_TESTS_RADIO_STUB_RADIOLIB_H_
