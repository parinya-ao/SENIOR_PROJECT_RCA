#include <Arduino.h>
#include <string.h>

#include "hello_config.h"
#include "../../../stable_lib/lora/lora.h"
#include "lora_rx.h"
#include "main.h"
#include "reliable_transport.h"
#include "role_log.h"
#include "ssot.h"
#include "task.h"

#if !HELLO_RF_DIAGNOSTIC_ONLY
static constexpr Address kPeerAddress=LORA_RECEIVER_ADDRESS;
#endif
static LoRa lora(LORA_PIN_CS,LORA_PIN_IRQ,LORA_PIN_RST,LORA_PIN_DIO1);
static ReliableTransport<LoRa> transport(
    lora,HELLO_RF_FREQUENCY_MHZ,HELLO_RF_TX_POWER_DBM,HELLO_RF_LONG_RANGE);
static Address local_address=LORA_SENDER_ADDRESS;
static bool started=false,radio_ready=false;
#if !HELLO_RF_DIAGNOSTIC_ONLY
static bool spi_selected=false;
static uint8_t sequence=SSOT_SEQUENCE;

static bool accept_data(void*,uint8_t seq,const uint8_t* data,uint8_t length) {
    static_cast<void>(seq);
    return data && length==SSOT_HELLO_PAYLOAD_SIZE &&
           memcmp(data,LORA_HELLO_PAYLOAD,length)==0;
}
#endif

void lora_rx_init_lora(Address my_addr) {
    local_address=my_addr;
#if HELLO_RF_DIAGNOSTIC_ONLY
    radio_ready=false;
    updi_role_log("GATEWAY","RADIO_INIT_SKIPPED_DIAGNOSTIC");
#else
    if(!spi_selected) {
        if(!SPI.swap(LORA_SPI_ROUTE)) {
            radio_ready=false;updi_role_log("GATEWAY","SPI_ROUTE_FAILED");return;
        }
        spi_selected=true;
    }
    radio_ready=transport.arm(local_address,kPeerAddress,accept_data,nullptr);
    updi_role_log("GATEWAY",radio_ready?"RADIO_READY":"RADIO_INIT_FAILED");
#endif
}

class TaskLoraRx : public virtual Task {
public:
    const char* GetName() override { return "LORA-ACK"; }

    TASK(Run()) override {
        TASK_BEGIN();
        for(;;) {
            TASK_WAIT_UNTIL(started);
#if HELLO_RF_DIAGNOSTIC_ONLY
            updi_role_log("GATEWAY","RF_TX_DISABLED_DIAGNOSTIC");
            started=false;
            continue;
#else
            if(!radio_ready) lora_rx_init_lora(local_address);
            if(!radio_ready || !transport.send_reliable_data(
                   sequence,reinterpret_cast<const uint8_t*>(LORA_HELLO_PAYLOAD),
                   SSOT_HELLO_PAYLOAD_SIZE,millis())) {
                updi_role_log("GATEWAY","DATA_START_FAILED");
                started=false;
                continue;
            }
            updi_role_log("GATEWAY","DATA_TX_BEGIN");
            while(transport.active()) {
                transport.poll(millis());
                TASK_YIELD();
            }
            if(transport.result()==ReliableTransport<LoRa>::Result::Accepted) {
                updi_role_log("GATEWAY","ACK_ACCEPTED");
                if(sequence!=UINT8_MAX) ++sequence;
            } else {
                radio_ready=transport.state()!=ReliableTransport<LoRa>::State::Failed;
                updi_role_log("GATEWAY",transport.result()==
                    ReliableTransport<LoRa>::Result::Rejected?"NACK_RETRY_EXHAUSTED":
                    "TRANSACTION_FAILED");
            }
            started=false;
#endif
        }
        TASK_END();
    }
} taskLoraRx;

void lora_rx_setup() { scheduler.Add(&taskLoraRx); }

void lora_rx_reject_config() {
    started=false;radio_ready=false;static_cast<void>(transport.stop());
    updi_role_log("GATEWAY","RADIO_CONFIG_REJECTED");
}

void lora_rx_start_lora() {
    if(started) return;
    if(!radio_ready) lora_rx_init_lora(local_address);
    started=radio_ready;
}

void lora_rx_stop_lora() {
    started=false;radio_ready=false;static_cast<void>(transport.stop());
}

void lora_rx_hello_boot() {
#if HELLO_TEST_MODE
    lora_rx_start_lora();
#endif
}
