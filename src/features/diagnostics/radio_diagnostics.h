#ifndef SENIOR_PROJECT_RCA_SRC_FEATURES_DIAGNOSTICS_RADIO_DIAGNOSTICS_H_
#define SENIOR_PROJECT_RCA_SRC_FEATURES_DIAGNOSTICS_RADIO_DIAGNOSTICS_H_

#include <application_config.h>
#include <stddef.h>
#include <stdint.h>

// Stores bounded, allocation-free radio observations for foreground logging.
namespace radio_diagnostics {

// Scalar event record. `name` must refer to storage that outlives the queued
// record; the production caller uses string literals.
struct Event {
  const char* name;
  uint32_t time_ms;
  int16_t error;
  uint8_t type;
  uint8_t sequence;
  uint16_t campaign_id;
};

// Caller-owned bounded FIFO for foreground radio observations. It performs no
// allocation and is not safe for concurrent or ISR access.
class EventQueue {
 public:
  static constexpr uint8_t kCapacity = application_config::logging::kSlotCount;

  // Copies one event. Returns false when full and saturates overflow_count().
  bool Push(const Event& event);

  // Removes the oldest event into `event`. Returns false for a null output or
  // an empty queue without changing the output or queue state.
  bool Pop(Event* event);

  // Returns the number of queued events and saturating dropped-event count.
  uint8_t size() const { return count_; }
  uint16_t overflow_count() const { return overflow_count_; }

 private:
  static_assert(kCapacity > 0, "diagnostic queue capacity must be nonzero");

  Event events_[kCapacity] = {};
  uint8_t head_ = 0;
  uint8_t count_ = 0;
  uint16_t overflow_count_ = 0;
};

}  // namespace radio_diagnostics

#endif  // SENIOR_PROJECT_RCA_SRC_FEATURES_DIAGNOSTICS_RADIO_DIAGNOSTICS_H_
