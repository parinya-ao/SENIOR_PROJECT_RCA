/// @file
/// Parses the existing bench grammar without changing radio or protocol state.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_COMMANDS_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_COMMANDS_H_

#include "arq_config.h"
#include "arq_frame.h"

namespace arq {
/// Actions accepted by the role-specific bench parser.
enum class CommandKind { kStatus, kStop, kArm, kSend, kFault };

/// Holds one parsed action and copied payload. Only fields selected by kind are
/// meaningful; parsing never retains pointers into the caller's text.
struct Command {
  /// Action determining which of the other fields are valid.
  CommandKind kind;
  /// Requested session ID for ARM.
  uint32_t session;
  /// Suppress every stride-th eligible response for FAULT.
  uint16_t stride;
  /// Maximum number of suppressed responses for FAULT.
  uint16_t budget;
  /// Number of decoded SEND bytes.
  uint8_t payload_length;
  /// Owned decoded SEND bytes.
  uint8_t payload[kMaxPayloadBytes];
};

/// Parses one NUL-terminated line using the current role's command grammar.
/// Both pointers must be non-null. Invalid text leaves command unspecified.
/// Does not validate application readiness, session state or radio ownership.
/// @param text Borrowed NUL-terminated command line.
/// @param command Caller-owned output, unspecified after failure.
/// @return True when text matches the current role grammar.
bool ParseCommand(const char* text, Command* command);

/// Result of feeding one byte to the line buffer.
enum class InputResult { kPending, kComplete, kOverflow };

/// Owns one fixed command line in foreground context; no heap or ISR access.
/// Consume text() immediately after kComplete, before feeding the next byte.
class CommandInput {
 public:
  /// Ignores CR; newline completes a line or reports overflow, then resets
  /// input. Overflow discards the entire line until newline, allowing clean
  /// recovery.
  /// @param value Next byte of the foreground command stream.
  /// @return Pending, completed line, or discarded overlong line.
  InputResult Feed(char value);
  /// @return Borrowed NUL-terminated line after kComplete, valid until Feed.
  const char* text() const { return buffer_; }

 private:
  char buffer_[application_config::commands::kCapacity]{};
  uint8_t length_ = 0;
  bool overflow_ = false;
};
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_COMMANDS_H_
