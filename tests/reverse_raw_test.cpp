#include "../src/reverse_raw/main.cpp"
#include <assert.h>
const arq_board board_ssot={3,4,5,6};
void board_ssot_init(void) {}
static void cmd(const char* s){for(;*s;s++)command_byte(*s);command_byte('\n');}
static const char* logged(const char* name){
    for(unsigned i=0;i<16;i++)if(strstr(log_slots[i].text,name))return log_slots[i].text;
    return "";
}
int main(int argc,char** argv){
    setup();assert(ready && !active && !tx_starts);
    if(argc>1){
#if defined(LORA_ROLE_SENDER)
        if(!strcmp(argv[1],"diagnostics")){
            cmd("RX");assert(strstr(logged("RAW_RX_READY"),"mode=141"));
            raw_regs[0x14]=0x12;raw_regs[0x15]=0x34;raw_regs[0x16]=0;raw_regs[0x17]=1;
            raw_regs[0x18]=0x10;raw_regs[0x1c]=0x40;
            memcpy(packet,"Hello World",11);packet_length=11;irq_flags=0x50;
            cmd("RX");assert(rx_starts==1 && irq_flags==0x50);
            clock_ms+=15001;loop();
            assert(matches==1 && !active && !irq_flags);
            assert(strstr(logged("RAW_RX_DONE"),"flags=80 headers=4660 packets=1"));
            assert(!*logged("RAW_RX_TIMEOUT"));assert(!log_overflow);return 0;
        }
        if(!strcmp(argv[1],"rx-error")){rx_status=-1;cmd("RX");assert(!active);return 0;}
        cmd("RX");
        if(!strcmp(argv[1],"timeout")){clock_ms+=15001;loop();assert(!active && !matches);
            assert(strstr(logged("RAW_RX_TIMEOUT"),"headers=0 packets=0"));return 0;}
        if(!strcmp(argv[1],"bad-length")){
            packet_length=255;irq_flags=0x40;loop();assert(active && !matches);cmd("X");return 0;
        }
#else
        if(!strcmp(argv[1],"tx-error")){
            tx_status=-1;cmd("SEND 48656C6C6F20576F726C64");assert(!active && cleanups==1);
            cmd("SEND 48656C6C6F20576F726C64");assert(tx_starts==1);return 0;
        }
        cmd("SEND 48656C6C6F20576F726C64");irq_flags=8;loop();assert(!active && cleanups==1);return 0;
#endif
    }
    cmd("SEND 00");assert(!tx_starts);
#if defined(LORA_ROLE_RECEIVER)
    cmd("SEND 48656C6C6F20576F726C64");assert(tx_starts==1 && sent_length==11);
    assert(!memcmp(sent,"Hello World",11));
    cmd("SEND 48656C6C6F20576F726C64");assert(tx_starts==1);
    clock_ms+=3001;loop();assert(!active && cleanups==1);
    cmd("SEND 48656C6C6F20576F726C64");assert(tx_starts==1);
#else
    cmd("RX");assert(active && rx_starts==1);
    memcpy(packet,"Hello World",11);packet_length=11;irq_flags=0x60;loop();
    assert(!matches && active);
    packet_length=11;irq_flags=0x40;loop();assert(matches==1 && !active);
    cmd("RX");assert(!active); // a run has exactly one bounded observation
#endif
    cmd("X");assert(!active);
}
