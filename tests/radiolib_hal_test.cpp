// Real installed driver; only the public electrical HAL is modeled.
#include <RadioLib.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
class Bus : public RadioLibHal {
 public:
  uint8_t regs[128] = {0}, fifo[256] = {0};
  uint32_t ticks = 0, finish_delay = 0;
  uint8_t reset_mode;
  Bus(uint8_t mode) : RadioLibHal(0, 1, 0, 1, 1, 0), reset_mode(mode) {
    reset();
  }
  void reset() {
    memset(regs, 0, sizeof regs);
    regs[1] = reset_mode;
    regs[0x42] = 0x12;
    regs[0x31] = 0xc3;
  }
  void pinMode(uint32_t, uint32_t) override {}
  void digitalWrite(uint32_t pin, uint32_t value) override {
    if (pin == 3 && value == 1) reset();
  }
  uint32_t digitalRead(uint32_t) override { return 0; }
  void attachInterrupt(uint32_t, void (*)(), uint32_t) override {}
  void detachInterrupt(uint32_t) override {}
  void delay(RadioLibTime_t ms) override { ticks += ms * 1000; }
  void delayMicroseconds(RadioLibTime_t us) override {
    finish_delay = us;
    ticks += us;
  }
  RadioLibTime_t millis() override { return ticks++ / 1000; }
  RadioLibTime_t micros() override { return ticks++; }
  long pulseIn(uint32_t, uint32_t, RadioLibTime_t) override { return 0; }
  void spiBegin() override {}
  void spiBeginTransaction() override {}
  void spiEndTransaction() override {}
  void spiEnd() override {}
  void spiTransfer(uint8_t* out, size_t n, uint8_t* in) override {
    assert(n >= 2);
    bool write = out[0] & 0x80;
    uint8_t address = out[0] & 0x7f;
    memset(in, 0, n);
    for (size_t i = 1; i < n; i++) {
      uint8_t a = address ? address + i - 1 : 0;
      if (write) {
        if (!a)
          fifo[regs[0x0d]++] = out[i];
        else if (a == 0x12)
          regs[a] &= ~out[i];  // silicon W1C model
        else
          regs[a] = out[i];
      } else
        in[i] = a ? regs[a] : fifo[regs[0x0d]++];
    }
  }
};
int main() {
  const uint8_t modes[] = {1, 9};
  for (uint8_t reset_mode : modes) {
    Bus bus(reset_mode);
    Module module(&bus, 1, 2, 3, 4);
    SX1276 radio(&module);
    assert(radio.begin(915, 125, 7, 5, 0x12, 2, 8, 0) == 0);
    assert((bus.regs[1] & 8) == (reset_mode & 8));
    assert(radio.setFrequency(915) == 0);
    assert(bus.regs[6] == 0xe4 && bus.regs[7] == 0xc0 && bus.regs[8] == 0);
    assert(radio.explicitHeader() == 0 && radio.setCRC(true) == 0 &&
           radio.invertIQ(false) == 0);
    assert(bus.regs[0x1d] == 0x72 && bus.regs[0x1e] == 0x74 &&
           bus.regs[0x26] == 4);
    assert(bus.regs[0x33] == 1 &&
           bus.regs[0x3b] == 0x1d);  // reserved IQ bits modeled as zero
    bus.regs[0x12] = 0x68;
    assert(radio.getIRQFlags() == 0x68 && radio.getIRQFlags() == 0x68);
    assert(radio.clearIrqFlags(0x20) == 0 && bus.regs[0x12] == 0x48);
    uint8_t payload[] = {1, 2, 3};
    assert(radio.startTransmit(payload, 3) == 0);
    assert((bus.regs[1] & 7) == 3 && bus.regs[0x12] == 0 &&
           !memcmp(bus.fifo, payload, 3));
    bus.regs[0x12] = 8;
    assert(radio.finishTransmit() == 0);
    assert(bus.finish_delay == 1000000 / 1200 && bus.regs[0x12] == 0 &&
           (bus.regs[1] & 7) == 1);
    assert(radio.startReceive() == 0 && (bus.regs[1] & 7) == 5 &&
           bus.regs[0x12] == 0);
    assert((bus.regs[0x31] & 0x87) == 3 && bus.regs[0x2f] == 0x40 &&
           bus.regs[0x30] == 0);
    assert(bus.regs[0x33] == 1 && bus.regs[0x3b] == 0x1d &&
           bus.regs[0x39] == 0x12);
    bus.regs[0x12] = 0x40;
    bus.regs[0x13] = 3;
    bus.regs[0x10] = 0;
    bus.regs[0x1c] = 0x40;
    memcpy(bus.fifo, payload, 3);
    uint8_t result[3];
    assert(radio.readData(result, 3) == 0 && !memcmp(result, payload, 3) &&
           bus.regs[0x12] == 0);
    bus.regs[0x12] = 0x60;
    assert(radio.readData(result, 3) == RADIOLIB_ERR_CRC_MISMATCH &&
           bus.regs[0x12] == 0);
    // Candidate 915 MHz HF selection: exercise the installed driver through
    // retry/reinitialization.
    for (int initialization = 0; initialization < 2; initialization++) {
      assert(radio.begin(915, 125, 7, 5, 0x12, 2, 8, 0) == 0);
      uint8_t before = bus.regs[1];
      assert(module.SPIsetRegValue(RADIOLIB_SX127X_REG_OP_MODE, 0, 3, 3) == 0);
      assert(bus.regs[1] == (before & 0xf7) && bus.regs[1] == 0x81);
      assert(bus.regs[6] == 0xe4 && bus.regs[7] == 0xc0 && bus.regs[8] == 0);
      for (int attempt = 0; attempt < 3; attempt++) {
        assert(radio.startReceive() == 0 && bus.regs[1] == 0x85);
        assert(radio.standby() == 0 && bus.regs[1] == 0x81);
        assert(radio.startTransmit(payload, 3) == 0 && bus.regs[1] == 0x83);
        bus.regs[0x12] = 8;
        assert(radio.finishTransmit() == 0 && bus.regs[1] == 0x81);
        assert(radio.startReceive() == 0 && bus.regs[1] == 0x85);
      }
    }
    puts(
        "begin -> carrier E4C000 -> IRQ read/W1C -> TX/FIFO -> finish "
        "833us/standby -> RX -> FIFO/CRC/clear: PASS");
  }
}
