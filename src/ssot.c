#include "ssot.h"

#include <string.h>

#ifndef HELLO_TEST_MODE
#define HELLO_TEST_MODE 0
#endif

#ifndef HELLO_RAM_ONLY_TEST
#define HELLO_RAM_ONLY_TEST 0
#endif

#if HELLO_RAM_ONLY_TEST && !HELLO_TEST_MODE
#error "RAM-only one-shot mode is restricted to the Hello test firmware."
#endif

static const char hello_payload[] = LORA_HELLO_PAYLOAD;
static const uint8_t campaign_messages = 20U;

_Static_assert(sizeof(hello_payload) - 1U == SSOT_HELLO_PAYLOAD_SIZE,
               "generated hello payload size mismatch");

static void encode_header(uint8_t destination, uint8_t source,
                          uint16_t campaign_id, uint8_t *output) {
    output[0] = destination;
    output[1] = source;
    /* Campaign IDs stay little-endian to preserve the existing wire format. */
    output[2] = (uint8_t)(campaign_id & 0xffU);
    output[3] = (uint8_t)(campaign_id >> 8);
}

bool ssot_encode_data_payload(uint8_t sequence, uint8_t *output,
                              size_t capacity, size_t *output_size) {
    if (output_size == NULL) {
        return false;
    }
    *output_size = 0U;
    if (output == NULL || capacity < SSOT_DATA_PAYLOAD_SIZE) {
        return false;
    }

    output[0] = (uint8_t)SSOT_DATA_TYPE;
    output[1] = sequence;
    memcpy(output + 2U, hello_payload, SSOT_HELLO_PAYLOAD_SIZE);
    *output_size = SSOT_DATA_PAYLOAD_SIZE;
    return true;
}

static bool encode_ack_or_nack_payload(uint8_t type, uint8_t sequence,
                                       uint8_t *output, size_t capacity,
                                       size_t *output_size) {
    if (output_size == NULL) {
        return false;
    }
    *output_size = 0U;
    if (output == NULL || capacity < SSOT_ACK_PAYLOAD_SIZE) {
        return false;
    }

    output[0] = type;
    output[1] = sequence;
    *output_size = SSOT_ACK_PAYLOAD_SIZE;
    return true;
}

bool ssot_encode_ack_payload(uint8_t sequence, uint8_t *output,
                             size_t capacity, size_t *output_size) {
    return encode_ack_or_nack_payload((uint8_t)SSOT_ACK_TYPE, sequence,
                                      output, capacity, output_size);
}

bool ssot_encode_nack_payload(uint8_t sequence, uint8_t *output,
                              size_t capacity, size_t *output_size) {
    return encode_ack_or_nack_payload((uint8_t)SSOT_NACK_TYPE, sequence,
                                      output, capacity, output_size);
}

bool ssot_encode_data_frame(uint8_t destination, uint8_t source,
                            uint16_t campaign_id, uint8_t sequence,
                            uint8_t *output, size_t capacity,
                            size_t *output_size) {
    if (output_size == NULL) {
        return false;
    }
    *output_size = 0U;
    if (output == NULL || capacity < SSOT_DATA_FRAME_SIZE) {
        return false;
    }

    encode_header(destination, source, campaign_id, output);
    size_t payload_size = 0U;
    if (!ssot_encode_data_payload(sequence,
                                  output + SSOT_RADIO_HEADER_SIZE,
                                  capacity - SSOT_RADIO_HEADER_SIZE,
                                  &payload_size)) {
        return false;
    }
    *output_size = SSOT_RADIO_HEADER_SIZE + payload_size;
    return true;
}

bool ssot_encode_ack_frame(uint8_t destination, uint8_t source,
                           uint16_t campaign_id, uint8_t sequence,
                           uint8_t *output, size_t capacity,
                           size_t *output_size) {
    if (output_size == NULL) {
        return false;
    }
    *output_size = 0U;
    if (output == NULL || capacity < SSOT_ACK_FRAME_SIZE) {
        return false;
    }

    encode_header(destination, source, campaign_id, output);
    size_t payload_size = 0U;
    if (!ssot_encode_ack_payload(sequence,
                                 output + SSOT_RADIO_HEADER_SIZE,
                                 capacity - SSOT_RADIO_HEADER_SIZE,
                                 &payload_size)) {
        return false;
    }
    *output_size = SSOT_RADIO_HEADER_SIZE + payload_size;
    return true;
}

static bool decode_payload(uint8_t destination, uint8_t source, uint8_t id,
                           uint8_t flags, const uint8_t *payload,
                           size_t payload_size, ssot_frame_t *frame) {
    if (payload == NULL || frame == NULL || payload_size < 1U) {
        return false;
    }

    if (payload[0] == SSOT_DATA_TYPE) {
        if (payload_size != SSOT_DATA_PAYLOAD_SIZE ||
            memcmp(payload + 2U, hello_payload, SSOT_HELLO_PAYLOAD_SIZE) != 0) {
            return false;
        }
    } else if (payload[0] == SSOT_ACK_TYPE || payload[0] == SSOT_NACK_TYPE) {
        if (payload_size != SSOT_ACK_PAYLOAD_SIZE) {
            return false;
        }
    } else {
        return false;
    }

    frame->destination = destination;
    frame->source = source;
    frame->campaign_id = (uint16_t)((uint16_t)id | ((uint16_t)flags << 8));
    frame->type = payload[0];
    frame->sequence = payload[1];
    return true;
}

bool ssot_decode_payload(uint8_t destination, uint8_t source, uint8_t id,
                         uint8_t flags, const uint8_t *payload,
                         size_t payload_size, ssot_frame_t *frame) {
    return decode_payload(destination, source, id, flags, payload, payload_size,
                          frame);
}

bool ssot_decode_frame(const uint8_t *input, size_t input_size,
                       ssot_frame_t *frame) {
    if (input == NULL || frame == NULL ||
        input_size < SSOT_RADIO_HEADER_SIZE + 1U) {
        return false;
    }
    return decode_payload(input[0], input[1], input[2], input[3],
                          input + SSOT_RADIO_HEADER_SIZE,
                          input_size - SSOT_RADIO_HEADER_SIZE, frame);
}

uint8_t ssot_reply_for_data(uint8_t destination, uint8_t source,
                            uint8_t id, uint8_t flags,
                            const uint8_t *payload, size_t payload_size,
                            uint16_t session, ssot_frame_t *frame) {
    const uint16_t received =
        (uint16_t)((uint16_t)id | ((uint16_t)flags << 8));
    if (session == 0U || received != session ||
        source != SSOT_SENDER_ADDRESS || destination != SSOT_RECEIVER_ADDRESS ||
        payload == NULL || payload_size < 2U ||
        payload[0] != SSOT_DATA_TYPE || payload[1] != SSOT_SEQUENCE ||
        frame == NULL) {
        return 0U;
    }

    *frame = (ssot_frame_t){destination, source, session,
                            (uint8_t)SSOT_DATA_TYPE, (uint8_t)SSOT_SEQUENCE};
    return decode_payload(destination, source, id, flags, payload, payload_size,
                          frame)
               ? (uint8_t)SSOT_ACK_TYPE
               : (uint8_t)SSOT_NACK_TYPE;
}

bool ssot_ack_matches(const ssot_frame_t *frame, uint8_t source,
                      uint8_t destination, uint16_t campaign_id,
                      uint8_t sequence) {
    return frame != NULL && frame->type == SSOT_ACK_TYPE &&
           frame->source == source && frame->destination == destination &&
           frame->campaign_id == campaign_id && frame->sequence == sequence;
}

void ssot_campaign_init(ssot_campaign_t *campaign, uint8_t source,
                        uint8_t destination, bool single_packet) {
    if (campaign == NULL) {
        return;
    }
    *campaign = (ssot_campaign_t){source, destination, 0U, 1U, 0U,
                                  SSOT_TEST_IDLE, single_packet};
}

bool ssot_campaign_arm(ssot_campaign_t *campaign, uint16_t campaign_id) {
    if (campaign == NULL || campaign->state != SSOT_TEST_IDLE) {
        return false;
    }
    campaign->campaign_id = campaign_id;
    campaign->state = SSOT_TEST_ARMED;
    return true;
}

bool ssot_campaign_start(ssot_campaign_t *campaign) {
    if (campaign == NULL || campaign->state != SSOT_TEST_ARMED) {
        return false;
    }
    if (campaign->sequence == 1U) {
        campaign->attempts = 0U;
    }
    campaign->state = SSOT_TEST_RUNNING;
    return true;
}

bool ssot_campaign_mark_sent(ssot_campaign_t *campaign) {
    uint8_t max_attempts = (uint8_t)SSOT_MAX_ATTEMPTS;
    if (campaign == NULL || campaign->state != SSOT_TEST_RUNNING) {
        return false;
    }
#if HELLO_RAM_ONLY_TEST
    if (campaign->single_packet) {
        max_attempts = 1U;
    }
#endif
    if (campaign->attempts >= max_attempts) {
        return false;
    }
    ++campaign->attempts;
    return true;
}

bool ssot_campaign_timeout(ssot_campaign_t *campaign) {
    uint8_t max_attempts = (uint8_t)SSOT_MAX_ATTEMPTS;
    if (campaign == NULL || campaign->state != SSOT_TEST_RUNNING ||
        campaign->attempts == 0U) {
        return false;
    }
#if HELLO_RAM_ONLY_TEST
    if (campaign->single_packet) {
        max_attempts = 1U;
    }
#endif
    if (campaign->attempts >= max_attempts) {
        campaign->state = SSOT_TEST_FAILED;
        return false;
    }
    return true;
}

bool ssot_campaign_acknowledge(ssot_campaign_t *campaign,
                               const ssot_frame_t *frame) {
    if (campaign == NULL || campaign->state != SSOT_TEST_RUNNING ||
        campaign->attempts == 0U ||
        !ssot_ack_matches(frame, campaign->destination, campaign->source,
                          campaign->campaign_id, campaign->sequence)) {
        return false;
    }
    if (campaign->single_packet) {
        campaign->state = SSOT_TEST_COMPLETED;
    } else if (campaign->sequence == 1U) {
        campaign->sequence = 2U;
        campaign->attempts = 0U;
        campaign->state = SSOT_TEST_ARMED;
    } else if (campaign->sequence == campaign_messages) {
        campaign->state = SSOT_TEST_COMPLETED;
    } else {
        ++campaign->sequence;
        campaign->attempts = 0U;
    }
    return true;
}

bool ssot_campaign_reject(ssot_campaign_t *campaign,
                          const ssot_frame_t *frame) {
    if (campaign == NULL || frame == NULL || frame->type != SSOT_NACK_TYPE ||
        campaign->state != SSOT_TEST_RUNNING || campaign->attempts == 0U) {
        return false;
    }
    ssot_frame_t ack = *frame;
    ack.type = (uint8_t)SSOT_ACK_TYPE;
    return ssot_ack_matches(&ack, campaign->destination, campaign->source,
                            campaign->campaign_id, campaign->sequence) &&
           ssot_campaign_timeout(campaign);
}

void ssot_campaign_fail(ssot_campaign_t *campaign) {
    if (campaign != NULL &&
        (campaign->state == SSOT_TEST_IDLE ||
         campaign->state == SSOT_TEST_ARMED ||
         campaign->state == SSOT_TEST_RUNNING)) {
        campaign->state = SSOT_TEST_FAILED;
    }
}

bool ssot_campaign_normal_reception_enabled(
    const ssot_campaign_t *campaign) {
    return campaign != NULL && !campaign->single_packet &&
           campaign->state != SSOT_TEST_ARMED &&
           campaign->state != SSOT_TEST_RUNNING;
}

uint32_t ssot_campaign_build_id(const char *build_marker) {
    if (build_marker == NULL) {
        return 0U;
    }
    uint32_t hash = UINT32_C(2166136261);
    while (*build_marker != '\0') {
        hash ^= (uint8_t)*build_marker++;
        hash *= UINT32_C(16777619);
    }
    if (hash == 0U || hash == UINT32_MAX) {
        --hash;
    }
    return hash;
}

uint32_t ssot_min_interval_ms_for_one_percent(uint32_t airtime_us) {
    const uint64_t interval_ms =
        ((uint64_t)airtime_us * 100U + 999U) / 1000U;
    return (uint32_t)interval_ms;
}

void ssot_duplicate_tracker_init(ssot_duplicate_tracker_t *tracker) {
    if (tracker != NULL) {
        memset(tracker, 0, sizeof *tracker);
    }
}

void ssot_duplicate_tracker_reset(ssot_duplicate_tracker_t *tracker) {
    if (tracker != NULL) {
        memset(tracker->seen, 0, sizeof tracker->seen);
        tracker->initialized = false;
    }
}

static void duplicate_tracker_reset_session(ssot_duplicate_tracker_t *tracker,
                                            uint8_t source,
                                            uint16_t campaign_id) {
    memset(tracker->seen, 0, sizeof tracker->seen);
    tracker->source = source;
    tracker->campaign_id = campaign_id;
    tracker->initialized = true;
}

bool ssot_duplicate_tracker_observe(ssot_duplicate_tracker_t *tracker,
                                    uint8_t source, uint16_t campaign_id,
                                    uint8_t sequence) {
    if (tracker == NULL) {
        return false;
    }
    if (!tracker->initialized || tracker->source != source ||
        tracker->campaign_id != campaign_id) {
        duplicate_tracker_reset_session(tracker, source, campaign_id);
    }

    const uint8_t mask = (uint8_t)(1U << (sequence & 7U));
    uint8_t *byte = &tracker->seen[sequence >> 3];
    const bool duplicate = (*byte & mask) != 0U;
    *byte = (uint8_t)(*byte | mask);
    return duplicate;
}

void ssot_control_input_init(ssot_control_input_t *input, char command) {
    if (input != NULL) {
        *input = (ssot_control_input_t){command, 0U, 0U, 0U, false, false};
    }
}

bool ssot_control_input_feed(ssot_control_input_t *input, char value,
                             uint32_t now_ms, uint16_t *session) {
    if (input == NULL || input->triggered || session == NULL) {
        return false;
    }
    if (input->reading && now_ms - input->last_ms > 1000U) {
        input->reading = false;
    }
    if (value == input->command) {
        input->reading = true;
        input->digits = 0U;
        input->value = 0U;
        input->last_ms = now_ms;
        return false;
    }
    if (!input->reading) {
        return false;
    }

    uint8_t digit;
    if (value >= '0' && value <= '9') {
        digit = (uint8_t)(value - '0');
    } else if (value >= 'A' && value <= 'F') {
        digit = (uint8_t)(value - 'A' + 10);
    } else {
        input->reading = false;
        return false;
    }

    input->value = (uint16_t)((input->value << 4) | digit);
    input->last_ms = now_ms;
    ++input->digits;
    if (input->digits != 4U) {
        return false;
    }
    input->reading = false;
    if (input->value == 0U) {
        return false;
    }
    *session = input->value;
    input->triggered = true;
    return true;
}
