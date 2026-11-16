#include "arq.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static const uint8_t hello[] = "Hello World";
static arq_frame data(void) {
    arq_frame f = {ARQ_DATA,1,2,0x12345678,0,11,0,{0}};
    memcpy(f.payload,hello,11); return f;
}
static arq_frame control(uint8_t type, uint8_t reason) {
    arq_frame f={type,2,1,0x12345678,0,0,reason,{0}}; return f;
}
static void codec(void) {
    const uint8_t golden[]={1,1,1,2,0x78,0x56,0x34,0x12,0,0,11,0,
        'H','e','l','l','o',' ','W','o','r','l','d'};
    uint8_t b[46]; memset(b,0xA5,sizeof b); arq_frame f=data(), out;
    assert(arq_encode(&f,b+1,44)==23);
    assert(b[0]==0xA5 && b[24]==0xA5 && !memcmp(b+1,golden,23));
    assert(arq_decode(&out,golden,23) && out.session==0x12345678);
    assert(!arq_encode(&f,b,22));
    for(size_t n=0;n<23;n++) assert(!arq_decode(&out,golden,n));
    memcpy(b,golden,23); b[0]=2; assert(!arq_decode(&out,b,23));
    memcpy(b,golden,23); b[1]=4; assert(!arq_decode(&out,b,23));
    memcpy(b,golden,23); b[10]=33; assert(!arq_decode(&out,b,23));
    memcpy(b,golden,23); b[11]=1; assert(!arq_decode(&out,b,23));
    f=control(ARQ_ACK,0);assert(arq_encode(&f,b,44)==12);
    f.length=1;assert(!arq_encode(&f,b,44));
    f=control(ARQ_NACK,0);assert(!arq_encode(&f,b,44));
    for(int r=1;r<=3;r++){f.reason=r;assert(arq_encode(&f,b,44)==12);}
    f=data();f.length=32;assert(arq_encode(&f,b,44)==44);
    assert(arq_decode(&out,b,44)); assert(!arq_decode(&out,b,45));
}
static arq_sender fresh(uint32_t now) {
    arq_sender s;arq_sender_init(&s);
    assert(!arq_sender_request(&s,hello,11,now,2000));
    assert(arq_sender_arm(&s,0x12345678));
    assert(arq_sender_arm(&s,0x12345678));
    assert(arq_sender_request(&s,hello,11,now,2000));
    assert(!arq_sender_request(&s,hello,11,now,2000));
    assert(!arq_sender_arm(&s,1));return s;
}
static void sender(void) {
    arq_sender s=fresh(100); arq_frame ack=control(ARQ_ACK,0);
    assert(s.state==ARQ_TRANSMITTING);
    arq_sender_tx_done(&s,150,true);
    assert(s.state==ARQ_WAITING_ACK && s.retry_at==2150);
    for(int field=0;field<5;field++) {
        arq_frame bad=ack;
        if(field==0)bad.src++;if(field==1)bad.dst++;if(field==2)bad.session++;
        if(field==3)bad.sequence++;if(field==4)bad.type=ARQ_DATA;
        arq_sender_control(&s,&bad,160);assert(s.state==ARQ_WAITING_ACK);
    }
    arq_sender_control(&s,&ack,200);assert(s.state==ARQ_DELIVERED);
    assert(s.sequence==1 && s.rtt_count==1 && s.rtt_last==50);
    assert(!arq_sender_request(&s,hello,11,200,1999));
    assert(arq_sender_request(&s,hello,11,200,2000));
    assert(s.state==ARQ_BACKOFF);arq_sender_poll(&s,3099);assert(s.attempts==0);
    arq_sender_poll(&s,99+ARQ_SPACING_MS);assert(s.attempts==0);
    arq_sender_poll(&s,100+ARQ_SPACING_MS);assert(s.state==ARQ_TRANSMITTING);
    arq_sender_tx_done(&s,3150,false);assert(s.result==ARQ_RADIO_ERROR);
    assert(!arq_sender_request(&s,hello,11,4000,2000));
    for(int r=1;r<=2;r++) {
        s=fresh(0);arq_sender_tx_done(&s,10,true);
        arq_frame nack=control(ARQ_NACK,r);arq_sender_control(&s,&nack,20);
        assert(s.state==ARQ_FAILED && s.attempts==1);
        assert(s.result==(r==1?ARQ_PROTOCOL_ERROR:ARQ_REJECTED));
    }
    s=fresh(0); arq_frame busy=control(ARQ_NACK,ARQ_BUSY);
    arq_sender_tx_done(&s,10,true);uint32_t deadline=s.terminal_at;
    arq_sender_control(&s,&busy,100);assert(s.state==ARQ_BACKOFF);
    for(uint32_t t=200;t<3000;t+=100)arq_sender_control(&s,&busy,t);
    assert(s.retry_at==2010 && s.terminal_at==deadline);
    arq_sender_control(&s,&ack,2999);assert(s.state==ARQ_DELIVERED);
    s=fresh(0);arq_frame immutable=s.frame;
    for(int attempt=1;attempt<=5;attempt++) {
        assert(s.attempts==attempt && !memcmp(&s.frame,&immutable,sizeof immutable));
        uint32_t done=s.last_start+10;arq_sender_tx_done(&s,done,true);
        assert(s.interval==((uint32_t)2000<<(attempt-1)));
        arq_sender_poll(&s,s.retry_at);
        if(s.state==ARQ_BACKOFF)arq_sender_poll(&s,s.last_start+ARQ_SPACING_MS);
    }
    assert(s.result==ARQ_TIMEOUT_EXHAUSTED && s.rtt_count==0);
    s=fresh(UINT32_MAX-100);arq_sender_tx_done(&s,UINT32_MAX-50,true);
    arq_sender_poll(&s,1948);assert(s.state==ARQ_WAITING_ACK);
    arq_sender_control(&s,&ack,1949);assert(s.state==ARQ_DELIVERED);
    s=fresh(0);s.sequence=65535;s.frame.sequence=65535;ack.sequence=65535;
    arq_sender_tx_done(&s,10,true);arq_sender_control(&s,&ack,20);
    assert(s.sequence==0 && !arq_sender_request(&s,hello,11,3000,2000));
    assert(arq_sender_arm(&s,0x12345679));
    s=fresh(0);arq_sender_stop(&s);arq_sender_tx_done(&s,10,true);
    ack.sequence=0;arq_sender_control(&s,&ack,20);
    assert(s.state==ARQ_DELIVERED && !arq_sender_request(&s,hello,11,3000,2000));
    s=fresh(0);arq_sender_poll(&s,3000);assert(s.result==ARQ_RADIO_ERROR);
    s=fresh(0);arq_sender_tx_done(&s,10,true);ack.sequence=0;
    arq_sender_control(&s,&ack,20);assert(arq_sender_arm(&s,0x12345679));
    assert(arq_sender_request(&s,hello,11,30,2000));
    assert(s.state==ARQ_BACKOFF);arq_sender_poll(&s,ARQ_SPACING_MS-1);
    assert(s.state==ARQ_BACKOFF);arq_sender_poll(&s,ARQ_SPACING_MS);
    assert(s.state==ARQ_TRANSMITTING);
}
static void absolute_deadline(void) {
    arq_frame ack=control(ARQ_ACK,0);
    const uint32_t starts[]={0,UINT32_MAX-100};
    for(size_t i=0;i<sizeof starts/sizeof starts[0];i++) {
        for(int offset=-1;offset<=1;offset++) {
            arq_sender s=fresh(starts[i]);
            arq_sender_tx_done(&s,starts[i]+10,true);
            uint32_t now=s.terminal_at+offset;
            arq_sender_control(&s,&ack,now);
            if(offset<0) assert(s.state==ARQ_DELIVERED && s.result==ARQ_OK && s.sequence==1);
            else assert(s.state==ARQ_FAILED && s.result==ARQ_TIMEOUT_EXHAUSTED && s.sequence==0 && s.rtt_count==0);
        }
    }
}

static void ack_matrix(void) {
    arq_sender s;arq_receiver r;arq_sender_init(&s);arq_receiver_init(&r);
    assert(arq_sender_arm(&s,0x12345678) && arq_receiver_arm(&r,0x12345678));
    uint32_t now=0;
    for(uint32_t sequence=0;sequence<=UINT16_MAX;sequence++,now+=ARQ_SPACING_MS) {
        assert(arq_sender_request(&s,hello,11,now,ARQ_ACK_MIN_MS));
        assert(s.state==ARQ_TRANSMITTING && s.frame.sequence==sequence);
        arq_frame ack=control(ARQ_ACK,0);ack.sequence=(uint16_t)sequence;
        arq_sender_control(&s,&ack,now+1);assert(s.state==ARQ_TRANSMITTING);
        arq_sender_tx_done(&s,now+10,true);
        for(unsigned field=0;field<8;field++) {
            arq_frame bad=ack;
            if(field==0)bad.src++;if(field==1)bad.dst++;if(field==2)bad.session++;
            if(field==3)bad.sequence--;if(field==4)bad.type=ARQ_DATA;
            if(field==5)bad.length=1;if(field==6)bad.reason=ARQ_BUSY;
            if(field==7)bad.type=0;
            arq_sender_control(&s,&bad,now+15);
            assert(s.state==ARQ_WAITING_ACK && s.sequence==sequence && s.rtt_count==sequence);
        }
        arq_frame response;
        assert(arq_receiver_data(&r,&s.frame,&response,false) && response.type==ARQ_ACK);
        arq_sender_control(&s,&response,now+20);
        assert(s.state==ARQ_DELIVERED && s.result==ARQ_OK);
        assert(s.frame.sequence==sequence && s.sequence==(uint16_t)(sequence+1));
        assert(s.rtt_count==sequence+1 && r.deliveries==sequence+1);
        arq_sender_control(&s,&response,now+21);
        assert(s.rtt_count==sequence+1 && s.state==ARQ_DELIVERED);
    }
    assert(s.used_up && !arq_sender_request(&s,hello,11,now,ARQ_ACK_MIN_MS));
    s=fresh(0);arq_sender_tx_done(&s,10,true);
    arq_frame old=control(ARQ_ACK,0);arq_sender_init(&s);
    arq_sender_control(&s,&old,20);assert(s.state==ARQ_IDLE && !s.armed);
    assert(arq_sender_arm(&s,0x12345679));
    assert(arq_sender_request(&s,hello,11,ARQ_SPACING_MS,ARQ_ACK_MIN_MS));
    arq_sender_tx_done(&s,ARQ_SPACING_MS+10,true);
    arq_sender_control(&s,&old,ARQ_SPACING_MS+20);
    assert(s.state==ARQ_WAITING_ACK && s.rtt_count==0);
    arq_sender_poll(&s,s.terminal_at);
    old.session=s.session;arq_sender_control(&s,&old,s.terminal_at+1);
    assert(s.state==ARQ_FAILED && s.result==ARQ_TIMEOUT_EXHAUSTED && s.sequence==0);
    puts("ACK matrix: all 65536 sequences, mismatches, duplicates, reset and stale sessions PASS");
}

static void parser_fuzz(void) {
    uint32_t seed=0x4c4f5241;
    for(unsigned iteration=0;iteration<50000;iteration++) {
        uint8_t input[64],encoded[44];
        seed=seed*1664525U+1013904223U;size_t length=seed%65;
        for(size_t i=0;i<length;i++){seed=seed*1664525U+1013904223U;input[i]=(uint8_t)(seed>>24);}
        if(iteration%4==0) {
            arq_frame f=data();f.length=(uint8_t)(seed%33);
            length=arq_encode(&f,input,sizeof input);
            if(iteration%8==0)input[seed%length]^=0x80;
        }
        arq_frame result,original;memset(&result,0xA5,sizeof result);original=result;
        if(arq_decode(&result,input,length)) {
            assert(arq_valid(&result));size_t n=arq_encode(&result,encoded,sizeof encoded);
            assert(n==length && !memcmp(input,encoded,n));
        } else assert(!memcmp(&result,&original,sizeof result));
    }
    puts("Parser fuzz: 50000 bounded inputs, seed 0x4c4f5241 PASS");
}

static void receiver(void) {
    arq_receiver r;arq_receiver_init(&r);arq_frame f=data(), response;
    assert(!arq_receiver_data(&r,&f,&response,false));
    assert(arq_receiver_arm(&r,f.session));
    for(int field=0;field<4;field++) {
        arq_frame bad=f;if(field==0)bad.src++;if(field==1)bad.dst++;
        if(field==2)bad.session++;if(field==3)bad.type=ARQ_ACK;
        assert(!arq_receiver_data(&r,&bad,&response,false));
    }
    assert(arq_receiver_data(&r,&f,&response,true));assert(response.reason==ARQ_BUSY);
    f.payload[0]='W';assert(arq_receiver_data(&r,&f,&response,false));
    assert(response.reason==ARQ_APPLICATION_REJECTED && r.deliveries==0);
    f=data();f.sequence=1;assert(arq_receiver_data(&r,&f,&response,false));
    assert(response.reason==ARQ_UNEXPECTED_SEQUENCE);f.sequence=0;
    assert(arq_receiver_data(&r,&f,&response,false));assert(response.type==ARQ_ACK);
    assert(r.deliveries==1 && r.expected==1);
    assert(arq_receiver_data(&r,&f,&response,false));assert(r.deliveries==1 && r.duplicates==1);
    f.payload[0]='W';assert(arq_receiver_data(&r,&f,&response,false));
    assert(response.reason==ARQ_APPLICATION_REJECTED && r.deliveries==1);
    assert(arq_receiver_arm(&r,0x12345679));f=data();
    assert(!arq_receiver_data(&r,&f,&response,false));
    assert(r.expected==0);
    r.expected=65535;f.session=r.session;f.sequence=65535;
    assert(arq_receiver_data(&r,&f,&response,false));assert(r.expected==0);
    assert(arq_receiver_data(&r,&f,&response,false));assert(response.type==ARQ_ACK);
}
static void fault_harness(void) {
    /* Each channel fault is injected at the real portable-module boundary. */
    for(int fault=0;fault<8;fault++) {
        arq_sender s=fresh(0);arq_receiver r;arq_receiver_init(&r);
        arq_receiver_arm(&r,s.session);arq_frame response;
        arq_sender_tx_done(&s,10,true);
        if(fault!=0 && fault!=4) {
            arq_frame f=s.frame;if(fault==3)f.payload[0]='W';
            assert(arq_receiver_data(&r,&f,&response,fault==5));
            if(fault==2){response.sequence++;arq_sender_control(&s,&response,100);}
            if(fault==5)arq_sender_control(&s,&response,100);
            /* fault 1: dropped ACK; fault 3: dropped NACK; fault 4: CRC discard */
            if(fault==6){arq_sender_poll(&s,2010);arq_sender_control(&s,&response,2500);}
        }
        if(s.state==ARQ_DELIVERED)continue;
        uint32_t retry_start=s.last_start+ARQ_SPACING_MS;
        arq_sender_poll(&s,retry_start);assert(s.state==ARQ_TRANSMITTING);
        if(fault==7){arq_sender_tx_done(&s,retry_start+10,false);assert(s.result==ARQ_RADIO_ERROR);continue;}
        arq_sender_tx_done(&s,retry_start+10,true);
        assert(arq_receiver_data(&r,&s.frame,&response,false));
        arq_sender_control(&s,&response,3100);
        assert(s.state==ARQ_DELIVERED && r.deliveries==1 && s.rtt_count==0);
    }
}
int main(void){codec();sender();absolute_deadline();ack_matrix();parser_fuzz();receiver();fault_harness();puts("ARQ core: PASS");}
