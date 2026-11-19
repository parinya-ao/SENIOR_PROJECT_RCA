/// @file
/// Tracks session delivery and determines ACK/NACK responses without radio I/O.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_RECEIVER_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_RECEIVER_H_
#include "arq_codec.h"
#include "arq_config.h"
namespace arq {
/// Exposes adapter RX/response progress without changing protocol
/// representation.
enum class ReceiverState {
  kListening,
  kValidating,
  kSendingResponse,
  kReturningToRx
};
/// Tracks one foreground session and its last accepted DATA for duplicate ACK
/// replay. Initialize before use; state pointers must be non-null and never
/// shared with ISRs.
struct Receiver {
  /// A session is bound.
  bool armed;
  /// Incoming DATA must be ignored.
  bool stopped;
  /// There is an accepted sequence eligible for ACK replay.
  bool accepted;
  /// Bound wire session ID.
  uint32_t session;
  /// Number of unique accepted DATA packets.
  uint32_t deliveries;
  /// Number of recognized DATA duplicates.
  uint32_t duplicates;
  /// Next acceptable sequence, modulo uint16_t.
  uint16_t expected;
  /// Previous accepted sequence when accepted is true.
  uint16_t last_sequence;
  /// Adapter or receive validation phase.
  ReceiverState state;
};
/// Clears delivery history and starts unarmed at the configured initial
/// sequence.
/// @param receiver Non-null caller-owned state to reset.
void InitReceiver(Receiver* receiver);
/// Arms a new session only while listening; the same session is a no-op.
/// @param receiver Non-null initialized state.
/// @param session Wire session to bind.
/// @return True if already bound to session or successfully armed.
bool ArmReceiver(Receiver* receiver, uint32_t session);
/// Validates DATA and fills response with ACK/NACK, counting each delivery
/// once. Null/invalid/unrelated frames return false without changing response.
/// Response must be non-null and distinct from frame; busy rejects only new
/// valid deliveries.
/// @param receiver Non-null initialized receiver state.
/// @param frame Borrowed decoded DATA frame, or null.
/// @param response Non-null caller-owned response, disjoint from frame.
/// @param busy True to NACK a new valid delivery.
/// @return True if a reply was written.
bool HandleDataFrame(Receiver* receiver, const Frame* frame, Frame* response,
                     bool busy);
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_RECEIVER_H_
