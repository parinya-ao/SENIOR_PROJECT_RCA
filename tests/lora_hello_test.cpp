#include "hello_protocol.h"

#include <cstdio>
#include <cstdlib>

using namespace lora_hello;

static unsigned checks = 0;

#define CHECK(condition) do { \
    ++checks; \
    if (!(condition)) { \
        std::fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); \
        return EXIT_FAILURE; \
    } \
} while (0)

int main() {
    const uint32_t build_id = campaign_build_id("sender_hello build-a");
    CHECK(build_id != 0 && build_id != UINT32_MAX);
    CHECK(build_id == campaign_build_id("sender_hello build-a"));
    CHECK(build_id != campaign_build_id("sender_hello build-b"));

    CHECK(min_interval_ms_for_one_percent(0) == 0);
    CHECK(min_interval_ms_for_one_percent(1) == 1);
    CHECK(min_interval_ms_for_one_percent(1000) == 100);
    CHECK(min_interval_ms_for_one_percent(1001) == 101);
    CHECK(min_interval_ms_for_one_percent(1000000) == 100000);

    static const uint8_t expected_data[] = {
        0x01, 0x00, 0x34, 0x12, kDataType, 0x01,
        'h', 'e', 'l', 'l', 'o', ' ', 'w', 'o', 'r', 'l', 'd'
    };
    static const uint8_t expected_ack[] = {
        0x00, 0x01, 0x34, 0x12, kAckType, 0x01
    };
    uint8_t bytes[kDataFrameSize] = {};
    size_t length = 0;

    CHECK(kHelloPayloadSize == 11);
    CHECK(encode_data_frame(1, 0, 0x1234, 1, bytes, sizeof(bytes), &length));
    CHECK(length == sizeof(expected_data));
    for (size_t i = 0; i < length; ++i) CHECK(bytes[i] == expected_data[i]);

    Frame frame{};
    CHECK(decode_frame(bytes, length, &frame));
    CHECK(frame.destination == 1 && frame.source == 0);
    CHECK(frame.campaign_id == 0x1234 && frame.sequence == 1);
    CHECK(frame.type == kDataType);
    CHECK(!decode_frame(bytes, length - 1, &frame));
    bytes[16] ^= 1;
    CHECK(!decode_frame(bytes, length, &frame));
    bytes[16] ^= 1;
    CHECK(!encode_data_frame(1, 0, 0x1234, 1, bytes, 16, &length));

    CHECK(encode_ack_frame(0, 1, 0x1234, 1, bytes, sizeof(bytes), &length));
    CHECK(length == sizeof(expected_ack));
    for (size_t i = 0; i < length; ++i) CHECK(bytes[i] == expected_ack[i]);
    CHECK(decode_frame(bytes, length, &frame));
    CHECK(frame.type == kAckType && frame.sequence == 1);
    CHECK(!decode_frame(bytes, length - 1, &frame));
    CHECK(ack_matches(frame, 1, 0, 0x1234, 1));

    CHECK(encode_data_frame(1, 0, 0x1234, 255, bytes, sizeof(bytes), &length));
    CHECK(decode_frame(bytes, length, &frame) && frame.sequence == 255);
    CHECK(encode_data_frame(1, 0, 0x1234, 0, bytes, sizeof(bytes), &length));
    CHECK(decode_frame(bytes, length, &frame) && frame.sequence == 0);

    DuplicateTracker duplicates;
    CHECK(!duplicates.observe(0, 0x1234, 1));
    CHECK(duplicates.observe(0, 0x1234, 1));
    CHECK(!duplicates.observe(0, 0x1234, 2));
    CHECK(duplicates.observe(0, 0x1234, 1));
    CHECK(!duplicates.observe(0, 0x1235, 1));
    CHECK(!duplicates.observe(1, 0x1235, 1));

    Campaign campaign(0, 1);
    CHECK(campaign.normal_reception_enabled());
    CHECK(campaign.arm(0x1234));
    CHECK(campaign.state() == State::TEST_ARMED);
    CHECK(!campaign.normal_reception_enabled());
    CHECK(!campaign.arm(0x1235));
    CHECK(campaign.start());
    CHECK(!campaign.start());
    CHECK(campaign.sequence() == 1);
    CHECK(campaign.mark_sent());

    Frame ack{0, 1, 0x1235, kAckType, 1};
    CHECK(!campaign.acknowledge(ack));
    ack.campaign_id = 0x1234;
    ack.source = 0;
    CHECK(!campaign.acknowledge(ack));
    ack.source = 1;
    ack.destination = 1;
    CHECK(!campaign.acknowledge(ack));
    ack.destination = 0;
    ack.sequence = 2;
    CHECK(!campaign.acknowledge(ack));
    ack.sequence = 1;
    CHECK(campaign.acknowledge(ack));
    CHECK(campaign.sequence() == 2 && campaign.attempts() == 0);
    CHECK(campaign.state() == State::TEST_ARMED);
    CHECK(!campaign.normal_reception_enabled());
    CHECK(campaign.start());  // Continue only after the first DATA/ACK succeeds.
    CHECK(campaign.state() == State::TEST_RUNNING);
    CHECK(!campaign.acknowledge(ack));

    Campaign retries(0, 1);
    CHECK(retries.arm(0x2001) && retries.start());
    for (unsigned attempt = 0; attempt < kMaxAttempts; ++attempt) {
        CHECK(retries.mark_sent());
        const bool retry = retries.timeout();
        CHECK(retry == (attempt + 1 < kMaxAttempts));
    }
    CHECK(retries.state() == State::TEST_FAILED);
    CHECK(retries.normal_reception_enabled());
    CHECK(!retries.mark_sent());
    CHECK(!retries.arm(0x2002));

    Campaign complete(0, 1);
    CHECK(complete.arm(0x4321) && complete.start());
    CHECK(complete.mark_sent());
    Frame first_ack{0, 1, 0x4321, kAckType, 1};
    CHECK(complete.acknowledge(first_ack));
    CHECK(complete.state() == State::TEST_ARMED && complete.sequence() == 2);
    CHECK(complete.start());
    for (uint8_t sequence = 2; sequence <= kCampaignMessages; ++sequence) {
        CHECK(complete.mark_sent());
        Frame current_ack{0, 1, 0x4321, kAckType, sequence};
        CHECK(complete.acknowledge(current_ack));
        CHECK(complete.sequence() == (sequence < kCampaignMessages
                                           ? static_cast<uint8_t>(sequence + 1)
                                           : sequence));
    }
    CHECK(complete.state() == State::TEST_COMPLETED);
    CHECK(complete.normal_reception_enabled());
    CHECK(!complete.arm(0x4322));

    std::printf("PASS %u checks\n", checks);
    return EXIT_SUCCESS;
}
