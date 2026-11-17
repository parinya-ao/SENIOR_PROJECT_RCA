#ifndef SENIOR_PROJECT_RCA_SRC_FEATURES_RADIO_LINK_RADIO_LINK_H_
#define SENIOR_PROJECT_RCA_SRC_FEATURES_RADIO_LINK_RADIO_LINK_H_

#include <RadioLib.h>
#include <SPI.h>
#include <stddef.h>
#include <stdint.h>

// Defines the SX127x LoRa HAL while preserving the existing RadioHead header.
typedef uint8_t Address;

// Owns one foreground LoRa interface and its RadioLib module. ISR callbacks
// only update latches; call this API from the foreground. One initialized
// instance is supported per MCU. Send and receive use fixed 255-byte stack
// buffers and preserve the existing four-byte RadioHead header.
class LoRa {
 public:
  // Binds chip-select, IRQ, reset and DIO1 Arduino pins without hardware I/O.
  LoRa(uint32_t cs_pin, uint32_t irq_pin, uint32_t rst_pin, uint32_t dio1_pin);

  // Resets/configures the radio and starts continuous RX. `my_addr` is the
  // local wire address, `freq` is MHz, `tx_power` is dBm, and `long_range`
  // selects the existing long-range PHY. Returns RadioLib's status code; zero
  // means RX was armed. On failure the object remains uninitialized.
  int16_t init(Address my_addr, float freq, int8_t tx_power,
               uint8_t long_range);

  // Returns SX127x RegVersion captured during init; zero means it was not read.
  uint8_t version() const { return _radio_version; }

  // Reports whether the RX callback latched a packet; performs no SPI work.
  bool available();

  // Copies `len` payload bytes after the existing header and starts async TX
  // to `dst`. `pkt` is borrowed only for this call. Returns a RadioLib status;
  // on failure TX state is cleared and RX re-arm is attempted.
  int16_t send(Address dst, const uint8_t* pkt, uint8_t len);

  // Same as send(), with `campaign_id` encoded little-endian in the existing
  // RadioHead ID/flags header bytes. Zero preserves the legacy header values.
  int16_t send(Address dst, uint16_t campaign_id, const uint8_t* pkt,
               uint8_t len);
  // Returns zero while TX is pending, one when no TX is pending or completion
  // cleanup has finished, and a negative RadioLib error otherwise. Completion
  // calls finishTransmit and re-arms RX.
  int16_t send_done();

  // Reads one latched packet, fills source/destination/payload length, then
  // re-arms RX. `capacity` bounds writes to `pkt`; after pointer validation,
  // `len` is zeroed before reading.
  // Returns a RadioLib status or RX_TIMEOUT when no packet is latched. Source
  // and destination are written only after a successful read.
  int16_t recv(Address* src, Address* dst, uint8_t* pkt, size_t capacity,
               uint8_t* len);

  // Same as recv(), additionally returning the little-endian campaign ID from
  // the existing RadioHead ID/flags header bytes.
  int16_t recv(Address* src, Address* dst, uint16_t* campaign_id, uint8_t* pkt,
               size_t capacity, uint8_t* len);

  // Sleeps the radio and clears software RX/TX state. Returns RadioLib status.
  int16_t sleep();

  // Sets output power in dBm. Returns RadioLib status.
  int16_t set_power(int8_t power) {
    return _module.setOutputPower(power, false);
  }

  // Sets center frequency in MHz. Returns RadioLib status.
  int16_t set_frequency(float freq) { return _module.setFrequency(freq); }

  // Changes the address written into outgoing packet headers. This does not
  // enable SX127x address filtering in LoRa mode.
  void set_my_address(uint8_t addr) { _my_addr = addr; }

  // Returns the local address written into outgoing packet headers.
  Address my_address() { return _my_addr; }

  // Returns RSSI in dBm from the last successfully read packet.
  int16_t get_last_rssi() { return _last_rssi; }

 private:
  static LoRa* _active;
  static void _sent_action();
  static void _received_action();
  int16_t receive_start();
  Module _hardware;
  SX1276 _module;
  Address _my_addr = 0;
  int16_t _last_rssi = 0;
  uint8_t _radio_version = 0;
  volatile bool _transmitting = false;
  volatile bool _received = false;
  bool _tx_pending = false;
  bool _initialized = false;
};

#endif  // SENIOR_PROJECT_RCA_SRC_FEATURES_RADIO_LINK_RADIO_LINK_H_
