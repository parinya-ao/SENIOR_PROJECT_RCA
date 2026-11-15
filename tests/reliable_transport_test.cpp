#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "reliable_transport.h"

struct FakeRadio {
    uint8_t local, src, dst=0, id=0, flags=0, length=0, bytes[251]={};
    bool incoming=false, done=false;
    int16_t error=0, start_error=0, rx_error=0;
    unsigned starts=0, recoveries=0;
    explicit FakeRadio(uint8_t address): local(address),src(address^1) {}
    int16_t send(uint8_t destination,uint8_t low,uint8_t high,const uint8_t* p,uint8_t n) {
        ++starts; done=false;
        if(start_error) return error=start_error;
        dst=destination;id=low;flags=high;length=n;memcpy(bytes,p,n);return error=0;
    }
    bool send_done() { return done; }
    int16_t last_error() const { return error; }
    int16_t recover() { ++recoveries;done=false;return error=0; }
    uint32_t time_on_air_us(uint8_t n) { return (n+4)*2000; }
    bool available() { return incoming; }
    int16_t start_receive() { return error=rx_error; }
    int16_t standby() { incoming=false;done=false;return error=0; }
    int16_t recv(uint8_t* src,uint8_t* dest,uint8_t* lo,uint8_t* hi,uint8_t* p,uint8_t* n,size_t cap) {
        incoming=false;*n=0;
        if(error) return error;
        if(length>cap) return -2;
        *src=this->src;*dest=dst;*lo=id;*hi=flags;*n=length;memcpy(p,bytes,length);return 0;
    }
};
using Transport=ReliableTransport<FakeRadio>;
struct Application { unsigned applied=0; bool reject=false; };
static bool accept(void* c,uint16_t session,uint8_t sequence,const uint8_t*,uint8_t) {
    assert(session>=0x1234 && sequence!=0);
    Application* a=static_cast<Application*>(c);
    if(a->reject) return false;
    ++a->applied; return true;
}
static const uint8_t hello[]="hello world";
static uint8_t failure_type, failure_sequence;
static void observe(void*,const char* event,uint8_t type,uint8_t sequence,int16_t) {
    if(!strcmp(event,"TRANSACTION_FAILED")) { failure_type=type;failure_sequence=sequence; }
}
struct Pair {
    FakeRadio a,b;
    Application aa,bb;
    Transport x,y;
    explicit Pair(uint8_t first=0):a(first),b(first^1),x(a),y(b) {
        assert(x.arm(first,first^1,0x1234,accept,&aa));
        assert(y.arm(first^1,first,0x1234,accept,&bb));
    }
};
static void deliver(FakeRadio& from,FakeRadio& to) {
    to.dst=from.dst;to.id=from.id;to.flags=from.flags;to.length=from.length;
    memcpy(to.bytes,from.bytes,from.length);to.incoming=true;to.error=0;
}
static void data_tx(Pair& p,uint8_t seq=1,uint32_t now=0) {
    assert(p.x.send_reliable_data(seq,hello,11,now));
    assert(p.a.length==13 && p.a.bytes[0]==SSOT_DATA_TYPE && p.a.bytes[1]==seq);
    assert(memcmp(p.a.bytes+2,hello,11)==0);
    p.a.done=true;p.x.poll(now+1);
}
static void round_trip(Pair& p,uint32_t now=0) {
    deliver(p.a,p.b);p.y.poll(now+2);
    assert(p.b.length==2 && p.b.bytes[0]==SSOT_ACK_TYPE);
    p.b.done=true;p.y.poll(now+3);
    deliver(p.b,p.a);p.x.poll(now+4);
    assert(p.x.state()==Transport::State::Complete);
}
int main() {
    // Packet vectors and physical-role symmetry, with one shared implementation.
    for(uint8_t first=0;first<2;++first) {
        Pair p(first);data_tx(p);round_trip(p);
        assert(p.bb.applied==1);
    }
    { Pair p;data_tx(p);
      p.a.bytes[0]=SSOT_ACK_TYPE;p.a.bytes[1]=2;p.a.length=2;
      p.a.dst=0;p.a.incoming=true;p.x.poll(5);
      assert(p.x.state()==Transport::State::WaitResponse);
      p.a.bytes[1]=1;p.a.dst=99;p.a.incoming=true;p.x.poll(6);
      assert(p.x.state()==Transport::State::WaitResponse);
      p.a.dst=0;p.a.id=0x35;p.a.incoming=true;p.x.poll(7);
      assert(p.x.state()==Transport::State::WaitResponse);
      p.a.id=0x34;p.a.src=9;p.a.incoming=true;p.x.poll(8);
      assert(p.x.state()==Transport::State::WaitResponse);
      p.a.src=1;p.a.length=3;p.a.incoming=true;p.x.poll(9);
      assert(p.x.state()==Transport::State::WaitResponse);
    }
    { Pair p;p.bb.reject=true;data_tx(p);deliver(p.a,p.b);p.y.poll(2);
      assert(p.b.bytes[0]==SSOT_NACK_TYPE && p.b.bytes[1]==1);
      p.b.done=true;p.y.poll(3);deliver(p.b,p.a);p.x.poll(4);
      assert(p.x.result()==Transport::Result::Rejected && p.bb.applied==0);
      assert(p.x.arm(0,1,0x1235,accept,&p.aa));
      assert(p.y.arm(1,0,0x1235,accept,&p.bb));
      p.bb.reject=false;data_tx(p,1,5);round_trip(p,5);
    }
    { Pair p;data_tx(p);uint8_t data[13];memcpy(data,p.a.bytes,13);
      deliver(p.a,p.b);p.y.poll(2);p.b.done=true;p.y.poll(3);
      p.x.poll(1+LORA_ACK_TIMEOUT_MS); // Drop first ACK; same bytes/session/seq retry.
      p.x.poll(20000);
      assert(p.a.starts==2 && p.a.length==13 && memcmp(data,p.a.bytes,13)==0);
      p.a.done=true;p.x.poll(20001);round_trip(p,20000);
      assert(p.bb.applied==1 && p.y.duplicates()==1);
    }
    { Pair p;data_tx(p);deliver(p.a,p.b);p.b.error=-7;p.y.poll(2);
      assert(p.b.starts==0 && p.bb.applied==0); // PHY CRC failure: silent discard.
      p.b.error=0;p.b.incoming=true;p.b.length=252;p.y.poll(3);
      assert(p.b.starts==0 && p.bb.applied==0);
    }
    { Pair p;p.a.start_error=-8;
      assert(!p.x.send_reliable_data(1,hello,11,0));
      assert(p.x.result()==Transport::Result::RadioError && p.a.recoveries==1);
      p.a.start_error=0;
      const uint8_t changed[]="other bytes";
      assert(!p.x.send_reliable_data(1,changed,11,1));
      assert(p.x.send_reliable_data(1,hello,11,2));
    }
    { Pair p;data_tx(p);deliver(p.a,p.b);p.b.start_error=-8;p.y.poll(2);
      assert(p.bb.applied==1 && p.y.result()==Transport::Result::RadioError);
      p.b.start_error=0;assert(p.y.arm(1,0,0x1234,accept,&p.bb));
      deliver(p.a,p.b);p.y.poll(3);
      assert(p.bb.applied==1 && p.b.bytes[0]==SSOT_ACK_TYPE);
    }
    { Pair p;data_tx(p,1);deliver(p.a,p.b);p.b.bytes[1]=2;p.y.poll(2);
      assert(p.bb.applied==0 && p.b.bytes[0]==SSOT_NACK_TYPE);
    }
    { Pair p;data_tx(p);round_trip(p);
      p.b.rx_error=-9;assert(!p.y.arm(1,0,0x1234,accept,&p.bb));
      p.b.rx_error=0;assert(p.y.arm(1,0,0x1234,accept,&p.bb));
      p.a.bytes[0]=SSOT_DATA_TYPE;p.a.bytes[1]=1;memcpy(p.a.bytes+2,hello,11);
      p.a.length=13;p.a.dst=1;
      deliver(p.a,p.b);p.y.poll(5);
      assert(p.bb.applied==1 && p.y.duplicates()==1);
    }
    { Pair p;data_tx(p);round_trip(p);data_tx(p,2,20000);
      p.y.on_event(observe,nullptr);p.b.start_error=-8;
      deliver(p.a,p.b);p.y.poll(20002);
      assert(failure_type==SSOT_ACK_TYPE && failure_sequence==2);
    }
    { Pair p;p.a.rx_error=-9;
      assert(!p.x.arm(0,1,0x1235,accept,&p.aa));
      assert(p.x.result()==Transport::Result::RadioError);
    }
    { Pair p;data_tx(p);deliver(p.a,p.b);p.y.poll(2);
      assert(p.y.stop()==0);
      assert(!p.y.send_reliable_data(1,hello,11,3));
      assert(p.y.arm(1,0,0x1234,accept,&p.bb));
      deliver(p.a,p.b);p.y.poll(4);
      assert(p.bb.applied==1 && p.y.duplicates()==1);
    }
    { Pair p;assert(p.x.send_reliable_data(1,hello,11,UINT32_MAX-100));
      p.x.poll(50);assert(p.x.state()==Transport::State::TxData);
      p.x.poll(LORA_TX_TIMEOUT_MS);
      assert(p.x.result()==Transport::Result::TxTimeout);
    }
    { Pair p;data_tx(p);deliver(p.a,p.b);p.y.poll(2);
      // A response-start failure cannot undo accepted application data.
      p.y.poll(LORA_TX_TIMEOUT_MS+3);
      assert(p.bb.applied==1 && p.y.result()==Transport::Result::TxTimeout);
    }
    { Pair p;data_tx(p);p.x.poll(LORA_ACK_TIMEOUT_MS+1);
      for(unsigned i=0;i<SSOT_MAX_RETRIES;++i) {
          uint32_t t=(i+1)*20000;p.x.poll(t);p.a.done=true;p.x.poll(t+1);
          p.x.poll(t+1+LORA_ACK_TIMEOUT_MS);
      }
      assert(p.x.result()==Transport::Result::AckTimeout);
      assert(p.a.starts==SSOT_MAX_ATTEMPTS);
    }
    { Pair p;
      for(unsigned sequence=1;sequence<=255;++sequence) {
          data_tx(p,static_cast<uint8_t>(sequence),sequence*20000);
          round_trip(p,sequence*20000);
      }
      assert(!p.x.send_reliable_data(0,hello,11,6000000));
      assert(p.x.arm(0,1,0x1235,accept,&p.aa));
      assert(p.y.arm(1,0,0x1235,accept,&p.bb));
      data_tx(p,1,6000001);round_trip(p,6000001);
      assert(p.bb.applied==256);
    }
    puts("PASS shared ACK/NACK symmetry, retries, duplicates, CRC/bounds, timeouts, wrap");
}
