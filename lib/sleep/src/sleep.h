// Exposes tracker sleep policy and its interrupt-safe wall-clock state.
#ifndef IW_SLEEP_POLICY_SLEEP_H_
#define IW_SLEEP_POLICY_SLEEP_H_

#include <stdint.h>

#include "iw/avr128da28/device.h"

// Initializes the RTC and standby-sleep policy state.
void InitializeSleep();

// Sleeps for up to seconds, returning earlier when ForceWakeup() is requested.
void SleepFor(uint32_t seconds);

// Advances wall-clock state from RTC ticks and returns the current tick count.
[[nodiscard]] uint32_t SleepRtcTicks();

// Returns the current wall-clock timestamp in Unix seconds.
[[nodiscard]] uint32_t GetUnixTime();

// Sets the wall-clock timestamp while preserving the interrupt state.
void SetUnixTime(uint32_t timestamp);

// Requests SleepFor() to wake on its next RTC cycle (at most one second).
void ForceWakeup();

#endif  // IW_SLEEP_POLICY_SLEEP_H_
