// Implements bounded sender retries, deadlines, and correlated ACK handling.
#include <string.h>

#include "arq_sender.h"

bool arq::IsDeadlineDue(uint32_t now_ms,
                        uint32_t deadline) {  // Deadlines must be less than
                                              // half the uint32_t range apart.
  return now_ms - deadline < (UINT32_C(1) << 31U);
}
void arq::InitSender(arq::Sender* sender) {
  *sender = {};
  sender->sequence = ARQ_INITIAL_SEQUENCE;
}
bool arq::IsSenderActive(const arq::Sender* sender) {
  return sender->state == arq::SenderState::kTransmitting ||
         sender->state == arq::SenderState::kWaitingAck ||
         sender->state == arq::SenderState::kBackoff;
}
bool arq::ArmSender(arq::Sender* sender, uint32_t session) {
  if (sender->armed && sender->session == session) return true;
  if (arq::IsSenderActive(sender)) return false;
  bool has_start = sender->has_start;
  uint32_t last_start = sender->last_start;
  arq::InitSender(sender);
  sender->session = session;
  sender->armed = true;
  // A new session cannot bypass the radio's minimum DATA start spacing.
  sender->has_start = has_start;
  sender->last_start = last_start;
  return true;
}
namespace {

// Retains diagnostics and prevents reusing a failed session/sequence pair.
void FailTransaction(arq::Sender* sender, arq::Result result) {
  // FAILED retains diagnostics; this pair cannot carry different application
  // data.
  sender->state = arq::SenderState::kFailed;
  sender->result = result;
  sender->used_up = true;
}
// Hands one immutable frame to the foreground radio adapter.
void StartAttempt(arq::Sender* sender, uint32_t now_ms) {
  // TRANSMITTING hands one immutable frame to the radio adapter.
  sender->state = arq::SenderState::kTransmitting;
  sender->last_start = now_ms;
  sender->has_start = true;
  ++sender->attempts;
}
}  // namespace

bool arq::RequestTransmission(arq::Sender* sender, const uint8_t* payload,
                              size_t length, uint32_t now_ms,
                              uint32_t ack_timeout_ms) {
  if (!sender->armed || sender->stopped || sender->used_up ||
      arq::IsSenderActive(sender) || !payload ||
      length > arq::kMaxPayloadBytes || ack_timeout_ms < ARQ_ACK_MIN_MS ||
      ack_timeout_ms > ARQ_ACK_MAX_MS)
    return false;
  sender->frame = {};
  sender->frame.type = arq::kData;
  sender->frame.src = arq::config::kSenderId;
  sender->frame.dst = arq::config::kReceiverId;
  sender->frame.session = sender->session;
  sender->frame.sequence = sender->sequence;
  sender->frame.length = static_cast<uint8_t>(length);
  memcpy(sender->frame.payload, payload, length);
  sender->attempts = 0;
  sender->interval = ack_timeout_ms;
  sender->result = arq::Result::kPending;
  uint32_t bound = 0;
  for (uint8_t i = 0; i <= arq::config::kMaxRetries; i++)
    bound += (ack_timeout_ms << i) + ARQ_TX_MS + ARQ_SPACING_MS;
  sender->terminal_at = now_ms + bound;
  sender->retry_at =
      sender->has_start ? sender->last_start + ARQ_SPACING_MS : now_ms;
  // BACKOFF also enforces spacing between separate explicit requests.
  sender->state = arq::SenderState::kBackoff;
  if (arq::IsDeadlineDue(now_ms, sender->retry_at))
    StartAttempt(sender, now_ms);
  return true;
}
void arq::HandleTxCompletion(arq::Sender* sender, uint32_t now_ms,
                             bool success) {
  if (sender->state != arq::SenderState::kTransmitting) return;
  if (!success) {
    FailTransaction(sender, arq::Result::kRadioError);
    return;
  }
  // WAITING_ACK starts only after TxDone, cleanup and RX arming succeed.
  sender->tx_done = now_ms;
  sender->retry_at = now_ms + sender->interval;
  sender->state = arq::SenderState::kWaitingAck;
}
void arq::HandleControlFrame(arq::Sender* sender, const arq::Frame* frame,
                             uint32_t now_ms) {
  if ((sender->state != arq::SenderState::kWaitingAck &&
       sender->state != arq::SenderState::kBackoff) ||
      !sender->attempts || !arq::IsValidFrame(frame) ||
      frame->src != arq::config::kReceiverId ||
      frame->dst != arq::config::kSenderId ||
      frame->session != sender->session || frame->sequence != sender->sequence)
    return;
  // A queued control must not revive a transaction past its absolute lifetime.
  if (arq::IsDeadlineDue(now_ms, sender->terminal_at)) {
    FailTransaction(sender, arq::Result::kTimeoutExhausted);
    return;
  }
  if (frame->type == arq::kAck) {
    if (sender->attempts == 1) {
      sender->rtt_last = now_ms - sender->tx_done;
      if (!sender->rtt_count || sender->rtt_last < sender->rtt_min)
        sender->rtt_min = sender->rtt_last;
      if (!sender->rtt_count || sender->rtt_last > sender->rtt_max)
        sender->rtt_max = sender->rtt_last;
      ++sender->rtt_count;
    }
    // DELIVERED is the only transition that advances sequence.
    sender->state = arq::SenderState::kDelivered;
    sender->result = arq::Result::kOk;
    ++sender->sequence;
    if (sender->sequence == ARQ_INITIAL_SEQUENCE) sender->used_up = true;
  } else if (frame->type == arq::kNack) {
    if (frame->reason == arq::kApplicationRejected)
      FailTransaction(sender, arq::Result::kRejected);
    else if (frame->reason == arq::kUnexpectedSequence)
      FailTransaction(sender, arq::Result::kProtocolError);
    // BUSY uses the same retry deadline; repeats never extend it.
    else
      sender->state = arq::SenderState::kBackoff;
  }
}
void arq::PollSender(arq::Sender* sender, uint32_t now_ms) {
  if (!arq::IsSenderActive(sender)) return;
  if (arq::IsDeadlineDue(now_ms, sender->terminal_at)) {
    FailTransaction(sender, arq::Result::kTimeoutExhausted);
    return;
  }
  if (sender->state == arq::SenderState::kTransmitting) {
    if (now_ms - sender->last_start >= ARQ_TX_MS)
      FailTransaction(sender, arq::Result::kRadioError);
    return;
  }
  if (!arq::IsDeadlineDue(now_ms, sender->retry_at)) return;
  if (sender->attempts > arq::config::kMaxRetries) {
    FailTransaction(sender, arq::Result::kTimeoutExhausted);
    return;
  }
  // BACKOFF adds spacing only, never another complete timeout interval.
  sender->state = arq::SenderState::kBackoff;
  if (sender->has_start && now_ms - sender->last_start < ARQ_SPACING_MS) return;
  if (sender->attempts) sender->interval *= 2;
  StartAttempt(sender, now_ms);
}
void arq::StopSender(arq::Sender* sender) { sender->stopped = true; }
