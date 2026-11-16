// No repository-wide license is declared; existing rights are unchanged.

// Collects the legacy command and four-hex-digit session without hardware
// access.

#ifndef SENIOR_PROJECT_RCA_SRC_SSOT_CONTROL_INPUT_H_
#define SENIOR_PROJECT_RCA_SRC_SSOT_CONTROL_INPUT_H_
#include <stdint.h>
namespace ssot {
// Accumulates a command plus four uppercase hex digits, then latches until
// reinitialized.
struct ControlInput {
  char command;
  uint8_t digits;
  uint16_t value;
  uint32_t last_ms;
  bool reading;
  bool triggered;
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
