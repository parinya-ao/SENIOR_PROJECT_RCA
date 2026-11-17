// Implements the foreground reliable DATA/ACK/NACK state machine over a radio.

#ifndef SENIOR_PROJECT_RCA_SRC_FEATURES_RELIABLE_TRANSFER_RELIABLE_TRANSPORT_H_
#define SENIOR_PROJECT_RCA_SRC_FEATURES_RELIABLE_TRANSFER_RELIABLE_TRANSPORT_H_

#include <RadioLib.h>
#include <ssot/ssot.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace reliable {

// Borrows a radio for its entire lifetime and owns bounded transaction buffers.
// Radio supplies init/send/send_done/recv/available/sleep; no virtual dispatch.
// Call only from the foreground, poll frequently and keep callbacks
// nonblocking. Callbacks and contexts must outlive all operations that can
// invoke them.
template <class Radio>
class Transport {
 public:
  enum class State : uint8_t {
    kRxWait,
    kTxData,
    kWaitResponse,
    kRetryPending,
    kTxResponse,
    kComplete,
    kFailed
  };
  enum class Result : uint8_t {
    kPending,
    kAccepted,
    kRejected,
    kInvalidArgument,
    kRadioError,
    kTxTimeout,
    kAckTimeout
  };
  using Accept = bool (*)(void*, uint8_t, const uint8_t*, uint8_t);
  using Event = void (*)(void*, const char*, uint8_t, uint8_t, int16_t);
  static constexpr uint8_t kMaxData = 249;

  // Borrows radio; construction stores parameters and performs no hardware I/O.
  Transport(Radio& radio, float frequency, int8_t tx_power, uint8_t long_range)
      : radio_(radio),
        frequency_(frequency),
        tx_power_(tx_power),
        long_range_(long_range) {}

  // Retains callback/context until replaced. Null callback disables
  // observations. Events run synchronously in the foreground; callbacks must
  // not reenter transport.
  void SetEventCallback(Event event, void* context) {
    event_ = event;
    event_context_ = context;
  }
  // Returns whether radio work or a response/retry deadline is outstanding.
  bool IsActive() const {
    return state_ == State::kTxData || state_ == State::kWaitResponse ||
           state_ == State::kRetryPending || state_ == State::kTxResponse;
  }
  bool IsTransmitting() const {
    return state_ == State::kTxData || state_ == State::kTxResponse;
  }
  State state() const { return state_; }
  Result result() const { return result_; }
  int16_t radio_error() const { return error_; }
  uint8_t attempts() const { return attempts_; }
  uint32_t duplicates() const { return duplicates_; }
  // Returns the current sender session or the receiver's adopted DATA session.
  uint16_t campaign_id() const { return campaign_id_; }
  // Drops one future response for explicit diagnostics, preserving duplicate
  // history.
  void SuppressNextResponse() { suppress_response_ = true; }

  // Parks the borrowed radio and cancels current work. Returns the driver
  // result. Rearm explicitly before sending again.
  int16_t Stop() {
    paused_ = true;
    armed_ = false;
    state_ = State::kRxWait;
    error_ = radio_.sleep();
    return error_;
  }

  // Initializes the existing PHY when no work is active. A nonzero campaign ID
  // binds a sender to one session; zero leaves a receiver unbound until its
  // first DATA frame. Duplicate history is retained for the same campaign and
  // cleared when a new campaign is observed. SendReliableData requires a
  // nonzero ID. Retains accept/context; peers must differ and must not use
  // broadcast address 255. A null callback or active transaction fails without
  // replacing configuration.
  bool Arm(uint8_t local, uint8_t peer, Accept accept, void* context,
           uint16_t campaign_id = 0) {
    if (IsActive() || local == peer || local == 255 || peer == 255 || !accept)
      return false;
    local_ = local;
    peer_ = peer;
    accept_ = accept;
    context_ = context;
    campaign_id_ = campaign_id;
    session_locked_ = campaign_id != 0;
    error_ = radio_.init(local_, frequency_, tx_power_, long_range_);
    armed_ = error_ == 0;
    paused_ = false;
    if (!have_accepted_ ||
        (campaign_id != 0 && last_campaign_id_ != campaign_id)) {
      have_accepted_ = false;
      next_rx_ = 1;
    }
    pending_identity_ = false;
    duplicates_ = 0;
    suppress_response_ = false;
    state_ = armed_ ? State::kRxWait : State::kFailed;
    result_ = armed_ ? Result::kPending : Result::kRadioError;
    return armed_;
  }

  // Copies 1..kMaxData bytes and starts one bounded reliable transaction.
  // Requires an armed idle radio, nonzero campaign ID/sequence and non-null
  // data. Pending identity prevents changing payload after a failed transaction
  // until explicit rearming.
  bool SendReliableData(uint8_t sequence, const uint8_t* data, size_t size,
                        uint32_t now) {
    if (!armed_ || paused_ || IsActive() || !campaign_id_ || !data || !size ||
        size > kMaxData || !sequence)
      return false;
    if (pending_identity_ &&
        (wire_size_ != size + 2 || memcmp(wire_ + 2, data, size)))
      return false;
    wire_[0] = ssot::kDataType;
    wire_[1] = sequence;
    memcpy(wire_ + 2, data, size);
    wire_size_ = static_cast<uint8_t>(size + 2);
    sequence_ = sequence;
    attempts_ = 0;
    pending_identity_ = true;
    result_ = Result::kPending;
    return TransmitData(now);
  }

  // Advances TX completion, receive handling and retry deadlines without
  // waiting. Timestamps are modulo-uint32 milliseconds; poll within the timeout
  // interval.
  void Poll(uint32_t now) {
    if (!armed_ || paused_) return;
    if (state_ == State::kTxData || state_ == State::kTxResponse) {
      const int16_t status = radio_.send_done();
      if (status < 0) {
        Fail(Result::kRadioError, ssot::kDataType, sequence_, status);
        return;
      }
      if (status == 1) {
        if (state_ == State::kTxData) {
          state_ = State::kWaitResponse;
          started_ = now;
          EmitEvent("DATA_TX_DONE", ssot::kDataType, sequence_);
        } else {
          state_ = State::kRxWait;
          EmitEvent(
              reply_[0] == ssot::kAckType ? "ACK_TX_DONE" : "NACK_TX_DONE",
              reply_[0], reply_[1]);
        }
      } else if (now - started_ >= LORA_TX_TIMEOUT_MS) {
        Fail(Result::kTxTimeout, ssot::kDataType, sequence_);
      }
      return;
    }
    if (radio_.available()) {
      HandleReceive(now);
      return;
    }
    if (state_ == State::kWaitResponse &&
        now - started_ >= LORA_ACK_TIMEOUT_MS) {
      if (attempts_ >= ssot::kMaxAttempts)
        Fail(Result::kAckTimeout, ssot::kDataType, sequence_);
      else {
        state_ = State::kRetryPending;
        EmitEvent("RETRY_SCHEDULED", ssot::kDataType, sequence_);
      }
      return;
    }
    if (state_ == State::kRetryPending) TransmitData(now);
  }

 private:
  // Reports an observation without owning the callback or its context.
  void EmitEvent(const char* event, uint8_t type, uint8_t sequence,
                 int16_t error = 0) {
    if (event_) event_(event_context_, event, type, sequence, error);
  }

  // Preserves the cause while parking hardware and requiring explicit rearming.
  void Fail(Result result, uint8_t type, uint8_t sequence, int16_t error = -1) {
    const int16_t stopped = radio_.sleep();
    state_ = State::kFailed;
    result_ = result;
    error_ = error;
    armed_ = false;
    if (stopped < 0 && error == -1) error_ = stopped;
    EmitEvent("TRANSACTION_FAILED", type, sequence, error_);
  }

  // Starts the immutable request and increments attempts only after driver
  // acceptance.
  bool TransmitData(uint32_t now) {
    const int16_t error = radio_.send(peer_, campaign_id_, wire_, wire_size_);
    if (error < 0) {
      Fail(Result::kRadioError, ssot::kDataType, sequence_, error);
      return false;
    }
    ++attempts_;
    started_ = now;
    state_ = State::kTxData;
    EmitEvent("DATA_TX_BEGIN", ssot::kDataType, sequence_);
    return true;
  }

  // Validates peers, packet bounds and response deadline before state
  // transitions. ACK replay does not redeliver already accepted payload bytes.
  void HandleReceive(uint32_t now) {
    uint8_t source = 0, destination = 0, size = 0;
    uint16_t campaign_id = 0;
    const int16_t error = radio_.recv(&source, &destination, &campaign_id, rx_,
                                      sizeof rx_, &size);
    if (error < 0) {
      if (error == RADIOLIB_ERR_CRC_MISMATCH ||
          error == RADIOLIB_ERR_PACKET_TOO_LONG)
        EmitEvent("RX_DISCARD", 0, 0, error);
      else
        Fail(Result::kRadioError, 0, 0, error);
      return;
    }
    if (destination != local_) {
      EmitEvent("RX_DISCARD_DEST", 0, 0);
      return;
    }
    if (source != peer_ || size < 2 || size > 251) {
      EmitEvent("RX_DISCARD", 0, 0);
      return;
    }
    if (session_locked_ && campaign_id != campaign_id_) {
      EmitEvent("RX_DISCARD", 0, 0);
      return;
    }

    const uint8_t type = rx_[0], sequence = rx_[1];
    if (type == ssot::kAckType || type == ssot::kNackType) {
      if (size != 2 || sequence != sequence_ ||
          state_ != State::kWaitResponse ||
          now - started_ >= LORA_ACK_TIMEOUT_MS)
        return;
      if (type == ssot::kAckType) {
        state_ = State::kComplete;
        result_ = Result::kAccepted;
        pending_identity_ = false;
        EmitEvent("ACK_ACCEPTED", type, sequence);
      } else if (attempts_ >= ssot::kMaxAttempts) {
        Fail(Result::kRejected, type, sequence);
      } else {
        state_ = State::kRetryPending;
        EmitEvent("NACK_RX", type, sequence);
      }
      return;
    }
    if (type != ssot::kDataType || IsActive() || size < 3) {
      EmitEvent("RX_DISCARD", type, sequence);
      return;
    }
    if (!session_locked_) {
      if (have_accepted_ && campaign_id != last_campaign_id_) {
        have_accepted_ = false;
        next_rx_ = 1;
      }
      campaign_id_ = campaign_id;
      session_locked_ = true;
    }

    const uint8_t data_size = static_cast<uint8_t>(size - 2);
    const bool duplicate =
        have_accepted_ && campaign_id_ == last_campaign_id_ &&
        sequence == last_sequence_ && data_size == last_size_ &&
        !memcmp(rx_ + 2, last_data_, data_size);
    bool accepted = duplicate;
    if (!duplicate && sequence == next_rx_)
      accepted = accept_(context_, sequence, rx_ + 2, data_size);
    if (accepted) {
      if (duplicate) {
        ++duplicates_;
        EmitEvent("DATA_DUP", type, sequence);
      } else {
        have_accepted_ = true;
        last_campaign_id_ = campaign_id_;
        last_sequence_ = sequence;
        last_size_ = data_size;
        memcpy(last_data_, rx_ + 2, data_size);
        next_rx_ =
            sequence == UINT8_MAX ? 0 : static_cast<uint8_t>(sequence + 1);
        EmitEvent("DATA_VALIDATED", type, sequence);
      }
    }
    reply_[0] = accepted ? ssot::kAckType : ssot::kNackType;
    reply_[1] = sequence;
    if (suppress_response_) {
      suppress_response_ = false;
      state_ = State::kRxWait;
      EmitEvent("RESPONSE_DROPPED", reply_[0], sequence);
      return;
    }
    const int16_t sent =
        radio_.send(peer_, campaign_id_, reply_, sizeof(reply_));
    if (sent < 0) {
      Fail(Result::kRadioError, reply_[0], sequence, sent);
      return;
    }
    state_ = State::kTxResponse;
    started_ = now;
    EmitEvent(accepted ? "ACK_TX_BEGIN" : "NACK_TX_BEGIN", reply_[0], sequence);
  }

  // Non-owning reference; radio and callback contexts must outlive this
  // instance.
  Radio& radio_;
  const float frequency_;
  const int8_t tx_power_;
  const uint8_t long_range_;
  Accept accept_ = nullptr;
  Event event_ = nullptr;
  void* context_ = nullptr;
  void* event_context_ = nullptr;
  State state_ = State::kRxWait;
  Result result_ = Result::kPending;
  int16_t error_ = 0;
  // These independent latches describe configuration, parking and replay
  // history.
  bool armed_ = false, paused_ = false, have_accepted_ = false,
       pending_identity_ = false, session_locked_ = false;
  bool suppress_response_ = false;
  uint8_t local_ = 0, peer_ = 0, sequence_ = 1, attempts_ = 0, next_rx_ = 1;
  uint8_t last_sequence_ = 0, last_size_ = 0, wire_size_ = 0;
  uint16_t campaign_id_ = 0;
  uint16_t last_campaign_id_ = 0;
  // Origin of the current TX/ACK timeout; unsigned subtraction tolerates
  // rollover.
  uint32_t started_ = 0, duplicates_ = 0;
  // Separate bounded TX/RX/replay buffers prevent a receive from altering
  // retries.
  uint8_t wire_[251] = {}, rx_[256] = {}, last_data_[kMaxData] = {},
          reply_[2] = {};
};

}  // namespace reliable
#endif  // SENIOR_PROJECT_RCA_SRC_FEATURES_RELIABLE_TRANSFER_RELIABLE_TRANSPORT_H_
