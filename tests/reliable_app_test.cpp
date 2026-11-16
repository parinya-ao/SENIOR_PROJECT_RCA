#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <Arduino.h>
#include <RadioLib.h>

namespace fake_radio { State state; }
namespace fake_spi { State state; }
SPIClass SPI;
uint32_t host_ms;

static const char* input="";
static char logs[12000];
static size_t used;
static bool mailbox_ready=true;
extern "C" bool updi_uart_enabled() { return true; }
extern "C" bool updi_uart_rx_poll() { return *input; }
extern "C" uint8_t updi_uart_rx() { return *input++; }
extern "C" void updi_uart_tx(uint8_t c) {
    assert(fake_radio::state.op_mode!=0x83);
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

#if !HELLO_RF_DIAGNOSTIC_ONLY
static void deliver(uint8_t source,uint8_t destination,
                    const uint8_t* payload,uint8_t length) {
    fake_radio::state.rx_data[0]=destination;
    fake_radio::state.rx_data[1]=source;
    fake_radio::state.rx_data[2]=0;
    fake_radio::state.rx_data[3]=0;
    memcpy(fake_radio::state.rx_data+4,payload,length);
    fake_radio::state.rx_size=static_cast<size_t>(length)+4;
    fake_radio::state.irq_flags=0x40;
    fake_radio::state.received_action();
}

static void complete_tx() {
    fake_radio::state.irq_flags=8;
    fake_radio::state.sent_action();
    loop();
}
#endif

int main() {
#if defined(TEST_LOG_DISABLED)
    SPI.reset();setup();command("S");
    assert(used==0 && updi_log_count==0);
    assert(fake_radio::state.transmit_starts==1);
    puts("PASS radio progresses with logging disabled");
    return 0;
#endif
#if defined(TEST_LOG_BACKPRESSURE)
    {
    mailbox_ready=false;SPI.reset();setup();
    for(unsigned i=0;i<100;++i) updi_role_log(role,"backpressure");
    assert(updi_role_log_dropped()>0);
    for(unsigned i=0;i<30;++i) record(nullptr,"TEST",0,0,0);
    assert(log_overflow==14);
    command("S");assert(fake_radio::state.transmit_starts==1);
    complete_tx();
    const uint8_t ack[]={SSOT_ACK_TYPE,SSOT_SEQUENCE};
    deliver(local_address,peer_address,ack,sizeof ack);loop();
    assert(transport.result()==decltype(transport)::Result::Accepted);
    mailbox_ready=true;
    for(unsigned i=0;i<30;++i) loop();
    assert(used>0);
    puts("PASS radio progresses while OCD is unavailable");
    return 0;
    }
#endif

    SPI.reset();setup();
#if HELLO_RF_DIAGNOSTIC_ONLY
    command("S");
    assert(fake_radio::state.transmit_starts==0);
    puts("PASS diagnostic target stays RF-disabled");
#elif defined(LORA_ROLE_RECEIVER)
    assert(radio_ready);
    command("N");
    const uint8_t data[]={SSOT_DATA_TYPE,SSOT_SEQUENCE,'h','e','l','l','o',' ','w','o','r','l','d'};
    deliver(LORA_SENDER_ADDRESS,LORA_RECEIVER_ADDRESS,data,sizeof data);loop();
    assert(fake_radio::state.tx_copy[4]==SSOT_NACK_TYPE);
    complete_tx();
    command("A");
    deliver(LORA_SENDER_ADDRESS,LORA_RECEIVER_ADDRESS,data,sizeof data);loop();
    assert(fake_radio::state.tx_copy[4]==SSOT_ACK_TYPE);
    complete_tx();
    command("P");assert(!radio_ready);
    command("R");assert(radio_ready);
    puts("PASS receiver validates DATA and transmits ACK/NACK with rearm");
#else
    assert(radio_ready);
    command("S");assert(fake_radio::state.transmit_starts==1);
    const uint8_t data[]={LORA_RECEIVER_ADDRESS,LORA_SENDER_ADDRESS,0,0,
        SSOT_DATA_TYPE,SSOT_SEQUENCE,'h','e','l','l','o',' ','w','o','r','l','d'};
    assert(fake_radio::state.tx_size==sizeof data);
    assert(!memcmp(data,fake_radio::state.tx_copy,sizeof data));
    complete_tx();
    const uint8_t nack[]={SSOT_NACK_TYPE,SSOT_SEQUENCE};
    deliver(LORA_RECEIVER_ADDRESS,LORA_SENDER_ADDRESS,nack,sizeof nack);loop();
    assert(fake_radio::state.transmit_starts==2);
    complete_tx();
    const uint8_t ack[]={SSOT_ACK_TYPE,SSOT_SEQUENCE};
    deliver(LORA_RECEIVER_ADDRESS,LORA_SENDER_ADDRESS,ack,sizeof ack);loop();
    assert(transport.result()==decltype(transport)::Result::Accepted);
    assert(strstr(logs,"ACK_ACCEPTED"));
    command("P");assert(!radio_ready);
    command("R");assert(radio_ready);
    puts("PASS sender retransmits NACK and accepts matching ACK");
#endif
}
