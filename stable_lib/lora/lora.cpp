#include <SPI.h>
#include <RadioLib.h>

#include "lora.h"

// The following static declarations will prevent the lib from being used by
// multiple LoRa instances.  However, these variables cannot be member
// variables because they cannot be accessed from ISRs.
static volatile bool _transmitting;
static volatile bool _received;
static void _sent_action();
static void _received_action();

/***********************************************
 * 
 */
LoRa::LoRa(uint32_t cs_pin, uint32_t irq_pin, uint32_t rst_pin, uint32_t dio1_pin):
    _module(new Module(cs_pin, irq_pin, rst_pin, dio1_pin)) {
    _transmitting = false;
    _received = false;
}

/***********************************************
 * 
 */
bool LoRa::init(Address my_addr, float freq, int8_t tx_power, uint8_t long_range) {
    _module.reset();
    if (_module.begin() != RADIOLIB_ERR_NONE)
        return false;
    _module.setFrequency(freq);
    _module.setOutputPower(tx_power, false);
    _module.setNodeAddress(my_addr);
    _module.setCurrentLimit(200);
    _module.setCRC(true);
    _module.invertIQ(false);
    _module.explicitHeader();
    if (long_range) {
        _module.setSpreadingFactor(12);
        _module.setBandwidth(125);
        _module.setCodingRate(8);
    }
    else {
        _module.setSpreadingFactor(7);
        _module.setBandwidth(125);
        _module.setCodingRate(5);
    }
    _my_addr = my_addr;
    _module.startReceive();
    _module.setPacketReceivedAction(_received_action);
    return true;
}

/***********************************************
 * 
 */
bool LoRa::available() {
    return _received;
}

/***********************************************
 * 
 */
int16_t LoRa::send(Address dst, const uint8_t* pkt, uint8_t len) {
    // Payload format follows RadioHead's header structure
    // See https://github.com/hallard/RadioHead/blob/master/RH_RF95.cpp#L293
    uint8_t buf[256];
    buf[0] = dst;
    buf[1] = _my_addr;
    buf[2] = 0;
    buf[3] = 0;
    memcpy(buf+4, pkt, len);
    _module.setPacketSentAction(_sent_action);
    _module.startTransmit(buf, len+4);
    _transmitting = true;
}

/***********************************************
 * 
 */
void LoRa::recv(Address *src, Address *dst, uint8_t* pkt, uint8_t* len) {
    if (!_received) return;

    uint8_t buf[256];
    uint8_t tmplen;
    tmplen = _module.getPacketLength();
    _module.readData(buf, tmplen);
    *dst = buf[0];
    *src = buf[1];
    *len = tmplen - 4;
    _last_rssi = (int16_t) _module.getRSSI();
    memcpy(pkt, buf+4, *len);
    _received = false;
}

/***********************************************
 * 
 */
static void _sent_action() {
    _transmitting = false;
}

/***********************************************
 * this method must be called and return true at least once after each send to
 * ensure proper cleanup.
 */
bool LoRa::send_done() {
    if (_transmitting) {
        return false;
    }
    else {
        _module.finishTransmit();
        _module.setPacketReceivedAction(_received_action);
        _module.startReceive();
        return true;
    }
}

/***********************************************
 * 
 */
static void _received_action() {
    _received = true;
}
