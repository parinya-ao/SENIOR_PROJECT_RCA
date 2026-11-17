// Parses the existing bench grammar without changing radio or protocol state.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_COMMANDS_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_COMMANDS_H_

#include "config.h"
#include "frame.h"

namespace arq {
enum class CommandKind { kStatus, kStop, kArm, kSend, kFault };

// Holds one parsed action and copied payload. Only fields selected by kind are
// meaningful; parsing never retains pointers into the caller's text.
struct Command {
  CommandKind kind;
  uint32_t session;
  uint16_t stride;
  uint16_t budget;
  uint8_t payload_length;
  uint8_t payload[kMaxPayloadBytes];
};

// Parses one NUL-terminated line using the current role's command grammar.
// Both pointers must be non-null. Invalid text leaves command unspecified.
// Does not validate application readiness, session state or radio ownership.
bool ParseCommand(const char* text, Command* command);

enum class InputResult { kPending, kComplete, kOverflow };

// Owns one fixed command line in foreground context; no heap or ISR access.
// Consume text() immediately after kComplete, before feeding the next byte.
class CommandInput {
 public:
  // Ignores CR; newline completes a line or reports overflow, then resets
  // input. Overflow discards the entire line until newline, allowing clean
  // recovery.
  InputResult Feed(char value);
  const char* text() const { return buffer_; }

 private:
  char buffer_[application_config::commands::kCapacity]{};
  uint8_t length_ = 0;
  bool overflow_ = false;
};
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_COMMANDS_H_
