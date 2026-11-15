#pragma once

#include <stdint.h>
#include <stddef.h>
#include <time.h>
#include "pt/pt.h"

#ifndef MAX_TASKS
#define MAX_TASKS 10
#endif

#define TASK          PT_THREAD
#define TASK_BEGIN()  PT_BEGIN(&_pt)
#define TASK_END()    PT_END(&_pt)
#define TASK_YIELD()  PT_YIELD(&_pt)
#define TASK_WAIT_UNTIL(cond)  PT_WAIT_UNTIL(&_pt, (cond))
#define TASK_WAIT_WHILE(cond)  PT_WAIT_WHILE(&_pt, (cond))

#define TASK_TIMER_START(ts)            ts = millis();
#define TASK_TIMER_EXPIRED(ts, timeout) ((millis()-ts) > (timeout))

#define TASK_DELAY(ms,tsVar) \
        do { \
          tsVar = millis(); \
          PT_WAIT_UNTIL(&_pt, millis()-tsVar >= (ms)); \
        } while (0);

/** 
 * Put task to sleep for the specified time in seconds.
 */
#define TASK_SLEEP_FOR(sec) \
        do { \
            set_wakeup_time(get_total_seconds() + sec); \
            TASK_WAIT_UNTIL(get_total_seconds() >= get_wakeup_time()); \
            reset_wakeup_time(); \
        } while (0);

/** 
 * Put task to sleep for the specified time in seconds.  When the condition is
 * met AND the CPU *is not sleeping*, the task will continue right away.
 */
#define TASK_SLEEP_FOR_OR_UNTIL(sec, cond) \
        do { \
            set_wakeup_time(get_total_seconds() + sec); \
            TASK_WAIT_UNTIL((get_total_seconds() >= get_wakeup_time()) || (cond)); \
            reset_wakeup_time(); \
        } while (0);

#define TASK_WAIT_UNTIL_OR_TIMEOUT(cond, timeout, tsVar)  \
        do { \
          tsVar = millis(); \
          TASK_WAIT_UNTIL((cond) || (millis() - tsVar > (timeout))); \
        } while (0);

/** 
 * @brief Abstract class for cooperative multitasking
 *
 * Minimum definitions of tasks for cooperative multitasking environment
 *
 * @author Chaiporn Jaikaeo <chaiporn.j@ku.ac.th>
 *
 */
class Task {
private:
    void _init();

protected:
    struct pt _pt;
    uint32_t _wakeup;
    bool _is_paused;

public:
    Task();
    void set_wakeup_time(uint32_t seconds);
    void reset_wakeup_time();
    uint32_t get_wakeup_time();
    virtual const char* get_name() = 0;
    virtual TASK(run()) = 0;
    void pause();
    bool is_paused();
    void resume();
    void restart();
};

/** 
 * @brief Simple cooperative task scheduler
 *
 * Definitions for task scheduler with an implementation of simple round-robin
 * algorithm
 *
 * @author Chaiporn Jaikaeo <chaiporn.j@ku.ac.th>
 *
 */
class TaskScheduler {
protected:
    Task* _tasks[MAX_TASKS];
    size_t _task_count;
public:
    TaskScheduler(): _task_count(0) {}
    void loop();
    void add(Task* task);
    Task** get_task_list();
    size_t get_task_count();
};

/** 
 * @brief Power-saving cooperative task scheduler
 *
 * Definitions for task scheduler with an implementation of sleep-enabled
 * algorithm
 *
 * @author Chaiporn Jaikaeo <chaiporn.j@ku.ac.th>
 *
 */
class PowerSavingTaskScheduler: public TaskScheduler {
public:
    void loop();
};
