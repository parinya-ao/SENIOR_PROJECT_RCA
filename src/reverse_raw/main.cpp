#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>
#include "generated/board_ssot.h"
#include "generated/arq_config.h"
#include "../arq/diagnostics.h"

static Module module(board_ssot.cs,board_ssot.irq,board_ssot.rst,board_ssot.dio1,
    SPI,SPISettings(ARQ_SPI_HZ,MSBFIRST,SPI_MODE0));
static SX1276 radio(&module);
static const uint8_t payload[]="Hello World";
static bool ready,active,used,attached;
static uint32_t started,matches;
static uint16_t observed_flags;
static uint8_t packet_events;
static char input_line[48];
static uint8_t input_length;
static bool input_overflow;
static void configuration(const char* name) {
    static const uint8_t addresses[]={0x42,0x01,0x06,0x07,0x08,0x09,0x4d,0x1d,0x1e,
        0x26,0x20,0x21,0x39,0x33,0x3b,0x11,0x40,0x41,0x0c,0x31,0x37,0x24,0x4b};
    char* out=log_slot();if(!out)return;
    int n=snprintf(out,192,"A t=%lu e=%s s=0 bytes=",(unsigned long)millis(),name);
    const char hex[]="0123456789ABCDEF";
    for(uint8_t address:addresses){uint8_t v=module.SPIreadRegister(address);out[n++]=hex[v>>4];out[n++]=hex[v&15];}
    out[n++]='\n';out[n]=0;
}
static uint16_t counter(uint8_t address) {
    uint8_t high=module.SPIreadRegister(address),low=module.SPIreadRegister(address+1);
    uint8_t again=module.SPIreadRegister(address);
    if(high!=again)low=module.SPIreadRegister(address+1);
    return ((uint16_t)again<<8)|low;
}
static void observation(const char* name,uint16_t flags) {
    uint16_t headers=counter(0x14),packets=counter(0x16);
    uint8_t mode=module.SPIreadRegister(1),stat=module.SPIreadRegister(0x18),hop=module.SPIreadRegister(0x1c);
    char* out=log_slot();if(out)snprintf(out,192,
        "A t=%lu e=%s s=0 rc=0 flags=%u headers=%u packets=%u mode=%u stat=%u hop=%u seen=%u overflow=%lu\n",
        (unsigned long)millis(),name,flags,headers,packets,mode,stat,hop,observed_flags,(unsigned long)log_overflow);
}
static void event(const char* name,int16_t rc,uint16_t flags=0) {
    char* out=log_slot();if(out)snprintf(out,192,"A t=%lu e=%s s=0 rc=%d flags=%u overflow=%lu\n",
        (unsigned long)millis(),name,rc,flags,(unsigned long)log_overflow);
}
static void stop() {
    int16_t rc=radio.standby();active=false;if(rc)ready=false;event("RAW_STANDBY",rc);
}
static void status() {
    char* out=log_slot();if(out)snprintf(out,192,"A t=%lu e=IDENTITY s=0 build=%s config=%s\n",
        (unsigned long)millis(),LORA_BUILD_ID,ARQ_CONFIG_HASH);
    event("RAW_STATUS",ready?0:-1);
    configuration("RAW_CONFIG");
}
static void command(const char* text) {
    if(!strcmp(text,"STATUS")){status();return;}
    if(!strcmp(text,"X")){used=true;stop();return;}
    if(!ready || active || used){event("RAW_REJECT",-1);return;}
#if defined(LORA_ROLE_RECEIVER)
    if(strcmp(text,"SEND 48656C6C6F20576F726C64")){event("RAW_REJECT",-1);return;}
    configuration("RAW_TX_PRE");
    used=true;int16_t rc=radio.startTransmit(payload,11);active=!rc;started=millis();
    event("RAW_TX",rc,11);
    configuration("RAW_TX_STATE");
    if(rc){radio.finishTransmit();stop();}
#else
    if(strcmp(text,"RX")){event("RAW_REJECT",-1);return;}
    used=true;int16_t rc=radio.startReceive();active=!rc;started=millis();
    if(!rc){configuration("RAW_RX_ACTIVE");observation("RAW_RX_READY",radio.getIRQFlags());}
    else event("RAW_RX_READY",rc);
    if(rc)stop();
#endif
}
static void command_byte(char c) {
    if(c=='\r')return;
    if(c=='\n'){
        input_line[input_length]=0;
        if(input_overflow)event("RAW_REJECT",-1);else command(input_line);
        input_length=0;input_overflow=false;return;
    }
    if(input_length>=sizeof(input_line)-1){input_overflow=true;return;}
    input_line[input_length++]=c;
}
void onPreMain(){_PROTECTED_WRITE(CPUINT.CTRLA,0);}
void setup() {
    board_ssot_init();delay(10);
    if(!SPI.swap(ARQ_SPI_ROUTE))return;
    SPI.begin();radio.reset();
    int16_t rc=radio.begin(ARQ_FREQUENCY_HZ/1000000.0f,ARQ_BANDWIDTH_KHZ,
        ARQ_SPREADING_FACTOR,ARQ_CODING_RATE,ARQ_SYNC_WORD,ARQ_TX_POWER_DBM,
        ARQ_PREAMBLE_SYMBOLS,0);
    // RadioLib leaves the reset-default LF bank selected; clear only bit 3 for 915 MHz.
    if(!rc)rc=module.SPIsetRegValue(RADIOLIB_SX127X_REG_OP_MODE,0,3,3);
    if(!rc)rc=radio.setOutputPower(ARQ_TX_POWER_DBM,false);
    if(!rc)rc=radio.explicitHeader();
    if(!rc)rc=radio.setCRC(true);
    if(!rc)rc=radio.invertIQ(false);
    if(!rc)rc=radio.standby();
    ready=!rc;
}
void loop() {
    if(updi_uart_enabled() && !attached)status();attached=updi_uart_enabled();
    if(updi_uart_rx_poll())command_byte(updi_uart_rx());
    if(active){
        uint16_t flags=radio.getIRQFlags();
        observed_flags|=flags;
#if defined(LORA_ROLE_RECEIVER)
        bool done=flags&RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE;
        if(done || millis()-started>=3000){
            int16_t rc=radio.finishTransmit();event(done?"RAW_TX_DONE":"RAW_TX_TIMEOUT",rc,flags);stop();
        }
#else
        if(module.SPIreadRegister(1)%8!=5){event("RAW_RADIO_ERROR",-1,flags);stop();}
        if(active && (flags&0x10) && !(observed_flags&0x100)){
            observed_flags|=0x100;observation("RAW_VALID_HEADER",flags);
        }
        if(active && (flags&RADIOLIB_SX127X_CLEAR_IRQ_FLAG_RX_DONE)){
            observation("RAW_RX_DONE",flags);++packet_events;
            int16_t rc=radio.standby();size_t length=radio.getPacketLength();uint8_t bytes[32]={0};
            if(!rc)rc=radio.readData(bytes,sizeof bytes);
            bool valid=!rc && !(flags&RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR) && length==11 && !memcmp(bytes,payload,11);
            if(valid)++matches;
            char* out=log_slot();if(out){
                int n=snprintf(out,192,"A t=%lu e=RAW_RX s=0 rc=%d flags=%u len=%u match=%u rssi=%d snr=%d bytes=",
                    (unsigned long)millis(),rc,flags,(unsigned)length,valid,(int)(radio.getRSSI()*100),(int)(radio.getSNR()*100));
                const char hex[]="0123456789ABCDEF";
                for(size_t i=0;i<length && i<sizeof bytes;i++){out[n++]=hex[bytes[i]>>4];out[n++]=hex[bytes[i]&15];}
                out[n++]='\n';out[n]=0;
            }
            if(valid || packet_events>=2 || (rc && rc!=RADIOLIB_ERR_CRC_MISMATCH))stop();
            else{rc=radio.startReceive();if(rc){ready=false;stop();}}
        }
        if(active && millis()-started>=15000){observation("RAW_RX_TIMEOUT",flags);stop();}
#endif
    }
    log_flush();
}
