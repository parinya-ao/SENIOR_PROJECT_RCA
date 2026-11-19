// Implements the fixed-buffer parser for legacy command/session serial input.
#include "ssot_control_input.h"

#include "application_config.h"
void ssot::ControlInputInit(ssot::ControlInput* input, char command) {
  if (input != nullptr) {
    *input = ssot::ControlInput{command, 0U, 0U, 0U, false, false};
  }
}

bool ssot::ControlInputFeed(ssot::ControlInput* input, char value,
                            uint32_t now_ms, uint16_t* session) {
  if (input == nullptr || input->triggered || session == nullptr) {
    return false;
  }
  // Unsigned elapsed time preserves the inter-byte timeout across timer
  // rollover.
  if (input->reading && now_ms - input->last_ms >
                            application_config::commands::kInterByteTimeoutMs) {
    input->reading = false;
  }
  if (value == input->command) {
    input->reading = true;
    input->digits = 0U;
    input->value = 0U;
    input->last_ms = now_ms;
    return false;
  }
  if (!input->reading) {
    return false;
  }

  uint8_t digit;
  if (value >= '0' && value <= '9') {
    digit = static_cast<uint8_t>(value - '0');
  } else if (value >= 'A' && value <= 'F') {
    digit = static_cast<uint8_t>(value - 'A' + 10);
  } else {
    input->reading = false;
    return false;
  }

  input->value = static_cast<uint16_t>(
      (static_cast<uint32_t>(input->value) << 4U) | digit);
  input->last_ms = now_ms;
  ++input->digits;
  if (input->digits != 4U) {
    return false;
  }
  input->reading = false;
  if (input->value == 0U) {
    return false;
  }
  *session = input->value;
  input->triggered = true;
  return true;
}
