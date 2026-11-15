#include "task.h"

#include "sleep.h"
#include "time-utils.h"

// Initializes the protothread continuation and scheduling state.
Task::Task() {
  PT_INIT(&pt_);
  Initialize();
}

void Task::Initialize() {
  wakeup_time_ = 0U;
  is_paused_ = false;
}

void Task::SetWakeupTime(uint32_t seconds) { wakeup_time_ = seconds; }

void Task::ResetWakeupTime() { wakeup_time_ = 0U; }

uint32_t Task::GetWakeupTime() { return wakeup_time_; }

void Task::Pause() { is_paused_ = true; }

bool Task::IsPaused() { return is_paused_; }

void Task::Resume() { is_paused_ = false; }

void Task::Restart() {
  Initialize();
  PT_INIT(&pt_);
}

void TaskScheduler::Add(Task* task) {
  if (task != nullptr && task_count_ < kMaxTasks) {
    tasks_[task_count_++] = task;
  }
}

Task* TaskScheduler::GetTask(size_t index) const {
  return index < task_count_ ? tasks_[index] : nullptr;
}

size_t TaskScheduler::GetTaskCount() const { return task_count_; }

void TaskScheduler::Loop() {
  for (size_t task_index = 0U; task_index < task_count_; ++task_index) {
    if (!tasks_[task_index]->IsPaused()) {
      tasks_[task_index]->Run();
    }
  }
}

void PowerSavingTaskScheduler::Loop() {
  uint32_t earliest_wakeup_time = UINT32_MAX;
  uint32_t current_time;
  for (size_t task_index = 0U; task_index < task_count_; ++task_index) {
    if (!tasks_[task_index]->IsPaused()) {
      // always run unpaused tasks no matter they are sleeping or not;
      // in case they need to be woken up by some other source
      tasks_[task_index]->Run();
    }
  }

  for (size_t task_index = 0U; task_index < task_count_; ++task_index) {
    if (!tasks_[task_index]->IsPaused()) {
      // determine the earliest wakeup time among all the unpaused tasks
      const uint32_t wakeup_time = tasks_[task_index]->GetWakeupTime();
      if (wakeup_time < earliest_wakeup_time) {
        earliest_wakeup_time = wakeup_time;
      }
    }
  }

  // if there is some time before the earliest wakeup time, put the CPU to sleep
  current_time = GetTotalSeconds();
  if (earliest_wakeup_time >= current_time) {
    SleepFor(earliest_wakeup_time - current_time);
  }
}
