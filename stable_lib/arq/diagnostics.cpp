// Formats and queues bounded ARQ event records for foreground UPDI logging.
#include "arq_diagnostics.h"

// DxCore headers contain implicit conversions; keep their diagnostics separate
// from strict checks on this module. AVR GCC cannot mark Arduino as a system
// include because that changes the linkage of its C++ overloads.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wconversion"
#pragma GCC diagnostic ignored "-Wsign-conversion"
#include <Arduino.h>
#pragma GCC diagnostic pop
#include <stdio.h>
#include <updi_uart.h>
namespace arq {
namespace diagnostics {
namespace {
// One queue belongs to this application, rather than one copy per includer.
char lines[application_config::logging::kSlotCount][kLineCapacity];
// Foreground-only indices; offset counts bytes already sent from head.
uint8_t head, tail, count, offset;
// Diagnostic loss never blocks radio progress or extends protocol deadlines.
uint32_t overflow;
}  // namespace
char* AcquireLine() {
  if (count == application_config::logging::kSlotCount) {
    ++overflow;
    return nullptr;
  }
  char* output = lines[tail];
  tail = static_cast<uint8_t>((tail + 1U) %
                              application_config::logging::kSlotCount);
  ++count;
  return output;
}
void FlushByte() {
  // The UPDI ready byte is a mailbox; never wait for a disconnected reader.
  if (!count || !updi_uart_enabled() || _SFR_MEM8(0x0f19)) return;
  _SFR_MEM8(0x0f18) = static_cast<uint8_t>(lines[head][offset++]);
  if (!lines[head][offset]) {
    offset = 0;
    head = static_cast<uint8_t>((head + 1U) %
                                application_config::logging::kSlotCount);
    --count;
  }
}
// Queues one bounded scalar event; log backpressure drops diagnostics, never
// radio progress.
void RecordEvent(const EventContext& context, const char* name, int16_t rc,
                 uint32_t value) {
  char* out = arq::diagnostics::AcquireLine();
  if (!out) return;
  snprintf(out, arq::diagnostics::kLineCapacity,
           "A t=%lu e=%s s=%08lX q=%u a=%u rc=%d v=%lu\n",
           static_cast<unsigned long>(millis()), name,
           static_cast<unsigned long>(context.session), context.sequence,
           context.attempts, rc, static_cast<unsigned long>(value));
}
// Queues frame bytes for host-side verification; bytes must span length
// readable bytes.
void RecordFrame(const EventContext& context, const char* name,
                 const uint8_t* bytes, size_t length, int16_t rssi,
                 int16_t snr) {
  char* out = arq::diagnostics::AcquireLine();
  if (!out) return;
  int n = snprintf(out, arq::diagnostics::kLineCapacity,
                   "A t=%lu e=%s s=%08lX q=%u rssi=%d snr=%d bytes=",
                   static_cast<unsigned long>(millis()), name,
                   static_cast<unsigned long>(context.session),
                   context.sequence, rssi, snr);
  if (n < 0 || static_cast<size_t>(n) >= kLineCapacity - 1) {
    out[kLineCapacity - 2] = '\n';
    out[kLineCapacity - 1] = 0;
    return;
  }
  static constexpr char kHexDigits[] = "0123456789ABCDEF";
  for (size_t i = 0;
       i < length && n < static_cast<int>(arq::diagnostics::kLineCapacity) - 4;
       i++) {
    out[n++] = kHexDigits[static_cast<unsigned>(bytes[i]) >> 4U];
    out[n++] = kHexDigits[static_cast<unsigned>(bytes[i]) & 15U];
  }
  out[n++] = '\n';
  out[n] = 0;
}

// Records a rejected decoded frame without changing transaction state.
void RecordDiscard(const EventContext& context, const char* name,
                   const arq::Frame* f, uint8_t reason) {
  char* out = arq::diagnostics::AcquireLine();
  if (!out) return;
  snprintf(
      out, arq::diagnostics::kLineCapacity,
      "A t=%lu e=%s s=%08lX q=%u rc=%u src=%u dst=%u rs=%08lX rq=%u type=%u\n",
      static_cast<unsigned long>(millis()), name,
      static_cast<unsigned long>(context.session), context.sequence, reason,
      f->src, f->dst, static_cast<unsigned long>(f->session), f->sequence,
      f->type);
}

uint8_t PendingLineCount() { return count; }
uint32_t OverflowCount() { return overflow; }
}  // namespace diagnostics
}  // namespace arq
