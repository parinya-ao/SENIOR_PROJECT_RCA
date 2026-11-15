#pragma once

#include <TimeLib.h>
#include <stdint.h>
#include "sleep.h"

void init_time();
void set_time(uint16_t year,
              uint8_t  month,
              uint8_t  day,
              uint8_t  hour,
              uint8_t  minute,
              uint8_t  second);
uint32_t get_total_seconds();
char* get_current_time_str();

#define get_hours()      hour(g_sleep_unix_time)
#define get_minutes()    minute(g_sleep_unix_time)
#define get_seconds()    second(g_sleep_unix_time)
#define get_year()       year(g_sleep_unix_time)
#define get_month()      month(g_sleep_unix_time)
#define get_day()        day(g_sleep_unix_time)
