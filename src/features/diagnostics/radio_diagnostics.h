#ifndef SENIOR_PROJECT_RCA_SRC_FEATURES_DIAGNOSTICS_RADIO_DIAGNOSTICS_H_
#define SENIOR_PROJECT_RCA_SRC_FEATURES_DIAGNOSTICS_RADIO_DIAGNOSTICS_H_

#include <application_config.h>
#include <stddef.h>
#include <stdint.h>

// Stores bounded, allocation-free radio observations for foreground logging.
namespace radio_diagnostics {

/// Scalar event record. `name` must refer to storage that outlives the queued
/// record; the production caller uses string literals.
struct Event {
  const char* name;      ///< Stable event marker.
  uint32_t time_ms;      ///< Capture time on the local MCU clock.
  int16_t error;         ///< Driver or transaction status.
  uint8_t type;          ///< Wire packet type, if available.
  uint8_t sequence;      ///< Wire sequence, if available.
  uint16_t campaign_id;  ///< Wire campaign, if available.
};

/// Caller-owned bounded FIFO for foreground radio observations. It performs no
/// allocation and is not safe for concurrent or ISR access.
class EventQueue {
 public:
  /// Maximum queued events.
  static constexpr uint8_t kCapacity = application_config::logging::kSlotCount;

  /// Copies one event or increments the overflow counter up to its limit.
  /// @param event Observation to enqueue.
  /// @return True if the event was stored.
  bool Push(const Event& event);

  /// Removes the oldest event.
  /// @param event Output event. A null pointer leaves the queue unchanged.
  /// @return True if an event was removed.
  bool Pop(Event* event);

  /// @return Number of queued events.
  uint8_t size() const { return count_; }
  /// @return Number of dropped events, clamped at the counter limit.
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
