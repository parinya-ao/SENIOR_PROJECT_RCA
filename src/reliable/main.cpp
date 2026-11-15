#include <Arduino.h>
#include "hello_config.h"
#include "lora.h"
#include "role_log.h"
#include "reliable_transport.h"

#if defined(LORA_ROLE_RECEIVER)
#include "generated/lora_receiver_board.h"
static constexpr uint8_t local_address=LORA_RECEIVER_ADDRESS;
static constexpr uint8_t peer_address=LORA_SENDER_ADDRESS;
static const char role[]="RECEIVER";
static const char firmware[]="receiver";
void onPreMain() { _PROTECTED_WRITE(CPUINT.CTRLA,0); }
#else
#include "generated/lora_sender_board.h"
static constexpr uint8_t local_address=LORA_SENDER_ADDRESS;
static constexpr uint8_t peer_address=LORA_RECEIVER_ADDRESS;
static const char role[]="GATEWAY";
static const char firmware[]="sender_hello";
#endif

static LoRa lora;
static ReliableTransport<LoRa> transport(lora);
static bool radio_ready=false,boot_logged=false,reject_data=false;
static uint8_t version=0;
static int16_t init_error=-1;
static uint8_t application_starts=0;
#if defined(LORA_ROLE_RECEIVER)
static uint32_t heartbeat_at;
static bool heartbeat_on=true;
#endif
static ssot_control_input_t commands[3];
struct RecordedEvent {
    const char* name;
    uint32_t time;
    uint16_t session;
    int16_t error;
    uint8_t type,sequence,irq;
};
static RecordedEvent events[24];
static uint8_t head=0,count=0;
static uint16_t log_overflow=0, log_overflow_reported=0;
static uint8_t accepted_payload[SSOT_HELLO_PAYLOAD_SIZE];

static void record(void*,const char* event,uint8_t type,uint8_t sequence,int16_t error) {
    if(count==24) { if(log_overflow!=UINT16_MAX) ++log_overflow;return; }
    events[(head+count)%24]={event,millis(),transport.session(),error,type,sequence,lora.last_irq()};
    ++count;
}
static void flush_event() {
    if(!count || !updi_uart_enabled()) return;
    const RecordedEvent& e=events[head];
    char session[5],type[3],irq[3],line[120];
    updi_role_log_format_hex(session,e.session,4);
    updi_role_log_format_hex(type,e.type,2);
    updi_role_log_format_hex(irq,e.irq,2);
    const bool incoming=strstr(e.name,"_RX") || strstr(e.name,"ACCEPTED") ||
        !strcmp(e.name,"DATA_VALIDATED") || !strcmp(e.name,"DATA_DUP") ||
        !strcmp(e.name,"TRANSACTION_COMPLETE") ||
        (!strcmp(e.name,"TRANSACTION_FAILED") && e.type!=SSOT_DATA_TYPE);
    snprintf(line,sizeof line,"%s T=%lu SID=%s SRC=%u DST=%u TYPE=%s Q=%u E=%d IRQ=%s",
             e.name,static_cast<unsigned long>(e.time),session,
             incoming?peer_address:local_address,incoming?local_address:peer_address,
             type,e.sequence,e.error,irq);
    updi_role_log(role,line);
    if(!strcmp(e.name,"DATA_TX_BEGIN"))
        updi_role_log_payload(role,"DATA_PAYLOAD",e.session,e.sequence,
            reinterpret_cast<const uint8_t*>(LORA_HELLO_PAYLOAD),SSOT_HELLO_PAYLOAD_SIZE);
    if(!strcmp(e.name,"DATA_VALIDATED"))
        updi_role_log_payload(role,"PAYLOAD_BYTES",e.session,e.sequence,
                              accepted_payload,sizeof accepted_payload);
    head=(head+1)%24;--count;
}

static bool accept_data(void*,uint16_t,uint8_t,const uint8_t* data,uint8_t length) {
    // FOTA can bind its staging+integrity callback here; this application is RAM-only.
    if(reject_data || length!=SSOT_HELLO_PAYLOAD_SIZE ||
       memcmp(data,LORA_HELLO_PAYLOAD,length)) return false;
    memcpy(accepted_payload,data,length);return true;
}

static void init_gpio() {
#if defined(LORA_ROLE_RECEIVER)
    digitalWriteFast(LORA_PIN_ENABLE,!LORA_POWER_ACTIVE_LEVEL);
    digitalWriteFast(LORA_PIN_GPS_ENABLE,HIGH);
    digitalWriteFast(LORA_PIN_SD_ENABLE,HIGH);
    pinModeFast(LORA_PIN_ENABLE,OUTPUT);
    pinModeFast(LORA_PIN_GPS_ENABLE,OUTPUT);
    pinModeFast(LORA_PIN_SD_ENABLE,OUTPUT);
    pinModeFast(LORA_PIN_SD_DETECT,INPUT);
    pinModeFast(LORA_PIN_RST,INPUT);
    digitalWriteFast(LORA_PIN_LED1,HIGH);digitalWriteFast(LORA_PIN_LED2,HIGH);
    pinModeFast(LORA_PIN_LED1,OUTPUT);pinModeFast(LORA_PIN_LED2,OUTPUT);
    digitalWriteFast(LORA_PIN_SD_CS,HIGH);pinModeFast(LORA_PIN_SD_CS,OUTPUT);
    digitalWriteFast(LORA_PIN_ENABLE,LORA_POWER_ACTIVE_LEVEL);
    delay(10);
#endif
    pinModeFast(LORA_PIN_IRQ,INPUT);pinModeFast(LORA_PIN_DIO1,INPUT);
    digitalWriteFast(LORA_PIN_CS,HIGH);pinModeFast(LORA_PIN_CS,OUTPUT);
}

void setup() {
    if(application_starts!=UINT8_MAX) ++application_starts;
    ssot_control_input_init(&commands[0],'R');
    ssot_control_input_init(&commands[1],'S');
    ssot_control_input_init(&commands[2],'N');
    transport.on_event(record,nullptr);
    init_gpio();
    init_error=lora.read_chip_version(&version);
#if !HELLO_RF_DIAGNOSTIC_ONLY
    if(!init_error && LoRa::is_supported_chip_version(version)) {
        radio_ready=lora.init(local_address);init_error=lora.last_error();
    }
#endif
#if defined(LORA_ROLE_RECEIVER)
    heartbeat_at=millis();digitalWriteFast(LORA_PIN_LED1,LOW);
#endif
}

static void status() {
#if defined(LORA_NONBLOCKING_LOG) && LORA_NONBLOCKING_LOG
    char drops[48];
    snprintf(drops,sizeof drops,"LOG_DROPPED E=%u Q=%u",
             static_cast<unsigned>(log_overflow),static_cast<unsigned>(updi_role_log_dropped()));
    updi_role_log(role,drops);
#endif
    static const uint8_t addresses[]={0x42,0x01,0x06,0x07,0x08,0x12,0x1d,0x1e,
        0x26,0x39,0x20,0x21,0x33,0x3b,0x40,0x0d,0x22,0x09,0x4d,0x0b};
    for(uint8_t address:addresses) {
        char reg[3],value[3],line[24];
        updi_role_log_format_hex(reg,address,2);
        updi_role_log_format_hex(value,lora.read_register(address),2);
        snprintf(line,sizeof line,"REG A=%s V=%s",reg,value);updi_role_log(role,line);
    }
}

void loop() {
#if defined(LORA_ROLE_RECEIVER)
    // LED1 is an independent, nonblocking main-loop heartbeat.
    const uint32_t heartbeat_now=millis();
    if(heartbeat_now-heartbeat_at >= (heartbeat_on ? 50U : 950U)) {
        heartbeat_at=heartbeat_now;heartbeat_on=!heartbeat_on;
        digitalWriteFast(LORA_PIN_LED1,heartbeat_on ? LOW : HIGH);
    }
#endif
#if defined(LORA_NONBLOCKING_LOG) && LORA_NONBLOCKING_LOG
    updi_role_log_service();
#endif
    if(!boot_logged && updi_uart_enabled()) {
        char start_count[24];
        snprintf(start_count,sizeof start_count,"APP_START N=%u",static_cast<unsigned>(application_starts));
        updi_role_log(role,start_count);
        updi_role_log_identity(role,firmware,__DATE__,__TIME__);
        updi_role_log_boot(role,firmware,__DATE__,__TIME__);
        updi_role_log(role,"BUILD_ID=" LORA_BUILD_ID);
        updi_role_log(role,"TRANSPORT=SSOT_SYMMETRIC_V1");
        updi_role_log(role,"CONFIG_FINGERPRINT=" LORA_CONFIG_FINGERPRINT);
        updi_role_log(role,"PROTOCOL_VERSION=" LORA_PROTOCOL_VERSION_TEXT);
        updi_role_log_radio_version(role,version);
#if HELLO_RF_DIAGNOSTIC_ONLY
        updi_role_log(role,"RADIO_INIT_SKIPPED_DIAGNOSTIC");
        updi_role_log(role,"RF_TX_DISABLED_DIAGNOSTIC");
#else
        updi_role_log_status(role,radio_ready?"RADIO_INIT_OK":"RADIO_INIT_FAILED",init_error);
        if(radio_ready) {
            updi_role_log_status(role,"RADIO_INIT",0);
            updi_role_log(role,"RADIO_READY");
            updi_role_log_radio_profile(role,HELLO_RF_FREQUENCY_MHZ,HELLO_RF_TX_POWER_DBM,
                HELLO_RF_SPREADING_FACTOR,HELLO_RF_BANDWIDTH_KHZ,HELLO_RF_CODING_RATE,
                HELLO_RF_SYNC_WORD,HELLO_RF_PREAMBLE_SYMBOLS,HELLO_RF_CRC_ENABLED,
                HELLO_RF_IQ_INVERTED);
#if defined(LORA_ROLE_RECEIVER)
            updi_role_log(role,"WAIT_SESSION");
#else
            updi_role_log(role,"WAIT_START");
#endif
        }
#endif
        boot_logged=true;
    }
    transport.poll(millis());
    if(updi_uart_rx_poll()) {
        const char c=updi_uart_rx();
        if(c=='P') {
            init_error=transport.stop();radio_ready=false;
            updi_role_log_status(role,"PARKED",init_error);
        } else if(!transport.active() && c=='?') status();
        else if(!transport.active() && !count) {
            uint16_t session;
            for(uint8_t i=0;i<3;++i) {
                if(!ssot_control_input_feed(&commands[i],c,millis(),&session)) continue;
                if(!radio_ready) {
                    // A parked radio keeps its configuration/power; no reinitialization.
                    radio_ready=lora.start_receive()==0;
                }
                if(radio_ready && transport.arm(local_address,peer_address,session,
                                                accept_data,nullptr)) {
                    reject_data=i==2;
                    updi_role_log_campaign(role,"SESSION_READY",session);
                    updi_role_log(role,"RX_READY");
                    if(i==1) transport.send_reliable_data(SSOT_SEQUENCE,
                        reinterpret_cast<const uint8_t*>(LORA_HELLO_PAYLOAD),
                        SSOT_HELLO_PAYLOAD_SIZE,millis());
                } else updi_role_log_status(role,"ARM_FAILED",lora.last_error());
                ssot_control_input_init(&commands[i],i==0?'R':i==1?'S':'N');
            }
        }
    }
    if(!transport.active()) flush_event();
    if(log_overflow!=log_overflow_reported && !transport.active()) {
        char line[32];snprintf(line,sizeof line,"LOG_OVERFLOW N=%u",static_cast<unsigned>(log_overflow));
        updi_role_log(role,line);
        log_overflow_reported=log_overflow;
    }
}
