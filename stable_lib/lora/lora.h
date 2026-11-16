#pragma once

#include <SPI.h>
#include <RadioLib.h>

typedef uint8_t Address;

class LoRa {
public:
    LoRa(uint32_t cs_pin, uint32_t irq_pin, uint32_t rst_pin, uint32_t dio1_pin);
    int16_t init(Address my_addr, float freq, int8_t tx_power, uint8_t long_range);
    bool available();
    int16_t send(Address dst, const uint8_t* pkt, uint8_t len);
    // 0 while pending, 1 after successful TX and RX rearm, negative RadioLib error.
    int16_t send_done();
    int16_t recv(Address *src, Address *dst, uint8_t* pkt, size_t capacity, uint8_t* len);
    int16_t sleep();
    int16_t set_power(int8_t power) { return _module.setOutputPower(power, false); }
    int16_t set_frequency(float freq) { return _module.setFrequency(freq); }
    void set_my_address(uint8_t addr) { _my_addr = addr; }
    Address my_address() { return _my_addr; }
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
    volatile bool _transmitting = false;
    volatile bool _received = false;
    bool _tx_pending = false;
    bool _initialized = false;
};
