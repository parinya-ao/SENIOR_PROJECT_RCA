#include <Arduino.h>
#include <avr/sleep.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <util/atomic.h>
#include <TimeLib.h>
#include "sleep.h"

static volatile uint32_t _rtc_ticks;
static volatile uint32_t g_sleep_unix_time;
volatile bool g_sleep_force_wakeup;
bool g_sleep_is_sleeping;

/************************************************************
 * Initialize RTC with PIT interrupt
 * (adapted from https://github.com/SpenceKonde/megaTinyCore/blob/master/megaavr/extras/PowerSave.md)
 */
static void rtc_init(void) {
    while (RTC.STATUS > 0) {}             /* Wait for all register to be synchronized */
    RTC.CLKSEL = RTC_CLKSEL_OSC32K_gc;    /* 32.768kHz Internal Ultra-Low-Power Oscillator (OSCULP32K) */

    RTC.PITINTCTRL = RTC_PI_bm;           /* PIT Interrupt: enabled */

    RTC.PITCTRLA = RTC_PERIOD_CYC32768_gc
                 | RTC_PITEN_bm;          /* Enable PIT counter: enabled */
}

ISR(RTC_PIT_vect) {
    RTC.PITINTFLAGS = RTC_PI_bm;          /* Clear interrupt flag by writing '1' (required) */
    _rtc_ticks++;
    g_sleep_unix_time++;
}

/************************************************************
 * Return the current value of RTC's ticks
 */
static uint32_t rtc_ticks() {
    uint32_t val;

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        val = _rtc_ticks;
    }
    return val;
}

/************************************************************
 * Reset RTC's ticks
 */
static void rtc_reset_ticks() {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        _rtc_ticks = 0;
    }
}

/************************************************************
 * Enable RTC
 */
static void rtc_start() {
    while (RTC.STATUS > 0) {} // Wait for all register to be synchronized
    RTC.CNT = 0;
    RTC.CTRLA |= RTC_RTCEN_bm;
    rtc_reset_ticks();
}

/************************************************************
 * Disable RTC
 */
static void rtc_stop() {
    while (RTC.STATUS > 0) {} // Wait for all register to be synchronized
    RTC.CTRLA &= ~RTC_RTCEN_bm;
}

/************************************************************
 * Go into standby sleep for the specified seconds
 */
void sleep_init() {
    g_sleep_force_wakeup = false;
    g_sleep_is_sleeping = false;
    g_sleep_unix_time = 0;
    rtc_init();
    rtc_reset_ticks();
    set_sleep_mode(SLEEP_MODE_PWR_DOWN);
    sleep_enable();     
}

/************************************************************
 * Go into standby sleep for the specified seconds
 */
void sleep_for(uint32_t seconds) {
    uint32_t ts = rtc_ticks();
    bool force_wakeup = false;
    g_sleep_is_sleeping = true;
    g_sleep_force_wakeup = false;
    while (rtc_ticks() - ts < seconds) {
        sleep_cpu();
        wdt_reset();
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
            if (g_sleep_force_wakeup) {
                force_wakeup = true;
            }
        }
        if (force_wakeup) {
            break;
        }
    }
    g_sleep_is_sleeping = false;
}

/************************************************************
 * Return the number of seconds since last reboot
 */
uint32_t sleep_rtc_ticks() {
    return rtc_ticks();
}
