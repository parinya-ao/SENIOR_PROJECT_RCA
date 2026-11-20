// Declares the tracker wall-clock and formatted-time helpers.
#ifndef IW_TIME_UTILS_TIME_UTILS_H_
#define IW_TIME_UTILS_TIME_UTILS_H_

#include <TimeLib.h>
#include <stdint.h>

#include "sleep.h"

/// @brief Initializes the wall clock to the project epoch.
/// @post The timestamp is set to 2000-01-01 00:00:00 UTC.
void InitializeTime();

/// @brief Sets wall-clock time from UTC calendar fields.
/// @param year Calendar year supported by TimeLib.
/// @param month Calendar month.
/// @param day Day of month.
/// @param hour Hour of day.
/// @param minute Minute of hour.
/// @param second Second of minute.
void SetTime(uint16_t year, uint8_t month, uint8_t day, uint8_t hour,
             uint8_t minute, uint8_t second);

/// @brief Returns wall-clock time relative to the project epoch.
/// @return Seconds since 2000-01-01 00:00:00 UTC.
[[nodiscard]] uint32_t GetTotalSeconds();

/// @brief Formats the current time for display.
/// @return Static string buffer, invalidated by the next call.
[[nodiscard]] char* GetCurrentTimeString();

/// @brief Returns the hour field of the current wall-clock time.
[[nodiscard]] inline uint8_t GetHours() { return hour(GetUnixTime()); }
/// @brief Returns the minute field of the current wall-clock time.
[[nodiscard]] inline uint8_t GetMinutes() { return minute(GetUnixTime()); }
/// @brief Returns the second field of the current wall-clock time.
[[nodiscard]] inline uint8_t GetSeconds() { return second(GetUnixTime()); }
/// @brief Returns the year field of the current wall-clock time.
[[nodiscard]] inline uint16_t GetYear() { return year(GetUnixTime()); }
/// @brief Returns the month field of the current wall-clock time.
[[nodiscard]] inline uint8_t GetMonth() { return month(GetUnixTime()); }
/// @brief Returns the day-of-month field of the current wall-clock time.
[[nodiscard]] inline uint8_t GetDay() { return day(GetUnixTime()); }

#endif  // IW_TIME_UTILS_TIME_UTILS_H_
