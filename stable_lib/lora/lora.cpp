#include "lora.h"
#include <string.h>

// RadioLib requires plain ISR callbacks; one physical radio is active per MCU.
LoRa* LoRa::_active = nullptr;

LoRa::LoRa(uint32_t cs, uint32_t irq, uint32_t rst, uint32_t dio1)
    : _hardware(cs, irq, rst, dio1), _module(&_hardware) {}

int16_t LoRa::receive_start() {
    _module.setPacketReceivedAction(_received_action);
    return _module.startReceive();
}

int16_t LoRa::init(Address address, float frequency, int8_t power, uint8_t long_range) {
    _initialized = false;
    _transmitting = false;
    _tx_pending = false;
    _received = false;
    _active = this;
    _module.reset();
    int16_t error = _module.begin(frequency, 125.0f, long_range ? 12 : 7,
                                  long_range ? 8 : 5, 0x12, power, 8, 0);
    if (error != RADIOLIB_ERR_NONE) return error;
    if ((error = _module.setCurrentLimit(200)) != RADIOLIB_ERR_NONE) return error;
    if ((error = _module.setCRC(true)) != RADIOLIB_ERR_NONE) return error;
    if ((error = _module.invertIQ(false)) != RADIOLIB_ERR_NONE) return error;
    if ((error = _module.explicitHeader()) != RADIOLIB_ERR_NONE) return error;
    _my_addr = address;
    error = receive_start();
    _initialized = error == RADIOLIB_ERR_NONE;
    return error;
}

bool LoRa::available() { return _initialized && _received; }

int16_t LoRa::send(Address destination, const uint8_t* packet, uint8_t length) {
    if (!packet && length) return RADIOLIB_ERR_NULL_POINTER;
    if (length > 251) return RADIOLIB_ERR_PACKET_TOO_LONG;
    if (!_initialized || _tx_pending) return RADIOLIB_ERR_WRONG_MODEM;
    uint8_t buffer[255] = {destination, _my_addr, 0, 0};
    if (length) memcpy(buffer + 4, packet, length);
    _received = false;
    _transmitting = true;
    _tx_pending = true;
    _module.setPacketSentAction(_sent_action);
    const int16_t error = _module.startTransmit(buffer, static_cast<size_t>(length) + 4);
    if (error != RADIOLIB_ERR_NONE) {
        _transmitting = false;
        _tx_pending = false;
        _initialized = receive_start() == RADIOLIB_ERR_NONE;
    }
    return error;
}

int16_t LoRa::send_done() {
    if (!_initialized) return RADIOLIB_ERR_WRONG_MODEM;
    if (_transmitting) return 0;
    if (!_tx_pending) return 1;
    _tx_pending = false;
    const int16_t error = _module.finishTransmit();
    const int16_t rearm = receive_start();
    _initialized = rearm == RADIOLIB_ERR_NONE;
    if (error != RADIOLIB_ERR_NONE) return error;
    return rearm == RADIOLIB_ERR_NONE ? 1 : rearm;
}

int16_t LoRa::recv(Address* source, Address* destination, uint8_t* packet,
                    size_t capacity, uint8_t* length) {
    if (!source || !destination || !length || (!packet && capacity))
        return RADIOLIB_ERR_NULL_POINTER;
    *length = 0;
    if (!available()) return RADIOLIB_ERR_RX_TIMEOUT;
    _received = false;
    const size_t frame_length = _module.getPacketLength();
    uint8_t buffer[255];
    int16_t error = RADIOLIB_ERR_NONE;
    if (frame_length < 4 || frame_length > sizeof(buffer)) {
        error = RADIOLIB_ERR_PACKET_TOO_LONG;
    } else {
        error = _module.readData(buffer, frame_length);
        if (error == RADIOLIB_ERR_NONE && frame_length - 4 > capacity)
            error = RADIOLIB_ERR_PACKET_TOO_LONG;
    }
    if (error == RADIOLIB_ERR_NONE) {
        *source = buffer[1];
        *destination = buffer[0];
        *length = static_cast<uint8_t>(frame_length - 4);
        if (*length) memcpy(packet, buffer + 4, *length);
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

void LoRa::_sent_action() { if (_active) _active->_transmitting = false; }
void LoRa::_received_action() { if (_active) _active->_received = true; }
