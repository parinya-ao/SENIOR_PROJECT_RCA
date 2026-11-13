#include "arq.h"
#include <string.h>

void arq_receiver_init(arq_receiver* r) {
    memset(r,0,sizeof *r);r->expected=ARQ_INITIAL_SEQUENCE;
}
bool arq_receiver_arm(arq_receiver* r,uint32_t session) {
    if (r->armed && r->session==session) return true;
    if (r->state!=ARQ_LISTENING) return false;
    arq_receiver_init(r);r->armed=true;r->session=session;return true;
}
bool arq_receiver_data(arq_receiver* r,const arq_frame* f,arq_frame* response,bool busy) {
    if (!r->armed || r->stopped || !arq_valid(f) || f->type!=ARQ_DATA ||
        f->src!=ARQ_SENDER_ID || f->dst!=ARQ_RECEIVER_ID || f->session!=r->session) return false;
    // VALIDATING checks content before replaying a previously accepted ACK.
    r->state=ARQ_VALIDATING;
    memset(response,0,sizeof *response);response->type=ARQ_NACK;
    response->src=ARQ_RECEIVER_ID;response->dst=ARQ_SENDER_ID;
    response->session=r->session;response->sequence=f->sequence;
    if (f->length!=sizeof(ARQ_PAYLOAD)-1 || memcmp(f->payload,ARQ_PAYLOAD,sizeof(ARQ_PAYLOAD)-1))
        response->reason=ARQ_APPLICATION_REJECTED;
    else if (r->accepted && f->sequence==r->last_sequence) {
        response->type=ARQ_ACK;++r->duplicates;
    } else if (f->sequence!=r->expected) response->reason=ARQ_UNEXPECTED_SEQUENCE;
    else if (busy) response->reason=ARQ_BUSY;
    else {
        // Acceptance precedes TX: response failure must not erase deduplication.
        r->accepted=true;r->last_sequence=f->sequence;++r->expected;++r->deliveries;
        response->type=ARQ_ACK;
    }
    // The adapter owns SENDING_RESPONSE/RETURNING_TO_RX while the radio is busy.
    r->state=ARQ_LISTENING;return true;
}
