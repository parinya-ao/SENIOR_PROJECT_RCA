// Shared ARQ bench observation and formatting, independent of transaction
// policy.
#include "arq_bench.h"

#include <Arduino.h>
#include <stdio.h>

#include "arq_config.h"
#include "shared/radio/arq_radio.h"

namespace arq::app {

// Captures relevant SPI readback before later mode transitions erase diagnostic
// evidence.
void RecordRadioRegisters(const diagnostics::EventContext& context,
                          const char* name) {
  static const uint8_t addresses[] = {
      0x01, 0x06, 0x07, 0x08, 0x09, 0x4d, 0x1d, 0x1e, 0x26, 0x39, 0x33, 0x3b,
      0x12, 0x13, 0x10, 0x1b, 0x40, 0x11, 0x18, 0x31, 0x42, 0x20, 0x21, 0x41};
  uint8_t values[sizeof addresses];
  for (size_t i = 0; i < sizeof addresses; ++i)
    values[i] = ReadRadioRegister(addresses[i]);
  arq::diagnostics::RecordFrame(context, name, values, sizeof values, 0, 0);
}
// Captures receive IRQ/FIFO state for the first failing boundary.
void RecordReceiveDiagnostics(const diagnostics::EventContext& context,
                              const char* name, uint16_t flags) {
  // Snapshot band counters before startReceive resets their observation window.
  uint8_t values[6] = {static_cast<uint8_t>(flags >> 8),
                       static_cast<uint8_t>(flags),
                       0,
                       0,
                       0,
                       0};
  for (uint8_t i = 0; i < 4; ++i) values[2 + i] = ReadRadioRegister(0x14 + i);
  arq::diagnostics::RecordFrame(context, name, values, sizeof values, 0, 0);
}
// Keeps result and RTT fields in their established STATUS order.
static void RecordStatusTiming(const diagnostics::EventContext& context,
                               const BenchStatus& status, uint8_t step) {
  if (step == 5) {
    diagnostics::RecordEvent(context, "RESULT", status.result, status.state);
    return;
  }
  static const char* const fields[] = {"RTT_LAST", "RTT_MIN", "RTT_MAX",
                                       "RTT_COUNT"};
  const uint8_t index = step - 6;
  diagnostics::RecordEvent(context, fields[index], 0, status.rtt[index]);
}

// Emits counters for both directions using the same wire-facing log format.
static void RecordStatusCounters(const diagnostics::EventContext& context,
                                 const BenchStatus& status) {
  char* out = arq::diagnostics::AcquireLine();
  if (out)
    snprintf(out, arq::diagnostics::kLineCapacity,
             "A t=%lu e=STATUS s=%08lX app=%lu dup=%lu gen=%lu sup=%lu "
             "att=%lu done=%lu crc=%lu overflow=%lu ready=%u\n",
             static_cast<unsigned long>(millis()),
             static_cast<unsigned long>(context.session),
             static_cast<unsigned long>(status.deliveries),
             static_cast<unsigned long>(status.duplicates),
             static_cast<unsigned long>(status.generated),
             static_cast<unsigned long>(status.suppressed),
             static_cast<unsigned long>(status.attempted),
             static_cast<unsigned long>(status.completed),
             static_cast<unsigned long>(status.crc_errors),
             static_cast<unsigned long>(arq::diagnostics::OverflowCount()),
             status.ready);
}
// Emits at most one pending status item per call so logging cannot monopolize
// loop.
void FlushBenchStatus(uint8_t& next, const diagnostics::EventContext& context,
                      const BenchStatus& status) {
  // Yield between status lines so an RX/response burst retains the bounded
  // logger.
  if (!next || arq::diagnostics::PendingLineCount()) return;
  const uint8_t step = next++;
  switch (step) {
    case 1:
      arq::diagnostics::RecordEvent(context, "BOOT", status.startup,
                                    status.reset_flags);
      break;
    case 2:
#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC)
      arq::diagnostics::RecordEvent(context, "RADIO_ONLY", status.startup, 1);
#endif
      break;
    case 3: {
      char* identity = arq::diagnostics::AcquireLine();
      if (identity)
        snprintf(identity, arq::diagnostics::kLineCapacity,
                 "A t=%lu e=IDENTITY s=%08lX build=%s config=%s\n",
                 static_cast<unsigned long>(millis()),
                 static_cast<unsigned long>(context.session), LORA_BUILD_ID,
                 ARQ_CONFIG_HASH);
      break;
    }
    case 4:
      RecordStatusCounters(context, status);
      break;
    case 5:
    case 6:
    case 7:
    case 8:
    case 9:
      RecordStatusTiming(context, status, step);
      break;
    case 10:
      arq::diagnostics::RecordEvent(context, "RX_DONE_COUNT", 0,
                                    status.rx_done);
      break;
    case 11:
      arq::diagnostics::RecordEvent(context, "DECODE_ERRORS", 0,
                                    status.decode_errors);
      break;
    case 12: {
      arq::diagnostics::RecordEvent(context, "CONTROL_REJECTS", 0,
                                    status.control_rejects);
      break;
    }
    case 13:
      // Read-only register evidence separates RX mode/configuration from RF
      // path failure.
      if (status.ready) RecordRadioRegisters(context, "REG");
      break;
    case 14:
      arq::diagnostics::RecordEvent(context, "STATUS_END", 0,
                                    arq::diagnostics::OverflowCount());
      next = 0;
      break;
    default:
      break;
  }
}

}  // namespace arq::app
