#include <string.h>
#include <Arduino.h>

#include "hello_config.h"
#include "lora.h"

LoRa* LoRa::_active_radio = nullptr;

LoRa::LoRa()
    : _hal(LORA_PIN_CS, LORA_PIN_IRQ, LORA_PIN_RST, LORA_PIN_DIO1),
      _module(&_hal),
      _cs_pin(LORA_PIN_CS),
      _my_addr(0),
      _last_rssi(0), _last_error(RADIOLIB_ERR_NONE), _transmitting(false),
      _received(false), _initialized(false), _spi1_selected(false),
      _tx_cleanup_pending(false), _tx_completion_ok(true), _tx_started_at(0),
      _tx_buffer{}, _rx_buffer{} {
    _active_radio = this;
}

bool LoRa::select_spi1() {
    if (_spi1_selected) return true;
    _spi1_selected = SPI.swap(LORA_SPI_ROUTE);
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

bool LoRa::init(Address my_addr) {
    _initialized = false;
    _received = false;
    _transmitting = false;
    _tx_cleanup_pending = false;
    _tx_completion_ok = true;
    if (!select_spi1()) return false;
    _module.reset();

    _last_error = _module.begin(HELLO_RF_FREQUENCY_MHZ,
                                HELLO_RF_BANDWIDTH_KHZ,
                                HELLO_RF_SPREADING_FACTOR,
                                HELLO_RF_CODING_RATE,
                                HELLO_RF_SYNC_WORD,
                                HELLO_RF_TX_POWER_DBM,
                                HELLO_RF_PREAMBLE_SYMBOLS,
                                HELLO_RF_AUTOMATIC_GAIN);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    // RadioLib 7.1.2 leaves LowFrequencyModeOn set at 915 MHz.
    _last_error = _module.standby();
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _hal.SPIsetRegValue(0x01, 0, 3, 3);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.setCurrentLimit(HELLO_RF_CURRENT_LIMIT_MA);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.setCRC(HELLO_RF_CRC_ENABLED);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.invertIQ(HELLO_RF_IQ_INVERTED);
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _last_error = _module.explicitHeader();
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _my_addr = my_addr;
    _module.setPacketReceivedAction(_received_action);
    _last_error = _module.startReceive();
    if (_last_error != RADIOLIB_ERR_NONE) return false;
    _initialized = true;
    return true;
}

bool LoRa::available() {
    return _initialized && !_tx_cleanup_pending &&
           (_received || (_module.getIrqFlags() & 0x40U));
}

int16_t LoRa::send(Address dst, const uint8_t* pkt, uint8_t len) {
    return send(dst, 0, 0, pkt, len);
}

int16_t LoRa::send(Address dst, uint8_t id, uint8_t flags,
                   const uint8_t* pkt, uint8_t len) {
#if HELLO_RF_DIAGNOSTIC_ONLY
    static_cast<void>(dst); static_cast<void>(id); static_cast<void>(flags);
    static_cast<void>(pkt); static_cast<void>(len);
    _last_error = RADIOLIB_ERR_UNKNOWN;
    return _last_error;
#endif
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
    _received = false;
    _transmitting = false;
    _tx_completion_ok = false;
    _last_error = _module.startTransmit(
        _tx_buffer, static_cast<uint8_t>(kRadioHeaderSize + len));
    if (_last_error == RADIOLIB_ERR_NONE) {
        _transmitting = true;
        _tx_cleanup_pending = true;
        _tx_started_at = millis();
    }
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
    // A DIO callback can be stale; only the current radio IRQ proves TxDone.
    _last_irq = static_cast<uint8_t>(_module.getIrqFlags());
    if (!(_last_irq & 0x08U)) {
        if (millis() - _tx_started_at >= LORA_TX_TIMEOUT_MS) {
            const int16_t recovery_error = recover();
            _last_error = recovery_error ? recovery_error : kTxTimeout;
        }
        return false;
    }

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
    if (!_initialized || _tx_cleanup_pending) {
        _last_error = RADIOLIB_ERR_UNKNOWN;
        return _last_error;
    }
    _last_irq = static_cast<uint8_t>(_module.getIrqFlags());
    if (!(_last_irq & 0x40U)) {
        _received = false;
        return RADIOLIB_ERR_NONE;
    }
    if (src == nullptr || dst == nullptr || id == nullptr || flags == nullptr ||
        (capacity != 0 && pkt == nullptr)) {
        _received = false;
        _last_error = RADIOLIB_ERR_UNKNOWN;
        return _last_error;
    }

    _received = false;
    const size_t packet_size = _module.getPacketLength();
    if (_last_irq & 0x20U) {
        _last_error = RADIOLIB_ERR_CRC_MISMATCH;
    } else if (packet_size < kRadioHeaderSize) {
        _last_error = RADIOLIB_ERR_UNKNOWN;
    } else if (packet_size > sizeof(_rx_buffer) ||
               packet_size - kRadioHeaderSize > capacity) {
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
    if (_tx_cleanup_pending) return RADIOLIB_ERR_UNKNOWN;
    if (!_initialized) return RADIOLIB_ERR_NONE;
    _last_error = _module.sleep();
    return _last_error;
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

int16_t LoRa::start_receive() {
    if (!_initialized || _tx_cleanup_pending) {
        _last_error = RADIOLIB_ERR_UNKNOWN;
        return _last_error;
    }
    _received = false;
    _module.setPacketReceivedAction(_received_action);
    _last_error = _module.startReceive();
    return _last_error;
}

int16_t LoRa::standby() {
    _last_error = _module.standby();
    _tx_cleanup_pending = false;
    _transmitting = false;
    _tx_completion_ok = false;
    _received = false;
    return _last_error;
}

int16_t LoRa::recover() {
    int16_t error = standby();
    if (!error) error = _module.clearIrqFlags(0xff);
    if (!error) error = start_receive();
    _last_error = error;
    return error;
}

uint8_t LoRa::read_register(uint8_t address) {
    return _hal.SPIgetRegValue(address);
}

void LoRa::_sent_action() {
    if (_active_radio != nullptr) _active_radio->_transmitting = false;
}

void LoRa::_received_action() {
    if (_active_radio != nullptr) _active_radio->_received = true;
}
