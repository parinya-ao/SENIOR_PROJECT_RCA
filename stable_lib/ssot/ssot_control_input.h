// Collects the legacy command and four-hex-digit session without hardware
// access.

#ifndef SENIOR_PROJECT_RCA_SRC_SSOT_CONTROL_INPUT_H_
#define SENIOR_PROJECT_RCA_SRC_SSOT_CONTROL_INPUT_H_
#include <stdint.h>
namespace ssot {
/// Accumulates a command plus four uppercase hex digits, then latches until
/// reinitialized.
struct ControlInput {
  char command;      ///< Command byte to start parsing.
  uint8_t digits;    ///< Hex digits collected so far.
  uint16_t value;    ///< Accumulated campaign value.
  uint32_t last_ms;  ///< Time of the last accepted byte.
  bool reading;      ///< Whether a command is in progress.
  bool triggered;    ///< Whether this input has already emitted a command.
};

/// @brief Resets command parsing and its one-shot latch.
/// @param input Parser state to reset; null is ignored.
/// @param command Byte that begins this command.
void ControlInputInit(ControlInput* input, char command);
/// @brief Consumes one byte of the legacy session command.
/// @param input Caller-owned parser state.
/// @param value Byte received from the command stream.
/// @param now_ms Current wrapping millisecond counter.
/// @param session Receives the session only when parsing completes.
/// @return True once after four nonzero hexadecimal digits; false for partial,
///   expired, or invalid input. Unsigned elapsed-time arithmetic handles wrap.
bool ControlInputFeed(ControlInput* input, char value, uint32_t now_ms,
                      uint16_t* session);
}  // namespace ssot
#endif  // SENIOR_PROJECT_RCA_SRC_SSOT_CONTROL_INPUT_H_
