// No repository-wide license is declared; existing rights are unchanged.

// Tracks session delivery and determines ACK/NACK responses without radio I/O.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_RECEIVER_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_RECEIVER_H_
#include "codec.h"
#include "config.h"
namespace arq {
// Exposes adapter RX/response progress without changing protocol
// representation.
enum class ReceiverState {
  kListening,
  kValidating,
  kSendingResponse,
  kReturningToRx
};
// Tracks one foreground session and its last accepted DATA for duplicate ACK
// replay. Initialize before use; state pointers must be non-null and never
// shared with ISRs.
struct Receiver {
  bool armed;
  bool stopped;
  bool accepted;
  uint32_t session;
  uint32_t deliveries;
  uint32_t duplicates;
  uint16_t expected;
  uint16_t last_sequence;
  ReceiverState state;
};
// Clears delivery history and starts unarmed at the configured initial
// sequence.
void InitReceiver(Receiver* receiver);
// Arms a new session only while listening; the same session is a no-op.
bool ArmReceiver(Receiver* receiver, uint32_t session);
// Validates DATA and fills response with ACK/NACK, counting each delivery once.
// Null/invalid/unrelated frames return false without changing response.
// Response must be non-null and distinct from frame; busy rejects only new
// valid deliveries.
bool HandleDataFrame(Receiver* receiver, const Frame* frame, Frame* response,
                     bool busy);
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_RECEIVER_H_
