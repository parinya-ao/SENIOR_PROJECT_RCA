// Declares the tracker wall-clock and formatted-time helpers.
#ifndef IW_TIME_UTILS_TIME_UTILS_H_
#define IW_TIME_UTILS_TIME_UTILS_H_

#include <TimeLib.h>
#include <stdint.h>

#include "sleep.h"

// Initializes the wall clock to the project epoch (2000-01-01 00:00:00).
void InitializeTime();

// Sets the wall clock from calendar fields expressed in UTC.
void SetTime(uint16_t year, uint8_t month, uint8_t day, uint8_t hour,
             uint8_t minute, uint8_t second);

// Returns the current wall-clock time as seconds since the project epoch.
[[nodiscard]] uint32_t GetTotalSeconds();

// Returns a pointer to a static formatted buffer invalidated by the next call.
[[nodiscard]] char* GetCurrentTimeString();

[[nodiscard]] inline uint8_t GetHours() { return hour(GetUnixTime()); }
[[nodiscard]] inline uint8_t GetMinutes() { return minute(GetUnixTime()); }
[[nodiscard]] inline uint8_t GetSeconds() { return second(GetUnixTime()); }
[[nodiscard]] inline uint16_t GetYear() { return year(GetUnixTime()); }
[[nodiscard]] inline uint8_t GetMonth() { return month(GetUnixTime()); }
[[nodiscard]] inline uint8_t GetDay() { return day(GetUnixTime()); }

#endif  // IW_TIME_UTILS_TIME_UTILS_H_
