// Tests accepted, rejected, and truncated ARQ serial command lines.
#include <assert.h>
#include <string.h>

#include "arq_commands.h"

int main() {
  arq::Command command{};
  assert(arq::ParseCommand("ARM 1234aBcD", &command));
  assert(command.kind == arq::CommandKind::kArm);
  assert(command.session == 0x1234abcd);
  assert(!arq::ParseCommand("ARM 1234567", &command));
  assert(!arq::ParseCommand("ARM 1234567Z", &command));
  assert(arq::ParseCommand("STATUS", &command));
  assert(command.kind == arq::CommandKind::kStatus);
  assert(arq::ParseCommand("X", &command));
  assert(command.kind == arq::CommandKind::kStop);
  assert(!arq::ParseCommand("STATUS ", &command));
#if defined(ARQ_ROLE_SENDER)
  assert(arq::ParseCommand("SEND 00FF61", &command));
  assert(command.payload_length == 3 && command.payload[0] == 0 &&
         command.payload[1] == 255 && command.payload[2] == 'a');
  assert(arq::ParseCommand("SEND ", &command));
  assert(command.payload_length == 0);
  assert(!arq::ParseCommand("SEND 0", &command));
  assert(!arq::ParseCommand("SEND gg", &command));
  char text[5 + 2 * arq::kMaxPayloadBytes + 3];
  strcpy(text, "SEND ");
  memset(text + 5, 'A', 2 * arq::kMaxPayloadBytes + 2);
  text[5 + 2 * arq::kMaxPayloadBytes] = 0;
  assert(arq::ParseCommand(text, &command));
  assert(command.payload_length == arq::kMaxPayloadBytes);
  text[5 + 2 * arq::kMaxPayloadBytes] = 'A';
  text[sizeof(text) - 1] = 0;
  assert(!arq::ParseCommand(text, &command));
  assert(!arq::ParseCommand("FAULT 1 1", &command));
#else
  assert(arq::ParseCommand("FAULT 10 2", &command));
  assert(command.stride == 10 && command.budget == 2);
  assert(!arq::ParseCommand("FAULT 0 1", &command));
  assert(!arq::ParseCommand("FAULT 101 1", &command));
  assert(!arq::ParseCommand("FAULT 4294967297 1", &command));
  assert(!arq::ParseCommand("FAULT 65537 1", &command));
  assert(!arq::ParseCommand("FAULT -4294967295 1", &command));
  assert(!arq::ParseCommand("FAULT 1 1 extra", &command));
  assert(!arq::ParseCommand("SEND 00", &command));
#endif
  arq::CommandInput input;
  assert(input.Feed('\r') == arq::InputResult::kPending);
  for (unsigned i = 0; i < application_config::commands::kCapacity; ++i) {
    assert(input.Feed('x') == arq::InputResult::kPending);
  }
  assert(input.Feed('\n') == arq::InputResult::kOverflow);
  assert(input.Feed('X') == arq::InputResult::kPending);
  assert(input.Feed('\n') == arq::InputResult::kComplete);
  assert(!strcmp(input.text(), "X"));
  return 0;
}
