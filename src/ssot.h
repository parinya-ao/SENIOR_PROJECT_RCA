#ifndef SSOT_H
#define SSOT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "generated/lora_shared_config.h"

#ifdef __cplusplus
extern "C" {
#endif

/* LORA_* values keep C and Arduino callers on generated project settings. */
enum {
    SSOT_RADIO_HEADER_SIZE = 4U,
    SSOT_DATA_TYPE = LORA_DATA_TYPE,
    SSOT_ACK_TYPE = LORA_ACK_TYPE,
    SSOT_NACK_TYPE = LORA_NACK_TYPE,
    SSOT_SENDER_ADDRESS = LORA_SENDER_ADDRESS,
    SSOT_RECEIVER_ADDRESS = LORA_RECEIVER_ADDRESS,
    SSOT_SEQUENCE = LORA_SEQUENCE,
    SSOT_HELLO_PAYLOAD_SIZE = sizeof(LORA_HELLO_PAYLOAD) - 1U,
    SSOT_DATA_PAYLOAD_SIZE = 2U + SSOT_HELLO_PAYLOAD_SIZE,
    SSOT_ACK_PAYLOAD_SIZE = 2U,
    SSOT_DATA_FRAME_SIZE = SSOT_RADIO_HEADER_SIZE + SSOT_DATA_PAYLOAD_SIZE,
    SSOT_ACK_FRAME_SIZE = SSOT_RADIO_HEADER_SIZE + SSOT_ACK_PAYLOAD_SIZE,
    SSOT_MAX_RETRIES = LORA_MAX_RETRIES,
    SSOT_MAX_ATTEMPTS = 1U + SSOT_MAX_RETRIES
};

typedef struct {
    uint8_t destination;
    uint8_t source;
    uint16_t campaign_id;
    uint8_t type;
    uint8_t sequence;
} ssot_frame_t;

typedef enum {
    SSOT_TEST_IDLE,
    SSOT_TEST_ARMED,
    SSOT_TEST_RUNNING,
    SSOT_TEST_COMPLETED,
    SSOT_TEST_FAILED
} ssot_state_t;

typedef struct {
    uint8_t source;
    uint8_t destination;
    uint16_t campaign_id;
    uint8_t sequence;
    uint8_t attempts;
    ssot_state_t state;
    bool single_packet;
} ssot_campaign_t;

typedef struct {
    uint8_t source;
    uint16_t campaign_id;
    bool initialized;
    uint8_t seen[32];
} ssot_duplicate_tracker_t;

typedef struct {
    char command;
    uint8_t digits;
    uint16_t value;
    uint32_t last_ms;
    bool reading;
    bool triggered;
} ssot_control_input_t;

bool ssot_encode_data_frame(uint8_t destination, uint8_t source,
                            uint16_t campaign_id, uint8_t sequence,
                            uint8_t *output, size_t capacity,
                            size_t *output_size);
bool ssot_encode_data_payload(uint8_t sequence, uint8_t *output,
                              size_t capacity, size_t *output_size);
bool ssot_encode_ack_payload(uint8_t sequence, uint8_t *output,
                             size_t capacity, size_t *output_size);
bool ssot_encode_nack_payload(uint8_t sequence, uint8_t *output,
                              size_t capacity, size_t *output_size);
bool ssot_encode_ack_frame(uint8_t destination, uint8_t source,
                           uint16_t campaign_id, uint8_t sequence,
                           uint8_t *output, size_t capacity,
                           size_t *output_size);
bool ssot_decode_frame(const uint8_t *input, size_t input_size,
                       ssot_frame_t *frame);
bool ssot_decode_payload(uint8_t destination, uint8_t source, uint8_t id,
                         uint8_t flags, const uint8_t *payload,
                         size_t payload_size, ssot_frame_t *frame);
uint8_t ssot_reply_for_data(uint8_t destination, uint8_t source,
                            uint8_t id, uint8_t flags,
                            const uint8_t *payload, size_t payload_size,
                            uint16_t session, ssot_frame_t *frame);
bool ssot_ack_matches(const ssot_frame_t *frame, uint8_t source,
                      uint8_t destination, uint16_t campaign_id,
                      uint8_t sequence);
void ssot_campaign_init(ssot_campaign_t *campaign, uint8_t source,
                        uint8_t destination, bool single_packet);
bool ssot_campaign_arm(ssot_campaign_t *campaign, uint16_t campaign_id);
bool ssot_campaign_start(ssot_campaign_t *campaign);
bool ssot_campaign_mark_sent(ssot_campaign_t *campaign);
bool ssot_campaign_timeout(ssot_campaign_t *campaign);
bool ssot_campaign_acknowledge(ssot_campaign_t *campaign,
                               const ssot_frame_t *frame);
bool ssot_campaign_reject(ssot_campaign_t *campaign,
                          const ssot_frame_t *frame);
void ssot_campaign_fail(ssot_campaign_t *campaign);
bool ssot_campaign_normal_reception_enabled(
    const ssot_campaign_t *campaign);
uint32_t ssot_campaign_build_id(const char *build_marker);
uint32_t ssot_min_interval_ms_for_one_percent(uint32_t airtime_us);
void ssot_duplicate_tracker_init(ssot_duplicate_tracker_t *tracker);
bool ssot_duplicate_tracker_observe(ssot_duplicate_tracker_t *tracker,
                                    uint8_t source, uint16_t campaign_id,
                                    uint8_t sequence);
void ssot_duplicate_tracker_reset(ssot_duplicate_tracker_t *tracker);
void ssot_control_input_init(ssot_control_input_t *input, char command);
bool ssot_control_input_feed(ssot_control_input_t *input, char value,
                             uint32_t now_ms, uint16_t *session);

#ifdef __cplusplus
}
#endif

#endif
