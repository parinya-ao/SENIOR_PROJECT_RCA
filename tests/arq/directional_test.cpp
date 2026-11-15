// Host adapter simulation; IRQ/FIFO observations here are not physical RF evidence.
#include "../../src/arq/main.cpp"
#include "../../src/arq/board_ssot.c"
#include <assert.h>

static void cmd(const char* text) {
    for(;*text;++text)command_byte(*text);
    command_byte('\n');
}
static void clear_log() { log_head=log_tail=log_count=log_offset=0; }
static bool logged(const char* name) {
    for(uint8_t i=0;i<log_count;i++)if(strstr(log_slots[i].text,name))return true;
    return false;
}
int main(int argc,char** argv) {
    bool nack=argc>1 && !strcmp(argv[1],"nack");
    setup();assert(ready && parked && !tx_starts);
    cmd("ARM 12345678");assert(raw_regs[1]==0x85);
    const char* payload=ARQ_SENDER_ID==1?"HELLO_LORA_GW":"HELLO_LORA_TR";
    if(nack)payload="REJECT_LORA";
#if defined(ARQ_ROLE_SENDER)
    char text[80]="SEND ";
    for(size_t i=0;i<strlen(payload);i++)sprintf(text+5+2*i,"%02X",(uint8_t)payload[i]);
    cmd(text);loop();assert(tx_starts==1 && raw_regs[1]==0x83);
    arq_frame data;assert(arq_decode(&data,sent,sent_length));
    assert(data.src==ARQ_SENDER_ID && data.dst==ARQ_RECEIVER_ID);
    assert(data.sequence==0 && data.session==0x12345678);
    assert(data.length==strlen(payload) && !memcmp(data.payload,payload,data.length));
    irq_flags=8;loop();assert(sender.state==ARQ_WAITING_ACK && raw_regs[1]==0x85);
    arq_frame response={(uint8_t)(nack?ARQ_NACK:ARQ_ACK),ARQ_RECEIVER_ID,ARQ_SENDER_ID,
        0x12345678,0,0,(uint8_t)(nack?ARQ_APPLICATION_REJECTED:ARQ_NONE),{0}};
    for(int invalid=0;invalid<4;invalid++){
        arq_frame bad=response;
        if(invalid==0)++bad.session;
        if(invalid==1)++bad.sequence;
        if(invalid==2)bad.src=bad.dst;
        packet_length=arq_encode(&bad,packet,44);
        if(invalid==3)--packet_length;
        irq_flags=0x40;clear_log();loop();assert(sender.state==ARQ_WAITING_ACK);
        assert(!logged("e=DELIVERED ") && !logged("e=REJECTED "));
    }
    packet_length=arq_encode(&response,packet,44);irq_flags=0x40;clear_log();
    if(argc>1 && !strcmp(argv[1],"expired")){
        clock_ms=sender.terminal_at;loop();
        assert(sender.result==ARQ_TIMEOUT_EXHAUSTED && sender.sequence==0);
        assert(!logged("e=DELIVERED "));return 0;
    }
    loop();assert(sender.result==(nack?ARQ_REJECTED:ARQ_OK));
    assert(sender.sequence==(nack?0:1));
    assert(logged(nack?"e=REJECTED ":"e=DELIVERED ") && logged(" q=0 "));
    irq_flags=0x40;clear_log();loop(); // duplicate control cannot repeat success
    assert(!logged("e=DELIVERED ") && !logged("e=REJECTED "));
#else
    arq_frame data={ARQ_DATA,ARQ_SENDER_ID,ARQ_RECEIVER_ID,0x12345678,0,0,0,{0}};
    data.length=strlen(payload);memcpy(data.payload,payload,data.length);
    packet_length=arq_encode(&data,packet,44);irq_flags=0x40;clear_log();loop();
    assert(receiver.deliveries==(nack?0:1) && response_wait && tx_starts==0);
    assert(logged(nack?"e=DATA_REJECT ":"e=ACCEPT "));
    clock_ms+=ARQ_RESPONSE_GUARD_MS;clear_log();loop();
    assert(tx_starts==1 && raw_regs[1]==0x83);
    arq_frame response;assert(arq_decode(&response,sent,sent_length));
    assert(response.type==(nack?ARQ_NACK:ARQ_ACK));
    assert(response.reason==(nack?ARQ_APPLICATION_REJECTED:ARQ_NONE));
    assert(response.src==ARQ_RECEIVER_ID && response.dst==ARQ_SENDER_ID);
    assert(response.session==data.session && response.sequence==data.sequence);
    irq_flags=8;clear_log();loop();assert(completed==1 && raw_regs[1]==0x85);
    assert(logged("e=TX_DONE ") && !log_overflow);
    irq_flags=8;loop();assert(completed==1 && tx_starts==1); // stale TX IRQ
#endif
    cmd("X");loop();assert(parked && raw_regs[1]==0x81);
#if defined(LORA_ROLE_RECEIVER)
    assert(gpio_value[PIN_PA7]==LOW && gpio_value[PIN_PD5]==HIGH && gpio_value[PIN_PD6]==HIGH);
#endif
}
