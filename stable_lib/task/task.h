/// @file
/// Provides cooperative task wrappers around the vendored protothread engine.
#ifndef IW_TASK_TASK_H_
#define IW_TASK_TASK_H_

#include <stddef.h>
#include <stdint.h>
#include <time.h>

#include "pt/pt.h"
#include "time-utils.h"

/// Maximum number of non-owning task pointers held by a scheduler.
inline constexpr size_t kMaxTasks = 10U;

/// Adapts the vendored protothread entry point to the project task API.
// P10-PT-001
#define TASK PT_THREAD
/// Begins the resumable body of a Task::Run() protothread.
#define TASK_BEGIN() PT_BEGIN(&pt_)
/// Ends the resumable body of a Task::Run() protothread.
#define TASK_END() PT_END(&pt_)
/// Yields the current task until its next scheduler call.
#define TASK_YIELD() PT_YIELD(&pt_)
/// Waits until cond evaluates to true, resuming at the next scheduler call.
#define TASK_WAIT_UNTIL(cond) PT_WAIT_UNTIL(&pt_, (cond))
/// Waits while cond evaluates to true, resuming at the next scheduler call.
#define TASK_WAIT_WHILE(cond) PT_WAIT_WHILE(&pt_, (cond))

/// Starts a timer using the Arduino millisecond clock.
#define TASK_TIMER_START(ts) ((ts) = millis());
/// Checks whether timeout milliseconds have elapsed since ts.
#define TASK_TIMER_EXPIRED(ts, timeout) ((millis() - (ts)) > (timeout))

/// Yields until ms milliseconds elapse, preserving the continuation state.
#define TASK_DELAY(ms, tsVar)                        \
  do {                                               \
    (tsVar) = millis();                              \
    PT_WAIT_UNTIL(&pt_, millis() - (tsVar) >= (ms)); \
  } while (0);

/// Suspends the task until sec tracker-clock seconds have elapsed.
#define TASK_SLEEP_FOR(sec)                                \
  do {                                                     \
    SetWakeupTime(GetTotalSeconds() + (sec));              \
    TASK_WAIT_UNTIL(GetTotalSeconds() >= GetWakeupTime()); \
    ResetWakeupTime();                                     \
  } while (0);

/// Suspends the task until sec tracker-clock seconds elapse or cond is true.
#define TASK_SLEEP_FOR_OR_UNTIL(sec, cond)                             \
  do {                                                                 \
    SetWakeupTime(GetTotalSeconds() + (sec));                          \
    TASK_WAIT_UNTIL((GetTotalSeconds() >= GetWakeupTime()) || (cond)); \
    ResetWakeupTime();                                                 \
  } while (0);

/// Yields until cond is true or timeout milliseconds have elapsed.
#define TASK_WAIT_UNTIL_OR_TIMEOUT(cond, timeout, tsVar)         \
  do {                                                           \
    (tsVar) = millis();                                          \
    TASK_WAIT_UNTIL((cond) || (millis() - (tsVar) > (timeout))); \
  } while (0);

/// Base class for one cooperative protothread task.
///
/// Subclasses implement GetName() and the TASK(Run()) body. A body must yield
/// through TASK_* macros instead of blocking the foreground loop.
class Task {
 private:
  /// Resets scheduling state without changing the protothread continuation.
  void Initialize();

 protected:
  struct pt pt_;          ///< Vendored protothread continuation state.
  uint32_t wakeup_time_;  ///< Absolute tracker time at which the task may run.
  bool is_paused_;        ///< Whether schedulers skip this task.

 public:
  /// Constructs a task in the initial runnable state.
  Task();

  /// Sets the absolute tracker-clock deadline used by TASK_SLEEP_FOR.
  /// @param seconds Absolute tracker time in seconds, not millis().
  void SetWakeupTime(uint32_t seconds);
  /// Clears the configured wakeup deadline.
  void ResetWakeupTime();

  /// Returns the configured absolute tracker-clock deadline.
  /// @return Deadline in seconds, or zero when no wakeup is configured.
  uint32_t GetWakeupTime();

  /// Returns the concrete task's stable diagnostic name.
  /// @return Borrowed, null-terminated name valid for the task lifetime.
  virtual const char* GetName() = 0;

  /// Defines the protothread body that performs one bounded cooperative step.
  /// @return Continuation status defined by the vendored PT_* macros.
  virtual TASK(Run()) = 0;

  /// Pauses scheduler invocation without destroying continuation state.
  void Pause();
  /// Reports whether schedulers currently skip this task.
  /// @return True when paused.
  bool IsPaused();
  /// Allows a scheduler to invoke this task again.
  void Resume();

  /// Restarts the protothread and clears its wakeup/pause state.
  void Restart();
};

/// Runs each unpaused task once per scheduler tick in insertion order.
class TaskScheduler {
 protected:
  Task* tasks_[kMaxTasks];  ///< Non-owning task pointers in insertion order.
  size_t task_count_;       ///< Number of populated entries in tasks_.

 public:
  /// Constructs an empty scheduler; task objects remain caller-owned.
  TaskScheduler() : tasks_{}, task_count_(0U) {}

  /// Runs one bounded step for every unpaused task.
  void Loop();

  /// Adds a task unless the pointer is null or capacity is exhausted.
  /// @param task Caller-owned task whose lifetime must cover scheduler use.
  void Add(Task* task);

  /// Returns one non-owning task pointer.
  /// @param index Zero-based insertion-order index.
  /// @return Task pointer, or nullptr when index is outside the populated
  /// range.
  [[nodiscard]] Task* GetTask(size_t index) const;

  /// Returns the number of populated task entries.
  /// @return Number of tasks currently stored.
  [[nodiscard]] size_t GetTaskCount() const;
};

/// Runs tasks, then sleeps until the earliest unpaused task wakeup time.
class PowerSavingTaskScheduler : public TaskScheduler {
 public:
  /// Executes one task round and enters standby when no task is due.
  /// This concrete policy has no in-tree caller through TaskScheduler*.
  // NOLINTNEXTLINE(bugprone-derived-method-shadowing-base-method)
  void Loop();
};

#endif  // IW_TASK_TASK_H_
