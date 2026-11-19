// Implements the foreground reliable DATA/ACK/NACK state machine over a radio.

#ifndef SENIOR_PROJECT_RCA_SRC_FEATURES_RELIABLE_TRANSFER_RELIABLE_TRANSPORT_H_
#define SENIOR_PROJECT_RCA_SRC_FEATURES_RELIABLE_TRANSFER_RELIABLE_TRANSPORT_H_

#include <RadioLib.h>
#include <ssot.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace reliable {

/// Borrows a radio for its entire lifetime and owns bounded transaction
/// buffers. Radio supplies init/send/send_done/recv/available/sleep; no virtual
/// dispatch. Call only from the foreground, poll frequently and keep callbacks
/// nonblocking. Callbacks and contexts must outlive all operations that can
/// invoke them.
template <class Radio>
class Transport {
 public:
  /// Operational phase of the radio or transaction.
  enum class State : uint8_t {
    kRxWait,        ///< Ready to receive DATA.
    kTxData,        ///< Transmitting DATA.
    kWaitResponse,  ///< Waiting for a matching ACK or NACK.
    kRetryPending,  ///< Waiting for the next poll to retry.
    kTxResponse,    ///< Transmitting a control response.
    kComplete,      ///< A matching ACK was accepted.
    kFailed         ///< Radio or transaction failure.
  };
  /// Outcome of the last sender transaction or radio operation.
  enum class Result : uint8_t {
    kPending,          ///< No final result yet.
    kAccepted,         ///< A matching ACK was accepted.
    kRejected,         ///< NACK exhausted the retry budget.
    kInvalidArgument,  ///< Invalid transaction argument.
    kRadioError,       ///< Driver reported an error.
    kTxTimeout,        ///< TX did not complete in time.
    kAckTimeout        ///< Response or transaction time budget expired.
  };
  /// Validates one DATA payload. The byte view lasts only for the callback.
  using Accept = bool (*)(void*, uint8_t, const uint8_t*, uint8_t);
  /// Reports an event name, type, sequence and driver status.
  using Event = void (*)(void*, const char*, uint8_t, uint8_t, int16_t);
  /// Maximum application bytes in one DATA packet.
  static constexpr uint8_t kMaxData = 249;
  /// Absolute sender transaction limit in milliseconds.
  static constexpr uint32_t kTransactionTimeoutMs =
      ssot::kMaxAttempts * (uint32_t{LORA_TX_TIMEOUT_MS} + LORA_ACK_TIMEOUT_MS);

  /// Borrows radio; construction stores parameters and performs no hardware
  /// I/O.
  /// @param radio Borrowed radio, with lifetime exceeding the transport.
  /// @param frequency Center frequency in MHz.
  /// @param tx_power Output power in dBm.
  /// @param long_range Nonzero to select the long-range PHY.
  Transport(Radio& radio, float frequency, int8_t tx_power, uint8_t long_range)
      : radio_(radio),
        frequency_(frequency),
        tx_power_(tx_power),
        long_range_(long_range) {}

  /// Retains callback/context until replaced. Null callback disables
  /// observations. Events run synchronously in the foreground; callbacks must
  /// not reenter transport.
  /// @param event Callback, or null to disable observations.
  /// @param context Opaque caller data passed to the callback.
  void SetEventCallback(Event event, void* context) {
    event_ = event;
    event_context_ = context;
  }
  /// @return True while radio work or a response/retry deadline is outstanding.
  bool IsActive() const {
    return state_ == State::kTxData || state_ == State::kWaitResponse ||
           state_ == State::kRetryPending || state_ == State::kTxResponse;
  }
  /// @return True while a DATA or response TX is outstanding.
  bool IsTransmitting() const {
    return state_ == State::kTxData || state_ == State::kTxResponse;
  }
  /// @return Current radio or transaction phase.
  State state() const { return state_; }
  /// @return Current transaction outcome.
  Result result() const { return result_; }
  /// @return Last stored driver or transaction error.
  int16_t radio_error() const { return error_; }
  /// @return Number of DATA transmissions started.
  uint8_t attempts() const { return attempts_; }
  /// @return Number of duplicate DATA frames seen since arming.
  uint32_t duplicates() const { return duplicates_; }
  /// @return Current sender campaign or the receiver's adopted DATA campaign.
  uint16_t campaign_id() const { return campaign_id_; }
  /// Campaign of the event currently being delivered.
  uint16_t event_campaign_id() const { return event_campaign_id_; }
  /// Fixed one-shot faults available to the board-owned bench console.
  enum class ResponseFault : uint8_t {
    kNone,
    kDrop,
    kCampaign,
    kSequence,
    kDuplicate
  };
  void SetResponseFault(ResponseFault fault) {
    response_fault_ = fault;
    if (fault == ResponseFault::kNone) repeat_ack_ = false;
  }
  void SuppressNextResponse() { SetResponseFault(ResponseFault::kDrop); }

  /// Parks the radio and cancels current work. Rearm before sending again.
  /// @return Driver status from parking the radio.
  int16_t Stop() {
    paused_ = true;
    armed_ = false;
    response_fault_ = ResponseFault::kNone;
    repeat_ack_ = sending_repeat_ = false;
    state_ = State::kRxWait;
    error_ = radio_.sleep();
    return error_;
  }

  /// Initializes the existing PHY when no work is active. A nonzero campaign ID
  /// binds a sender to one session; zero leaves a receiver unbound until its
  /// first DATA frame. Duplicate history is retained for the same campaign and
  /// cleared when a new campaign is observed. SendReliableData requires a
  /// nonzero ID. Retains accept/context; peers must differ and must not use
  /// broadcast address 255. A null callback or active transaction fails without
  /// replacing configuration.
  /// @param local Local unicast address.
  /// @param peer Remote unicast address.
  /// @param accept DATA payload validator.
  /// @param context Opaque caller data passed to the validator.
  /// @param campaign_id Initial campaign, or zero to adopt one from DATA.
  /// @return True if the radio is armed.
  bool Arm(uint8_t local, uint8_t peer, Accept accept, void* context,
           uint16_t campaign_id = 0) {
    if (IsActive() || local == peer || local == 255 || peer == 255 || !accept)
      return false;
    if (local_ != local || peer_ != peer) {
      have_accepted_ = false;
      tx_campaign_id_ = 0;
      last_tx_sequence_ = 0;
    }
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
    duplicates_ = 0;
    response_fault_ = ResponseFault::kNone;
    repeat_ack_ = sending_repeat_ = false;
    state_ = armed_ ? State::kRxWait : State::kFailed;
    result_ = armed_ ? Result::kPending : Result::kRadioError;
    return armed_;
  }

  /// Copies 1..kMaxData bytes and starts one bounded reliable transaction.
  /// Requires an armed idle radio and a nonzero campaign. A failed request can
  /// restart only with identical bytes and sequence in that campaign.
  /// @param sequence Nonzero transaction sequence.
  /// @param data Caller buffer copied synchronously.
  /// @param size Application bytes to copy.
  /// @param now Local time in milliseconds.
  /// @return True if the first DATA TX starts.
  bool SendReliableData(uint8_t sequence, const uint8_t* data, size_t size,
                        uint32_t now) {
    if (!armed_ || paused_ || IsActive() || !campaign_id_ || !data || !size ||
        size > kMaxData || !sequence)
      return false;
    if (tx_campaign_id_ == campaign_id_) {
      if (tx_outstanding_) {
        if (sequence != last_tx_sequence_ || size + 2 != wire_size_ ||
            memcmp(wire_ + 2, data, size) != 0)
          return false;
      } else if (sequence <= last_tx_sequence_) {
        return false;
      }
    }
    tx_campaign_id_ = campaign_id_;
    last_tx_sequence_ = sequence;
    tx_outstanding_ = true;
    transaction_started_ = now;
    wire_[0] = ssot::kDataType;
    wire_[1] = sequence;
    memcpy(wire_ + 2, data, size);
    wire_size_ = static_cast<uint8_t>(size + 2);
    sequence_ = sequence;
    attempts_ = 0;
    result_ = Result::kPending;
    return TransmitData(now);
  }

  /// Advances TX completion, receive handling and retry deadlines without
  /// waiting. Timestamps are modulo-uint32 milliseconds; poll within the
  /// timeout interval.
  /// @param now Local time in milliseconds.
  void Poll(uint32_t now, bool receive_data = true) {
    if (!armed_ || paused_) return;
    if (IsActive() && state_ != State::kTxResponse &&
        now - transaction_started_ >= kTransactionTimeoutMs) {
      Fail(state_ == State::kTxData ? Result::kTxTimeout : Result::kAckTimeout,
           ssot::kDataType, sequence_);
      return;
    }
    switch (state_) {
      case State::kTxData:
      case State::kTxResponse:
        PollTransmit(now);
        return;
      case State::kWaitResponse:
        if (now - started_ >= LORA_ACK_TIMEOUT_MS) {
          HandleAckTimeout();
          return;
        }
        break;
      case State::kRetryPending:
        TransmitData(now);
        return;
      default:
        break;
    }
    if (radio_.available()) HandleReceive(now, receive_data);
  }

 private:
  /// @brief Emits an event synchronously without taking callback ownership.
  /// @param event Stable event name.
  /// @param type Wire message type.
  /// @param sequence Wire sequence number.
  /// @param error Driver status or zero.
  void EmitEvent(const char* event, uint8_t type, uint8_t sequence,
                 int16_t error = 0, uint16_t campaign = 0) {
    event_campaign_id_ = campaign ? campaign : campaign_id_;
    if (event_) event_(event_context_, event, type, sequence, error);
  }

  /// @brief Stops the radio and records a terminal transaction failure.
  /// @param result Transaction outcome to retain.
  /// @param type Wire type associated with the failure event.
  /// @param sequence Sequence associated with the failure event.
  /// @param error Original error code, when available.
  /// @post The transport is failed and must be armed again before reuse.
  void Fail(Result result, uint8_t type, uint8_t sequence, int16_t error = -1) {
    const int16_t stopped = radio_.sleep();
    state_ = State::kFailed;
    result_ = result;
    error_ = error;
    armed_ = false;
    if (stopped < 0 && error == -1) error_ = stopped;
    EmitEvent("TRANSACTION_FAILED", type, sequence, error_);
  }

  /// @brief Starts a retry using the transport-owned DATA bytes.
  /// @param now Current wrapping millisecond counter.
  /// @return True if the radio accepted the transmission request.
  /// @post Attempts increase only after driver acceptance.
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

  /// @brief Polls completion of the current asynchronous transmission.
  /// @param now Current wrapping millisecond counter.
  /// @post DATA TX completion starts its response timeout; response TX returns
  ///   to receive state.
  void PollTransmit(uint32_t now) {
    bool tx_done = false;
    int16_t rearm = 0;
    const int16_t status = radio_.send_done(&tx_done, &rearm);
    const bool data = state_ == State::kTxData;
    const uint8_t type = data ? ssot::kDataType : reply_[0];
    const uint8_t seq = data ? sequence_ : reply_[1];
    const uint16_t campaign = data ? campaign_id_ : reply_campaign_;
    if (tx_done) {
      const char* event = "DATA_TX_DONE";
      if (!data) {
        event = type == ssot::kAckType ? "ACK_TX_DONE" : "NACK_TX_DONE";
        if (sending_repeat_) event = "ACK_DUP_TX_DONE";
      }
      EmitEvent(event, type, seq, 0, campaign);
      if (rearm < 0) EmitEvent("RX_REARM_FAILED", type, seq, rearm, campaign);
    }
    if (status < 0) {
      Fail(Result::kRadioError, type, seq, status);
    } else if (status == 1) {
      if (data) {
        state_ = State::kWaitResponse;
        started_ = now;
        EmitEvent("RX_REARMED", ssot::kDataType, sequence_);
      } else {
        state_ = State::kRxWait;
        sending_repeat_ = false;
        if (repeat_ack_) {
          repeat_ack_ = false;
          sending_repeat_ = TransmitResponse(now);
        }
      }
    } else if (now - started_ >= LORA_TX_TIMEOUT_MS) {
      Fail(Result::kTxTimeout, type, seq);
    }
  }

  /// @brief Schedules a retry or fails when the configured attempt budget ends.
  /// @post The original absolute transaction deadline is unchanged.
  void HandleAckTimeout() {
    if (attempts_ >= ssot::kMaxAttempts) {
      Fail(Result::kAckTimeout, ssot::kDataType, sequence_);
      return;
    }
    state_ = State::kRetryPending;
    EmitEvent("RETRY_SCHEDULED", ssot::kDataType, sequence_);
  }

  /// @brief Reads and classifies one available radio packet.
  /// @param now Current wrapping millisecond counter.
  /// @post Invalid packets cannot advance transaction or application state.
  void HandleReceive(uint32_t now, bool receive_data) {
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
      EmitEvent("RX_DISCARD_DEST", size >= 2 ? rx_[0] : 0,
                size >= 2 ? rx_[1] : 0, 0, campaign_id);
      return;
    }
    if (source != peer_ || size < 2 || size > 251 || !campaign_id || !rx_[1]) {
      EmitEvent("RX_DISCARD", 0, 0);
      return;
    }
    if (session_locked_ && campaign_id != campaign_id_ &&
        !CanRollCampaign(campaign_id, size)) {
      if (rx_[0] == ssot::kAckType || rx_[0] == ssot::kNackType)
        EmitEvent("CONTROL_IGNORED", rx_[0], rx_[1], 0, campaign_id);
      else
        EmitEvent("RX_DISCARD", rx_[0], rx_[1], 0, campaign_id);
      return;
    }
    if (rx_[0] == ssot::kAckType || rx_[0] == ssot::kNackType) {
      HandleControl(size);
    } else if (receive_data) {
      HandleData(campaign_id, size, now);
    }
  }

  /// @brief Checks whether the expected DATA frame may advance the campaign.
  /// @param campaign_id Campaign identifier from the received header.
  /// @param size Received payload size.
  /// @return True only at sequence rollover for the immediate successor
  ///   campaign and its first DATA sequence.
  bool CanRollCampaign(uint16_t campaign_id, uint8_t size) const {
    return next_rx_ == 0 && rx_[0] == ssot::kDataType && size >= 3 &&
           rx_[1] == ssot::kSequence &&
           campaign_id == ssot::NextCampaignId(campaign_id_);
  }

  /// @brief Applies an ACK or NACK to the outstanding transaction.
  /// @param size Control payload size.
  /// @pre HandleReceive has validated peer, destination, and campaign.
  /// @post Only an exact two-byte matching sequence can change the transaction.
  void HandleControl(uint8_t size) {
    const uint8_t type = rx_[0], sequence = rx_[1];
    if (size != 2 || sequence != sequence_ || state_ != State::kWaitResponse) {
      EmitEvent("CONTROL_IGNORED", type, sequence);
      return;
    }
    if (type == ssot::kAckType) {
      EmitEvent("ACK_RX", type, sequence);
      tx_outstanding_ = false;
      state_ = State::kComplete;
      result_ = Result::kAccepted;
      EmitEvent("ACK_ACCEPTED", type, sequence);
      return;
    }
    EmitEvent("NACK_RX", type, sequence);
    if (attempts_ >= ssot::kMaxAttempts)
      Fail(Result::kRejected, type, sequence);
    else
      state_ = State::kRetryPending;
  }

  /// @brief Validates an incoming DATA packet and schedules its response.
  /// @param campaign_id Campaign identifier from the radio header.
  /// @param size Received payload size.
  /// @param now Current wrapping millisecond counter.
  void HandleData(uint16_t campaign_id, uint8_t size, uint32_t now) {
    const uint8_t type = rx_[0], sequence = rx_[1];
    if (type != ssot::kDataType || IsActive() || size < 3) {
      EmitEvent("RX_DISCARD", type, sequence);
      return;
    }
    const bool accepted =
        ValidatePayload(campaign_id, sequence, static_cast<uint8_t>(size - 2));
    SendResponse(campaign_id, sequence, accepted, now);
  }

  /// @brief Checks duplicates and invokes the application DATA validator.
  /// @param sequence Received DATA sequence.
  /// @param data_size Application payload length.
  /// @return True for accepted data or an exact duplicate of accepted data.
  /// @post Accepted payload bytes are saved before the ACK is sent; sequence
  ///   zero marks an exhausted receive campaign.
  bool ValidatePayload(uint16_t campaign_id, uint8_t sequence,
                       uint8_t data_size) {
    if (have_accepted_ && campaign_id == last_campaign_id_ &&
        sequence == last_sequence_ && data_size == last_size_ &&
        memcmp(rx_ + 2, last_data_, data_size) == 0) {
      campaign_id_ = campaign_id;
      session_locked_ = true;
      ++duplicates_;
      EmitEvent("DATA_DUP", ssot::kDataType, sequence);
      return true;
    }
    const uint8_t expected = have_accepted_ && campaign_id == last_campaign_id_
                                 ? next_rx_
                                 : ssot::kSequence;
    if (sequence != expected) {
      EmitEvent("DATA_REJECTED_SEQUENCE", ssot::kDataType, sequence);
      return false;
    }
    event_campaign_id_ = campaign_id;
    if (!accept_(context_, sequence, rx_ + 2, data_size)) return false;

    campaign_id_ = campaign_id;
    session_locked_ = true;
    have_accepted_ = true;
    last_campaign_id_ = campaign_id;
    last_sequence_ = sequence;
    last_size_ = data_size;
    memcpy(last_data_, rx_ + 2, data_size);
    next_rx_ = sequence == UINT8_MAX ? 0 : static_cast<uint8_t>(sequence + 1);
    EmitEvent("DATA_VALIDATED", ssot::kDataType, sequence);
    return true;
  }

  /// @brief Sends the ACK/NACK response or drops it for explicit diagnostics.
  /// @param sequence DATA sequence being acknowledged or rejected.
  /// @param accepted Whether application validation accepted the payload.
  /// @param now Current wrapping millisecond counter.
  /// @post The reply remains in owned storage until asynchronous TX completes.
  void SendResponse(uint16_t campaign_id, uint8_t sequence, bool accepted,
                    uint32_t now) {
    reply_[0] = accepted ? ssot::kAckType : ssot::kNackType;
    reply_[1] = sequence;
    reply_campaign_ = campaign_id;
    const ResponseFault fault = response_fault_;
    response_fault_ = ResponseFault::kNone;
    if (fault == ResponseFault::kDrop) {
      state_ = State::kRxWait;
      EmitEvent("RESPONSE_DROPPED", reply_[0], sequence, 0, campaign_id);
      return;
    }
    if (accepted && fault == ResponseFault::kCampaign)
      reply_campaign_ = ssot::NextCampaignId(campaign_id);
    if (accepted && fault == ResponseFault::kSequence)
      reply_[1] = sequence == UINT8_MAX ? ssot::kSequence : sequence + 1;
    repeat_ack_ = accepted && fault == ResponseFault::kDuplicate;
    if (TransmitResponse(now))
      EmitEvent(accepted ? "ACK_TX_BEGIN" : "NACK_TX_BEGIN", reply_[0],
                reply_[1], 0, reply_campaign_);
  }

  /// Starts TX of the owned two-byte response and keeps it until TxDone.
  bool TransmitResponse(uint32_t now) {
    const int16_t sent =
        radio_.send(peer_, reply_campaign_, reply_, sizeof(reply_));
    if (sent < 0) {
      Fail(Result::kRadioError, reply_[0], reply_[1], sent);
      return false;
    }
    state_ = State::kTxResponse;
    started_ = now;
    return true;
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
       session_locked_ = false;
  bool tx_outstanding_ = false, repeat_ack_ = false, sending_repeat_ = false;
  ResponseFault response_fault_ = ResponseFault::kNone;
  uint8_t local_ = 0, peer_ = 0, sequence_ = 1, attempts_ = 0, next_rx_ = 1;
  uint8_t last_sequence_ = 0, last_size_ = 0, wire_size_ = 0;
  uint8_t last_tx_sequence_ = 0;
  uint16_t campaign_id_ = 0, tx_campaign_id_ = 0;
  uint16_t last_campaign_id_ = 0;
  uint16_t event_campaign_id_ = 0, reply_campaign_ = 0;
  // Origin of the current TX/ACK timeout; unsigned subtraction tolerates
  // rollover.
  uint32_t started_ = 0, transaction_started_ = 0, duplicates_ = 0;
  // Separate bounded TX/RX/replay buffers prevent a receive from altering
  // retries.
  uint8_t wire_[251] = {}, rx_[256] = {}, last_data_[kMaxData] = {},
          reply_[2] = {};
};

}  // namespace reliable
#endif  // SENIOR_PROJECT_RCA_SRC_FEATURES_RELIABLE_TRANSFER_RELIABLE_TRANSPORT_H_
