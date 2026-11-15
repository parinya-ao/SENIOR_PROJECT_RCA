#pragma once

#include <stddef.h>
#include <SPI.h>
#include <RadioLib.h>
#include "../../../include/generated/radio_915_config.h"

typedef uint8_t Address;

class LoRa {
public:
    static constexpr uint8_t kRadioHeaderSize = 4;
    static constexpr uint8_t kMaxPayloadSize = 251;
    static constexpr uint8_t kSx127xVersionRegister = 0x42;
    static constexpr uint8_t kSx127xVersionRfm9x = 0x11;
    static constexpr uint8_t kSx127xVersionOfficial = 0x12;
    static constexpr uint8_t kSx127xVersionAlternate = 0x13;

    LoRa();
    static bool is_supported_chip_version(uint8_t version);
    int16_t read_chip_version(uint8_t* version);
    bool init(Address my_addr);
    bool available();
    int16_t send(Address dst, const uint8_t* pkt, uint8_t len);
    int16_t send(Address dst, uint8_t id, uint8_t flags,
                 const uint8_t* pkt, uint8_t len);
    bool send_done();
    void recv(Address* src, Address* dst, uint8_t* pkt, uint8_t* len);
    int16_t recv(Address* src, Address* dst, uint8_t* id, uint8_t* flags,
                 uint8_t* pkt, uint8_t* len, size_t capacity);
    int16_t sleep();
    void set_my_address(uint8_t addr);
    Address my_address();
    int16_t get_last_rssi();
    uint32_t time_on_air_us(uint8_t payload_size);
    int16_t last_error() const;
    int16_t start_receive();
    int16_t recover();
    int16_t standby();
    uint8_t read_register(uint8_t address);
    uint8_t last_irq() const { return _last_irq; }
    static constexpr int16_t kTxTimeout = -1001;

private:
    static void _sent_action();
    static void _received_action();
    static LoRa* _active_radio;
    bool select_spi1();

    Module _hal;
    SX1276 _module;
    uint32_t _cs_pin;
    Address _my_addr;
    int16_t _last_rssi;
    int16_t _last_error;
    volatile bool _transmitting;
    volatile bool _received;
    bool _initialized;
    bool _spi1_selected;
    bool _tx_cleanup_pending;
    bool _tx_completion_ok;
    uint32_t _tx_started_at;
    uint8_t _last_irq = 0;
    uint8_t _tx_buffer[255];
    uint8_t _rx_buffer[255];
};
