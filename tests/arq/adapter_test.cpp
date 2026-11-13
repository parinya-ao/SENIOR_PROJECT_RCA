#include "../../src/arq/main.cpp"
#include <assert.h>
const arq_board board_ssot={3,4,5,6};
void board_ssot_init(void) {}
static void send_command(const char* s){for(;*s;s++) command_byte(*s);command_byte('\n');}
int main(int argc,char** argv) {
    if(argc>1){
        if(!strcmp(argv[1],"begin"))init_status=-1;
        if(!strcmp(argv[1],"power"))power_status=-1;
        if(!strcmp(argv[1],"header"))header_status=-1;
        if(!strcmp(argv[1],"crc"))crc_status=-1;
        if(!strcmp(argv[1],"iq"))iq_status=-1;
        if(!strcmp(argv[1],"standby"))standby_status=-1;
        setup();
        if(!strcmp(argv[1],"rx")){assert(ready);rx_status=-1;send_command("ARM 12345678");}
        assert(!ready);return 0;
    }
    setup();assert(ready && !sender.armed && !receiver.armed);
    assert(parked && rx_starts==0);
    status();
    bool registers_seen=false;
    for(uint8_t i=0;i<log_count;i++)if(strstr(log_slots[i].text,"e=REG "))registers_seen=true;
    assert(registers_seen);
    assert(strstr(log_slots[(log_tail+15)%16].text,"e=STATUS_END "));
    bool dio_mapping_seen=false;
    for(uint8_t i=0;i<log_count;i++)if(strstr(log_slots[i].text,"e=REG ") && strlen(strstr(log_slots[i].text,"bytes=")+6)==41)dio_mapping_seen=true;
    assert(dio_mapping_seen);
    log_head=log_tail=log_count=log_offset=0;
    loop();assert(!tx_starts);
    send_command("SEND 48656C6C6F20576F726C64");assert(!tx_starts);
    send_command("ARM 12345678");assert(sender.armed || receiver.armed);
    assert(!parked && rx_starts==1);
    send_command("ARM 12345678garbage");
#if defined(LORA_ROLE_SENDER)
    send_command("SEND 48656C6C6F20576F726C64");loop();
    assert(tx_starts==1 && sent_length==23);
    send_command("ARM 00000001");assert(sender.session==0x12345678);
    irq_flags=8;loop();assert(sender.state==ARQ_WAITING_ACK);
    arq_frame ack={ARQ_ACK,2,1,0x12345678,0,0,0,{0}};
    packet_length=arq_encode(&ack,packet,44);irq_flags=0x40;
    clock_ms=sender.retry_at;loop();assert(sender.state==ARQ_DELIVERED);
    send_command("X");send_command("SEND 00");assert(sender.state==ARQ_DELIVERED);
    loop();assert(parked && !radio_tx);
#else
    arq_frame data={ARQ_DATA,1,2,0x12345678,0,11,0,{0}};memcpy(data.payload,"Hello World",11);
    const size_t invalid_lengths[]={0,11,45,255};
    for(size_t length: invalid_lengths){
        packet_length=length;irq_flags=0x40;int starts=rx_starts;loop();
        assert(receiver.deliveries==0 && rx_starts==starts+1);
    }
    packet_length=arq_encode(&data,packet,44);data_status=-7;irq_flags=0x60;loop();
    assert(receiver.deliveries==0 && crc_errors==1);data_status=0;
    log_head=log_tail=log_count=log_offset=0;log_overflow=0;
    send_command("FAULT 1 1");
    packet_length=arq_encode(&data,packet,44);irq_flags=0x40;loop();
    assert(receiver.deliveries==1 && suppressed==1 && tx_starts==0);
    packet_length=arq_encode(&data,packet,44);irq_flags=0x40;loop();
    assert(receiver.duplicates==1);
    send_command("ARM 12345678");
    assert(strstr(log_slots[(log_tail+15)%16].text,"e=ARM "));
    clock_ms+=ARQ_RESPONSE_GUARD_MS;loop();
    assert(tx_starts==1 && sent_length==12);
    cleanup_status=-1;irq_flags=8;loop();assert(receiver.deliveries==1 && !ready);
    cleanup_status=0;ready=true;
    send_command("ARM 12345679");
    assert(generated==0 && suppressed==0 && attempted==0 && completed==0);
    assert(receiver.deliveries==0 && receiver.duplicates==0);
#endif
    /* Full ring and disconnected/busy logger may lose evidence, never stall RF. */
    for(int i=0;i<32;i++)event("TEST",0,0);
    assert(log_overflow>0);monitor=true;registers[1]=1;
    uint32_t before=clock_ms;loop();assert(clock_ms-before<20);
    send_command("ARM zzzzzzzz");
    for(int i=0;i<200;i++)command_byte('A');command_byte('\n');
    return 0;
}
