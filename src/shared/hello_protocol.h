#pragma once

#include <stddef.h>
#include <stdint.h>

namespace lora_hello {

constexpr uint8_t kDataType = 0x08;
constexpr uint8_t kAckType = 0x03;
constexpr size_t kRadioHeaderSize = 4;
constexpr size_t kHelloPayloadSize = 11;
constexpr size_t kDataPayloadSize = 2 + kHelloPayloadSize;
constexpr size_t kAckPayloadSize = 2;
constexpr size_t kDataFrameSize = kRadioHeaderSize + kDataPayloadSize;
constexpr size_t kAckFrameSize = kRadioHeaderSize + kAckPayloadSize;
constexpr uint8_t kCampaignMessages = 20;
constexpr uint8_t kMaxRetries = 3;
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
bool ack_matches(const Frame& frame, uint8_t source, uint8_t destination,
                 uint16_t campaign_id, uint8_t sequence);
uint32_t campaign_build_id(const char* build_marker);
uint32_t min_interval_ms_for_one_percent(uint32_t airtime_us);

class Campaign {
public:
    Campaign(uint8_t source, uint8_t destination);
    bool arm(uint16_t campaign_id);
    bool start();
    bool mark_sent();
    bool timeout();
    bool acknowledge(const Frame& frame);
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

}  // namespace lora_hello
