#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "reliable_transport.h"

struct FakeRadio {
    uint8_t local=0,source=0,destination=0,length=0,bytes[256]={};
    bool incoming=false,done=false,init_ok=true;
    unsigned starts=0,inits=0,sleeps=0;

    bool init(uint8_t address,float,int8_t,uint8_t) {
        ++inits;local=address;incoming=false;done=false;return init_ok;
    }
    void send(uint8_t dst,const uint8_t* payload,uint8_t size) {
        ++starts;done=false;destination=dst;length=size;
        memcpy(bytes,payload,size);
    }
    bool send_done() { return done; }
    bool available() { return incoming; }
    void recv(uint8_t* src,uint8_t* dst,uint8_t* payload,uint8_t* size) {
        incoming=false;*src=source;*dst=destination;*size=length;
        memcpy(payload,bytes,length);
    }
    int16_t sleep() { ++sleeps;return 0; }
};

using Transport=ReliableTransport<FakeRadio>;
struct Application { unsigned applied=0;bool reject=false; };
static bool accept(void* context,uint8_t sequence,const uint8_t* data,uint8_t size) {
    assert(sequence!=0);
    Application* app=static_cast<Application*>(context);
    if(app->reject || size==0 || data[0]!='h') return false;
    ++app->applied;return true;
}
static const uint8_t hello[]="hello world";

struct Pair {
    FakeRadio a,b;
    Application aa,bb;
    Transport x,y;
    explicit Pair(uint8_t first=0):x(a,915.0f,2,0),y(b,915.0f,2,0) {
        assert(x.arm(first,first^1,accept,&aa));
        assert(y.arm(first^1,first,accept,&bb));
    }
};

static void deliver(FakeRadio& from,FakeRadio& to) {
    to.source=from.local;to.destination=from.destination;to.length=from.length;
    memcpy(to.bytes,from.bytes,from.length);to.incoming=true;
}

static void start_data(Pair& p,uint8_t sequence=1,uint32_t now=0) {
    assert(p.x.send_reliable_data(sequence,hello,sizeof(hello)-1,now));
    assert(p.a.length==13 && p.a.bytes[0]==SSOT_DATA_TYPE &&
           p.a.bytes[1]==sequence && !memcmp(p.a.bytes+2,hello,sizeof(hello)-1));
    p.a.done=true;p.x.poll(now+1);
}

static void finish_reply(FakeRadio& radio,Transport& transport,uint32_t now) {
    radio.done=true;transport.poll(now);
}

static void successful_round_trip(Pair& p,uint32_t now=0) {
    deliver(p.a,p.b);p.y.poll(now+2);
    assert(p.b.length==2 && p.b.bytes[0]==SSOT_ACK_TYPE && p.b.bytes[1]==1);
    finish_reply(p.b,p.y,now+3);
    deliver(p.b,p.a);p.x.poll(now+4);
    assert(p.x.result()==Transport::Result::Accepted);
}

static bool dropped(unsigned loss_percent,uint32_t& random) {
    random=random*1664525U+1013904223U;
    return random%100U<loss_percent;
}

static bool loss_scenario(unsigned loss_percent,uint32_t seed,unsigned* attempts) {
    Pair p;uint32_t now=0,random=seed;
    assert(p.x.send_reliable_data(1,hello,sizeof(hello)-1,now));
    p.a.done=true;p.x.poll(++now);
    for(unsigned attempt=0;attempt<SSOT_MAX_ATTEMPTS &&
        p.x.result()==Transport::Result::Pending;++attempt) {
        if(!dropped(loss_percent,random)) {
            deliver(p.a,p.b);p.y.poll(++now);
            if(p.y.state()==Transport::State::TxResponse) {
                finish_reply(p.b,p.y,++now);
                if(!dropped(loss_percent,random)) {
                    deliver(p.b,p.a);p.x.poll(++now);
                }
            }
        }
        if(p.x.result()==Transport::Result::Accepted) break;
        if(p.x.state()==Transport::State::WaitResponse) {
            now+=LORA_ACK_TIMEOUT_MS+1U;p.x.poll(now);
        }
        if(p.x.state()==Transport::State::RetryPending) {
            p.x.poll(++now);
            if(p.x.state()==Transport::State::TxData) {
                p.a.done=true;p.x.poll(++now);
            }
        }
    }
    assert(p.x.attempts()<=SSOT_MAX_ATTEMPTS);
    if(p.x.result()==Transport::Result::Accepted) assert(p.bb.applied==1);
    else assert(p.x.result()==Transport::Result::AckTimeout);
    *attempts=p.x.attempts();
    return p.x.result()==Transport::Result::Accepted;
}

int main() {
    for(uint8_t first=0;first<2;++first) {
        Pair p(first);start_data(p);successful_round_trip(p);
        assert(p.bb.applied==1);
    }

    // A NACK requests a bounded retransmission; the next matching ACK accepts it.
    {
        Pair p;p.bb.reject=true;start_data(p);deliver(p.a,p.b);p.y.poll(2);
        assert(p.b.bytes[0]==SSOT_NACK_TYPE && p.b.bytes[1]==1);
        finish_reply(p.b,p.y,3);deliver(p.b,p.a);p.x.poll(4);
        assert(p.x.state()==Transport::State::RetryPending && p.x.attempts()==1);
        p.bb.reject=false;p.x.poll(5);
        assert(p.a.starts==2 && p.a.bytes[0]==SSOT_DATA_TYPE);
        p.a.done=true;p.x.poll(6);deliver(p.a,p.b);p.y.poll(7);
        finish_reply(p.b,p.y,8);deliver(p.b,p.a);p.x.poll(9);
        assert(p.x.result()==Transport::Result::Accepted && p.bb.applied==1);
    }

    // A lost NACK times out; a later NACK still schedules a bounded retry.
    {
        Pair p;p.bb.reject=true;start_data(p);deliver(p.a,p.b);p.y.poll(2);
        finish_reply(p.b,p.y,3); // Drop NACK.
        p.x.poll(LORA_ACK_TIMEOUT_MS+2);p.x.poll(LORA_ACK_TIMEOUT_MS+3);
        p.a.done=true;p.x.poll(LORA_ACK_TIMEOUT_MS+4);
        deliver(p.a,p.b);p.y.poll(LORA_ACK_TIMEOUT_MS+5);
        assert(p.b.bytes[0]==SSOT_NACK_TYPE);
        finish_reply(p.b,p.y,LORA_ACK_TIMEOUT_MS+6);
        deliver(p.b,p.a);p.x.poll(LORA_ACK_TIMEOUT_MS+7);
        assert(p.x.state()==Transport::State::RetryPending);
        assert(p.x.attempts()==2);
    }

    // A lost ACK causes a retry; the receiver ACKs the duplicate without reapplying it.
    {
        Pair p;start_data(p);deliver(p.a,p.b);p.y.poll(2);finish_reply(p.b,p.y,3);
        p.x.poll(LORA_ACK_TIMEOUT_MS+2);p.x.poll(LORA_ACK_TIMEOUT_MS+3);
        assert(p.a.starts==2);
        p.a.done=true;p.x.poll(LORA_ACK_TIMEOUT_MS+4);
        deliver(p.a,p.b);p.y.poll(LORA_ACK_TIMEOUT_MS+5);
        assert(p.bb.applied==1 && p.y.duplicates()==1);
        finish_reply(p.b,p.y,LORA_ACK_TIMEOUT_MS+6);
        deliver(p.b,p.a);p.x.poll(LORA_ACK_TIMEOUT_MS+7);
        assert(p.x.result()==Transport::Result::Accepted);
    }

    // An ACK arriving after the timeout cannot accept an attempt already queued for retry.
    {
        Pair p;start_data(p);p.x.poll(LORA_ACK_TIMEOUT_MS+2);
        assert(p.x.state()==Transport::State::RetryPending);
        p.a.source=1;p.a.destination=0;p.a.length=2;
        p.a.bytes[0]=SSOT_ACK_TYPE;p.a.bytes[1]=1;p.a.incoming=true;
        p.x.poll(LORA_ACK_TIMEOUT_MS+3);
        assert(p.x.state()==Transport::State::RetryPending &&
               p.x.result()==Transport::Result::Pending);
        p.x.poll(LORA_ACK_TIMEOUT_MS+4);p.a.done=true;
        p.x.poll(LORA_ACK_TIMEOUT_MS+5);
        p.a.incoming=true;p.a.source=1;p.a.destination=0;p.a.length=2;
        p.a.bytes[0]=SSOT_ACK_TYPE;p.a.bytes[1]=1;
        p.x.poll(LORA_ACK_TIMEOUT_MS+6);
        assert(p.x.result()==Transport::Result::Accepted);
        p.a.incoming=true;p.a.source=1;p.a.destination=0;p.a.length=2;
        p.a.bytes[0]=SSOT_ACK_TYPE;p.a.bytes[1]=1;
        p.x.poll(LORA_ACK_TIMEOUT_MS+7);
        assert(p.x.result()==Transport::Result::Accepted);
    }

    // Invalid, unrelated and oversized packets are discarded; RX is reinitialized.
    {
        Pair p;const unsigned before=p.b.inits;
        p.b.source=9;p.b.destination=1;p.b.length=3;
        p.b.bytes[0]=SSOT_DATA_TYPE;p.b.bytes[1]=1;p.b.bytes[2]='x';p.b.incoming=true;
        p.y.poll(1);assert(p.b.inits==before+1 && p.bb.applied==0);
        p.b.source=0;p.b.destination=1;p.b.length=252;p.b.incoming=true;
        p.y.poll(2);assert(p.b.inits==before+2 && p.bb.applied==0);
    }

    // The payload maximum keeps RadioHead's four-byte header within 255 bytes.
    {
        Pair p;uint8_t data[249];memset(data,'h',sizeof(data));
        assert(p.x.send_reliable_data(1,data,sizeof(data),0));
        assert(p.a.length==251 && p.a.bytes[0]==SSOT_DATA_TYPE);
    }

    // Radio initialization failure is reported; TX timeout stops without an unbounded loop.
    {
        FakeRadio radio;Application app;Transport transport(radio,915.0f,2,0);
        radio.init_ok=false;assert(!transport.arm(0,1,accept,&app));
        assert(transport.result()==Transport::Result::RadioError);
        radio.init_ok=true;assert(transport.arm(0,1,accept,&app));
    }
    {
        Pair p;assert(p.x.send_reliable_data(1,hello,sizeof(hello)-1,0));
        p.x.poll(LORA_TX_TIMEOUT_MS+1);
        assert(p.x.result()==Transport::Result::TxTimeout && !p.x.active());
    }

    // A fresh arm supports another bounded communication session.
    {
        Pair p;start_data(p);successful_round_trip(p);
        assert(p.x.arm(0,1,accept,&p.aa));
        assert(p.y.arm(1,0,accept,&p.bb));
        start_data(p,1,10000);successful_round_trip(p,10000);
        assert(p.bb.applied==2);
    }
    const unsigned losses[]={0U,5U,10U};
    for(size_t rate=0;rate<sizeof(losses)/sizeof(losses[0]);++rate) {
        unsigned delivered=0,total_attempts=0;
        for(uint32_t scenario=0;scenario<100;++scenario) {
            unsigned attempts=0;
            delivered+=loss_scenario(losses[rate],
                                     scenario+losses[rate]*1000U+1U,&attempts);
            total_attempts+=attempts;
        }
        printf("LOSS %u%% delivered=%u/100 attempts=%u\n",
               losses[rate],delivered,total_attempts);
    }
    puts("PASS stable-API transport: ACK/NACK, bounded retry, duplicate, bounds and rearm");
}
