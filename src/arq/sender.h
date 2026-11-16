// No repository-wide license is declared; existing rights are unchanged.

// Owns caller-held ARQ transaction and deadline state; foreground access only.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_SENDER_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_SENDER_H_
#include "codec.h"
#include "config.h"
namespace arq {
// Keeps the original native int representation; states never become wire bytes.
enum class SenderState {
  kIdle,
  kTransmitting,
  kWaitingAck,
  kBackoff,
  kDelivered,
  kFailed
};
// Distinguishes terminal failure reasons from a pending or delivered
// transaction.
enum class Result {
  kPending,
  kOk,
  kRejected,
  kProtocolError,
  kTimeoutExhausted,
  kRadioError
};
// Owns one immutable in-flight frame and bounded retry state, without heap
// allocation. All operations require a non-null initialized state in the
// foreground context. The radio adapter calls TX completion only after cleanup
// and successful RX arming.
struct Sender {
  SenderState state;
  Result result;
  bool armed;
  bool stopped;
  // Distinguishes a real start at timestamp zero from a never-started sender.
  bool has_start;
  // Prevents session/sequence reuse after failure or full sequence wraparound.
  bool used_up;
  uint32_t session;
  // All timestamps and intervals below are milliseconds, modulo uint32_t.
  uint32_t last_start;
  uint32_t retry_at;
  uint32_t terminal_at;
  uint32_t interval;
  uint32_t tx_done;
  // RTT samples are valid only for successful transactions without
  // retransmission.
  uint32_t rtt_count;
  uint32_t rtt_last;
  uint32_t rtt_min;
  uint32_t rtt_max;
  uint16_t sequence;
  uint8_t attempts;
  Frame frame;
};
// Tests a wraparound deadline; now/deadline must be less than 2^31 ms apart.
bool IsDeadlineDue(uint32_t now, uint32_t deadline);
// Clears diagnostics and starts an unarmed session at the configured initial
// sequence.
void InitSender(Sender* sender);
// Returns whether TX, ACK waiting or retry backoff is in progress.
bool IsSenderActive(const Sender* sender);
// Arms a session when idle; preserves DATA start spacing across session
// changes. Re-arming the same session is a no-op, including its stop/exhaustion
// latches.
bool ArmSender(Sender* sender, uint32_t session);
// Copies length payload bytes into state; rejects null payload, oversize or
// invalid RTO. Requires an armed, reusable session; timestamps/RTO are
// milliseconds.
bool RequestTransmission(Sender* sender, const uint8_t* payload, size_t length,
                         uint32_t now_ms, uint32_t ack_timeout_ms);
// Records radio completion and RX readiness, or terminates a failed TX/rearm.
void HandleTxCompletion(Sender* sender, uint32_t now_ms, bool success);
// Accepts only matching peer/session/sequence control before the absolute
// deadline. Null or invalid frames are ignored. Advances sequence only after a
// valid ACK.
void HandleControlFrame(Sender* sender, const Frame* frame, uint32_t now_ms);
// Advances bounded retry/deadline handling; the adapter performs actual radio
// I/O.
void PollSender(Sender* sender, uint32_t now_ms);
// Latches stop for future requests; the current transaction may still complete.
void StopSender(Sender* sender);
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_SENDER_H_
