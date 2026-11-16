// Record real-driver writes through the existing fake public HAL; no RF model.
#define main previous_hal_main
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wreturn-type"
#include "radiolib_hal_test.cpp"
#pragma GCC diagnostic pop
#undef main
#include <math.h>

class TraceBus : public Bus {
public:
    const char* stage = "construct";
    unsigned sensitivity_writes = 0;
    TraceBus() : Bus(9) { defaults(); }
    void defaults() {
        regs[0x31]=0xc3; regs[0x2f]=0x20; regs[0x30]=0;
        regs[0x36]=3; regs[0x3a]=0x65; regs[0x33]=0x27; regs[0x3b]=0x1d;
        regs[0x4d]=0x84; regs[0x0c]=0x20;
    }
    void digitalWrite(uint32_t pin, uint32_t value) override {
        Bus::digitalWrite(pin,value);
        if(pin==3 && value==1) defaults();
    }
    void spiTransfer(uint8_t* out, size_t n, uint8_t* in) override {
        if(out[0]&0x80) for(size_t i=1;i<n;i++) {
            uint8_t address=(out[0]&0x7f)?(out[0]&0x7f)+i-1:0;
            printf("W %s %02X %02X\n",stage,address,out[i]);
            if(address==0x36 || address==0x3a) ++sensitivity_writes;
        }
        Bus::spiTransfer(out,n,in);
    }
};

int main() {
    TraceBus bus; Module module(&bus,1,2,3,4); SX1276 radio(&module);
    assert(bus.regs[0x31]&0x80); // Documented reset seed, not measured silicon.
    bus.stage="begin";
    assert(radio.begin(915,125,7,5,0x12,2,8,0)==0);
    bus.stage="PA_BOOST"; assert(radio.setOutputPower(2,false)==0);
    bus.stage="explicit"; assert(radio.explicitHeader()==0);
    bus.stage="CRC"; assert(radio.setCRC(true)==0);
    bus.stage="IQ"; assert(radio.invertIQ(false)==0);
    bus.stage="standby"; assert(radio.standby()==0);
    const unsigned before=bus.sensitivity_writes;
    for(unsigned i=0;i<2;i++) {
        bus.stage=i?"RX_again":"RX";
        assert(radio.startReceive()==0);
        assert(bus.regs[1]==0x8d && bus.regs[6]==0xe4 && bus.regs[7]==0xc0 && bus.regs[8]==0);
#if RADIOLIB_FIX_ERRATA_SX127X
        assert(bus.regs[0x31]==0x43 && bus.regs[0x2f]==0x40 && bus.regs[0x30]==0);
#else
        assert(bus.regs[0x31]==0xc3 && bus.regs[0x2f]==0x20 && bus.regs[0x30]==0);
#endif
        assert(bus.regs[0x1d]==0x72 && bus.regs[0x1e]==0x74 && bus.regs[0x26]==4);
        assert(bus.regs[0x33]==0x27 && bus.regs[0x3b]==0x1d && bus.regs[0x39]==0x12);
    }
    assert(bus.sensitivity_writes==before); // BW125 must not run the BW500 branch.
    assert(bus.regs[0x09]==0xf0 && bus.regs[0x4d]==0x84 && bus.regs[0x0c]==0x23);
    bus.stage="IRQ_read_clear";
    bus.regs[0x1a]=50; bus.regs[0x19]=32;
    assert(radio.getRSSI()==-107 && radio.getSNR()==8);
    bus.regs[0x12]=0x50; bus.regs[0x16]=0; bus.regs[0x17]=0;
    assert(radio.getIRQFlags()==0x50 && radio.getIRQFlags()==0x50);
    assert(radio.clearIrqFlags(0x40)==0 && bus.regs[0x12]==0x10);
    printf("PASS errata=%d modeled BW125 RX, repeated RX, IQ, bit3 preservation, RSSI HF offset, W1C\n",RADIOLIB_FIX_ERRATA_SX127X);
}
