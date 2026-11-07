#include "hello_protocol.h"
#include "hello_config.h"

#include <string.h>

namespace lora_hello {
bool ControlInput::feed(char input, uint32_t now_ms, uint16_t* session) {
    if (triggered_ || session == nullptr) return false;
    if (reading_ && now_ms - last_ms_ > 1000) reading_ = false;
    if (input == command_) {
        reading_ = true;
        digits_ = 0;
        value_ = 0;
        last_ms_ = now_ms;
        return false;
    }
    if (!reading_) return false;
    uint8_t digit;
    if (input >= '0' && input <= '9') digit = input - '0';
    else if (input >= 'A' && input <= 'F') digit = input - 'A' + 10;
    else {
        reading_ = false;
        return false;
    }
    value_ = static_cast<uint16_t>((value_ << 4) | digit);
    last_ms_ = now_ms;
    if (++digits_ != 4) return false;
    reading_ = false;
    if (value_ == 0) return false;
    *session = value_;
    triggered_ = true;
    return true;
}

namespace {

const char kHelloPayload[] = LORA_HELLO_PAYLOAD;
static_assert(sizeof(kHelloPayload) - 1 == kHelloPayloadSize, "payload size");

bool encode_header(uint8_t destination, uint8_t source, uint16_t campaign_id,
                   uint8_t* output, size_t capacity) {
    if (output == nullptr || capacity < kRadioHeaderSize) return false;
    output[0] = destination;
    output[1] = source;
    output[2] = static_cast<uint8_t>(campaign_id & 0xffU);
    output[3] = static_cast<uint8_t>(campaign_id >> 8);
    return true;
}

}  // namespace

bool encode_data_payload(uint8_t sequence, uint8_t* output, size_t capacity,
                         size_t* output_size) {
    if (output_size == nullptr) return false;
    *output_size = 0;
    if (output == nullptr || capacity < kDataPayloadSize) return false;
    output[0] = kDataType;
    output[1] = sequence;
    memcpy(output + 2, kHelloPayload, kHelloPayloadSize);
    *output_size = kDataPayloadSize;
    return true;
}

bool encode_ack_payload(uint8_t sequence, uint8_t* output, size_t capacity,
                        size_t* output_size) {
    if (output_size == nullptr) return false;
    *output_size = 0;
    if (output == nullptr || capacity < kAckPayloadSize) return false;
    output[0] = kAckType;
    output[1] = sequence;
    *output_size = kAckPayloadSize;
    return true;
}

bool encode_nack_payload(uint8_t sequence, uint8_t* output, size_t capacity,
                         size_t* output_size) {
    if (!encode_ack_payload(sequence, output, capacity, output_size)) return false;
    output[0] = kNackType;
    return true;
}

bool encode_data_frame(uint8_t destination, uint8_t source, uint16_t campaign_id,
                       uint8_t sequence, uint8_t* output, size_t capacity,
                       size_t* output_size) {
    if (output_size == nullptr) return false;
    *output_size = 0;
    if (capacity < kDataFrameSize ||
        !encode_header(destination, source, campaign_id, output, capacity)) {
        return false;
    }
    size_t payload_size = 0;
    if (!encode_data_payload(sequence, output + kRadioHeaderSize,
                             capacity - kRadioHeaderSize, &payload_size)) {
        return false;
    }
    *output_size = kRadioHeaderSize + payload_size;
    return true;
}

bool encode_ack_frame(uint8_t destination, uint8_t source, uint16_t campaign_id,
                      uint8_t sequence, uint8_t* output, size_t capacity,
                      size_t* output_size) {
    if (output_size == nullptr) return false;
    *output_size = 0;
    if (capacity < kAckFrameSize ||
        !encode_header(destination, source, campaign_id, output, capacity)) {
        return false;
    }
    size_t payload_size = 0;
    if (!encode_ack_payload(sequence, output + kRadioHeaderSize,
                            capacity - kRadioHeaderSize, &payload_size)) {
        return false;
    }
    *output_size = kRadioHeaderSize + payload_size;
    return true;
}

bool decode_payload(uint8_t destination, uint8_t source, uint8_t id,
                    uint8_t flags, const uint8_t* payload, size_t payload_size,
                    Frame* frame) {
    if (payload == nullptr || frame == nullptr || payload_size < 1) return false;
    const uint16_t campaign_id = static_cast<uint16_t>(id) |
                                 (static_cast<uint16_t>(flags) << 8);
    if (payload[0] == kDataType) {
        if (payload_size != kDataPayloadSize ||
            memcmp(payload + 2, kHelloPayload, kHelloPayloadSize) != 0) {
            return false;
        }
    } else if (payload[0] == kAckType || payload[0] == kNackType) {
        if (payload_size != kAckPayloadSize) return false;
    } else {
        return false;
    }

    frame->destination = destination;
    frame->source = source;
    frame->campaign_id = campaign_id;
    frame->type = payload[0];
    frame->sequence = payload[1];
    return true;
}

uint8_t reply_for_data(uint8_t destination, uint8_t source, uint8_t id, uint8_t flags,
                       const uint8_t* payload, size_t size, uint16_t session, Frame* frame) {
    const uint16_t received = static_cast<uint16_t>(id) | (static_cast<uint16_t>(flags) << 8);
    if (!session || received != session || source != LORA_SENDER_ADDRESS ||
        destination != LORA_RECEIVER_ADDRESS || payload == nullptr || size < 2 ||
        payload[0] != kDataType || payload[1] != LORA_SEQUENCE || frame == nullptr) return 0;
    *frame = Frame{destination, source, session, kDataType, LORA_SEQUENCE};
    return decode_payload(destination, source, id, flags, payload, size, frame) ? kAckType : kNackType;
}

bool decode_frame(const uint8_t* input, size_t input_size, Frame* frame) {
    if (input == nullptr || frame == nullptr || input_size < kRadioHeaderSize + 1) {
        return false;
    }
    return decode_payload(input[0], input[1], input[2], input[3],
                          input + kRadioHeaderSize,
                          input_size - kRadioHeaderSize, frame);
}

bool ack_matches(const Frame& frame, uint8_t source, uint8_t destination,
                 uint16_t campaign_id, uint8_t sequence) {
    return frame.type == kAckType && frame.source == source &&
           frame.destination == destination && frame.campaign_id == campaign_id &&
           frame.sequence == sequence;
}

uint32_t campaign_build_id(const char* build_marker) {
    if (build_marker == nullptr) return 0;
    uint32_t hash = 2166136261UL;
    while (*build_marker != '\0') {
        hash ^= static_cast<uint8_t>(*build_marker++);
        hash *= 16777619UL;
    }
    if (hash == 0 || hash == 0xffffffffUL) --hash;
    return hash;
}

uint32_t min_interval_ms_for_one_percent(uint32_t airtime_us) {
    const uint64_t interval_ms =
        (static_cast<uint64_t>(airtime_us) * 100U + 999U) / 1000U;
    return static_cast<uint32_t>(interval_ms);
}

Campaign::Campaign(uint8_t source, uint8_t destination, bool single_packet)
    : source_(source), destination_(destination), campaign_id_(0), sequence_(1),
      attempts_(0), state_(State::TEST_IDLE), single_packet_(single_packet) {}

bool Campaign::arm(uint16_t campaign_id) {
    if (state_ != State::TEST_IDLE) return false;
    campaign_id_ = campaign_id;
    state_ = State::TEST_ARMED;
    return true;
}

bool Campaign::start() {
    if (state_ != State::TEST_ARMED) return false;
    if (sequence_ == 1) attempts_ = 0;
    state_ = State::TEST_RUNNING;
    return true;
}

bool Campaign::mark_sent() {
    if (state_ != State::TEST_RUNNING ||
        attempts_ >= (HELLO_RAM_ONLY_TEST && single_packet_ ? 1 : kMaxAttempts)) return false;
    ++attempts_;
    return true;
}

bool Campaign::timeout() {
    if (state_ != State::TEST_RUNNING || attempts_ == 0) return false;
    if (attempts_ >= (HELLO_RAM_ONLY_TEST && single_packet_ ? 1 : kMaxAttempts)) {
        state_ = State::TEST_FAILED;
        return false;
    }
    return true;
}

bool Campaign::acknowledge(const Frame& frame) {
    if (state_ != State::TEST_RUNNING || attempts_ == 0 ||
        !ack_matches(frame, destination_, source_, campaign_id_, sequence_)) {
        return false;
    }
    if (single_packet_) {
        state_ = State::TEST_COMPLETED;
    } else if (sequence_ == 1) {
        sequence_ = 2;
        attempts_ = 0;
        state_ = State::TEST_ARMED;
    } else if (sequence_ == kCampaignMessages) {
        state_ = State::TEST_COMPLETED;
    } else {
        ++sequence_;
        attempts_ = 0;
    }
    return true;
}

bool Campaign::reject(const Frame& frame) {
    Frame ack = frame;
    ack.type = kAckType;
    return frame.type == kNackType && state_ == State::TEST_RUNNING &&
           ack_matches(ack, destination_, source_, campaign_id_, sequence_) && timeout();
}

void Campaign::fail() {
    if (state_ == State::TEST_IDLE || state_ == State::TEST_ARMED || state_ == State::TEST_RUNNING) {
        state_ = State::TEST_FAILED;
    }
}

State Campaign::state() const { return state_; }
uint16_t Campaign::campaign_id() const { return campaign_id_; }
uint8_t Campaign::sequence() const { return sequence_; }
uint8_t Campaign::attempts() const { return attempts_; }
bool Campaign::normal_reception_enabled() const {
    return !single_packet_ && state_ != State::TEST_ARMED && state_ != State::TEST_RUNNING;
}

DuplicateTracker::DuplicateTracker()
    : source_(0), campaign_id_(0), initialized_(false), seen_{} {}

bool DuplicateTracker::observe(uint8_t source, uint16_t campaign_id,
                               uint8_t sequence) {
    if (!initialized_ || source_ != source || campaign_id_ != campaign_id) {
        reset_session(source, campaign_id);
    }
    const uint8_t mask = static_cast<uint8_t>(1U << (sequence & 7U));
    uint8_t& byte = seen_[sequence >> 3];
    const bool duplicate = (byte & mask) != 0;
    byte = static_cast<uint8_t>(byte | mask);
    return duplicate;
}

void DuplicateTracker::reset() {
    memset(seen_, 0, sizeof(seen_));
    initialized_ = false;
}

void DuplicateTracker::reset_session(uint8_t source, uint16_t campaign_id) {
    memset(seen_, 0, sizeof(seen_));
    source_ = source;
    campaign_id_ = campaign_id;
    initialized_ = true;
}

}  // namespace lora_hello
