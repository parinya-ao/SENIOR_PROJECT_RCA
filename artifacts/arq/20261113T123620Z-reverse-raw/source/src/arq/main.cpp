#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>
#include <stdlib.h>
#include "arq.h"
#include "generated/board_ssot.h"
#include "diagnostics.h"

static Module module(board_ssot.cs,board_ssot.irq,board_ssot.rst,board_ssot.dio1,
    SPI,SPISettings(ARQ_SPI_HZ,MSBFIRST,SPI_MODE0));
static SX1276 radio(&module);
static arq_sender sender;
static arq_receiver receiver;
static bool ready,radio_tx,response_wait,attached,command_overflow,parked;
static uint8_t wire[44],wire_length,reset_flags;
static uint32_t tx_started,response_at;
static uint32_t generated,suppressed,attempted,completed,crc_errors;
static uint32_t rx_done,decode_errors,control_rejects;
static uint16_t last_rx_flags;
static uint16_t fault_stride,fault_budget;
static char command_buffer[80];
static uint8_t command_length;
static int16_t startup_status;

static uint32_t session() {
#if defined(LORA_ROLE_SENDER)
    return sender.session;
#else
    return receiver.session;
#endif
}
static uint16_t sequence() {
#if defined(LORA_ROLE_SENDER)
    return sender.frame.sequence;
#else
    return receiver.last_sequence;
#endif
}
static void event(const char* name,int16_t rc,uint32_t value) {
    char* out=log_slot();if(!out)return;
    snprintf(out,192,"A t=%lu e=%s s=%08lX q=%u a=%u rc=%d v=%lu\n",
        (unsigned long)millis(),name,(unsigned long)session(),sequence(),sender.attempts,rc,(unsigned long)value);
}
static void frame_event(const char* name,const uint8_t* bytes,size_t length,int16_t rssi,int16_t snr) {
    char* out=log_slot();if(!out)return;
    int n=snprintf(out,192,"A t=%lu e=%s s=%08lX q=%u rssi=%d snr=%d bytes=",
        (unsigned long)millis(),name,(unsigned long)session(),sequence(),rssi,snr);
    static const char hex[]="0123456789ABCDEF";
    for(size_t i=0;i<length && n<188;i++){out[n++]=hex[bytes[i]>>4];out[n++]=hex[bytes[i]&15];}
    out[n++]='\n';out[n]=0;
}
static void register_state(const char* name) {
    static const uint8_t addresses[]={0x01,0x06,0x07,0x08,0x09,0x4d,0x1d,0x1e,
        0x26,0x39,0x33,0x3b,0x12,0x13,0x10,0x1b,0x40,0x11,0x18,0x31};
    uint8_t values[sizeof addresses];
    for(uint8_t i=0;i<sizeof addresses;i++){
        SPI.beginTransaction(SPISettings(ARQ_SPI_HZ,MSBFIRST,SPI_MODE0));
        digitalWrite(board_ssot.cs,LOW);SPI.transfer(addresses[i]);values[i]=SPI.transfer(0);
        digitalWrite(board_ssot.cs,HIGH);SPI.endTransaction();
    }
    frame_event(name,values,sizeof values,0,0);
}
static void rx_diagnostics(const char* name,uint16_t flags) {
    // Snapshot band counters before startReceive resets their observation window.
    uint8_t values[6]={(uint8_t)(flags>>8),(uint8_t)flags,0,0,0,0};
    for(uint8_t i=0;i<4;i++){
        SPI.beginTransaction(SPISettings(ARQ_SPI_HZ,MSBFIRST,SPI_MODE0));
        digitalWrite(board_ssot.cs,LOW);SPI.transfer(0x14+i);values[2+i]=SPI.transfer(0);
        digitalWrite(board_ssot.cs,HIGH);SPI.endTransaction();
    }
    frame_event(name,values,sizeof values,0,0);
}
static void discard(const char* name,const arq_frame* f,uint8_t reason) {
    char* out=log_slot();if(!out)return;
    snprintf(out,192,"A t=%lu e=%s s=%08lX q=%u rc=%u src=%u dst=%u rs=%08lX rq=%u type=%u\n",
        (unsigned long)millis(),name,(unsigned long)session(),sequence(),reason,
        f->src,f->dst,(unsigned long)f->session,f->sequence,f->type);
}
static void status() {
    event("BOOT",startup_status,reset_flags);
    char* identity=log_slot();if(identity)snprintf(identity,192,"A t=%lu e=IDENTITY s=%08lX build=%s config=%s\n",
        (unsigned long)millis(),(unsigned long)session(),LORA_BUILD_ID,ARQ_CONFIG_HASH);
    char* out=log_slot();if(out)snprintf(out,192,
        "A t=%lu e=STATUS s=%08lX app=%lu dup=%lu gen=%lu sup=%lu att=%lu done=%lu crc=%lu overflow=%lu ready=%u\n",
        (unsigned long)millis(),(unsigned long)session(),(unsigned long)receiver.deliveries,
        (unsigned long)receiver.duplicates,(unsigned long)generated,(unsigned long)suppressed,
        (unsigned long)attempted,(unsigned long)completed,(unsigned long)crc_errors,
        (unsigned long)log_overflow,ready);
    event("RESULT",sender.result,sender.state);
    event("RTT_LAST",0,sender.rtt_last);
    event("RTT_MIN",0,sender.rtt_min);event("RTT_MAX",0,sender.rtt_max);
    event("RTT_COUNT",0,sender.rtt_count);
    event("RX_DONE_COUNT",0,rx_done);event("DECODE_ERRORS",0,decode_errors);event("CONTROL_REJECTS",0,control_rejects);
    if(ready){
        // Read-only register evidence separates RX mode/configuration from RF path failure.
        register_state("REG");
    }
    event("STATUS_END",0,log_overflow);
}
static bool rx_restore() {
    receiver.state=ARQ_RETURNING_TO_RX; // RX restoration is checked after every response/error.
    rx_diagnostics("RX_RESTART",radio.getIRQFlags());
    int16_t rc=radio.startReceive();
    event("RX_READY",rc,0);
#if defined(LORA_ROLE_SENDER)
    if(!rc)register_state("RX_STATE");
#endif
    receiver.state=ARQ_LISTENING;
    if(rc){ready=false;event("RX_ERROR",rc,0);}
    else parked=false;
    return !rc;
}
static void fatal(int16_t rc) {
    ready=false;event("ADAPTER_ERROR",rc,0);
    if(arq_sender_active(&sender)){
        // Fatal adapter errors terminate even if the sender was waiting in RX.
        sender.state=ARQ_FAILED;sender.result=ARQ_RADIO_ERROR;sender.used_up=true;
    }
}
static int unhex(char c) {
    if(c>='0' && c<='9')return c-'0';
    if(c>='A' && c<='F')return c-'A'+10;
    if(c>='a' && c<='f')return c-'a'+10;
    return -1;
}
static void command(const char* text) {
    if(!strcmp(text,"STATUS")){status();return;}
    if(!strcmp(text,"X")){arq_sender_stop(&sender);receiver.stopped=true;event("STOP",0,0);return;}
    if(!strncmp(text,"ARM ",4) && strlen(text)==12){
        uint32_t value=0;
        for(uint8_t i=4;i<12;i++){int c=unhex(text[i]);if(c<0){event("COMMAND_ERROR",-1,0);return;}value=(value<<4)|c;}
        bool ok=false;uint32_t previous=session();
#if defined(LORA_ROLE_SENDER)
        ok=arq_sender_arm(&sender,value);
#else
        if(receiver.armed && receiver.session==value)ok=true;
        else if(!radio_tx && !response_wait)ok=arq_receiver_arm(&receiver,value);
#endif
        if(ok && previous!=value){
            generated=suppressed=attempted=completed=crc_errors=0;
            rx_done=decode_errors=control_rejects=0;last_rx_flags=0;
            fault_stride=fault_budget=0;
        }
        if(ok && ready && parked){
#if defined(LORA_ROLE_SENDER)
            if(!sender.stopped)ok=rx_restore();
#else
            if(!receiver.stopped)ok=rx_restore();
#endif
        }
        event(ok?"ARM":"ARM_REJECT",ready?0:-1,value);return;
    }
#if defined(LORA_ROLE_SENDER)
    if(!strncmp(text,"SEND ",5)){
        size_t n=strlen(text+5);uint8_t bytes[32];
        if(n>64 || (n&1)){event("COMMAND_ERROR",-1,0);return;}
        for(size_t i=0;i<n;i+=2){int a=unhex(text[5+i]),b=unhex(text[6+i]);
            if(a<0 || b<0){event("COMMAND_ERROR",-1,0);return;}bytes[i/2]=(a<<4)|b;}
        uint32_t rto=ARQ_ACK_MIN_MS+(uint32_t)random(ARQ_ACK_MAX_MS-ARQ_ACK_MIN_MS+1);
        bool ok=ready && arq_sender_request(&sender,bytes,n/2,millis(),rto);
        event(ok?"REQUEST":"SEND_REJECT",0,rto);return;
    }
#elif defined(ARQ_TEST_MODE)
    if(!strncmp(text,"FAULT ",6)){
        unsigned stride,budget;char extra;
        if(sscanf(text+6,"%u %u %c",&stride,&budget,&extra)==2 && stride<=100 && budget<=100 &&
           !radio_tx && !response_wait && (!budget || stride)){
            fault_stride=stride;fault_budget=budget;event("FAULT",0,budget);return;
        }
    }
#endif
    event("COMMAND_ERROR",-1,0);
}
static void command_byte(char c) {
    if(c=='\r')return;
    if(c=='\n'){
        if(!command_overflow){command_buffer[command_length]=0;command(command_buffer);}
        else event("COMMAND_ERROR",-1,0);
        command_length=0;command_overflow=false;return;
    }
    if(command_length>=sizeof(command_buffer)-1){command_overflow=true;return;}
    command_buffer[command_length++]=c;
}
void onPreMain(){_PROTECTED_WRITE(CPUINT.CTRLA,0);}
void setup() {
    arq_sender_init(&sender);arq_receiver_init(&receiver);reset_flags=GPR_GPR0;
    board_ssot_init();delay(10);
    if(!SPI.swap(ARQ_SPI_ROUTE)){startup_status=-1;return;}SPI.begin();radio.reset();
    bool supported=false;
    for(uint8_t i=0;i<3;i++){
        SPI.beginTransaction(SPISettings(ARQ_SPI_HZ,MSBFIRST,SPI_MODE0));
        digitalWrite(board_ssot.cs,LOW);SPI.transfer(0x42);uint8_t version=SPI.transfer(0);
        digitalWrite(board_ssot.cs,HIGH);SPI.endTransaction();
        supported=version==RADIOLIB_SX1278_CHIP_VERSION || version==RADIOLIB_SX1278_CHIP_VERSION_ALT ||
            version==RADIOLIB_SX1278_CHIP_VERSION_RFM9X;
        if(supported)break;delay(10);
    }
    int16_t rc=supported?0:RADIOLIB_ERR_CHIP_NOT_FOUND;
    if(!rc)rc=radio.begin(ARQ_FREQUENCY_HZ/1000000.0f,ARQ_BANDWIDTH_KHZ,
        ARQ_SPREADING_FACTOR,ARQ_CODING_RATE,ARQ_SYNC_WORD,ARQ_TX_POWER_DBM,ARQ_PREAMBLE_SYMBOLS,0);
    if(!rc)rc=radio.setOutputPower(ARQ_TX_POWER_DBM,false);
    if(!rc)rc=radio.explicitHeader();if(!rc)rc=radio.setCRC(ARQ_CRC_ENABLED);
    if(!rc)rc=radio.invertIQ(ARQ_IQ_INVERTED);
    if(!rc)rc=radio.standby();startup_status=rc;ready=!rc;parked=!rc;
    randomSeed(micros());
}
static void receive(uint32_t now,uint16_t flags) {
    ++rx_done;last_rx_flags=flags;rx_diagnostics("RX_IRQ",flags);
    int16_t rc=radio.standby();if(rc){fatal(rc);return;}
    size_t length=radio.getPacketLength();uint8_t bytes[44];
    if(length<12 || length>sizeof bytes){event("LENGTH_DISCARD",0,length);rx_restore();return;}
    rc=radio.readData(bytes,length);
    if(rc || (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR)){
        if(rc==RADIOLIB_ERR_CRC_MISMATCH || (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR))++crc_errors;
        event("RX_DISCARD",rc,flags);rx_restore();return;
    }
    frame_event("RX",bytes,length,(int16_t)(radio.getRSSI()*100),(int16_t)(radio.getSNR()*100));
    arq_frame frame;
    if(!arq_decode(&frame,bytes,length)){++decode_errors;event("DECODE_DISCARD",0,length);rx_restore();return;}
#if defined(LORA_ROLE_SENDER)
    uint8_t reason=0;
    if(frame.type!=ARQ_ACK && frame.type!=ARQ_NACK)reason=1;
    else if(frame.src!=ARQ_RECEIVER_ID || frame.dst!=ARQ_SENDER_ID)reason=2;
    else if(frame.session!=sender.session)reason=3;
    else if(frame.sequence!=sender.sequence)reason=4;
    else if((sender.state!=ARQ_WAITING_ACK && sender.state!=ARQ_BACKOFF) || !sender.attempts)reason=5;
    if(reason){++control_rejects;discard("CONTROL_DISCARD",&frame,reason);}
    arq_sender_control(&sender,&frame,now);if(!rx_restore())fatal(-1);
#else
    arq_frame response;uint32_t deliveries=receiver.deliveries;
    if(!arq_receiver_data(&receiver,&frame,&response,false)){discard("DATA_DISCARD",&frame,1);rx_restore();return;}
    ++generated;
    if(receiver.deliveries!=deliveries)event("ACCEPT",0,receiver.deliveries);
    else if(response.type==ARQ_ACK)event("DUPLICATE",0,receiver.duplicates);
#if defined(ARQ_TEST_MODE)
    if(receiver.deliveries!=deliveries && fault_budget && fault_stride && receiver.deliveries%fault_stride==0){
        --fault_budget;++suppressed;event("SUPPRESS",0,suppressed);rx_restore();return;
    }
#endif
    wire_length=arq_encode(&response,wire,sizeof wire);response_at=now+ARQ_RESPONSE_GUARD_MS;
    response_wait=true;receiver.state=ARQ_SENDING_RESPONSE; // Response guard precedes RF TX.
#endif
}
void loop() {
    if(updi_uart_enabled() && !attached)status();attached=updi_uart_enabled();
    if(updi_uart_rx_poll())command_byte(updi_uart_rx());
    uint32_t now=millis();arq_sender_state old=sender.state;
    if(ready && !parked){
        uint16_t flags=radio.getIRQFlags();
        if(radio_tx){
            bool done=flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE;
            if(done || now-tx_started>=ARQ_TX_MS){
                int16_t rc=radio.finishTransmit();radio_tx=false;
                event(done?"TX_DONE":"TX_TIMEOUT",rc,flags);
                bool rx=rx_restore();
#if defined(LORA_ROLE_SENDER)
                arq_sender_tx_done(&sender,millis(),done && !rc && rx);
                if(sender.state==ARQ_WAITING_ACK)sender.tx_done=now;
#else
                if(done && !rc)++completed;
#endif
                if(rc)fatal(rc);
            }
        }else if(!response_wait && (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_RX_DONE))receive(now,flags);
        // Read matching controls before evaluating deadlines or initiating a retry.
        if(sender.state==ARQ_WAITING_ACK && arq_due(now,sender.retry_at))rx_diagnostics("RX_TIMEOUT",radio.getIRQFlags());
        arq_sender_poll(&sender,now);
#if defined(LORA_ROLE_SENDER)
        bool start=sender.state==ARQ_TRANSMITTING && !radio_tx;
        if(start)wire_length=arq_encode(&sender.frame,wire,sizeof wire);
#else
        bool start=response_wait && arq_due(now,response_at);
#endif
        if(start && ready){
            response_wait=false;
            int16_t rc=radio.standby();if(!rc)rc=radio.startTransmit(wire,wire_length);
            ++attempted;
            if(rc){
                int16_t cleanup=radio.finishTransmit();bool rx=rx_restore();event("TX_ERROR",rc,cleanup);
#if defined(LORA_ROLE_SENDER)
                fatal(cleanup?cleanup:rc);
#else
                if(cleanup || !rx)fatal(cleanup?cleanup:rc);
#endif
            }
            else{radio_tx=true;tx_started=now;frame_event("TX",wire,wire_length,0,0);register_state("TX_STATE");}
        }
    }
    if(old!=sender.state && (sender.state==ARQ_DELIVERED || sender.state==ARQ_FAILED)){
        static const char* const names[]={"PENDING","DELIVERED","REJECTED","PROTOCOL_ERROR","TIMEOUT_EXHAUSTED","RADIO_ERROR"};
        event(names[sender.result],0,sender.attempts);
        if(sender.result==ARQ_OK && sender.attempts==1)event("RTT",0,sender.rtt_last);
    }
#if defined(LORA_ROLE_SENDER)
    bool stopped=sender.stopped;
#else
    bool stopped=receiver.stopped;
#endif
    if(ready && !parked && stopped && !radio_tx && !response_wait && !arq_sender_active(&sender)){
        // X parks only after the outstanding exchange terminates.
        int16_t rc=radio.standby();if(rc)fatal(rc);else parked=true;
        event("STANDBY",rc,0);if(!rc)register_state("PARKED");
    }
    log_flush();
}
