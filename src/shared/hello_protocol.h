#pragma once

#include <stddef.h>
#include <stdint.h>
#include "../../include/generated/lora_shared_config.h"

namespace lora_hello {

constexpr uint8_t kDataType = LORA_DATA_TYPE;
constexpr uint8_t kAckType = LORA_ACK_TYPE;
constexpr uint8_t kNackType = LORA_NACK_TYPE;
constexpr size_t kRadioHeaderSize = 4;
constexpr size_t kHelloPayloadSize = 11;
constexpr size_t kDataPayloadSize = 2 + kHelloPayloadSize;
constexpr size_t kAckPayloadSize = 2;
constexpr size_t kDataFrameSize = kRadioHeaderSize + kDataPayloadSize;
constexpr size_t kAckFrameSize = kRadioHeaderSize + kAckPayloadSize;
constexpr uint8_t kCampaignMessages = 20;
constexpr uint8_t kMaxRetries = LORA_MAX_RETRIES;
constexpr uint8_t kMaxAttempts = 1 + kMaxRetries;

enum class State : uint8_t {
    TEST_IDLE, TEST_ARMED, TEST_RUNNING, TEST_COMPLETED, TEST_FAILED
};

struct Frame {
    uint8_t destination;
    uint8_t source;
    uint16_t campaign_id;
    uint8_t type;
    uint8_t sequence;
};

bool encode_data_payload(uint8_t sequence, uint8_t* output, size_t capacity,
                         size_t* output_size);
bool encode_ack_payload(uint8_t sequence, uint8_t* output, size_t capacity,
                        size_t* output_size);
bool encode_nack_payload(uint8_t sequence, uint8_t* output, size_t capacity,
                         size_t* output_size);
bool encode_data_frame(uint8_t destination, uint8_t source, uint16_t campaign_id,
                       uint8_t sequence, uint8_t* output, size_t capacity,
                       size_t* output_size);
bool encode_ack_frame(uint8_t destination, uint8_t source, uint16_t campaign_id,
                      uint8_t sequence, uint8_t* output, size_t capacity,
                      size_t* output_size);
bool decode_payload(uint8_t destination, uint8_t source, uint8_t id,
                    uint8_t flags, const uint8_t* payload, size_t payload_size,
                    Frame* frame);
bool decode_frame(const uint8_t* input, size_t input_size, Frame* frame);
uint8_t reply_for_data(uint8_t destination, uint8_t source, uint8_t id, uint8_t flags,
                       const uint8_t* payload, size_t size, uint16_t session, Frame* frame);
bool ack_matches(const Frame& frame, uint8_t source, uint8_t destination,
                 uint16_t campaign_id, uint8_t sequence);
uint32_t campaign_build_id(const char* build_marker);
uint32_t min_interval_ms_for_one_percent(uint32_t airtime_us);

class Campaign {
public:
    Campaign(uint8_t source, uint8_t destination, bool single_packet = false);
    bool arm(uint16_t campaign_id);
    bool start();
    bool mark_sent();
    bool timeout();
    bool acknowledge(const Frame& frame);
    bool reject(const Frame& frame);
    void fail();
    State state() const;
    uint16_t campaign_id() const;
    uint8_t sequence() const;
    uint8_t attempts() const;
    bool normal_reception_enabled() const;

private:
    uint8_t source_;
    uint8_t destination_;
    uint16_t campaign_id_;
    uint8_t sequence_;
    uint8_t attempts_;
    State state_;
    bool single_packet_;
};

class DuplicateTracker {
public:
    DuplicateTracker();
    bool observe(uint8_t source, uint16_t campaign_id, uint8_t sequence);
    void reset();

private:
    void reset_session(uint8_t source, uint16_t campaign_id);

    uint8_t source_;
    uint16_t campaign_id_;
    bool initialized_;
    uint8_t seen_[32];
};

// Prefix plus four hexadecimal session digits; incomplete/disconnected input cannot start RF.
class ControlInput {
public:
    explicit ControlInput(char command) : command_(command), digits_(0), value_(0),
        last_ms_(0), reading_(false), triggered_(false) {}
    bool feed(char input, uint32_t now_ms, uint16_t* session);
private:
    char command_;
    uint8_t digits_;
    uint16_t value_;
    uint32_t last_ms_;
    bool reading_;
    bool triggered_;
};

}  // namespace lora_hello
