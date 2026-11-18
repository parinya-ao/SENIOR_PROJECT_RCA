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

// Resets command parsing and its one-shot latch; null is ignored.
void ControlInputInit(ControlInput* input, char command);
// Consumes one byte and returns true once after four nonzero session hex
// digits. Null input/session fails; session is overwritten only on success. A
// gap over the configured inter-byte timeout cancels a partial command.
// Unsigned elapsed arithmetic handles clock rollover.
bool ControlInputFeed(ControlInput* input, char value, uint32_t now_ms,
                      uint16_t* session);
}  // namespace ssot
#endif  // SENIOR_PROJECT_RCA_SRC_SSOT_CONTROL_INPUT_H_
