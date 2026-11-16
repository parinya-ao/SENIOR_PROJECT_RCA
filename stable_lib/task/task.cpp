#include "sleep.h"
#include "time-utils.h"
#include "task.h"
#include "debug.h"

/***************************************************
 *
 */
Task::Task() {
    PT_INIT(&_pt);
    _init();
}

/***************************************************
 *
 */
void Task::_init() {
    _wakeup = 0;
    _is_paused = false;
}

/***************************************************
 *
 */
void Task::set_wakeup_time(uint32_t seconds) {
    _wakeup = seconds;
}

/***************************************************
 *
 */
void Task::reset_wakeup_time() {
    _wakeup = 0;
}

/***************************************************
 *
 */
uint32_t Task::get_wakeup_time() {
    return _wakeup;
}

/***************************************************
 *
 */
void Task::pause() {
    _is_paused = true;
}

/***************************************************
 *
 */
bool Task::is_paused() {
    return _is_paused;
}

/***************************************************
 *
 */
void Task::resume() {
    _is_paused = false;
}

/***************************************************
 *
 */
void Task::restart() {
    _init();
    PT_RESTART(&_pt);
}


/***************************************************
 *
 */
void TaskScheduler::add(Task* task) {
    _tasks[_task_count++] = task;
}

/***************************************************
 *
 */
Task** TaskScheduler::get_task_list() {
    return _tasks;
}

/***************************************************
 *
 */
size_t TaskScheduler::get_task_count() {
    return _task_count;
}

/***************************************************
 *
 */
void TaskScheduler::loop() {
    for (size_t i = 0; i < _task_count; i++) {
        if (!_tasks[i]->is_paused()) {
            _tasks[i]->run();
        }
    }
}

/***************************************************
 *
 */
void PowerSavingTaskScheduler::loop() {
    uint32_t min_wakeup_time = (uint32_t)-1;
    uint32_t wakeup_time;
    uint32_t current;
    for (uint8_t i=0; i < _task_count; i++) {
        if (!_tasks[i]->is_paused()) {
            // always run unpaused tasks no matter they are sleeping or not;
            // in case they need to be woken up by some other source
            _tasks[i]->run();
        }
    }

    for (uint8_t i=0; i < _task_count; i++) {
        if (!_tasks[i]->is_paused()) {
            // determine the earliest wakeup time among all the unpaused tasks
            wakeup_time = _tasks[i]->get_wakeup_time();
            if (wakeup_time < min_wakeup_time) {
                min_wakeup_time = wakeup_time;
            }
        }
    }

    // if there is some time before the earliest wakeup time, put the CPU to sleep
    current = get_total_seconds();
    if (min_wakeup_time >= current) {
        DEBUG_TS("Scheduler: Going to sleep for %" PRIu32 " seconds\r\n", min_wakeup_time - current);
        DEBUG_FLUSH();
        sleep_for(min_wakeup_time - current);
    }
}
