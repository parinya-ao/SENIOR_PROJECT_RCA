// Implements tracker sleep policy on top of the AVR128DA28 RTC primitives.
#include "sleep.h"

#include <Arduino.h>
#include <TimeLib.h>

#include "iw/avr128da28/device.h"
#include "iw/avr128da28/sleep.h"

namespace {

constexpr uint32_t kMaximumSleepSeconds = 86400U;

// This state is private to the sleep owner; ForceWakeup is the only ISR-facing
// operation and protects the volatile fields with the platform critical-section
// primitive.
struct SleepState {
  volatile uint32_t unix_time;
  volatile bool force_wakeup;
  bool is_sleeping;
  uint32_t last_rtc_ticks;
};

// P10-ISR-001: sleep and wake ISR paths share this bounded state owner.
SleepState g_sleep_state{};

}  // namespace

void InitializeSleep() {
  g_sleep_state = {};
  iw::avr128da28::InitializeRtc();
  iw::avr128da28::ConfigureStandbySleep();
}

void SleepFor(uint32_t seconds) {
  const uint32_t start_ticks = iw::avr128da28::ReadRtcTicks();
  const uint32_t bounded_seconds =
      seconds > kMaximumSleepSeconds ? kMaximumSleepSeconds : seconds;
  if (bounded_seconds == 0U) {
    g_sleep_state.is_sleeping = false;
    return;
  }
  bool should_wake = false;
  g_sleep_state.is_sleeping = true;
  g_sleep_state.force_wakeup = false;
  for (uint32_t elapsed = 0U; elapsed < bounded_seconds && !should_wake;
       ++elapsed) {
    iw::avr128da28::EnterStandbySleep();
    iw::avr128da28::ResetWatchdog();
    const uint8_t saved_status = iw::avr128da28::SaveAndDisableInterrupts();
    if (g_sleep_state.force_wakeup ||
        iw::avr128da28::ReadRtcTicks() - start_ticks >= bounded_seconds) {
      should_wake = true;
    }
    iw::avr128da28::RestoreInterruptState(saved_status);
  }
  g_sleep_state.is_sleeping = false;
}

// Advances the wall clock by the RTC ticks elapsed since the previous call.
uint32_t SleepRtcTicks() {
  const uint32_t ticks = iw::avr128da28::ReadRtcTicks();
  const uint32_t elapsed = ticks - g_sleep_state.last_rtc_ticks;
  if (elapsed != 0U) {
    const uint8_t saved_status = iw::avr128da28::SaveAndDisableInterrupts();
    g_sleep_state.unix_time += elapsed;
    iw::avr128da28::RestoreInterruptState(saved_status);
    g_sleep_state.last_rtc_ticks = ticks;
  }
  return ticks;
}

uint32_t GetUnixTime() { return g_sleep_state.unix_time; }

void SetUnixTime(uint32_t timestamp) {
  const uint8_t saved_status = iw::avr128da28::SaveAndDisableInterrupts();
  g_sleep_state.unix_time = timestamp;
  iw::avr128da28::RestoreInterruptState(saved_status);
}

void ForceWakeup() {
  const uint8_t saved_status = iw::avr128da28::SaveAndDisableInterrupts();
  g_sleep_state.force_wakeup = true;
  iw::avr128da28::RestoreInterruptState(saved_status);
}
