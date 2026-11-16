// No repository-wide license is declared; existing rights are unchanged.

#include "receiver.h"

#include <string.h>

void arq::InitReceiver(arq::Receiver* receiver) {
  *receiver = {};
  receiver->expected = ARQ_INITIAL_SEQUENCE;
}
bool arq::ArmReceiver(arq::Receiver* receiver, uint32_t session) {
  if (receiver->armed && receiver->session == session) return true;
  if (receiver->state != arq::ReceiverState::kListening) return false;
  arq::InitReceiver(receiver);
  receiver->armed = true;
  receiver->session = session;
  return true;
}
bool arq::HandleDataFrame(arq::Receiver* receiver, const arq::Frame* frame,
                          arq::Frame* response, bool busy) {
  if (!receiver->armed || receiver->stopped || !arq::IsValidFrame(frame) ||
      frame->type != arq::kData || frame->src != arq::config::kSenderId ||
      frame->dst != arq::config::kReceiverId ||
      frame->session != receiver->session)
    return false;
  // VALIDATING checks content before replaying a previously accepted ACK.
  receiver->state = arq::ReceiverState::kValidating;
  *response = {};
  response->type = arq::kNack;
  response->src = arq::config::kReceiverId;
  response->dst = arq::config::kSenderId;
  response->session = receiver->session;
  response->sequence = frame->sequence;
  bool payload_ok = frame->length == sizeof(arq::config::kPayload) - 1 &&
                    !memcmp(frame->payload, arq::config::kPayload,
                            sizeof(arq::config::kPayload) - 1);
#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC)
  payload_ok = payload_ok ||
               (frame->length == sizeof(arq::config::kDirectionPayload) - 1 &&
                !memcmp(frame->payload, arq::config::kDirectionPayload,
                        sizeof(arq::config::kDirectionPayload) - 1));
#endif
  if (!payload_ok)
    response->reason = arq::kApplicationRejected;
  else if (receiver->accepted && frame->sequence == receiver->last_sequence) {
    response->type = arq::kAck;
    ++receiver->duplicates;
  } else if (frame->sequence != receiver->expected)
    response->reason = arq::kUnexpectedSequence;
  else if (busy)
    response->reason = arq::kBusy;
  else {
    // Acceptance precedes TX: response failure must not erase deduplication.
    receiver->accepted = true;
    receiver->last_sequence = frame->sequence;
    ++receiver->expected;
    ++receiver->deliveries;
    response->type = arq::kAck;
  }
  // The adapter owns SENDING_RESPONSE/RETURNING_TO_RX while the radio is busy.
  receiver->state = arq::ReceiverState::kListening;
  return true;
}
