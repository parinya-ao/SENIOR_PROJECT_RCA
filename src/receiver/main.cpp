#include <Arduino.h>

#include "lora.h"
#include "role_log.h"
#include "hello_config.h"
#include "../../include/generated/lora_receiver_board.h"
#include "hello_protocol.h"
#include "iw/tracker/radio/packets.h"
#include "iw/tracker/radio/codec.h"

using namespace iw::tracker::radio;

// DxCore calls this in .init3, before constructors and interrupt enable.
void onPreMain() {
    _PROTECTED_WRITE(CPUINT.CTRLA, 0);
}

// LoRa Tracker RFM Rev 1.0 (2025-02-16); Receiver wiring differs from Gateway.
#define PIN_LED1 LORA_PIN_LED1
#define PIN_LED2 LORA_PIN_LED2
#define PIN_LORA_CS LORA_PIN_CS
#define PIN_LORA_RST LORA_PIN_RST
#define PIN_LORA_IRQ LORA_PIN_IRQ
#define PIN_LORA_DIO1 LORA_PIN_DIO1
#define PIN_LORA_EN LORA_PIN_ENABLE
#define PIN_SD_CS LORA_PIN_SD_CS

#define LED1_OFF() digitalWriteFast(PIN_LED1, HIGH)
#define LED2_OFF() digitalWriteFast(PIN_LED2, HIGH)

static constexpr Address RECEIVER_ADDRESS = LORA_RECEIVER_ADDRESS;
static constexpr Address GATEWAY_ADDRESS = LORA_SENDER_ADDRESS;
static constexpr uint32_t ACK_TIMEOUT_MS = LORA_TX_TIMEOUT_MS;

static LoRa lora(PIN_LORA_CS, PIN_LORA_IRQ, PIN_LORA_RST, PIN_LORA_DIO1);
static bool radio_ready = false;
static bool boot_logged = false;
static uint8_t radio_version = 0;
static int16_t radio_probe_status = RADIOLIB_ERR_UNKNOWN;
static int16_t radio_init_status = RADIOLIB_ERR_UNKNOWN;
static bool radio_init_attempted = false;
static lora_hello::DuplicateTracker duplicates;
static lora_hello::ControlInput arm_input('R');
static uint16_t armed_session = 0;

static void init_receiver_gpio() {
    digitalWriteFast(PIN_LORA_EN, !LORA_POWER_ACTIVE_LEVEL);
    digitalWriteFast(LORA_PIN_GPS_ENABLE, HIGH);
    digitalWriteFast(LORA_PIN_SD_ENABLE, HIGH);
    pinModeFast(PIN_LORA_EN, OUTPUT);
    pinModeFast(LORA_PIN_GPS_ENABLE, OUTPUT);
    pinModeFast(LORA_PIN_SD_ENABLE, OUTPUT);
    pinModeFast(LORA_PIN_SD_DETECT, INPUT);
    // Keep the unpowered radio's reset high impedance throughout POR.
    pinModeFast(PIN_LORA_RST, INPUT);
    pinModeFast(PIN_LORA_IRQ, INPUT);
    pinModeFast(PIN_LORA_DIO1, INPUT);
    LED1_OFF();
    LED2_OFF();
    pinModeFast(PIN_LED1, OUTPUT);
    pinModeFast(PIN_LED2, OUTPUT);
    digitalWriteFast(PIN_SD_CS, HIGH);
    pinModeFast(PIN_SD_CS, OUTPUT);
    digitalWriteFast(PIN_LORA_EN, LORA_POWER_ACTIVE_LEVEL);
    // Radio POR guard only; actual rail rise/settling remains a physical prerequisite.
    delay(10);
    digitalWriteFast(PIN_LORA_CS, HIGH);
    pinModeFast(PIN_LORA_CS, OUTPUT);
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
        updi_role_log("RECEIVER", "CONFIG_FINGERPRINT=" LORA_CONFIG_FINGERPRINT);
        updi_role_log("RECEIVER", "PROTOCOL_VERSION=" LORA_PROTOCOL_VERSION_TEXT);
        updi_role_log("RECEIVER", "BUILD_ID=" LORA_BUILD_ID);
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
            updi_role_log("RECEIVER", "WAIT_SESSION");
        }
#endif
        boot_logged = true;
    }

    if (radio_ready && updi_uart_rx_poll() &&
        arm_input.feed(updi_uart_rx(), millis(), &armed_session)) {
        duplicates.reset();
        updi_role_log_campaign("RECEIVER", "SESSION_READY", armed_session);
        updi_role_log("RECEIVER", "RX_READY");
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
        updi_role_log_status("RECEIVER", "RADIO_RX_FAILED", lora.last_error());
        return;
    }

    lora_hello::Frame frame{};
    const uint16_t session = static_cast<uint16_t>(id) | (static_cast<uint16_t>(flags) << 8);
    const uint8_t reply = lora_hello::reply_for_data(destination, source, id, flags,
                                                   packet, packet_size, armed_session, &frame);
    if (!reply) return;
    const bool valid = reply == lora_hello::kAckType;
    if (valid) {

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
    } else {
        updi_role_log_packet("RECEIVER", "PAYLOAD_REJECTED", session, 1, 0);
    }

#if !HELLO_RF_DIAGNOSTIC_ONLY
    uint8_t ack_bytes[lora_hello::kAckPayloadSize];
    size_t ack_size = 0;
    const bool encoded = valid
        ? lora_hello::encode_ack_payload(1, ack_bytes, sizeof(ack_bytes), &ack_size)
        : lora_hello::encode_nack_payload(1, ack_bytes, sizeof(ack_bytes), &ack_size);
    if (!encoded) {
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
    updi_role_log_airtime("RECEIVER", valid ? "ACK_TX" : "NACK_TX", session,
                          1, 0, ack_airtime_us);

    const uint32_t started_at = millis();
    while (!lora.send_done() && millis() - started_at < ACK_TIMEOUT_MS) {
        delay(1);
    }
    const bool done = lora.send_done();
    updi_role_log_packet("RECEIVER", done ? (valid ? "ACK_DONE" : "NACK_DONE") : "ACK_TX_TIMEOUT",
                         session, 1, 0);
    if (!done) {
        radio_ready = false;
        updi_role_log_status("RECEIVER", "RADIO_TX_FAILED", lora.last_error());
    }
#endif
}
