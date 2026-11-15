#pragma once
#include <stdint.h>
#include <util/atomic.h>

extern volatile bool g_sleep_force_wakeup;
extern bool g_sleep_is_sleeping;
extern volatile uint32_t g_sleep_unix_time;

void sleep_init();
void sleep_for(uint32_t seconds);
uint32_t sleep_rtc_ticks();

/************************************************************
 * Return current unix timestamp (the number of seconds since epoch)
 */
inline uint32_t sleep_get_unix_time() {
    return g_sleep_unix_time;
}
/************************************************************
 * Set current unix time stamp (the number of seconds since epoch)
 */
inline void sleep_set_unix_time(uint32_t ts) {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        g_sleep_unix_time = ts;
    }
}

/************************************************************
 * Force sleep_for() to wake up right away (max 1 second delay)
 */
inline void sleep_force_wakeup() {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        g_sleep_force_wakeup = true;
    }
}
