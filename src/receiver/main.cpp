#include <Arduino.h>
#include <string.h>

#include "hello_config.h"
#include "lora.h"
#include "role_log.h"
#include "ssot.h"
#include "generated/lora_receiver_board.h"

void onPreMain() { _PROTECTED_WRITE(CPUINT.CTRLA,0); }

static constexpr Address kReceiverAddress=LORA_RECEIVER_ADDRESS;
static constexpr Address kSenderAddress=LORA_SENDER_ADDRESS;
static LoRa lora(LORA_PIN_CS,LORA_PIN_IRQ,LORA_PIN_RST,LORA_PIN_DIO1);
static bool radio_ready=false,boot_logged=false,spi_selected=false;
static bool have_accepted=false;
static uint8_t last_sequence=0,next_sequence=SSOT_SEQUENCE;
static uint8_t last_payload[SSOT_HELLO_PAYLOAD_SIZE];

static bool init_radio();

static void init_receiver_gpio() {
    digitalWriteFast(LORA_PIN_ENABLE,!LORA_POWER_ACTIVE_LEVEL);
    digitalWriteFast(LORA_PIN_GPS_ENABLE,HIGH);
    digitalWriteFast(LORA_PIN_SD_ENABLE,HIGH);
    pinModeFast(LORA_PIN_ENABLE,OUTPUT);
    pinModeFast(LORA_PIN_GPS_ENABLE,OUTPUT);
    pinModeFast(LORA_PIN_SD_ENABLE,OUTPUT);
    pinModeFast(LORA_PIN_SD_DETECT,INPUT);
    pinModeFast(LORA_PIN_RST,INPUT);
    pinModeFast(LORA_PIN_IRQ,INPUT);
    pinModeFast(LORA_PIN_DIO1,INPUT);
    digitalWriteFast(LORA_PIN_LED1,HIGH);digitalWriteFast(LORA_PIN_LED2,HIGH);
    pinModeFast(LORA_PIN_LED1,OUTPUT);pinModeFast(LORA_PIN_LED2,OUTPUT);
    digitalWriteFast(LORA_PIN_SD_CS,HIGH);pinModeFast(LORA_PIN_SD_CS,OUTPUT);
    digitalWriteFast(LORA_PIN_ENABLE,LORA_POWER_ACTIVE_LEVEL);
    delay(10);
    digitalWriteFast(LORA_PIN_CS,HIGH);pinModeFast(LORA_PIN_CS,OUTPUT);
}

void setup() {
    init_receiver_gpio();
    radio_ready=init_radio();
}

static bool init_radio() {
    if(!spi_selected) {
        if(!SPI.swap(LORA_SPI_ROUTE)) return false;
        spi_selected=true;
    }
    return lora.init(kReceiverAddress,HELLO_RF_FREQUENCY_MHZ,
                     HELLO_RF_TX_POWER_DBM,HELLO_RF_LONG_RANGE);
}

void loop() {
    if(!boot_logged && updi_uart_enabled()) {
        updi_role_log_identity("RECEIVER","receiver",__DATE__,__TIME__);
        updi_role_log_boot("RECEIVER","receiver",__DATE__,__TIME__);
        updi_role_log("RECEIVER","BUILD_ID=" LORA_BUILD_ID);
        updi_role_log("RECEIVER",radio_ready?"RADIO_READY":"RADIO_INIT_FAILED");
        boot_logged=true;
    }
    if(!radio_ready || !lora.available()) { delay(1);return; }

    Address source=0,destination=0;
    uint8_t packet[256]={},size=0;
    lora.recv(&source,&destination,packet,&size);
    // The stable API rearms RX through init(); no legacy start_receive() exists.
    radio_ready=init_radio();
    if(!radio_ready) { updi_role_log("RECEIVER","RADIO_INIT_FAILED");return; }
    if(size>251 || source!=kSenderAddress || destination!=kReceiverAddress || size<2) {
        updi_role_log("RECEIVER","RX_DISCARD");
        return;
    }

    const uint8_t type=packet[0],sequence=packet[1];
    if(type!=SSOT_DATA_TYPE) return;
    ssot_frame_t frame={};
    const bool decoded=ssot_decode_payload(destination,source,0,0,packet,size,&frame);
    const bool payload_valid=decoded && size==SSOT_DATA_PAYLOAD_SIZE &&
        memcmp(packet+2,LORA_HELLO_PAYLOAD,SSOT_HELLO_PAYLOAD_SIZE)==0;
    const bool duplicate=payload_valid && have_accepted &&
        frame.sequence==last_sequence &&
        memcmp(packet+2,last_payload,sizeof last_payload)==0;
    const bool valid=payload_valid && (duplicate || frame.sequence==next_sequence);
    if(valid) {
        if(!duplicate) {
            have_accepted=true;last_sequence=sequence;
            memcpy(last_payload,packet+2,sizeof last_payload);
            next_sequence=sequence==UINT8_MAX?0:static_cast<uint8_t>(sequence+1);
        }
        updi_role_log("RECEIVER",duplicate?"DATA_DUP":"DATA_RX");
    } else {
        updi_role_log("RECEIVER","DATA_REJECTED");
    }

#if !HELLO_RF_DIAGNOSTIC_ONLY
    uint8_t reply[SSOT_ACK_PAYLOAD_SIZE];
    size_t reply_size=0;
    const bool encoded=valid
        ? ssot_encode_ack_payload(sequence,reply,sizeof reply,&reply_size)
        : ssot_encode_nack_payload(sequence,reply,sizeof reply,&reply_size);
    if(!encoded) return;
    lora.send(source,reply,static_cast<uint8_t>(reply_size));
    const uint32_t started=millis();
    while(!lora.send_done() && millis()-started<LORA_TX_TIMEOUT_MS) delay(1);
    if(lora.send_done()) updi_role_log("RECEIVER",valid?"ACK_TX":"NACK_TX");
    else { radio_ready=false;updi_role_log("RECEIVER","ACK_TX_TIMEOUT"); }
#endif
}
