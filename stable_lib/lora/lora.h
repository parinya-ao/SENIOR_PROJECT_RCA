#pragma once

#include <SPI.h>
#include <RadioLib.h>

typedef uint8_t Address;

class LoRa {
public:
    LoRa(uint32_t cs_pin, uint32_t irq_pin, uint32_t rst_pin, uint32_t dio1_pin);
    bool init(Address my_addr, float freq, int8_t tx_power, uint8_t long_range);
    bool available();
    int16_t send(Address dst, const uint8_t* pkt, uint8_t len);
    bool send_done();
    void recv(Address *src, Address *dst, uint8_t* pkt, uint8_t* len);
    int16_t sleep() { return _module.sleep(); }
    void set_power(int8_t power) { _module.setOutputPower(power, false); }
    void set_frequency(float freq) { _module.setFrequency(freq); }
    void set_my_address(uint8_t addr) { _my_addr = addr; }
    Address my_address() { return _my_addr; }
    int16_t get_last_rssi() { return _last_rssi; }

private:
    SX1276 _module;
    Address _my_addr;
    int16_t _last_rssi;
};
