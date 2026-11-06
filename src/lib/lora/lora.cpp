#include <string.h>
#include <Arduino.h>

#include "hello_config.h"
#include "lora.h"

LoRa* LoRa::_active_radio = nullptr;

LoRa::LoRa(uint32_t cs_pin, uint32_t irq_pin, uint32_t rst_pin, uint32_t dio1_pin)
    : _module(new Module(cs_pin, irq_pin, rst_pin, dio1_pin)), _cs_pin(cs_pin),
      _my_addr(0),
      _last_rssi(0), _last_error(RADIOLIB_ERR_NONE), _transmitting(false),
      _received(false), _initialized(false), _spi1_selected(false),
      _tx_cleanup_pending(false), _tx_completion_ok(true),
      _tx_buffer{}, _rx_buffer{} {
    _active_radio = this;
}

bool LoRa::select_spi1() {
    if (_spi1_selected) return true;
    _spi1_selected = SPI.swap(SPI1_SWAP_DEFAULT);
    if (!_spi1_selected) _last_error = RADIOLIB_ERR_UNKNOWN;
    return _spi1_selected;
}

bool LoRa::is_supported_chip_version(uint8_t version) {
    return version == kSx127xVersionRfm9x ||
           version == kSx127xVersionOfficial ||
           version == kSx127xVersionAlternate;
}

int16_t LoRa::read_chip_version(uint8_t* version) {
    if (version == nullptr) {
        _last_error = RADIOLIB_ERR_UNKNOWN;
        return _last_error;
    }
    if (!select_spi1()) return _last_error;

    SPI.begin();
    SPI.beginTransaction(RADIOLIB_DEFAULT_SPI_SETTINGS);
    digitalWrite(_cs_pin, LOW);
    static_cast<void>(SPI.transfer(kSx127xVersionRegister & 0x7f));
    *version = SPI.transfer(0x00);
    digitalWrite(_cs_pin, HIGH);
    SPI.endTransaction();
    _last_error = RADIOLIB_ERR_NONE;
    return _last_error;
}

bool LoRa::init(Address my_addr, float freq, int8_t tx_power, uint8_t long_range) {
    _initialized = false;
    _received = false;
    _transmitting = false;
    _tx_cleanup_pending = false;
    _tx_completion_ok = true;
    if (!select_spi1()) return false;
    _module.reset();

    _last_error = _module.begin();
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.setFrequency(freq);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.setOutputPower(tx_power, false);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.setCurrentLimit(200);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.setCRC(HELLO_RF_CRC_ENABLED);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.invertIQ(HELLO_RF_IQ_INVERTED);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.explicitHeader();
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.setSyncWord(HELLO_RF_SYNC_WORD);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.setPreambleLength(HELLO_RF_PREAMBLE_SYMBOLS);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    if (long_range) {
        _last_error = _module.setSpreadingFactor(12);
        if (_last_error != RADIOLIB_ERR_NONE) return false;
        _last_error = _module.setBandwidth(125);
        if (_last_error != RADIOLIB_ERR_NONE) return false;
        _last_error = _module.setCodingRate(8);
    } else {
        _last_error = _module.setSpreadingFactor(HELLO_RF_SPREADING_FACTOR);
        if (_last_error != RADIOLIB_ERR_NONE) return false;
        _last_error = _module.setBandwidth(HELLO_RF_BANDWIDTH_KHZ);
        if (_last_error != RADIOLIB_ERR_NONE) return false;
        _last_error = _module.setCodingRate(HELLO_RF_CODING_RATE);
    }
    if (_last_error != RADIOLIB_ERR_NONE) return false;

    _my_addr = my_addr;
    _module.setPacketReceivedAction(_received_action);
    _last_error = _module.startReceive();
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _initialized = true;
    return true;
}

bool LoRa::available() {
    return _received;
}

int16_t LoRa::send(Address dst, const uint8_t* pkt, uint8_t len) {
    return send(dst, 0, 0, pkt, len);
}

int16_t LoRa::send(Address dst, uint8_t id, uint8_t flags,
                   const uint8_t* pkt, uint8_t len) {
    if (!_initialized || _tx_cleanup_pending || (len != 0 && pkt == nullptr)) {
        _last_error = RADIOLIB_ERR_UNKNOWN;
        return _last_error;
    }
    if (len > kMaxPayloadSize) {
        _last_error = RADIOLIB_ERR_PACKET_TOO_LONG;
        return _last_error;
    }

    _tx_buffer[0] = dst;
    _tx_buffer[1] = _my_addr;
    _tx_buffer[2] = id;
    _tx_buffer[3] = flags;
    if (len != 0) memcpy(_tx_buffer + kRadioHeaderSize, pkt, len);

    _module.setPacketSentAction(_sent_action);
    _transmitting = true;
    _tx_cleanup_pending = true;
    _tx_completion_ok = false;
    _last_error = _module.startTransmit(
        _tx_buffer, static_cast<uint8_t>(kRadioHeaderSize + len));
    if (_last_error != RADIOLIB_ERR_NONE) {
        const int16_t transmit_error = _last_error;
        _transmitting = false;
        _tx_cleanup_pending = false;
        _module.setPacketReceivedAction(_received_action);
        const int16_t receive_error = _module.startReceive();
        if (receive_error != RADIOLIB_ERR_NONE) {
            _initialized = false;
            _last_error = receive_error;
            return _last_error;
        }
        _last_error = transmit_error;
    }
    return _last_error;
}

bool LoRa::send_done() {
    if (!_tx_cleanup_pending) return _tx_completion_ok;
    if (_transmitting) return false;

    const int16_t finish_error = _module.finishTransmit();
    _module.setPacketReceivedAction(_received_action);
    const int16_t receive_error = _module.startReceive();
    _tx_cleanup_pending = false;
    _transmitting = false;
    _tx_completion_ok = finish_error == RADIOLIB_ERR_NONE &&
                        receive_error == RADIOLIB_ERR_NONE;
    if (receive_error != RADIOLIB_ERR_NONE) _initialized = false;
    _last_error = receive_error != RADIOLIB_ERR_NONE
                      ? receive_error
                      : finish_error;
    return _tx_completion_ok;
}

void LoRa::recv(Address* src, Address* dst, uint8_t* pkt, uint8_t* len) {
    uint8_t id = 0;
    uint8_t flags = 0;
    static_cast<void>(recv(src, dst, &id, &flags, pkt, len, kMaxPayloadSize));
}

int16_t LoRa::recv(Address* src, Address* dst, uint8_t* id, uint8_t* flags,
                   uint8_t* pkt, uint8_t* len, size_t capacity) {
    if (len == nullptr) {
        _last_error = RADIOLIB_ERR_UNKNOWN;
        return _last_error;
    }
    *len = 0;
    if (!_received) return RADIOLIB_ERR_NONE;
    if (src == nullptr || dst == nullptr || id == nullptr || flags == nullptr ||
        (capacity != 0 && pkt == nullptr)) {
        _received = false;
        _last_error = RADIOLIB_ERR_UNKNOWN;
        return _last_error;
    }

    _received = false;
    const size_t packet_size = _module.getPacketLength();
    if (packet_size > sizeof(_rx_buffer)) {
        _last_error = RADIOLIB_ERR_PACKET_TOO_LONG;
    } else {
        _last_error = _module.readData(_rx_buffer,
                                       static_cast<uint8_t>(packet_size));
        if (_last_error == RADIOLIB_ERR_NONE) {
            if (packet_size < kRadioHeaderSize ||
                packet_size - kRadioHeaderSize > capacity) {
                _last_error = packet_size < kRadioHeaderSize
                                  ? RADIOLIB_ERR_UNKNOWN
                                  : RADIOLIB_ERR_PACKET_TOO_LONG;
            } else {
                *dst = _rx_buffer[0];
                *src = _rx_buffer[1];
                *id = _rx_buffer[2];
                *flags = _rx_buffer[3];
                *len = static_cast<uint8_t>(packet_size - kRadioHeaderSize);
                if (*len != 0) memcpy(pkt, _rx_buffer + kRadioHeaderSize, *len);
                _last_rssi = static_cast<int16_t>(_module.getRSSI());
            }
        }
    }

    const int16_t read_error = _last_error;
    const int16_t receive_error = _module.startReceive();
    if (receive_error != RADIOLIB_ERR_NONE) {
        _initialized = false;
        _last_error = receive_error;
        return receive_error;
    }
    _last_error = read_error;
    return read_error;
}

int16_t LoRa::sleep() {
    if (!_initialized) return RADIOLIB_ERR_NONE;
    _last_error = _module.sleep();
    return _last_error;
}

void LoRa::set_power(int8_t power) {
    _last_error = _module.setOutputPower(power, false);
}

void LoRa::set_frequency(float freq) {
    _last_error = _module.setFrequency(freq);
}

void LoRa::set_my_address(uint8_t addr) {
    _my_addr = addr;
}

Address LoRa::my_address() {
    return _my_addr;
}

int16_t LoRa::get_last_rssi() {
    return _last_rssi;
}

uint32_t LoRa::time_on_air_us(uint8_t payload_size) {
    if (!_initialized || payload_size > kMaxPayloadSize) {
        _last_error = payload_size > kMaxPayloadSize
                          ? RADIOLIB_ERR_PACKET_TOO_LONG
                          : RADIOLIB_ERR_UNKNOWN;
        return 0;
    }
    return static_cast<uint32_t>(
        _module.getTimeOnAir(kRadioHeaderSize + payload_size));
}

int16_t LoRa::last_error() const {
    return _last_error;
}

void LoRa::_sent_action() {
    if (_active_radio != nullptr) _active_radio->_transmitting = false;
}

void LoRa::_received_action() {
    if (_active_radio != nullptr) _active_radio->_received = true;
}
