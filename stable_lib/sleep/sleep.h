// Exposes tracker sleep policy and its interrupt-safe wall-clock state.
#ifndef IW_SLEEP_POLICY_SLEEP_H_
#define IW_SLEEP_POLICY_SLEEP_H_

#include <stdint.h>

#include "avr128da28_device.h"

/// @brief Initializes RTC hardware and foreground sleep policy state.
/// @post The wall clock starts from its configured initial timestamp.
void InitializeSleep();

/// @brief Sleeps for the requested duration unless woken early.
/// @param seconds Maximum sleep duration in seconds.
/// @post ForceWakeup ends sleep on the next RTC cycle, at most one second
/// later.
void SleepFor(uint32_t seconds);

/// @brief Updates wall-clock state from RTC ticks and reads the counter.
/// @return Current RTC tick count.
[[nodiscard]] uint32_t SleepRtcTicks();

/// @brief Reads the current wall-clock timestamp.
/// @return Unix timestamp in seconds.
[[nodiscard]] uint32_t GetUnixTime();

/// @brief Sets wall-clock time without changing interrupt enable state.
/// @param timestamp New Unix timestamp in seconds.
void SetUnixTime(uint32_t timestamp);

/// @brief Requests an active SleepFor() call to wake early.
/// @post The request is consumed by the next RTC wake cycle.
void ForceWakeup();

#endif  // IW_SLEEP_POLICY_SLEEP_H_
