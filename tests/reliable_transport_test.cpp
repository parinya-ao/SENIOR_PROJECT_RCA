#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "reliable_transport.h"

struct FakeRadio {
    uint8_t local=0,source=0,destination=0,length=0,bytes[256]={};
    bool incoming=false,done=false,init_ok=true;
    unsigned starts=0,inits=0,sleeps=0;
    int16_t send_error=0,completion_error=0,receive_error=0;

    int16_t init(uint8_t address,float,int8_t,uint8_t) {
        ++inits;local=address;incoming=false;done=false;return init_ok?0:-1;
    }
    int16_t send(uint8_t dst,const uint8_t* payload,uint8_t size) {
        ++starts;done=false;destination=dst;length=size;
        memcpy(bytes,payload,size);return send_error;
    }
    int16_t send_done() { return completion_error ? completion_error : (done ? 1 : 0); }
    bool available() { return incoming; }
    int16_t recv(uint8_t* src,uint8_t* dst,uint8_t* payload,size_t capacity,uint8_t* size) {
        incoming=false;*src=source;*dst=destination;*size=length;
        if(receive_error) { *size=0;return receive_error; }
        assert(length<=capacity);memcpy(payload,bytes,length);return 0;
    }
    int16_t sleep() { ++sleeps;return 0; }
};

using Transport=ReliableTransport<FakeRadio>;
struct Application { unsigned applied=0;bool reject=false; };
struct EventStats {
    unsigned data_tx=0,ack_tx=0,nack_tx=0,ack_accepted=0,nack_received=0;
    unsigned retries=0,duplicates=0,failures=0,total=0;
};

static void count_event(void* context,const char* event,uint8_t,uint8_t,int16_t) {
    EventStats* stats=static_cast<EventStats*>(context);
    ++stats->total;
    if(!strcmp(event,"DATA_TX_BEGIN")) ++stats->data_tx;
    else if(!strcmp(event,"ACK_TX_BEGIN")) ++stats->ack_tx;
    else if(!strcmp(event,"NACK_TX_BEGIN")) ++stats->nack_tx;
    else if(!strcmp(event,"ACK_ACCEPTED")) ++stats->ack_accepted;
    else if(!strcmp(event,"NACK_RX")) ++stats->nack_received;
    else if(!strcmp(event,"RETRY_SCHEDULED")) ++stats->retries;
    else if(!strcmp(event,"DATA_DUP")) ++stats->duplicates;
    else if(!strcmp(event,"TRANSACTION_FAILED")) ++stats->failures;
}

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
    EventStats events;
    Transport x,y;
    explicit Pair(uint8_t first=0):x(a,915.0f,2,0),y(b,915.0f,2,0) {
        x.on_event(count_event,&events);y.on_event(count_event,&events);
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

struct LossMetrics {
    unsigned attempts=0,ack_tx=0,nack_tx=0,retries=0,timeouts=0,duplicates=0;
};

static bool loss_scenario(unsigned loss_percent,uint32_t seed,LossMetrics* metrics) {
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
            ++metrics->timeouts;
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
    metrics->attempts=p.x.attempts();
    metrics->ack_tx=p.events.ack_tx;
    metrics->nack_tx=p.events.nack_tx;
    metrics->retries=p.events.retries+p.events.nack_received;
    metrics->duplicates=p.events.duplicates;
    return p.x.result()==Transport::Result::Accepted;
}

template<class T,class Action>
static void count_transition(T& transport,unsigned& transitions,Action action) {
    const typename T::State before=transport.state();
    action();
    transitions+=before!=transport.state();
}

static void stress_round_trips(unsigned transactions) {
    Pair p;unsigned transitions=0;
    for(unsigned i=0;i<transactions;++i) {
        const uint32_t now=i*10U;
        if(i) {
            count_transition(p.x,transitions,[&] { assert(p.x.arm(0,1,accept,&p.aa)); });
            count_transition(p.y,transitions,[&] { assert(p.y.arm(1,0,accept,&p.bb)); });
        }
        count_transition(p.x,transitions,[&] {
            assert(p.x.send_reliable_data(1,hello,sizeof(hello)-1,now));
        });
        p.a.done=true;
        count_transition(p.x,transitions,[&] { p.x.poll(now+1); });
        deliver(p.a,p.b);
        count_transition(p.y,transitions,[&] { p.y.poll(now+2); });
        assert(p.b.bytes[0]==SSOT_ACK_TYPE);
        p.b.done=true;
        count_transition(p.y,transitions,[&] { p.y.poll(now+3); });
        deliver(p.b,p.a);
        count_transition(p.x,transitions,[&] { p.x.poll(now+4); });
        assert(p.x.result()==Transport::Result::Accepted);
        assert(p.x.attempts()==1 && p.y.duplicates()==0);
        assert(p.bb.applied==i+1);
    }
    assert(transitions>=10000);
    assert(p.events.ack_accepted==transactions && p.events.ack_tx==transactions);
    printf("STRESS transactions=%u state_transitions=%u accepted=%u duplicates=%u\n",
           transactions,transitions,p.events.ack_accepted,p.events.duplicates);
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
        printf("NACK retry data_tx=%u nack_tx=%u nack_rx=%u ack_tx=%u ack_accepted=%u\n",
               p.events.data_tx,p.events.nack_tx,p.events.nack_received,
               p.events.ack_tx,p.events.ack_accepted);
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

    // Invalid, unrelated and oversized packets are discarded without resetting the radio.
    {
        Pair p;const unsigned before=p.b.inits;
        p.b.source=9;p.b.destination=1;p.b.length=3;
        p.b.bytes[0]=SSOT_DATA_TYPE;p.b.bytes[1]=1;p.b.bytes[2]='x';p.b.incoming=true;
        p.y.poll(1);assert(p.b.inits==before && p.bb.applied==0);
        p.b.source=0;p.b.destination=1;p.b.length=252;p.b.incoming=true;
        p.y.poll(2);assert(p.b.inits==before && p.bb.applied==0);
    }

    // Invalid arguments and malformed ACK/NACK responses never accept a transaction.
    {
        Pair p;uint8_t payload[250];memset(payload,'h',sizeof(payload));
        assert(!p.x.send_reliable_data(0,hello,sizeof(hello)-1,0));
        assert(!p.x.send_reliable_data(1,hello,0,0));
        assert(!p.x.send_reliable_data(1,payload,sizeof(payload),0));
        assert(p.a.starts==0);
    }
    {
        Pair p;start_data(p);
        const uint8_t frames[][3]={{SSOT_ACK_TYPE,2,0},{SSOT_NACK_TYPE,2,0},
                                   {SSOT_ACK_TYPE,1,0xAA},{0xFE,1,0}};
        const uint8_t sizes[]={2,2,3,2};
        for(unsigned i=0;i<sizeof(sizes);++i) {
            p.a.source=(i==0)?9:1;p.a.destination=0;p.a.length=sizes[i];
            memcpy(p.a.bytes,frames[i],sizes[i]);p.a.incoming=true;
            p.x.poll(4+i);
            assert(p.x.state()==Transport::State::WaitResponse &&
                   p.x.result()==Transport::Result::Pending);
        }
    }

    // Corrupted application data is rejected and produces a NACK.
    {
        Pair p;start_data(p);deliver(p.a,p.b);p.b.bytes[2]^=1;p.y.poll(2);
        assert(p.bb.applied==0 && p.b.bytes[0]==SSOT_NACK_TYPE);
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
        Pair p;start_data(p);deliver(p.a,p.b);p.b.receive_error=-6;p.y.poll(2);
        assert(p.y.result()==Transport::Result::RadioError && !p.y.active());
        p.b.receive_error=0;assert(p.y.arm(1,0,accept,&p.bb));
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
    // NACK retry exhaustion is explicit and never exceeds the configured attempt limit.
    {
        Pair p;p.bb.reject=true;start_data(p);uint32_t now=1;
        for(unsigned attempt=1;attempt<=SSOT_MAX_ATTEMPTS;++attempt) {
            deliver(p.a,p.b);p.y.poll(++now);
            assert(p.b.bytes[0]==SSOT_NACK_TYPE && p.b.bytes[1]==1);
            finish_reply(p.b,p.y,++now);deliver(p.b,p.a);p.x.poll(++now);
            if(attempt<SSOT_MAX_ATTEMPTS) {
                assert(p.x.state()==Transport::State::RetryPending);
                p.x.poll(++now);p.a.done=true;p.x.poll(++now);
            }
        }
        assert(p.x.result()==Transport::Result::Rejected);
        assert(p.x.attempts()==SSOT_MAX_ATTEMPTS);
        printf("NACK exhaustion data_tx=%u nack_tx=%u result=Rejected attempts=%u/%u\n",
               p.events.data_tx,p.events.nack_tx,p.x.attempts(),SSOT_MAX_ATTEMPTS);
    }

    // A valid but stale ACK cannot be distinguished after a new session reuses sequence 1.
    {
        Pair p;start_data(p);deliver(p.a,p.b);p.y.poll(2);finish_reply(p.b,p.y,3);
        const uint8_t old_ack[2]={p.b.bytes[0],p.b.bytes[1]};
        assert(old_ack[0]==SSOT_ACK_TYPE);
        deliver(p.b,p.a);p.x.poll(4);
        assert(p.x.result()==Transport::Result::Accepted);
        assert(p.x.arm(0,1,accept,&p.aa));assert(p.y.arm(1,0,accept,&p.bb));
        start_data(p,1,100);
        p.a.source=1;p.a.destination=0;p.a.length=2;
        memcpy(p.a.bytes,old_ack,sizeof(old_ack));p.a.incoming=true;
        p.x.poll(104);
        assert(p.x.result()==Transport::Result::Accepted);
        puts("LIMIT stale-session ACK accepted after sequence reuse");
    }
    {
        Pair p;start_data(p);deliver(p.a,p.b);p.y.poll(2);
        assert(p.bb.applied==1);finish_reply(p.b,p.y,3); // ACK lost; receiver restarts.
        assert(p.y.arm(1,0,accept,&p.bb));
        p.x.poll(LORA_ACK_TIMEOUT_MS+2);p.x.poll(LORA_ACK_TIMEOUT_MS+3);
        p.a.done=true;p.x.poll(LORA_ACK_TIMEOUT_MS+4);
        deliver(p.a,p.b);p.y.poll(LORA_ACK_TIMEOUT_MS+5);
        assert(p.bb.applied==2);
        puts("LIMIT receiver restart clears duplicate cache; retry redelivers DATA");
    }

    {
        Pair p;p.y.suppress_next_response();start_data(p);
        deliver(p.a,p.b);p.y.poll(2);
        assert(p.bb.applied==1 && p.b.starts==0 && !p.y.active());
        p.x.poll(LORA_ACK_TIMEOUT_MS+2);p.x.poll(LORA_ACK_TIMEOUT_MS+3);
        p.a.done=true;p.x.poll(LORA_ACK_TIMEOUT_MS+4);
        deliver(p.a,p.b);p.y.poll(LORA_ACK_TIMEOUT_MS+5);
        assert(p.bb.applied==1 && p.y.duplicates()==1);
        finish_reply(p.b,p.y,LORA_ACK_TIMEOUT_MS+6);
        deliver(p.b,p.a);p.x.poll(LORA_ACK_TIMEOUT_MS+7);
        assert(p.x.result()==Transport::Result::Accepted && p.a.starts==2);
    }

    const unsigned losses[]={0U,1U,5U,10U,20U,30U,50U,100U};
    for(size_t rate=0;rate<sizeof(losses)/sizeof(losses[0]);++rate) {
        unsigned delivered=0,total_attempts=0,total_acks=0,total_nacks=0;
        unsigned total_retries=0,total_timeouts=0,total_duplicates=0;
        for(uint32_t scenario=0;scenario<100;++scenario) {
            LossMetrics metrics;
            delivered+=loss_scenario(losses[rate],
                                     scenario+losses[rate]*1000U+1U,&metrics);
            total_attempts+=metrics.attempts;total_acks+=metrics.ack_tx;
            total_nacks+=metrics.nack_tx;total_retries+=metrics.retries;
            total_timeouts+=metrics.timeouts;total_duplicates+=metrics.duplicates;
        }
        assert(total_attempts<=100U*SSOT_MAX_ATTEMPTS);
        if(losses[rate]==0) assert(delivered==100 && total_timeouts==0);
        if(losses[rate]==100) assert(delivered==0 && total_attempts==100U*SSOT_MAX_ATTEMPTS);
        printf("LOSS %u%% seed_start=%u transactions=100 delivered=%u/100 data_tx=%u ack_tx=%u nack_tx=%u retries=%u timeouts=%u duplicates=%u\n",
               losses[rate],losses[rate]*1000U+1U,delivered,total_attempts,
               total_acks,total_nacks,total_retries,total_timeouts,total_duplicates);
    }
    {
        Pair p;p.a.send_error=-4;
        assert(!p.x.send_reliable_data(1,hello,11,0));
        assert(p.x.result()==Transport::Result::RadioError);
        assert(p.x.radio_error()==-4);
    }
    stress_round_trips(3000);
    puts("PASS stable-API transport: ACK/NACK, bounded retry, duplicate, bounds and rearm");
}
