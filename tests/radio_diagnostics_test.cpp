// Checks radio event FIFO ordering, capacity, and saturating overflow behavior.
#include "features/diagnostics/radio_diagnostics.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main() {
  radio_diagnostics::EventQueue queue;
  radio_diagnostics::Event event = {};
  assert(queue.size() == 0);
  assert(!queue.Pop(nullptr));
  assert(!queue.Pop(&event));

  for (uint8_t i = 0; i < radio_diagnostics::EventQueue::kCapacity; ++i) {
    const radio_diagnostics::Event next = {
        "queued", i, -1, 2, i, static_cast<uint16_t>(0x1200U + i)};
    assert(queue.Push(next));
  }
  assert(queue.size() == radio_diagnostics::EventQueue::kCapacity);

  const radio_diagnostics::Event dropped = {"dropped", 0, -2, 3, 0, 0xFFFFU};
  for (uint32_t i = 0; i < static_cast<uint32_t>(UINT16_MAX) + 2; ++i)
    assert(!queue.Push(dropped));
  assert(queue.overflow_count() == UINT16_MAX);

  const uint8_t consumed = radio_diagnostics::EventQueue::kCapacity / 2;
  for (uint8_t i = 0; i < consumed; ++i) {
    assert(queue.Pop(&event));
    assert(event.time_ms == i && event.sequence == i);
    assert(event.campaign_id == static_cast<uint16_t>(0x1200U + i));
  }
  for (uint8_t i = 0; i < consumed; ++i) {
    const uint8_t sequence =
        static_cast<uint8_t>(radio_diagnostics::EventQueue::kCapacity + i);
    const radio_diagnostics::Event next = {
        "wrapped", sequence, 0,
        4,         sequence, static_cast<uint16_t>(0x3400U + sequence)};
    assert(queue.Push(next));
  }
  for (uint8_t i = consumed; i < radio_diagnostics::EventQueue::kCapacity;
       ++i) {
    assert(queue.Pop(&event));
    assert(event.time_ms == i && event.sequence == i);
  }
  for (uint8_t i = 0; i < consumed; ++i) {
    assert(queue.Pop(&event));
    assert(event.name[0] == 'w');
    assert(event.sequence ==
           static_cast<uint8_t>(radio_diagnostics::EventQueue::kCapacity + i));
    assert(event.campaign_id ==
           static_cast<uint16_t>(0x3400U +
                                 radio_diagnostics::EventQueue::kCapacity + i));
  }
  assert(queue.size() == 0);
  puts("PASS bounded diagnostics FIFO and overflow accounting");
}
