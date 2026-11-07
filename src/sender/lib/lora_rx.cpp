#include <Arduino.h>

#include "hello_config.h"
#if HELLO_TEST_MODE && !HELLO_RAM_ONLY_TEST
#include <EEPROM.h>
#endif

#include "lora.h"
#include "main.h"
#include "lora_rx.h"
#include "debug.h"
#include "io.h"
#include "role_log.h"
#include "hello_protocol.h"
#include "iw/tracker/radio/packets.h"
#include "iw/tracker/radio/codec.h"

using namespace iw::tracker::radio;
#include "task.h"

#define LORA_DEVICE_ADDR LORA_SENDER_ADDRESS
#define LORA_TEST_PEER_ADDR LORA_RECEIVER_ADDRESS

static LoRa lora(PIN_LORA_CS, PIN_LORA_IRQ, PIN_LORA_RST, PIN_LORA_DIO1);
static bool _started = false;
static bool _radio_ready = false;

static bool probe_radio_version() {
    uint8_t version = 0;
    const int16_t status = lora.read_chip_version(&version);
    if (status != RADIOLIB_ERR_NONE) {
        updi_role_log_status("GATEWAY", "RADIO_SPI_READ", status);
        return false;
    }
    updi_role_log_radio_version("GATEWAY", version);
    if (!LoRa::is_supported_chip_version(version)) {
        updi_role_log("GATEWAY", "RADIO_VERSION_MISMATCH");
        return false;
    }
    return true;
}

#if HELLO_TEST_MODE
static lora_hello::Campaign test_campaign(LORA_DEVICE_ADDR, LORA_TEST_PEER_ADDR, true);
static constexpr int kCampaignBuildMarkerAddress = 2;

enum class CampaignBuildGateResult : uint8_t {
    Ready,
    AlreadyRun,
    ReadbackFailed,
};

static CampaignBuildGateResult claim_campaign_build() {
#if HELLO_RAM_ONLY_TEST
    // Boot-local only; the host reserves a fresh session and sends S once.
    static bool claimed = false;
    if (claimed) return CampaignBuildGateResult::AlreadyRun;
    claimed = true;
    return CampaignBuildGateResult::Ready;
#else
    const uint32_t build_id =
        lora_hello::campaign_build_id(LORA_BUILD_ID);
    uint32_t stored_id = 0xffffffffUL;
    EEPROM.get(kCampaignBuildMarkerAddress, stored_id);
    if (stored_id == build_id) return CampaignBuildGateResult::AlreadyRun;

    EEPROM.put(kCampaignBuildMarkerAddress, build_id);
    uint32_t readback = 0;
    EEPROM.get(kCampaignBuildMarkerAddress, readback);
    return readback == build_id ? CampaignBuildGateResult::Ready
                                : CampaignBuildGateResult::ReadbackFailed;
#endif
}

#endif

/***********************************************
 * Report error code and repeatedly blink LED
 */
void error_blink_loop(uint8_t code) {
    DEBUG_TS("ERROR: code %d\n", code);
    for (;;) {
        LED2_ON();
        delay(200);
        LED2_OFF();
        delay(200);
    }
}

class TaskLoraRx : public virtual Task {
private:
    uint32_t _ts;
    Address _src;
    Address _dst;
    uint8_t _id;
    uint8_t _flags;
    uint8_t _pkt[256];
    uint8_t _len;
    uint8_t _type;
    int16_t _rssi;
    int16_t _status;
    size_t _payload_len;
    uint16_t _campaign_id;
    PacketAck _ack;
    PacketReportWithAck _report;
    uint8_t _ack_bytes[kPacketAckBytes];
#if HELLO_TEST_MODE
    bool _test_result_logged;
    CampaignBuildGateResult _campaign_build_gate_result;
    bool _has_data_tx;
    uint8_t _campaign_attempt;
    uint32_t _data_airtime_us;
    uint32_t _ack_airtime_us;
    uint32_t _minimum_data_interval_ms;
    uint32_t _data_tx_started_at;
    lora_hello::Frame _hello_frame;
    lora_hello::ControlInput _start_input{'S'};
#endif

public:
    virtual const char* GetName() {
        return "LORA-RX";
    }

    virtual TASK(Run()) {
        TASK_BEGIN();

        for (;;) {
            if (!_started) {
                _status = lora.sleep();
                if (_status == RADIOLIB_ERR_NONE) {
                    DEBUG_TS("%s LoRa module put to sleep successfully.\r\n", GetName());
                } else {
                    DEBUG_TS("%s Failed to put LoRa module to sleep (%d).\r\n",
                             GetName(), _status);
                }
            }
            TASK_WAIT_UNTIL(_started);

#if HELLO_TEST_MODE
            if (test_campaign.state() == lora_hello::State::TEST_IDLE) {
                TASK_WAIT_UNTIL(updi_uart_enabled());
                updi_role_log_boot("GATEWAY", "sender_hello", __DATE__, __TIME__);
                updi_role_log("GATEWAY", "CONFIG_FINGERPRINT=" LORA_CONFIG_FINGERPRINT);
                updi_role_log("GATEWAY", "PROTOCOL_VERSION=" LORA_PROTOCOL_VERSION_TEXT);
                updi_role_log("GATEWAY", "BUILD_ID=" LORA_BUILD_ID);
#if HELLO_RF_DIAGNOSTIC_ONLY
                static_cast<void>(probe_radio_version());
                updi_role_log("GATEWAY", "RADIO_INIT_SKIPPED_DIAGNOSTIC");
                updi_role_log("GATEWAY", "RF_TX_DISABLED_DIAGNOSTIC");
                _started = false;
                continue;
#else
                lora_rx_init_lora(LORA_DEVICE_ADDR, HELLO_RF_FREQUENCY_MHZ,
                                  HELLO_RF_TX_POWER_DBM, HELLO_RF_LONG_RANGE);
                if (!_radio_ready) {
                    test_campaign.fail();
                    updi_role_log("GATEWAY", "RADIO_INIT_FAILED");
                    _test_result_logged = true;
                    _started = false;
                    continue;
                }
                updi_role_log("GATEWAY", "WAIT_START");
                do {
                    TASK_WAIT_UNTIL(updi_uart_rx_poll() || !_started);
                    if (!_started) break;
                } while (!_start_input.feed(updi_uart_rx(), millis(), &_campaign_id));
                if (!_started) continue;
                _campaign_build_gate_result = claim_campaign_build();
                if (_campaign_build_gate_result ==
                    CampaignBuildGateResult::AlreadyRun) {
                    test_campaign.fail();
                    updi_role_log("GATEWAY", "TEST_ALREADY_RUN");
                    _test_result_logged = true;
                    continue;
                }
                if (_campaign_build_gate_result ==
                    CampaignBuildGateResult::ReadbackFailed) {
                    test_campaign.fail();
                    updi_role_log("GATEWAY", "EEPROM_READBACK_FAILED");
                    _test_result_logged = true;
                    continue;
                }
                updi_role_log_campaign("GATEWAY", "S_RECEIVED", _campaign_id);
                if (!test_campaign.arm(_campaign_id) || !test_campaign.start()) {
                    test_campaign.fail();
                    updi_role_log("GATEWAY", "TEST_START_FAILED");
                    _test_result_logged = true;
                    continue;
                }
                _test_result_logged = false;
                _has_data_tx = false;
                updi_role_log_campaign("GATEWAY", "TEST_RUNNING",
                                       test_campaign.campaign_id());
#endif
            }

            while (test_campaign.state() == lora_hello::State::TEST_RUNNING) {
                if (!lora_hello::encode_data_payload(test_campaign.sequence(), _pkt,
                                                     sizeof(_pkt), &_payload_len) ||
                    !test_campaign.mark_sent()) {
                    test_campaign.fail();
                    break;
                }
                _campaign_attempt = test_campaign.attempts();
                _data_airtime_us = lora.time_on_air_us(
                    static_cast<uint8_t>(_payload_len));
                _ack_airtime_us = lora.time_on_air_us(
                    lora_hello::kAckPayloadSize);
                if (_data_airtime_us == 0 || _ack_airtime_us == 0) {
                    test_campaign.fail();
                    updi_role_log_packet("GATEWAY", "AIRTIME_ESTIMATE_FAILED",
                                         test_campaign.campaign_id(),
                                         test_campaign.sequence(), _campaign_attempt);
                    break;
                }
                // Count DATA plus ACK airtime and stay at the stricter 1% tier.
                _minimum_data_interval_ms =
                    lora_hello::min_interval_ms_for_one_percent(
                        _data_airtime_us + _ack_airtime_us);
                if (_has_data_tx) {
                    TASK_WAIT_UNTIL(millis() - _data_tx_started_at >=
                                    _minimum_data_interval_ms);
                }
                _data_tx_started_at = millis();
                _has_data_tx = true;
                _status = lora.send(
                    LORA_TEST_PEER_ADDR,
                    static_cast<uint8_t>(test_campaign.campaign_id() & 0xffU),
                    static_cast<uint8_t>(test_campaign.campaign_id() >> 8),
                    _pkt, static_cast<uint8_t>(_payload_len));
                if (_status != RADIOLIB_ERR_NONE) {
                    updi_role_log_packet("GATEWAY", "DATA_START_FAILED",
                                         test_campaign.campaign_id(),
                                         test_campaign.sequence(), _campaign_attempt);
                    if (!test_campaign.timeout()) break;
                    continue;
                }
                if (test_campaign.sequence() == 1 && _campaign_attempt == 1) {
                    updi_role_log_payload("GATEWAY", "DATA_PAYLOAD",
                                          test_campaign.campaign_id(),
                                          test_campaign.sequence(), _pkt + 2,
                                          lora_hello::kHelloPayloadSize);
                }
                updi_role_log_airtime("GATEWAY", "DATA_TX",
                                      test_campaign.campaign_id(),
                                      test_campaign.sequence(), _campaign_attempt,
                                      _data_airtime_us);

                _ts = millis();
                TASK_WAIT_UNTIL(lora.send_done() ||
                                (millis() - _ts >= LORA_TX_TIMEOUT_MS));
                if (millis() - _ts >= LORA_TX_TIMEOUT_MS && !lora.send_done()) {
                    test_campaign.fail();
                    updi_role_log_packet("GATEWAY", "DATA_TX_TIMEOUT",
                                         test_campaign.campaign_id(),
                                         test_campaign.sequence(), _campaign_attempt);
                    _radio_ready = lora.init(LORA_DEVICE_ADDR,
                                             HELLO_RF_FREQUENCY_MHZ,
                                             HELLO_RF_TX_POWER_DBM,
                                             HELLO_RF_LONG_RANGE);
                    _started = _radio_ready;
                    _test_result_logged = true;
                    break;
                }
                updi_role_log_packet("GATEWAY", "DATA_DONE",
                                     test_campaign.campaign_id(),
                                     test_campaign.sequence(), _campaign_attempt);

                _ts = millis();
                TASK_WAIT_UNTIL(lora.available() ||
                                (millis() - _ts >= LORA_ACK_TIMEOUT_MS));
                if (lora.available()) {
                    _status = lora.recv(&_src, &_dst, &_id, &_flags, _pkt, &_len,
                                        sizeof(_pkt));
                    if (_status == RADIOLIB_ERR_NONE &&
                        lora_hello::decode_payload(_dst, _src, _id, _flags,
                                                   _pkt, _len, &_hello_frame) &&
                        test_campaign.acknowledge(_hello_frame)) {
                        updi_role_log_rtt("GATEWAY", "ACK_RX",
                                          test_campaign.campaign_id(),
                                          _hello_frame.sequence,
                                          millis() - _data_tx_started_at);
                        if (_hello_frame.sequence == 1) {
                            updi_role_log_packet("GATEWAY", "PREFLIGHT_OK",
                                                 test_campaign.campaign_id(),
                                                 _hello_frame.sequence,
                                                 _campaign_attempt);
                        }
                        if (test_campaign.state() == lora_hello::State::TEST_COMPLETED) {
                            updi_role_log_campaign("GATEWAY", "TEST_COMPLETED",
                                                   test_campaign.campaign_id());
                            _test_result_logged = true;
                        }
                        continue;
                    }
                    if (_status == RADIOLIB_ERR_NONE &&
                        lora_hello::decode_payload(_dst, _src, _id, _flags,
                                                  _pkt, _len, &_hello_frame) &&
                        _hello_frame.type == lora_hello::kNackType) {
                        lora_hello::Frame response = _hello_frame;
                        response.type = lora_hello::kAckType;
                        if (lora_hello::ack_matches(response, LORA_TEST_PEER_ADDR,
                                LORA_DEVICE_ADDR, _campaign_id, 1)) {
                            updi_role_log_packet("GATEWAY", "NACK_RX", _campaign_id, 1, _campaign_attempt);
                            if (test_campaign.reject(_hello_frame)) continue;
                            break;
                        }
                    }
                }
                updi_role_log_packet("GATEWAY", "ACK_TIMEOUT",
                                     test_campaign.campaign_id(),
                                     test_campaign.sequence(), _campaign_attempt);
                if (!test_campaign.timeout()) break;
            }

            if (test_campaign.state() == lora_hello::State::TEST_FAILED &&
                !_test_result_logged) {
                updi_role_log_packet("GATEWAY", "TEST_FAILED",
                                     test_campaign.campaign_id(),
                                     test_campaign.sequence(),
                                     test_campaign.attempts());
                _test_result_logged = true;
            }
            // Standalone tests must never fall through to the production report/ACK service.
            _started = false;
            continue;
#endif

            TASK_WAIT_UNTIL(lora.available() || !_started);
            if (!_started) continue;

            _status = lora.recv(&_src, &_dst, &_id, &_flags, _pkt, &_len,
                                sizeof(_pkt));
            if (_status != RADIOLIB_ERR_NONE || _len == 0) {
                DEBUG_TS("%s LoRa receive failed (%d).\r\n", GetName(), _status);
                continue;
            }
            _type = _pkt[0];
            _rssi = lora.get_last_rssi();
            if ((_dst != LORA_DEVICE_ADDR) && (_dst != 0xFF)) {
                continue;
            }
#if HELLO_TEST_MODE
            if ((_id != 0 || _flags != 0) &&
                (_type == lora_hello::kDataType || _type == lora_hello::kAckType)) {
                continue;
            }
#endif
            DEBUG_TS("%s Receive %d bytes from %d (RSSI=%d,type=%d)\r\n",
                     GetName(), _len, _src, _rssi, _type);
            LED2_ON();
            TASK_DELAY(50, _ts);
            LED2_OFF();

            ringbuf.Write(_src);
            ringbuf.Write(_rssi);
            ringbuf.Write(_len);
            ringbuf.Write(_pkt, _len);
            digitalWriteFast(PIN_INT, HIGH);

            if (_type == PKT_TYPE_REPORT_WITH_ACK) {
                if (!DecodePacketReportWithAck(_pkt, _len, &_report)) {
                    continue;
                }
                _ack.seq = _report.seq;
                if (!EncodePacketAck(_ack, _ack_bytes, sizeof(_ack_bytes))) {
                    continue;
                }
                _status = lora.send(_src, _ack_bytes, sizeof(_ack_bytes));
                if (_status != RADIOLIB_ERR_NONE) continue;
                _ts = millis();
                TASK_WAIT_UNTIL(lora.send_done() ||
                                (millis() - _ts >= LORA_TX_TIMEOUT_MS));
                if (millis() - _ts >= LORA_TX_TIMEOUT_MS && !lora.send_done()) {
                    DEBUG_TS("%s LoRa ACK TX timed out.\r\n", GetName());
                }
            }
        }

        TASK_END();
    }
} taskLoraRx;

void lora_rx_setup() {
    scheduler.Add(&taskLoraRx);
}

void lora_rx_init_lora(Address my_addr, float freq, int8_t tx_power,
                       uint8_t long_range) {
#if HELLO_TEST_MODE
    if (my_addr != LORA_DEVICE_ADDR || freq != HELLO_RF_FREQUENCY_MHZ ||
        tx_power != HELLO_RF_TX_POWER_DBM || long_range != HELLO_RF_LONG_RANGE) {
        _radio_ready = false;
        updi_role_log("GATEWAY", "RADIO_PROFILE_MISMATCH");
        return;
    }
#endif
    if (!probe_radio_version()) {
        _radio_ready = false;
        return;
    }
    _radio_ready = lora.init(my_addr, freq, tx_power, long_range);
    updi_role_log_status("GATEWAY", "RADIO_INIT", lora.last_error());
    if (_radio_ready) {
        const uint8_t spreading_factor = long_range
                                             ? 12
                                             : HELLO_RF_SPREADING_FACTOR;
        const uint8_t coding_rate = long_range ? 8 : HELLO_RF_CODING_RATE;
        updi_role_log_radio_profile(
            "GATEWAY", freq, tx_power, spreading_factor,
            HELLO_RF_BANDWIDTH_KHZ, coding_rate,
            HELLO_RF_SYNC_WORD, HELLO_RF_PREAMBLE_SYMBOLS,
            HELLO_RF_CRC_ENABLED, HELLO_RF_IQ_INVERTED);
        updi_role_log("GATEWAY", "RADIO_READY");
        DEBUG_TS("LoRa initialized successfully\r\n");
    } else {
        updi_role_log("GATEWAY", "RADIO_INIT_FAILED");
        DEBUG_TS("Failed to initialize LoRa (%d)\r\n", lora.last_error());
    }
}

void lora_rx_start_lora() {
#if HELLO_TEST_MODE
    if (_started || test_campaign.state() != lora_hello::State::TEST_IDLE) {
        updi_role_log("GATEWAY", "REPEATED_START_IGNORED");
        return;
    }
#endif
    _started = true;
}

void lora_rx_stop_lora() {
    _started = false;
    if (lora.sleep() != RADIOLIB_ERR_NONE) {
        DEBUG_TS("Failed to sleep LoRa module (%d)\r\n", lora.last_error());
    }
}

void lora_rx_hello_boot() {
#if HELLO_TEST_MODE
    lora_rx_start_lora();
#endif
}
