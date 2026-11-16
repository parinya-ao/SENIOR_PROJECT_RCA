#include "arq.h"
#include <string.h>

bool arq_valid(const arq_frame* f) {
    if (!f || f->length>32) return false;
    if (f->type==ARQ_DATA) return f->reason==ARQ_NONE;
    if (f->length) return false;
    if (f->type==ARQ_ACK) return f->reason==ARQ_NONE;
    return f->type==ARQ_NACK && f->reason>=ARQ_UNEXPECTED_SEQUENCE && f->reason<=ARQ_BUSY;
}
size_t arq_encode(const arq_frame* f, uint8_t* b, size_t capacity) {
    if (!arq_valid(f) || !b || capacity<(size_t)(12+f->length)) return 0;
    b[0]=1;b[1]=f->type;b[2]=f->src;b[3]=f->dst;
    for (uint8_t i=0;i<4;i++) b[4+i]=(uint8_t)(f->session>>(8*i));
    b[8]=(uint8_t)f->sequence;b[9]=(uint8_t)(f->sequence>>8);
    b[10]=f->length;b[11]=f->reason;
    memcpy(b+12,f->payload,f->length);return 12+f->length;
}
bool arq_decode(arq_frame* f, const uint8_t* b, size_t length) {
    if (!f || !b || length<12 || length>44 || b[0]!=1 || b[10]>32 || length!=(size_t)(12+b[10])) return false;
    arq_frame value={0};value.type=b[1];value.src=b[2];value.dst=b[3];
    for (uint8_t i=0;i<4;i++) value.session|=(uint32_t)b[4+i]<<(8*i);
    value.sequence=(uint16_t)b[8]|(uint16_t)b[9]<<8;
    value.length=b[10];value.reason=b[11];
    if (!arq_valid(&value)) return false;
    memcpy(value.payload,b+12,value.length);*f=value;return true;
}
