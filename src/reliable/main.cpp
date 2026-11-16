#include <Arduino.h>
#include <stdio.h>
#include <string.h>

#include "hello_config.h"
#include "lora.h"
#include "role_log.h"
#include "reliable_transport.h"

#if defined(LORA_ROLE_RECEIVER)
#include "generated/lora_receiver_board.h"
#if !HELLO_RF_DIAGNOSTIC_ONLY
static constexpr uint8_t local_address=LORA_RECEIVER_ADDRESS;
static constexpr uint8_t peer_address=LORA_SENDER_ADDRESS;
#endif
static const char role[]="RECEIVER";
static const char firmware[]="receiver";
#else
#include "generated/lora_sender_board.h"
#if !HELLO_RF_DIAGNOSTIC_ONLY
static constexpr uint8_t local_address=LORA_SENDER_ADDRESS;
static constexpr uint8_t peer_address=LORA_RECEIVER_ADDRESS;
#endif
static const char role[]="GATEWAY";
static const char firmware[]="sender_hello";
#endif

void onPreMain() { _PROTECTED_WRITE(CPUINT.CTRLA,0); }

static LoRa lora(LORA_PIN_CS,LORA_PIN_IRQ,LORA_PIN_RST,LORA_PIN_DIO1);
static ReliableTransport<LoRa> transport(
    lora,HELLO_RF_FREQUENCY_MHZ,HELLO_RF_TX_POWER_DBM,HELLO_RF_LONG_RANGE);
static bool radio_ready=false,boot_logged=false;
#if !HELLO_RF_DIAGNOSTIC_ONLY
static bool reject_data=false,spi_selected=false;
static bool completion_reported=false;
static uint8_t tx_sequence=SSOT_SEQUENCE;
#endif
static uint8_t accepted_payload[SSOT_HELLO_PAYLOAD_SIZE];
static uint16_t log_overflow=0;

struct RecordedEvent {
    const char* name;
    uint32_t time;
    int16_t error;
    uint8_t type,sequence;
};
static RecordedEvent events[16];
static uint8_t head=0,count=0;

static void record(void*,const char* event,uint8_t type,uint8_t sequence,int16_t error) {
    if(count==16) { if(log_overflow!=UINT16_MAX) ++log_overflow;return; }
    events[(head+count)%16]={event,millis(),error,type,sequence};
    ++count;
}

static void flush_event() {
    if(!count || !updi_uart_enabled()) return;
    const RecordedEvent& event=events[head];
    char line[80];
    snprintf(line,sizeof line,"%s T=%lu TYPE=%u Q=%u E=%d",event.name,
             static_cast<unsigned long>(event.time),event.type,event.sequence,event.error);
    updi_role_log(role,line);
    if(!strcmp(event.name,"DATA_VALIDATED"))
        updi_role_log_payload(role,"PAYLOAD_BYTES",0,event.sequence,
                              accepted_payload,sizeof accepted_payload);
    head=static_cast<uint8_t>((head+1)%16);--count;
}

#if !HELLO_RF_DIAGNOSTIC_ONLY
static bool accept_data(void*,uint8_t sequence,const uint8_t* data,uint8_t length) {
    static_cast<void>(sequence);
    if(reject_data) { reject_data=false;return false; }
    if(length!=SSOT_HELLO_PAYLOAD_SIZE || !data ||
       memcmp(data,LORA_HELLO_PAYLOAD,length)) return false;
    memcpy(accepted_payload,data,length);return true;
}
#endif

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

#if !HELLO_RF_DIAGNOSTIC_ONLY
static bool arm_radio() {
    if(!spi_selected) {
        if(!SPI.swap(LORA_SPI_ROUTE)) return false;
        spi_selected=true;
    }
    return transport.arm(local_address,peer_address,accept_data,nullptr);
}
#endif

void setup() {
    transport.on_event(record,nullptr);
    init_gpio();
#if HELLO_RF_DIAGNOSTIC_ONLY
    updi_role_log(role,"RADIO_INIT_SKIPPED_DIAGNOSTIC");
    updi_role_log(role,"RF_TX_DISABLED_DIAGNOSTIC");
#else
    radio_ready=arm_radio();
#if defined(LORA_ROLE_RECEIVER)
    if(radio_ready) updi_role_log(role,"RX_READY");
#endif
#endif
}

static void status() {
    updi_role_log(role,radio_ready?"RADIO_READY":"RADIO_NOT_READY");
    if(log_overflow) {
        char line[32];snprintf(line,sizeof line,"LOG_OVERFLOW N=%u",
                              static_cast<unsigned>(log_overflow));
        updi_role_log(role,line);
    }
}

void loop() {
#if defined(LORA_NONBLOCKING_LOG) && LORA_NONBLOCKING_LOG
    if(!transport.active()) updi_role_log_service();
#endif
    if(!boot_logged && updi_uart_enabled()) {
        updi_role_log_identity(role,firmware,__DATE__,__TIME__);
        updi_role_log_boot(role,firmware,__DATE__,__TIME__);
        updi_role_log(role,"BUILD_ID=" LORA_BUILD_ID);
        updi_role_log(role,"PROTOCOL_VERSION=" LORA_PROTOCOL_VERSION_TEXT);
#if HELLO_RF_DIAGNOSTIC_ONLY
        updi_role_log(role,"RF_TX_DISABLED_DIAGNOSTIC");
#else
        updi_role_log(role,radio_ready?"RADIO_INIT_OK":"RADIO_INIT_FAILED");
        if(radio_ready) {
            updi_role_log_radio_profile(role,HELLO_RF_FREQUENCY_MHZ,
                HELLO_RF_TX_POWER_DBM,HELLO_RF_SPREADING_FACTOR,
                HELLO_RF_BANDWIDTH_KHZ,HELLO_RF_CODING_RATE,HELLO_RF_SYNC_WORD,
                HELLO_RF_PREAMBLE_SYMBOLS,HELLO_RF_CRC_ENABLED,HELLO_RF_IQ_INVERTED);
#if defined(LORA_ROLE_RECEIVER)
            updi_role_log(role,"RX_READY");
#else
            updi_role_log(role,"WAIT_START");
#endif
        }
#endif
        boot_logged=true;
    }

#if !HELLO_RF_DIAGNOSTIC_ONLY
    transport.poll(millis());
    if(transport.state()==decltype(transport)::State::Failed) radio_ready=false;
    if(transport.result()==decltype(transport)::Result::Accepted && !completion_reported) {
        completion_reported=true;
        if(tx_sequence!=UINT8_MAX) ++tx_sequence;
    }
#endif

    while(updi_uart_rx_poll()) {
        const char command=static_cast<char>(updi_uart_rx());
        if(command=='?') { status();continue; }
#if HELLO_RF_DIAGNOSTIC_ONLY
        continue;
#else
        if(command=='P') {
            const int16_t error=transport.stop();radio_ready=false;
            updi_role_log_status(role,"PARKED",error);continue;
        }
        if(command=='N') { reject_data=true;continue; }
        if(command=='A') { reject_data=false;continue; }
        if(command=='D') { transport.suppress_next_response();continue; }
        if(command=='R') {
            radio_ready=arm_radio();completion_reported=false;tx_sequence=SSOT_SEQUENCE;
            if(radio_ready) updi_role_log(role,"RX_READY");
            else updi_role_log(role,"RADIO_INIT_FAILED");
            continue;
        }
#if !defined(LORA_ROLE_RECEIVER)
        if(command=='S') {
            if(!radio_ready || transport.active()) continue;
            completion_reported=false;
            if(transport.send_reliable_data(tx_sequence,
                    reinterpret_cast<const uint8_t*>(LORA_HELLO_PAYLOAD),
                    SSOT_HELLO_PAYLOAD_SIZE,millis()))
                record(nullptr,"DATA_TX_REQUESTED",SSOT_DATA_TYPE,tx_sequence,0);
        }
#endif
#endif
    }
    if(!transport.active()) flush_event();
}
