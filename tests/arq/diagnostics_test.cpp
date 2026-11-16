// No repository-wide license is declared; existing rights are unchanged.
// Checks real queue behavior against the UPDI mailbox stub.
#include "../../src/arq/diagnostics.cpp"

#include <assert.h>
#include <string.h>

int main() {
  using arq::diagnostics::AcquireLine;
  using arq::diagnostics::FlushByte;
  using arq::diagnostics::OverflowCount;
  using arq::diagnostics::PendingLineCount;
  for (unsigned i = 0; i < application_config::logging::kSlotCount; ++i) {
    char* line = AcquireLine();
    assert(line);
    strcpy(line, "AB\n");
  }
  assert(!AcquireLine() && OverflowCount() == 1);
  assert(PendingLineCount() == application_config::logging::kSlotCount);
  monitor = false;
  FlushByte();
  assert(registers[0] == 0);
  monitor = true;
  registers[1] = 1;
  FlushByte();
  assert(registers[0] == 0);
  registers[1] = 0;
  const char expected[] = "AB\n";
  for (char value : expected) {
    if (!value) break;
    FlushByte();
    assert(registers[0] == value);
  }
  assert(PendingLineCount() == application_config::logging::kSlotCount - 1);
  char* recovered = AcquireLine();
  assert(recovered);
  strcpy(recovered, "C\n");
  while (PendingLineCount()) FlushByte();
  // Long event names must not turn snprintf's required length into an index.
  char name[256];
  memset(name, 'N', sizeof(name) - 1);
  name[sizeof(name) - 1] = 0;
  arq::diagnostics::RecordFrame({1, 2, 3}, name, nullptr, 0, 0, 0);
  assert(PendingLineCount() == 1);
  while (PendingLineCount()) FlushByte();
  return 0;
}
