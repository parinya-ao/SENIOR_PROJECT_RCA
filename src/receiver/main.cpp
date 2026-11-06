#include <Arduino.h>

#include "lora.h"
#include "role_log.h"
#include "hello_config.h"
#include "hello_protocol.h"
#include "iw/tracker/radio/packets.h"
#include "iw/tracker/radio/codec.h"

using namespace iw::tracker::radio;

// RFM95W wiring follows the LoRa Board Rev 1.0 schematic and Gateway mapping.
#define PIN_LED1 PIN_PA5
#define PIN_LED2 PIN_PA4
#define PIN_LORA_CS PIN_PC3
#define PIN_LORA_RST PIN_PD0
#define PIN_LORA_IRQ PIN_PD2
#define PIN_LORA_DIO1 PIN_PD3

#define LED1_OFF() digitalWriteFast(PIN_LED1, HIGH)
#define LED2_OFF() digitalWriteFast(PIN_LED2, HIGH)

static constexpr Address RECEIVER_ADDRESS = 1;
static constexpr Address GATEWAY_ADDRESS = 0;
static constexpr uint32_t ACK_TIMEOUT_MS = 3000;

static LoRa lora(PIN_LORA_CS, PIN_LORA_IRQ, PIN_LORA_RST, PIN_LORA_DIO1);
static bool radio_ready = false;
static bool boot_logged = false;
static uint8_t radio_version = 0;
static int16_t radio_probe_status = RADIOLIB_ERR_UNKNOWN;
static int16_t radio_init_status = RADIOLIB_ERR_UNKNOWN;
static bool radio_init_attempted = false;
static lora_hello::DuplicateTracker duplicates;

static void init_receiver_gpio() {
    pinModeFast(PIN_LED1, OUTPUT);
    pinModeFast(PIN_LED2, OUTPUT);
    pinModeFast(PIN_LORA_CS, OUTPUT);
    pinModeFast(PIN_LORA_RST, OUTPUT);
    pinModeFast(PIN_LORA_IRQ, INPUT);
    pinModeFast(PIN_LORA_DIO1, INPUT);
    LED1_OFF();
    LED2_OFF();
    digitalWriteFast(PIN_LORA_CS, HIGH);
    digitalWriteFast(PIN_LORA_RST, HIGH);
}

void setup() {
    init_receiver_gpio();
    radio_probe_status = lora.read_chip_version(&radio_version);
#if !HELLO_RF_DIAGNOSTIC_ONLY
    if (radio_probe_status == RADIOLIB_ERR_NONE &&
        LoRa::is_supported_chip_version(radio_version)) {
        radio_init_attempted = true;
        radio_ready = lora.init(RECEIVER_ADDRESS, HELLO_RF_FREQUENCY_MHZ,
                                HELLO_RF_TX_POWER_DBM, HELLO_RF_LONG_RANGE);
        radio_init_status = lora.last_error();
    } else {
        radio_init_status = radio_probe_status == RADIOLIB_ERR_NONE
                                ? RADIOLIB_ERR_UNKNOWN
                                : radio_probe_status;
    }
#endif
}

void loop() {
    if (!boot_logged && updi_uart_enabled()) {
        updi_role_log_identity("RECEIVER", "receiver", __DATE__, __TIME__);
        updi_role_log_boot("RECEIVER", "receiver", __DATE__, __TIME__);
        if (radio_probe_status == RADIOLIB_ERR_NONE) {
            updi_role_log_radio_version("RECEIVER", radio_version);
            if (!LoRa::is_supported_chip_version(radio_version)) {
                updi_role_log("RECEIVER", "RADIO_VERSION_MISMATCH");
            }
        } else {
            updi_role_log_status("RECEIVER", "RADIO_SPI_READ",
                                 radio_probe_status);
        }
#if HELLO_RF_DIAGNOSTIC_ONLY
        updi_role_log("RECEIVER", "RADIO_INIT_SKIPPED_DIAGNOSTIC");
        updi_role_log("RECEIVER", "RF_TX_DISABLED_DIAGNOSTIC");
#else
        if (radio_init_attempted) {
            updi_role_log_status("RECEIVER", "RADIO_INIT", radio_init_status);
        } else {
            updi_role_log("RECEIVER", "RADIO_INIT_SKIPPED");
        }
        updi_role_log("RECEIVER", radio_ready ? "RADIO_READY" : "RADIO_INIT_FAILED");
        if (radio_ready) {
            updi_role_log_radio_profile(
                "RECEIVER", HELLO_RF_FREQUENCY_MHZ, HELLO_RF_TX_POWER_DBM,
                HELLO_RF_SPREADING_FACTOR, HELLO_RF_BANDWIDTH_KHZ,
                HELLO_RF_CODING_RATE, HELLO_RF_SYNC_WORD,
                HELLO_RF_PREAMBLE_SYMBOLS, HELLO_RF_CRC_ENABLED,
                HELLO_RF_IQ_INVERTED);
            updi_role_log("RECEIVER", "RX_READY");
        }
#endif
        boot_logged = true;
    }

    if (!radio_ready || !lora.available()) {
        delay(1);
        return;
    }

    Address source = 0;
    Address destination = 0;
    uint8_t id = 0;
    uint8_t flags = 0;
    uint8_t packet[255];
    uint8_t packet_size = 0;
    if (lora.recv(&source, &destination, &id, &flags, packet, &packet_size,
                  sizeof(packet)) != RADIOLIB_ERR_NONE) {
        updi_role_log("RECEIVER", "RADIO_RX_FAILED");
        return;
    }

    lora_hello::Frame frame{};
    if (!lora_hello::decode_payload(destination, source, id, flags, packet,
                                    packet_size, &frame) ||
        frame.type != lora_hello::kDataType ||
        source != GATEWAY_ADDRESS || destination != RECEIVER_ADDRESS) {
        return;
    }

    const bool duplicate = duplicates.observe(source, frame.campaign_id,
                                               frame.sequence);
    updi_role_log_packet("RECEIVER", "PAYLOAD_MATCH", frame.campaign_id,
                         frame.sequence, 0);
    if (frame.sequence == 1) {
        updi_role_log_payload("RECEIVER", "PAYLOAD_BYTES", frame.campaign_id,
                              frame.sequence, packet + 2,
                              lora_hello::kHelloPayloadSize);
    }
    updi_role_log_packet("RECEIVER", duplicate ? "DATA_DUP" : "DATA_RX",
                         frame.campaign_id, frame.sequence, 0);

#if !HELLO_RF_DIAGNOSTIC_ONLY
    PacketAck ack;
    ack.seq = frame.sequence;
    uint8_t ack_bytes[kPacketAckBytes];
    if (!EncodePacketAck(ack, ack_bytes, sizeof(ack_bytes))) {
        updi_role_log_packet("RECEIVER", "ACK_ENCODE_FAILED",
                             frame.campaign_id, frame.sequence, 0);
        return;
    }
    const uint32_t ack_airtime_us = lora.time_on_air_us(sizeof(ack_bytes));
    if (ack_airtime_us == 0) {
        updi_role_log_packet("RECEIVER", "ACK_AIRTIME_FAILED",
                             frame.campaign_id, frame.sequence, 0);
        return;
    }
    if (lora.send(source, id, flags, ack_bytes, sizeof(ack_bytes)) !=
            RADIOLIB_ERR_NONE) {
        updi_role_log_packet("RECEIVER", "ACK_START_FAILED",
                             frame.campaign_id, frame.sequence, 0);
        return;
    }
    updi_role_log_airtime("RECEIVER", "ACK_TX", frame.campaign_id,
                          frame.sequence, 0, ack_airtime_us);

    const uint32_t started_at = millis();
    while (!lora.send_done() && millis() - started_at < ACK_TIMEOUT_MS) {
        delay(1);
    }
    updi_role_log_packet("RECEIVER",
                         lora.send_done() ? "ACK_DONE" : "ACK_TX_TIMEOUT",
                         frame.campaign_id, frame.sequence, 0);
#endif
}
