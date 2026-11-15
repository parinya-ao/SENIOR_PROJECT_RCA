#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <Arduino.h>
#include <RadioLib.h>
namespace fake_radio { State state; }
namespace fake_spi { State state; }
SPIClass SPI;
uint32_t host_ms;
void delay(unsigned ms) { host_ms+=ms; }
static const char* input="";
static char logs[12000];
static size_t used;
static bool mailbox_ready=true;
extern "C" bool updi_uart_enabled() { return true; }
extern "C" bool updi_uart_rx_poll() { return *input; }
extern "C" uint8_t updi_uart_rx() { return *input++; }
extern "C" void updi_uart_tx(uint8_t c) {
    assert(fake_radio::state.op_mode!=0x83); // Monitoring cannot block the TX-to-RX path.
    assert(used+1<sizeof logs);logs[used++]=c;logs[used]=0;
}
extern "C" bool updi_uart_try_tx(uint8_t c) {
    if(!mailbox_ready) return false;
    updi_uart_tx(c);return true;
}
#include "../src/reliable/main.cpp"
static void command(const char* text) {
    input=text;for(unsigned i=0;i<100;++i) { loop();++host_ms; }
}
int main() {
#if defined(TEST_LOG_DISABLED)
    {
    SPI.reset();fake_radio::state.airtime_us=50000;setup();
    for(unsigned i=0;i<100;++i) loop();
    command("R1234");command("S1234");
    assert(used==0 && updi_log_count==0);
    assert(fake_radio::state.transmit_starts==1);
    puts("PASS radio progresses with logging disabled");
    return 0;
    }
#endif
#if defined(TEST_LOG_BACKPRESSURE)
    {
    mailbox_ready=false;
    SPI.reset();fake_radio::state.airtime_us=50000;setup();
    for(unsigned i=0;i<3000;++i) { loop();++host_ms; }
    for(unsigned i=0;i<100;++i) updi_role_log(role,"backpressure");
    assert(updi_role_log_dropped()>0);
    for(unsigned i=0;i<30;++i) record(nullptr,"TEST",0,0,0);
    assert(log_overflow==6);
    command("R1234");command("S1234");
    assert(fake_radio::state.transmit_starts==1);
    fake_radio::state.irq_flags=8;loop();
    uint8_t ack[]={local_address,peer_address,0x34,0x12,3,1};
    memcpy(fake_radio::state.rx_data,ack,sizeof ack);
    fake_radio::state.rx_size=sizeof ack;fake_radio::state.irq_flags=0x40;
    loop();assert(transport.result()==decltype(transport)::Result::Accepted);
    mailbox_ready=true;
    for(unsigned i=0;i<3000;++i) loop();
    assert(used>0);
    puts("PASS radio progresses while OCD is permanently unavailable");
    return 0;
    }
#endif
    SPI.reset();fake_radio::state.airtime_us=50000;setup();loop();
#if HELLO_RF_DIAGNOSTIC_ONLY
    assert(strstr(logs,"RF_TX_DISABLED_DIAGNOSTIC"));
    command("S1234");command("N1235");
    assert(fake_radio::state.transmit_starts==0);
    puts("PASS RF-disabled diagnostic remains nontransmitting");
#else
    command("R1234");assert(strstr(logs,"RX_READY"));
    command("S1234");assert(fake_radio::state.transmit_starts==1);
    const uint8_t data[]={peer_address,local_address,0x34,0x12,8,1,
                          'h','e','l','l','o',' ','w','o','r','l','d'};
    assert(fake_radio::state.tx_size==sizeof data);
    assert(!memcmp(data,fake_radio::state.tx_data,sizeof data));
    fake_radio::state.irq_flags=8;loop();
    uint8_t ack[]={local_address,peer_address,0x34,0x12,3,1};
    memcpy(fake_radio::state.rx_data,ack,sizeof ack);
    fake_radio::state.rx_size=sizeof ack;fake_radio::state.irq_flags=0x40;
    loop();for(int i=0;i<30;++i)loop();
    assert(strstr(logs,"ACK_ACCEPTED"));
    command("N1235");
    uint8_t rejected[sizeof data];memcpy(rejected,data,sizeof data);
    rejected[0]=local_address;rejected[1]=peer_address;rejected[2]=0x35;
    memcpy(fake_radio::state.rx_data,rejected,sizeof rejected);
    fake_radio::state.rx_size=sizeof rejected;fake_radio::state.irq_flags=0x40;
    loop();assert(fake_radio::state.tx_data[4]==9);
    fake_radio::state.irq_flags=8;loop();
    for(int i=0;i<30;++i)loop();
    assert(strstr(logs,"NACK_TX_DONE"));
    command("P");assert(!radio_ready);
    command("S1236");assert(transport.active());
    command("P");assert(!transport.active() && !radio_ready);
    puts("PASS shared application send/receive/reject/rearm/park");
#endif
}
