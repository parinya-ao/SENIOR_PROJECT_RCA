#include "ssot.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    static const uint8_t expected[] = {
        0x01, 0x00, 0x34, 0x12, 0x08, 0x01,
        'h', 'e', 'l', 'l', 'o', ' ', 'w', 'o', 'r', 'l', 'd'
    };
    uint8_t frame[sizeof expected];
    size_t frame_size = 0U;

    assert(ssot_encode_data_frame(1U, 0U, 0x1234U, 1U, frame,
                                  sizeof frame, &frame_size));
    assert(frame_size == sizeof expected);
    assert(memcmp(frame, expected, sizeof expected) == 0);

    static const uint8_t expected_ack[] = {0x00, 0x01, 0x34, 0x12, 0x03, 0x01};
    assert(ssot_encode_ack_frame(0U, 1U, 0x1234U, 1U, frame,
                                 sizeof frame, &frame_size));
    assert(frame_size == sizeof expected_ack);
    assert(memcmp(frame, expected_ack, sizeof expected_ack) == 0);
    frame_size = sizeof frame;
    assert(!ssot_encode_ack_frame(0U, 1U, 0x1234U, 1U, frame,
                                  sizeof expected_ack - 1U, &frame_size));
    assert(frame_size == 0U);

    static const uint8_t expected_data_payload[] = {
        0x08, 0x01, 'h', 'e', 'l', 'l', 'o', ' ', 'w', 'o', 'r', 'l', 'd'
    };
    static const uint8_t expected_ack_payload[] = {0x03, 0x01};
    static const uint8_t expected_nack_payload[] = {0x09, 0x01};
    uint8_t payload[SSOT_DATA_PAYLOAD_SIZE];
    size_t payload_size = 0U;
    assert(ssot_encode_data_payload(1U, payload, sizeof payload, &payload_size));
    assert(payload_size == sizeof expected_data_payload);
    assert(memcmp(payload, expected_data_payload, sizeof expected_data_payload) == 0);
    assert(ssot_encode_ack_payload(1U, payload, sizeof payload, &payload_size));
    assert(payload_size == sizeof expected_ack_payload);
    assert(memcmp(payload, expected_ack_payload, sizeof expected_ack_payload) == 0);
    assert(ssot_encode_nack_payload(1U, payload, sizeof payload, &payload_size));
    assert(payload_size == sizeof expected_nack_payload);
    assert(memcmp(payload, expected_nack_payload, sizeof expected_nack_payload) == 0);

    ssot_frame_t decoded = {0};
    assert(ssot_decode_frame(expected, sizeof expected, &decoded));
    assert(decoded.destination == 1U && decoded.source == 0U);
    assert(decoded.campaign_id == 0x1234U && decoded.sequence == 1U);
    assert(decoded.type == 8U);
    assert(!ssot_decode_frame(expected, sizeof expected - 1U, &decoded));
    assert(ssot_decode_payload(1U, 0U, 0x34U, 0x12U, expected + 4U,
                               sizeof expected - 4U, &decoded));
    assert(decoded.type == 8U && decoded.campaign_id == 0x1234U);
    assert(ssot_reply_for_data(1U, 0U, 0x34U, 0x12U, expected + 4U,
                               sizeof expected - 4U, 0x1234U, &decoded) == 3U);
    assert(decoded.type == 8U && decoded.sequence == 1U);
    assert(ssot_reply_for_data(1U, 0U, 0x34U, 0x12U, expected + 4U,
                               sizeof expected - 5U, 0x1234U, &decoded) == 9U);
    assert(ssot_reply_for_data(1U, 0U, 0x34U, 0x12U, expected + 4U,
                               sizeof expected - 4U, 0x1235U, &decoded) == 0U);

    const ssot_frame_t correct_ack = {0U, 1U, 0x1234U, 3U, 1U};
    assert(ssot_ack_matches(&correct_ack, 1U, 0U, 0x1234U, 1U));
    assert(!ssot_ack_matches(&correct_ack, 1U, 0U, 0x1235U, 1U));

    ssot_campaign_t campaign;
    ssot_campaign_init(&campaign, 0U, 1U, true);
    assert(campaign.state == SSOT_TEST_IDLE);
    assert(!ssot_campaign_normal_reception_enabled(&campaign));
    assert(ssot_campaign_arm(&campaign, 0x1234U));
    assert(!ssot_campaign_arm(&campaign, 0x1235U));
    assert(ssot_campaign_start(&campaign));
    assert(ssot_campaign_mark_sent(&campaign));
    assert(!ssot_campaign_acknowledge(&campaign, &decoded));
    assert(ssot_campaign_acknowledge(&campaign, &correct_ack));
    assert(campaign.state == SSOT_TEST_COMPLETED && campaign.sequence == 1U);
    assert(!ssot_campaign_mark_sent(&campaign));
    assert(!ssot_campaign_normal_reception_enabled(&campaign));

    ssot_campaign_t retries;
    ssot_campaign_init(&retries, 0U, 1U, false);
    assert(ssot_campaign_arm(&retries, 0x2001U));
    assert(ssot_campaign_start(&retries));
    for (uint8_t attempt = 0U; attempt < SSOT_MAX_ATTEMPTS; ++attempt) {
        assert(ssot_campaign_mark_sent(&retries));
        assert(ssot_campaign_timeout(&retries) ==
               (attempt + 1U < SSOT_MAX_ATTEMPTS));
    }
    assert(retries.state == SSOT_TEST_FAILED);
    assert(ssot_campaign_normal_reception_enabled(&retries));

#if defined(HELLO_RAM_ONLY_TEST) && HELLO_RAM_ONLY_TEST
    ssot_campaign_t ram_only;
    ssot_campaign_init(&ram_only, 0U, 1U, true);
    assert(ssot_campaign_arm(&ram_only, 0x3001U));
    assert(ssot_campaign_start(&ram_only));
    assert(ssot_campaign_mark_sent(&ram_only));
    assert(!ssot_campaign_mark_sent(&ram_only));
    assert(!ssot_campaign_timeout(&ram_only));
    assert(ram_only.state == SSOT_TEST_FAILED);
#endif

    assert(ssot_campaign_build_id(NULL) == 0U);
    assert(ssot_campaign_build_id("sender build-a") != 0U);
    assert(ssot_campaign_build_id("sender build-a") != UINT32_MAX);
    assert(ssot_campaign_build_id("sender build-a") ==
           ssot_campaign_build_id("sender build-a"));
    assert(ssot_campaign_build_id("sender build-a") !=
           ssot_campaign_build_id("sender build-b"));
    assert(ssot_min_interval_ms_for_one_percent(0U) == 0U);
    assert(ssot_min_interval_ms_for_one_percent(1U) == 1U);
    assert(ssot_min_interval_ms_for_one_percent(1000U) == 100U);
    assert(ssot_min_interval_ms_for_one_percent(1001U) == 101U);
    assert(ssot_min_interval_ms_for_one_percent(1000000U) == 100000U);

    ssot_duplicate_tracker_t duplicates;
    ssot_duplicate_tracker_init(&duplicates);
    assert(!ssot_duplicate_tracker_observe(&duplicates, 0U, 0x1234U, 1U));
    assert(ssot_duplicate_tracker_observe(&duplicates, 0U, 0x1234U, 1U));
    assert(!ssot_duplicate_tracker_observe(&duplicates, 0U, 0x1234U, 2U));
    assert(ssot_duplicate_tracker_observe(&duplicates, 0U, 0x1234U, 1U));
    assert(!ssot_duplicate_tracker_observe(&duplicates, 0U, 0x1235U, 1U));
    assert(!ssot_duplicate_tracker_observe(&duplicates, 1U, 0x1235U, 1U));
    assert(!ssot_duplicate_tracker_observe(&duplicates, 1U, 0x1235U, 255U));
    assert(ssot_duplicate_tracker_observe(&duplicates, 1U, 0x1235U, 255U));
    ssot_duplicate_tracker_reset(&duplicates);
    assert(!ssot_duplicate_tracker_observe(&duplicates, 1U, 0x1235U, 255U));

    ssot_control_input_t control;
    uint16_t session = 0U;
    ssot_control_input_init(&control, 'S');
    assert(!ssot_control_input_feed(&control, 'C', 0U, &session));
    assert(!ssot_control_input_feed(&control, 'S', 1U, &session));
    assert(!ssot_control_input_feed(&control, '1', 2U, &session));
    assert(!ssot_control_input_feed(&control, '2', 3U, &session));
    assert(!ssot_control_input_feed(&control, '3', 4U, &session));
    assert(ssot_control_input_feed(&control, '4', 5U, &session));
    assert(session == 0x1234U);
    assert(!ssot_control_input_feed(&control, 'S', 6U, &session));

    ssot_control_input_init(&control, 'S');
    assert(!ssot_control_input_feed(&control, 'S', 0U, &session));
    assert(!ssot_control_input_feed(&control, '1', 2000U, &session));
    assert(!ssot_control_input_feed(&control, '2', 2001U, &session));
    assert(!ssot_control_input_feed(&control, '3', 2002U, &session));
    assert(!ssot_control_input_feed(&control, '4', 2003U, &session));
    puts("PASS C protocol tests");
    return 0;
}
