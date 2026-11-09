// Converts the tracker wall-clock state to calendar fields and display text.
#include "time-utils.h"

#include <TimeLib.h>
#include <stdio.h>

namespace {

// Shared formatting buffer; callers must consume the result before the next
// GetCurrentTimeString() call.
char g_datetime_string[30];

}  // namespace

void InitializeTime() { SetTime(2000, 1, 1, 0, 0, 0); }

void SetTime(uint16_t year, uint8_t month, uint8_t day, uint8_t hour,
             uint8_t minute, uint8_t second) {
  tmElements_t time_elements;
  time_elements.Year = year - 1970;
  time_elements.Month = month;
  time_elements.Day = day;
  time_elements.Hour = hour;
  time_elements.Minute = minute;
  time_elements.Second = second;
  const uint32_t unix_time = makeTime(time_elements);

  SetUnixTime(unix_time);
}

uint32_t GetTotalSeconds() { return GetUnixTime(); }

char* GetCurrentTimeString() {
  snprintf(g_datetime_string, sizeof(g_datetime_string),
           "%u-%02u-%02u %02u:%02u:%02u", static_cast<unsigned int>(GetYear()),
           static_cast<unsigned int>(GetMonth()),
           static_cast<unsigned int>(GetDay()),
           static_cast<unsigned int>(GetHours()),
           static_cast<unsigned int>(GetMinutes()),
           static_cast<unsigned int>(GetSeconds()));
  return g_datetime_string;
}
