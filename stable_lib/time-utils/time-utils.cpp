#include <TimeLib.h>
#include <stdio.h>
#include "time-utils.h"

char _datetime_string[30];

void init_time() {
    set_time(2000, 1, 1, 0, 0, 0);
}

/************************************
 *
 */
void set_time(uint16_t year,
              uint8_t  month,
              uint8_t  day,
              uint8_t  hour,
              uint8_t  minute,
              uint8_t  second) {
    tmElements_t tm;
    tm.Year   = year - 1970;
    tm.Month  = month;
    tm.Day    = day;
    tm.Hour   = hour;
    tm.Minute = minute;
    tm.Second = second;
    uint32_t ts = makeTime(tm);

    sleep_set_unix_time(ts);
}

/************************************
 *
 */
uint32_t get_total_seconds() {
    return sleep_get_unix_time();
}

/************************************
 *
 */
char* get_current_time_str() {
    sprintf(_datetime_string, "%d-%02d-%02d %02d:%02d:%02d",
            get_year(),
            get_month(),
            get_day(),
            get_hours(),
            get_minutes(),
            get_seconds());
    return _datetime_string;
}

