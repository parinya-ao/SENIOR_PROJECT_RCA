// Implements the fixed-capacity FIFO used to defer radio diagnostics.

#include "radio_diagnostics.h"

bool radio_diagnostics::EventQueue::Push(
    const radio_diagnostics::Event& event) {
  if (count_ == kCapacity) {
    if (overflow_count_ != UINT16_MAX) ++overflow_count_;
    return false;
  }
  const uint8_t tail = static_cast<uint8_t>((head_ + count_) % kCapacity);
  events_[tail] = event;
  ++count_;
  return true;
}

bool radio_diagnostics::EventQueue::Pop(radio_diagnostics::Event* event) {
  if (!event || !count_) return false;
  *event = events_[head_];
  head_ = static_cast<uint8_t>((head_ + 1U) % kCapacity);
  --count_;
  return true;
}
