#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "ssot.h"

// Existing wire: dst,src,session_lo,session_hi, type,sequence,application bytes.
// Radio owns framing/CRC; application acceptance is the staging/validation boundary.
template<class Radio> class ReliableTransport {
public:
    enum class State : uint8_t { RxWait, TxData, WaitResponse, RetryPending,
                                 TxResponse, Complete, Failed };
    enum class Result : uint8_t { Pending, Accepted, Rejected, InvalidArgument,
                                  RadioError, TxTimeout, AckTimeout };
    using Accept = bool (*)(void*, uint16_t, uint8_t, const uint8_t*, uint8_t);
    using Event = void (*)(void*, const char*, uint8_t, uint8_t, int16_t);
    static constexpr uint8_t kMaxData = 249;

    explicit ReliableTransport(Radio& radio): radio_(radio) {}
    void on_event(Event event, void* context) { event_=event; event_context_=context; }
    bool active() const {
        return state_==State::TxData || state_==State::WaitResponse ||
               state_==State::RetryPending || state_==State::TxResponse;
    }
    State state() const { return state_; }
    Result result() const { return result_; }
    int16_t radio_error() const { return error_; }
    uint16_t session() const { return session_; }
    uint32_t duplicates() const { return duplicates_; }
    uint8_t attempts() const { return attempts_; }
    int16_t stop() {
        paused_=true;state_=State::RxWait;
        error_=radio_.standby();return error_;
    }

    bool arm(uint8_t local, uint8_t peer, uint16_t session, Accept accept,
             void* context) {
        if(active() || !session || local==peer || local==255 || peer==255 || !accept)
            return false;
        const bool same = session_==session && local_==local && peer_==peer;
        local_=local;peer_=peer;session_=session;accept_=accept;context_=context;
        if(!same) {
            next_rx_=next_tx_=1;have_accepted_=false;duplicates_=0;pending_identity_=false;
        }
        error_=radio_.start_receive();
        armed_=!error_;paused_=false;
        state_=error_ ? State::Failed : State::RxWait;
        result_=error_ ? Result::RadioError : Result::Pending;
        return armed_;
    }

    bool send_reliable_data(uint8_t sequence,const uint8_t* data,size_t size,
                            uint32_t now) {
        if(!armed_ || paused_ || active() || !data || !size || size>kMaxData ||
           !next_tx_ || sequence!=next_tx_) return false;
        // A delayed ACK must never accept different content under a reused identity.
        if(pending_identity_ && (wire_size_!=size+2 || memcmp(wire_+2,data,size)))
            return false;
        wire_[0]=SSOT_DATA_TYPE;wire_[1]=sequence;
        memcpy(wire_+2,data,size);wire_size_=static_cast<uint8_t>(size+2);
        sequence_=sequence;attempts_=0;result_=Result::Pending;
        pending_identity_=true;
        const uint32_t data_us=radio_.time_on_air_us(wire_size_);
        const uint32_t response_us=radio_.time_on_air_us(2);
        if(!data_us || !response_us) { fail(Result::RadioError,-1);return false; }
        // Keep the established retry spacing; include both directions' airtime.
        spacing_ms_=static_cast<uint32_t>((static_cast<uint64_t>(data_us)+response_us)*100/1000+1);
        const uint32_t response_ms=(response_us+999)/1000+50;
        ack_ms_=response_ms>LORA_ACK_TIMEOUT_MS ? response_ms : LORA_ACK_TIMEOUT_MS;
        return transmit_data(now);
    }

    void poll(uint32_t now) {
        if(!armed_ || paused_) return;
        if(state_==State::TxData || state_==State::TxResponse) {
            if(radio_.send_done()) {
                if(state_==State::TxData) {
                    state_=State::WaitResponse;started_=now;
                    emit("DATA_TX_DONE",SSOT_DATA_TYPE,sequence_);
                } else {
                    state_=State::RxWait;
                    emit(reply_[0]==SSOT_ACK_TYPE ? "ACK_TX_DONE" : "NACK_TX_DONE",
                         reply_[0],reply_[1]);
                }
            } else if(now-started_>=LORA_TX_TIMEOUT_MS) fail(Result::TxTimeout,radio_.last_error());
            else if(radio_.last_error()) fail(Result::RadioError,radio_.last_error());
            return;
        }
        if(radio_.available()) receive(now);
        if(state_==State::WaitResponse && now-started_>=ack_ms_) {
            if(attempts_>=SSOT_MAX_ATTEMPTS) fail(Result::AckTimeout,0);
            else { state_=State::RetryPending;emit("RETRY_SCHEDULED",SSOT_DATA_TYPE,sequence_); }
        }
        if(state_==State::RetryPending && now-last_start_>=spacing_ms_)
            transmit_data(now);
    }

private:
    void emit(const char* event,uint8_t type,uint8_t sequence,int16_t error=0) {
        if(event_) event_(event_context_,event,type,sequence,error);
    }
    void fail(Result result,int16_t error) {
        fail(result,error,state_==State::TxResponse ? reply_[0] : SSOT_DATA_TYPE,
             state_==State::TxResponse ? reply_[1] : sequence_);
    }
    void fail(Result result,int16_t error,uint8_t type,uint8_t sequence) {
        const int16_t recovery=radio_.recover();
        error_=recovery ? recovery : error;
        if(recovery) armed_=false;
        state_=State::Failed;result_=result;
        emit("TRANSACTION_FAILED",type,sequence,error_);
    }
    bool transmit_data(uint32_t now) {
        error_=radio_.send(peer_,static_cast<uint8_t>(session_),
                            static_cast<uint8_t>(session_>>8),wire_,wire_size_);
        if(error_) { fail(Result::RadioError,error_);return false; }
        ++attempts_;started_=last_start_=now;state_=State::TxData;
        emit("DATA_TX_BEGIN",SSOT_DATA_TYPE,sequence_);return true;
    }
    void receive(uint32_t now) {
        uint8_t src=0,dst=0,low=0,high=0,size=0;
        const int16_t rc=radio_.recv(&src,&dst,&low,&high,rx_,&size,sizeof rx_);
        if(rc) { emit("RX_DISCARD",0,0,rc);return; }
        if(src!=peer_ || dst!=local_ ||
           (static_cast<uint16_t>(low)|(static_cast<uint16_t>(high)<<8))!=session_ ||
           size<2) return;
        const uint8_t type=rx_[0],seq=rx_[1];
        if(type==SSOT_ACK_TYPE || type==SSOT_NACK_TYPE) {
            if(size!=2 || seq!=sequence_ ||
               (state_!=State::WaitResponse && state_!=State::RetryPending)) return;
            if(state_==State::WaitResponse && now-started_>=ack_ms_) return;
            emit(type==SSOT_ACK_TYPE ? "ACK_RX" : "NACK_RX",type,seq);
            if(type==SSOT_ACK_TYPE) {
                state_=State::Complete;result_=Result::Accepted;
                pending_identity_=false;
                ++next_tx_; // Wrap requires a fresh session to exclude stale responses.
                emit("ACK_ACCEPTED",type,seq);emit("TRANSACTION_COMPLETE",type,seq);
            } else {
                state_=State::Failed;result_=Result::Rejected;
                // SSOT NACK has no reason byte: it is a terminal application rejection.
                emit("NACK_ACCEPTED",type,seq);emit("TRANSACTION_FAILED",type,seq);
            }
            return;
        }
        // Serialize local transactions; never ACK an ACK/NACK or collide with DATA TX.
        if(type!=SSOT_DATA_TYPE || active() || size<3) return;
        const uint8_t data_size=static_cast<uint8_t>(size-2);
        emit("DATA_RX",type,seq);
        const bool duplicate=have_accepted_ && seq==last_sequence_ &&
            data_size==last_size_ && !memcmp(rx_+2,last_data_,data_size);
        bool accepted=duplicate;
        if(!duplicate && next_rx_ && seq==next_rx_)
            accepted=accept_(context_,session_,seq,rx_+2,data_size);
        if(accepted) {
            if(duplicate) { ++duplicates_;emit("DATA_DUP",type,seq); }
            else {
                have_accepted_=true;last_sequence_=seq;last_size_=data_size;
                memcpy(last_data_,rx_+2,data_size);++next_rx_;
                emit("DATA_VALIDATED",type,seq);
            }
        }
        reply_[0]=accepted ? SSOT_ACK_TYPE : SSOT_NACK_TYPE;reply_[1]=seq;
        error_=radio_.send(peer_,low,high,reply_,2);
        if(error_) { fail(Result::RadioError,error_,reply_[0],seq);return; }
        state_=State::TxResponse;started_=now;
        emit(accepted ? "ACK_TX_BEGIN" : "NACK_TX_BEGIN",reply_[0],seq);
    }
    Radio& radio_;
    Accept accept_=nullptr;
    Event event_=nullptr;
    void* context_=nullptr;
    void* event_context_=nullptr;
    State state_=State::RxWait;
    Result result_=Result::Pending;
    int16_t error_=0;
    bool armed_=false,have_accepted_=false,paused_=false,pending_identity_=false;
    uint8_t local_=0,peer_=0,sequence_=1,attempts_=0,next_rx_=1,next_tx_=1;
    uint8_t last_sequence_=0,last_size_=0,wire_size_=0;
    uint16_t session_=0;
    uint32_t started_=0,last_start_=0,spacing_ms_=0,ack_ms_=0,duplicates_=0;
    uint8_t wire_[251]={},rx_[251]={},last_data_[kMaxData]={},reply_[2]={};
};
