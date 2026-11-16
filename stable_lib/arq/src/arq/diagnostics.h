// No repository-wide license is declared; existing rights are unchanged.

// Provides the foreground ARQ application's bounded diagnostic queue.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_DIAGNOSTICS_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_DIAGNOSTICS_H_
#include <stddef.h>
#include <stdint.h>

#include "application_config.h"
#include "frame.h"
namespace arq {
namespace diagnostics {
// Borrows live transaction fields; referenced state must outlive each logging
// call. Keeping references avoids copying an AVR aggregate at every event call
// site.
struct EventContext {
  const uint32_t& session;
  const uint16_t& sequence;
  const uint8_t& attempts;
};
// Queues one scalar observation. Names must remain valid until this call
// returns.
void RecordEvent(const EventContext& context, const char* name, int16_t error,
                 uint32_t value);
// Queues exact bytes with observed radio metrics; retains no pointers.
void RecordFrame(const EventContext& context, const char* name,
                 const uint8_t* bytes, size_t length, int16_t rssi,
                 int16_t snr);
// Queues rejected decoded fields without changing protocol state.
void RecordDiscard(const EventContext& context, const char* name,
                   const arq::Frame* frame, uint8_t reason);

inline constexpr size_t kLineCapacity = application_config::logging::kSlotBytes;
// Reserves a line or returns nullptr and counts a dropped event if full.
// Immediately write a nonempty NUL-terminated line within kLineCapacity bytes.
// The pointer expires when flushed. Foreground-only; never call from an ISR.
char* AcquireLine();
// Writes at most one byte when UPDI is connected and its mailbox is free.
// A missing reader or full mailbox leaves all pending data untouched.
void FlushByte();
// Returns queued line count, including a partially flushed line.
uint8_t PendingLineCount();
// Returns the cumulative number of events dropped by a full queue.
uint32_t OverflowCount();
}  // namespace diagnostics
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_DIAGNOSTICS_H_
