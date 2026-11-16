#pragma once

#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <RadioLib.h>
#include "ssot.h"

template<class Radio> class ReliableTransport {
public:
    enum class State : uint8_t { RxWait, TxData, WaitResponse, RetryPending,
                                 TxResponse, Complete, Failed };
    enum class Result : uint8_t { Pending, Accepted, Rejected, InvalidArgument,
                                  RadioError, TxTimeout, AckTimeout };
    using Accept = bool (*)(void*, uint8_t, const uint8_t*, uint8_t);
    using Event = void (*)(void*, const char*, uint8_t, uint8_t, int16_t);
    static constexpr uint8_t kMaxData = 249;

    ReliableTransport(Radio& radio,float frequency,int8_t tx_power,uint8_t long_range)
        : radio_(radio),frequency_(frequency),tx_power_(tx_power),long_range_(long_range) {}

    void on_event(Event event,void* context) { event_=event;event_context_=context; }
    bool active() const {
        return state_==State::TxData || state_==State::WaitResponse ||
               state_==State::RetryPending || state_==State::TxResponse;
    }
    State state() const { return state_; }
    Result result() const { return result_; }
    int16_t radio_error() const { return error_; }
    uint8_t attempts() const { return attempts_; }
    uint32_t duplicates() const { return duplicates_; }
    void suppress_next_response() { suppress_response_=true; }

    int16_t stop() {
        paused_=true;armed_=false;state_=State::RxWait;
        error_=radio_.sleep();return error_;
    }

    bool arm(uint8_t local,uint8_t peer,Accept accept,void* context) {
        if(active() || local==peer || local==255 || peer==255 || !accept) return false;
        local_=local;peer_=peer;accept_=accept;context_=context;
        error_=radio_.init(local_,frequency_,tx_power_,long_range_);
        armed_=error_==0;
        paused_=false;next_rx_=1;pending_identity_=false;
        have_accepted_=false;duplicates_=0;
        suppress_response_=false;
        state_=armed_?State::RxWait:State::Failed;
        result_=armed_?Result::Pending:Result::RadioError;
        return armed_;
    }

    bool send_reliable_data(uint8_t sequence,const uint8_t* data,size_t size,
                            uint32_t now) {
        if(!armed_ || paused_ || active() || !data || !size || size>kMaxData ||
           !sequence) return false;
        if(pending_identity_ &&
           (wire_size_!=size+2 || memcmp(wire_+2,data,size))) return false;
        wire_[0]=SSOT_DATA_TYPE;wire_[1]=sequence;
        memcpy(wire_+2,data,size);wire_size_=static_cast<uint8_t>(size+2);
        sequence_=sequence;attempts_=0;pending_identity_=true;
        result_=Result::Pending;
        return transmit_data(now);
    }

    void poll(uint32_t now) {
        if(!armed_ || paused_) return;
        if(state_==State::TxData || state_==State::TxResponse) {
            const int16_t status=radio_.send_done();
            if(status<0) { fail(Result::RadioError,SSOT_DATA_TYPE,sequence_,status);return; }
            if(status==1) {
                if(state_==State::TxData) {
                    state_=State::WaitResponse;started_=now;
                    emit("DATA_TX_DONE",SSOT_DATA_TYPE,sequence_);
                } else {
                    state_=State::RxWait;
                    emit(reply_[0]==SSOT_ACK_TYPE?"ACK_TX_DONE":"NACK_TX_DONE",
                         reply_[0],reply_[1]);
                }
            } else if(now-started_>=LORA_TX_TIMEOUT_MS) {
                fail(Result::TxTimeout,SSOT_DATA_TYPE,sequence_);
            }
            return;
        }
        if(radio_.available()) {
            receive(now);
            return;
        }
        if(state_==State::WaitResponse && now-started_>=LORA_ACK_TIMEOUT_MS) {
            if(attempts_>=SSOT_MAX_ATTEMPTS) fail(Result::AckTimeout,SSOT_DATA_TYPE,sequence_);
            else {
                state_=State::RetryPending;
                emit("RETRY_SCHEDULED",SSOT_DATA_TYPE,sequence_);
            }
            return;
        }
        if(state_==State::RetryPending) transmit_data(now);
    }

private:
    void emit(const char* event,uint8_t type,uint8_t sequence,int16_t error=0) {
        if(event_) event_(event_context_,event,type,sequence,error);
    }

    void fail(Result result,uint8_t type,uint8_t sequence,int16_t error=-1) {
        const int16_t stopped=radio_.sleep();
        state_=State::Failed;result_=result;error_=error;armed_=false;
        if(stopped<0 && error==-1) error_=stopped;
        emit("TRANSACTION_FAILED",type,sequence,error_);
    }

    bool transmit_data(uint32_t now) {
        const int16_t error=radio_.send(peer_,wire_,wire_size_);
        if(error<0) { fail(Result::RadioError,SSOT_DATA_TYPE,sequence_,error);return false; }
        ++attempts_;started_=now;state_=State::TxData;
        emit("DATA_TX_BEGIN",SSOT_DATA_TYPE,sequence_);
        return true;
    }

    void receive(uint32_t now) {
        uint8_t source=0,destination=0,size=0;
        const int16_t error=radio_.recv(&source,&destination,rx_,sizeof rx_,&size);
        if(error<0) {
            if(error==RADIOLIB_ERR_CRC_MISMATCH || error==RADIOLIB_ERR_PACKET_TOO_LONG)
                emit("RX_DISCARD",0,0,error);
            else fail(Result::RadioError,0,0,error);
            return;
        }
        if(source!=peer_ || destination!=local_ || size<2 || size>251) {
            emit("RX_DISCARD",0,0);return;
        }

        const uint8_t type=rx_[0],sequence=rx_[1];
        if(type==SSOT_ACK_TYPE || type==SSOT_NACK_TYPE) {
            if(size!=2 || sequence!=sequence_ || state_!=State::WaitResponse ||
               now-started_>=LORA_ACK_TIMEOUT_MS) return;
            if(type==SSOT_ACK_TYPE) {
                state_=State::Complete;result_=Result::Accepted;
                pending_identity_=false;
                emit("ACK_ACCEPTED",type,sequence);
            } else if(attempts_>=SSOT_MAX_ATTEMPTS) {
                fail(Result::Rejected,type,sequence);
            } else {
                state_=State::RetryPending;
                emit("NACK_RX",type,sequence);
            }
            return;
        }
        if(type!=SSOT_DATA_TYPE || active() || size<3) {
            emit("RX_DISCARD",type,sequence);return;
        }

        const uint8_t data_size=static_cast<uint8_t>(size-2);
        const bool duplicate=have_accepted_ && sequence==last_sequence_ &&
            data_size==last_size_ && !memcmp(rx_+2,last_data_,data_size);
        bool accepted=duplicate;
        if(!duplicate && sequence==next_rx_)
            accepted=accept_(context_,sequence,rx_+2,data_size);
        if(accepted) {
            if(duplicate) { ++duplicates_;emit("DATA_DUP",type,sequence); }
            else {
                have_accepted_=true;last_sequence_=sequence;last_size_=data_size;
                memcpy(last_data_,rx_+2,data_size);
                next_rx_=sequence==UINT8_MAX?0:static_cast<uint8_t>(sequence+1);
                emit("DATA_VALIDATED",type,sequence);
            }
        }
        reply_[0]=accepted?SSOT_ACK_TYPE:SSOT_NACK_TYPE;reply_[1]=sequence;
        if(suppress_response_) {
            suppress_response_=false;state_=State::RxWait;
            emit("RESPONSE_DROPPED",reply_[0],sequence);return;
        }
        const int16_t sent=radio_.send(peer_,reply_,sizeof(reply_));
        if(sent<0) { fail(Result::RadioError,reply_[0],sequence,sent);return; }
        state_=State::TxResponse;started_=now;
        emit(accepted?"ACK_TX_BEGIN":"NACK_TX_BEGIN",reply_[0],sequence);
    }

    Radio& radio_;
    const float frequency_;
    const int8_t tx_power_;
    const uint8_t long_range_;
    Accept accept_=nullptr;
    Event event_=nullptr;
    void* context_=nullptr;
    void* event_context_=nullptr;
    State state_=State::RxWait;
    Result result_=Result::Pending;
    int16_t error_=0;
    bool armed_=false,paused_=false,have_accepted_=false,pending_identity_=false;
    bool suppress_response_=false;
    uint8_t local_=0,peer_=0,sequence_=1,attempts_=0,next_rx_=1;
    uint8_t last_sequence_=0,last_size_=0,wire_size_=0;
    uint32_t started_=0,duplicates_=0;
    uint8_t wire_[251]={},rx_[256]={},last_data_[kMaxData]={},reply_[2]={};
};
