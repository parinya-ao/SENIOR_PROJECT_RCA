#include "radio_link.h"

#include <string.h>

#include "ssot_radio_header.h"

// RadioLib requires plain ISR callbacks; one physical radio is active per MCU.
LoRa* LoRa::_active = nullptr;

LoRa::LoRa(uint32_t cs, uint32_t irq, uint32_t rst, uint32_t dio1)
    : _hardware(cs, irq, rst, dio1), _module(&_hardware) {}

int16_t LoRa::receive_start() {
  _module.setPacketReceivedAction(_received_action);
  return _module.startReceive();
}

int16_t LoRa::init(Address address, float frequency, int8_t power,
                   uint8_t long_range) {
  _initialized = false;
  _radio_version = 0;
  _transmitting = false;
  _tx_pending = false;
  _received = false;
  _active = this;
  _module.reset();
  int16_t error = _module.begin(frequency, 125.0f, long_range ? 12 : 7,
                                long_range ? 8 : 5, 0x12, power, 8, 0);
  if (error != RADIOLIB_ERR_NONE) return error;
  error = _module.setCurrentLimit(200);
  if (error != RADIOLIB_ERR_NONE) return error;
  error = _module.setCRC(true);
  if (error != RADIOLIB_ERR_NONE) return error;
  error = _module.invertIQ(false);
  if (error != RADIOLIB_ERR_NONE) return error;
  error = _module.explicitHeader();
  if (error != RADIOLIB_ERR_NONE) return error;
  const int16_t version = _module.getChipVersion();
  if (version < RADIOLIB_ERR_NONE) return version;
  _radio_version = static_cast<uint8_t>(version);
  _my_addr = address;
  error = receive_start();
  _initialized = error == RADIOLIB_ERR_NONE;
  return error;
}

bool LoRa::available() { return _initialized && _received; }

int16_t LoRa::send(Address destination, const uint8_t* packet, uint8_t length) {
  return send(destination, 0, packet, length);
}

int16_t LoRa::send(Address destination, uint16_t campaign_id,
                   const uint8_t* packet, uint8_t length) {
  if (!packet && length) return RADIOLIB_ERR_NULL_POINTER;
  if (length > 255U - ssot::kRadioHeaderSize)
    return RADIOLIB_ERR_PACKET_TOO_LONG;
  if (!_initialized || _tx_pending) return RADIOLIB_ERR_WRONG_MODEM;
  uint8_t buffer[255];
  ssot::EncodeRadioHeader({destination, _my_addr, campaign_id}, buffer);
  if (length) memcpy(buffer + ssot::kRadioHeaderSize, packet, length);
  _received = false;
  _transmitting = true;
  _tx_pending = true;
  _module.setPacketSentAction(_sent_action);
  const int16_t error = _module.startTransmit(
      buffer, static_cast<size_t>(length) + ssot::kRadioHeaderSize);
  if (error != RADIOLIB_ERR_NONE) {
    _transmitting = false;
    _tx_pending = false;
    _initialized = receive_start() == RADIOLIB_ERR_NONE;
  }
  return error;
}

int16_t LoRa::send_done(bool* tx_done, int16_t* rx_rearm) {
  if (tx_done) *tx_done = false;
  if (rx_rearm) *rx_rearm = RADIOLIB_ERR_NONE;
  if (!_initialized) return RADIOLIB_ERR_WRONG_MODEM;
  if (_transmitting) return 0;
  if (!_tx_pending) return 1;
  _tx_pending = false;
  if (tx_done) *tx_done = true;
  const int16_t error = _module.finishTransmit();
  const int16_t rearm = receive_start();
  if (rx_rearm) *rx_rearm = rearm;
  _initialized = rearm == RADIOLIB_ERR_NONE;
  if (error != RADIOLIB_ERR_NONE) return error;
  return rearm == RADIOLIB_ERR_NONE ? 1 : rearm;
}

int16_t LoRa::recv(Address* source, Address* destination, uint8_t* packet,
                   size_t capacity, uint8_t* length) {
  return recv(source, destination, nullptr, packet, capacity, length);
}

int16_t LoRa::recv(Address* source, Address* destination, uint16_t* campaign_id,
                   uint8_t* packet, size_t capacity, uint8_t* length) {
  if (!source || !destination || !length || (!packet && capacity))
    return RADIOLIB_ERR_NULL_POINTER;
  *length = 0;
  if (!available()) return RADIOLIB_ERR_RX_TIMEOUT;
  _received = false;
  const size_t frame_length = _module.getPacketLength();
  uint8_t buffer[255];
  int16_t error = RADIOLIB_ERR_NONE;
  if (frame_length < ssot::kRadioHeaderSize || frame_length > sizeof(buffer)) {
    error = RADIOLIB_ERR_PACKET_TOO_LONG;
  } else {
    error = _module.readData(buffer, frame_length);
    if (error == RADIOLIB_ERR_NONE &&
        frame_length - ssot::kRadioHeaderSize > capacity)
      error = RADIOLIB_ERR_PACKET_TOO_LONG;
  }
  if (error == RADIOLIB_ERR_NONE) {
    const ssot::RadioHeader header = ssot::DecodeRadioHeader(buffer);
    *source = header.source;
    *destination = header.destination;
    if (campaign_id) *campaign_id = header.campaign_id;
    *length = static_cast<uint8_t>(frame_length - ssot::kRadioHeaderSize);
    if (*length) memcpy(packet, buffer + ssot::kRadioHeaderSize, *length);
    _last_rssi = static_cast<int16_t>(_module.getRSSI());
  }
  const int16_t rearm = receive_start();
  _initialized = rearm == RADIOLIB_ERR_NONE;
  return rearm != RADIOLIB_ERR_NONE ? rearm : error;
}

int16_t LoRa::sleep() {
  const int16_t error = _module.sleep();
  if (error == RADIOLIB_ERR_NONE) {
    _initialized = false;
    _transmitting = false;
    _tx_pending = false;
    _received = false;
  }
  return error;
}

int16_t LoRa::park() {
  const int16_t status = _module.standby();
  if (status != RADIOLIB_ERR_NONE) return status;
  _initialized = false;
  _transmitting = false;
  _tx_pending = false;
  _received = false;
  return read_register(0x01) == 0x81 ? RADIOLIB_ERR_NONE
                                     : RADIOLIB_ERR_WRONG_MODEM;
}

void LoRa::_sent_action() {
  if (_active) _active->_transmitting = false;
}
void LoRa::_received_action() {
  if (_active) _active->_received = true;
}
