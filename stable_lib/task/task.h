// Provides the cooperative protothread task and scheduler wrappers used by
// application code. The protothread implementation itself remains vendored.
#ifndef IW_TASK_TASK_H_
#define IW_TASK_TASK_H_

#include <stddef.h>
#include <stdint.h>
#include <time.h>

#include "pt/pt.h"
#include "time-utils.h"

inline constexpr size_t kMaxTasks = 10U;

// P10-PT-001: these wrappers are the required macro surface around vendored
// protothread continuation macros; each expands to one bounded scheduler step.
// P10-PT-001
#define TASK PT_THREAD
// P10-PT-001
#define TASK_BEGIN() PT_BEGIN(&pt_)
// P10-PT-001
#define TASK_END() PT_END(&pt_)
// P10-PT-001
#define TASK_YIELD() PT_YIELD(&pt_)
// P10-PT-001
#define TASK_WAIT_UNTIL(cond) PT_WAIT_UNTIL(&pt_, (cond))
// P10-PT-001
#define TASK_WAIT_WHILE(cond) PT_WAIT_WHILE(&pt_, (cond))

// P10-PT-001: the delay wrapper retains the vendored continuation contract.
// P10-PT-001
#define TASK_TIMER_START(ts) ts = millis();
// P10-PT-001
#define TASK_TIMER_EXPIRED(ts, timeout) ((millis() - ts) > (timeout))

// P10-PT-001
#define TASK_DELAY(ms, tsVar)                      \
  do {                                             \
    tsVar = millis();                              \
    PT_WAIT_UNTIL(&pt_, millis() - tsVar >= (ms)); \
  } while (0);

// Suspends the current task until seconds have elapsed on the tracker clock.
// P10-PT-001
#define TASK_SLEEP_FOR(sec)                                \
  do {                                                     \
    SetWakeupTime(GetTotalSeconds() + sec);                \
    TASK_WAIT_UNTIL(GetTotalSeconds() >= GetWakeupTime()); \
    ResetWakeupTime();                                     \
  } while (0);

// Suspends the current task until seconds elapse or condition becomes true.
// P10-PT-001
#define TASK_SLEEP_FOR_OR_UNTIL(sec, cond)                             \
  do {                                                                 \
    SetWakeupTime(GetTotalSeconds() + sec);                            \
    TASK_WAIT_UNTIL((GetTotalSeconds() >= GetWakeupTime()) || (cond)); \
    ResetWakeupTime();                                                 \
  } while (0);

// P10-PT-001
#define TASK_WAIT_UNTIL_OR_TIMEOUT(cond, timeout, tsVar)       \
  do {                                                         \
    tsVar = millis();                                          \
    TASK_WAIT_UNTIL((cond) || (millis() - tsVar > (timeout))); \
  } while (0);

// Base class for one cooperative protothread. Subclasses implement Run() and
// must not block outside the TASK_* scheduling macros.
class Task {
 private:
  // Resets scheduling state without changing the protothread stack itself.
  void Initialize();

 protected:
  struct pt pt_;          // Vendored protothread continuation state.
  uint32_t wakeup_time_;  // Absolute tracker time at which the task may run.
  bool is_paused_;        // Paused tasks are skipped by schedulers.

 public:
  // Constructs a task in the initial runnable state.
  Task();

  // Sets or clears the absolute tracker time used by TASK_SLEEP_FOR macros.
  void SetWakeupTime(uint32_t seconds);
  void ResetWakeupTime();

  // Returns the currently configured wakeup time.
  uint32_t GetWakeupTime();

  // Returns a stable diagnostic name supplied by each concrete task.
  // P10-PT-002: the legacy scheduler owns this support-boundary dispatch; FOTA,
  // boot, and NVM core code do not depend on Task virtual calls.
  // P10-PT-002
  virtual const char* GetName() = 0;

  // Runs one bounded cooperative step for the concrete task.
  // P10-PT-002
  virtual TASK(Run()) = 0;

  // Changes whether the scheduler invokes this task.
  void Pause();
  bool IsPaused();
  void Resume();

  // Restarts the protothread and clears its scheduling state.
  void Restart();
};

// Runs each unpaused task once per scheduler tick in insertion order.
class TaskScheduler {
 protected:
  Task* tasks_[kMaxTasks];  // Non-owning task pointers.
  size_t task_count_;       // Number of populated entries in tasks_.

 public:
  // Constructs an empty scheduler; task objects remain caller-owned.
  TaskScheduler() : tasks_{}, task_count_(0U) {}

  // Runs one bounded step for every unpaused task.
  void Loop();

  // Adds a non-null task pointer until kMaxTasks is reached.
  void Add(Task* task);

  // Returns one non-owning task pointer, or nullptr for an invalid index.
  [[nodiscard]] Task* GetTask(size_t index) const;

  // Returns the number of populated task entries.
  [[nodiscard]] size_t GetTaskCount() const;
};

// Runs tasks, then sleeps until the earliest unpaused task wakeup time.
class PowerSavingTaskScheduler : public TaskScheduler {
 public:
  // Executes one task round and enters standby when no task is due.
  void Loop();
};

#endif  // IW_TASK_TASK_H_
