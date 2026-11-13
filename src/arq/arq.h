#ifndef RAW_ARQ_H
#define RAW_ARQ_H
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "generated/arq_config.h"
#ifdef __cplusplus
extern "C" {
#endif
enum { ARQ_DATA=1, ARQ_ACK=2, ARQ_NACK=3 };
enum { ARQ_NONE, ARQ_UNEXPECTED_SEQUENCE, ARQ_APPLICATION_REJECTED, ARQ_BUSY };
typedef struct {
    uint8_t type,src,dst;
    uint32_t session;
    uint16_t sequence;
    uint8_t length,reason,payload[32];
} arq_frame;
size_t arq_encode(const arq_frame*, uint8_t*, size_t);
bool arq_decode(arq_frame*, const uint8_t*, size_t);
bool arq_valid(const arq_frame*);
typedef enum { ARQ_IDLE, ARQ_TRANSMITTING, ARQ_WAITING_ACK, ARQ_BACKOFF,
               ARQ_DELIVERED, ARQ_FAILED } arq_sender_state;
typedef enum { ARQ_PENDING, ARQ_OK, ARQ_REJECTED, ARQ_PROTOCOL_ERROR,
               ARQ_TIMEOUT_EXHAUSTED, ARQ_RADIO_ERROR } arq_result;
typedef struct {
    arq_sender_state state;
    arq_result result;
    bool armed,stopped,has_start,used_up;
    uint32_t session,last_start,retry_at,terminal_at,interval,tx_done;
    uint32_t rtt_count,rtt_last,rtt_min,rtt_max;
    uint16_t sequence;
    uint8_t attempts;
    arq_frame frame;
} arq_sender;
bool arq_due(uint32_t now, uint32_t deadline);
void arq_sender_init(arq_sender*);
bool arq_sender_active(const arq_sender*);
bool arq_sender_arm(arq_sender*, uint32_t);
bool arq_sender_request(arq_sender*, const uint8_t*, size_t, uint32_t, uint32_t);
void arq_sender_tx_done(arq_sender*, uint32_t, bool);
void arq_sender_control(arq_sender*, const arq_frame*, uint32_t);
void arq_sender_poll(arq_sender*, uint32_t);
void arq_sender_stop(arq_sender*);
typedef enum { ARQ_LISTENING, ARQ_VALIDATING, ARQ_SENDING_RESPONSE,
               ARQ_RETURNING_TO_RX } arq_receiver_state;
typedef struct {
    bool armed,stopped,accepted;
    uint32_t session,deliveries,duplicates;
    uint16_t expected,last_sequence;
    arq_receiver_state state;
} arq_receiver;
void arq_receiver_init(arq_receiver*);
bool arq_receiver_arm(arq_receiver*, uint32_t);
bool arq_receiver_data(arq_receiver*, const arq_frame*, arq_frame*, bool);
#ifdef __cplusplus
}
#endif
#endif
