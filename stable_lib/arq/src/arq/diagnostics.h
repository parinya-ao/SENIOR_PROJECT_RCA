/// @file
/// Provides the foreground ARQ application's bounded diagnostic queue.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_DIAGNOSTICS_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_DIAGNOSTICS_H_
#include <stddef.h>
#include <stdint.h>

#include "application_config.h"
#include "frame.h"
namespace arq {
namespace diagnostics {
/// Borrows live transaction fields; referenced state must outlive each logging
/// call. Keeping references avoids copying an AVR aggregate at every event call
/// site.
struct EventContext {
  /// Borrowed active or last session ID.
  const uint32_t& session;
  /// Borrowed active or observed sequence.
  const uint16_t& sequence;
  /// Borrowed number of attempted transmissions.
  const uint8_t& attempts;
};
/// Queues one scalar observation. Names must remain valid until this call
/// returns.
/// @param context Borrowed live transaction fields.
/// @param name NUL-terminated event identifier.
/// @param error Logged operation status.
/// @param value Event-specific data.
void RecordEvent(const EventContext& context, const char* name, int16_t error,
                 uint32_t value);
/// Queues frame bytes that fit the line with observed radio metrics. Retains
/// no pointers and drops the event if the queue is full.
/// @param context Borrowed live transaction fields.
/// @param name NUL-terminated event identifier.
/// @param bytes Readable bytes for the duration of this call.
/// @param length Number of readable bytes.
/// @param rssi Observed signal strength, or zero when absent.
/// @param snr Observed signal-to-noise ratio, or zero when absent.
void RecordFrame(const EventContext& context, const char* name,
                 const uint8_t* bytes, size_t length, int16_t rssi,
                 int16_t snr);
/// Queues rejected decoded fields without changing protocol state.
/// @param context Borrowed live transaction fields.
/// @param name NUL-terminated event identifier.
/// @param frame Borrowed decoded fields used during the call.
/// @param reason Diagnostic discard code.
void RecordDiscard(const EventContext& context, const char* name,
                   const arq::Frame* frame, uint8_t reason);

/// Total bytes in a queue slot, including the NUL terminator.
inline constexpr size_t kLineCapacity = application_config::logging::kSlotBytes;
/// Reserves a line or returns nullptr and counts a dropped event if full.
/// Immediately write a nonempty NUL-terminated line within kLineCapacity bytes.
/// The pointer expires when flushed. Foreground-only; never call from an ISR.
/// @return Writable line slot, or null if the queue is full.
char* AcquireLine();
/// Writes at most one byte when UPDI is connected and its mailbox is free.
/// A missing reader or full mailbox leaves all pending data untouched.
void FlushByte();
/// Returns queued line count, including a partially flushed line.
/// @return Number of queued lines, including a partially flushed line.
uint8_t PendingLineCount();
/// Returns the cumulative number of events dropped by a full queue.
/// @return Cumulative number of events dropped by a full queue.
uint32_t OverflowCount();
}  // namespace diagnostics
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_DIAGNOSTICS_H_
