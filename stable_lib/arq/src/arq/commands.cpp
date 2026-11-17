// Parses the bounded ARQ serial command grammar into caller-owned state.
#include "commands.h"

#include <stdio.h>
#include <string.h>

namespace arq {
namespace {
// Returns one hexadecimal nibble or -1 for an invalid character.
int DecodeHexDigit(char value) {
  if (value >= '0' && value <= '9') return value - '0';
  if (value >= 'A' && value <= 'F') return value - 'A' + 10;
  if (value >= 'a' && value <= 'f') return value - 'a' + 10;
  return -1;
}
}  // namespace

bool ParseCommand(const char* text, Command* command) {
  if (!strcmp(text, "STATUS")) {
    command->kind = CommandKind::kStatus;
    return true;
  }
  if (!strcmp(text, "X")) {
    command->kind = CommandKind::kStop;
    return true;
  }
  if (!strncmp(text, "ARM ", 4) && strlen(text) == 12) {
    command->session = 0;
    for (uint8_t i = 4; i < 12; ++i) {
      const int digit = DecodeHexDigit(text[i]);
      if (digit < 0) return false;
      command->session =
          (command->session << 4U) | static_cast<uint32_t>(digit);
    }
    command->kind = CommandKind::kArm;
    return true;
  }
#if defined(ARQ_ROLE_SENDER)
  if (!strncmp(text, "SEND ", 5)) {
    const size_t hex_length = strlen(text + 5);
    if (hex_length > 2 * kMaxPayloadBytes || (hex_length & 1U)) return false;
    for (size_t i = 0; i < hex_length; i += 2) {
      const int high = DecodeHexDigit(text[5 + i]);
      const int low = DecodeHexDigit(text[6 + i]);
      if (high < 0 || low < 0) return false;
      command->payload[i / 2] = static_cast<uint8_t>(
          (static_cast<unsigned>(high) << 4U) | static_cast<unsigned>(low));
    }
    command->payload_length = static_cast<uint8_t>(hex_length / 2);
    command->kind = CommandKind::kSend;
    return true;
  }
#elif defined(ARQ_TEST_MODE)
  if (!strncmp(text, "FAULT ", 6)) {
    unsigned stride, budget;
    char extra;
    if (sscanf(text + 6, "%u %u %c", &stride, &budget, &extra) != 2 ||
        stride > application_config::commands::kFaultLimit ||
        budget > application_config::commands::kFaultLimit ||
        (budget && !stride))
      return false;
    command->stride = static_cast<uint16_t>(stride);
    command->budget = static_cast<uint16_t>(budget);
    command->kind = CommandKind::kFault;
    return true;
  }
#endif
  return false;
}

InputResult CommandInput::Feed(char value) {
  if (value == '\r') return InputResult::kPending;
  if (value == '\n') {
    buffer_[length_] = 0;
    const InputResult result =
        overflow_ ? InputResult::kOverflow : InputResult::kComplete;
    length_ = 0;
    overflow_ = false;
    return result;
  }
  if (length_ >= sizeof(buffer_) - 1) {
    overflow_ = true;
  } else {
    buffer_[length_++] = value;
  }
  return InputResult::kPending;
}
}  // namespace arq
