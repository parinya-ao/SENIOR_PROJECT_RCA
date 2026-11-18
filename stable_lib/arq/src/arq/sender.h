/// @file
/// Owns caller-held ARQ transaction and deadline state; foreground access only.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_SENDER_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_SENDER_H_
#include "codec.h"
#include "config.h"
namespace arq {
/// Keeps the original native int representation; states never become wire
/// bytes.
enum class SenderState {
  kIdle,
  kTransmitting,
  kWaitingAck,
  kBackoff,
  kDelivered,
  kFailed
};
/// Distinguishes terminal failure reasons from a pending or delivered
/// transaction.
enum class Result {
  kPending,
  kOk,
  kRejected,
  kProtocolError,
  kTimeoutExhausted,
  kRadioError
};
/// Owns one immutable in-flight frame and bounded retry state, without heap
/// allocation. All operations require a non-null initialized state in the
/// foreground context. The radio adapter calls TX completion only after cleanup
/// and successful RX arming.
struct Sender {
  /// Current sender phase.
  SenderState state;
  /// Most recent transaction outcome.
  Result result;
  /// A session is bound.
  bool armed;
  /// New DATA requests are disabled.
  bool stopped;
  /// Distinguishes a real start at timestamp zero from a never-started sender.
  bool has_start;
  /// Prevents session/sequence reuse after failure or full sequence wraparound.
  bool used_up;
  /// Bound wire session ID.
  uint32_t session;
  /// All timestamps and intervals below are milliseconds, modulo uint32_t.
  /// Most recent DATA start.
  uint32_t last_start;
  /// Earliest next transition eligible for retry.
  uint32_t retry_at;
  /// Absolute deadline for the transaction.
  uint32_t terminal_at;
  /// Current ACK window, doubled after each retry.
  uint32_t interval;
  /// Time associated with the most recent TxDone.
  uint32_t tx_done;
  /// RTT samples are valid only for successful transactions without
  /// retransmission.
  /// Number of accepted, unambiguous RTT samples.
  uint32_t rtt_count;
  /// Most recent RTT sample in milliseconds.
  uint32_t rtt_last;
  /// Minimum RTT in the bound session once a sample exists.
  uint32_t rtt_min;
  /// Maximum RTT in the bound session once a sample exists.
  uint32_t rtt_max;
  /// Sequence for the current or next DATA.
  uint16_t sequence;
  /// Number of DATA attempts in the transaction.
  uint8_t attempts;
  /// Owned DATA frame reused for each attempt.
  Frame frame;
};
/// Tests a wraparound deadline; now/deadline must be less than 2^31 ms apart.
/// @param now Current tick in milliseconds.
/// @param deadline Absolute tick in the same clock domain.
/// @return True when now equals or follows deadline modulo uint32_t.
bool IsDeadlineDue(uint32_t now, uint32_t deadline);
/// Clears diagnostics and starts an unarmed session at the configured initial
/// sequence.
/// @param sender Non-null caller-owned state to reset.
void InitSender(Sender* sender);
/// Returns whether TX, ACK waiting or retry backoff is in progress.
/// @param sender Non-null initialized sender state.
/// @return True while an attempt or response window is outstanding.
bool IsSenderActive(const Sender* sender);
/// Arms a session when idle; preserves DATA start spacing across session
/// changes. Re-arming the same session is a no-op, including its
/// stop/exhaustion latches.
/// @param sender Non-null initialized state.
/// @param session Wire session to bind.
/// @return True if already bound to session or successfully armed.
bool ArmSender(Sender* sender, uint32_t session);
/// Copies length payload bytes into state; rejects null payload, oversize or
/// invalid RTO. Requires an armed, reusable session; timestamps/RTO are
/// milliseconds.
/// @param sender Non-null initialized state.
/// @param payload Borrowed, readable payload bytes.
/// @param length Number of bytes copied from payload.
/// @param now_ms Current modulo millisecond tick.
/// @param ack_timeout_ms Initial ACK window within configured bounds.
/// @return True if the transaction was scheduled.
bool RequestTransmission(Sender* sender, const uint8_t* payload, size_t length,
                         uint32_t now_ms, uint32_t ack_timeout_ms);
/// Records radio completion and RX readiness, or terminates a failed TX/rearm.
/// @param sender Non-null initialized state.
/// @param now_ms Millisecond tick at completion or after restoring RX.
/// @param success True after TX completion, cleanup and RX rearm.
void HandleTxCompletion(Sender* sender, uint32_t now_ms, bool success);
/// Accepts only matching peer/session/sequence control before the absolute
/// deadline. Null or invalid frames are ignored. Advances sequence only after a
/// valid ACK.
/// @param sender Non-null initialized state.
/// @param frame Borrowed decoded frame, or null.
/// @param now_ms Millisecond tick of handling the frame.
void HandleControlFrame(Sender* sender, const Frame* frame, uint32_t now_ms);
/// Advances bounded retry/deadline handling; the adapter performs actual radio
/// I/O.
/// @param sender Non-null initialized state.
/// @param now_ms Current modulo millisecond tick.
void PollSender(Sender* sender, uint32_t now_ms);
/// Latches stop for future requests; the current transaction may still
/// complete.
/// @param sender Non-null initialized state.
void StopSender(Sender* sender);
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_SENDER_H_
