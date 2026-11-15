#include "../../src/arq/main.cpp"
#include <assert.h>
#include "../../src/arq/board_ssot.c"
static void send_command(const char* s){for(;*s;s++) command_byte(*s);command_byte('\n');}
static void drain_status(char* out,size_t capacity,bool interrupt_rx=false){
    bool previous_monitor=monitor,previous_attached=attached;monitor=attached=true;
    size_t length=0;
    for(unsigned i=0;i<20000 && (status_next || log_count);i++){
        if(interrupt_rx && i==600){packet_length=0;irq_flags=0xC2;}
        registers[0]=registers[1]=0;loop();
        if(registers[0]){assert(length+1<capacity);out[length++]=registers[0];}
    }
    assert(!status_next && !log_count);out[length]=0;
    monitor=previous_monitor;attached=previous_attached;
}
int main(int argc,char** argv) {
    if(argc>1 && !strcmp(argv[1],"status-rx-burst")) {
        setup();assert(ready);send_command("ARM 12345678");
        // Reproduce the physical RX_IRQ/LENGTH_DISCARD burst overlapping STATUS.
        packet_length=0;irq_flags=0xC2;loop();
        send_command("STATUS");
        assert(log_overflow==0);
        char output[8192];drain_status(output,sizeof output,true);
        assert(strstr(output,"e=STATUS_END ") && strstr(output,"e=REG "));
        assert(strstr(output,"e=RX_IRQ ") && rx_done==2 && raw_regs[1]==0x85);
        assert(log_overflow==0);
        return 0;
    }
#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC) && defined(LORA_ROLE_RECEIVER)
    USART2.CTRLA=USART2.CTRLB=0xff;
    gpio_mode[PIN_PF0]=gpio_mode[PIN_PF1]=OUTPUT;
    gpio_value[PIN_PF0]=gpio_value[PIN_PF1]=HIGH;
    if(argc>1 && !strcmp(argv[1],"card")){
        sd_inserted=true;setup();
        assert(!ready && !begun && !tx_starts);
        assert(gpio_value[PIN_PA7]==HIGH);
        assert(gpio_mode[PIN_PC3]==INPUT && gpio_value[PIN_PC3]==LOW);
        assert(gpio_value[PIN_PD6]==HIGH && gpio_mode[PIN_PD6]==OUTPUT);
        assert(reset_flags==GPR_GPR0);return 0;
    }
#endif
#if defined(LORA_ROLE_SENDER)
    if(argc>1 && !strcmp(argv[1],"ack-sequences")) {
        setup();send_command("ARM 12345678");
        const uint16_t sequences[]={0,1,32768,65535};
        for(uint16_t seq:sequences) {
            sender.sequence=seq;clock_ms+=ARQ_SPACING_MS;
            send_command("SEND 48656C6C6F20576F726C64");loop();
            irq_flags=8;loop();assert(sender.state==ARQ_WAITING_ACK);
            arq_frame ack={ARQ_ACK,2,1,0x12345678,seq,0,0,{0}};
            packet_length=arq_encode(&ack,packet,44);irq_flags=0x40;
            log_head=log_tail=log_count=log_offset=0;loop();
            assert(sender.state==ARQ_DELIVERED && sender.sequence==(uint16_t)(seq+1));
            char expected[20];snprintf(expected,sizeof expected," q=%u ",seq);
            unsigned deliveries=0;
            for(uint8_t i=0;i<log_count;i++)if(strstr(log_slots[i].text,"e=DELIVERED ")) {
                assert(strstr(log_slots[i].text,expected));++deliveries;
            }
            assert(deliveries==1);
            log_head=log_tail=log_count=log_offset=0;
            irq_flags=0x40;loop();
            for(uint8_t i=0;i<log_count;i++)assert(!strstr(log_slots[i].text,"e=DELIVERED "));
        }
        assert(sender.used_up && sender.sequence==0);return 0;
    }
    if(argc>1 && !strcmp(argv[1],"expired-ack")) {
        setup();send_command("ARM 12345678");
        send_command("SEND 48656C6C6F20576F726C64");loop();
        irq_flags=8;loop();assert(sender.state==ARQ_WAITING_ACK);
        arq_frame ack={ARQ_ACK,2,1,0x12345678,0,0,0,{0}};
        packet_length=arq_encode(&ack,packet,44);irq_flags=0x40;
        log_head=log_tail=log_count=log_offset=0;
        clock_ms=sender.terminal_at;loop();
        assert(sender.state==ARQ_FAILED && sender.result==ARQ_TIMEOUT_EXHAUSTED && sender.sequence==0);
        bool failure_seen=false;
        for(uint8_t i=0;i<log_count;i++) {
            assert(!strstr(log_slots[i].text,"e=DELIVERED "));
            if(strstr(log_slots[i].text,"e=TIMEOUT_EXHAUSTED ") && strstr(log_slots[i].text," q=0 "))failure_seen=true;
        }
        assert(failure_seen && tx_starts==1);return 0;
    }
#endif
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
    assert(raw_regs[1]==0x81); // Standby keeps the mode bits while clearing only the HF/LF selector.
#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC) && defined(LORA_ROLE_RECEIVER)
    assert(!USART2.CTRLA && !USART2.CTRLB);
    assert(gpio_mode[PIN_PF0]==INPUT && gpio_mode[PIN_PF1]==INPUT);
    assert(!gpio_value[PIN_PF0] && !gpio_value[PIN_PF1]);
    assert(gpio_value[PIN_PD5]==HIGH && gpio_mode[PIN_PD5]==OUTPUT);
    assert(gpio_value[PIN_PD6]==HIGH && gpio_mode[PIN_PD6]==OUTPUT);
    assert(gpio_mode[PIN_PA4]==INPUT_PULLUP);
    assert(gpio_value[PIN_PA7]==LOW && gpio_mode[PIN_PA7]==OUTPUT);
    assert(gpio_value[PIN_PC3]==HIGH && gpio_mode[PIN_PC3]==OUTPUT);
    assert(reset_flags==GPR_GPR0);
#endif
    assert(parked && rx_starts==0);
    status();
    char output[8192];drain_status(output,sizeof output);
    assert(strstr(output,"e=REG ") && strstr(output,"e=STATUS_END "));
    const char* register_bytes=strstr(strstr(output,"e=REG "),"bytes=")+6;
    assert(strchr(register_bytes,'\n')-register_bytes==48);
    log_head=log_tail=log_count=log_offset=0;
    /* Polling diagnostics survive destructive driver reads and logger loss. */
    unsigned observed_before=rx_done;
    loop();assert(!tx_starts);
    send_command("SEND 48656C6C6F20576F726C64");assert(!tx_starts);
    send_command("ARM 12345678");assert(sender.armed || receiver.armed);
    assert(!parked && rx_starts==1);
    assert(raw_regs[1] == 0x85); // LoRa RX continuous, HF band, no LF register bank.
    send_command("ARM 12345678garbage");
#if defined(LORA_ROLE_SENDER)
    send_command("SEND 48656C6C6F20576F726C64");loop();
    assert(tx_starts==1 && sent_length==23);
    assert(raw_regs[1]==0x83);
    send_command("ARM 00000001");assert(sender.session==0x12345678);
    irq_flags=8;loop();assert(sender.state==ARQ_WAITING_ACK);
    assert(raw_regs[1]==0x85);
    arq_frame ack={ARQ_ACK,2,1,0x12345678,0,0,0,{0}};
    for(int bad=0;bad<5;bad++){
        arq_frame rejected=ack;
        if(bad==0)rejected.src=7;
        if(bad==1)rejected.session++;
        if(bad==2)rejected.sequence++;
        if(bad==3)rejected.type=ARQ_DATA;
        packet_length=arq_encode(&rejected,packet,44);
        if(bad==4)packet[0]=0xff;
        log_head=log_tail=log_count=log_offset=0;
        int starts=rx_starts;irq_flags=0x40;loop();
        assert(sender.state==ARQ_WAITING_ACK && rx_starts==starts+1 && !irq_flags);
    }
    assert(control_rejects==4 && decode_errors==1);
    packet_length=arq_encode(&ack,packet,44);irq_flags=0x40;
    clock_ms=sender.retry_at;loop();assert(sender.state==ARQ_DELIVERED);
    bool delivered_sequence_seen=false;
    for(uint8_t i=0;i<log_count;i++)
        if(strstr(log_slots[i].text,"e=DELIVERED ") && strstr(log_slots[i].text," q=0 "))delivered_sequence_seen=true;
    assert(delivered_sequence_seen);
    assert(rx_done==observed_before+6 && last_rx_flags==0x40);
    send_command("X");send_command("SEND 00");assert(sender.state==ARQ_DELIVERED);
    loop();assert(parked && !radio_tx);
#else
    arq_frame data={ARQ_DATA,1,2,0x12345678,0,sizeof(ARQ_PAYLOAD)-1,0,{0}};memcpy(data.payload,ARQ_PAYLOAD,sizeof(ARQ_PAYLOAD)-1);
    const size_t invalid_lengths[]={0,11,45,255};
    for(size_t length: invalid_lengths){
        packet_length=length;irq_flags=0x40;int starts=rx_starts;loop();
        assert(receiver.deliveries==0 && rx_starts==starts+1);
    }
    packet_length=arq_encode(&data,packet,44);data_status=-7;irq_flags=0x60;loop();
    assert(receiver.deliveries==0 && crc_errors==1);data_status=0;
    assert(rx_done==observed_before+5 && last_rx_flags==0x60);
    assert(irq_flags==0);
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
    assert(raw_regs[1]==0x83);
    assert(gpio_value[PIN_PA7]==LOW);
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
