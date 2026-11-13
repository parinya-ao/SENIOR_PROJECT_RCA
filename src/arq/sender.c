#include "arq.h"
#include <string.h>

bool arq_due(uint32_t now,uint32_t deadline) { return (int32_t)(now-deadline)>=0; }
void arq_sender_init(arq_sender* s) { memset(s,0,sizeof *s);s->sequence=ARQ_INITIAL_SEQUENCE; }
bool arq_sender_active(const arq_sender* s) {
    return s->state==ARQ_TRANSMITTING || s->state==ARQ_WAITING_ACK || s->state==ARQ_BACKOFF;
}
bool arq_sender_arm(arq_sender* s,uint32_t session) {
    if (s->armed && s->session==session) return true;
    if (arq_sender_active(s)) return false;
    bool has_start=s->has_start;uint32_t last_start=s->last_start;
    arq_sender_init(s);s->session=session;s->armed=true;
    // A new session cannot bypass the radio's minimum DATA start spacing.
    s->has_start=has_start;s->last_start=last_start;return true;
}
static void fail(arq_sender* s,arq_result result) {
    // FAILED retains diagnostics; this pair cannot carry different application data.
    s->state=ARQ_FAILED;s->result=result;s->used_up=true;
}
static void start(arq_sender* s,uint32_t now) {
    // TRANSMITTING hands one immutable frame to the radio adapter.
    s->state=ARQ_TRANSMITTING;s->last_start=now;s->has_start=true;++s->attempts;
}
bool arq_sender_request(arq_sender* s,const uint8_t* payload,size_t length,uint32_t now,uint32_t rto) {
    if (!s->armed || s->stopped || s->used_up || arq_sender_active(s) || !payload || length>32 ||
        rto<ARQ_ACK_MIN_MS || rto>ARQ_ACK_MAX_MS) return false;
    memset(&s->frame,0,sizeof s->frame);
    s->frame.type=ARQ_DATA;s->frame.src=ARQ_SENDER_ID;s->frame.dst=ARQ_RECEIVER_ID;
    s->frame.session=s->session;s->frame.sequence=s->sequence;
    s->frame.length=(uint8_t)length;memcpy(s->frame.payload,payload,length);
    s->attempts=0;s->interval=rto;s->result=ARQ_PENDING;
    uint32_t bound=0;
    for (uint8_t i=0;i<=ARQ_MAX_RETRIES;i++) bound+=(rto<<i)+ARQ_TX_MS+ARQ_SPACING_MS;
    s->terminal_at=now+bound;
    s->retry_at=s->has_start?s->last_start+ARQ_SPACING_MS:now;
    // BACKOFF also enforces spacing between separate explicit requests.
    s->state=ARQ_BACKOFF;
    if (arq_due(now,s->retry_at)) start(s,now);
    return true;
}
void arq_sender_tx_done(arq_sender* s,uint32_t now,bool success) {
    if (s->state!=ARQ_TRANSMITTING) return;
    if (!success) { fail(s,ARQ_RADIO_ERROR);return; }
    // WAITING_ACK starts only after TxDone, cleanup and RX arming succeed.
    s->tx_done=now;s->retry_at=now+s->interval;s->state=ARQ_WAITING_ACK;
}
void arq_sender_control(arq_sender* s,const arq_frame* f,uint32_t now) {
    if ((s->state!=ARQ_WAITING_ACK && s->state!=ARQ_BACKOFF) || !s->attempts ||
        !arq_valid(f) || f->src!=ARQ_RECEIVER_ID || f->dst!=ARQ_SENDER_ID ||
        f->session!=s->session || f->sequence!=s->sequence) return;
    if (f->type==ARQ_ACK) {
        if (s->attempts==1) {
            s->rtt_last=now-s->tx_done;
            if (!s->rtt_count || s->rtt_last<s->rtt_min) s->rtt_min=s->rtt_last;
            if (!s->rtt_count || s->rtt_last>s->rtt_max) s->rtt_max=s->rtt_last;
            ++s->rtt_count;
        }
        // DELIVERED is the only transition that advances sequence.
        s->state=ARQ_DELIVERED;s->result=ARQ_OK;
        ++s->sequence;if (s->sequence==ARQ_INITIAL_SEQUENCE) s->used_up=true;
    } else if (f->type==ARQ_NACK) {
        if (f->reason==ARQ_APPLICATION_REJECTED) fail(s,ARQ_REJECTED);
        else if (f->reason==ARQ_UNEXPECTED_SEQUENCE) fail(s,ARQ_PROTOCOL_ERROR);
        // BUSY uses the same retry deadline; repeats never extend it.
        else s->state=ARQ_BACKOFF;
    }
}
void arq_sender_poll(arq_sender* s,uint32_t now) {
    if (!arq_sender_active(s)) return;
    if (arq_due(now,s->terminal_at)) { fail(s,ARQ_TIMEOUT_EXHAUSTED);return; }
    if (s->state==ARQ_TRANSMITTING) {
        if (now-s->last_start>=ARQ_TX_MS) fail(s,ARQ_RADIO_ERROR);
        return;
    }
    if (!arq_due(now,s->retry_at)) return;
    if (s->attempts>ARQ_MAX_RETRIES) { fail(s,ARQ_TIMEOUT_EXHAUSTED);return; }
    // BACKOFF adds spacing only, never another complete timeout interval.
    s->state=ARQ_BACKOFF;
    if (s->has_start && now-s->last_start<ARQ_SPACING_MS) return;
    if (s->attempts) s->interval*=2;
    start(s,now);
}
void arq_sender_stop(arq_sender* s) { s->stopped=true; }
